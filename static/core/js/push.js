(() => {
  const button = document.getElementById("pantau-push-toggle");
  if (!button || !("serviceWorker" in navigator) || !("PushManager" in window)) {
    if (button) button.hidden = true;
    return;
  }

  const csrf = button.form.querySelector("[name=csrfmiddlewaretoken]").value;
  let registration;

  const applicationServerKey = (value) => {
    const padding = "=".repeat((4 - (value.length % 4)) % 4);
    const base64 = (value + padding).replace(/-/g, "+").replace(/_/g, "/");
    const raw = atob(base64);
    return Uint8Array.from([...raw].map((character) => character.charCodeAt(0)));
  };

  const post = async (url, payload) => {
    const response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      throw new Error(result.error || `HTTP ${response.status}`);
    }
  };

  const update = async () => {
    const subscription = await registration.pushManager.getSubscription();
    button.dataset.active = subscription ? "true" : "false";
    button.textContent = subscription ? "Nonaktifkan notifikasi" : "Aktifkan notifikasi";
  };

  navigator.serviceWorker.register(button.dataset.workerUrl, { scope: "/" })
    .then((workerRegistration) => {
      registration = workerRegistration;
      return update();
    })
    .catch((error) => {
      button.disabled = true;
      button.textContent = "Notifikasi tidak tersedia";
      button.title = error.message;
    });

  button.addEventListener("click", async () => {
    if (!registration) return;
    button.disabled = true;
    try {
      const existing = await registration.pushManager.getSubscription();
      if (existing) {
        await post(button.dataset.unsubscribeUrl, { endpoint: existing.endpoint });
        await existing.unsubscribe();
      } else {
        const permission = await Notification.requestPermission();
        if (permission !== "granted") throw new Error("Izin notifikasi ditolak browser.");
        const subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: applicationServerKey(button.dataset.publicKey),
        });
        await post(button.dataset.subscribeUrl, subscription.toJSON());
      }
      await update();
    } catch (error) {
      button.title = error.message;
    } finally {
      button.disabled = false;
    }
  });
})();
