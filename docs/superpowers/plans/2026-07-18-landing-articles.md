# Landing Page Articles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a visible "Artikel" section to the public landing page linking to 6 real,
server-rendered article pages (Bahasa Indonesia) that explain why media monitoring matters
and how PANTAU addresses it.

**Architecture:** Static content module (`apps/core/articles.py`) holding a list of article
dicts, one new Django view + URL for the detail page, one new template that reuses the
landing page's chrome, one new section inserted into `landing.html`, and matching CSS added
to the existing `landing.css`. No new model, no migration, no JS — matches the existing
zero-JS static-content pattern of the public site.

**Tech Stack:** Django templates, existing `landing.css`, Django test client (`TestCase`).

## Global Constraints

- All user-facing copy is Bahasa Indonesia (matches the rest of the site).
- No new dependencies (no markdown library) — article bodies are plain `("h", ...)` /
  `("p", ...)` tuples rendered by the template.
- No new Django app, model, or migration — content lives in `apps/core/articles.py`.
- Views use `@login_not_required` like the existing `landing`/`onboarding` views (spec:
  `docs/superpowers/specs/2026-07-18-landing-articles-design.md`).
- Follow the existing route naming: `core:artikel_detail`, path `artikel/<slug:slug>/`.

---

### Task 1: Article content module

**Files:**
- Create: `apps/core/articles.py`
- Test: `apps/core/tests/test_articles.py`

**Interfaces:**
- Produces: `ARTICLES: list[dict]` where each dict has keys `slug` (str), `title` (str),
  `excerpt` (str), `category` (str), `read_minutes` (int), `body` (list of 2-tuples,
  first element `"h"` or `"p"`, second element str). Also `get_article(slug: str) -> dict | None`.

- [ ] **Step 1: Write the failing test**

```python
# apps/core/tests/test_articles.py
from django.test import SimpleTestCase

from apps.core.articles import ARTICLES, get_article


class ArticleContentTest(SimpleTestCase):
    def test_six_articles_with_unique_slugs(self):
        self.assertEqual(len(ARTICLES), 6)
        slugs = [a["slug"] for a in ARTICLES]
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_every_article_has_required_fields_and_body(self):
        required_keys = {"slug", "title", "excerpt", "category", "read_minutes", "body"}
        for article in ARTICLES:
            self.assertTrue(required_keys.issubset(article.keys()), article["slug"])
            self.assertIsInstance(article["read_minutes"], int)
            self.assertGreater(len(article["body"]), 0)
            for kind, text in article["body"]:
                self.assertIn(kind, {"h", "p"})
                self.assertTrue(text.strip())

    def test_get_article_looks_up_by_slug(self):
        first = ARTICLES[0]
        self.assertEqual(get_article(first["slug"]), first)
        self.assertIsNone(get_article("tidak-ada-slug-seperti-ini"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.core.tests.test_articles -v 2`
Expected: FAIL with `ModuleNotFoundError: No module named 'apps.core.articles'`

- [ ] **Step 3: Write the content module**

```python
# apps/core/articles.py
"""Static editorial content for the public landing page.

Six evergreen articles in Bahasa Indonesia. Each explains why a facet of media
monitoring matters, then closes by connecting it to a concrete PANTAU capability
already listed on the landing page (see templates/core/landing.html #fitur).
"""

ARTICLES = [
    {
        "slug": "memantau-percakapan-publik-real-time",
        "title": "Kenapa organisasi perlu memantau percakapan publik secara real-time",
        "excerpt": (
            "Opini publik terbentuk dalam hitungan jam, bukan minggu. Organisasi yang "
            "masih menunggu laporan mingguan selalu tertinggal satu langkah."
        ),
        "category": "Dasar-dasar",
        "read_minutes": 4,
        "body": [
            ("p", (
                "Percakapan publik hari ini bergerak lebih cepat daripada siklus "
                "pelaporan organisasi mana pun. Sebuah unggahan bisa dibagikan ribuan "
                "kali sebelum tim komunikasi sempat membuka dashboard media sosial "
                "mereka. Ketika organisasi baru menyadari sebuah isu setelah muncul di "
                "berita utama, mereka sudah kehilangan kesempatan untuk merespons di "
                "titik paling murah: sebelum isu itu membesar."
            )),
            ("h", "Mendengar bukan hanya mencatat"),
            ("p", (
                "Media monitoring yang baik bukan sekadar mengumpulkan mention atau "
                "menghitung berapa kali sebuah kata kunci disebut. Nilainya ada pada "
                "konteks: siapa yang bicara, di kanal apa, dengan nada seperti apa, dan "
                "apakah volumenya sedang naik atau baru saja mereda. Tanpa konteks itu, "
                "angka mentah hanya menjadi kebisingan tambahan di meja kerja tim."
            )),
            ("h", "Kecepatan adalah keunggulan, bukan kemewahan"),
            ("p", (
                "Bagi brand, keterlambatan merespons isu pelanggan berarti kehilangan "
                "kepercayaan sebelum sempat menjelaskan duduk perkara. Bagi instansi "
                "publik, keterlambatan berarti kebijakan yang sudah dijalankan sebelum "
                "aspirasi masyarakat sempat didengar. Di kedua kasus, kecepatan mendengar "
                "menentukan kualitas keputusan yang diambil sesudahnya."
            )),
            ("p", (
                "PANTAU dibangun di atas prinsip ini: pengumpulan data berjalan "
                "real-time dan terjadwal dari media sosial, portal berita, RSS, dan "
                "sumber digital lain, dengan kata kunci dan domain yang dapat "
                "dikonfigurasi sesuai kebutuhan organisasi Anda — sehingga sinyal "
                "penting sampai ke meja Anda saat masih bisa ditindaklanjuti, bukan "
                "setelah menjadi berita."
            )),
        ],
    },
    {
        "slug": "mendeteksi-krisis-reputasi-sebelum-membesar",
        "title": "Mendeteksi krisis reputasi sebelum membesar",
        "excerpt": (
            "Krisis reputasi jarang muncul tiba-tiba. Ia meninggalkan jejak sinyal kecil "
            "yang sering terlewat karena tidak ada yang memantaunya secara sistematis."
        ),
        "category": "Reputasi",
        "read_minutes": 5,
        "body": [
            ("p", (
                "Sebagian besar krisis reputasi punya pola yang mirip: dimulai dari "
                "keluhan kecil di satu kanal, dibagikan ulang oleh segelintir akun "
                "berpengaruh, lalu meledak setelah media arus utama ikut memberitakan. "
                "Antara tahap pertama dan tahap terakhir itu biasanya ada jendela waktu "
                "yang cukup untuk merespons — asalkan ada yang memperhatikannya."
            )),
            ("h", "Masalahnya bukan data, tapi visibilitas"),
            ("p", (
                "Banyak organisasi sebenarnya punya cukup data untuk melihat krisis "
                "sejak dini: keluhan pelanggan, komentar di media sosial, forum diskusi. "
                "Yang sering hilang adalah kemampuan menyatukan sinyal-sinyal ini dan "
                "mengenali kapan sebuah lonjakan kecil berbeda dari fluktuasi normal "
                "harian."
            )),
            ("h", "Dari ambang batas ke eskalasi terkoordinasi"),
            ("p", (
                "Begitu sebuah topik melewati ambang batas yang wajar, yang dibutuhkan "
                "bukan lagi sekadar notifikasi, tapi ruang kerja bersama: siapa yang "
                "menindaklanjuti, respons apa yang sudah dikirim, dan bagaimana "
                "perkembangan sentimen setelah respons itu keluar. Tanpa ruang kerja "
                "semacam ini, krisis sering ditangani secara ad-hoc lewat pesan berantai "
                "yang sulit diaudit setelahnya."
            )),
            ("p", (
                "Fitur Peringatan & War Room PANTAU dirancang untuk jendela waktu ini: "
                "atur ambang peringatan sesuai konteks organisasi, eskalasikan isu "
                "penting ke tim yang tepat, dan catat setiap respons dalam satu ruang "
                "kendali bersama — sehingga penanganan krisis meninggalkan jejak yang "
                "bisa dievaluasi, bukan hanya percakapan yang menguap."
            )),
        ],
    },
    {
        "slug": "media-monitoring-untuk-pemerintah",
        "title": "Media monitoring untuk pemerintah: mendengar aspirasi, merancang kebijakan berbasis data",
        "excerpt": (
            "Instansi publik punya kewajiban mendengar warganya. Media monitoring "
            "membantu mengubah kewajiban itu dari formalitas menjadi praktik yang hidup."
        ),
        "category": "Pemerintahan",
        "read_minutes": 5,
        "body": [
            ("p", (
                "Kebijakan publik yang baik biasanya lahir dari dua arah: kajian teknis "
                "di dalam instansi, dan aspirasi masyarakat yang disampaikan lewat "
                "berbagai kanal — media sosial, portal berita daerah, forum warga. "
                "Tantangannya, arah kedua ini jauh lebih sulit dipantau secara "
                "sistematis dibanding arah pertama, terutama ketika volumenya besar dan "
                "tersebar di banyak platform."
            )),
            ("h", "Aspirasi yang tersebar butuh peta, bukan sekadar arsip"),
            ("p", (
                "Mengumpulkan sebutan tentang sebuah program adalah langkah awal. "
                "Langkah yang lebih penting adalah memetakan di wilayah mana respons "
                "paling positif, di wilayah mana keluhan menumpuk, dan isu apa yang "
                "mulai tumbuh sebelum sempat masuk ke rapat evaluasi. Tanpa pemetaan "
                "ini, instansi berisiko merespons isu yang sudah usang sambil melewatkan "
                "isu yang justru sedang membesar."
            )),
            ("h", "Netral, terukur, dan bisa dipertanggungjawabkan"),
            ("p", (
                "Media monitoring di ranah pemerintahan menuntut standar berbeda "
                "dibanding di dunia brand: data harus terisolasi dengan tegas dari "
                "kepentingan politik praktis, aksesnya perlu diatur berdasarkan peran, "
                "dan setiap analisis idealnya bisa ditelusuri kembali sumbernya. Ini "
                "bukan detail teknis semata — ini yang membuat hasil pemantauan layak "
                "dijadikan dasar kebijakan publik."
            )),
            ("p", (
                "PANTAU menyediakan intelijen regional hingga tingkat provinsi dan "
                "kabupaten/kota, brief eksekutif harian yang dapat ditinjau dan "
                "didukung rujukan regulasi, serta governance dengan isolasi tenant, "
                "akses berbasis peran, dan jejak audit — dirancang agar instansi "
                "pemerintah bisa mendengar aspirasi warganya tanpa mengorbankan tata "
                "kelola yang netral dan akuntabel."
            )),
        ],
    },
    {
        "slug": "dari-data-mentah-ke-keputusan",
        "title": "Dari data mentah ke keputusan: memahami sentimen & narasi publik",
        "excerpt": (
            "Ribuan sebutan per hari tidak ada artinya tanpa cara membacanya. Sentimen "
            "dan narasi adalah dua lensa yang mengubah angka menjadi pemahaman."
        ),
        "category": "Analisis",
        "read_minutes": 4,
        "body": [
            ("p", (
                "Angka jumlah sebutan sering jadi metrik pertama yang dilihat, padahal "
                "metrik ini paling mudah menyesatkan. Lonjakan sebutan bisa berarti "
                "kampanye berhasil, atau bisa berarti krisis sedang berlangsung — angka "
                "itu sendiri tidak membedakan keduanya."
            )),
            ("h", "Sentimen memberi arah, narasi memberi makna"),
            ("p", (
                "Sentimen — positif, negatif, netral, dan emosi dominan di baliknya — "
                "memberi tahu ke arah mana persepsi publik bergerak. Namun untuk "
                "memahami mengapa ia bergerak ke arah itu, dibutuhkan lapisan "
                "berikutnya: narasi. Tema apa yang sedang dominan, aktor mana yang "
                "menggerakkannya, dan berapa besar share of voice masing-masing pihak "
                "dalam percakapan tersebut."
            )),
            ("h", "Dari isu yang tumbuh ke isu yang mereda"),
            ("p", (
                "Isu publik punya siklus hidup. Melihat siklus ini — bukan hanya potret "
                "sesaat — memungkinkan tim membedakan isu yang sedang tumbuh dan perlu "
                "direspons segera, dari isu yang sebenarnya sudah mulai mereda dengan "
                "sendirinya. Salah membaca fase ini berarti membuang sumber daya untuk "
                "merespons sesuatu yang sudah selesai, atau justru mengabaikan sesuatu "
                "yang baru mulai."
            )),
            ("p", (
                "Kapabilitas Sentimen & Emosi serta Narasi & Isu di PANTAU dirancang "
                "untuk dua lapisan pembacaan ini sekaligus — memetakan tema, share of "
                "voice, dan aktor, sambil tetap memberi tim analis kendali untuk "
                "mengoreksi label AI dan mengelola taksonomi sesuai konteks organisasi."
            )),
        ],
    },
    {
        "slug": "mengenali-disinformasi-dan-aktivitas-terkoordinasi",
        "title": "Mengenali disinformasi dan aktivitas terkoordinasi (buzzer/bot) di ruang digital",
        "excerpt": (
            "Tidak semua lonjakan percakapan itu organik. Membedakan suara publik yang "
            "asli dari aktivitas terkoordinasi adalah keterampilan tersendiri."
        ),
        "category": "Integritas Informasi",
        "read_minutes": 5,
        "body": [
            ("p", (
                "Salah satu tantangan terbesar dalam membaca ruang digital hari ini "
                "adalah membedakan mana suara publik yang genuin dan mana aktivitas yang "
                "sengaja direkayasa untuk terlihat seperti suara publik. Buzzer, akun "
                "bot, dan jaringan amplifikasi terkoordinasi bisa membuat sebuah opini "
                "minoritas terlihat seperti pendapat mayoritas dalam hitungan jam."
            )),
            ("h", "Pola yang menyingkap koordinasi"),
            ("p", (
                "Aktivitas terkoordinasi biasanya meninggalkan pola yang tidak muncul "
                "pada percakapan organik: pesan yang nyaris identik disebar oleh banyak "
                "akun dalam rentang waktu sempit, akun-akun baru yang tiba-tiba aktif "
                "bersamaan pada satu isu, atau cluster akun yang selalu bergerak "
                "serempak pada topik yang berbeda-beda. Pola semacam ini sulit dilihat "
                "manusia satu per satu, tapi cukup jelas ketika dianalisis secara "
                "agregat."
            )),
            ("h", "Kenapa ini penting di luar urusan politik"),
            ("p", (
                "Deteksi koordinasi bukan hanya relevan untuk isu politik. Brand juga "
                "menghadapi kampanye negatif terkoordinasi dari pesaing atau pihak tak "
                "dikenal, dan instansi publik perlu memastikan masukan yang mereka "
                "gunakan sebagai dasar kebijakan benar-benar mencerminkan aspirasi "
                "warga, bukan hasil rekayasa segelintir pihak."
            )),
            ("p", (
                "Fitur Deteksi Koordinasi PANTAU dibangun untuk menemukan pola aktivitas "
                "tidak organik, kemiripan pesan antar akun, dan cluster akun yang "
                "bergerak serempak — membantu tim membedakan sinyal publik yang otentik "
                "dari kebisingan yang sengaja diciptakan."
            )),
        ],
    },
    {
        "slug": "dari-mendengar-ke-bertindak",
        "title": "Dari mendengar ke bertindak: membangun war room komunikasi krisis yang efektif",
        "excerpt": (
            "Mendengar sinyal lebih awal tidak banyak berguna jika organisasi tidak "
            "punya cara terstruktur untuk bertindak atasnya."
        ),
        "category": "Respons",
        "read_minutes": 4,
        "body": [
            ("p", (
                "Banyak organisasi sudah cukup baik dalam mengumpulkan data monitoring, "
                "tapi berhenti di situ. Dashboard penuh grafik dan angka, namun ketika "
                "krisis benar-benar terjadi, respons tetap berjalan lewat rangkaian "
                "pesan WhatsApp yang tersebar dan sulit ditelusuri ulang setelah "
                "krisisnya reda."
            )),
            ("h", "War room bukan sekadar ruang chat"),
            ("p", (
                "War room komunikasi krisis yang efektif menyatukan tiga hal dalam satu "
                "tempat: sinyal yang memicu perhatian, keputusan yang diambil oleh tim, "
                "dan hasil dari keputusan tersebut. Struktur ini penting bukan hanya "
                "saat krisis berlangsung, tapi juga sesudahnya — untuk evaluasi, "
                "pelaporan ke pimpinan, dan pembelajaran organisasi ke depan."
            )),
            ("h", "Dari respons individu ke respons tim"),
            ("p", (
                "Ketika penanganan krisis hanya bergantung pada satu-dua orang yang "
                "kebetulan melihat isunya lebih dulu, organisasi rentan kehilangan "
                "momentum begitu orang itu tidak tersedia. Ruang kerja bersama dengan "
                "peran dan izin yang jelas memastikan penanganan krisis tetap berjalan "
                "sebagai proses tim, bukan tindakan individu yang kebetulan sigap."
            )),
            ("p", (
                "PANTAU menyatukan pengumpulan data, analisis AI, dan War Room dalam "
                "satu sistem yang dapat diaudit — dilengkapi Brief Eksekutif harian "
                "serta Governance & Audit dengan akses berbasis peran dan jejak audit, "
                "sehingga setiap langkah dari mendengar sinyal sampai menindaklanjutinya "
                "tercatat dan bisa dipertanggungjawabkan."
            )),
        ],
    },
]

_ARTICLES_BY_SLUG = {article["slug"]: article for article in ARTICLES}


def get_article(slug):
    return _ARTICLES_BY_SLUG.get(slug)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test apps.core.tests.test_articles -v 2`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add apps/core/articles.py apps/core/tests/test_articles.py
git commit -m "$(cat <<'EOF'
Add static article content for the landing page

Six evergreen articles (Bahasa Indonesia) on why media monitoring
matters, each closing with the concrete PANTAU capability that
addresses it. Content lives in apps/core/articles.py, no DB model.
EOF
)"
```

---

### Task 2: Article detail view and URL

**Files:**
- Modify: `apps/core/views.py`
- Modify: `apps/core/urls.py`
- Test: `apps/core/tests/test_articles.py` (append to Task 1's file)

**Interfaces:**
- Consumes: `apps.core.articles.ARTICLES`, `apps.core.articles.get_article(slug)` from Task 1.
- Produces: view `article_detail(request, slug)`; URL name `core:artikel_detail` resolving
  `artikel/<slug:slug>/`. Renders `core/artikel_detail.html` with context `{"article": ...,
  "related": [...]}` where `related` is `ARTICLES` minus the current one (max 5, natural order).

- [ ] **Step 1: Write the failing tests**

Append to `apps/core/tests/test_articles.py`:

```python
from django.test import TestCase


class ArticleDetailViewTest(TestCase):
    def test_known_slug_returns_200_with_title_and_related_links(self):
        article = ARTICLES[0]
        response = self.client.get(f"/artikel/{article['slug']}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, article["title"])
        other = ARTICLES[1]
        self.assertContains(response, other["title"])

    def test_unknown_slug_returns_404(self):
        response = self.client.get("/artikel/slug-yang-tidak-ada/")
        self.assertEqual(response.status_code, 404)

    def test_landing_page_links_to_every_article(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        for article in ARTICLES:
            self.assertContains(response, f"/artikel/{article['slug']}/")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.core.tests.test_articles -v 2`
Expected: FAIL — `test_known_slug_...` and `test_unknown_slug_...` fail with 404/`NoReverseMatch`
(no URL yet); `test_landing_page_links_to_every_article` fails because the links aren't on the
page yet.

- [ ] **Step 3: Add the view**

In `apps/core/views.py`, add the import and view (after the existing `onboarding_success` view,
before `profile`):

```python
from django.http import Http404
from django.shortcuts import redirect, render

from .articles import ARTICLES, get_article
from .forms import OnboardingRequestForm
from .models import AnalystProfile


@login_not_required
def article_detail(request, slug):
    article = get_article(slug)
    if article is None:
        raise Http404("Artikel tidak ditemukan")
    related = [a for a in ARTICLES if a["slug"] != slug][:5]
    return render(request, "core/artikel_detail.html", {"article": article, "related": related})
```

- [ ] **Step 4: Add the URL**

In `apps/core/urls.py`:

```python
from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("mulai/", views.onboarding, name="onboarding"),
    path("mulai/berhasil/", views.onboarding_success, name="onboarding_success"),
    path("artikel/<slug:slug>/", views.article_detail, name="artikel_detail"),
    path("profil/", views.profile, name="profile"),
]
```

- [ ] **Step 5: Run tests — expect the 404 test to pass, the other two still failing**

Run: `python manage.py test apps.core.tests.test_articles -v 2`
Expected: `test_unknown_slug_returns_404` PASS; `test_known_slug_...` fails with
`TemplateDoesNotExist: core/artikel_detail.html`; `test_landing_page_links_to_every_article`
still fails (Task 3 fixes this).

- [ ] **Step 6: Commit**

```bash
git add apps/core/views.py apps/core/urls.py apps/core/tests/test_articles.py
git commit -m "$(cat <<'EOF'
Add article_detail view and artikel/<slug>/ route

Wires apps.core.articles content to a public, login-not-required
detail page. Template comes in the next commit.
EOF
)"
```

---

### Task 3: Article detail template

**Files:**
- Create: `templates/core/artikel_detail.html`
- Test: none new — Task 2's `test_known_slug_returns_200_with_title_and_related_links` covers
  this.

**Interfaces:**
- Consumes: context `article` (dict shape from Task 1: `slug`, `title`, `excerpt`, `category`,
  `read_minutes`, `body`) and `related` (list of the same shape) from Task 2's view.
- Consumes: `core:onboarding`, `core:artikel_detail`, `login` URL names (already used in
  `templates/core/landing.html`).

- [ ] **Step 1: Write the template**

```html
{% load static %}
<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ article.title }} — PANTAU</title><meta name="description" content="{{ article.excerpt }}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet"><link rel="stylesheet" href="{% static 'core/css/landing.css' %}"></head>
<body><div class="research-banner"><div class="wrap">PANTAU adalah proyek riset yang dikembangkan oleh <a href="https://senada-ugm.github.io/" target="_blank" rel="noopener">SENADA (Software Engineering and Data Lab)</a>, Departemen Ilmu Komputer dan Elektronika, Fakultas MIPA, Universitas Gadjah Mada.</div></div>
<nav class="nav wrap"><a class="brand" href="/"><span class="logo">P</span><span>PANTAU<small>NARASI &amp; OPINI</small></span></a><div class="navlinks"><a href="/#fitur">Fitur</a><a href="/#solusi">Solusi</a><a href="/#artikel">Artikel</a></div><div class="navcta"><a class="text-link" href="{% url 'login' %}">Masuk</a><a class="button small" href="{% url 'core:onboarding' %}">Jadwalkan demo <span>↗</span></a></div></nav>

<main><article class="article-detail wrap"><div class="article-meta"><span class="article-tag">{{ article.category }}</span><span>{{ article.read_minutes }} menit baca</span></div><h1>{{ article.title }}</h1>
{% for kind, text in article.body %}{% if kind == "h" %}<h2>{{ text }}</h2>{% else %}<p>{{ text }}</p>{% endif %}{% endfor %}
</article>

<section class="article-related wrap"><h3>Artikel lainnya</h3><ul>{% for other in related %}<li><a href="{% url 'core:artikel_detail' other.slug %}">{{ other.title }}</a></li>{% endfor %}</ul></section>

<section class="final-cta wrap"><small>KEPUTUSAN YANG LEBIH CEPAT DIMULAI DARI SINYAL YANG TEPAT</small><h2>Apa yang perlu Anda <em>pantau hari ini?</em></h2><p>Jadwalkan sesi singkat bersama tim kami. Kami akan membantu memetakan kebutuhan organisasi Anda.</p><a class="button" href="{% url 'core:onboarding' %}">Jadwalkan demo <span>→</span></a></section></main>
<footer><div class="wrap footer"><a class="brand" href="/"><span class="logo">P</span><span>PANTAU<small>NARASI &amp; OPINI</small></span></a><p>Social intelligence untuk keputusan yang bertanggung jawab.</p><div><a href="/#fitur">Fitur</a><a href="{% url 'login' %}">Masuk</a><a href="{% url 'core:onboarding' %}">Hubungi kami</a></div></div>
<div class="wrap research-credit"><p>PANTAU adalah proyek riset yang dikembangkan oleh <a href="https://senada-ugm.github.io/" target="_blank" rel="noopener">SENADA — Software Engineering and Data Lab</a>, Departemen Ilmu Komputer dan Elektronika, FMIPA, Universitas Gadjah Mada, dipimpin oleh Assoc. Prof. Lukman Heryawan, Ph.D. SENADA meneliti rekayasa perangkat lunak, ilmu data, dan teknologi mutakhir untuk kesehatan, pendidikan, dan masyarakat.</p></div></footer></body></html>
```

- [ ] **Step 2: Run the Task 2 tests to verify the detail page now passes**

Run: `python manage.py test apps.core.tests.test_articles -v 2`
Expected: `test_known_slug_returns_200_with_title_and_related_links` PASS;
`test_landing_page_links_to_every_article` still FAILS (Task 4 adds those links).

- [ ] **Step 3: Commit**

```bash
git add templates/core/artikel_detail.html
git commit -m "$(cat <<'EOF'
Add article detail template

Reuses the landing page's header/footer chrome and ends every
article with the same onboarding CTA as the landing page.
EOF
)"
```

---

### Task 4: Landing page "Artikel" section, nav link, and CSS

**Files:**
- Modify: `templates/core/landing.html`
- Modify: `static/core/css/landing.css`

**Interfaces:**
- Consumes: `apps.core.articles.ARTICLES` is not passed as context (landing view renders with
  no context per `apps/core/views.py:15`) — the section is built with a Django `{% for %}` over
  a context variable, so `views.landing` must pass `articles=ARTICLES` as well. This is the one
  change to `views.landing` in this task.

- [ ] **Step 1: Pass articles into the landing view**

In `apps/core/views.py`, update `landing`:

```python
@login_not_required
def landing(request):
    # The public page is for the public. Someone already signed in who lands here — from a
    # bookmark of the root, or the logo on the way back — should go to work, not be shown
    # a "Masuk" button and a demo booking form they have no use for.
    if request.user.is_authenticated:
        return redirect("analytics:ringkasan")
    return render(request, "core/landing.html", {"articles": ARTICLES})
```

- [ ] **Step 2: Add the nav link**

In `templates/core/landing.html`, in the `<nav class="nav wrap">` line, change:

```html
<div class="navlinks"><a href="#fitur">Fitur</a><a href="#solusi">Solusi</a><a href="#cara-kerja">Cara kerja</a></div>
```

to:

```html
<div class="navlinks"><a href="#fitur">Fitur</a><a href="#solusi">Solusi</a><a href="#artikel">Artikel</a><a href="#cara-kerja">Cara kerja</a></div>
```

- [ ] **Step 3: Insert the Artikel section**

In `templates/core/landing.html`, insert this new `<section>` between the `#solusi` section
(ends `</section>`) and the `#cara-kerja` section (`<section id="cara-kerja" ...>`):

```html
<section id="artikel" class="articles wrap"><div class="section-kicker">KENAPA MEDIA MONITORING PENTING</div><div class="section-head"><h2>Bukan sekadar tren.<br><em>Ini cara kerja opini publik.</em></h2><p>Sebelum memutuskan bagaimana PANTAU cocok untuk organisasi Anda, kenali dulu mengapa memantau percakapan publik — dan bertindak cepat atasnya — menjadi kebutuhan, bukan pilihan.</p></div><div class="article-grid">{% for article in articles %}<a class="article-card" href="{% url 'core:artikel_detail' article.slug %}"><span class="article-tag">{{ article.category }}</span><h3>{{ article.title }}</h3><p>{{ article.excerpt }}</p><small>{{ article.read_minutes }} menit baca →</small></a>{% endfor %}</div></section>
```

- [ ] **Step 4: Add CSS for `.articles`, `.article-grid`, `.article-card`, and the detail page**

Append to `static/core/css/landing.css` (same minified single-line convention as the rest of
the file):

```css
.articles{padding:110px 0}.article-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:#cfd9d8;border:1px solid #cfd9d8}.article-card{display:block;background:var(--paper);padding:28px;transition:background .15s}.article-card:hover{background:#eef4f3}.article-tag{display:inline-block;font:700 9px Archivo;letter-spacing:.1em;color:var(--teal);margin-bottom:14px}.article-card h3{font-size:18px;line-height:1.3;margin-bottom:12px}.article-card p{color:var(--muted);font-size:13px;line-height:1.6;margin-bottom:18px}.article-card small{font-size:11px;font-weight:600;color:var(--teal)}.article-detail{max-width:700px;padding:90px 0 40px}.article-meta{display:flex;gap:16px;align-items:center;margin-bottom:18px}.article-meta span:last-child{font-size:11px;color:var(--muted)}.article-detail>h1{font-size:clamp(30px,4vw,44px);line-height:1.15;letter-spacing:-.03em;margin:0 0 34px}.article-detail h2{font-size:22px;margin:38px 0 14px}.article-detail p{color:var(--ink2);font-size:15px;line-height:1.8;margin:0 0 18px}.article-related{max-width:700px;padding:20px 0 60px;border-top:1px solid var(--line)}.article-related h3{font-size:13px;letter-spacing:.06em;color:var(--muted);margin:30px 0 16px}.article-related ul{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:12px}.article-related a{font-size:14px;font-weight:600;color:var(--teal)}.article-related a:hover{text-decoration:underline}
```

Also extend the existing mobile media query (the single `@media(max-width:800px){...}` rule at
the end of the file) by adding `.article-grid{grid-template-columns:1fr}` to it, next to the
existing `.feature-grid{grid-template-columns:1fr}` declaration.

- [ ] **Step 5: Run the full article test suite**

Run: `python manage.py test apps.core.tests.test_articles -v 2`
Expected: PASS (all tests, including `test_landing_page_links_to_every_article`)

- [ ] **Step 6: Run the existing navigation smoke tests to check for regressions**

Run: `python manage.py test apps.core.tests.test_navigation -v 2`
Expected: PASS (landing page still renders, still contains "Pahami apa yang publik")

- [ ] **Step 7: Commit**

```bash
git add apps/core/views.py templates/core/landing.html static/core/css/landing.css
git commit -m "$(cat <<'EOF'
Surface articles section on the landing page

Adds an "Artikel" nav link and a 6-card section linking to the new
article pages, styled to match the existing feature-grid language.
EOF
)"
```

---

### Task 5: Manual verification in browser

**Files:** none (verification only)

- [ ] **Step 1: Start the dev server**

Run: `python manage.py runserver`

- [ ] **Step 2: Visit the landing page and confirm the Artikel section renders**

Open `http://127.0.0.1:8000/` — confirm the nav has an "Artikel" link, the new section appears
between "Solusi" and "Cara kerja" with 6 cards, and clicking a card navigates to its detail page.

- [ ] **Step 3: Confirm a detail page renders correctly and links back**

On an article detail page, confirm the title/body render, "Artikel lainnya" lists the other 5
titles and each links to a working page, and the final CTA button links to `/mulai/`.

- [ ] **Step 4: Confirm mobile layout**

Resize the browser below 800px width (or use device toolbar) and confirm the article grid
collapses to one column without overflow.

---

## Self-Review Notes

- Spec coverage: content module (Task 1), routing (Task 2), detail template (Task 3), landing
  section + nav + CSS (Task 4), manual check (Task 5) — all spec sections have a task.
- Type consistency: `ARTICLES` / `get_article` names and the `body` tuple shape are defined
  once in Task 1 and reused verbatim in Tasks 2-4.
- No placeholders: article bodies, view code, template markup, and CSS are complete, not
  described.
