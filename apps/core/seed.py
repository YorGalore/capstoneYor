from django.contrib.auth import get_user_model

from .models import AnalystProfile, Platform, Province, Regency, Project, Tenant
from .permissions import seed_permission_matrix

DEMO_USERNAME = "dewi.anjani"
DEMO_PASSWORD = "demo12345"

PLATFORMS = [
    ("x", "X (Twitter)", "#0B1F33", Platform.METHOD_INTERNAL),
    ("instagram", "Instagram", "#DD2A7B", Platform.METHOD_APIFY),
    ("tiktok", "TikTok", "#0B1F33", Platform.METHOD_APIFY),
    ("youtube", "YouTube", "#FF0000", Platform.METHOD_APIFY),
    ("facebook", "Facebook", "#0866FF", Platform.METHOD_APIFY),
    ("berita", "Berita Daring", "#0E7C86", Platform.METHOD_INTERNAL),
    ("forum", "Forum/Blog", "#7C8A99", Platform.METHOD_INTERNAL),
]

PROVINCES = [
    ("DKI Jakarta", 9_000_000),
    ("Jawa Barat", 11_000_000),
    ("Jawa Tengah", 8_500_000),
    ("Jawa Timur", 9_800_000),
    ("Banten", 3_200_000),
    ("Sumatera Utara", 3_600_000),
    ("Sulawesi Selatan", 2_500_000),
    ("Kalimantan Timur", 1_900_000),
    ("Maluku", 420_000),
    ("Papua", 690_000),
    ("Sulawesi Tengah", 780_000),
    ("Nusa Tenggara Timur", 810_000),
]

REGENCIES = {
    "Maluku": ["Kota Ambon", "Maluku Tengah", "Kota Tual", "Buru", "Seram Bagian Barat"],
    "Papua": ["Kota Jayapura", "Jayapura", "Mimika", "Nabire"],
}


def seed_core():
    tenant, _ = Tenant.objects.get_or_create(name="Kemenko PMK")
    project, _ = Project.objects.get_or_create(tenant=tenant, name="Program Pangan Rakyat")

    for slug, display_name, brand_color, method in PLATFORMS:
        Platform.objects.get_or_create(
            slug=slug,
            defaults={"display_name": display_name, "brand_color": brand_color, "method": method},
        )

    for name, population_online in PROVINCES:
        province, _ = Province.objects.get_or_create(
            name=name, defaults={"population_online": population_online}
        )
        for regency_name in REGENCIES.get(name, []):
            Regency.objects.get_or_create(province=province, name=regency_name)

    User = get_user_model()
    demo_user, created = User.objects.get_or_create(
        username=DEMO_USERNAME,
        defaults={"first_name": "Dewi", "last_name": "Anjani", "is_staff": True},
    )
    if created:
        demo_user.set_password(DEMO_PASSWORD)
        demo_user.save()
    AnalystProfile.objects.update_or_create(
        user=demo_user,
        defaults={
            "tenant": tenant,
            "role_label": "Analis Humas",
            # Structured role governs page access (FR-1A). The single demo user is
            # a Platform Super Admin so every screen — including the reserved
            # Dev/Ops runtime settings — is reachable in the demo.
            # Political-monitoring access is NOT granted here: it is a separate,
            # compliance-approved grant recorded in governance (FR-29.1).
            "role": AnalystProfile.ROLE_SUPER_ADMIN,
        },
    )
    seed_permission_matrix()
    return tenant, project
