# 🏛️ Cetak Biru Konsep Menu & Arsitektur Project-Centric

Dokumen ini berisi rancangan struktur menu CLI dan arsitektur data **Project-Centric** untuk menyederhanakan antarmuka pengguna (*User Interface*) dan mengisolasi data per website serta per channel YouTube.

---

## 🌟 1. Menu Utama (5 Menu Ringkas + Clean Status List di Bawah)

```text
🏛️  AI SILO BUILDER & PUBLISHER
============================================================
▶ MENU UTAMA
------------------------------------------------------------
 ➔ [1]  🌐 Website Projects       (Silo, Artikel & Live Publishing per Web) ◀
    [2]  🎬 YouTube Channels       (Upload, Live Video, CTR & Metadata)
    [3]  📄 Global Articles Hub    (Arsip, Pencarian & Export Lintas Web)
    [4]  ⚙️ Global Settings        (AI Model, API Keys & Visual Style)
    [0]  🚪 Keluar
------------------------------------------------------------
 📌 STATUS SISTEM & INTEGRASI:
  • ✍️  Text AI   : gemini-3.5-flash (3 keys)
  • 🖼️  Images    : gpt-6-luna • Illustration (15 keys)
  • 🎬 YouTube   : 2 Channel (Soft Piano Rain, Elaina...) [2/2 OAuth Live]
  • 🌐 Website   : spotty [WordPress] (total 3 web)
------------------------------------------------------------
Pilih [↑/↓ + Enter] atau tekan angka/huruf:
```

---

## 🌐 2. Sub-Menu: `[1] Website Projects`

### Alur Langkah 1: Pemilihan Website (Workspace Picker)
```text
Daftar Website Terdaftar:
 [1] spotty (https://spottybreath.s2-tastewp.com) [WordPress Live]
 [2] Astro Tech Blog (D:/Websites/my-astro-site) [Astro Static]
 [0] ➕ Tambah Website Baru (WordPress / Astro)
 [B] ⬅️ Kembali ke Menu Utama
```

### Alur Langkah 2: Dashboard Website Terpilih (Contoh: `spotty`)
Seluruh operasi di bawah ini terisolasi untuk project website yang sedang dibuka:
```text
🌐 PROJECT: spotty (WordPress REST API)
================================================================
 [1] 🎯 Riset & Buat Arsitektur Silo Baru
     ➔ Riset keyword, grounding profil bisnis web ini, & rancang cluster
 [2] 📁 Kelola & Lanjutkan Silo Web Ini
     ➔ Lihat daftar Silo milik web ini & lanjutkan produksi artikel tertunda
 [3] 🚀 Publish Artikel ke Web Ini
     ➔ Kirim artikel draft lokal ke WordPress REST API / Sync ke Astro
 [4] 🔴 Kelola Post Live di Web Ini
     ➔ Tarik daftar artikel yang sudah terbit, edit live, & regenerate thumbnail
 [5] 🏢 Pengaturan Profil Bisnis & Grounding Web Ini
     ➔ Nama usaha, alamat, izin usaha, nomor kontak, daftar harga/layanan
 [6] 🔑 Pengaturan Kredensial Web Ini
     ➔ URL, Username, Application Password / Target Folder Astro
 [0] ⬅️ Ganti / Kembali ke Daftar Website
================================================================
```

---

## 🎬 3. Sub-Menu: `[2] YouTube Channels`

### Alur Langkah 1: Pemilihan Channel
```text
Daftar Channel YouTube:
 [1] Soft Piano Rain (@softpianorain) [🟢 Aktif / OAuth Live]
 [2] Elaina Yolande (@elainayolande)   [🟢 Aktif / OAuth Live]
 [0] ➕ Tambah Channel Baru (1-Click Google OAuth)
 [B] ⬅️ Kembali ke Menu Utama
```

### Alur Langkah 2: Dashboard Channel Terpilih (Contoh: `Soft Piano Rain`)
```text
🎬 CHANNEL: Soft Piano Rain [OAuth Live]
================================================================
 [1] 📹 Upload Video Baru (Resumable Chunked)
     ➔ Auto-detect file di folder `channels_youtube/Soft_Piano_Rain/videos/`
 [2] 🔴 Kelola Live Video di Channel Ini
     ➔ Tarik video live, AI CTR Regeneration judul, edit tags/desc, hapus video
 [3] 📝 Generate Metadata Pack AI
     ➔ Buat 5 variasi judul High-CTR, deskripsi hook, tags, & prompt thumbnail
 [4] 📢 Optimasi Bio / About Channel & Push Live
     ➔ Generate copywriting bio channel & langsung push update ke YouTube
 [5] 📂 Buka Folder Fisik Channel
     ➔ Akses cepat folder videos, thumbnails, metadata, dan profile
 [6] ⚙️ Pengaturan Niche & Tone Channel Ini
 [0] ⬅️ Ganti / Kembali ke Daftar Channel
================================================================
```

---

## 📄 4. Sub-Menu: `[3] Global Articles Hub`

Pusat pencarian dan ekspor lintas seluruh website:
```text
================================================================
 📄 GLOBAL ARTICLES & EXPORT HUB
================================================================
 [1] 🔍 Cari / Filter Artikel (Berdasarkan Judul, Niche, atau Status Terbit)
 [2] 📦 Export Universal WordPress WXR (.XML)
 [3] 📊 Riwayat & Log Publishing Global
 [0] ⬅️ Kembali ke Menu Utama
================================================================
```

---

## ⚙️ 5. Sub-Menu: `[4] Global Settings`

Pengaturan teknis AI dan sistem global:
```text
================================================================
 ⚙️ GLOBAL SYSTEM & AI SETTINGS
================================================================
 [1] 🤖 Google Gemini AI
     ➔ Ganti model aktif (Flash / Pro) & kelola multi-key rotation
 [2] 🎨 Kie.ai & Visual Style
     ➔ Pilih model gambar, ganti gaya visual featured image (Vector/3D/Line Art)
 [3] 🧠 Agnes AI
     ➔ Konfigurasi model teks & visi Agnes AI
 [4] 🔄 Multi-Model AI Pipeline
     ➔ Konfigurasi AI terpisah untuk Brief (Tahap 1), Draf (Tahap 2), Kurasi (Tahap 3)
 [0] ⬅️ Kembali ke Menu Utama
================================================================
```

---

## 📁 Rencana Struktur Direktori Project-Centric

```text
Silo/
├── config/                          # Kredensial & konfigurasi global AI
├── core/                            # Modul engine (ai, silo, youtube)
│
├── projects_web/                    # 🌐 Workspace Fisik per Website
│   ├── spotty/
│   │   ├── config.json              # URL, username, auth, setting publish
│   │   ├── business_profile.json    # Grounding profile usaha khusus web ini
│   │   ├── publish_log.json         # Log artikel yang sudah terbit di web ini
│   │   └── silos/                   # Folder Silo khusus website ini
│   │       ├── cara-membuat-pempek/
│   │       └── reksadana-pasar-uang/
│   └── astro_tech_blog/
│       └── ...
│
├── channels_youtube/                # 🎬 Workspace Fisik per Channel YouTube
│   ├── Soft_Piano_Rain/
│   └── Elaina_Yolande/
│
├── plan-menu.md                     # Cetak biru struktur menu
├── main.py                          # Entry point CLI
└── README.md
```
