from django.db import models

from apps.analytics.models import PoliticalIssue


class CoordinationCluster(models.Model):
    STATUS_FLAGGED = "flagged"
    STATUS_REVIEWED_ORGANIC = "reviewed_organic"
    STATUS_IGNORED = "ignored"
    STATUS_CHOICES = [
        (STATUS_FLAGGED, "Ditandai"),
        (STATUS_REVIEWED_ORGANIC, "Ditinjau — Organik"),
        (STATUS_IGNORED, "Diabaikan"),
    ]

    issue = models.ForeignKey(PoliticalIssue, on_delete=models.CASCADE, related_name="coordination_clusters")
    cluster_code = models.CharField(max_length=30, unique=True)
    score = models.DecimalField(max_digits=3, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_FLAGGED)
    account_count = models.PositiveIntegerField(default=0)
    detected_at = models.DateTimeField()
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-score"]

    def __str__(self):
        return self.cluster_code


class ClusterAccount(models.Model):
    ROLE_HUB = "hub"
    ROLE_AMPLIFIER = "amplifier"
    ROLE_SATELLITE = "satellite"
    ROLE_CHOICES = [
        (ROLE_HUB, "Pusat penyebaran"),
        (ROLE_AMPLIFIER, "Amplifier inti"),
        (ROLE_SATELLITE, "Akun satelit"),
    ]

    cluster = models.ForeignKey(CoordinationCluster, on_delete=models.CASCADE, related_name="accounts")
    handle = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    reach = models.PositiveIntegerField(default=0)
    post_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.handle


class CoordinationSignal(models.Model):
    SIGNAL_TEXT_SIMILARITY = "text_similarity"
    SIGNAL_TIME_SYNC = "time_sync"
    SIGNAL_ACCOUNT_AGE = "account_age"
    SIGNAL_SHARED_MEDIA = "shared_media"
    SIGNAL_CHOICES = [
        (SIGNAL_TEXT_SIMILARITY, "Teks nyaris identik"),
        (SIGNAL_TIME_SYNC, "Sinkronisasi waktu unggah"),
        (SIGNAL_ACCOUNT_AGE, "Akun baru / riwayat minim"),
        (SIGNAL_SHARED_MEDIA, "Aset media bersama"),
    ]

    cluster = models.ForeignKey(CoordinationCluster, on_delete=models.CASCADE, related_name="signals")
    signal_type = models.CharField(max_length=30, choices=SIGNAL_CHOICES)
    score = models.DecimalField(max_digits=3, decimal_places=2)

    def __str__(self):
        return f"{self.cluster.cluster_code} — {self.get_signal_type_display()}"


class DuplicateTextSample(models.Model):
    cluster = models.ForeignKey(CoordinationCluster, on_delete=models.CASCADE, related_name="duplicate_samples")
    account_handle = models.CharField(max_length=150)
    posted_at = models.DateTimeField()
    text = models.TextField()
    highlighted_phrase = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.account_handle} @ {self.posted_at:%H:%M}"
