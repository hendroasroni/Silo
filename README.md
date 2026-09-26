# 🏛️ AI Silo Content Architect & Multi-Site Publisher (WordPress & Astro)

Aplikasi Python berbasis CLI untuk meriset, merancang arsitektur **SEO Silo**, menulis artikel pilar & cluster mendalam, kurasi otomatis multi-model AI (**Google Gemini & GPT-6 Luna**), generate visual featured image otomatis (**Kie.ai Z-Image & Mesh Gradient**), serta **menerbitkan (push) artikel langsung ke berbagai website WordPress maupun Static Web Astro (Cloudflare Pages / Netlify / Vercel)**.

---

## 🌟 Fitur Utama

1. **🎯 Universal Multi-Site Publisher (WordPress & Astro)**:
   - **WordPress REST API**: Publish otomatis via Application Password, auto featured image, auto kategori ringkas, dan sinkronisasi SEO Meta (Rank Math & Yoast).
   - **Static Web Astro**: 100% kompatibel dengan Astro Content Collections (`src/content/blog/`), auto-copy WebP image ke `public/images/silo/`, dan opsi **Git Auto-Commit & Push** untuk trigger deploy otomatis.
2. **🎨 Kie.ai Art Director & Image Style Selector**:
   - Pilihan gaya visual featured image: **Ilustrasi Modern Vector & Flat Art** *(Rekomendasi Bersih & Bebas Glitch)*, **3D Isometric & Studio Render**, **Minimalist Line Art**, **Cyberpunk Tech**, dan **Photorealistic Photography**.
   - Otomatis convert ke **WebP murni (Quality 90)** dan fallback lokal instan ke **Mesh Gradient Glassmorphic Banner** jika tanpa API Key.
3. **🧠 Multi-Model AI Pipeline (Gemini & GPT-6 Luna)**:
   - Konfigurasi model terpisah untuk tiap tahapan (Tahap 1 Brief: Gemini Flash, Tahap 2 Draf: GPT-6 Luna / Gemini Pro, Tahap 3 Kurasi: Gemini Pro).
4. **🏢 Ground Truth Business Profile & Strict Knowledge Grounding**:
   - Artikel berbasis data valid profil bisnis (alamat, izin usaha, daftar harga, kontak, keunggulan nyata). AI dilarang keras mengarang data faktual usaha.
5. **🎯 Struktur SEO Silo Dinamis & Prioritas Rekomendasi**:
   - Riset 1 Artikel Pilar Utama + *N* Supporting Clusters dengan pemetaan Search Intent, Target Audience, dan peringkat prioritas penulisan.
6. **🔄 Two-Way Internal Linking & Semantic Anchor Text**:
   - Otomatis menghubungkan cluster ke pilar dan pilar ke cluster dengan anchor text variatif (Exact Match, LSI Semantik, Frasa Natural).
7. **📂 Resume Proyek & Global Single-Publish Protection**:
   - Lanjutkan pembuatan cluster yang pending kapan saja. Artikel yang sudah pernah dipublish terkunci otomatis agar tidak terduplikasi.

---

## 🚀 Panduan Teknis: Integrasi Website Astro

Sistem ini dirancang **Universal & Plug-and-Play** untuk project Astro mana pun (Astro 2.x, 3.x, 4.x, 5.x).

### 1. Struktur Standar Folder Project Astro
Pastikan project Astro Anda memiliki struktur folder standar:
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

### 2. Definisi Skema `src/content.config.ts` (Universal Zod Schema)
Gunakan skema koleksi standar berikut pada project Astro Anda agar kompatibel 100%:

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

### 3. Skema Frontmatter Markdown yang Dihasilkan
Setiap artikel yang dipublish ke Astro otomatis memiliki Frontmatter lengkap:
```yaml
---
title: "Judul Artikel Silo Terstruktur"
description: "Meta deskripsi yang dioptimasi untuk CTR pencarian Google..."
pubDate: 2026-09-26
date: 2026-09-26
author: "Tim Geoteknik SondirPro"
category: "Uji Tanah"
image: "/images/silo/slug-artikel.webp"
heroImage: "/images/silo/slug-artikel.webp"
coverImage: "/images/silo/slug-artikel.webp"
tags: ["sondir tanah", "Uji Tanah"]
siloRole: "Cluster"
draft: false
---

Konten artikel Markdown lengkap dengan internal link otomatis...
```

### 4. Cara Mendaftarkan Project Astro Baru di Menu Aplikasi
1. Jalankan `python main.py`
2. Masuk ke menu **`[6] Pengaturan Website`** ➔ **`[1] Tambah Website Baru`**
3. Pilih tipe **`[2] Static Astro / Cloudflare / Netlify`**
4. Masukkan input:
   - **Nama / Label:** Misal `SondirPro Astro`
   - **Path Folder Content:** Path absolut ke folder blog Markdown, misal:
     ```
     C:/Users/Hendro/astro-sondirpro/src/content/blog
     ```
   - **Path Folder Image:** *(Kosongkan untuk auto-detect di `public/images/silo`)*
   - **Domain / URL Live:** Misal `https://sondirpro.com`
   - **Git Auto-Push [Y/N]:** Pilih `Y` jika project terhubung ke GitHub / GitLab untuk auto-deploy di Cloudflare Pages/Netlify.

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

## ⚙️ Persyaratan Sistem & Instalasi

### 1. Prasyarat:
- Python 3.10+
- Library yang dibutuhkan:
```bash
pip install requests pillow google-genai
```

### 2. File Konfigurasi Kunci API:
- **`apikey.txt`**: Masukkan API key Google Gemini (satu key per baris untuk multi-key rotation).
- **`kie_apikey.txt`**: Masukkan API key Kie.ai (untuk Z-Image / GPT-6 Luna).

### 3. Menjalankan Aplikasi:
```bash
python main.py
```

---

## 📂 Struktur Output File Silo Lokal
Setiap topik Silo yang dibuat tersimpan rapi di folder `output/<seed-keyword>/`:
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
