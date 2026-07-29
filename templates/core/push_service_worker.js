self.addEventListener("push", (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch (_error) {
    payload = { title: "PANTAU", body: event.data ? event.data.text() : "" };
  }
  event.waitUntil(
    self.registration.showNotification(payload.title || "PANTAU", {
      body: payload.body || "",
      tag: payload.kind === "alert" ? `pantau-alert-${payload.triggered_at || ""}` : "pantau",
      data: { url: payload.url || "/ringkasan/" },
      requireInteraction: payload.severity === "critical",
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = event.notification.data && event.notification.data.url
    ? event.notification.data.url
    : "/ringkasan/";
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((windows) => {
      const existing = windows.find((windowClient) => windowClient.url.includes(target));
      return existing ? existing.focus() : clients.openWindow(target);
    })
  );
});
