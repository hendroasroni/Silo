# 🏛️ AI Silo Content Architect & Multi-Channel YouTube Creator Suite

Aplikasi Python berbasis CLI multifungsi untuk:
1. **🌐 Web Content Publisher**: Meriset dan merancang arsitektur **SEO Silo**, menulis artikel pilar & cluster mendalam, kurasi multi-model AI (**Google Gemini & GPT-6 Luna**), generate visual featured image otomatis (**Kie.ai Z-Image & Agnes AI**), serta menerbitkan artikel ke **WordPress (REST API & XML WXR)** dan **Static Web Astro (Cloudflare Pages / Netlify / Vercel)**.
2. **🎬 YouTube Creator & Multi-Channel Suite**: Manajemen banyak channel YouTube secara terisolasi via **YouTube Data API v3**, otentikasi **1-Click Google OAuth**, optimasi metadata AI (Judul High-CTR, Deskripsi Hook, Tags, Rekomendasi Thumbnail), **Resumable Live Video Upload**, manajemen & optimasi video live, serta sinkronisasi halaman About channel.

---

## 🌟 Fitur Utama

### 🎬 A. YouTube Creator & Multi-Channel Suite
1. **👥 Multi-Channel Management & Dedicated Physical Workspace**:
   - Setiap channel memiliki folder fisik mandiri di `channels_youtube/<nama_channel>/`.
   - Subfolder terisolasi: `videos/` (video mentah/siap upload), `thumbnails/` (cover/gambar), `metadata_packs/` (paket judul & deskripsi tersimpan).
   - Setiap channel memiliki file `profile.json`, `token.json`, dan opsional `client_secret.json` sendiri sehingga tidak terjadi tabrakan data antar channel.
2. **🚀 1-Click Google OAuth Integration**:
   - Tambah channel baru langsung via browser 1-Click login (`prompt="select_account"`).
   - Otomatis menarik nama channel asli, Channel ID, custom handle (`@channel`), total subscriber, total view, dan bio.
3. **📹 Live Resumable Video Upload (Chunked Upload)**:
   - Upload video lokal (`.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`) langsung ke YouTube dengan progress bar real-time (`[████████░░░░] 65%`).
   - Auto-detect file video yang ditaruh di folder `channels_youtube/<channel>/videos/`.
   - Opsi privasi: **Public**, **Unlisted**, atau **Private / Draft**.
   - Pilihan metadata: AI Generator otomatis, manual input, atau memuat dari file `.txt`.
   - Dukungan pemasangan *Custom Thumbnail* langsung saat upload.
4. **🔴 Kelola & Update Live Video Channel**:
   - Tarik daftar video live channel secara real-time dari YouTube.
   - **AI CTR Regeneration**: Analisis kelemahan judul lama dan generate 5 variasi judul High-CTR baru, deskripsi hook, dan tags baru dengan opsi langsung push live ke YouTube.
   - Edit langsung Judul, Deskripsi, Tags, dan upload thumbnail baru ke video live.
   - **🗑️ Hapus Video Permanen**: Hapus video dari channel YouTube dengan proteksi konfirmasi ketik `'HAPUS'`.
5. **📢 Optimasi Halaman About & Push Live**:
   - Generate copywriting bio channel panjang, bio pendek, tagline branding, saran playlist, dan kata kunci YouTube Studio.
   - Opsi langsung update live deskripsi channel ke YouTube API.

---

### 🌐 B. Universal Web Publisher (WordPress & Astro)
1. **🎯 Universal Multi-Site Publisher**:
   - **WordPress REST API**: Publish otomatis via Application Password, auto featured image, auto kategori ringkas, dan sinkronisasi SEO Meta (Rank Math & Yoast).
   - **Static Web Astro**: 100% kompatibel dengan Astro Content Collections (`src/content/blog/`), auto-copy WebP image ke `public/images/silo/`, dan opsi **Git Auto-Commit & Push** untuk trigger deploy otomatis di Cloudflare Pages / Netlify.
   - **Export WordPress WXR XML**: Export artikel lokal lengkap dengan meta tag dan media untuk diimpor ke WordPress tanpa koneksi REST API.
2. **🎨 Kie.ai Art Director & Image Style Selector**:
   - Pilihan gaya visual featured image: **Ilustrasi Modern Vector & Flat Art** *(Rekomendasi Bersih & Bebas Glitch)*, **3D Isometric & Studio Render**, **Minimalist Line Art**, **Cyberpunk Tech**, dan **Photorealistic Photography**.
   - Otomatis convert ke **WebP murni (Quality 90)** dan fallback lokal instan ke **Mesh Gradient Glassmorphic Banner** jika tanpa API Key.
3. **🧠 Multi-Model AI Pipeline**:
   - Konfigurasi model terpisah untuk tiap tahapan (Tahap 1 Brief: Gemini Flash, Tahap 2 Draf: GPT-6 Luna / Gemini Pro / Agnes AI, Tahap 3 Kurasi: Gemini Pro).
4. **🏢 Ground Truth Business Profile & Strict Knowledge Grounding**:
   - Artikel berbasis data valid profil bisnis (alamat, izin usaha, daftar harga, kontak, keunggulan nyata). AI dilarang keras mengarang data faktual usaha.
5. **🎯 Struktur SEO Silo Dinamis & Two-Way Internal Linking**:
   - Riset 1 Artikel Pilar Utama + *N* Supporting Clusters dengan pemetaan Search Intent, Target Audience, dan peringkat prioritas penulisan.
   - Otomatis menghubungkan cluster ke pilar dan pilar ke cluster dengan anchor text variatif (Exact Match, LSI Semantik, Frasa Natural).

---

## 📁 Struktur Workspace Channel YouTube (`channels_youtube/`)

Setiap channel yang ditambahkan memiliki folder fisik terisolasi:

```text
channels_youtube/
├── 📁 Soft_Piano_Rain/
│   ├── 📄 profile.json            # Identitas channel (niche, target audiens, CTA, tone, tagline)
│   ├── 🔑 token.json              # Token OAuth aktif channel ini
│   ├── 🔑 client_secret.json      # (Opsional) jika channel punya Google Cloud Project sendiri
│   ├── 📁 videos/                 # Taruh video mentah (.mp4/.mov/.mkv) di sini
│   ├── 📁 thumbnails/             # Taruh cover/thumbnail (.jpg/.webp/.png) di sini
│   └── 📁 metadata_packs/         # File teks & JSON hasil generate AI tersimpan di sini
│
└── 📁 Channel_Bisnis_Digital/
    ├── 📄 profile.json
    ├── 🔑 token.json
    ├── 📁 videos/
    ├── 📁 thumbnails/
    └── 📁 metadata_packs/
```

---

## 📁 Struktur Arsitektur Modular Project

```text
Silo/
├── 📁 config/                       # Kumpulan Konfigurasi & Kredensial Private
│   ├── apikey.txt                   # Google Gemini API Keys
│   ├── agnes_apikey.txt             # Agnes AI API Keys
│   ├── kie_apikey.txt               # Kie.ai API Keys
│   ├── client_secret.json           # Google OAuth 2.0 Client Secret
│   ├── gemini_config.json           # Setting model Gemini aktif
│   ├── kie_config.json              # Setting model & style Kie.ai
│   ├── pipeline_config.json         # Konfigurasi engine AI per tahap
│   ├── wp_config.json               # Konfigurasi WordPress & Astro
│   ├── wp_publish_log.json          # Riwayat publish artikel web
│   ├── youtube_channels.json        # Database channel YouTube terdaftar
│   └── 📁 examples/                 # Template contoh file config (.example)
│
├── 📁 core/                         # Modul Engine Utama (Python Packages)
│   ├── 📁 ai/                       # Integrasi Multi-Model AI & Image Engine
│   │   ├── gemini_api.py            # Google Gemini Flash & Pro Engine
│   │   ├── agnes_api.py             # Agnes AI Text & Vision Engine
│   │   ├── kie_chat_api.py          # Kie.ai GPT-6 Luna Engine
│   │   ├── kie_image_api.py         # Kie.ai Z-Image & Mesh Gradient Generator
│   │   └── ai_pipeline.py           # 3-Stage Pipeline Orchestrator
│   ├── 📁 silo/                     # Engine SEO Silo & Publishing Web
│   │   ├── silo_generator.py        # Silo Keyword Research & Article Generator
│   │   └── wp_publisher.py          # WordPress REST API & Astro Content Collections
│   ├── 📁 youtube/                  # Engine Multi-Channel YouTube & Live API
│   │   ├── youtube_generator.py     # Workspace Manager & Metadata AI Generator
│   │   └── youtube_live_api.py      # Resumable Uploader & YouTube Data API v3
│   └── config_utils.py              # Centralized Path & Configuration Resolver
│
├── 📁 projects_web/                 # 🌐 Workspace Fisik Dedicated per Website Project
│   ├── 📁 spotty/                   # Project Web 1: silos/, config.json, business_profile.json
│   ├── 📁 victorious/               # Project Web 2: silos/, config.json, business_profile.json
│   └── 📁 SondirPro__Astro_/        # Project Web 3: silos/, config.json, business_profile.json
│
├── 📁 channels_youtube/             # 🎬 Workspace Fisik Dedicated per Channel YouTube
│   ├── 📁 Soft_Piano_Rain/          # Channel 1: videos/, thumbnails/, metadata_packs/, profile.json, token.json
│   └── 📁 Elaina_Yolande/           # Channel 2: videos/, thumbnails/, metadata_packs/, profile.json, token.json
│
├── 📁 output/                       # Output Silo Web / Artikel Blog (.md & .webp)
├── 📄 main.py                       # CLI Terminal User Interface (5 Menu Utama)
├── 📄 plan-menu.md                  # Cetak Biru Konsep Menu & Arsitektur Project-Centric
├── 📄 README.md                     # Dokumentasi Lengkap Aplikasi
└── 📄 .gitignore                    # Proteksi Kredensial & Cache
```

---

## ⚙️ Persyaratan Sistem & Instalasi

### 1. Prasyarat:
- Python 3.10+
- Library yang dibutuhkan:
```bash
pip install requests pillow google-genai google-api-python-client google-auth-oauthlib google-auth-httplib2
```
*(Opsional untuk pembuatan video dummy lokal)*: [FFmpeg](https://ffmpeg.org/).

### 2. Kredensial & File API Key:
- **`config/apikey.txt`**: Masukkan API key Google Gemini (satu key per baris untuk multi-key rotation).
- **`config/kie_apikey.txt`**: Masukkan API key Kie.ai (untuk Z-Image / GPT-6 Luna).
- **`config/agnes_apikey.txt`**: Masukkan API key Agnes AI.
- **`config/client_secret.json`**: Unduh Kredensial OAuth 2.0 (Desktop App) dari [Google Cloud Console](https://console.cloud.google.com/) dengan **YouTube Data API v3** aktif.

*(Sistem otomatis mendeteksi file kredensial baik di folder `config/` maupun di root directory).*

### 3. Menjalankan Aplikasi:
```bash
python main.py
```

---

## 🚀 Panduan Teknis: Integrasi YouTube OAuth 2.0

1. Buka [Google Cloud Console](https://console.cloud.google.com/) dan buat project baru.
2. Aktifkan **YouTube Data API v3** di menu **APIs & Services ➔ Library**.
3. Di menu **OAuth consent screen**, pilih tipe *External*, isi nama aplikasi dan email developer. Tambahkan scope: `https://www.googleapis.com/auth/youtube.force-ssl`.
4. Di menu **Credentials**, klik **+ Create Credentials ➔ OAuth client ID**.
5. Pilih Application Type: **Desktop app**.
6. Unduh JSON kredensial dan simpan di root folder aplikasi dengan nama **`client_secret.json`**.
7. Di Silo Builder, buka menu **`[8] 🎬 YouTube` ➔ `[5] Ganti / Kelola Multi-Channel` ➔ `[2] Tambah Channel YouTube Baru` ➔ `[1] 🚀 Login Google Otomatis`**.

---

## 🚀 Panduan Teknis: Integrasi Website Astro

Sistem ini kompatibel dengan Astro 2.x, 3.x, 4.x, dan 5.x.

### 1. Struktur Folder Astro
```text
my-astro-project/
├── public/
│   └── images/
│       └── silo/                <-- Gambar WebP otomatis disimpan di sini
├── src/
│   ├── content/
│   │   └── blog/                <-- File Markdown (.md) otomatis disimpan di sini
│   └── content.config.ts        <-- Definisi skema Content Collection
├── astro.config.mjs
└── package.json
```

### 2. Definisi Skema `src/content.config.ts`
```typescript
import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const blog = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/blog' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.coerce.date(),
    date: z.coerce.date().optional(),
    author: z.string().default('Tim Redaksi'),
    category: z.string().default('Umum'),
    image: z.string().optional(),
    heroImage: z.string().optional(),
    coverImage: z.string().optional(),
    tags: z.array(z.string()).default([]),
    siloRole: z.string().optional(),
    draft: z.boolean().default(false),
  }),
});

export const collections = { blog };
```

---

## 🌐 Panduan Teknis: Integrasi Website WordPress

1. Masuk ke **WP Admin ➔ Users ➔ Profile**.
2. Scroll ke bagian **Application Passwords**, buat nama baru (misal `SiloApp`), lalu klik **Add New Application Password**.
3. Salin password 16 karakter (misal: `xxxx xxxx xxxx xxxx`).
4. Di aplikasi Silo Builder, pilih menu **`[6] Pengaturan Website` ➔ `[1] Tambah Website Baru` ➔ `[1] WordPress (REST API)`**.
5. Masukkan URL Web, Username Admin, dan Application Password.

---

## 🎨 Pengaturan Gaya Visual Featured Image (Kie.ai)

Buka menu **`[7] Pengaturan AI & API Key` ➔ `[2] Model & API Key Kie.ai` ➔ `[5] Ganti Gaya Visual`**:

| No | Gaya Visual | Karakteristik Output | Cocok Untuk |
|---|---|---|---|
| **1** | **Ilustrasi Modern Vector & Flat Art** *(Default)* | Garis bersih, komposisi geometris elegan, palet harmonis, flat vector. | Semua artikel web, teknik, edukasi, & bisnis. |
| **2** | **3D Isometric & Studio Render** | Render 3D isometric Claymorphism, lighting studio lembut. | Topik teknologi, software, arsitektur, & panduan teknis. |
| **3** | **Minimalist Line Art & Duotone** | Outline minimalis dengan aksen warna duotone elegan. | Artikel riset, analisis, & editorial. |
| **4** | **Futuristic Tech / Cyber Glow** | Aksen neon cyber, dark theme kontras tinggi. | Topik AI, automasi, & infrastruktur digital. |
| **5** | **Photorealistic Photography** | Gaya fotografi komersial 8k klasik. | Mode foto nyata. |

---

## 📂 Struktur Output File Silo Web Lokal
Setiap topik Silo web yang dibuat tersimpan rapi di folder `output/<seed-keyword>/`:
```text
output/jasa-sondir-tanah-jogja/
├── images/
│   ├── 01_jasa-sondir-tanah-jogja.webp
│   └── 04_perbedaan-sondir-dan-boring.webp
├── 01_jasa-sondir-tanah-jogja.md
├── 04_perbedaan-sondir-dan-boring.md
├── SILO_BLUEPRINT.md
└── silo_metadata.json
```
