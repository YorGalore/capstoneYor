#import "lib.typ": *

#show: ugm-theme.with(
  title: "Template Presentasi UGM",
  subtitle: "Tema Typst berbasis brand UGM",
  author: "Nama Penyaji",
  faculty: "Fakultas Matematika dan Ilmu Pengetahuan Alam",
  date: "6 Juli 2026",
  toc: true,
)

= Pendahuluan

== Selamat Datang

Tema ini mereproduksi identitas visual *Template PowerPoint UGM* di dalam Typst:

- Warna resmi: navy `#01416B` dan emas `#FDD402`
- Tipografi *Gama-Serif* (judul) dan *Gama-Sans* (isi)
- Motif kelopak teratai serta bilah emas di tepi kiri
- Navigasi bagian di bagian atas, terinspirasi oleh #link("https://typst.app/universe/package/diatypst")[diatypst]

== Cara Menulis Slide

Penulisan berbasis _heading_, mirip diatypst:

+ `= Judul` → *slide pembatas bagian* + menu navigasi
+ `== Judul` → *slide konten* baru otomatis
+ Isi ditulis seperti Markdown biasa

/ Tip: gunakan `#focus-slide[..]` untuk penekanan dan `#columns-slide(..)` untuk kolom.

= Konten

== Daftar dan Penekanan

Beberapa poin penting:

- Butir pertama dengan *kata kunci* yang ditebalkan
- Butir kedua
  - Sub-butir
  - Sub-butir lain
- Butir ketiga — angka penting seperti *34.000+* mahasiswa aktif

== Dua Kolom

#columns-slide(
  [
    === Kekuatan
    - Reputasi akademik
    - Jejaring global
    - Riset unggulan
  ],
  [
    === Fokus
    - Pendidikan
    - Penelitian
    - Pengabdian masyarakat
  ],
)

== Tabel dan Kode

#table(
  columns: 3,
  [*Program*], [*Jenjang*], [*Akreditasi*],
  [Ilmu Komputer], [S1], [Unggul],
  [Informatika], [S2], [A],
)

```python
def salam(nama):
    return f"Selamat datang di UGM, {nama}!"
```

#focus-slide[
  "Locally Rooted, \ Globally Respected"
]

= Penutup

== Terima Kasih

Silakan gunakan tema ini untuk presentasi resmi UGM Anda.

Kompilasi:

```bash
typst compile --font-path assets/fonts example.typ
```
