"""Contextual, fictional demo fixture for Kabupaten Kulon Progo.

The generic Kemenko PMK fixture is useful for showing the platform at national
scale.  This fixture deliberately lives beside it as a separate tenant so a
government communications team can evaluate the same screens with local names,
programs, sources, and issues.  Every record is deterministic and idempotent;
none of it is presented as live collection data.
"""

import random
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.analytics import briefs, incidents
from apps.analytics.models import (
    ActorSentimentAssessment,
    Alert,
    AlertRule,
    Camp,
    Category,
    Coalition,
    DailyBrief,
    GovernmentProgram,
    Issue,
    IssueLabel,
    Incident,
    Mention,
    PoliticalActor,
    PoliticalIssue,
    SubCategory,
)
from apps.coordination.models import ClusterAccount, CoordinationCluster, CoordinationSignal, DuplicateTextSample
from apps.governance.models import (
    AuditLogEntry,
    MonitoredDomain,
    MonitoringKeyword,
    PlatformIntegration,
    PolicyAcknowledgment,
    PoliticalMonitoringPermission,
)
from apps.governance.apify_crawler import ACTOR_CONFIG
from apps.governance.seed import seed_schedules

from .models import AnalystProfile, Platform, Project, Province, Regency, Tenant


TENANT_NAME = "Kabupaten Kulon Progo"
PROJECT_NAME = "Monitoring Media Pemkab Kulon Progo"
DEMO_USERNAME = "humas.kulonprogo"
DEMO_PASSWORD = "demo12345"


KEYWORDS = [
    "Bupati Kulon Progo",
    "Agung Setyawan",
    "Wakil Bupati Kulon Progo",
    "Ambar Purwoko",
    "Pemkab Kulon Progo",
    "Pemerintah Kabupaten Kulon Progo",
    # Issue/event queries needed to reproduce the 21-27 July analytical report.
    # Location qualifiers keep broad national topics such as MBG from flooding a
    # district-level project with unrelated results.
    "MBG Kulon Progo",
    "Makan Bergizi Gratis Kulon Progo",
    "keracunan MBG Kulon Progo",
    "SMPN 3 Wates",
    "SPPG Karangwuni",
    "BGN Kulon Progo",
    "Dinkes Kulon Progo",
    "DPRD Kulon Progo",
    "Sermo Run 2026",
    "kenakalan pelajar Kulon Progo",
    "BUKP Kulon Progo",
]


DOMAINS = [
    ("jogja.tribunnews.com", "portal-listing", "https://jogja.tribunnews.com/"),
    ("jogjapolitan.harianjogja.com", "portal-sitemap", "https://www.harianjogja.com/sitemap-news-jogjapolitan.xml"),
    ("jogja.antaranews.com", "portal-rss", "https://jogja.antaranews.com/rss/terkini.xml"),
    ("www.prolimannews.id", "portal-rss", "https://www.prolimannews.id/feed/"),
    ("rri.co.id", "portal-rss", "https://rri.co.id/rss"),
    ("jogja.viva.co.id", "portal-listing", "https://jogja.viva.co.id/warta"),
    ("www.detik.com", "portal-listing", "https://www.detik.com/jogja/berita"),
    ("www.purworejo24.com", "portal-rss", "https://www.purworejo24.com/feed/"),
    ("kominfo.kulonprogokab.go.id", "portal-listing", "https://kominfo.kulonprogokab.go.id/publikasi/berita"),
    ("yogyakarta.kompas.com", "portal-listing", "https://yogyakarta.kompas.com/"),
    ("jogja.idntimes.com", "portal-listing", "https://jogja.idntimes.com/"),
    ("radarjogja.jawapos.com", "portal-listing", "https://radarjogja.jawapos.com/kulonprogo/"),
    ("www.bisnis.com", "portal-listing", "https://www.bisnis.com/"),
    ("espos.id", "portal-listing", "https://espos.id/"),
    ("kulonprogokab.go.id", "portal-listing", "https://kulonprogokab.go.id/"),
]

LEGACY_DOMAIN_ALIASES = {"prolimannews.com", "vivajogja.com", "detik.com", "purworejo24.com", "kulonprogokab.go.id"}


PROGRAMS = [
    ("BBGRM 2026", "Dinas PMD Dalduk dan KB", ["bbgrm", "bulan bhakti gotong royong"]),
    ("Kulinerun 2026", "Dinas Pariwisata", ["kulinerun", "sport tourism"]),
    ("Sekolah Rakyat Kulon Progo", "Dinas Pendidikan", ["sekolah rakyat"]),
    ("Pengembangan BUMDes", "Dinas PMD Dalduk dan KB", ["bumdes", "potensi lokal"]),
    ("Ketahanan Pangan", "Dinas Pertanian dan Pangan", ["ketahanan pangan", "penanaman jagung"]),
    ("Makan Bergizi Gratis", "Badan Gizi Nasional", ["makan bergizi gratis", "program mbg", "mbg"]),
    ("Sermo Run 2026", "Dinas Pariwisata", ["sermo run", "sermorun", "sport tourism waduk sermo"]),
    ("Deklarasi Cegah Kenakalan Pelajar", "Pemkab Kulon Progo", ["cegah kenakalan pelajar", "kejahatan jalanan", "deklarasi pelajar"]),
]


# The 14 editorially curated news examples mirror the structure of the supplied
# 19-25 May report: 7 positive, 4 neutral, 3 negative.  Dates are placed in the
# most recent seven days so the existing rolling dashboard immediately shows them.
NEWS_ITEMS = [
    # title, outlet, subject, sentiment, issue key, program name, days ago
    ("PMI Kulon Progo Bersiap Gelar Muskab, Bupati: Cari Pemimpin yang Hangayomi", "Proliman News", "Bupati Agung", "positive", "program", "", 6),
    ("BBGRM Kulon Progo 2026 Tuntas, Swadaya Warga Tembus Rp16,6 Miliar", "Harian Jogja", "Bupati Agung", "positive", "program", "BBGRM 2026", 5),
    ("Kulinerun 2026 Kulon Progo Diikuti Lebih dari 1.000 Peserta", "Tribun Jogja", "Bupati Agung", "positive", "program", "Kulinerun 2026", 4),
    ("Ambar Purwoko Masuk Tiga Besar Tokoh Muda Berprestasi", "Purworejo24.com", "Wabup Ambar", "positive", "program", "", 4),
    ("Pemkab Kulon Progo Dorong Pengembangan BUMDes Berbasis Potensi Lokal", "Proliman News", "Pemkab", "positive", "program", "Pengembangan BUMDes", 3),
    ("Polres Kulon Progo dan Pemda Berkolaborasi Dukung Ketahanan Pangan", "Antara Yogyakarta", "Pemkab", "positive", "program", "Ketahanan Pangan", 2),
    ("Sekolah Rakyat Kulon Progo Progres Pembangunan Sesuai Target", "Harian Jogja", "Wabup Ambar", "positive", "program", "Sekolah Rakyat Kulon Progo", 1),
    ("Bupati Agung Setyawan Hadiri Upacara Peringatan Hari Kebangkitan Nasional", "Kominfo Kulon Progo", "Bupati Agung", "neutral", "agenda", "", 6),
    ("Muskab PMI Kulon Progo Digelar untuk Memilih Pengurus Baru", "Proliman News", "Pemkab", "neutral", "agenda", "", 5),
    ("Pemkab Kulon Progo Finalisasi Program Pembangunan Semester II", "Kominfo Kulon Progo", "Pemkab", "neutral", "agenda", "", 3),
    ("Wabup Ambar Purwoko Pimpin Rapat Koordinasi Lintas Sektor Pendidikan", "Kominfo Kulon Progo", "Wabup Ambar", "neutral", "agenda", "", 1),
    ("Dugaan Pungli Lurah Garongan Masih Didalami, Warga Desak Penuntasan", "Harian Jogja", "Pemkab", "negative", "integrity", "", 1),
    ("Warga Garongan Meminta Ketegasan Bupati dalam Penanganan Dugaan Pungli", "Proliman News", "Bupati Agung", "negative", "integrity", "", 0),
    ("Pelabuhan Adikarto Masih Mangkrak dan Kembali Disorot Warga", "Tribun Jogja", "Bupati dan Wabup", "negative", "infrastructure", "", 2),
    # Extended window (8-30 hari lalu) so the 30-day sentiment trend has a full
    # month of movement instead of a single-week spike, for demo purposes.
    ("Bupati Agung Resmikan Pasar Rakyat Wates Usai Direvitalisasi", "Antara Yogyakarta", "Bupati Agung", "positive", "program", "", 10),
    ("BUMDes Kulon Progo Sukses Ekspor Gula Semut ke Pasar Eropa", "Harian Jogja", "Pemkab", "positive", "program", "Pengembangan BUMDes", 9),
    ("Wabup Ambar Luncurkan Beasiswa Pendidikan Vokasi untuk Pelajar Kurang Mampu", "Kominfo Kulon Progo", "Wabup Ambar", "positive", "program", "Sekolah Rakyat Kulon Progo", 15),
    ("Panen Raya Jagung di Kokap Catat Hasil Terbaik dalam Lima Tahun", "Tribun Jogja", "Pemkab", "positive", "program", "Ketahanan Pangan", 18),
    ("Pemkab Kulon Progo Raih Predikat WTP dari BPK Tahun Kelima Berturut", "Antara Yogyakarta", "Bupati Agung", "positive", "program", "", 22),
    ("Festival Layang-Layang Internasional Kulon Progo Diapresiasi Wisatawan", "Proliman News", "Pemkab", "positive", "program", "Kulinerun 2026", 27),
    ("Bupati dan Wabup Tinjau Kesiapan Posyandu Digital di Kapanewon Pengasih", "Kominfo Kulon Progo", "Bupati dan Wabup", "neutral", "agenda", "", 8),
    ("Pemkab Gelar Rapat Evaluasi Serapan Anggaran Triwulan II", "Kominfo Kulon Progo", "Pemkab", "neutral", "agenda", "", 14),
    ("Dinas Pertanian Sosialisasikan Kalender Tanam ke Petani Kokap", "Harian Jogja", "Pemkab", "neutral", "agenda", "Ketahanan Pangan", 20),
    ("Proyek Jalan Lingkar Selatan Molor dari Jadwal, Warga Pertanyakan Progres", "Tribun Jogja", "Pemkab", "negative", "infrastructure", "", 12),
    ("Keluhan Layanan Adminduk di Kapanewon Sentolo Ramai Dikeluhkan Warga", "Proliman News", "Pemkab", "negative", "integrity", "", 17),
    ("DPRD Soroti Minimnya Transparansi Anggaran Perbaikan Pelabuhan Adikarto", "Harian Jogja", "Bupati dan Wabup", "negative", "infrastructure", "", 25),
]


# Social buzz: a larger, randomized-but-deterministic layer of posts across every
# non-berita platform so the demo's charts (platform mix, 30-day trend, regional
# reach) are not built from 26 curated rows alone. Seeded with a fixed RNG so the
# fixture stays reproducible and idempotent across re-seeds.
SOCIAL_BUZZ_SEED = 20260717
SOCIAL_BUZZ_COUNT = 220

# Narrative comparison: two symmetric, fictional perspectives plus a small
# unattributed pool. These records power /narasi/ for the Kulon Progo tenant.
NARRATIVE_SEED = 20260724
NARRATIVE_UNATTRIBUTED_COUNT = 12
NARRATIVE_PERSPECTIVES = [
    {
        "slug": "kulon-progo-penanganan",
        "name": "Narasi Penanganan & Klarifikasi",
        "actor_name": "Pemerintah Kabupaten Kulon Progo",
        "stance": Coalition.STANCE_PETAHANA,
        "color": "#0E7C86",
        "count": 48,
        "sentiments": [
            (Mention.SENTIMENT_POSITIVE, 0.46),
            (Mention.SENTIMENT_NEUTRAL, 0.42),
            (Mention.SENTIMENT_NEGATIVE, 0.12),
        ],
        "themes": [
            ("proses pemeriksaan berjalan", 0.34),
            ("komitmen keterbukaan hasil", 0.27),
            ("koordinasi Inspektorat", 0.22),
            ("kanal aduan resmi", 0.17),
        ],
        "snippets": [
            "Pemkab menyampaikan pemeriksaan dugaan pungli Garongan sedang berjalan dan hasilnya akan diumumkan setelah verifikasi.",
            "Inspektorat diminta menelusuri laporan warga secara objektif serta menjaga kerahasiaan pelapor.",
            "Warga diimbau menyampaikan bukti melalui kanal aduan resmi agar setiap laporan dapat ditindaklanjuti.",
            "Koordinasi dengan pemerintah kalurahan dilakukan untuk memastikan layanan publik tetap berjalan selama pemeriksaan.",
            "Keterbukaan hasil pemeriksaan diperlukan agar warga memperoleh informasi yang jelas dan terverifikasi.",
        ],
    },
    {
        "slug": "kulon-progo-akuntabilitas",
        "name": "Narasi Kritik & Akuntabilitas",
        "actor_name": "DPRD Kulon Progo",
        "stance": Coalition.STANCE_PENANTANG,
        "color": "#B2601F",
        "count": 36,
        "sentiments": [
            (Mention.SENTIMENT_POSITIVE, 0.08),
            (Mention.SENTIMENT_NEUTRAL, 0.31),
            (Mention.SENTIMENT_NEGATIVE, 0.61),
        ],
        "themes": [
            ("desakan penyelesaian", 0.36),
            ("keterbukaan hasil pemeriksaan", 0.28),
            ("perlindungan pelapor", 0.21),
            ("pengawasan layanan kalurahan", 0.15),
        ],
        "snippets": [
            "DPRD Kulon Progo meminta pemeriksaan dugaan pungli Garongan segera dituntaskan dengan tenggat yang jelas.",
            "DPRD Kulon Progo meminta hasil pemeriksaan dibuka agar proses penanganan dapat diawasi bersama.",
            "DPRD Kulon Progo menekankan perlindungan pelapor dan saksi agar warga tidak takut menyampaikan bukti.",
            "DPRD Kulon Progo mendorong pengawasan layanan kalurahan diperkuat agar keluhan serupa tidak berulang.",
            "DPRD Kulon Progo meminta penjelasan tahapan pemeriksaan dan tindak lanjut yang sudah dilakukan.",
        ],
    },
]

# Citizen-service complaints sized to exercise the Incident board.
#
# The social-buzz layer above sets only a free-text ``theme`` and creates no
# IssueLabel, so incident detection — which clusters on (taxonomy Issue x Regency)
# — cannot see any of it. Without this layer the demo board is empty, which
# demonstrates nothing.
#
# Volumes and sentiment splits are chosen to land on three different severity
# tiers, so the board shows real triage rather than a single flat list:
#   * jalan  — 22 mentions, 86% negative → above the from-zero surge floor → Kritis
#   * air    —  9 mentions, 78% negative → below the surge floor        → Tinggi
#   * sampah —  7 mentions, 57% negative → below the surge floor        → Sedang
INCIDENT_CLUSTER_SEED = 20260720
INCIDENT_CLUSTERS = [
    {
        "key": "jalan",
        "subcategory": "Infrastruktur Jalan",
        "issue": "Jalan Rusak Wates–Sentolo",
        "keywords": ["jalan rusak", "berlubang", "wates", "sentolo"],
        "total": 22,
        "negative": 19,
        "negative_snippets": [
            "jalan wates-sentolo makin parah, lubangnya dalam sekali",
            "sudah tiga motor jatuh di lubang depan pasar sentolo",
            "tolong pak bupati jalan ini diperbaiki, tiap hari macet",
            "lubang di jalan wates bikin bahaya kalau malam, tidak ada lampu",
            "drainase mampet jadi jalan cepat rusak lagi setelah ditambal",
        ],
        "other_snippets": [
            "katanya minggu depan mulai ditambal, semoga benar",
            "ada alat berat masuk di ruas sentolo pagi ini",
        ],
    },
    {
        "key": "air",
        "subcategory": "Air Bersih",
        "issue": "Air PDAM Mati Berhari-hari",
        "keywords": ["pdam", "air mati", "air bersih"],
        "total": 9,
        "negative": 7,
        "negative_snippets": [
            "air pdam mati sudah tiga hari, tidak ada pemberitahuan",
            "beli air galon terus jadi boros, tolong segera diperbaiki",
            "giliran air tidak jelas jadwalnya di daerah kami",
        ],
        "other_snippets": [
            "info dari pdam katanya ada perbaikan pipa induk",
        ],
    },
    {
        "key": "sampah",
        "subcategory": "Persampahan",
        "issue": "Sampah Menumpuk di Pasar",
        "keywords": ["sampah", "tps", "bau"],
        "total": 7,
        "negative": 4,
        "negative_snippets": [
            "sampah di tps pasar sudah seminggu tidak diangkut, bau sekali",
            "tumpukan sampah meluber sampai bahu jalan",
        ],
        "other_snippets": [
            "truk sampah tadi pagi sudah datang, semoga rutin",
            "warga swadaya bersih-bersih tps kemarin sore",
        ],
    },
]

SOCIAL_PLATFORM_WEIGHTS = {
    "x": 0.30, "instagram": 0.24, "tiktok": 0.22, "facebook": 0.14, "youtube": 0.06, "forum": 0.04,
}

SOCIAL_SENTIMENT_WEIGHTS = [
    (Mention.SENTIMENT_POSITIVE, 0.52),
    (Mention.SENTIMENT_NEUTRAL, 0.31),
    (Mention.SENTIMENT_NEGATIVE, 0.17),
]

SOCIAL_HANDLES = [
    "@wargakulonprogo", "@infowates", "@pojokmenoreh", "@suarabinangun",
    "@kulonprogohits", "@petanimenoreh", "@relawankp", "@komunitaskp",
    "@pantaupublikkp", "@anakwates", "@jogoworo_kp", "@binangunmuda",
]

SOCIAL_SNIPPETS = {
    Mention.SENTIMENT_POSITIVE: [
        "Bangga lihat progres pembangunan di Kulon Progo makin nyata.",
        "Terima kasih Pemkab, layanan makin cepat dan transparan.",
        "Program BUMDes bener-bener bantu ekonomi desa kami.",
        "Salut sama kinerja Bupati dan jajaran, semoga terus konsisten.",
        "Festival dan agenda pariwisata Kulon Progo makin ramai wisatawan.",
    ],
    Mention.SENTIMENT_NEUTRAL: [
        "Ada yang tahu jadwal lengkap agenda Pemkab minggu ini?",
        "Info tentang program ini masih simpang siur di warga.",
        "Menunggu update resmi dari Kominfo Kulon Progo soal ini.",
        "Rapat koordinasi hari ini dihadiri beberapa dinas terkait.",
        "Ada yang sudah coba layanan baru di kapanewon setempat?",
    ],
    Mention.SENTIMENT_NEGATIVE: [
        "Kapan urusan pungli di Garongan ini benar-benar dituntaskan?",
        "Pelabuhan Adikarto masih mangkrak, kapan ditindaklanjuti?",
        "Pelayanan di kantor kapanewon masih lambat, tolong dievaluasi.",
        "Warga masih menunggu kejelasan soal proyek yang molor ini.",
        "Kok belum ada tindak lanjut jelas soal keluhan warga kemarin?",
    ],
}


def _weighted_choice(rng, weighted_options):
    total = sum(weight for _, weight in weighted_options)
    pick = rng.uniform(0, total)
    upto = 0
    for option, weight in weighted_options:
        upto += weight
        if pick <= upto:
            return option
    return weighted_options[-1][0]


def _seed_identity():
    tenant, _ = Tenant.objects.get_or_create(name=TENANT_NAME)
    project, _ = Project.objects.get_or_create(tenant=tenant, name=PROJECT_NAME)

    province, _ = Province.objects.get_or_create(
        name="DI Yogyakarta", defaults={"population_online": 2_800_000}
    )
    regency, _ = Regency.objects.get_or_create(province=province, name="Kulon Progo")

    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=DEMO_USERNAME,
        defaults={
            "first_name": "Analis",
            "last_name": "Humas Kulon Progo",
            "is_staff": True,
        },
    )
    if created:
        user.set_password(DEMO_PASSWORD)
        user.save()
    AnalystProfile.objects.update_or_create(
        user=user,
        defaults={
            "tenant": tenant,
            "role_label": "Analis Humas Pemkab Kulon Progo",
            "role": AnalystProfile.ROLE_TENANT_ADMIN,
        },
    )
    return tenant, project, province, regency, user


def _seed_governance(tenant, project, user):
    # Earlier demo revisions used brand-like hostnames that do not resolve to the
    # publishers' live portals. They are fixture-owned, so replace them on reseed.
    MonitoredDomain.objects.filter(project=project, domain__in=LEGACY_DOMAIN_ALIASES).delete()
    for platform in Platform.objects.exclude(slug__in=["berita", "forum"]):
        actor_config = ACTOR_CONFIG.get(platform.slug, {})
        PlatformIntegration.objects.update_or_create(
            project=project,
            platform=platform,
            defaults={
                "method": platform.method,
                "actor_id": actor_config.get("actor_id", ""),
                "is_active": True,
                "status_note": "",
            },
        )

    for domain, adapter, feed_url in DOMAINS:
        MonitoredDomain.objects.update_or_create(
            project=project,
            domain=domain,
            defaults={
                "adapter": adapter,
                "status": (
                    MonitoredDomain.STATUS_ACTIVE
                    if feed_url
                    else MonitoredDomain.STATUS_NEEDS_REVIEW
                ),
                "feed_url": feed_url,
            },
        )

    for keyword in KEYWORDS:
        MonitoringKeyword.objects.get_or_create(
            project=project,
            keyword=keyword,
            defaults={"created_by": "Sistem (demo Kulon Progo)"},
        )

    now = timezone.now()
    PoliticalMonitoringPermission.objects.get_or_create(
        user=user,
        defaults={
            "approved_by": "Sekretaris Daerah (demo)",
            "approved_at": now - timezone.timedelta(days=30),
        },
    )
    PolicyAcknowledgment.objects.get_or_create(
        tenant=tenant,
        defaults={
            "approved_by": "Tenant Admin Kulon Progo (demo)",
            "approved_at": now - timezone.timedelta(days=30),
            "next_review_at": now + timezone.timedelta(days=335),
        },
    )
    for action, target in [
        ("Membuat konfigurasi pemantauan Kabupaten Kulon Progo", PROJECT_NAME),
        ("Meninjau koreksi sentimen pemberitaan lokal", "Dugaan pungli Garongan"),
        ("Membuat draf brief pimpinan", "Isu pelayanan publik"),
    ]:
        AuditLogEntry.objects.get_or_create(
            actor_label="Analis Humas Kulon Progo (demo)", action=action, target=target
        )

    seed_schedules(project)


def _seed_taxonomy():
    category, _ = Category.objects.get_or_create(name="Pemerintahan Daerah")
    definitions = {
        "program": ("Program dan Prestasi", "Program Unggulan Pemkab", ["bbgrm", "kulinerun", "sekolah rakyat", "bumdes"]),
        "agenda": ("Agenda Kelembagaan", "Agenda Pemerintahan", ["upacara", "rapat koordinasi", "muskab"]),
        "integrity": ("Integritas Pelayanan Publik", "Dugaan Pungli Garongan", ["pungli", "garongan"]),
        "infrastructure": ("Infrastruktur Strategis", "Pelabuhan Adikarto", ["adikarto", "pelabuhan"]),
    }
    issues = {}
    for key, (sub_name, issue_name, keywords) in definitions.items():
        subcategory, _ = SubCategory.objects.get_or_create(category=category, name=sub_name)
        issue, _ = Issue.objects.get_or_create(
            subcategory=subcategory,
            name=issue_name,
            defaults={"keywords": keywords},
        )
        issues[key] = issue

    health, _ = Category.objects.get_or_create(name="Kesehatan dan Keamanan Pangan")
    health_sub, _ = SubCategory.objects.get_or_create(
        category=health, name="Makan Bergizi Gratis"
    )
    Issue.objects.get_or_create(
        subcategory=health_sub,
        name="Dugaan Keracunan MBG SMPN 3 Wates",
        defaults={"keywords": [
            "keracunan mbg", "smpn 3 wates", "sppg karangwuni",
            "mual muntah mbg", "klb mbg", "uji laboratorium mbg",
        ]},
    )

    public_agenda, _ = Category.objects.get_or_create(name="Agenda Publik dan Reputasi")
    youth_sub, _ = SubCategory.objects.get_or_create(
        category=public_agenda, name="Kepemudaan"
    )
    Issue.objects.get_or_create(
        subcategory=youth_sub,
        name="Deklarasi Cegah Kenakalan Pelajar",
        defaults={"keywords": [
            "cegah kenakalan pelajar", "kejahatan jalanan", "deklarasi pelajar",
        ]},
    )
    tourism_sub, _ = SubCategory.objects.get_or_create(
        category=public_agenda, name="Pariwisata dan Olahraga"
    )
    Issue.objects.get_or_create(
        subcategory=tourism_sub,
        name="Sermo Run 2026",
        defaults={"keywords": ["sermo run", "sermorun", "sport tourism waduk sermo"]},
    )

    economy, _ = Category.objects.get_or_create(name="Ekonomi Daerah")
    finance_sub, _ = SubCategory.objects.get_or_create(
        category=economy, name="Lembaga Keuangan Daerah"
    )
    Issue.objects.get_or_create(
        subcategory=finance_sub,
        name="Kepastian Dana Nasabah BUKP",
        defaults={"keywords": ["bukp", "dana nasabah bukp", "simpanan nasabah bukp"]},
    )
    return issues


def _seed_entities(project):
    actors = {}
    for name, actor_type, keywords, handles in [
        ("Agung Setyawan", PoliticalActor.TYPE_OFFICIAL, ["agung setyawan", "bupati kulon progo"], []),
        ("Ambar Purwoko", PoliticalActor.TYPE_OFFICIAL, ["ambar purwoko", "wakil bupati kulon progo"], []),
        ("Pemerintah Kabupaten Kulon Progo", PoliticalActor.TYPE_ORGANIZATION, ["pemkab kulon progo", "pemerintah kabupaten kulon progo"], ["@pemkabkulonprogo"]),
        ("Badan Gizi Nasional", PoliticalActor.TYPE_ORGANIZATION, ["badan gizi nasional", "bgn"], []),
        ("DPRD Kulon Progo", PoliticalActor.TYPE_ORGANIZATION, ["dprd kulon progo", "ketua dprd kulon progo"], []),
        ("Dinas Kesehatan Kulon Progo", PoliticalActor.TYPE_ORGANIZATION, ["dinkes kulon progo", "dinas kesehatan kulon progo"], []),
        ("SPPG Karangwuni", PoliticalActor.TYPE_ORGANIZATION, ["sppg karangwuni", "dapur mbg karangwuni"], []),
    ]:
        actor, _ = PoliticalActor.objects.get_or_create(
            project=project,
            name=name,
            defaults={
                "actor_type": actor_type,
                "keywords": keywords,
                "handles": handles,
            },
        )
        actors[name] = actor

    programs = {}
    for name, agency, keywords in PROGRAMS:
        program, _ = GovernmentProgram.objects.get_or_create(
            project=project,
            name=name,
            defaults={"agency": agency, "keywords": keywords},
        )
        programs[name] = program
    return actors, programs


def _seed_opds(project):
    """OPD the incident board can assign work to. Idempotent: the demo seed is
    re-run routinely and must not duplicate rows."""
    from apps.analytics.models import OPD

    for slug, name, abbr in [
        ("pu", "Dinas Pekerjaan Umum dan Perumahan Rakyat", "PU"),
        ("dlh", "Dinas Lingkungan Hidup", "DLH"),
        ("dishub", "Dinas Perhubungan", "Dishub"),
        ("dinkes", "Dinas Kesehatan", "Dinkes"),
    ]:
        OPD.objects.get_or_create(
            project=project, slug=slug, defaults={"name": name, "abbr": abbr}
        )


def _posted_at(days_ago, index):
    if days_ago == 0:
        return timezone.now() - timezone.timedelta(minutes=25)
    local_day = timezone.localdate() - timezone.timedelta(days=days_ago)
    local_time = time(hour=8 + (index % 8), minute=(index * 7) % 60)
    return timezone.make_aware(
        datetime.combine(local_day, local_time), timezone.get_current_timezone()
    )


def _seed_mentions(project, province, regency, issues, programs, actors):
    news_platform = Platform.objects.get(slug="berita")
    emotion_by_sentiment = {
        Mention.SENTIMENT_POSITIVE: Mention.EMOTION_JOY,
        Mention.SENTIMENT_NEUTRAL: Mention.EMOTION_TRUST,
        Mention.SENTIMENT_NEGATIVE: Mention.EMOTION_ANGER,
    }

    mentions = []
    for index, (title, outlet, subject, sentiment, issue_key, program_name, days_ago) in enumerate(NEWS_ITEMS, start=1):
        mention, _ = Mention.objects.get_or_create(
            external_id=f"demo-kulon-progo-news-{index:02d}",
            defaults={
                "project": project,
                "platform": news_platform,
                "province": province,
                "regency": regency,
                "author_handle": outlet,
                "content_snippet": f"{title}. Subyek pemantauan: {subject}.",
                "theme": issues[issue_key].name,
                "sentiment": sentiment,
                "sentiment_confidence": 1.0,
                "sentiment_model": "demo-curated-v1",
                "emotion": emotion_by_sentiment[sentiment],
                "emotion_labels": [emotion_by_sentiment[sentiment]],
                "posted_at": _posted_at(days_ago, index),
                "engagement_count": 80 + (index * 37),
                "reach_estimate": 1_500 + (index * 850),
                "matched_keyword": subject,
                "is_scraped": False,
                "program": programs.get(program_name),
            },
        )
        IssueLabel.objects.get_or_create(
            mention=mention,
            defaults={
                "issue": issues[issue_key],
                "source": IssueLabel.SOURCE_MANUAL,
                "decided_by": "Kurasi demo",
            },
        )
        matched_actors = [actors["Pemerintah Kabupaten Kulon Progo"]]
        if "Agung" in subject or subject == "Bupati dan Wabup":
            matched_actors.append(actors["Agung Setyawan"])
        if "Ambar" in subject or subject == "Bupati dan Wabup":
            matched_actors.append(actors["Ambar Purwoko"])
        mention.political_actors.add(*matched_actors)
        mentions.append(mention)
    return mentions


def _seed_social_buzz(project, province, regency, issues, programs):
    # Guard on the model marker rather than count: re-seeding must add nothing once
    # this layer exists, same idempotency contract as the rest of the fixture.
    if Mention.objects.filter(project=project, sentiment_model="demo-social-v1").exists():
        return

    platforms = {p.slug: p for p in Platform.objects.exclude(slug="berita")}
    program_list = list(programs.values())
    theme_by_sentiment = {
        Mention.SENTIMENT_POSITIVE: issues["program"].name,
        Mention.SENTIMENT_NEUTRAL: issues["agenda"].name,
        Mention.SENTIMENT_NEGATIVE: None,  # chosen per-post below (integrity/infra)
    }
    emotion_by_sentiment = {
        Mention.SENTIMENT_POSITIVE: Mention.EMOTION_JOY,
        Mention.SENTIMENT_NEUTRAL: Mention.EMOTION_TRUST,
        Mention.SENTIMENT_NEGATIVE: Mention.EMOTION_ANGER,
    }
    rng = random.Random(SOCIAL_BUZZ_SEED)
    now = timezone.now()

    mentions = []
    for i in range(SOCIAL_BUZZ_COUNT):
        platform_slug = _weighted_choice(rng, list(SOCIAL_PLATFORM_WEIGHTS.items()))
        sentiment = _weighted_choice(rng, SOCIAL_SENTIMENT_WEIGHTS)
        theme = theme_by_sentiment[sentiment] or rng.choice(
            [issues["integrity"].name, issues["infrastructure"].name]
        )
        mentions.append(Mention(
            project=project,
            platform=platforms[platform_slug],
            province=province,
            regency=regency,
            author_handle=rng.choice(SOCIAL_HANDLES),
            content_snippet=rng.choice(SOCIAL_SNIPPETS[sentiment]),
            theme=theme,
            sentiment=sentiment,
            sentiment_confidence=round(rng.uniform(0.68, 0.97), 2),
            sentiment_model="demo-social-v1",
            emotion=emotion_by_sentiment[sentiment],
            emotion_labels=[emotion_by_sentiment[sentiment]],
            posted_at=now - timedelta(days=rng.uniform(0, 30), hours=rng.uniform(0, 24)),
            engagement_count=rng.randint(3, 850),
            reach_estimate=rng.randint(150, 60_000),
            matched_keyword=rng.choice(KEYWORDS),
            is_scraped=False,
            program=rng.choice(program_list) if rng.random() < 0.4 else None,
        ))
    Mention.objects.bulk_create(mentions)


def _seed_incident_clusters(project, province, regency):
    """Seed labeled citizen-service complaints so the Incident board has something
    to detect.

    Unlike ``_seed_social_buzz``, every mention here carries an ``IssueLabel``:
    incident detection clusters on (taxonomy Issue x Regency) and is blind to the
    free-text ``theme`` field the buzz layer uses.
    """
    # Guard on the model marker, matching the idempotency contract of the layers
    # above: re-seeding must add nothing once this layer exists.
    if Mention.objects.filter(project=project, sentiment_model="demo-incident-v1").exists():
        return

    category, _ = Category.objects.get_or_create(name="Layanan Publik")
    platforms = list(Platform.objects.exclude(slug="berita"))
    rng = random.Random(INCIDENT_CLUSTER_SEED)
    now = timezone.now()

    for cluster in INCIDENT_CLUSTERS:
        subcategory, _ = SubCategory.objects.get_or_create(
            category=category, name=cluster["subcategory"]
        )
        issue, _ = Issue.objects.get_or_create(
            subcategory=subcategory,
            name=cluster["issue"],
            defaults={"keywords": cluster["keywords"]},
        )

        for index in range(cluster["total"]):
            is_negative = index < cluster["negative"]
            if is_negative:
                sentiment = Mention.SENTIMENT_NEGATIVE
                emotion = Mention.EMOTION_ANGER
                snippet = cluster["negative_snippets"][index % len(cluster["negative_snippets"])]
            else:
                sentiment = Mention.SENTIMENT_NEUTRAL
                emotion = Mention.EMOTION_TRUST
                offset = index - cluster["negative"]
                snippet = cluster["other_snippets"][offset % len(cluster["other_snippets"])]

            mention = Mention.objects.create(
                project=project,
                platform=rng.choice(platforms),
                province=province,
                regency=regency,
                author_handle=rng.choice(SOCIAL_HANDLES),
                content_snippet=snippet,
                theme=issue.name,
                sentiment=sentiment,
                sentiment_confidence=round(rng.uniform(0.72, 0.96), 2),
                sentiment_model="demo-incident-v1",
                emotion=emotion,
                emotion_labels=[emotion],
                # Inside the board's default 7-day window, so the demo shows
                # candidates without the operator changing the filter first.
                posted_at=now - timedelta(days=rng.uniform(0, 5), hours=rng.uniform(0, 24)),
                engagement_count=rng.randint(5, 900),
                reach_estimate=rng.randint(200, 45_000),
                matched_keyword=cluster["keywords"][0],
                is_scraped=False,
            )
            IssueLabel.objects.create(
                mention=mention,
                issue=issue,
                source=IssueLabel.SOURCE_AUTO,
            )


def _seed_incident_board(project):
    """Materialize demo candidates and attach the generated evidence simulation."""
    incidents.refresh_candidates(project)
    Incident.objects.filter(
        project=project, issue__name="Jalan Rusak Wates–Sentolo"
    ).update(
        evidence_image_path=(
            "analytics/img/incidents/"
            "jalan-rusak-wates-sentolo-simulasi-ai.webp"
        ),
        evidence_caption=(
            "Visualisasi kondisi jalan berlubang berdasarkan pola keluhan "
            "warga dalam data demonstrasi."
        ),
        evidence_is_simulated=True,
    )


def _seed_coordination_cluster(project):
    # A local CIB-detection example tied to the Garongan issue, so the coordination
    # screen has something concrete to show in a Kulon Progo-specific demo rather
    # than only the national fixture's clusters.
    if CoordinationCluster.objects.filter(issue__project=project).exists():
        return
    issue = PoliticalIssue.objects.filter(project=project, title="Dugaan Pungli Lurah Garongan").first()
    if issue is None:
        return

    now = timezone.now()
    cluster = CoordinationCluster.objects.create(
        issue=issue,
        cluster_code="Klaster-KP-01",
        score="0.83",
        status=CoordinationCluster.STATUS_FLAGGED,
        account_count=17,
        detected_at=now - timezone.timedelta(days=1, hours=6),
        note="17 akun · amplifikasi isu dugaan pungli Garongan · aktif sejak kemarin",
    )
    for handle, role, reach, post_count in [
        ("@suarabinangun", ClusterAccount.ROLE_HUB, 41_000, 12),
        ("@jogoworo_kp", ClusterAccount.ROLE_AMPLIFIER, 9_800, 7),
        ("@pantaupublikkp", ClusterAccount.ROLE_AMPLIFIER, 6_200, 5),
    ]:
        ClusterAccount.objects.create(cluster=cluster, handle=handle, role=role, reach=reach, post_count=post_count)
    for signal_type, score in [
        (CoordinationSignal.SIGNAL_TEXT_SIMILARITY, "0.88"),
        (CoordinationSignal.SIGNAL_TIME_SYNC, "0.81"),
        (CoordinationSignal.SIGNAL_ACCOUNT_AGE, "0.55"),
    ]:
        CoordinationSignal.objects.create(cluster=cluster, signal_type=signal_type, score=score)
    for handle, text, phrase in [
        ("@suarabinangun", "Pungli Garongan belum juga dituntaskan, warga menunggu ketegasan Pemkab!", "belum juga dituntaskan"),
        ("@jogoworo_kp", "Kasus pungli Garongan belum juga dituntaskan... warga menunggu ketegasan Pemkab", "belum juga dituntaskan"),
        ("@pantaupublikkp", "pungli di garongan belum juga dituntaskan, warga menunggu ketegasan pemkab", "belum juga dituntaskan"),
    ]:
        DuplicateTextSample.objects.create(
            cluster=cluster, account_handle=handle,
            posted_at=now - timezone.timedelta(days=1, hours=5, minutes=40),
            text=text, highlighted_phrase=phrase,
        )


def _seed_issue_and_alerts(project, mentions):
    now = timezone.now()
    live_issue, _ = PoliticalIssue.objects.get_or_create(
        project=project,
        title="Dugaan Pungli Lurah Garongan",
        defaults={
            "status": PoliticalIssue.STATUS_ACTIVE,
            "opened_at": now - timezone.timedelta(days=7),
            "owner_label": "Tim Humas dan Inspektorat Daerah",
        },
    )
    for mention in mentions:
        if "Pungli" in mention.content_snippet or "pungli" in mention.content_snippet:
            if mention.issue_id != live_issue.id:
                mention.issue = live_issue
                mention.save(update_fields=["issue"])

    rule, _ = AlertRule.objects.get_or_create(
        project=project,
        name="Rasio negatif isu pelayanan publik",
        defaults={
            "condition_summary": "Sentimen negatif >20% dalam tujuh hari",
            "channel": AlertRule.CHANNEL_PUSH,
            "condition_type": AlertRule.CONDITION_NEGATIVE_RATIO,
            "threshold": 0.20,
            "window_minutes": 10_080,
        },
    )
    Alert.objects.get_or_create(
        project=project,
        title="Isu dugaan pungli Garongan perlu respons terkoordinasi",
        defaults={
            "rule": rule,
            "issue": live_issue,
            "severity": Alert.SEVERITY_WARNING,
            "detail": "Dua pemberitaan negatif meminta ketegasan dan transparansi penanganan.",
            "triggered_at": now - timezone.timedelta(minutes=20),
            "status": Alert.STATUS_ACTIVE,
        },
    )
    return live_issue


def _seed_narrative_mentions(project, province, regency, issue):
    """Populate a balanced, explicitly fictional comparison for /narasi/.

    The fake fixture must not expose fake external links. Its provenance is
    carried by ``sentiment_model`` and ``external_id`` instead.
    """
    rng = random.Random(NARRATIVE_SEED)
    now = timezone.now()
    platforms = list(Platform.objects.exclude(slug="berita"))
    emotion_by_sentiment = {
        Mention.SENTIMENT_POSITIVE: Mention.EMOTION_TRUST,
        Mention.SENTIMENT_NEUTRAL: Mention.EMOTION_ANTICIPATION,
        Mention.SENTIMENT_NEGATIVE: Mention.EMOTION_ANGER,
    }
    narrative_mentions = []
    configured_perspectives = []

    for perspective in NARRATIVE_PERSPECTIVES:
        coalition, _ = Coalition.objects.update_or_create(
            slug=perspective["slug"],
            defaults={
                "name": perspective["name"],
                "stance": perspective["stance"],
                "color": perspective["color"],
            },
        )
        camp, _ = Camp.objects.update_or_create(
            project=project,
            name=perspective["name"],
            defaults={"color": perspective["color"]},
        )
        actor = PoliticalActor.objects.get(
            project=project, name=perspective["actor_name"]
        )
        if actor.camp_id != camp.pk:
            actor.camp = camp
            actor.save(update_fields=["camp"])
        configured_perspectives.append((perspective, actor))

        prefix = f"demo-kp-narasi-{perspective['slug']}-"
        if not Mention.objects.filter(project=project, external_id__startswith=prefix).exists():
            for index in range(perspective["count"]):
                sentiment = _weighted_choice(rng, perspective["sentiments"])
                narrative_mentions.append(
                    Mention(
                        project=project,
                        platform=rng.choice(platforms),
                        province=province,
                        regency=regency,
                        author_handle=rng.choice(SOCIAL_HANDLES),
                        external_id=f"{prefix}{index + 1:03d}",
                        content_snippet=rng.choice(perspective["snippets"]),
                        theme=_weighted_choice(rng, perspective["themes"]),
                        sentiment=sentiment,
                        sentiment_confidence=round(rng.uniform(0.72, 0.96), 2),
                        sentiment_model="demo-narrative-v1",
                        emotion=emotion_by_sentiment[sentiment],
                        emotion_labels=[emotion_by_sentiment[sentiment]],
                        posted_at=now - timedelta(
                            days=rng.uniform(0, 30), hours=rng.uniform(0, 24)
                        ),
                        engagement_count=rng.randint(8, 1_200),
                        reach_estimate=rng.randint(300, 75_000),
                        is_political=True,
                        coalition=coalition,
                        issue=issue,
                        matched_keyword="dugaan pungli Garongan",
                        is_scraped=False,
                    )
                )

    unattributed_prefix = "demo-kp-narasi-tidak-teratribusi-"
    if not Mention.objects.filter(
        project=project, external_id__startswith=unattributed_prefix
    ).exists():
        for index in range(NARRATIVE_UNATTRIBUTED_COUNT):
            sentiment = _weighted_choice(
                rng,
                [
                    (Mention.SENTIMENT_POSITIVE, 0.15),
                    (Mention.SENTIMENT_NEUTRAL, 0.55),
                    (Mention.SENTIMENT_NEGATIVE, 0.30),
                ],
            )
            narrative_mentions.append(
                Mention(
                    project=project,
                    platform=rng.choice(platforms),
                    province=province,
                    regency=regency,
                    author_handle=rng.choice(SOCIAL_HANDLES),
                    external_id=f"{unattributed_prefix}{index + 1:03d}",
                    content_snippet=(
                        "Percakapan warga membahas penanganan laporan Garongan, "
                        "namun posisinya belum cukup jelas untuk diatribusikan."
                    ),
                    theme="percakapan campuran",
                    sentiment=sentiment,
                    sentiment_confidence=round(rng.uniform(0.64, 0.82), 2),
                    sentiment_model="demo-narrative-v1",
                    emotion=emotion_by_sentiment[sentiment],
                    emotion_labels=[emotion_by_sentiment[sentiment]],
                    posted_at=now - timedelta(
                        days=rng.uniform(0, 30), hours=rng.uniform(0, 24)
                    ),
                    engagement_count=rng.randint(5, 500),
                    reach_estimate=rng.randint(200, 25_000),
                    is_political=True,
                    issue=issue,
                    matched_keyword="dugaan pungli Garongan",
                    is_scraped=False,
                )
            )

    if narrative_mentions:
        Mention.objects.bulk_create(narrative_mentions)

    # Link the seeded evidence through the same actor/camp and assessment
    # relations used by live ingestion. This also upgrades existing demo rows
    # created by older fixture revisions.
    through_model = Mention.political_actors.through
    actor_links = []
    assessments = []
    for perspective, actor in configured_perspectives:
        mentions = Mention.objects.filter(
            project=project,
            external_id__startswith=f"demo-kp-narasi-{perspective['slug']}-",
        )
        for mention in mentions:
            actor_links.append(
                through_model(mention_id=mention.pk, politicalactor_id=actor.pk)
            )
            assessments.append(
                ActorSentimentAssessment(
                    mention=mention,
                    actor=actor,
                    sentiment=mention.sentiment,
                    confidence=mention.sentiment_confidence,
                    model=mention.sentiment_model,
                )
            )
    through_model.objects.bulk_create(actor_links, ignore_conflicts=True)
    ActorSentimentAssessment.objects.bulk_create(
        assessments, ignore_conflicts=True
    )


def _seed_reviewable_brief(project):
    brief_date = timezone.localdate() - timezone.timedelta(days=1)
    if not DailyBrief.objects.filter(project=project, brief_date=brief_date).exists():
        briefs.generate(project, brief_date, triggered_by="Sistem demo Kulon Progo")


def seed_kulon_progo_demo():
    """Create and return the separate Kulon Progo demo tenant and project."""
    tenant, project, province, regency, user = _seed_identity()
    _seed_governance(tenant, project, user)
    issues = _seed_taxonomy()
    actors, programs = _seed_entities(project)
    _seed_opds(project)
    # Older fixture revisions stored links on a deliberately unresolvable host.
    # Clear them on every reseed so existing deployments stop rendering 404 links.
    Mention.objects.filter(
        project=project, source_url__contains="demo.pantau.local"
    ).update(source_url=None)
    mentions = _seed_mentions(project, province, regency, issues, programs, actors)
    live_issue = _seed_issue_and_alerts(project, mentions)
    _seed_social_buzz(project, province, regency, issues, programs)
    _seed_incident_clusters(project, province, regency)
    _seed_incident_board(project)
    _seed_narrative_mentions(project, province, regency, live_issue)
    _seed_coordination_cluster(project)
    _seed_intelligence(project)
    _seed_reviewable_brief(project)
    return tenant, project


def _seed_intelligence(project):
    """Run the early-warning enrichment stages over the demo corpus.

    Without this the new panels render empty on a fresh install and the features
    look broken rather than unconfigured. Every stage here is idempotent, so a
    reseed refreshes rather than duplicates.

    Deliberately ordered: attribution first (drivers consult it to decide whether
    a mention carries a complaint), then comment analysis, then escalation, which
    consumes all three.
    """
    from apps.analytics import attribution, comment_intel, drivers, escalation

    attribution.ensure_registry(project, own_government_name="Pemkab Kulon Progo")
    drivers.ensure_drivers(project)

    attribution.backfill(project)
    drivers.backfill(project)
    comment_intel.backfill(project)
    comment_intel.recompute_threads(project)
    escalation.assess_project(project)
