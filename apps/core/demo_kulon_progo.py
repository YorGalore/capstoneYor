"""Contextual, fictional demo fixture for Kabupaten Kulon Progo.

The generic Kemenko PMK fixture is useful for showing the platform at national
scale.  This fixture deliberately lives beside it as a separate tenant so a
government communications team can evaluate the same screens with local names,
programs, sources, and issues.  Every record is deterministic and idempotent;
none of it is presented as live collection data.
"""

from datetime import datetime, time

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.analytics import briefs
from apps.analytics.models import (
    Alert,
    AlertRule,
    Category,
    DailyBrief,
    GovernmentProgram,
    Issue,
    IssueLabel,
    Mention,
    PoliticalActor,
    PoliticalIssue,
    SubCategory,
)
from apps.governance.models import (
    AuditLogEntry,
    MonitoredDomain,
    MonitoringKeyword,
    PlatformIntegration,
    PolicyAcknowledgment,
    PoliticalMonitoringPermission,
)
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
]

LEGACY_DOMAIN_ALIASES = {"prolimannews.com", "vivajogja.com", "detik.com", "purworejo24.com", "kulonprogokab.go.id"}


PROGRAMS = [
    ("BBGRM 2026", "Dinas PMD Dalduk dan KB", ["bbgrm", "bulan bhakti gotong royong"]),
    ("Kulinerun 2026", "Dinas Pariwisata", ["kulinerun", "sport tourism"]),
    ("Sekolah Rakyat Kulon Progo", "Dinas Pendidikan", ["sekolah rakyat"]),
    ("Pengembangan BUMDes", "Dinas PMD Dalduk dan KB", ["bumdes", "potensi lokal"]),
    ("Ketahanan Pangan", "Dinas Pertanian dan Pangan", ["ketahanan pangan", "penanaman jagung"]),
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
]


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
        PlatformIntegration.objects.get_or_create(
            project=project,
            platform=platform,
            defaults={
                "method": platform.method,
                "actor_id": "demo-contextual",
                "is_active": True,
                "status_note": "Konfigurasi demo; kredensial live belum dipasang",
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
    return issues


def _seed_entities(project):
    actors = {}
    for name, actor_type, keywords, handles in [
        ("Agung Setyawan", PoliticalActor.TYPE_OFFICIAL, ["agung setyawan", "bupati kulon progo"], []),
        ("Ambar Purwoko", PoliticalActor.TYPE_OFFICIAL, ["ambar purwoko", "wakil bupati kulon progo"], []),
        ("Pemerintah Kabupaten Kulon Progo", PoliticalActor.TYPE_ORGANIZATION, ["pemkab kulon progo", "pemerintah kabupaten kulon progo"], ["@pemkabkulonprogo"]),
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
                "source_url": f"https://demo.pantau.local/kulon-progo/berita/{index:02d}",
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
    mentions = _seed_mentions(project, province, regency, issues, programs, actors)
    _seed_issue_and_alerts(project, mentions)
    _seed_reviewable_brief(project)
    return tenant, project
