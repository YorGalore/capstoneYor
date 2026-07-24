#set document(title: "Dokumentasi Teknis - PANTAU", author: "Tim Pengembang PANTAU")
#set text(lang: "id", size: 10.5pt, font: "New Computer Modern")
#set page(numbering: "1", margin: (x: 2.2cm, y: 2.2cm))
#set heading(numbering: "1.1.1")
#set par(justify: true)

#let zws = "\u{200B}"
#let brk(s) = {
  let out = ""
  let first = true
  for c in s {
    if not first and c == upper(c) and c != lower(c) {
      out += zws
    }
    out += c
    if c == "_" or c == "/" or c == "." {
      out += zws
    }
    first = false
  }
  out
}
#let mcell(s) = raw(brk(s))

#let diagram(path, caption) = figure(
  block(
    width: 100%,
    fill: rgb("#f5f5f7"),
    inset: 8pt,
    radius: 3pt,
    align(center, image(path, width: 95%))
  ),
  caption: caption,
  supplement: "Diagram"
)

#align(center)[
  #v(3cm)
  #text(size: 24pt, weight: "bold")[Dokumentasi Teknis]
  #v(0.3cm)
  #text(size: 18pt)[Platform PANTAU]
  #v(0.1cm)
  #text(size: 13pt, style: "italic")[Sistem Pemantauan Media Sosial dan Narasi Politik Multi-Tenant]
  #v(2cm)
  #text(size: 11pt)[Disusun berdasarkan analisis kode sumber repositori]
  #v(0.2cm)
  #text(size: 11pt)[18 Juli 2026]
]

#pagebreak()
#outline(indent: auto)
#pagebreak()

= Pendahuluan

== Latar Belakang

PANTAU adalah platform pemantauan media sosial dan narasi politik yang dibangun di atas Django, ditujukan untuk instansi pemerintah dan organisasi (brand) yang perlu memantau sentimen publik, mendeteksi isu politik, mengelola respons krisis (War Room), dan menghasilkan ringkasan eksekutif harian (Daily Brief) secara terkendali dan dapat diaudit. Sistem dirancang multi-tenant: setiap *Tenant* (misalnya sebuah kementerian atau kabupaten) memiliki satu atau lebih *Project* yang menjadi batas isolasi data.

== Tujuan Dokumen

Dokumen ini memberikan gambaran teknis menyeluruh atas seluruh modul (Django apps) dalam basis kode PANTAU: model data, alur permintaan (views/URL), logika bisnis inti, serta relasi antar modul. Dokumen dilengkapi diagram UML (PlantUML) untuk kelas, ER, komponen, deployment, dan sequence pada alur-alur penting.

== Ruang Lingkup

Dokumentasi mencakup empat modul aplikasi Django:

- `apps.core` -- tenancy, identitas, kontrol akses, halaman publik.
- `apps.analytics` -- konten mention, taksonomi isu, alert, notifikasi, Daily Brief, War Room.
- `apps.governance` -- konfigurasi sumber data, penjadwalan (scheduler), kill switch, rahasia terenkripsi, audit log, korpus regulasi.
- `apps.coordination` -- deteksi Coordinated Inauthentic Behavior (CIB).

Beserta lapisan infrastruktur proyek (`pantau/` -- settings, urls, wsgi, health check) dan topologi deployment (Docker Compose: `web`, `scheduler`, `db`).

== Cara Membaca Diagram PlantUML

Setiap diagram pada dokumen ini dirender sebagai gambar (PNG) dari berkas sumber PlantUML (`.puml`) yang tersimpan pada `docs/diagrams/`. Rendering dilakukan secara lokal menggunakan `plantuml.jar` (tanpa mengirim kode sumber ke layanan pihak ketiga di internet). Sumber `.puml` tetap disertakan di repositori sehingga setiap diagram dapat diperiksa, disunting, dan dirender ulang kapan pun kode berubah -- lihat Lampiran C untuk cara merender ulang.

#pagebreak()

= Arsitektur Sistem

== Gambaran Umum Teknologi

#table(
  columns: (auto, 1fr),
  stroke: 0.5pt + gray,
  [*Komponen*], [*Teknologi*],
  [Framework web], [Django >= 6.0, < 6.1],
  [Bahasa], [Python 3.13 (`python:3.13-slim`)],
  [Basis data], [PostgreSQL 17 (produksi), SQLite (fallback dev jika `DATABASE_URL` tidak diset)],
  [Driver DB], [`psycopg[binary]` >= 3.2],
  [Server aplikasi], [gunicorn >= 23 (sync worker)],
  [Static files], [WhiteNoise (`CompressedManifestStaticFilesStorage`, brotli/gzip)],
  [Enkripsi rahasia], [`cryptography` (Fernet) untuk token Apify dan Runtime Settings],
  [Ekspor data], [`openpyxl` (XLSX)],
)

== Struktur Proyek Django

Paket proyek `pantau/` berisi:

- `settings.py` -- konfigurasi environment-driven, `INSTALLED_APPS` (`apps.core`, `apps.analytics`, `apps.coordination`, `apps.governance`, ditambah app bawaan Django).
- `urls.py` -- root URLConf: `/healthz/`, `/admin/`, `/accounts/` (auth bawaan Django), lalu masing-masing app dipasang di root (`""`) sesuai prefix path miliknya sendiri.
- `wsgi.py` -- entry point gunicorn.
- `env.py` -- parsing environment variable, gagal secara eksplisit (fail loudly) alih-alih diam-diam memakai default tidak aman ketika `DEBUG=False`.
- `health.py` -- `GET /healthz/` memanggil `connection.ensure_connection()` ke Postgres; mengembalikan 503 saat `OperationalError`. Dikecualikan dari `LoginRequiredMiddleware` (`@login_not_required`) dan dari redirect HTTPS (`SECURE_REDIRECT_EXEMPT`).

== Middleware Stack

Urutan middleware (`pantau/settings.py`) beserta rasionalnya:

+ `SecurityMiddleware`
+ `WhiteNoiseMiddleware` -- diletakkan tepat di bawah `SecurityMiddleware` agar respons static tetap mendapat header keamanan, namun di atas session/auth agar permintaan static tidak menanggung beban kerja tersebut.
+ `SessionMiddleware`
+ `CsrfViewMiddleware`
+ `CommonMiddleware`
+ `AuthenticationMiddleware`
+ `MessageMiddleware`
+ `XFrameOptionsMiddleware`
+ `LoginRequiredMiddleware` -- paling akhir; middleware bawaan Django 6 yang membuat *seluruh* view memerlukan login secara default, kecuali ditandai eksplisit `@login_not_required` (dipakai pada `healthz`, `landing`, `onboarding`, `onboarding_success`).

== Konfigurasi Berbasis Environment Variable

#table(
  columns: (auto, 1fr),
  stroke: 0.5pt + gray,
  [*Variabel*], [*Keterangan*],
  [`DJANGO_DEBUG`], [Default `0`. Nilai `False` mewajibkan variabel keamanan lain diisi.],
  [`DJANGO_SECRET_KEY`], [Wajib saat tidak DEBUG; kunci pengembangan bawaan ditolak secara eksplisit.],
  [`DJANGO_ALLOWED_HOSTS`], [Wajib saat tidak DEBUG; nilai `*` ditolak.],
  [`DJANGO_CSRF_TRUSTED_ORIGINS`], [Origin tepercaya untuk proteksi CSRF.],
  [`DJANGO_BEHIND_TLS`], [Default `1`; menandakan aplikasi berada di belakang TLS terminator.],
  [`DATABASE_URL`], [`postgres://user:pass\@host:5432/db`; fallback ke `db.sqlite3` lokal bila kosong.],
  [`DJANGO_EMAIL_BACKEND` dkk.], [Konfigurasi SMTP untuk pengiriman notifikasi alert/brief; default console backend.],
  [`DJANGO_LOG_LEVEL`], [Level logging aplikasi.],
  [`GUNICORN_WORKERS`/`_THREADS`/`_TIMEOUT`/`_LOG_LEVEL`/`_FORWARDED_ALLOW_IPS`], [Tuning gunicorn; `timeout` besar (120s) karena koleksi Apify dan pembuatan brief adalah proses lambat yang blocking.],
  [`RUN_MIGRATIONS`], [Dikontrol `entrypoint.sh`; hanya container `web` menjalankan migrasi.],
  [`SEED_DEMO_DATA`], [Memicu seeding data demo saat startup container.],
)

== Diagram Komponen

#diagram("diagrams/00_component_architecture.png", "Diagram komponen arsitektur sistem PANTAU, menunjukkan modul, alur panggilan lintas-app, dan penyimpanan data.")

== Topologi Deployment

Deployment menggunakan Docker Compose dengan tiga layanan:

- *`db`* -- `postgres:17-alpine`, healthcheck `pg_isready` (bukan sekadar cek port terbuka, karena Postgres menerima koneksi TCP sebelum benar-benar siap melayani).
- *`web`* -- image dari `Dockerfile`, menjalankan `entrypoint.sh` lalu gunicorn (`pantau.wsgi:application`); satu-satunya container yang menjalankan migrasi.
- *`scheduler`* -- image yang sama, override command `python manage.py run_scheduler`; sengaja dipisah dari `web` karena proses koleksi yang memakan waktu beberapa menit tidak boleh membuat worker gunicorn tidak responsif terhadap analis. Menunggu skema database siap (`manage.py migrate --check` di loop `entrypoint.sh`) alih-alih ikut migrasi.

Static files dikumpulkan (`collectstatic`) saat *build time* dengan nilai environment sekali-pakai, lalu dilayani WhiteNoise saat runtime dengan penamaan berbasis hash konten (cache selamanya, aman untuk pre-kompresi brotli/gzip). Image berjalan sebagai pengguna non-root `pantau` (uid 1001). Tidak ada TLS terminator dalam compose -- deployment nyata menempatkan reverse proxy di depan dan mengembalikan `DJANGO_BEHIND_TLS=1`.

#diagram("diagrams/01_deployment.png", "Diagram deployment: kontainer web, scheduler, db, serta layanan eksternal (Apify, situs berita).")

#pagebreak()

= Model Data dan Multi-Tenancy

Seluruh data domain berada dalam hierarki tenant tunggal: `Tenant` -> `Project`. Sebagian besar model pada `apps.analytics` dan `apps.governance` memiliki foreign key langsung ke `core.Project` (`on_delete=CASCADE`). Isolasi lintas-tenant ditegakkan melalui `apps.core.selectors.scope_to_tenant(queryset, request, project_path)`, yang memfilter queryset apa pun berdasarkan `{project_path}__tenant = active_tenant`.

#block(fill: rgb("#fff4e5"), inset: 8pt, radius: 3pt)[
  *Catatan riwayat:* Model `PoliticalIssue` sebelumnya tidak terikat ke `Project`, menyebabkan kebocoran data lintas-tenant. Isu ini telah ditutup (lihat riwayat commit "Scope PoliticalIssue to a project, closing a cross-tenant leak", FR-1.2) dengan menambahkan FK `project` wajib.
]

#diagram("diagrams/11_er_multitenancy_overview.png", "Diagram ER ringkas: bagaimana setiap modul terikat pada Tenant/Project.")

#pagebreak()

= Modul apps.core

== Tujuan dan Tanggung Jawab

`apps.core` adalah fondasi tenancy, identitas, dan kontrol akses platform. Modul ini tidak memiliki "konten" domain sendiri -- setiap modul lain bergantung pada `Tenant`, `Project`, dan `Platform` miliknya. Tanggung jawabnya meliputi: hierarki multi-tenant, profil analis dan peran (role), katalog geografi (provinsi/kabupaten), katalog platform media sosial, matriks izin halaman yang dapat diubah saat runtime, funnel pemasaran/onboarding publik, primitif RBAC (aktivasi pengguna tertunda, penjagaan agar admin terakhir tidak terhapus), dan seeding data demo.

== Model Data

#table(
  columns: (0.8fr, 1.5fr, 1.7fr),
  stroke: 0.5pt + gray,
  [*Model*], [*Field Kunci*], [*Relasi*],
  [#mcell("Tenant")], [`name`], [Akar hierarki multi-tenant.],
  [#mcell("OnboardingRequest")], [`organization_type`, `organization_name`, `contact_name`, `work_email`, `phone`, `role`, `monitoring_goal`, `platforms`, `team_size`, `consent`, `status`, `created_at`], [Berdiri sendiri, tanpa FK -- rekaman lead dari formulir onboarding publik.],
  [#mcell("Project")], [`name`], [FK `tenant` -> `Tenant` (CASCADE, `related_name= projects`).],
  [#mcell("Platform")], [`slug` (unik), `display_name`, `brand_color`, `method` (apify/internal)], [Katalog platform (x, instagram, tiktok, youtube, facebook, berita, forum).],
  [#mcell("Province")], [`name` (unik), `population_online`], [--],
  [#mcell("Regency")], [`name`], [FK `province` -> `Province` (CASCADE, `related_name= regencies`); `unique_together(province, name)`.],
  [#mcell("PagePermission")], [`role`, `page`, `can_access`, `updated_by`, `updated_at`], [`unique_together(role, page)` -- satu sel matriks ACL role x halaman.],
  [#mcell("AnalystProfile")], [`role_label`, `role` (super_admin/tenant_admin/analyst/viewer)], [O2O `user` -> `AUTH_USER_MODEL` (CASCADE); FK `tenant` -> `Tenant` (CASCADE, `related_name= analysts`). Properti `has_political_monitoring_permission` dihitung langsung dari #raw(brk("apps.governance.PoliticalMonitoringPermission")) (tidak diduplikasi).],
)

#diagram("diagrams/02_core_class.png", "Diagram kelas apps.core.")

== Views dan Routing

#table(
  columns: (1fr, 0.9fr, 0.8fr, 1.9fr),
  stroke: 0.5pt + gray,
  [*Path*], [*View*], [*Metode*], [*Keterangan*],
  [`/`], [#mcell("landing")], [GET], [Halaman pemasaran publik; `@login_not_required`; pengguna terautentikasi dialihkan ke `analytics:ringkasan`.],
  [`/mulai/`], [#mcell("onboarding")], [GET/POST], [Formulir onboarding publik (`@login_not_required`); parameter `type` mengisi awal `organization_type`.],
  [`/mulai/berhasil/`], [#mcell("onboarding_success")], [GET], [Halaman konfirmasi statis.],
  [`/profil/`], [#mcell("profile")], [GET], [Profil `AnalystProfile` pengguna aktif (memerlukan login via middleware global).],
)

== Logika Bisnis

- *`permissions.py`* -- matriks ACL role x halaman (FR-1A). Registry `PAGES` berisi 15 slug halaman. `SUPER_ADMIN_ONLY_PAGES = {runtime_settings, permission_matrix}` selalu ditolak untuk non-Super Admin dan tidak dapat diubah lewat matriks. `DASHBOARD_PAGES` diizinkan default untuk analyst/viewer. `can_access(role, page)`: super_admin selalu True -> halaman reserved selalu False untuk non-super-admin -> baris DB eksplisit menang -> fallback default aman (`default_can_access`). Decorator `require_page(page)` melempar `PermissionDenied`.
- *`rbac.py`* -- `create_pending_user()` membuat pengguna nonaktif (FR-1.5) menunggu aktivasi admin (`activate_user()`). `assert_can_delete_user`/`assert_can_deactivate_user` melempar `AdminLockoutError` untuk mencegah penghapusan diri sendiri atau penghapusan Super Admin/Tenant Admin terakhir (FR-1.6).
- *`selectors.py`* -- `get_active_tenant`, `get_active_project`, `visible_projects`, dan `scope_to_tenant` -- mekanisme inti penutup kebocoran lintas-tenant, dipakai di seluruh selector modul lain.
- *`signals.py`* -- `post_save` pada model User otomatis membuat `AnalystProfile` default untuk pengguna baru yang belum memilikinya.
- *`context_processors.py`* -- `tenant_context` menyuntikkan `instansi`, `proyek`, `analyst_profile`, `can_view_feed`, `can_view_taxonomy` ke seluruh konteks template.
- *`seed.py`* -- fixture demo generik: tenant "Kemenko PMK", project "Program Pangan Rakyat", 7 platform, 12 provinsi, satu pengguna Super Admin demo, seed matriks izin penuh.
- *`demo_kulon_progo.py`* -- fixture kedua yang lebih kaya dan idempoten: tenant terpisah "Kabupaten Kulon Progo", menyeed `apps.governance` (domain terpantau, kata kunci, integrasi platform, izin monitoring politik, pengakuan kebijakan, log audit, jadwal), taksonomi `apps.analytics` (Category/SubCategory/Issue), aktor politik dan program pemerintah, 26 mention berita terkurasi + 220 mention buzz sosial acak-deterministik + 38 mention insiden layanan publik + 96 mention perbandingan narasi, satu `PoliticalIssue` dengan `Alert`/`AlertRule` terkait, contoh `CoordinationCluster`, visual bukti insiden berlabel simulasi AI, serta `DailyBrief` yang dapat ditinjau. Seluruh mention fiktif tidak memiliki tautan sumber eksternal agar antarmuka tidak mengarahkan pengguna ke URL palsu. Modul ini adalah kode paling terintegrasi lintas-app dalam basis kode (menyentuh keempat app secara langsung).

#pagebreak()

= Modul apps.analytics

== Tujuan dan Tanggung Jawab

`apps.analytics` adalah lapisan intelijen inti platform: penyimpanan mention mentah, pengayaan sentimen/emosi beserta koreksi manual, taksonomi isu tiga tingkat, pelacakan aktor politik/koalisi/kubu, evaluasi aturan alert dan pengiriman notifikasi multi-kanal, normalisasi dan skor pengaruh penulis (author), War Room (linimasa respons isu aktif), tampilan analitik naratif/regional/sosiograf, pusat laporan, serta alur Daily Brief berbantuan AI (draft -> tinjau -> finalisasi/kunci).

== Model Data -- Konten, Taksonomi, dan Aktor

#table(
  columns: (0.8fr, 1.5fr, 1.7fr),
  stroke: 0.5pt + gray,
  [*Model*], [*Field Kunci*], [*Relasi*],
  [#mcell("Coalition")], [`name`, `slug` (unik), `stance` (petahana/penantang), `color`], [--],
  [#mcell("PoliticalIssue")], [`title`, `status` (active/closed), `opened_at`, `owner_label`], [FK `project` -> `Project` (CASCADE, `related_name= political_issues`).],
  [#mcell("Author")], [`handle`, `display_name`, `follower_count`, `influence_score` (Decimal 6,2)], [FK `platform` -> `Platform` (CASCADE); `unique_together(platform, handle)`.],
  [`Mention` (tabel fakta pusat)], [`author_handle`, `external_id` (unik, null), `content_snippet`, `theme`, `sentiment`, `sentiment_confidence`, `sentiment_model`, `emotion` (8 pilihan Plutchik), `emotion_labels` (JSON), `posted_at` (indexed), `engagement_count`, `reach_estimate`, `is_political` (indexed), `source_url` (unik, null), `matched_keyword`, `is_scraped`], [FK `project` (CASCADE), `platform` (PROTECT), `province`/`regency` (SET_NULL), `author` (SET_NULL), `coalition` (SET_NULL), `issue` -> PoliticalIssue (SET_NULL), `program` -> GovernmentProgram (SET_NULL); M2M `political_actors`.],
  [#mcell("LabelCorrection")], [`field` (sentiment/emotion), `old_value`, `new_value`, `corrected_by`, `corrected_at`], [FK `mention` -> `Mention` (CASCADE, `related_name= corrections`).],
  [#mcell("Category")], [`name` (unik), `is_active`], [--],
  [#mcell("SubCategory")], [`name`, `is_active`], [FK `category` (CASCADE, `related_name= subcategories`); `unique_together(category, name)`.],
  [#mcell("Issue")], [`name`, `keywords` (JSON), `is_active`], [FK `subcategory` (CASCADE, `related_name= issues`).],
  [#mcell("IssueLabel")], [`source` (auto/manual), `decided_by`, `decided_at`], [O2O `mention` -> `Mention` (CASCADE, `related_name= issue_label`); FK `issue` (CASCADE, `related_name= labels`).],
  [#mcell("IssueMergeHistory")], [`source_issue_ids` (JSON), `moved` (JSON), `performed_by`, `performed_at`, `reversed_at` (null)], [FK `target_issue` -> `Issue` (CASCADE, `related_name= merges_in`).],
  [#mcell("Camp")], [`name`, `color` (default `#7C8A99`), `is_user_defined`], [FK `project` (CASCADE, `related_name= camps`); `unique_together(project, name)`.],
  [#mcell("PoliticalActor")], [`name`, `actor_type` (party/coalition/official/organization), `keywords` (JSON), `handles` (JSON), `is_active`], [FK `project` (CASCADE); FK `camp` -> `Camp` (SET_NULL).],
  [#mcell("GovernmentProgram")], [`name`, `agency`, `keywords` (JSON), `is_active`], [FK `project` (CASCADE).],
  [#mcell("ResponseAction")], [`action_type` (statement/clarification/briefing/escalation/other), `description`, `logged_by`, `occurred_at`], [FK `issue` -> `PoliticalIssue` (CASCADE, `related_name= response_actions`).],
)

#diagram("diagrams/03_analytics_class_content.png", "Diagram kelas apps.analytics -- konten mention, taksonomi, dan aktor.")

== Model Data -- Alert, Notifikasi, dan Daily Brief

#table(
  columns: (0.8fr, 1.5fr, 1.7fr),
  stroke: 0.5pt + gray,
  [*Model*], [*Field Kunci*], [*Relasi*],
  [#mcell("AlertRule")], [`name`, `condition_summary`, `channel` (email/push/webhook), `condition_type` (negative_ratio/volume_spike), `threshold`, `window_minutes`, `is_active`], [FK `project` (CASCADE, `related_name= alert_rules`).],
  [#mcell("Alert")], [`severity` (info/warning/critical), `title`, `detail`, `triggered_at`, `status` (active/resolved)], [FK `project` (CASCADE); FK `rule` -> `AlertRule` (CASCADE, `related_name= alerts`); FK `issue` (SET_NULL).],
  [#mcell("NotificationDelivery")], [`kind` (alert/brief), `channel`, `subject`, `recipients` (JSON), `status` (sent/failed/skipped), `detail`, `created_at`], [FK `project` (CASCADE, `related_name= notification_deliveries`); FK `alert` (CASCADE, null); FK `brief` (CASCADE, null).],
  [#mcell("DailyBrief")], [`brief_date`, `status` (pending/generating/draft/final/failed), `finalized_by`, `finalized_at`, `created_at`], [FK `project` (CASCADE, `related_name= briefs`); `unique_together(project, brief_date)`. Properti `is_locked` = `status == FINAL`.],
  [#mcell("DailyBriefIssue")], [`title`, `content`, `preview_summary`, `risk_level` (default "low"), `order`, `approved`, `edited_by`, `regulatory_context` (JSON), `mention_count`, `negative_pct`], [FK `brief` -> `DailyBrief` (CASCADE, `related_name= issues`).],
  [#mcell("DailyBriefRun")], [`triggered_by`, `started_at`, `completed_at`, `succeeded`, `detail`], [FK `brief` -> `DailyBrief` (CASCADE, `related_name= runs`).],
)

#diagram("diagrams/04_analytics_class_brief_alert.png", "Diagram kelas apps.analytics -- AlertRule, Alert, NotificationDelivery, DailyBrief.")

== Views dan Routing

`app_name = "analytics"`.

#table(
  columns: (1fr, 0.9fr, 0.8fr, 1.9fr),
  stroke: 0.5pt + gray,
  [*Path*], [*View*], [*Gerbang Izin*], [*Keterangan*],
  [`ringkasan/`], [#mcell("ringkasan")], [--], [Dasbor ringkasan + alert terbaru.],
  [`umpan/`], [#mcell("feed")], [#mcell("feed")], [Umpan mention dengan filter (platform/sentimen/penulis), paginasi 25.],
  [`umpan/<id>/koreksi-sentimen/`], [#mcell("correct_sentiment")], [#mcell("feed")], [POST -- override sentimen manual, menulis `LabelCorrection`.],
  [`war-room/`], [#mcell("war_room")], [--], [Dasbor War Room untuk isu politik aktif.],
  [`war-room/<issue_id>/aksi/`], [#mcell("log_response")], [--], [POST -- mencatat `ResponseAction` + entri audit.],
  [`narasi/`], [#mcell("narasi")], [#mcell("require_political_monitoring")], [Perbandingan narasi antar kubu/koalisi; menampilkan notifikasi netralitas.],
  [`regional/`], [#mcell("regional")], [--], [Heatmap/tren tingkat provinsi.],
  [`sosiograf/`], [#mcell("sosiograf")], [#mcell("sosiograf")], [Graf interaksi akun berpengaruh (render sisi server).],
  [`laporan/`], [#mcell("laporan")], [#mcell("laporan")], [Pusat laporan: arsip brief final + rekap periodik (7-90 hari).],
  [`ekspor/mention/`], [#mcell("export_mentions")], [#mcell("export")], [Ekspor CSV/XLSX streaming, batas baris dari Runtime Setting.],
  [`brief/`], [#mcell("brief_view")], [#mcell("brief")], [Ruang kerja tinjauan Daily Brief.],
  [`brief/buat/`], [#mcell("generate_brief")], [#mcell("brief")], [POST -- memicu `briefs.generate()`.],
  [`brief/<id>/cetak/`], [#mcell("brief_print")], [#mcell("brief")], [Render siap cetak + entri audit.],
  [`brief/isu/<issue_id>/tinjau/`], [#mcell("review_brief_issue")], [#mcell("brief")], [POST -- simpan/approve `DailyBriefIssue`.],
  [`brief/<id>/finalisasi/`], [#mcell("finalize_brief")], [#mcell("brief")], [POST -- mengunci brief via `briefs.finalize()`.],
  [`taksonomi/`], [#mcell("taxonomy_view")], [#mcell("taxonomy")], [Antrean tinjauan + riwayat penggabungan isu.],
  [`taksonomi/<mention_id>/label/`], [#mcell("assign_issue")], [#mcell("taxonomy")], [POST -- label isu manual.],
  [`taksonomi/gabung/`], [#mcell("merge_issues")], [#mcell("taxonomy")], [POST -- gabungkan beberapa isu (reversibel).],
  [`taksonomi/gabung/<history_id>/batal/`], [#mcell("unmerge_issues")], [#mcell("taxonomy")], [POST -- membatalkan penggabungan.],
)

== Logika Bisnis

=== Alerting (`alerting.py`)

`evaluate_rules(project, issue=None)` mengiterasi `AlertRule` aktif; `_evaluate` membangun queryset jendela waktu (`window_minutes`). Untuk `negative_ratio`: rasio negatif/total dibandingkan ambang (severity *critical* jika >= 0.8, selain itu *warning*). Untuk `volume_spike`: jumlah mentah dibandingkan ambang. Dedup: jika sudah ada `Alert` aktif untuk rule yang sama, evaluasi dilewati. Saat ambang terlampaui: buat `Alert`, lalu panggil `notifications.deliver_alert(alert)` (impor lambat/lazy untuk menghindari siklus impor).

=== Notifikasi (`notifications.py`)

`deliver_alert(alert)` bercabang berdasarkan `alert.rule.channel`: *email* -> `recipient_emails` (email `AnalystProfile.user` pada tenant) -> `_send_email` (`send_mail` Django, exception ditangkap -> status FAILED); *webhook* -> `_send_webhook` membaca Runtime Setting `alerts.webhook_url`, POST JSON via `urllib` (timeout 10 detik), SKIPPED bila belum diset; *push* -> selalu SKIPPED (belum ada integrasi). Setiap jalur memanggil `_record(...)` untuk menulis `NotificationDelivery`. Tidak pernah melempar exception (semua ditangkap dan dicatat). `send_brief(brief)` menjaga `brief.status == FINAL` (jika tidak, SKIPPED), menyusun isi dari `brief.issues.all()`. `brief_already_sent(brief)` memeriksa `NotificationDelivery` SENT yang sudah ada untuk menjamin pengiriman *exactly-once*.

=== Author (`authors.py`)

`link_authors(project)` -- untuk mention tanpa `author` namun memiliki `author_handle`, melakukan `get_or_create` `Author` per (platform, handle). `influence_score(reach, engagement, mention_count)` = kombinasi log10 berbobot (`REACH_WEIGHT=12`, `ENGAGEMENT_WEIGHT=8`, `MENTION_WEIGHT=2`) -- diskalakan logaritmik agar akun viral tidak mendominasi skor. `recompute_influence(project)` mengagregasi reach/engagement/jumlah mention per penulis dan melakukan bulk update. `enrich(project)` adalah titik masuk terjadwal yang memanggil keduanya.

=== Taksonomi (`taxonomy.py`)

`match_issue(text)` -- isu aktif pertama yang kata kuncinya cocok (substring, tanpa memandang huruf besar/kecil). `auto_label(mention)` membuat/memperbarui `IssueLabel` kecuali sudah ada label manual (manual selalu menang). `merge_issues(source_ids, target_id, performed_by)` -- secara atomik memindahkan seluruh `IssueLabel` dari isu sumber ke target, menonaktifkan sumber, mencatat `IssueMergeHistory.moved` untuk keperluan pembatalan. `unmerge(history)` mengaktifkan kembali isu sumber dan mengembalikan label.

=== Mesin Daily Brief (`briefs.py`)

`generate(project, brief_date, triggered_by)` -> `_claim` (atomik, `select_for_update`, `get_or_create`; melempar `BriefLocked` bila sudah FINAL, `BriefAlreadyGenerating` bila sedang GENERATING) -> membuat `DailyBriefRun` -> `_shortlist` (mengelompokkan `IssueLabel` per isu untuk tanggal tersebut, filter `MIN_MENTIONS=3`/`MIN_NEGATIVE_PCT=40%`, batas `MAX_ISSUES_PER_BRIEF=8`) -> per isu: `_grounding_query` (10 cuplikan teratas berdasarkan engagement + kata kunci isu) -> `apps.governance.regulatory.retrieve(query, limit=2)` (panggilan lintas-app) -> `regulatory.classify_risk(...)` -> `_compose` (template deterministik dengan `DRAFT_BANNER`, selalu mewajibkan tinjauan manusia) -> membuat `DailyBriefIssue`. Sukses: `brief.status=DRAFT`; gagal: `status=FAILED`, dicatat pada run, exception dilempar ulang. Alur tinjauan: `edit_issue`/`approve_issue` (diblokir jika `is_locked`, melempar `BriefLocked`) -> `finalize(brief, finalized_by)` (melempar `BriefNotReviewed` jika ada isu belum di-approve; jika lolos, mengunci: `status=FINAL`, `finalized_by`/`finalized_at` diisi).

=== Selectors (`selectors.py`)

Kumpulan fungsi baca murni (tanpa efek samping) untuk agregasi dasbor: `ringkasan_summary`, `timeline_chart`, `recent_alerts`, `war_room_summary`, `narasi_summary`, `regional_summary`, `sosiograf_summary`, `laporan_summary`.

== Diagram Sequence

#diagram("diagrams/07_sequence_alerting.png", "Sequence: evaluasi aturan alert hingga pengiriman notifikasi.")

#diagram("diagrams/08_sequence_brief_generation.png", "Sequence: pembuatan Daily Brief hingga tinjauan dan finalisasi.")

#pagebreak()

= Modul apps.governance

== Tujuan dan Tanggung Jawab

`apps.governance` adalah *control plane* platform: konfigurasi sumber per-project (kata kunci, domain, integrasi platform, kredensial Apify), scheduler berbasis kadensa dan job runner-nya, kill switch koleksi data, Runtime Settings terenkripsi, matriks izin halaman, log audit, korpus dokumen regulasi, dan pengakuan kebijakan (policy acknowledgment). Modul ini juga menghosting form/view CRUD untuk objek taksonomi konten (`AlertRule`, `Camp`, `PoliticalActor`, `GovernmentProgram`) yang model-nya sebenarnya berada di `apps.analytics` -- governance memiliki UI konfigurasinya, analytics memiliki skemanya.

== Model Data

Kelas dasar abstrak `ProjectOwnedModel` (`project` FK -> `core.Project`, CASCADE) diturunkan oleh `PlatformIntegration`, `ApifyCredential`, `MonitoredDomain`, `MonitoringKeyword`, `CollectionRun`, `ManualCollectionRequest`.

#table(
  columns: (0.8fr, 1.5fr, 1.7fr),
  stroke: 0.5pt + gray,
  [*Model*], [*Field Kunci*], [*Relasi / Meta*],
  [#mcell("PlatformIntegration")], [`method` (apify/internal), `actor_id`, `is_active`, `status_note`], [FK `platform` -> `core.Platform` (CASCADE, `related_name= integrations`); `UniqueConstraint(project, platform)`.],
  [#mcell("ApifyCredential")], [`masked_token`, `token_encrypted` (Fernet), `status` (active/invalid/revoked), `last_verified_at`], [--],
  [#mcell("RuntimeSetting")], [`key` (unik), `value`, `is_secret`, `scope` (default "platform"), `updated_by`, `updated_at`], [Tidak terikat project -- berlaku platform-global.],
  [#mcell("MonitoredDomain")], [`domain`, `adapter`, `status` (active/needs_review/inactive), `last_tested_at`, `feed_url`], [`UniqueConstraint(project, domain)`.],
  [#mcell("MonitoringKeyword")], [`keyword`, `is_active`, `match_count`, `created_at`, `created_by`], [`UniqueConstraint(project, keyword)`.],
  [#mcell("PoliticalMonitoringPermission")], [`approved_by`, `approved_at`, `active`, `revoked_at`], [FK `user` -> `AUTH_USER_MODEL` (CASCADE, `related_name= political_monitoring_permissions`).],
  [#mcell("AuditLogEntry")], [`timestamp`, `actor_label`, `action`, `target`], [Manager `ImmutableAuditLogQuerySet` -- `update()`/`delete()` melempar `ValidationError`; append-only.],
  [#mcell("RegulatoryDocument")], [`title`, `source_ref`, `body`, `indexed_at`, `retired_at`], [Properti `is_active` = `retired_at is None`.],
  [#mcell("CollectionRun")], [`source`, `status` (running/completed/failed/skipped), `keywords_count`, `items_found`, `cost_estimate` (Decimal 10,4), `error`, `started_at`, `finished_at`], [--],
  [#mcell("ManualCollectionRequest")], [`collection_type` (social/news), `status` (queued/running/completed/failed/skipped, indexed), `requested_by`, `requested_at`, `started_at`, `finished_at`, `items_found`, `sources_processed`, `detail`], [Index `(status, requested_at)`; baris antrean tahan-lama agar request web tidak menunggu proses crawling.],
  [#mcell("ScheduledJob")], [`job_type` (collect/evaluate_alerts/detect_coordination/generate_brief/purge_retention/enrich_authors/send_brief), `cadence_minutes` (default 60), `enabled`, `next_run_at` (indexed), `last_run_at`, `last_status`, `last_error`, `last_detail`, `consecutive_failures`], [FK `project` (CASCADE, `related_name= scheduled_jobs`); `unique_together(project, job_type)` -- satu baris per pasangan (project, job_type).],
  [#mcell("PolicyAcknowledgment")], [`approved_by`, `approved_at`, `next_review_at`], [FK `tenant` -> `core.Tenant` (CASCADE, `related_name= policy_acknowledgments`).],
)

#diagram("diagrams/05_governance_class.png", "Diagram kelas apps.governance.")

== Views dan Routing

`app_name = "governance"`. Sebagian besar view mutating menggunakan `@require_POST` + `@transaction.atomic`, seluruhnya digerbangi `@require_page(slug)`.

#table(
  columns: (1fr, 0.9fr, 0.8fr, 1.9fr),
  stroke: 0.5pt + gray,
  [*Path*], [*View*], [*Gerbang*], [*Keterangan*],
  [`konfigurasi/`], [#mcell("konfigurasi")], [#mcell("konfigurasi")], [Konsol konfigurasi utama (kata kunci, domain, integrasi, jadwal, aturan alert, kubu, aktor, program).],
  [`konfigurasi/apify/simpan\|cabut/`], [#raw(brk("save_project_apify_token/revoke_project_apify_token"))], [#mcell("konfigurasi")], [Token Apify per-project, dienkripsi via `crypto.encrypt`.],
  [`konfigurasi/kata-kunci/...`], [#raw(brk("add_keyword/toggle_keyword/delete_keyword"))], [#mcell("konfigurasi")], [CRUD kata kunci pemantauan.],
  [`konfigurasi/domain/...`], [#raw(brk("add_domain/delete_domain/test_domain_connection"))], [#mcell("konfigurasi")], [CRUD domain terpantau + uji koneksi.],
  [`konfigurasi/integrasi/<pk>/toggle/`], [#mcell("toggle_integration")], [#mcell("konfigurasi")], [Aktif/nonaktifkan integrasi platform.],
  [`konfigurasi/pindai/`], [#mcell("queue_news_collection")], [#mcell("konfigurasi")], [Antre `ManualCollectionRequest` (berita).],
  [`konfigurasi/koleksi/social-media/`], [#mcell("queue_social_collection")], [#mcell("konfigurasi")], [Antre permintaan koleksi sosial.],
  [`konfigurasi/koleksi/status/<pk>/`], [#mcell("collection_request_status")], [#mcell("konfigurasi")], [GET -- polling status permintaan.],
  [`konfigurasi/jadwal/<job_id>/ubah/`], [#mcell("update_schedule")], [#mcell("konfigurasi")], [Ubah `cadence_minutes`/`enabled` pada `ScheduledJob`.],
  [`konfigurasi/koleksi/toggle/`], [#mcell("toggle_collection")], [#mcell("konfigurasi")], [*Kill switch* koleksi data.],
  [`konfigurasi/peringatan/...`], [#raw(brk("add_alert_rule/toggle_alert_rule/delete_alert_rule"))], [#mcell("konfigurasi")], [CRUD `analytics.AlertRule`.],
  [`konfigurasi/kubu/...`], [#raw(brk("add_camp/delete_camp"))], [#mcell("konfigurasi")], [CRUD `analytics.Camp`.],
  [`konfigurasi/aktor/...`], [#raw(brk("add_actor/toggle_actor"))], [#mcell("konfigurasi")], [CRUD `analytics.PoliticalActor`.],
  [`konfigurasi/program/...`], [#raw(brk("add_program/delete_program"))], [#mcell("konfigurasi")], [CRUD `analytics.GovernmentProgram`.],
  [`pengawasan/`], [#mcell("pengawasan")], [#mcell("pengawasan")], [Dasbor pengawasan/oversight.],
  [`konfigurasi/izin/`], [#mcell("permission_matrix")], [#mcell("permission_matrix")], [Editor matriks izin role x halaman.],
  [`konfigurasi/izin/ubah/`], [#mcell("toggle_permission")], [#mcell("permission_matrix")], [POST -- ubah satu sel matriks.],
  [`dev-ops/`], [#mcell("runtime_settings")], [#mcell("runtime_settings")], [Konsol Dev/Ops khusus Super Admin.],
  [`dev-ops/apify/...`], [#raw(brk("save_apify_token/revoke_apify_token"))], [#mcell("runtime_settings")], [Token Apify tingkat platform.],
  [`dev-ops/setting/simpan/`], [#mcell("save_runtime_setting")], [#mcell("runtime_settings")], [Tulis `RuntimeSetting`.],
)

== Logika Bisnis

=== Penjadwalan (`scheduling.py`)

Loop berbasis database, tanpa broker/Celery -- mengandalkan `SELECT ... FOR UPDATE SKIP LOCKED` Postgres untuk keamanan multi-replika. `due_jobs(now)` mengambil job dengan `enabled=True, next_run_at <= now`. `run_due()`: untuk setiap job yang jatuh tempo, transaksi atomik memilih ulang dengan `select_for_update(skip_locked=True)`, memanggil `run_job(job)`. `run_job` mendispatch via dict `HANDLERS` berdasarkan `job_type`:

- `_run_collect` -- memanggil `apify.get_active_token` + `orchestrator.run_apify_collection`/`run_news_collection`.
- `_run_evaluate_alerts` -- `apps.analytics.alerting.evaluate_rules`.
- `_run_detect_coordination` -- mengiterasi `analytics.PoliticalIssue` aktif per project -> `apps.coordination.detection.detect`.
- `_run_generate_brief` -- `apps.analytics.briefs.generate` (selalu menghasilkan draft).
- `_run_purge_retention` -- `retention.purge`.
- `_run_enrich_authors` -- `apps.analytics.authors.enrich`.
- `_run_send_brief` -- `apps.analytics.notifications.send_brief` (exactly-once via `brief_already_sent`).

Exception ditangkap per-job (tidak pernah merusak loop utama); `consecutive_failures` mendorong backoff eksponensial (`BACKOFF_FACTOR=2`, dibatasi `MAX_BACKOFF_MINUTES=60`). `_reschedule` selalu menghitung `next_run_at` dari waktu sekarang, tidak pernah menumpuk (backfill) jendela yang terlewat -- mencegah *stampede*.

=== Kill Switch

`collection_enabled()`/`set_collection_enabled()`, didukung `RuntimeSetting` dengan key `collection.enabled` (default aktif). Diperiksa baik pada eksekusi permintaan manual maupun pada `run_job` untuk job dalam `COLLECTION_JOBS = {collect}` -- evaluasi alert/pembuatan brief tetap berjalan atas data yang sudah ada selama koleksi dipadamkan. Diberlakukan pada satu titik tunggal `orchestrator.run_apify_collection` (bukan di scheduler), sehingga `manage.py collect`, tombol "Pindai" di konsol, dan scheduler semuanya patuh secara seragam (REQ-LC-03). Setiap perubahan kill switch dicatat via `services.record_audit_entry`.

=== Antrean Koleksi Manual

`queue_news_collection`/`queue_social_collection` membuat baris `ManualCollectionRequest` (status=queued) secara sinkron dalam request web; `run_pending_manual_collections(limit)` (dijalankan proses scheduler terpisah) mengklaim baris dengan `select_for_update(skip_locked=True)`, mengeksekusi `_execute_manual_collection`, menulis kembali status/detail/items_found -- UI melakukan polling ke `collection_request_status`.

=== Kripto (`crypto.py`)

Kunci Fernet diturunkan via `sha256(SECRET_KEY)` -> urlsafe-b64 -> `Fernet`. `encrypt`/`decrypt` dipakai untuk `ApifyCredential.token_encrypted` dan `RuntimeSetting.value` yang bertanda rahasia. `mask(value, visible=4)` menampilkan `"••••••••" + 4 karakter terakhir` -- nilai terenkripsi asli tidak pernah dirender ke UI.

=== Koleksi Data / Crawler

`orchestrator.py` (`run_apify_collection`) mengedarkan `MonitoringKeyword` aktif ke setiap `PlatformIntegration` aktif, memanggil `apify_crawler.collect(...)`, lalu `ingestion.ingest_items(project, platform, items)`, mencatat setiap upaya sebagai `CollectionRun`. Biaya per-run diestimasi lewat tabel `PRICING_PER_1000` per platform. Overlap-skip: platform/sumber yang sudah `STATUS_RUNNING` untuk project yang sama dilewati, tidak dijalankan ganda (REQ-SC-05). `portal_crawler.py`/`scraping.py` mengimplementasikan "respectful news crawler" untuk situs berita -- terpisah dari koleksi Apify berbasis platform sosial. Koleksi *nonaktif secara default* -- memerlukan Super Admin memasukkan token Apify lewat halaman Dev/Ops sebelum aktif.

=== Seed (`seed.py`)

`seed_schedules(project)` membuat baris `ScheduledJob` default per job type; `seed_governance(tenant)` menyeed kata kunci/domain/integrasi/kredensial/izin demo untuk project sebuah tenant; `seed_regulatory_corpus()` memuat baris `RegulatoryDocument` dasar.

== Diagram Sequence

#diagram("diagrams/09_sequence_collection_scheduling.png", "Sequence: scheduler, kill switch, dan alur koleksi data terjadwal.")

#pagebreak()

= Modul apps.coordination

== Tujuan dan Tanggung Jawab

`apps.coordination` mendeteksi Coordinated Inauthentic Behavior (CIB) (FR-26): klaster akun yang memposting konten hampir identik dalam ledakan waktu yang tersinkron di sekitar sebuah `PoliticalIssue` (dimiliki `apps.analytics`), memberi skor, dan menyimpannya *hanya* sebagai tanda untuk ditinjau analis manusia -- sistem tidak pernah menindak akun secara otomatis (FR-26.2).

== Model Data

#table(
  columns: (0.8fr, 1.5fr, 1.7fr),
  stroke: 0.5pt + gray,
  [*Model*], [*Field Kunci*], [*Relasi*],
  [#mcell("CoordinationCluster")], [`cluster_code` (unik, format `Klaster-NN`), `score` (Decimal 3,2), `status` (flagged/reviewed_organic/ignored), `account_count`, `detected_at`, `note`], [FK `issue` -> `analytics.PoliticalIssue` (CASCADE, `related_name= coordination_clusters`); `ordering=["-score"]`.],
  [#mcell("ClusterAccount")], [`handle`, `role` (hub/amplifier/satellite), `reach`, `post_count`], [FK `cluster` (CASCADE, `related_name= accounts`).],
  [#mcell("CoordinationSignal")], [`signal_type` (text_similarity/time_sync/account_age/shared_media), `score` (Decimal 3,2)], [FK `cluster` (CASCADE, `related_name= signals`).],
  [#mcell("DuplicateTextSample")], [`account_handle`, `posted_at`, `text`, `highlighted_phrase`], [FK `cluster` (CASCADE, `related_name= duplicate_samples`).],
)

#diagram("diagrams/06_coordination_class.png", "Diagram kelas apps.coordination.")

== Views dan Routing

#table(
  columns: (1fr, 0.9fr, 0.8fr, 1.9fr),
  stroke: 0.5pt + gray,
  [*Path*], [*View*], [*Metode*], [*Keterangan*],
  [`koordinasi/`], [#mcell("koordinasi")], [GET], [Daftar `CoordinationCluster` (select_related `issue`, prefetch akun/sinyal/sampel); parameter `?cluster=<code>` memilih satu klaster.],
  [`koordinasi/<cluster_code>/eskalasi/`], [#mcell("escalate_cluster")], [POST], [Atomik -- mencatat entri audit, tidak mengubah status klaster.],
  [`koordinasi/<cluster_code>/tandai-organik/`], [#mcell("mark_cluster_organic")], [POST], [Atomik -- set `status=REVIEWED_ORGANIC`, mencatat audit.],
)

== Algoritma Deteksi (`detection.py`)

`detect(project, issue, threshold=0.6, since=None)`:

+ Mengambil `Mention` untuk project/issue tertentu.
+ Mengelompokkan near-duplicate via kemiripan token Jaccard (`text_similarity`, ambang 0.6).
+ Mewajibkan minimal 2 `author_handle` berbeda per klaster kandidat (satu akun yang mengulang diri sendiri bukan "koordinasi").
+ Menghitung skor komposit berbobot: $0.45 times "text_similarity" + 0.35 times "time_sync" + 0.20 times "shared_media"$. `time_sync_score` dihitung dari selisih median dalam jendela sinkron 300 detik; `_shared_media_score` dari rasio `source_url` yang sama.
+ Menyimpan klaster di atas ambang sebagai `STATUS_FLAGGED`, dengan `ClusterAccount` (role=amplifier untuk semua), `CoordinationSignal` per jenis sinyal berbobot, dan hingga 5 `DuplicateTextSample` (frasa bersama terpanjang disorot).
+ Kode klaster auto-increment format `Klaster-NN`.

== Diagram Sequence

#diagram("diagrams/10_sequence_coordination_detection.png", "Sequence: deteksi CIB terjadwal hingga tinjauan analis.")

#pagebreak()

= Hubungan Antar Modul

#table(
  columns: (0.8fr, 1.5fr, 1.7fr),
  stroke: 0.5pt + gray,
  [*Dari*], [*Ke*], [*Bentuk Ketergantungan*],
  [`core`], [`governance`], [#raw(brk("AnalystProfile.has_political_monitoring_permission")) membaca #raw(brk("governance.PoliticalMonitoringPermission")) secara langsung (tidak diduplikasi).],
  [`analytics`], [`governance`], [`views.py` mengimpor `regulatory` (label risiko brief), #raw(brk("neutrality.require_political_monitoring")), `services.record_audit_entry`; `briefs.py` memanggil #raw(brk("regulatory.retrieve"))/`classify_risk`; #raw(brk("notifications._send_webhook")) dan #raw(brk("views._export_max_rows")) membaca #raw(brk("governance.runtime.get_setting")).],
  [`governance`], [`analytics`], [`forms.py` membangun `ModelForm` untuk `AlertRule`/`Camp`/`PoliticalActor`/`GovernmentProgram` (model analytics, UI governance); `scheduling.py` memanggil `alerting`, `briefs`, `authors`, `notifications`, `PoliticalIssue` secara lazy-import saat runtime job.],
  [`governance`], [`coordination`], [`scheduling._run_detect_coordination` memanggil `coordination.detection.detect`.],
  [`coordination`], [`analytics`], [`CoordinationCluster.issue` adalah FK wajib ke `PoliticalIssue`; `detection.py` membaca `Mention`.],
  [`coordination`], [`governance`], [`views.py` memanggil `services.record_audit_entry`.],
  [Semua modul], [`core`], [Hampir seluruh model lain memiliki FK langsung/tidak langsung ke `core.Project`/`core.Tenant`; `permissions.require_page` dan `selectors.scope_to_tenant` (keduanya di `core`) dipakai di seluruh view app lain.],
)

`apps.core.demo_kulon_progo` adalah satu-satunya modul yang menyentuh keempat app secara langsung dalam satu alur seeding -- kandidat baik untuk memahami urutan integrasi lintas modul secara konkret.

#pagebreak()

= Keamanan dan Catatan Operasional

- *Isolasi tenant*: ditegakkan lewat `scope_to_tenant` di `apps.core.selectors`; riwayat perbaikan kebocoran lintas-tenant pada `PoliticalIssue` menjadi pengingat pentingnya FK `project` eksplisit pada setiap model domain baru.
- *Kontrol akses berbasis halaman*: `apps.core.permissions` -- `SUPER_ADMIN_ONLY_PAGES` tidak dapat diturunkan lewat matriks UI, mencegah eskalasi privilege tidak sengaja.
- *Rahasia terenkripsi*: token Apify dan Runtime Setting bertanda rahasia dienkripsi Fernet (`apps.governance.crypto`), kunci diturunkan dari `SECRET_KEY`; nilai hanya ditampilkan dalam bentuk masked (`mask()`), tidak pernah plaintext ke UI.
- *Log audit tidak dapat diubah*: `AuditLogEntry` memakai manager kustom yang memblokir `update()`/`delete()` -- append-only by design.
- *Kill switch koleksi*: satu titik pemeriksaan (`orchestrator.run_apify_collection`) memastikan seluruh jalur pemicu koleksi (CLI, tombol UI, scheduler) patuh secara konsisten.
- *Retensi data*: `manage.py purge_retention` bersifat dry-run secara default (`--apply` untuk eksekusi); mention yang tergabung dalam klaster koordinasi yang masih terbuka/ditandai tidak pernah dihapus retensi (ketergantungan lintas-app: retensi governance menghormati status klaster coordination).
- *Catatan repositori*: berkas `docs/malaria vps.txt` yang ditemukan selama audit berisi kredensial SSH root aktif dalam bentuk plaintext. Kredensial semacam ini tidak boleh disimpan dalam repositori kode maupun dokumentasi -- direkomendasikan untuk segera dihapus dari riwayat git dan dirotasi (diganti) di server terkait. Detail kredensial secara sengaja *tidak* disertakan dalam dokumen ini.

#pagebreak()

= Lampiran

== A. Ringkasan Halaman Bergerbang Izin (`PAGES` registry)

Terdapat 15 slug halaman yang diketahui dari analisis modul, dengan halaman berikut secara eksplisit hanya dapat diakses Super Admin dan tidak dapat diubah lewat matriks UI: `runtime_settings`, `permission_matrix`. Halaman lain yang teridentifikasi melalui gerbang `@require_page` pada view: `feed`, `sosiograf`, `laporan`, `export`, `brief`, `taxonomy`, `konfigurasi`, `pengawasan`.

== B. Daftar Berkas Diagram PlantUML

#table(
  columns: (auto, 1fr),
  stroke: 0.5pt + gray,
  [*Berkas*], [*Isi*],
  [`00_component_architecture.puml`], [Diagram komponen sistem keseluruhan.],
  [`01_deployment.puml`], [Diagram deployment Docker Compose.],
  [`02_core_class.puml`], [Diagram kelas apps.core.],
  [`03_analytics_class_content.puml`], [Diagram kelas apps.analytics (konten/taksonomi/aktor).],
  [`04_analytics_class_brief_alert.puml`], [Diagram kelas apps.analytics (alert/notifikasi/brief).],
  [`05_governance_class.puml`], [Diagram kelas apps.governance.],
  [`06_coordination_class.puml`], [Diagram kelas apps.coordination.],
  [`07_sequence_alerting.puml`], [Sequence evaluasi alert dan notifikasi.],
  [`08_sequence_brief_generation.puml`], [Sequence pembuatan hingga finalisasi Daily Brief.],
  [`09_sequence_collection_scheduling.puml`], [Sequence scheduler, kill switch, koleksi data.],
  [`10_sequence_coordination_detection.puml`], [Sequence deteksi CIB.],
  [`11_er_multitenancy_overview.puml`], [Diagram ER ringkas multi-tenancy lintas modul.],
)

== C. Cara Merender Diagram

Berkas `.puml` pada `docs/diagrams/` dapat dirender dengan salah satu cara berikut:

+ *PlantUML CLI lokal*: `java -jar plantuml.jar docs/diagrams/*.puml` (memerlukan Java, tersedia di lingkungan ini) -- menghasilkan berkas `.svg`/`.png` di folder yang sama.
+ *Ekstensi editor*: ekstensi "PlantUML" pada VS Code/JetBrains untuk pratinjau langsung saat menyunting.
+ *Server PlantUML mandiri (self-hosted)*: menghindari pengiriman kode sumber ke layanan publik pihak ketiga.
