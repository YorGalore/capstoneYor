// Presentasi PANTAU untuk Pemerintah Kabupaten Kulon Progo (v2)
// Tema: ugm-clean-theme (Template Presentasi UGM 5)
// v2 menambahkan Bagian 2 "Bagaimana PANTAU Bekerja di Balik Layar":
//   landasan teori pengumpulan data (API/scraping) dan teknik analisis
//   media sosial (NLP, deteksi lonjakan, analisis jaringan).
// Kompilasi:
//   typst compile --root documentation-output \
//     --font-path documentation-output/ugm-slides/assets/fonts \
//     documentation-output/presentasi-kulonprogo/presentasi-kulonprogo-v2.typ

#import "../ugm-slides/clean.typ": *

// ── Identitas produk PANTAU ────────────────────────────────────────────────
// Warna merek PANTAU (teal→mint) — berbeda dari navy/emas UGM. Kotak logo dan
// wordmark ini menghadirkan nuansa produk di sisi identitas kampus penyaji.
#let pantau-teal = rgb("#0E7C86")
#let pantau-mint = rgb("#2FD4C4")

#let pantau-mark(scale: 1.0) = box(grid(
  columns: (auto, auto),
  column-gutter: 9pt * scale,
  align: horizon + left,
  box(
    width: 34pt * scale, height: 34pt * scale, radius: 9pt * scale,
    fill: gradient.linear(pantau-teal, pantau-mint, angle: 135deg),
    align(center + horizon, text(
      font: ugm-sans, size: 18pt * scale, weight: "bold", fill: white,
    )[P]),
  ),
  stack(
    spacing: 3pt * scale,
    text(font: ugm-sans, size: 16pt * scale, weight: "bold",
      fill: ugm-navy, tracking: 0.6pt)[PANTAU],
    text(font: ugm-sans, size: 9pt * scale, fill: pantau-teal,
      tracking: 1.4pt)[NARASI & OPINI],
  ),
))

#show: ugm-clean-theme.with(
  title: "PANTAU: Sistem Pemantauan Aspirasi Publik",
  subtitle: "Penjelasan alur kerja melalui studi kasus demonstrasi Kabupaten Kulon Progo",
  author: "Dr.techn. Guntur Budi Herwanto, M.Cs. — DIKE FMIPA, Universitas Gadjah Mada",
  date: "Juli 2026",
  brand-mark: move(dy: -8pt, pantau-mark(scale: 1.05)),
)

// Alamat sistem berjalan — setiap tangkapan layar di bawah dapat diklik
// langsung menuju halaman aslinya di sistem yang sedang beroperasi.
#let sys = "https://pantau.komunitech.id"

// ── Bagian 1 ──────────────────────────────────────────────────────────────

= Aspirasi Warga di Media Sosial

== Contoh Aspirasi yang Terekam

#grid(
  columns: (54%, 46%),
  gutter: 1.1em,
  align: (left + horizon, center + horizon),
  [
    #grid(
      columns: (auto, 1fr),
      gutter: 12pt,
      align: (left + top, left + horizon),
      text(font: ugm-serif, size: 54pt, weight: "bold", fill: ugm-gold)[“],
      [
        #text(size: 25pt, weight: "light", style: "italic", fill: ugm-navy)[
          Sudah tiga motor jatuh di lubang depan Pasar Sentolo.
        ]
        #v(0.25em)
        #text(size: 12.5pt, fill: ugm-navy.lighten(25%))[
          TikTok · \@anakwates · 23 Juli 2026, 02.18
        ]
      ],
    )

    #v(0.7em)
    #text(size: 12pt, weight: "bold", fill: ugm-navy)[Rekaman pada Umpan Sebutan PANTAU]
    #v(0.2em)
    #block(
      width: 100%, inset: 7pt, radius: 6pt,
      stroke: 0.8pt + ugm-navy.lighten(70%), fill: white,
      image("figs/umpan_sentolo_crop.png", width: 100%),
    )
    #v(0.2em)
    #text(size: 10.5pt, fill: ugm-navy.lighten(25%))[
      Data demonstrasi untuk skenario Kulon Progo.
    ]
  ],
  [
    #image("figs/tiktok_sentolo_simulasi.png", height: 4.55in)
    #v(0.2em)
    #align(center, text(size: 10.5pt, fill: ugm-navy.lighten(25%))[
      Simulasi tampilan unggahan TikTok berdasarkan data demonstrasi.
    ])
  ],
)

== Media Sosial sebagai Kanal Aspirasi Warga

#grid(
  columns: (56%, 44%),
  gutter: 1.2em,
  align: (left + horizon, center + horizon),
  [
    - Keluhan tentang *jalan rusak, air mati, dan sampah* kini lebih dulu muncul di TikTok, X, Instagram, atau Facebook
    - Kanal resmi tetap penting, tetapi belum menjadi pilihan semua warga
    - Tanpa pemantauan aktif, pemerintah sering baru mengetahui masalah *setelah telanjur ramai*
  ],
  image("figs/fig_warga_bersuara.png", height: 3.3in),
)

#v(0.6em)
#align(center, block(
  inset: 12pt, radius: 6pt, fill: ugm-navy.lighten(92%),
  text(size: 18pt)[Pemantauan diperlukan agar keluhan yang tersebar di berbagai platform dapat dihimpun dan dianalisis secara konsisten.]
))

== Informasi yang Disajikan kepada Pimpinan

#grid(
  columns: (40%, 60%),
  gutter: 1.2em,
  align: (left + horizon, center + horizon),
  [
    Ringkasan PANTAU menyusun informasi ke dalam tiga pertanyaan operasional:

    #v(0.5em)
    #stack(
      spacing: 9pt,
      ..(("1", "Apa yang terjadi?"),
         ("2", "Mana yang paling mendesak?"),
         ("3", "Siapa yang perlu bergerak hari ini?")).map(((n, q)) => block(
        width: 100%, inset: 11pt, radius: 7pt, fill: ugm-navy,
        grid(
          columns: (auto, 1fr), gutter: 10pt, align: horizon,
          text(fill: ugm-gold, size: 23pt, weight: "bold")[#n],
          text(fill: white, size: 15.5pt, weight: "bold")[#q],
        ),
      ))
    )

    #v(0.5em)
    #text(size: 14pt, fill: ugm-navy)[Informasi ditampilkan secara *ringkas dan terurut* untuk mendukung proses peninjauan.]
  ],
  image("figs/fig_pertanyaan_pimpinan.png", width: 100%),
)

== PANTAU: Dari Percakapan Menjadi Tindak Lanjut

#v(0.5em)
#grid(
  columns: (1fr, 1fr, 1fr, 1fr), gutter: 12pt,
  ..(("Pantau", "Tangkap percakapan publik dari media sosial dan berita daring"),
     ("Pahami", "Baca sentimen dan topik, lalu satukan keluhan yang serupa"),
     ("Prioritaskan", "Temukan lonjakan dan urutkan isu berdasarkan tingkat urgensinya"),
     ("Tindak lanjuti", "Teruskan ke OPD, pantau progres, dan siapkan ringkasan pimpinan")).enumerate().map(((i, (t, d))) => block(
    width: 100%, height: 2.9in, inset: 13pt, radius: 8pt,
    fill: if calc.even(i) { ugm-navy } else { ugm-navy.lighten(12%) },
    align(center)[
      #text(fill: ugm-gold, size: 15pt, weight: "bold")[Langkah #(i + 1)]
      #v(0.3em)
      #text(fill: white, size: 19pt, weight: "bold")[#t]
      #v(0.5em)
      #text(fill: white.darken(4%), size: 13.5pt)[#d]
    ]
  ))
)

// ── Bagian 2 (baru) ─────────────────────────────────────────────────────
// Landasan teori: bagaimana PANTAU mengumpulkan data (API/scraping) dan
// menganalisisnya (NLP, deteksi lonjakan, analisis jaringan) — memperdalam
// langkah "Pantau" dan "Pahami" pada slide 4-langkah di atas, dan menjadi
// dasar bagi angka-angka yang muncul pada studi kasus di Bagian 3.

= Bagaimana PANTAU Bekerja di Balik Layar

== Dua Jalur Pengumpulan Data

#grid(
  columns: (56%, 44%),
  gutter: 1.2em,
  align: (left + horizon, center + horizon),
  [
    - PANTAU mengambil data lewat dua jalur yang saling melengkapi
    - *API resmi platform* media sosial — terstruktur, sesuai kuota dan ketentuan layanan
    - *Penelusuran web (web scraping)* untuk sumber tanpa API resmi — terutama *portal berita daring*, di samping forum dan blog lokal
    - Setiap jalur disaring dengan *kata kunci dan wilayah* yang telah dikonfigurasi, misalnya "jalan rusak", "Sentolo", atau "PDAM"
    - Hanya *unggahan publik* yang diproses — pesan pribadi dan akun privat tidak pernah diakses
    - Pengambilan data mengikuti *ketentuan layanan platform* dan menghormati batas laju (rate limit) yang berlaku
  ],
  image("figs/fig_pengumpulan_data.png", width: 100%),
)

== Dari Teks Warga menjadi Data Terstruktur

#grid(
  columns: (56%, 44%),
  gutter: 1.2em,
  align: (left + horizon, center + horizon),
  [
    - Teks mentah dibersihkan lebih dulu — *typo, singkatan, dan bahasa gaul* dinormalisasi agar dapat dibaca sistem
    - Proses ini berlaku untuk *unggahan medsos maupun artikel berita daring* — keduanya diberi *label sentimen* (positif/netral/negatif) dan dipetakan ke *topik atau isu* yang relevan
    - Keluhan yang membicarakan hal serupa *dikelompokkan menjadi satu*, sehingga ratusan unggahan terbaca sebagai beberapa isu utama
    - Operator tetap dapat *meninjau dan mengoreksi* hasil klasifikasi otomatis
  ],
  image("figs/fig_pipeline_teks.png", width: 100%),
)

== Mendeteksi Lonjakan dan Menentukan Prioritas

#grid(
  columns: (56%, 44%),
  gutter: 1.2em,
  align: (left + horizon, center + horizon),
  [
    - Sistem memantau *jumlah unggahan dan proporsi sentimen negatif* pada suatu isu dari waktu ke waktu
    - Ketika angka itu melewati ambang tertentu dalam rentang waktu singkat, sistem menandai *lonjakan* dan membuat kandidat insiden
    - Tingkat urgensi (*Kritis / Tinggi / Sedang*) dihitung dari kombinasi volume, kecepatan lonjakan, dan proporsi sentimen negatif
    - Perhitungan inilah yang mendasari status *Kritis* pada isu Jalan Rusak Wates–Sentolo di Bagian berikutnya
  ],
  image("figs/fig_deteksi_lonjakan.png", width: 100%),
)

== Mengenali Pola Jaringan: Organik atau Terkoordinasi?

#grid(
  columns: (56%, 44%),
  gutter: 1.2em,
  align: (left + horizon, center + horizon),
  [
    - Selain isi teks, PANTAU turut mengamati *pola perilaku akun*: kemiripan waktu unggah, kemiripan redaksi, dan pola saling membagikan
    - Akun-akun dengan pola yang sangat mirip dipetakan sebagai *klaster* dalam sebuah graf jaringan
    - Klaster yang padat dan seragam menjadi indikasi *gerakan terkoordinasi*, berbeda dari sebaran keluhan warga yang organik
    - Hasilnya tetap berupa *indikasi* yang memerlukan tinjauan manusia — lihat penerapannya pada slide "Koordinasi"
  ],
  image("figs/fig_jaringan_klaster.png", width: 100%),
)

// ── Bagian 3 ──────────────────────────────────────────────────────────────

= Demonstrasi PANTAU di Kulon Progo

== Tampilan Sistem dan Data Demonstrasi

#grid(
  columns: (60%, 40%),
  gutter: 1.2em,
  align: (left + horizon, center + horizon),
  [
    Bagian berikut menampilkan *tangkapan layar sistem PANTAU*.

    Untuk keperluan presentasi, sistem menggunakan *data demonstrasi yang disusun sesuai konteks Kulon Progo*, seperti jalan rusak, air bersih, sampah, dan isu lokal lainnya.

    #v(0.4em)
    #table(
      columns: (auto, 1fr),
      [*Waktu*], [*Yang terjadi*],
      [*18–23 Juli*], [Keluhan warga terus bertambah di media sosial],
      [*23 Juli, 16.24*], [PANTAU menangkap lonjakan → kandidat insiden *Kritis*],
      [*23 Juli, 16.25*], [Operator mengonfirmasi dan meneruskan ke Dinas PU],
      [*Keesokan pagi*], [Pimpinan menerima ringkasan eksekutif],
    )

    #v(0.4em)
    #text(size: 12.5pt, fill: ugm-navy)[🔗 Setiap tangkapan layar dapat *diklik* untuk membuka halaman aslinya di #link(sys)[pantau.komunitech.id] (memerlukan akun).]
  ],
  image("figs/fig_sumber_data.png", width: 100%),
)

== 18–23 Juli: Keluhan Terus Bertambah

#grid(
  columns: (75%, 25%),
  gutter: 0.9em,
  align: (center + horizon, left + horizon),
  [
    #link(sys + "/umpan/", image("figs/umpan_negatif.png", height: 5in))
  ],
  [
    #text(size: 12.5pt)[
      - Unggahan dari TikTok, X, dan berita daring masuk ke *satu umpan pemantauan*
      - Sentimen dibaca otomatis, tetapi operator tetap dapat memeriksa dan mengoreksinya
      - Keluhan di ruas *Wates–Sentolo* mulai membentuk pola — bukan lagi satu-dua unggahan terpisah
    ]
  ],
)

== 23 Juli, 16.24: PANTAU Menangkap Lonjakan

#grid(
  columns: (75%, 25%),
  gutter: 0.9em,
  align: (center + horizon, left + horizon),
  [
    #link(sys + "/insiden/", image("figs/insiden_board.png", height: 5in))
  ],
  [
    #text(size: 12.5pt)[
      - Keluhan yang serupa otomatis dikelompokkan berdasarkan *isu dan wilayah*
      - #text(size: 19pt, weight: "bold")[22 sebutan · 86% negatif]
        #linebreak()→ *Jalan Rusak Wates–Sentolo* muncul sebagai kandidat *Kritis*
      - Gangguan air PDAM (*Tinggi*) dan sampah pasar (*Sedang*) ikut terpantau
      - Operator tidak perlu menyisir ribuan unggahan satu per satu
    ]
  ],
)

== Satu Kartu, Semua yang Perlu Diketahui

#align(center, link(sys + "/insiden/1/", image("figs/insiden_detail_crop.png", height: 74%)))
#v(0.3em)
Apa yang terjadi, dugaan penyebab, dampak, dan langkah yang disarankan tersusun dari angka serta kutipan warga. Semuanya tetap berstatus *DRAF* sampai ditinjau manusia.

== 16.25: Operator Mengonfirmasi, Dinas PU Menerima

#align(center, link(sys + "/insiden/1/", image("figs/insiden_timeline_crop.png", width: 68%)))
#v(0.4em)
- Operator meninjau kandidat, mengonfirmasinya, lalu meneruskan penanganan ke OPD terkait
- PANTAU mencatat alur proses; keputusan tetap berada di tangan pejabat berwenang
- Setiap langkah tercatat dalam *jejak audit*: siapa melakukan apa, dan kapan

== Keesokan Pagi: Ringkasan Siap untuk Pimpinan

#columns-slide(
  [
    #link(sys + "/brief/15/cetak/", image("figs/brief_cetak_crop.png", height: 88%))
  ],
  [
    - Ringkasan hari sebelumnya tersusun otomatis — *Jalan Rusak Wates–Sentolo* berada di urutan teratas
    - Operator wajib *meninjau dan menyetujui* sebelum ringkasan difinalkan
    - Hasilnya siap dicetak atau dibagikan sebagai PDF untuk apel pagi dan rapat pimpinan
  ],
)

== Satu Papan Prioritas untuk Seluruh Daerah

#v(0.5em)
#table(
  columns: (1fr, auto, auto, auto, auto),
  [*Isu*], [*Sebutan*], [*Negatif*], [*Tingkat*], [*OPD Tujuan*],
  [Jalan Rusak Wates–Sentolo], [22], [86%], [#text(fill: rgb("#b3261e"), weight: "bold")[Kritis]], [Dinas PU],
  [Air PDAM Mati Berhari-hari], [9], [78%], [#text(fill: rgb("#b3600f"), weight: "bold")[Tinggi]], [Dinas PU / PDAM],
  [Sampah Menumpuk di Pasar], [7], [57%], [#text(fill: rgb("#8a6d00"), weight: "bold")[Sedang]], [DLH],
)
#v(0.8em)
- Semua isu layanan publik terlihat dalam satu papan dan langsung terurut berdasarkan tingkat urgensinya
- Data dapat disaring berdasarkan waktu, OPD, atau tingkat insiden untuk bahan *rapat koordinasi mingguan*

== Keluhan Warga atau Gerakan Terkoordinasi?

#grid(
  columns: (75%, 25%),
  gutter: 0.9em,
  align: (center + horizon, left + horizon),
  [
    #link(sys + "/koordinasi/", image("figs/koordinasi.png", height: 5in))
  ],
  [
    #text(size: 12.5pt)[
      - PANTAU menemukan indikasi *perilaku terkoordinasi*: 17 akun dalam Klaster-KP-01 menyebarkan narasi yang nyaris sama
      - Temuan ini membantu pimpinan membedakan keluhan organik warga dari kampanye yang sengaja digerakkan
      - Hasilnya tetap berupa indikasi: *wajib ditinjau manusia* dan tidak pernah memicu pemblokiran otomatis
    ]
  ],
)

// ── Bagian 4 ──────────────────────────────────────────────────────────────

= Prinsip dan Batasan Sistem

== Prinsip Penggunaan PANTAU

#grid(
  columns: (58%, 42%),
  gutter: 1.2em,
  align: (left + horizon, center + horizon),
  [
    - *Keputusan tetap di tangan manusia* — AI menyiapkan draf; pejabat berwenang yang meninjau dan menetapkan tindak lanjut
    - *Berpijak pada bukti* — kesimpulan ditopang angka dan kutipan warga, bukan opini sistem
    - *Semua dapat ditelusuri* — deteksi, konfirmasi, dan perubahan status tercatat dalam jejak audit
    - *Data antarlembaga dipisahkan* — data setiap instansi tersimpan dan dikelola secara terisolasi
  ],
  image("figs/fig_prinsip_kepercayaan.png", width: 100%),
)

== Komponen Operasional Sistem

#v(0.4em)
#table(
  columns: (25%, 75%),
  [*Komponen*], [*Fungsi dalam alur PANTAU*],
  [*Operator*], [Meninjau hasil analisis, mengoreksi sentimen, mengonfirmasi insiden, dan mencatat tindak lanjut],
  [*Konfigurasi*], [Menentukan daftar OPD, wilayah pantauan, sumber data, serta kata kunci untuk setiap isu],
  [*Infrastruktur*], [Menjalankan proses pengumpulan data, analisis, penyimpanan, dan penyajian dasbor],
  [*Jejak audit*], [Mencatat perubahan status, penugasan, identitas pengguna, dan waktu setiap tindakan],
)

#v(0.8em)
#block(
  width: 100%, inset: 14pt, radius: 7pt,
  fill: ugm-navy.lighten(94%), stroke: 0.8pt + ugm-navy.lighten(65%),
)[
  Komponen tersebut menjelaskan konteks operasional sistem pada demonstrasi ini. Konfigurasi dan prosedurnya dapat berbeda pada lingkungan lain.
]

== Batasan Demonstrasi

#v(0.5em)
#grid(
  columns: (1fr, 1fr, 1fr), gutter: 14pt,
  ..((
      "Data",
      "Data yang digunakan merupakan data demonstrasi kontekstual, bukan gambaran kondisi aktual Kabupaten Kulon Progo."
    ), (
      "Hasil analisis",
      "Sentimen, tingkat insiden, dan indikasi koordinasi merupakan keluaran sistem yang tetap memerlukan tinjauan manusia."
    ), (
      "Kesimpulan",
      "Demonstrasi menjelaskan alur kerja PANTAU; hasilnya belum dapat digunakan untuk menilai dampak operasional di lapangan."
    )).map(((t, d)) => block(
      width: 100%, height: 2.7in, inset: 15pt, radius: 8pt,
      fill: ugm-navy.lighten(94%), stroke: 1pt + ugm-navy.lighten(60%),
      [
        #text(fill: ugm-navy, size: 20pt, weight: "bold")[#t]
        #v(0.45em)
        #text(size: 14.5pt)[#d]
      ],
    ))
)

== Ringkasan Studi Kasus

#grid(
  columns: (43%, 57%),
  gutter: 1.2em,
  align: (left + horizon, center + horizon),
  [
    Studi kasus demonstrasi Kulon Progo memperlihatkan empat fungsi utama PANTAU:

    #v(0.45em)
    - menghimpun percakapan dari beberapa sumber
    - mengelompokkan isu dan mendeteksi lonjakan
    - mencatat konfirmasi serta penugasan
    - menyusun ringkasan untuk peninjauan

    #v(0.7em)
    #text(size: 13pt, fill: ugm-navy.lighten(20%))[
      Seluruh keluaran sistem tetap memerlukan validasi manusia sebelum digunakan dalam pengambilan keputusan.
    ]

    #v(0.8em)
    #text(size: 13.5pt)[
      *Dr.techn. Guntur Budi Herwanto, M.Cs.* \
      Departemen Ilmu Komputer dan Elektronika \
      FMIPA, Universitas Gadjah Mada \
      gunturbudi\@ugm.ac.id
    ]
  ],
  image("figs/fig_penutup_kolaborasi_crop.png", height: 3.7in),
)
