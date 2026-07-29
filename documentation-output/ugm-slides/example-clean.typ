#import "clean.typ": *

#show: ugm-clean-theme.with(
  title: "Ini Adalah Judul Presentasi Menggunakan Font Gama-Sans Bold",
  subtitle: "Sub-judul sebagai pelengkap judul utama di atas, sentence case dengan font Gama-Sans regular.",
  author: "Nama Penyaji",
  date: "7 Juli 2026",
)

= Pendahuluan

== Selamat Datang

Tema *clean* ini mengikuti _Template Presentasi UGM 5_ — kanvas putih, garis
Balairung UGM, dan aksen emas–navy, dengan judul 30pt dan isi yang dibesarkan
agar lebih mudah dibaca.

- Warna resmi: navy `#01416B` dan emas `#FDD402`
- Tipografi *Gama-Sans* untuk judul maupun isi
- Latar otentik diekspor langsung dari berkas PowerPoint

== Daftar dan Penekanan

Beberapa poin penting dengan ukuran huruf yang lebih ringkas:

+ Butir pertama dengan *kata kunci* yang ditebalkan
+ Butir kedua yang menjelaskan konteks
+ Butir ketiga — angka penting seperti *34.000+* mahasiswa aktif

Ukuran isi yang lebih besar membuat teks nyaman dibaca dari kejauhan.

= Konten

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
  [Program], [Jenjang], [Akreditasi],
  [Ilmu Komputer], [S1], [Unggul],
  [Informatika], [S2], [A],
)

```python
def salam(nama):
    return f"Selamat datang di UGM, {nama}!"
```

#quote-slide[
  "Ini adalah teks untuk kutipan atau _quotes_ yang menggunakan font Gama-Sans light italic."
]

= Penutup

== Terima Kasih

Silakan gunakan tema ini untuk presentasi resmi UGM dengan gaya yang lebih ringan.

Kompilasi:

```bash
typst compile --font-path assets/fonts example-clean.typ
```
