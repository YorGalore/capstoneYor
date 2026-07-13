from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.models import Platform

from .models import (
    ApifyCredential, AuditLogEntry, MonitoredDomain, PlatformIntegration,
    PoliticalMonitoringPermission, PolicyAcknowledgment,
)

DOMAINS = [
    ("kompas.com", "generik-berita", MonitoredDomain.STATUS_ACTIVE),
    ("detik.com", "generik-berita", MonitoredDomain.STATUS_ACTIVE),
    ("forum.kaskus.co.id", "adapter khusus", MonitoredDomain.STATUS_NEEDS_REVIEW),
    ("tribunnews.com", "generik-berita", MonitoredDomain.STATUS_INACTIVE),
]

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

    for domain, adapter, status in DOMAINS:
        MonitoredDomain.objects.get_or_create(
            domain=domain,
            defaults={
                "adapter": adapter, "status": status,
                "last_tested_at": now - timezone.timedelta(hours=2),
            },
        )

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
