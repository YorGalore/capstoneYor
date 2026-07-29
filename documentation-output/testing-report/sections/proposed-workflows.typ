#import "../../_shared/style.typ": *

= Usulan Perbaikan Alur Kerja <sec-proposed>

Bagian ini adalah *usulan* (proposal) untuk alur kerja yang teridentifikasi memiliki kesenjangan nyata pada @sec-gap -- bukan deskripsi perilaku yang sudah ada di aplikasi saat ini.

== Penegakan Matriks Izin yang Konsisten di Seluruh View (mengatasi ISS-KOORDINASI-003, ISS-FW-002, RBAC-ISSUE-001)

Alur yang diusulkan agar matriks izin benar-benar menjadi satu-satunya sumber kebenaran untuk akses halaman *dan* aksi tulis terkaitnya:

+ Setiap view baru yang didaftarkan pada registry `PAGES` (`apps/core/permissions.py`) WAJIB dibungkus `@require_page(<slug>)` -- tidak terkecuali. Tambahkan test regresi otomatis yang meng-iterasi seluruh 16 halaman pada registry, mentoggle tiap sel non-reserved ke "Tolak", lalu memverifikasi HTTP 403 pada request langsung ke halaman terkait (REC-003).
+ Untuk endpoint aksi tulis yang menempel pada sebuah halaman baca (mis. `log_response` di War Room, `insiden_note`/`insiden_status`/`insiden_assign` di Insiden, `escalate_cluster`/`mark_cluster_organic` di Koordinasi, `generate_brief`/`review_brief_issue`/`finalize_brief` di Brief), perkenalkan konsep izin terpisah untuk *baca* vs *tulis* pada halaman yang sama -- mis. `@require_page('war_room', level='write')` yang secara eksplisit mengecualikan peran `viewer` -- alih-alih mengandalkan gerbang baca halaman yang sama untuk melindungi aksi tulis (REC-001, REC-002, REC-004, REC-006, REC-007).
+ Segera setelah decorator ditambahkan, jalankan ulang seluruh 68 baris `role-permission-matrix.csv` sebagai regression suite untuk memastikan tidak ada regresi akses baca yang sebelumnya sah.

== Jalur Revisi Brief Final (mengatasi ISS-BTX-001)

Diusulkan aksi baru "Tarik/Revisi" yang hanya dapat dijalankan Tenant Admin/Super Admin:

+ Tombol "Tarik ke Draft" muncul pada brief berstatus Final, dibatasi role tenant_admin/super_admin.
+ Aksi ini dicatat ke audit log (aktor, waktu, alasan opsional) sebelum mengembalikan `brief.status` ke Draft.
+ Riwayat versi final sebelumnya tetap tersimpan sebagai snapshot (bukan ditimpa), sehingga brief yang sudah terlanjur dibagikan ke pihak eksternal tetap dapat dirujuk (REC-010).

== Indikator Status Eskalasi Klaster Koordinasi (mengatasi ISS-KOORDINASI-001)

+ Tambahkan field status baru (mis. `escalated`) pada `CoordinationCluster`, diset oleh `escalate_cluster` selain entri audit log yang sudah ada.
+ Tampilkan badge status berbeda ("Dieskalasi" vs "Ditandai") pada daftar klaster di `/koordinasi/`, bertahan setelah reload, agar analis dapat membedakan klaster yang sudah ditindaklanjuti tanpa membuka log audit terpisah (REC-012).

== Sidebar Responsif dan Tabel Taksonomi yang Dapat Dijangkau di Mobile (mengatasi ISS-BTX-006)

+ Terapkan pola collapse standar: sidebar menjadi off-canvas/hamburger di bawah breakpoint tablet (kurang dari 900px), konsisten di seluruh halaman dashboard bukan hanya sebagian.
+ Pastikan kontainer tabel (`pantau-table-scroll`) pada Taksonomi Isu menampilkan indikator scroll horizontal yang jelas terlihat pada lebar sempit, sehingga kolom "Konten" dan tombol "Labeli" tetap terjangkau (REC-005).

== Verifikasi OnboardingRequest Tanpa Bergantung pada Django Admin (mengatasi ONB-ISSUE-003)

+ Berikan `is_staff=True` dan izin model yang relevan kepada akun `role=super_admin` secara otomatis saat provisioning profil, ATAU
+ Tampilkan daftar `OnboardingRequest` langsung pada halaman `/pengawasan/` atau `/konfigurasi/izin/` di UI PANTAU, sehingga verifikasi lead onboarding tidak pernah bergantung pada Django admin sama sekali (REC-008).
