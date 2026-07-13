from django.utils import timezone

from apps.analytics.models import PoliticalIssue

from .models import ClusterAccount, CoordinationCluster, CoordinationSignal, DuplicateTextSample

CLUSTER_DEFS = [
    {
        "cluster_code": "Klaster-07", "score": "0.91", "status": CoordinationCluster.STATUS_FLAGGED,
        "account_count": 62, "note": "62 akun · isu distribusi pangan · aktif sejak 24 Jun",
        "accounts": [
            ("@suara_timur88", ClusterAccount.ROLE_HUB, 640000, 31),
            ("@nusantara_bgkt", ClusterAccount.ROLE_AMPLIFIER, 120000, 14),
            ("@warga_peduli21", ClusterAccount.ROLE_AMPLIFIER, 98000, 9),
        ],
        "signals": [
            (CoordinationSignal.SIGNAL_TEXT_SIMILARITY, "0.86"),
            (CoordinationSignal.SIGNAL_TIME_SYNC, "0.91"),
            (CoordinationSignal.SIGNAL_ACCOUNT_AGE, "0.62"),
            (CoordinationSignal.SIGNAL_SHARED_MEDIA, "0.74"),
        ],
        "samples": [
            ("@suara_timur88", "Bantuan tak kunjung sampai, rakyat timur kembali jadi penonton. Sampai kapan? #PanganUntukSiapa", "rakyat timur kembali jadi penonton"),
            ("@warga_peduli21", "Bantuan tidak kunjung sampai, rakyat timur kembali jadi penonton!! Sampai kapan #PanganUntukSiapa", "rakyat timur kembali jadi penonton"),
            ("@nusantara_bgkt", "bantuan tak kunjung sampai... rakyat timur kembali jadi penonton — sampai kapan? #PanganUntukSiapa", "rakyat timur kembali jadi penonton"),
        ],
    },
    {
        "cluster_code": "Klaster-09", "score": "0.79", "status": CoordinationCluster.STATUS_FLAGGED,
        "account_count": 28, "note": "28 akun · amplifikasi tagar #GantiSkema · sejak 27 Jun",
        "accounts": [("@gerakmaju_net", ClusterAccount.ROLE_HUB, 296000, 22)],
        "signals": [
            (CoordinationSignal.SIGNAL_TIME_SYNC, "0.79"),
            (CoordinationSignal.SIGNAL_TEXT_SIMILARITY, "0.71"),
        ],
        "samples": [],
    },
    {
        "cluster_code": "Klaster-05", "score": "0.76", "status": CoordinationCluster.STATUS_REVIEWED_ORGANIC,
        "account_count": 19, "note": "Komunitas relawan asli — diputuskan analis 28 Jun (false positive)",
        "accounts": [], "signals": [], "samples": [],
    },
    {
        "cluster_code": "Klaster-03", "score": "0.68", "status": CoordinationCluster.STATUS_IGNORED,
        "account_count": 11, "note": "Jaringan giveaway komersial — tidak relevan dgn isu politik",
        "accounts": [], "signals": [], "samples": [],
    },
]


def seed_coordination():
    if CoordinationCluster.objects.exists():
        return

    issue = PoliticalIssue.objects.filter(title="Distribusi Pangan Wilayah Timur").first()
    if issue is None:
        return

    now = timezone.now()
    for definition in CLUSTER_DEFS:
        cluster = CoordinationCluster.objects.create(
            issue=issue,
            cluster_code=definition["cluster_code"],
            score=definition["score"],
            status=definition["status"],
            account_count=definition["account_count"],
            detected_at=now - timezone.timedelta(days=6),
            note=definition["note"],
        )
        for handle, role, reach, post_count in definition["accounts"]:
            ClusterAccount.objects.create(
                cluster=cluster, handle=handle, role=role, reach=reach, post_count=post_count
            )
        for signal_type, score in definition["signals"]:
            CoordinationSignal.objects.create(cluster=cluster, signal_type=signal_type, score=score)
        for handle, text, phrase in definition["samples"]:
            DuplicateTextSample.objects.create(
                cluster=cluster, account_handle=handle,
                posted_at=now - timezone.timedelta(days=6, minutes=2),
                text=text, highlighted_phrase=phrase,
            )
