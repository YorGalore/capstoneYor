from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.models import Platform

from .models import (
    ApifyCredential, AuditLogEntry, MonitoredDomain, MonitoringKeyword, PlatformIntegration,
    PoliticalMonitoringPermission, PolicyAcknowledgment,
)

# feed_url is left blank for sources with no known public RSS feed — the
# console still lists them, but "Jalankan Sekarang" skips them until an
# analyst supplies one.
DOMAINS = [
    ("antaranews.com", "RSS", MonitoredDomain.STATUS_ACTIVE, "https://www.antaranews.com/rss/terkini.xml"),
    ("cnnindonesia.com", "RSS", MonitoredDomain.STATUS_ACTIVE, "https://www.cnnindonesia.com/nasional/rss"),
    ("forum.kaskus.co.id", "adapter khusus", MonitoredDomain.STATUS_NEEDS_REVIEW, ""),
    ("tribunnews.com", "generik-berita", MonitoredDomain.STATUS_INACTIVE, ""),
]

MONITORING_KEYWORDS = ["pangan", "bansos"]

PERMISSION_USERS = [
    ("bagus.prakoso", "Bagus Prakoso"),
    ("siti.rahmawati", "Siti Rahmawati"),
]

AUDIT_ENTRIES = [
    ("D. Anjani", "Ekspor brief perbandingan narasi", "Isu #PGN-118"),
    ("B. Prakoso", "Kueri tren aktor politik", "Koalisi Nusantara Raya"),
    ("Sistem", "Klaster koordinasi ditandai untuk tinjauan", "Klaster-07"),
    ("R. Hartono", "Menyetujui izin Pemantauan Politik", "S. Rahmawati"),
    ("D. Anjani", "Mencatat aksi War Room", "Distribusi Pangan Timur"),
    ("Sistem", "Profil individu dikecualikan dari penandaan aktor otomatis", "@warga_pribadi_01"),
    ("Sistem", "Profil individu dikecualikan dari penandaan aktor otomatis", "@akun_pribadi_44"),
    ("B. Prakoso", "Kueri sebaran regional isu politik", "Maluku"),
    ("S. Rahmawati", "Ekspor log audit", "7 hari terakhir"),
    ("R. Hartono", "Menyetujui izin Pemantauan Politik", "B. Prakoso"),
]

ACTOR_IDS = {
    "instagram": "apify/instagram-scraper",
    "tiktok": "clockworks/tiktok-scraper",
    "youtube": "streamers/youtube-scraper",
    "facebook": "apify/facebook-posts-scraper",
    "x": "scraper internal v2.4.1",
}


def seed_governance(tenant):
    if PlatformIntegration.objects.exists():
        return

    now = timezone.now()
    social_platforms = Platform.objects.exclude(slug__in=["berita", "forum"])
    for platform in social_platforms:
        PlatformIntegration.objects.get_or_create(
            platform=platform,
            defaults={
                "method": platform.method,
                "actor_id": ACTOR_IDS.get(platform.slug, ""),
                "is_active": platform.slug != "facebook",
                "status_note": "deprecation notice" if platform.slug == "facebook" else "",
            },
        )

    ApifyCredential.objects.get_or_create(
        masked_token="apify_••••••••••••••••••3f9a",
        defaults={"last_verified_at": now - timezone.timedelta(hours=2)},
    )

    for domain, adapter, status, feed_url in DOMAINS:
        MonitoredDomain.objects.get_or_create(
            domain=domain,
            defaults={
                "adapter": adapter, "status": status, "feed_url": feed_url,
                "last_tested_at": now - timezone.timedelta(hours=2),
            },
        )

    for keyword in MONITORING_KEYWORDS:
        MonitoringKeyword.objects.get_or_create(keyword=keyword, defaults={"created_by": "Sistem (seed)"})

    User = get_user_model()
    demo_user = User.objects.filter(username="dewi.anjani").first()
    if demo_user is not None:
        PoliticalMonitoringPermission.objects.get_or_create(
            user=demo_user,
            defaults={"approved_by": "R. Hartono (Kepatuhan)", "approved_at": now - timezone.timedelta(days=120)},
        )
    for username, first_name in PERMISSION_USERS:
        user, _ = User.objects.get_or_create(username=username, defaults={"first_name": first_name})
        PoliticalMonitoringPermission.objects.get_or_create(
            user=user,
            defaults={"approved_by": "R. Hartono (Kepatuhan)", "approved_at": now - timezone.timedelta(days=90)},
        )

    for actor_label, action, target in AUDIT_ENTRIES:
        AuditLogEntry.objects.create(actor_label=actor_label, action=action, target=target)

    PolicyAcknowledgment.objects.get_or_create(
        tenant=tenant,
        defaults={
            "approved_by": "Tenant Admin",
            "approved_at": now - timezone.timedelta(days=190),
            "next_review_at": now + timezone.timedelta(days=175),
        },
    )


# Curated regulatory corpus backing the RAG grounding (FR-31.1). Real Indonesian
# regulations relevant to the demo's food-distribution and energy-subsidy issues.
REGULATORY_DOCS = [
    (
        "Permensos No. 1 Tahun 2024 tentang Penyaluran Bantuan Sosial Pangan",
        "Permensos No. 1/2024 Pasal 12",
        "Penyaluran bantuan sosial pangan kepada keluarga penerima manfaat dilakukan "
        "paling lambat 14 hari sejak penetapan daftar penerima. Keterlambatan penyaluran "
        "wajib dilaporkan kepada dinas sosial setempat beserta alasan dan rencana "
        "penyelesaiannya. Pemerintah daerah bertanggung jawab memastikan ketepatan sasaran.",
    ),
    (
        "Perpres No. 91 Tahun 2023 tentang Subsidi Energi Tepat Sasaran",
        "Perpres No. 91/2023 Pasal 4",
        "Subsidi energi diberikan kepada golongan masyarakat yang berhak sesuai basis data "
        "terpadu. Penyesuaian harga bahan bakar minyak bersubsidi ditetapkan oleh menteri "
        "dengan memperhatikan daya beli masyarakat dan kondisi fiskal negara.",
    ),
    (
        "UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi",
        "UU PDP No. 27/2022 Pasal 20",
        "Pengendali data pribadi wajib memiliki dasar pemrosesan yang sah. Pemrosesan data "
        "pribadi harus dilakukan secara terbatas dan spesifik, sah menurut hukum, serta "
        "transparan kepada subjek data.",
    ),
    (
        "SOP Humas: Penanganan Isu Negatif di Media Sosial",
        "SOP Humas No. 5/2025",
        "Klarifikasi resmi atas isu negatif berdampak luas diterbitkan paling lambat 1x24 jam "
        "sejak isu terverifikasi. Setiap pernyataan wajib berbasis data dan tidak menyerang "
        "pihak manapun. Juru bicara adalah satu-satunya kanal pernyataan resmi.",
    ),
]


def seed_regulatory_corpus():
    from .models import RegulatoryDocument

    for title, source_ref, body in REGULATORY_DOCS:
        RegulatoryDocument.objects.get_or_create(
            title=title, defaults={"source_ref": source_ref, "body": body}
        )
