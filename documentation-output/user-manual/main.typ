#import "/_shared/style.typ": *

#set document(title: "Buku Panduan Pengguna - PANTAU", author: "Tim Pengembang PANTAU")
#set text(lang: "id", size: 10.5pt, font: "New Computer Modern")
#set page(numbering: "1", margin: (x: 2.2cm, y: 2.2cm))
#set heading(numbering: "1.1.1")
#set par(justify: true)

#cover(
  "Buku Panduan Pengguna",
  "Sistem Pemantauan Media Sosial dan Narasi Politik Multi-Tenant",
  "Disusun berdasarkan pengujian QA fungsional terhadap aplikasi yang berjalan -- setiap prosedur di dokumen ini telah diverifikasi langsung pada aplikasi, bukan disalin dari spesifikasi.",
  "21 Juli 2026",
)

#include "chapters/pendahuluan.typ"
#include "chapters/persyaratan-sistem.typ"
#include "chapters/login-logout.typ"
#include "chapters/gambaran-antarmuka.typ"
#include "chapters/navigasi-umum.typ"
#include "chapters/panduan-peran-super-admin.typ"
#include "chapters/panduan-peran-tenant-admin.typ"
#include "chapters/panduan-peran-analis.typ"
#include "chapters/panduan-peran-peninjau.typ"
#include "chapters/prosedur-umpan-sebutan.typ"
#include "chapters/prosedur-war-room.typ"
#include "chapters/prosedur-insiden.typ"
#include "chapters/prosedur-brief.typ"
#include "chapters/prosedur-taksonomi.typ"
#include "chapters/prosedur-koordinasi.typ"
#include "chapters/prosedur-konfigurasi.typ"
#include "chapters/prosedur-analitik-lainnya.typ"
#include "chapters/laporan-dan-ekspor.typ"
#include "chapters/status-dan-notifikasi.typ"
#include "chapters/pemecahan-masalah.typ"
#include "chapters/faq.typ"
#include "chapters/glosarium.typ"
#include "chapters/dukungan.typ"
