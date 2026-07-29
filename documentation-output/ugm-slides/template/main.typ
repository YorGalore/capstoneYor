#import "@preview/ugm-slides:0.1.0": *

#show: ugm-theme.with(
  title: "Judul Presentasi",
  subtitle: "Sub-judul opsional",
  author: "Nama Penyaji",
  faculty: "Fakultas / Unit",
  date: "6 Juli 2026",
  toc: true,
)

= Bagian Pertama

== Slide Pertama

- Tulis konten Anda di sini
- Gunakan *penekanan* untuk kata kunci

== Slide Kedua

#columns-slide(
  [
    === Kolom Kiri
    Isi kolom kiri.
  ],
  [
    === Kolom Kanan
    Isi kolom kanan.
  ],
)

#focus-slide[Kalimat penekanan]

= Penutup

== Terima Kasih

Kontak: nama\@ugm.ac.id
