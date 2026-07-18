"""Static editorial content for the public landing page.

Six evergreen articles in Bahasa Indonesia. Each explains why a facet of media
monitoring matters, then closes by connecting it to a concrete PANTAU capability
already listed on the landing page (see templates/core/landing.html #fitur).
"""

ARTICLES = [
    {
        "slug": "memantau-percakapan-publik-real-time",
        "title": "Kenapa organisasi perlu memantau percakapan publik secara real-time",
        "excerpt": (
            "Opini publik terbentuk dalam hitungan jam, bukan minggu. Organisasi yang "
            "masih menunggu laporan mingguan selalu tertinggal satu langkah."
        ),
        "category": "Dasar-dasar",
        "read_minutes": 4,
        "body": [
            ("p", (
                "Percakapan publik hari ini bergerak lebih cepat daripada siklus "
                "pelaporan organisasi mana pun. Sebuah unggahan bisa dibagikan ribuan "
                "kali sebelum tim komunikasi sempat membuka dashboard media sosial "
                "mereka. Ketika organisasi baru menyadari sebuah isu setelah muncul di "
                "berita utama, mereka sudah kehilangan kesempatan untuk merespons di "
                "titik paling murah: sebelum isu itu membesar."
            )),
            ("h", "Mendengar bukan hanya mencatat"),
            ("p", (
                "Media monitoring yang baik bukan sekadar mengumpulkan mention atau "
                "menghitung berapa kali sebuah kata kunci disebut. Nilainya ada pada "
                "konteks: siapa yang bicara, di kanal apa, dengan nada seperti apa, dan "
                "apakah volumenya sedang naik atau baru saja mereda. Tanpa konteks itu, "
                "angka mentah hanya menjadi kebisingan tambahan di meja kerja tim."
            )),
            ("h", "Kecepatan adalah keunggulan, bukan kemewahan"),
            ("p", (
                "Bagi brand, keterlambatan merespons isu pelanggan berarti kehilangan "
                "kepercayaan sebelum sempat menjelaskan duduk perkara. Bagi instansi "
                "publik, keterlambatan berarti kebijakan yang sudah dijalankan sebelum "
                "aspirasi masyarakat sempat didengar. Di kedua kasus, kecepatan mendengar "
                "menentukan kualitas keputusan yang diambil sesudahnya."
            )),
            ("p", (
                "PANTAU dibangun di atas prinsip ini: pengumpulan data berjalan "
                "real-time dan terjadwal dari media sosial, portal berita, RSS, dan "
                "sumber digital lain, dengan kata kunci dan domain yang dapat "
                "dikonfigurasi sesuai kebutuhan organisasi Anda — sehingga sinyal "
                "penting sampai ke meja Anda saat masih bisa ditindaklanjuti, bukan "
                "setelah menjadi berita."
            )),
        ],
    },
    {
        "slug": "mendeteksi-krisis-reputasi-sebelum-membesar",
        "title": "Mendeteksi krisis reputasi sebelum membesar",
        "excerpt": (
            "Krisis reputasi jarang muncul tiba-tiba. Ia meninggalkan jejak sinyal kecil "
            "yang sering terlewat karena tidak ada yang memantaunya secara sistematis."
        ),
        "category": "Reputasi",
        "read_minutes": 5,
        "body": [
            ("p", (
                "Sebagian besar krisis reputasi punya pola yang mirip: dimulai dari "
                "keluhan kecil di satu kanal, dibagikan ulang oleh segelintir akun "
                "berpengaruh, lalu meledak setelah media arus utama ikut memberitakan. "
                "Antara tahap pertama dan tahap terakhir itu biasanya ada jendela waktu "
                "yang cukup untuk merespons — asalkan ada yang memperhatikannya."
            )),
            ("h", "Masalahnya bukan data, tapi visibilitas"),
            ("p", (
                "Banyak organisasi sebenarnya punya cukup data untuk melihat krisis "
                "sejak dini: keluhan pelanggan, komentar di media sosial, forum diskusi. "
                "Yang sering hilang adalah kemampuan menyatukan sinyal-sinyal ini dan "
                "mengenali kapan sebuah lonjakan kecil berbeda dari fluktuasi normal "
                "harian."
            )),
            ("h", "Dari ambang batas ke eskalasi terkoordinasi"),
            ("p", (
                "Begitu sebuah topik melewati ambang batas yang wajar, yang dibutuhkan "
                "bukan lagi sekadar notifikasi, tapi ruang kerja bersama: siapa yang "
                "menindaklanjuti, respons apa yang sudah dikirim, dan bagaimana "
                "perkembangan sentimen setelah respons itu keluar. Tanpa ruang kerja "
                "semacam ini, krisis sering ditangani secara ad-hoc lewat pesan berantai "
                "yang sulit diaudit setelahnya."
            )),
            ("p", (
                "Fitur Peringatan & War Room PANTAU dirancang untuk jendela waktu ini: "
                "atur ambang peringatan sesuai konteks organisasi, eskalasikan isu "
                "penting ke tim yang tepat, dan catat setiap respons dalam satu ruang "
                "kendali bersama — sehingga penanganan krisis meninggalkan jejak yang "
                "bisa dievaluasi, bukan hanya percakapan yang menguap."
            )),
        ],
    },
    {
        "slug": "media-monitoring-untuk-pemerintah",
        "title": "Media monitoring untuk pemerintah: mendengar aspirasi, merancang kebijakan berbasis data",
        "excerpt": (
            "Instansi publik punya kewajiban mendengar warganya. Media monitoring "
            "membantu mengubah kewajiban itu dari formalitas menjadi praktik yang hidup."
        ),
        "category": "Pemerintahan",
        "read_minutes": 5,
        "body": [
            ("p", (
                "Kebijakan publik yang baik biasanya lahir dari dua arah: kajian teknis "
                "di dalam instansi, dan aspirasi masyarakat yang disampaikan lewat "
                "berbagai kanal — media sosial, portal berita daerah, forum warga. "
                "Tantangannya, arah kedua ini jauh lebih sulit dipantau secara "
                "sistematis dibanding arah pertama, terutama ketika volumenya besar dan "
                "tersebar di banyak platform."
            )),
            ("h", "Aspirasi yang tersebar butuh peta, bukan sekadar arsip"),
            ("p", (
                "Mengumpulkan sebutan tentang sebuah program adalah langkah awal. "
                "Langkah yang lebih penting adalah memetakan di wilayah mana respons "
                "paling positif, di wilayah mana keluhan menumpuk, dan isu apa yang "
                "mulai tumbuh sebelum sempat masuk ke rapat evaluasi. Tanpa pemetaan "
                "ini, instansi berisiko merespons isu yang sudah usang sambil melewatkan "
                "isu yang justru sedang membesar."
            )),
            ("h", "Netral, terukur, dan bisa dipertanggungjawabkan"),
            ("p", (
                "Media monitoring di ranah pemerintahan menuntut standar berbeda "
                "dibanding di dunia brand: data harus terisolasi dengan tegas dari "
                "kepentingan politik praktis, aksesnya perlu diatur berdasarkan peran, "
                "dan setiap analisis idealnya bisa ditelusuri kembali sumbernya. Ini "
                "bukan detail teknis semata — ini yang membuat hasil pemantauan layak "
                "dijadikan dasar kebijakan publik."
            )),
            ("p", (
                "PANTAU menyediakan intelijen regional hingga tingkat provinsi dan "
                "kabupaten/kota, brief eksekutif harian yang dapat ditinjau dan "
                "didukung rujukan regulasi, serta governance dengan isolasi tenant, "
                "akses berbasis peran, dan jejak audit — dirancang agar instansi "
                "pemerintah bisa mendengar aspirasi warganya tanpa mengorbankan tata "
                "kelola yang netral dan akuntabel."
            )),
        ],
    },
    {
        "slug": "dari-data-mentah-ke-keputusan",
        "title": "Dari data mentah ke keputusan: memahami sentimen & narasi publik",
        "excerpt": (
            "Ribuan sebutan per hari tidak ada artinya tanpa cara membacanya. Sentimen "
            "dan narasi adalah dua lensa yang mengubah angka menjadi pemahaman."
        ),
        "category": "Analisis",
        "read_minutes": 4,
        "body": [
            ("p", (
                "Angka jumlah sebutan sering jadi metrik pertama yang dilihat, padahal "
                "metrik ini paling mudah menyesatkan. Lonjakan sebutan bisa berarti "
                "kampanye berhasil, atau bisa berarti krisis sedang berlangsung — angka "
                "itu sendiri tidak membedakan keduanya."
            )),
            ("h", "Sentimen memberi arah, narasi memberi makna"),
            ("p", (
                "Sentimen — positif, negatif, netral, dan emosi dominan di baliknya — "
                "memberi tahu ke arah mana persepsi publik bergerak. Namun untuk "
                "memahami mengapa ia bergerak ke arah itu, dibutuhkan lapisan "
                "berikutnya: narasi. Tema apa yang sedang dominan, aktor mana yang "
                "menggerakkannya, dan berapa besar share of voice masing-masing pihak "
                "dalam percakapan tersebut."
            )),
            ("h", "Dari isu yang tumbuh ke isu yang mereda"),
            ("p", (
                "Isu publik punya siklus hidup. Melihat siklus ini — bukan hanya potret "
                "sesaat — memungkinkan tim membedakan isu yang sedang tumbuh dan perlu "
                "direspons segera, dari isu yang sebenarnya sudah mulai mereda dengan "
                "sendirinya. Salah membaca fase ini berarti membuang sumber daya untuk "
                "merespons sesuatu yang sudah selesai, atau justru mengabaikan sesuatu "
                "yang baru mulai."
            )),
            ("p", (
                "Kapabilitas Sentimen & Emosi serta Narasi & Isu di PANTAU dirancang "
                "untuk dua lapisan pembacaan ini sekaligus — memetakan tema, share of "
                "voice, dan aktor, sambil tetap memberi tim analis kendali untuk "
                "mengoreksi label AI dan mengelola taksonomi sesuai konteks organisasi."
            )),
        ],
    },
    {
        "slug": "mengenali-disinformasi-dan-aktivitas-terkoordinasi",
        "title": "Mengenali disinformasi dan aktivitas terkoordinasi (buzzer/bot) di ruang digital",
        "excerpt": (
            "Tidak semua lonjakan percakapan itu organik. Membedakan suara publik yang "
            "asli dari aktivitas terkoordinasi adalah keterampilan tersendiri."
        ),
        "category": "Integritas Informasi",
        "read_minutes": 5,
        "body": [
            ("p", (
                "Salah satu tantangan terbesar dalam membaca ruang digital hari ini "
                "adalah membedakan mana suara publik yang genuin dan mana aktivitas yang "
                "sengaja direkayasa untuk terlihat seperti suara publik. Buzzer, akun "
                "bot, dan jaringan amplifikasi terkoordinasi bisa membuat sebuah opini "
                "minoritas terlihat seperti pendapat mayoritas dalam hitungan jam."
            )),
            ("h", "Pola yang menyingkap koordinasi"),
            ("p", (
                "Aktivitas terkoordinasi biasanya meninggalkan pola yang tidak muncul "
                "pada percakapan organik: pesan yang nyaris identik disebar oleh banyak "
                "akun dalam rentang waktu sempit, akun-akun baru yang tiba-tiba aktif "
                "bersamaan pada satu isu, atau cluster akun yang selalu bergerak "
                "serempak pada topik yang berbeda-beda. Pola semacam ini sulit dilihat "
                "manusia satu per satu, tapi cukup jelas ketika dianalisis secara "
                "agregat."
            )),
            ("h", "Kenapa ini penting di luar urusan politik"),
            ("p", (
                "Deteksi koordinasi bukan hanya relevan untuk isu politik. Brand juga "
                "menghadapi kampanye negatif terkoordinasi dari pesaing atau pihak tak "
                "dikenal, dan instansi publik perlu memastikan masukan yang mereka "
                "gunakan sebagai dasar kebijakan benar-benar mencerminkan aspirasi "
                "warga, bukan hasil rekayasa segelintir pihak."
            )),
            ("p", (
                "Fitur Deteksi Koordinasi PANTAU dibangun untuk menemukan pola aktivitas "
                "tidak organik, kemiripan pesan antar akun, dan cluster akun yang "
                "bergerak serempak — membantu tim membedakan sinyal publik yang otentik "
                "dari kebisingan yang sengaja diciptakan."
            )),
        ],
    },
    {
        "slug": "dari-mendengar-ke-bertindak",
        "title": "Dari mendengar ke bertindak: membangun war room komunikasi krisis yang efektif",
        "excerpt": (
            "Mendengar sinyal lebih awal tidak banyak berguna jika organisasi tidak "
            "punya cara terstruktur untuk bertindak atasnya."
        ),
        "category": "Respons",
        "read_minutes": 4,
        "body": [
            ("p", (
                "Banyak organisasi sudah cukup baik dalam mengumpulkan data monitoring, "
                "tapi berhenti di situ. Dashboard penuh grafik dan angka, namun ketika "
                "krisis benar-benar terjadi, respons tetap berjalan lewat rangkaian "
                "pesan WhatsApp yang tersebar dan sulit ditelusuri ulang setelah "
                "krisisnya reda."
            )),
            ("h", "War room bukan sekadar ruang chat"),
            ("p", (
                "War room komunikasi krisis yang efektif menyatukan tiga hal dalam satu "
                "tempat: sinyal yang memicu perhatian, keputusan yang diambil oleh tim, "
                "dan hasil dari keputusan tersebut. Struktur ini penting bukan hanya "
                "saat krisis berlangsung, tapi juga sesudahnya — untuk evaluasi, "
                "pelaporan ke pimpinan, dan pembelajaran organisasi ke depan."
            )),
            ("h", "Dari respons individu ke respons tim"),
            ("p", (
                "Ketika penanganan krisis hanya bergantung pada satu-dua orang yang "
                "kebetulan melihat isunya lebih dulu, organisasi rentan kehilangan "
                "momentum begitu orang itu tidak tersedia. Ruang kerja bersama dengan "
                "peran dan izin yang jelas memastikan penanganan krisis tetap berjalan "
                "sebagai proses tim, bukan tindakan individu yang kebetulan sigap."
            )),
            ("p", (
                "PANTAU menyatukan pengumpulan data, analisis AI, dan War Room dalam "
                "satu sistem yang dapat diaudit — dilengkapi Brief Eksekutif harian "
                "serta Governance & Audit dengan akses berbasis peran dan jejak audit, "
                "sehingga setiap langkah dari mendengar sinyal sampai menindaklanjutinya "
                "tercatat dan bisa dipertanggungjawabkan."
            )),
        ],
    },
]

_ARTICLES_BY_SLUG = {article["slug"]: article for article in ARTICLES}


def get_article(slug):
    return _ARTICLES_BY_SLUG.get(slug)
