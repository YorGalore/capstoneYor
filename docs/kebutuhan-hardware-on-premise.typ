#set document(
  title: "Kebutuhan Perangkat Keras On-Premise dan AI Lokal — PANTAU Kabupaten Kulon Progo",
  author: "Pemerintah Kabupaten Kulon Progo",
)
#set text(lang: "id", size: 10.5pt, font: "New Computer Modern")
#set page(
  paper: "a4",
  numbering: "1",
  margin: (x: 2.1cm, y: 2.0cm),
  footer: context [
    #set text(size: 8pt, fill: rgb("#667085"))
    #grid(
      columns: (1fr, auto),
    [PANTAU Kulon Progo — Hardware On-Premise dan AI Lokal],
      [Halaman #counter(page).display()],
    )
  ],
)
#set heading(numbering: "1.1")
#set par(justify: true, leading: 0.65em)
#show link: set text(fill: rgb("#175CD3"))

#let navy = rgb("#17324D")
#let blue = rgb("#175CD3")
#let pale = rgb("#EFF6FF")
#let border = rgb("#D0D5DD")
#let muted = rgb("#475467")
#let warning = rgb("#FFF7E8")
#let head(s) = table.cell(fill: navy)[#text(fill: white, weight: "bold")[#s]]

#let callout(title, body, fill: pale) = block(
  width: 100%,
  fill: fill,
  stroke: 0.7pt + border,
  radius: 4pt,
  inset: 10pt,
)[
  #text(weight: "bold", fill: navy)[#title]
  #v(3pt)
  #body
]

#let spec-table(..cells) = table(
  columns: (1.25fr, 1fr, 1fr, 1.15fr),
  inset: 6pt,
  stroke: 0.55pt + border,
  align: (left, left, left, left),
  table.header(
    head[Komponen],
    head[Pilot],
    head[Produksi],
    head[Volume Tinggi],
  ),
  ..cells,
)

#align(center)[
  #v(2.4cm)
  #text(size: 27pt, weight: "bold", fill: navy)[Kebutuhan Perangkat Keras]
  #v(0.15cm)
  #text(size: 21pt, weight: "bold", fill: blue)[PANTAU Kabupaten Kulon Progo]
  #v(0.7cm)
  #line(length: 62%, stroke: 1.5pt + blue)
  #v(0.7cm)
  #text(size: 13pt, fill: muted)[Pemantauan media, analisis komentar dan aktor,]
  #text(size: 13pt, fill: muted)[serta inferensi AI lokal di pusat data pemerintah daerah]
  #v(2.2cm)
  #callout(
    [Rekomendasi utama],
    [Dengan target anggaran *Rp300 juta*, pisahkan server aplikasi/database dari node AI
    lokal: GPU NVIDIA 32 GB, CPU 24 core, RAM ECC 128 GB, server aplikasi ECC 64 GB,
    backup terpisah, dan UPS online 5 kVA.],
  )
  #v(2.1cm)
  #text(size: 10pt, fill: muted)[Versi 1.0 — 29 Juli 2026]
  #v(0.15cm)
  #text(size: 9pt, fill: muted)[Disusun berdasarkan arsitektur dan kemampuan aktual repositori PANTAU]
]

#pagebreak()
#outline(title: [Daftar Isi], indent: auto)
#pagebreak()

= Ringkasan Eksekutif

PANTAU saat ini merupakan aplikasi Django berbentuk *modular monolith* yang dijalankan
dengan Docker Compose. Satu pemasangan produksi terdiri dari tiga kontainer: aplikasi web
Gunicorn, penjadwal pekerjaan, dan PostgreSQL 17. Berkas statis dilayani oleh WhiteNoise.
Pembuatan laporan PDF berlangsung di server aplikasi, sedangkan pengambilan data media
sosial dan komentar menggunakan layanan Apify melalui koneksi HTTPS.

Kapasitas server terutama ditentukan oleh empat hal:

+ jumlah posting dan komentar yang disimpan per hari;
+ lama retensi data;
+ jumlah pengguna yang membuka dashboard atau membuat laporan secara bersamaan; dan
+ frekuensi pekerjaan terjadwal seperti koleksi, analisis, alert, brief, dan deteksi
  koordinasi.

#callout(
  [Pilihan yang disarankan untuk plafon Rp300 juta],
  [
    Gunakan dua node: (1) server PANTAU/PostgreSQL *8 core, RAM ECC 64 GB, 2 × 1,92 TB
    SSD enterprise RAID 1*; dan (2) node AI *24 core, RAM ECC 128 GB, NVIDIA RTX 5090
    32 GB, serta NVMe 4 TB*. Tambahkan NAS backup dan UPS. RAB indikatif berjumlah tepat
    *Rp300.000.000*.
  ],
)

Angka dalam dokumen ini adalah *baseline perencanaan*, bukan hasil uji beban. Sebelum
pengadaan final, jalankan uji beban menggunakan pola data dan jumlah pengguna instansi
yang sebenarnya.

Plafon Rp300 juta diperlakukan sebagai anggaran proyek on-premise, bukan harga penawaran
vendor. Status pajak, pengiriman, garansi, instalasi, dan dukungan harus ditegaskan dalam
dokumen pengadaan agar total kontrak tidak melewati plafon.

= Profil Kebutuhan Kabupaten Kulon Progo

Dokumen ini ditailor untuk Pemerintah Kabupaten Kulon Progo, bukan untuk deployment
nasional. Dashboard kependudukan resmi mencatat *445.318 penduduk* pada Semester II 2025
yang tersebar di *12 kapanewon*: Temon, Wates, Panjatan, Galur, Lendah, Sentolo,
Pengasih, Kokap, Girimulyo, Nanggulan, Samigaluh, dan Kalibawang.
#footnote[
  Sumber: #link("https://data.dukcapil.kulonprogokab.go.id/")[Dashboard Sidutaku
  Dukcapil Kabupaten Kulon Progo], diakses 29 Juli 2026.
]

Skala tersebut tidak memerlukan klaster GPU nasional. Namun, pemerintah daerah
membutuhkan isolasi data, respons cepat saat isu lokal berkembang, dan kemampuan
menganalisis Bahasa Indonesia serta ragam bahasa lokal tanpa mengirim seluruh korpus ke
penyedia AI eksternal.

== Fokus Pemantauan Daerah

Kapasitas disiapkan untuk topik yang relevan bagi Kulon Progo:

- layanan publik, administrasi kependudukan, kesehatan, pendidikan, dan perizinan;
- infrastruktur, jalan, air, sampah, tata ruang, dan transportasi;
- Bandara Internasional Yogyakarta dan dampak ekonomi kawasan;
- pertanian, pangan, UMKM, investasi, pariwisata, dan kegiatan budaya;
- kebencanaan, cuaca ekstrem, longsor, banjir, kekeringan, dan kedaruratan;
- program prioritas daerah, aduan masyarakat, serta komunikasi krisis.

Daftar aktor awal mencakup Bupati/Wakil Bupati, Sekretariat Daerah, DPRD, seluruh OPD,
12 kapanewon, kalurahan/kelurahan, BUMD, pengelola layanan publik, komunitas, media
lokal, dan akun program resmi. Nama, alias, handle, singkatan OPD, serta kata kunci wajib
dikelola oleh analis karena berubah mengikuti organisasi dan periode jabatan.

Portal resmi kabupaten juga mengelompokkan layanan kependudukan, pendidikan, kesehatan,
perizinan, ketenagakerjaan, aduan, SatuData, dan Smart City; taksonomi awal PANTAU harus
menjaga keterhubungan dengan kategori layanan tersebut.
#footnote[
  Sumber: #link("https://kulonprogokab.go.id/v3/")[Portal Pemerintah Kabupaten Kulon
  Progo], diakses 29 Juli 2026.
]

= Arsitektur yang Menjadi Dasar Perhitungan

== Komponen Runtime

#table(
  columns: (1.1fr, 1.7fr, 1.4fr),
  inset: 6pt,
  stroke: 0.55pt + border,
  table.header(
    head[Komponen],
    head[Fungsi],
    head[Karakter Beban],
  ),
  [Web / Gunicorn], [Dashboard, autentikasi, analitik, ekspor, dan laporan PDF],
    [CPU dan RAM meningkat saat pengguna atau laporan bersamaan bertambah],
  [Scheduler], [Koleksi, alert, brief, retensi, pengayaan penulis, dan deteksi koordinasi],
    [Pekerjaan periodik; sebagian masih bersifat blocking],
  [PostgreSQL 17], [Menyimpan posting, komentar, aktor, hasil analisis, konfigurasi, dan audit],
    [I/O acak, RAM untuk cache, serta pertumbuhan indeks],
  [Layanan AI lokal (rencana)], [Sentimen, topik, ekstraksi aktor, ringkasan, dan bantuan penyusunan laporan],
    [GPU/VRAM tinggi; harus dipisahkan dari layanan web],
  [Apify], [Scraping historis dan terkini dari platform sosial beserta komentar],
    [Berjalan di luar server; membutuhkan internet keluar dan kuota Apify],
  [WhiteNoise], [Melayani CSS, JavaScript, dan aset statis],
    [Beban ringan; dapat dialihkan ke reverse proxy],
)

== Batas Arsitektur Saat Ini

- Docker Compose bawaan belum menyertakan reverse proxy atau terminasi TLS. Produksi harus
  menempatkan Nginx, Caddy, HAProxy, atau perangkat load balancer di depan port aplikasi.
- Migrasi basis data dijalankan oleh kontainer `web`. Sebelum menambah replika web,
  migrasi perlu dipindahkan menjadi langkah rilis tunggal.
- Koleksi dan beberapa pekerjaan analitik masih sinkron. Menambah core membantu, tetapi
  volume sangat tinggi sebaiknya memakai antrean pekerjaan terpisah.
- Server tidak menjalankan browser scraper atau model bahasa besar secara lokal. Jika
  AI lokal akan diaktifkan, tambahkan layanan inferensi dan integrasi aplikasi; membeli
  GPU saja belum mengaktifkan AI pada kode PANTAU.

= Asumsi Kapasitas

#table(
  columns: (1.35fr, 1fr, 1fr, 1.15fr),
  inset: 6pt,
  stroke: 0.55pt + border,
  table.header(
    head[Parameter],
    head[Pilot],
    head[Produksi],
    head[Volume Tinggi],
  ),
  [Item baru per hari], [hingga 10.000], [hingga 100.000], [hingga 500.000],
  [Termasuk komentar], [Ya], [Ya], [Ya],
  [Pengguna bersamaan], [hingga 10], [hingga 30], [hingga 100],
  [Retensi daring], [90–180 hari], [365 hari], [365 hari],
  [Pembuatan PDF bersamaan], [1], [2–4], [5–10],
  [Ketersediaan], [Satu server], [Satu server + backup], [Layanan dipisah / HA],
)

“Item” berarti satu baris konten yang dianalisis: posting, artikel, komentar, atau balasan.
Karena komentar disimpan sebagai item tersendiri dan ditautkan ke posting induk, jumlah
komentar dapat menjadi pengali volume terbesar. Batasi jumlah komentar per posting sesuai
kebutuhan analisis agar biaya Apify, waktu koleksi, dan pertumbuhan basis data terkendali.

Untuk Kulon Progo, sasaran operasional yang wajar adalah 10.000–50.000 item per hari
dengan kapasitas lonjakan sampai 100.000 item per hari ketika terjadi isu atau pengambilan
histori. Batas ini harus ditinjau setelah tiga bulan data produksi tersedia.

= Rancangan AI Lokal Kulon Progo

== Kemampuan yang Ditargetkan

Node AI disiapkan untuk melayani:

+ klasifikasi sentimen per posting dan per komentar;
+ deteksi topik, pengelompokan isu, dan kata kunci yang sedang tumbuh;
+ ekstraksi aktor, OPD, program, lokasi kapanewon, dan hubungan dengan posting induk;
+ ringkasan bukti, perbandingan periode, serta draf narasi laporan PDF;
+ embedding dan pencarian semantik atas korpus regulasi atau dokumen internal yang
  memang boleh digunakan;
+ bantuan draf respons insiden dengan persetujuan manusia.

Semua keluaran generatif harus menyertakan referensi ke item sumber dan berstatus draf.
AI tidak boleh otomatis mempublikasikan respons atas nama Pemerintah Kabupaten Kulon
Progo.

== Topologi Logis

#table(
  columns: (1.1fr, 1.7fr, 1.4fr),
  inset: 6pt,
  stroke: 0.55pt + border,
  table.header(
    head[Node],
    head[Layanan],
    head[Batas Keamanan],
  ),
  [Server PANTAU], [Django, Gunicorn, scheduler, PostgreSQL, PDF], [Tidak menjalankan job GPU],
  [Node AI], [Runtime inferensi, embedding, model registry, antrean kerja], [API internal saja; tanpa port publik],
  [NAS backup], [Backup database, konfigurasi, dan artefak model yang disetujui], [Tidak menjadi volume DB aktif],
  [Reverse proxy/firewall], [TLS, kontrol akses, VPN manajemen], [Satu-satunya jalur masuk publik],
)

== Gap Software yang Harus Ditutup

Kode PANTAU saat ini sudah menyimpan sentimen, komentar, aktor, topik, sumber URL, dan
hasil laporan, tetapi belum memiliki layanan inferensi LLM/GPU lokal. Pengadaan hardware
harus diikuti pekerjaan software berikut:

- memilih runtime inferensi, format model, dan lisensi model yang sesuai;
- membuat adapter PANTAU → API AI internal dengan timeout, retry, dan circuit breaker;
- membuat antrean agar inferensi tidak menahan worker web;
- menyimpan nama model, versi, confidence, waktu proses, serta koreksi analis;
- menyusun *golden dataset* Bahasa Indonesia/Kulon Progo untuk evaluasi;
- menerapkan fallback deterministik ketika layanan AI tidak tersedia;
- menguji kebocoran data, prompt injection, bias politik, dan halusinasi.

Tidak ada klaim “AI lokal siap produksi” sampai integrasi tersebut lulus uji fungsional,
akurasi, beban, keamanan, dan penerimaan pengguna.

= Spesifikasi Perangkat Keras

== Matriks Utama

#spec-table(
  [CPU], [4 core x86-64], [8 core x86-64], [16 core total atau lebih],
  [RAM ECC], [8 GB], [16 GB], [32–64 GB],
  [Penyimpanan aktif], [150 GB NVMe], [500 GB NVMe], [1–2 TB NVMe],
  [Konfigurasi disk], [1 disk + backup], [RAID 1 enterprise], [RAID 1/10 enterprise],
  [Jaringan LAN], [1 Gbps], [1 Gbps], [10 Gbps antarserver],
  [Internet], [100 Mbps], [100–300 Mbps], [300 Mbps–1 Gbps],
  [Server fisik], [1 unit], [1 unit + target backup], [Pisahkan app, scheduler, dan DB],
  [UPS], [Minimum 15 menit], [30 menit + shutdown otomatis], [Redundan / terhubung genset],
)

Matriks di atas berlaku untuk aplikasi tanpa AI lokal. Konfigurasi Kulon Progo menambahkan
node GPU khusus sebagaimana bagian berikut.

CPU dengan performa *single-core* yang baik tetap penting karena worker Gunicorn bersifat
sinkron. Jangan memilih core sangat banyak dengan frekuensi terlalu rendah hanya karena
angka core terlihat lebih besar.

== Kelas Pilot

Kelas Pilot cocok untuk evaluasi, demo internal, atau satu unit kerja dengan volume
terbatas. Spesifikasi minimum:

- 4 core CPU modern, RAM 8 GB;
- NVMe 150 GB dengan ruang kosong dipertahankan minimal 25%;
- LAN 1 Gbps dan internet stabil minimal 100 Mbps;
- backup harian ke NAS atau server lain.

Kelas ini bukan pilihan ideal untuk operasi 24×7 dengan retensi setahun. RAM 8 GB akan
membatasi cache PostgreSQL dan jumlah worker aplikasi saat laporan PDF dibuat.

== Kelas Produksi — Rekomendasi

Untuk satu instansi, sampai sekitar 100.000 item per hari:

- 8 core CPU server kelas enterprise atau setara;
- RAM ECC 16 GB, dapat ditingkatkan menjadi 32 GB tanpa mengganti server;
- 2 × NVMe enterprise 500 GB dalam RAID 1;
- pengendali penyimpanan dengan proteksi kehilangan daya atau NVMe dengan *power-loss
  protection*;
- dua antarmuka jaringan 1 Gbps bila pemisahan jaringan layanan dan manajemen diperlukan;
- UPS dengan agen *graceful shutdown*.

Jika retensi 365 hari benar-benar mencapai 100.000 item per hari, kapasitas 500 GB adalah
batas awal, bukan ruang berlebih. Pertimbangkan 1 TB sejak awal bila komentar panjang,
audit, dan pertumbuhan indeks diperkirakan tinggi.

== Kelas Produksi Plus + AI Lokal — Target Rp300 Juta

Plafon ini memungkinkan rancangan yang lebih tahan gangguan daripada spesifikasi produksi
minimum. Server aplikasi/database yang ditargetkan:

- CPU minimal 8 core kelas server dengan performa *single-core* yang baik;
- RAM ECC 64 GB, dengan ruang ekspansi setidaknya sampai 128 GB;
- 2 × 1,92 TB NVMe/SSD enterprise dalam RAID 1, kapasitas efektif sekitar 1,92 TB;
- *hot-plug drive*, TPM 2.0, manajemen jarak jauh, dan catu daya redundan;
- dua port 1 Gbps atau satu/dua port 10 Gbps;
- dukungan vendor di lokasi minimal tiga tahun.

Node AI lokal yang ditargetkan:

- CPU AMD Ryzen Threadripper PRO 7965WX 24 core atau kelas setara;
- RAM ECC 128 GB;
- satu NVIDIA RTX 5090 dengan VRAM 32 GB;
- NVMe 2 TB untuk sistem/model dan NVMe 2 TB untuk cache/dataset kerja;
- PSU PCIe 5.1 minimal 1.600 W, pendinginan workstation, dan sasis dengan aliran udara
  yang divalidasi untuk beban GPU kontinu;
- NIC 10 Gbps ke server aplikasi dan NAS.

Spesifikasi resmi NVIDIA menyatakan RTX 5090 memiliki VRAM GDDR7 32 GB dan daya GPU
575 W, sedangkan AMD menyatakan Threadripper PRO 7965WX memiliki 24 core, dukungan ECC,
dan TDP 350 W.
#footnote[
  Sumber spesifikasi:
  #link("https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5090/")[NVIDIA
  GeForce RTX 5090] dan
  #link("https://www.amd.com/en/support/downloads/drivers.html/processors/ryzen-threadripper-pro/amd-ryzen-threadripper-pro-7000-wx-series/amd-ryzen-threadripper-pro-7965wx.html")[AMD
  Ryzen Threadripper PRO 7965WX], diakses 29 Juli 2026.
]

VRAM 32 GB cocok untuk classifier, embedding, reranker, serta model generatif 7B–14B dan
sebagian model sekitar 32B dalam kuantisasi dengan batas konteks yang diuji. Konfigurasi
ini tidak dijanjikan untuk menjalankan model 70B penuh dengan seluruh bobot di GPU.
Model yang dipilih harus melalui evaluasi Bahasa Indonesia, terminologi Kulon Progo,
akurasi sentimen/aktor, latensi, dan risiko halusinasi.

== Daya Listrik dan Pendinginan Node AI

GPU referensi memiliki daya sampai 575 W dan CPU kelas sasaran sampai 350 W. Setelah
motherboard, RAM, NVMe, kipas, rugi PSU, server aplikasi, NAS, dan perangkat jaringan
dihitung, sediakan sirkuit listrik khusus dengan kapasitas kontinu minimal 2,5 kW dan UPS
online 5 kVA. Pengukuran aktual dengan *power meter* tetap wajib saat uji beban.

Node AI tidak boleh ditempatkan di ruang kantor tanpa pengendalian suhu. Siapkan ruang
server dengan pendinginan 24×7, sensor suhu/kelembapan, alarm, aliran udara depan-ke-
belakang, dan prosedur shutdown otomatis ketika suhu atau kapasitas baterai melewati
batas aman. Biaya pembangunan atau peningkatan AC ruang server berada di luar RAB
Rp300 juta ini.

== Kelas Volume Tinggi

Pada volume sampai 500.000 item per hari, jangan hanya memperbesar satu mesin. Topologi
yang lebih aman:

#table(
  columns: (1.1fr, 1fr, 1fr, 1.1fr),
  inset: 6pt,
  stroke: 0.55pt + border,
  table.header(
    head[Node],
    head[CPU],
    head[RAM],
    head[Disk],
  ),
  [Aplikasi web], [8 core], [16 GB], [150 GB NVMe],
  [Scheduler / worker], [8 core], [16 GB], [150 GB NVMe],
  [PostgreSQL], [16 core], [64 GB ECC], [2 TB NVMe RAID 10],
  [Backup], [4–8 core], [8–16 GB], [≥ 2 × ukuran DB],
)

Pemisahan ini memerlukan perubahan konfigurasi deployment. Untuk ketersediaan tinggi,
tambahkan replika database, mekanisme failover yang diuji, dan minimal dua node aplikasi.

= Perhitungan Penyimpanan

Gunakan rumus perencanaan berikut:

#align(center)[
  *Kapasitas DB = item/hari × hari retensi × 4 KB × 1,5*
]

Nilai 4 KB per item merupakan perkiraan konservatif untuk teks, metadata, relasi, dan
indeks. Faktor 1,5 menyediakan ruang untuk indeks tambahan, *vacuum*, migrasi, dan
pertumbuhan sementara. Tambahkan lagi 25% ruang kosong agar performa NVMe dan operasi
database tetap sehat.

#table(
  columns: (1fr, 1fr, 1fr, 1fr),
  inset: 6pt,
  stroke: 0.55pt + border,
  table.header(
    head[Volume],
    head[Retensi],
    head[Estimasi DB],
    head[Disk Disarankan],
  ),
  [10.000 item/hari], [180 hari], [± 11 GB], [150 GB],
  [100.000 item/hari], [365 hari], [± 219 GB], [500 GB–1 TB],
  [500.000 item/hari], [365 hari], [± 1,1 TB], [2 TB atau lebih],
)

PANTAU menyimpan teks, URL, dan metadata; media asli tidak disalin ke penyimpanan lokal
dalam arsitektur saat ini. Jika nanti gambar atau video diarsipkan, sediakan *object
storage* terpisah. Jangan menaruh arsip media besar di volume PostgreSQL.

= Rancangan Anggaran Rp300 Juta

== RAB Indikatif

#table(
  columns: (0.32fr, 1.6fr, 1.15fr, 0.85fr),
  inset: 5.5pt,
  stroke: 0.55pt + border,
  table.header(
    head[No.],
    head[Paket],
    head[Spesifikasi Sasaran],
    head[Anggaran],
  ),
  [1], [Node AI lokal],
    [24 core, ECC 128 GB, RTX 5090 32 GB, NVMe total 4 TB, PSU 1.600 W],
    [Rp145.000.000],
  [2], [Server aplikasi dan database],
    [8 core, ECC 64 GB, 2 × 1,92 TB enterprise RAID 1, manajemen jarak jauh],
    [Rp65.000.000],
  [3], [NAS / target backup],
    [4–8 bay, kapasitas usable minimal 16 TB, RAID 6, NIC redundan],
    [Rp30.000.000],
  [4], [UPS dan proteksi daya],
    [Online 5 kVA, kartu jaringan, baterai untuk shutdown aman],
    [Rp25.000.000],
  [5], [Jaringan, rack, dan lingkungan],
    [Managed switch 10 Gbps, kabel/optic, PDU, sensor suhu, integrasi firewall/VPN],
    [Rp12.000.000],
  [6], [Instalasi dan integrasi awal],
    [Hardening, deploy, runtime AI, uji beban, uji backup-restore, dokumentasi],
    [Rp10.000.000],
  [7], [Cadangan harga/pengiriman/pajak],
    [Buffer pengadaan; penggunaannya harus disetujui dan dibuktikan],
    [Rp13.000.000],
  table.cell(colspan: 3, fill: pale, align: right)[*TOTAL PLAFON*],
  table.cell(fill: pale)[*Rp300.000.000*],
)

Harga di atas adalah alokasi maksimum per paket, bukan kutipan vendor atau Harga
Perkiraan Sendiri final. Minta sekurang-kurangnya penawaran yang dapat dibandingkan sesuai
prosedur instansi. Dalam evaluasi, bandingkan nomor komponen, garansi, dukungan di lokasi,
ketahanan tulis SSD, proteksi kehilangan daya, jenis RAID, dan kapasitas efektif—bukan
hanya nama produk.

== Prioritas Saat Penawaran Melebihi Plafon

Urutan yang tidak boleh dikorbankan:

+ VRAM GPU 32 GB, RAM ECC, RAID 1 server aplikasi, backup terpisah, dan UPS;
+ garansi serta ketersediaan penggantian komponen;
+ kapasitas efektif yang cukup untuk retensi;
+ pengujian pemulihan.

Jika harga vendor lebih tinggi, turunkan CPU node AI dari 24 menjadi 16 core atau gunakan
uplink 1 Gbps terlebih dahulu. Jangan mengurangi VRAM menjadi 16 GB, mengganti SSD server
aplikasi dengan satu disk konsumen, menghapus backup, atau menganggap RAID sebagai
pengganti backup.

== Biaya yang Tidak Termasuk

RAB ini tidak memasukkan langganan Apify, koneksi internet bulanan, domain, sertifikat
komersial, pendingin ruang server, genset, lisensi SIEM, maupun lisensi model AI komersial.
Docker, PostgreSQL, Django, Gunicorn, dan komponen perangkat lunak utama yang digunakan
PANTAU bersifat sumber terbuka, tetapi dukungan komersial dapat dibeli terpisah.

= Jaringan dan Keamanan Infrastruktur

== Akses Jaringan

- Buka TCP 443 dari pengguna ke reverse proxy.
- Jangan mempublikasikan PostgreSQL 5432 ke internet.
- Izinkan HTTPS keluar TCP 443 menuju Apify dan sumber berita.
- Izinkan server PANTAU mengakses API node AI hanya pada VLAN internal dan port yang
  ditentukan; node AI tidak membuka endpoint ke internet.
- Batasi SSH ke VLAN manajemen atau VPN; nonaktifkan login kata sandi dan gunakan kunci.
- Gunakan DNS internal/publik yang sesuai dan sertifikat TLS yang dapat diperbarui
  otomatis.

Kebutuhan bandwidth lebih dipengaruhi jumlah respons API daripada ukuran media karena
server menerima data teks/metadata. Stabilitas koneksi, latensi, DNS, dan akses HTTPS
keluar lebih penting daripada kecepatan puncak semata.

== Segmentasi yang Disarankan

#table(
  columns: (1fr, 1.5fr, 1.4fr),
  inset: 6pt,
  stroke: 0.55pt + border,
  table.header(
    head[Zona],
    head[Isi],
    head[Aturan],
  ),
  [DMZ / layanan], [Reverse proxy], [443 masuk; teruskan hanya ke web],
  [Aplikasi], [Web dan scheduler], [Tidak dapat diakses langsung dari internet],
  [AI internal], [Runtime model dan GPU], [Hanya menerima permintaan dari aplikasi/worker],
  [Data], [PostgreSQL dan target backup], [Hanya dari node aplikasi/backup],
  [Manajemen], [SSH, monitoring, patching], [Hanya admin melalui VPN/VLAN],
)

= Backup, Pemulihan, dan Ketersediaan

RAID menjaga layanan saat satu disk gagal, tetapi bukan backup. Minimum produksi:

+ backup PostgreSQL harian dan backup logis mingguan;
+ salinan terenkripsi pada perangkat atau lokasi berbeda;
+ retensi harian 14–30 hari, bulanan sesuai kebijakan instansi;
+ backup `.env` dan konfigurasi reverse proxy dalam penyimpanan rahasia;
+ uji pemulihan minimal setiap tiga bulan;
+ dokumentasikan target *Recovery Point Objective* (RPO) dan *Recovery Time Objective*
  (RTO).

#callout(
  [Target awal yang praktis],
  [
    Untuk satu server produksi: RPO 24 jam dan RTO 4–8 jam. Jika instansi memerlukan RPO
    menit atau RTO di bawah satu jam, gunakan replikasi PostgreSQL, node aplikasi
    redundan, load balancer, dan prosedur failover yang diuji.
  ],
  fill: warning,
)

Sediakan target backup berkapasitas minimal dua kali ukuran data aktif. Untuk database
500 GB, target 1–2 TB memberi ruang bagi beberapa generasi backup dan pertumbuhan.

= Sistem Operasi dan Perangkat Lunak

#table(
  columns: (1fr, 1.8fr),
  inset: 6pt,
  stroke: 0.55pt + border,
  table.header(
    head[Lapisan],
    head[Rekomendasi],
  ),
  [Sistem operasi], [Linux server 64-bit yang masih didukung, misalnya Ubuntu Server LTS atau Debian stable],
  [Container runtime], [Docker Engine dan Docker Compose plugin],
  [Reverse proxy], [Nginx, Caddy, HAProxy, atau load balancer instansi],
  [Waktu], [NTP/chrony; zona waktu server konsisten],
  [Monitoring], [CPU, RAM, disk, I/O, status kontainer, HTTP `/healthz/`, PostgreSQL, dan umur koleksi terakhir],
  [Log], [Rotasi log, retensi, dan pengiriman ke SIEM bila diwajibkan],
  [Patch], [Jadwal patch OS, Docker, dan dependensi; lingkungan staging sebelum produksi],
)

Variabel produksi minimum meliputi `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`,
`DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, dan pengaturan TLS. Token Apify
dapat disimpan per proyek di aplikasi; `APIFY_API_TOKEN` atau `APIFY_KEY` berfungsi sebagai
fallback deployment. Token tidak boleh dimasukkan ke Git atau image Docker.

= Bill of Materials Teknis Kulon Progo

#table(
  columns: (0.35fr, 1.7fr, 1.2fr),
  inset: 6pt,
  stroke: 0.55pt + border,
  table.header(
    head[Qty],
    head[Barang],
    head[Catatan],
  ),
  [1], [Server aplikasi/database, 8 core, RAM ECC 64 GB], [2 × 1,92 TB enterprise RAID 1],
  [1], [Node AI, 24 core, RAM ECC 128 GB, GPU 32 GB], [NVMe total 4 TB, PSU 1.600 W],
  [1], [NAS backup usable minimal 16 TB], [RAID 6, snapshot, NIC redundan],
  [1], [UPS online 5 kVA dengan kartu jaringan], [Shutdown otomatis dua node dan NAS],
  [1], [Managed switch dengan uplink 10 Gbps], [VLAN aplikasi, AI, data, dan manajemen],
  [1], [Rack/PDU/sensor dan layanan monitoring], [Daya, suhu, kapasitas, GPU, dan health check],
)

Merek dan model tidak ditentukan agar pengadaan dapat mengikuti standar instansi. Prioritas
ada pada dukungan vendor, ECC, ketahanan tulis NVMe, proteksi kehilangan daya, kemudahan
penggantian disk, dan ketersediaan suku cadang.

= Checklist Sebelum Go-Live

- [ ] Volume harian, jumlah komentar, pengguna bersamaan, dan retensi telah disepakati.
- [ ] Kapasitas disk dihitung dengan ruang kosong minimal 25%.
- [ ] TLS aktif dan hanya port yang diperlukan dibuka.
- [ ] Database tidak dipublikasikan ke internet.
- [ ] `SEED_DEMO_DATA=0`; data demo tidak bercampur dengan data produksi.
- [ ] Token Apify tersedia sebagai kredensial proyek atau fallback environment.
- [ ] Runtime dan model AI memiliki lisensi yang mengizinkan penggunaan pemerintah.
- [ ] API AI hanya dapat diakses dari jaringan internal.
- [ ] Dataset evaluasi Kulon Progo, ambang akurasi, dan prosedur koreksi telah disetujui.
- [ ] Setiap ringkasan/draf AI dapat ditelusuri kembali ke sumber dan ditinjau manusia.
- [ ] Backup berhasil dibuat dan dipulihkan pada lingkungan uji.
- [ ] UPS dan *graceful shutdown* telah diuji.
- [ ] Monitoring `/healthz/`, disk, database, scheduler, kolektor, suhu, dan GPU telah aktif.
- [ ] Uji beban dan uji pembuatan beberapa PDF bersamaan telah dilakukan.
- [ ] Prosedur patch, rollback, pemulihan, dan kontak eskalasi telah didokumentasikan.

= Kesimpulan

Untuk Kabupaten Kulon Progo dengan plafon *Rp300 juta*, rancangan paling seimbang adalah
dua node: server aplikasi/database ECC yang stabil dan node AI lokal dengan *GPU 32 GB,
CPU 24 core, serta RAM ECC 128 GB*. NAS backup, UPS online 5 kVA, jaringan tersegmentasi,
dan pengujian integrasi termasuk di dalam alokasi.

Desain ini mendukung monitoring posting dan komentar, analisis aktor/topik, serta AI lokal
untuk klasifikasi dan bantuan ringkasan. Desain ini tidak menjanjikan model 70B penuh,
high availability otomatis, atau AI siap pakai tanpa pekerjaan integrasi software.

Spesifikasi dan RAB akhir harus divalidasi melalui penawaran vendor, uji daya/pendinginan,
uji beban dengan korpus Kulon Progo, evaluasi model Bahasa Indonesia, serta uji
backup-restore. Jika penawaran melewati plafon, pertahankan GPU 32 GB, ECC, storage
redundan, backup, dan UPS; kurangi kelas CPU atau kecepatan jaringan terlebih dahulu.
