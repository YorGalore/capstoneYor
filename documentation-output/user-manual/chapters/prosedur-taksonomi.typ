#import "/_shared/style.typ": *

= Prosedur: Taksonomi Isu

Taksonomi Isu (`/taksonomi/`) adalah halaman tunggal untuk mengelola pelabelan konten ke isu dan menggabungkan isu yang tumpang tindih. Terdiri dari antrean tinjauan manual, formulir gabung isu, dan riwayat penggabungan.

#belum_tersedia[
  *Analis dan Peninjau tidak memiliki akses bawaan ke Taksonomi Isu.* Keduanya menerima 403 Forbidden saat mencoba membuka `/taksonomi/`. Prosedur pada bab ini diverifikasi menggunakan akun Tenant Admin.
]

== Melabeli konten pada antrean tinjauan manual

*Tujuan.* Menetapkan sebuah konten (mention) yang belum terklasifikasi ke isu yang sesuai.

*Peran yang berlaku.* Tenant Admin, Platform Super Admin.

*Prasyarat.* Terdapat konten pada antrean tinjauan manual.

*Langkah-langkah.*
1. Buka halaman *Taksonomi Isu* (`/taksonomi/`).
2. Pada baris pertama antrean tinjauan manual, pilih isu tujuan pada dropdown.
3. Klik tombol *Labeli*.

#screenshot("/testing-report/screenshots/taksonomi_labeli_admin_02_setelah-labeli.png", [Pesan sukses setelah konten dilabeli ke sebuah isu.])

*Hasil yang diharapkan.* Konten berpindah keluar dari antrean tinjauan manual dan tercatat sebagai berlabel ke isu yang dipilih; pesan sukses tampil.

*Perubahan status.* Konten berpindah dari status belum-terklasifikasi menjadi berlabel pada isu tertentu.

*Pemecahan masalah.*
- Antrean tinjauan manual dibatasi menampilkan maksimum 25 baris teratas. Setelah melabeli satu konten, jumlah baris pada tabel bisa tampak tetap 25 karena baris berikutnya otomatis mengisi slot yang kosong -- ini bukan berarti label Anda gagal tersimpan. Untuk memastikan, cari kembali item spesifik yang tadi Anda labeli; item tersebut seharusnya sudah tidak ada lagi di antrean.

== Menggabungkan (merge) dua isu

*Tujuan.* Menggabungkan dua isu yang sebenarnya membahas topik yang sama, agar analisis tidak terpecah.

*Peran yang berlaku.* Tenant Admin, Platform Super Admin.

*Prasyarat.* Terdapat minimal dua isu berbeda yang ingin digabungkan.

*Langkah-langkah.*
1. Pada formulir *Gabungkan Isu*, pilih satu isu sumber.
2. Pilih satu isu tujuan yang berbeda dari isu sumber.
3. Klik tombol *Gabungkan*.

#screenshot("/testing-report/screenshots/taksonomi_gabung_admin_03_setelah-gabung.png", [Pesan sukses setelah dua isu digabungkan.])

*Hasil yang diharapkan.* Isu sumber digabung ke isu tujuan (konten dipindah, isu sumber dinonaktifkan) dan tercatat pada tabel Riwayat Penggabungan dengan tombol "Batalkan" (unmerge) yang tetap tersedia setelah halaman dimuat ulang.

*Perubahan status.* Isu sumber berpindah dari status aktif menjadi tergabung/nonaktif; kontennya berpindah ke isu tujuan.

*Pemecahan masalah.*
- *Mengirim formulir gabung isu tanpa memilih isu sumber maupun tujuan:* ditolak dengan pesan "Pilih minimal satu isu sumber dan satu isu tujuan." Perhatikan bahwa pesan ini hanya tampil sekali pada tampilan pertama setelah pengiriman -- jika Anda memuat ulang halaman secara terpisah setelah itu, pesannya sudah tidak lagi terlihat meski tidak ada perubahan data yang terjadi.

#belum_tersedia[
  *Tampilan pada layar sempit (mobile, 390px lebar) memiliki keterbatasan serius pada halaman ini.* Sidebar navigasi tidak menyusut pada lebar ini, menyisakan ruang sangat sempit untuk tabel Antrean Tinjauan Manual -- kolom "Platform" dapat terpotong dan kolom "Konten" beserta tombol "Labeli" bisa sama sekali tidak terlihat tanpa scroll horizontal yang jelas indikatornya. Sebaiknya gunakan Taksonomi Isu dari layar tablet (834px) ke atas.
]
