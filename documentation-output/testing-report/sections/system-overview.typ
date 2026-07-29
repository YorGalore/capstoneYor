#import "../../_shared/style.typ": *

= Gambaran Sistem

PANTAU adalah platform Django untuk pemantauan media sosial dan narasi politik, ditujukan bagi instansi pemerintah dan organisasi yang perlu memantau sentimen publik, mendeteksi isu, mengelola respons krisis, dan menghasilkan ringkasan eksekutif harian secara terkendali dan dapat diaudit. Bagian ini hanya merangkum aspek yang dibutuhkan untuk memahami temuan pengujian pada laporan ini -- untuk gambaran arsitektur teknis lengkap, lihat dokumen terpisah `docs/documentation.typ`.

== Multi-Tenancy

Struktur data PANTAU bertingkat: satu *Tenant* (mis. sebuah kabupaten atau kementerian) memiliki satu atau lebih *Project* sebagai batas isolasi data. Data uji pada laporan ini disusun untuk tenant "Kabupaten Kulon Progo".

== Empat Peran (Roles)

Akses pengguna diatur oleh field `AnalystProfile.role` dengan empat nilai:

- *`super_admin`* (Platform Super Admin) -- akses penuh ke seluruh halaman, selalu diizinkan tanpa bergantung pada matriks izin.
- *`tenant_admin`* (Tenant Admin) -- akses penuh dalam lingkup tenant-nya, termasuk konfigurasi sumber data dan penjadwalan koleksi.
- *`analyst`* (Analis) -- akses baca ke sebagian besar modul analitik, dapat melakukan aksi analitik tertentu (koreksi sentimen, log respons War Room) bila matriks izin mengizinkan.
- *`viewer`* (Peninjau) -- dimaksudkan hanya-baca (read-only) terhadap dasbor analitik; laporan ini menunjukkan peran ini pada praktiknya dapat melakukan beberapa aksi tulis akibat celah kontrol akses (lihat @sec-gap).

== Mekanisme Matriks Izin Halaman

Menurut FR-1A, akses ke setiap halaman diatur oleh sebuah matriks basis data (peran x halaman) yang dapat disunting Super Admin melalui `/konfigurasi/izin/`. Setiap halaman yang terdaftar dalam registry `PAGES` di `apps/core/permissions.py` seharusnya digerbang oleh decorator `@require_page(<slug>)` pada view Django-nya, yang memeriksa baris `PagePermission` (atau nilai `default_can_access` bila belum ada baris eksplisit) sebelum mengizinkan request. Dua halaman (Matriks Izin dan Pengaturan Dev/Ops) dikunci permanen ("reserved") hanya untuk `super_admin`.

Pengujian ini menemukan bahwa asumsi "setiap halaman di registry benar-benar digerbang oleh decorator-nya" tidak selalu benar -- lima view (Ringkasan, War Room, Narasi, Regional, Koordinasi) tampil dapat ditoggle di editor matriks izin namun secara nyata tidak memiliki `@require_page` pada kode view-nya, sehingga toggle tersebut tidak berefek. Ini adalah inti dari temuan Critical dan High pada laporan ini.

== Modul yang Diuji

- *Analitik* -- Ringkasan, Umpan Sebutan (feed), War Room, Insiden, Perbandingan Narasi, Regional, Sosiograf, Laporan, Sorotan Eksekutif/Daily Brief, Taksonomi Isu, Ekspor Sebutan.
- *Koordinasi* -- Deteksi Perilaku Tidak Otentik Terkoordinasi (Coordinated Inauthentic Behavior).
- *Tata Kelola (Governance)* -- Konsol Konfigurasi, Dasbor Pengawasan, Matriks Izin Halaman, Pengaturan Dev/Ops.
- *Publik/Onboarding* -- landing page, formulir permintaan demo, artikel, login.
