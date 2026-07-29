#import "../../_shared/style.typ": *

= Aksesibilitas dan Responsivitas <sec-a11y>

== Cakupan Pengujian

Pengujian responsif dijalankan dengan menangkap tangkapan layar pada tiga lebar viewport standar -- *1440x900* (desktop), *834x1112* (tablet), dan *390x844* (mobile, setara iPhone 12/13) -- untuk halaman-halaman utama: landing page publik, formulir onboarding, halaman login, Umpan Sebutan, War Room, Konsol Konfigurasi, Deteksi Koordinasi, Sorotan Eksekutif, dan Taksonomi Isu.

#belum_tersedia[
  Pengujian ini tidak mencakup audit aksesibilitas terukur (navigasi keyboard penuh dengan pembacaan urutan fokus, rasio kontras warna dihitung dengan alat otomatis seperti axe/Lighthouse, atau uji pembaca layar). Verifikasi visual responsif dilakukan secara otomatis melalui perbandingan tangkapan layar tanpa pemeriksaan piksel-demi-piksel manual pada setiap kasus (dicatat eksplisit sebagai "Complete with Friction" pada beberapa kasus uji, mis. BTX-030, BTX-031), sehingga direkomendasikan tinjauan visual manual tambahan sebelum rilis.
]

== Hasil per Lebar Layar

Mayoritas halaman tetap dapat digunakan pada ketiga lebar viewport -- tata letak kartu dan tabel pada Konsol Konfigurasi, War Room, dan Umpan Sebutan menyesuaikan dengan baik. Namun dua celah signifikan ditemukan konsisten pada lebar mobile (390x844):

- *Sidebar tidak collapse pada mobile.* Pada `/brief/` dan `/taksonomi/`, sidebar navigasi tetap tampil sebagai kolom lebar tetap alih-alih menyusut menjadi hamburger/off-canvas, menyisakan sangat sedikit ruang untuk konten utama (ISS-BTX-006, High).
- *Dampak parah pada tabel Taksonomi Isu.* Akibat sidebar yang tidak collapse, kolom "Konten" dan tombol aksi "Labeli" pada tabel Antrean Tinjauan Manual tidak terlihat/tidak dapat dijangkau tanpa scroll horizontal yang jelas -- skenario realistis untuk analis/humas yang bertugas di lapangan menggunakan ponsel.

#screenshot("/testing-report/screenshots/brief_responsif_admin_390x844.png", "Tampilan /brief/ pada viewport mobile 390x844 -- sidebar tetap menghabiskan ruang layar signifikan.")

#screenshot("/testing-report/screenshots/taksonomi_responsif_admin_390x844.png", "Tampilan /taksonomi/ pada viewport mobile 390x844 -- kolom Konten dan tombol Labeli pada tabel Antrean Tinjauan Manual praktis tidak terjangkau.")

Untuk perbandingan, berikut tampilan tablet (834x1112) dan desktop (1440x900) dari halaman yang sama, yang tidak menunjukkan masalah serupa:

#screenshot("/testing-report/screenshots/taksonomi_responsif_admin_834x1112.png", "Tampilan /taksonomi/ pada viewport tablet 834x1112 -- tabel tetap dapat dibaca dengan sidebar yang proporsional.")

Halaman lain yang diuji pada ketiga lebar layar (Umpan Sebutan, War Room, Deteksi Koordinasi, Konsol Konfigurasi, landing page publik, formulir onboarding) tidak mencatat masalah serupa pada register -- lihat `feed_responsif_tenant-admin_390x844.png`, `warroom_responsif_tenant-admin_390x844.png`, `koordinasi_responsif_tenant-admin_mobile_390x844.png`, dan `konfigurasi_responsif_tenant-admin_mobile_390x844.png` untuk bukti tambahan.
