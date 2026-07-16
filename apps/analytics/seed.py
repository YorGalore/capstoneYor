import random
from datetime import timedelta

from django.utils import timezone

from apps.core.models import Platform, Province

from .models import (
    Alert, AlertRule, Camp, Category, Coalition, GovernmentProgram, Issue, Mention,
    PoliticalActor, PoliticalIssue, SubCategory,
)

RNG_SEED = 20260710

PLATFORM_WEIGHTS = {
    "x": 0.34, "tiktok": 0.24, "instagram": 0.17, "berita": 0.13,
    "youtube": 0.06, "facebook": 0.04, "forum": 0.02,
}

SENTIMENT_WEIGHTS = [
    (Mention.SENTIMENT_POSITIVE, 0.46),
    (Mention.SENTIMENT_NEUTRAL, 0.33),
    (Mention.SENTIMENT_NEGATIVE, 0.21),
]
EMOTION_CHOICES = [c[0] for c in Mention.EMOTION_CHOICES]

SAMPLE_HANDLES = [
    "@warga_peduli21", "@nusantara_bgkt", "@kabarnusantara", "@suara_timur88",
    "@wartadesa_id", "@analisis_pangan", "@gerakmaju_net", "@ibu_rumahtangga",
    "@petani_muda", "@relawan_pangan",
]

SNIPPET_TEMPLATES = [
    "Program distribusi pangan tahap ini terasa membantu di lingkungan kami.",
    "Kapan bantuan sampai ke wilayah kami? Sudah ditunggu sejak minggu lalu.",
    "Terima kasih atas transparansi data yang dibagikan pemerintah.",
    "Ada laporan keterlambatan distribusi di beberapa titik.",
    "Testimoni penerima manfaat cukup positif di daerah kami.",
    "Perlu evaluasi lebih lanjut soal ketepatan sasaran program ini.",
]

COALITION_THEME_WEIGHTS = {
    "nusantara-raya": [
        ("capaian distribusi tahap 2", 0.31),
        ("testimoni penerima manfaat", 0.24),
        ("transparansi anggaran", 0.17),
        ("koreksi hoaks", 0.11),
        ("kolaborasi pemerintah daerah", 0.10),
        ("apresiasi relawan lapangan", 0.07),
    ],
    "perubahan-bersatu": [
        ("keterlambatan wilayah timur", 0.38),
        ("dugaan salah sasaran", 0.22),
        ("kritik tata kelola anggaran", 0.19),
        ("usulan skema alternatif", 0.09),
        ("desakan audit independen", 0.07),
        ("laporan warga terdampak", 0.05),
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


TAXONOMY = [
    ("Ekonomi", [
        ("Energi", [
            ("Harga BBM", ["bbm", "pertamax", "solar", "subsidi energi"]),
            ("Tarif Listrik", ["listrik", "pln", "tarif dasar"]),
        ]),
        ("Pangan", [
            ("Harga Pangan", ["pangan", "beras", "sembako", "harga bahan"]),
            ("Distribusi Bansos", ["bansos", "bantuan sosial", "sembako gratis"]),
        ]),
    ]),
    ("Kesejahteraan", [
        ("Kesehatan", [
            ("Layanan BPJS", ["bpjs", "jkn", "iuran kesehatan"]),
        ]),
        ("Pendidikan", [
            ("Biaya Sekolah", ["ukt", "spp", "biaya sekolah"]),
        ]),
    ]),
]


def seed_taxonomy():
    """Idempotently seed the three-level Issue Taxonomy (FR-3A.1)."""
    for category_name, subcategories in TAXONOMY:
        category, _ = Category.objects.get_or_create(name=category_name)
        for sub_name, issues in subcategories:
            sub, _ = SubCategory.objects.get_or_create(category=category, name=sub_name)
            for issue_name, keywords in issues:
                Issue.objects.get_or_create(
                    subcategory=sub, name=issue_name, defaults={"keywords": keywords}
                )


CAMPS = [
    ("Koalisi Nusantara Raya", "#1F6FB2"),
    ("Koalisi Perubahan Bersatu", "#B2601F"),
]

# Camps and actors are configuration, never hard-coded political judgments
# (FR-24.3). The seed provides a neutral, symmetric starting set for the demo.
ACTORS = [
    ("Partai Nusantara", PoliticalActor.TYPE_PARTY, "Koalisi Nusantara Raya",
     ["partai nusantara", "nusantara raya"], ["@partainusantara"]),
    ("Partai Perubahan", PoliticalActor.TYPE_PARTY, "Koalisi Perubahan Bersatu",
     ["partai perubahan", "perubahan bersatu"], ["@partaiperubahan"]),
]

PROGRAMS = [
    ("Program Pangan Rakyat", "Kemenko PMK", ["pangan rakyat", "distribusi pangan", "bansos pangan"]),
    ("Subsidi Energi Tepat Sasaran", "Kementerian ESDM", ["subsidi energi", "subsidi bbm"]),
]


def seed_political_entities(project):
    """Seed user-defined camps, public political actors, and tracked programs
    (FR-24, FR-27). Only public/organizational actors — never private individuals
    (FR-29.3)."""
    camps = {}
    for name, color in CAMPS:
        camp, _ = Camp.objects.get_or_create(
            project=project, name=name, defaults={"color": color}
        )
        camps[name] = camp

    for name, actor_type, camp_name, keywords, handles in ACTORS:
        PoliticalActor.objects.get_or_create(
            project=project, name=name,
            defaults={
                "actor_type": actor_type, "camp": camps.get(camp_name),
                "keywords": keywords, "handles": handles,
            },
        )

    for name, agency, keywords in PROGRAMS:
        GovernmentProgram.objects.get_or_create(
            project=project, name=name,
            defaults={"agency": agency, "keywords": keywords},
        )


def seed_analytics(project, mention_count=4000):
    seed_taxonomy()
    seed_political_entities(project)
    if Mention.objects.filter(project=project).exists():
        return

    rng = random.Random(RNG_SEED)
    platforms = {p.slug: p for p in Platform.objects.all()}
    provinces = list(Province.objects.all())
    province_weights = [(p, p.population_online) for p in provinces]
    now = timezone.now()

    mentions = []
    for _ in range(mention_count):
        platform_slug = _weighted_choice(rng, list(PLATFORM_WEIGHTS.items()))
        sentiment = _weighted_choice(rng, SENTIMENT_WEIGHTS)
        province = _weighted_choice(rng, province_weights)
        regency = rng.choice(list(province.regencies.all())) if province.regencies.exists() else None
        posted_at = now - timedelta(days=rng.uniform(0, 30), hours=rng.uniform(0, 24))
        mentions.append(Mention(
            project=project,
            platform=platforms[platform_slug],
            province=province,
            regency=regency,
            author_handle=rng.choice(SAMPLE_HANDLES),
            content_snippet=rng.choice(SNIPPET_TEMPLATES),
            sentiment=sentiment,
            emotion=rng.choice(EMOTION_CHOICES),
            posted_at=posted_at,
            engagement_count=rng.randint(5, 4000),
            reach_estimate=rng.randint(200, 500000),
        ))
    Mention.objects.bulk_create(mentions)

    _seed_political_issue(project, rng, now)
    _seed_alerts(project, now)


def _seed_political_issue(project, rng, now):
    issue, _ = PoliticalIssue.objects.get_or_create(
        project=project,
        title="Distribusi Pangan Wilayah Timur",
        defaults={
            "status": PoliticalIssue.STATUS_ACTIVE,
            "opened_at": now - timedelta(days=16),
            "owner_label": "Tim Respons Cepat",
        },
    )
    coalition_a, _ = Coalition.objects.get_or_create(
        slug="nusantara-raya",
        defaults={
            "name": "Koalisi Nusantara Raya",
            "stance": Coalition.STANCE_PETAHANA,
            "color": "#4656C9",
        },
    )
    coalition_b, _ = Coalition.objects.get_or_create(
        slug="perubahan-bersatu",
        defaults={
            "name": "Koalisi Perubahan Bersatu",
            "stance": Coalition.STANCE_PENANTANG,
            "color": "#B07818",
        },
    )

    platforms = {p.slug: p for p in Platform.objects.all()}
    provinces = list(Province.objects.all())
    province_weights = [(p, p.population_online) for p in provinces]
    political_mentions = []
    coalition_sentiment_weights = (
        (coalition_a, [
            (Mention.SENTIMENT_POSITIVE, 0.58),
            (Mention.SENTIMENT_NEUTRAL, 0.29),
            (Mention.SENTIMENT_NEGATIVE, 0.13),
        ]),
        (coalition_b, [
            (Mention.SENTIMENT_POSITIVE, 0.21),
            (Mention.SENTIMENT_NEUTRAL, 0.33),
            (Mention.SENTIMENT_NEGATIVE, 0.46),
        ]),
    )
    for coalition, sentiment_weights in coalition_sentiment_weights:
        theme_weights = COALITION_THEME_WEIGHTS[coalition.slug]
        for _ in range(700):
            sentiment = _weighted_choice(rng, sentiment_weights)
            political_mentions.append(Mention(
                project=project,
                platform=platforms[_weighted_choice(rng, list(PLATFORM_WEIGHTS.items()))],
                province=_weighted_choice(rng, province_weights),
                author_handle=rng.choice(SAMPLE_HANDLES),
                content_snippet=rng.choice(SNIPPET_TEMPLATES),
                theme=_weighted_choice(rng, theme_weights),
                sentiment=sentiment,
                emotion=rng.choice(EMOTION_CHOICES),
                posted_at=now - timedelta(days=rng.uniform(0, 16), hours=rng.uniform(0, 24)),
                engagement_count=rng.randint(5, 4000),
                reach_estimate=rng.randint(200, 500000),
                is_political=True,
                coalition=coalition,
                issue=issue,
            ))
    Mention.objects.bulk_create(political_mentions)


def _seed_alerts(project, now):
    rule_spike, _ = AlertRule.objects.get_or_create(
        project=project,
        name="Rasio-Neg-3J",
        defaults={
            "condition_summary": "Volume negatif naik >150% dalam 3 jam",
            "channel": AlertRule.CHANNEL_WEBHOOK,
        },
    )
    rule_influencer, _ = AlertRule.objects.get_or_create(
        project=project,
        name="Akun-Berpengaruh",
        defaults={
            "condition_summary": "Sebutan dari akun >1 juta pengikut",
            "channel": AlertRule.CHANNEL_PUSH,
        },
    )
    issue = PoliticalIssue.objects.filter(
        project=project, title="Distribusi Pangan Wilayah Timur"
    ).first()

    Alert.objects.get_or_create(
        project=project,
        title="Lonjakan sentimen negatif — distribusi wilayah timur",
        defaults={
            "rule": rule_spike, "issue": issue, "severity": Alert.SEVERITY_CRITICAL,
            "detail": "Volume negatif +212% dalam 3 jam",
            "triggered_at": now - timedelta(hours=2), "status": Alert.STATUS_ACTIVE,
        },
    )
    Alert.objects.get_or_create(
        project=project,
        title="Sebutan dari akun berpengaruh tinggi",
        defaults={
            "rule": rule_influencer, "issue": issue, "severity": Alert.SEVERITY_WARNING,
            "detail": "@kabarnusantara (2,4 jt pengikut) mengunggah utas kritik",
            "triggered_at": now - timedelta(hours=4), "status": Alert.STATUS_ACTIVE,
        },
    )
    Alert.objects.get_or_create(
        project=project,
        title="Ambang volume harian tercapai — teratasi",
        defaults={
            "rule": rule_spike, "issue": None, "severity": Alert.SEVERITY_INFO,
            "detail": "Dikonfirmasi analis, dikirim ke webhook CRM",
            "triggered_at": now - timedelta(days=1), "status": Alert.STATUS_RESOLVED,
        },
    )
    Alert.objects.get_or_create(
        project=project,
        title="Klaster amplifikasi baru terdeteksi",
        defaults={
            "rule": rule_spike, "issue": issue, "severity": Alert.SEVERITY_WARNING,
            "detail": "Klaster-09 melewati ambang skor koordinasi 0,75",
            "triggered_at": now - timedelta(hours=30), "status": Alert.STATUS_ACTIVE,
        },
    )
    Alert.objects.get_or_create(
        project=project,
        title="Sentimen positif melampaui rata-rata mingguan",
        defaults={
            "rule": rule_spike, "issue": None, "severity": Alert.SEVERITY_INFO,
            "detail": "Testimoni penerima manfaat tahap 2 mendominasi linimasa",
            "triggered_at": now - timedelta(days=2), "status": Alert.STATUS_RESOLVED,
        },
    )
