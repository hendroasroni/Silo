# 📋 Rencana Audit & Prosedur Pengujian Menyeluruh (Comprehensive Test Plan)

Dokumen ini adalah panduan standar operasional (*Standard Operating Procedure / SOP*) untuk mengaudit dan menguji setiap menu, sub-menu, integrasi API, serta alur data pada aplikasi **AI Silo Content Architect & Multi-Channel YouTube Suite** secara 1 per 1.

---

## 🎯 Tujuan Audit
1. Memastikan seluruh **5 Menu Utama** dan sub-menunya dapat diakses tanpa hambatan (`0 NameError / 0 KeyError`).
2. Memverifikasi isolasi data **Project-Centric** (`projects_web/` dan `channels_youtube/`) berjalan 100% independen tanpa saling mencemari.
3. Memastikan integrasi API eksternal (**Google Gemini**, **Kie.ai**, **Agnes AI**, **WordPress REST API**, dan **YouTube Data API v3**) berfungsi secara live dan responsif.
4. Memvalidasi sistem fallback otomatis (contoh: Mesh Gradient saat Kie.ai offline, rotasi API key saat limit).

---

## 🧭 Matriks Pengujian Menu (Checklist Table)

| No | Modul / Menu | Sub-Fitur yang Diuji | Status Target | Catatan Verifikasi |
|---|---|---|:---:|---|
| **1.1** | Website Projects | Pemilihan & Tampilan Daftar Web | `[ ]` | Badge status tipe (`[WP]`/`[Astro]`) dan aktif |
| **1.2** | Website Projects | Tambah Website Baru (WP & Astro) | `[ ]` | Tersimpan di `config/` dan folder fisik `projects_web/` |
| **1.3** | Website Projects | Dashboard Project Website Terpilih | `[ ]` | Menampilkan path workspace, statistik Silo & artikel |
| **1.4** | Website Projects | Riset & Buat Silo Baru (Web-Centric) | `[ ]` | Grounding profil bisnis otomatis, simpan ke `projects_web/<slug>/silos/` |
| **1.5** | Website Projects | Kelola & Lanjutkan Silo Web Ini | `[ ]` | Resume artikel cluster tertunda, ubah jumlah cluster |
| **1.6** | Website Projects | Publish Artikel ke Website Ini | `[ ]` | REST API (Draft/Publish/Drip) & Astro Sync |
| **1.7** | Website Projects | Kelola Postingan Live WordPress | `[ ]` | Tarik artikel live, ganti judul/thumbnail dari REST API |
| **1.8** | Website Projects | Profil Bisnis & Knowledge Grounding | `[ ]` | Simpan NAP, legalitas, tarif ke `business_profile.json` |
| **1.9** | Website Projects | Pengaturan Kredensial & Uji Koneksi | `[ ]` | Uji koneksi sukses, update kredensial, hapus web |
| **2.1** | YouTube Channels | Multi-Channel Switcher & Badges | `[ ]` | Menampilkan semua channel `[🟢 Aktif / OAuth Live]` |
| **2.2** | YouTube Channels | Tambah Channel (1-Click OAuth) | `[ ]` | Auto buka browser, auto tarik nama & identitas live |
| **2.3** | YouTube Channels | Upload Video Resumable Chunked | `[ ]` | Auto-detect file video & thumbnail, progress bar |
| **2.4** | YouTube Channels | Kelola Live Video di YouTube | `[ ]` | Tarik video live, AI CTR Regeneration, edit/hapus video |
| **2.5** | YouTube Channels | Generate Metadata Pack AI | `[ ]` | 5 variasi judul CTR, deskripsi hook, tags, thumbnail prompt |
| **2.6** | YouTube Channels | Optimasi Bio / About Channel | `[ ]` | AI copywriting bio channel & push live ke YouTube |
| **2.7** | YouTube Channels | Akses Folder Fisik Channel | `[ ]` | Membuka folder `channels_youtube/<channel>/` |
| **3.1** | Global Articles Hub | Inventori & Pencarian Seluruh Artikel | `[ ]` | Pindai semua Silo lintas website & filter status |
| **3.2** | Global Articles Hub | Export Universal WordPress WXR (.XML)| `[ ]` | Generate file XML 1.2 valid siap import di WP |
| **3.3** | Global Articles Hub | Kirim Artikel Pending Lintas Web | `[ ]` | Pindai artikel pending global dan pilih target web |
| **4.1** | Global Settings | Pengaturan Google Gemini AI | `[ ]` | Ganti model (Flash/Pro) & rotasi multi API key |
| **4.2** | Global Settings | Pengaturan Kie.ai & Visual Style | `[ ]` | Ganti model, ubah gaya visual featured image (Vector/3D/Line) |
| **4.3** | Global Settings | Pengaturan Agnes AI | `[ ]` | Konfigurasi model teks & visi Agnes AI |
| **4.4** | Global Settings | Multi-Model AI Pipeline Orchestrator | `[ ]` | Pemetaan model AI independen per Tahap 1, 2, dan 3 |
| **5.1** | Main Exit | Keluar dari Aplikasi | `[ ]` | Terminasi proses CLI bersih tanpa residual task |

---

## 🔬 Prosedur Pengujian Detail Langkah Demi Langkah

### 🌐 MODUL 1: WEBSITE PROJECTS & SILO WORKSPACE

#### Skenario 1.1: Buka Daftar Project Website
1. Di Menu Utama, tekan `[1]`.
2. **Kriteria Kelulusan**:
   - Tampil daftar seluruh website yang terdaftar (contoh: `spotty`, `victorious`, `SondirPro`).
   - Setiap website memiliki label tipe `[WP]` atau `[Astro]`.
   - Website aktif memiliki tanda `[Aktif]`.

#### Skenario 1.2: Buka Dashboard Project Tertentu
1. Pilih salah satu website (contoh: tekan `[1]` untuk `spotty`).
2. **Kriteria Kelulusan**:
   - Judul Dashboard menampilkan: `🌐 PROJECT WEBSITE: SPOTTY`.
   - Baris *Workspace* mengarah ke `projects_web/spotty`.
   - Menampilkan total koleksi Silo yang sudah ada di website tersebut beserta total artikelnya.

#### Skenario 1.3: Riset & Produksi Silo Baru di Website Ini
1. Dari Dashboard Website, pilih `[1] Riset & Buat Arsitektur Silo Baru`.
2. Masukkan Keyword Utama (misal: `alat uji penetrasi konus`).
3. Tentukan jumlah cluster (misal: `4`).
4. **Kriteria Kelulusan**:
   - Sistem secara otomatis menggunakan profil bisnis website tersebut (tanpa perlu ditanya ulang).
   - Gemini AI memetakan 1 Pilar + 4 Cluster pendukung.
   - Folder baru `projects_web/spotty/silos/alat-uji-penetrasi-konus/` otomatis tercipta di disk lengkap dengan `silo_metadata.json` dan `SILO_BLUEPRINT.md`.
   - Eksekusi 4 tahap (Brief ➔ Draf ➔ Kurasi ➔ Featured Image) tersimpan langsung di dalam subfolder website tersebut.

#### Skenario 1.4: Lanjutkan Silo yang Tertunda
1. Dari Dashboard Website, pilih `[2] Kelola & Lanjutkan Silo Web Ini`.
2. Pilih Silo yang memiliki status *Pending*.
3. Pilih opsi `[1] Tulis Sisa Cluster`.
4. **Kriteria Kelulusan**:
   - Sistem melanjutkan artikel yang belum selesai tanpa menulis ulang artikel yang sudah ada.
   - File markdown artikel baru tersimpan di folder Silo website terkait.

#### Skenario 1.5: Publish Artikel ke Website
1. Dari Dashboard Website, pilih `[3] Publish Artikel ke Web Ini`.
2. **Kriteria Kelulusan**:
   - Sistem memindai artikel lokal di website tersebut.
   - Menguji koneksi REST API / Folder Astro.
   - Artikel berhasil diterbitkan sebagai `Draft` / `Publish` dan tercatat di publish log lokal.

#### Skenario 1.6: Kelola Profil Bisnis Website
1. Dari Dashboard Website, pilih `[5] Profil Bisnis & Knowledge Grounding Web Ini`.
2. Isi atau perbarui salah satu field (misal: *Nomor WhatsApp* atau *Tarif Resmi*).
3. Simpan perubahan.
4. **Kriteria Kelulusan**:
   - File `projects_web/<website>/business_profile.json` terupdate.
   - Konfigurasi `config/wp_config.json` juga tersinkronisasi otomatis.

---

### 🎬 MODUL 2: YOUTUBE MULTI-CHANNEL SUITE

#### Skenario 2.1: Pemilihan Channel & Multi-OAuth Status
1. Di Menu Utama, pilih `[2] 🎬 YouTube Channels`.
2. **Kriteria Kelulusan**:
   - Menampilkan seluruh channel yang terhubung (`Soft Piano Rain`, `Elaina Yolande`).
   - Seluruh channel berstatus `[🟢 Aktif / OAuth Live]`.

#### Skenario 2.2: Upload Video (Resumable Chunked)
1. Buka channel target (misal: `Soft Piano Rain`).
2. Masuk ke menu `[1] 📹 Upload Video Baru`.
3. **Kriteria Kelulusan**:
   - Sistem otomatis mendeteksi file video yang ditaruh di `channels_youtube/Soft_Piano_Rain/videos/`.
   - Menampilkan opsi pemilihan metadata (AI Generator / File .txt).
   - Upload berjalan dengan status bar chunked progress hingga `100% SUKSES`.
   - Video live terdaftar di YouTube Studio sebagai Draft/Private/Public.

#### Skenario 2.3: Kelola Live Video & AI CTR Regeneration
1. Dari Dashboard Channel, pilih `[2] 🔴 Kelola Live Video di Channel Ini`.
2. Pilih salah satu video yang ada di daftar live.
3. Pilih opsi `[1] 🚀 AI CTR Regeneration Judul & Deskripsi`.
4. **Kriteria Kelulusan**:
   - AI menganalisis video dan memberikan 5 variasi judul baru dengan hook CTR tinggi.
   - Opsi *Push Live ke YouTube* berhasil memperbarui judul video secara langsung di server YouTube.

#### Skenario 2.4: Optimasi About / Bio Channel
1. Dari Dashboard Channel, pilih `[4] 📢 Optimasi Bio / About Channel & Push Live`.
2. Generate copywriting bio channel baru.
3. **Kriteria Kelulusan**:
   - Tampil rekomendasi bio channel, tagline, dan target keywords.
   - Jika disetujui, update live berhasil mengubah deskripsi channel di YouTube.

---

### 📄 MODUL 3: GLOBAL ARTICLES HUB

#### Skenario 3.1: Inventori & Pencarian Global
1. Di Menu Utama, pilih `[3] 📄 Global Articles Hub` ➔ `[1] Inventori Seluruh Artikel`.
2. **Kriteria Kelulusan**:
   - Menampilkan total gabungan artikel dari semua website di `projects_web/` dan legacy `output/`.
   - Menampilkan pemisahan status jelas antara artikel *Pending* dan artikel *Published*.

#### Skenario 3.2: Export Universal WordPress XML (WXR)
1. Di Global Articles Hub, pilih `[2] 📦 Export Universal WordPress WXR (.XML)`.
2. Pilih salah satu topik Silo dari daftar.
3. **Kriteria Kelulusan**:
   - File `.xml` berhasil di-generate di folder Silo terkait.
   - File XML valid berstandar WXR 1.2 lengkap dengan meta tag dan link media.

---

### ⚙️ MODUL 4: GLOBAL SETTINGS

#### Skenario 4.1: Pengaturan Model & Multi-Key Gemini
1. Di Menu Utama, pilih `[4] ⚙️ Global Settings` ➔ `[1] Google Gemini AI`.
2. Ganti model default (misal dari `gemini-3.5-flash` ke `gemini-3.8-flash` atau `gemini-3.7-pro`).
3. **Kriteria Kelulusan**:
   - Model aktif pada status bar menu utama langsung berubah.
   - File `config/gemini_config.json` terupdate.

#### Skenario 4.2: Pengaturan Gaya Visual Featured Image (Kie.ai)
1. Di Global Settings, pilih `[2] Kie.ai & Visual Style` ➔ `[5] Ganti Gaya Visual`.
2. Pilih salah satu style (misal: *3D Isometric & Studio Render* atau *Minimalist Line Art*).
3. **Kriteria Kelulusan**:
   - Gaya visual aktif terupdate di `config/kie_config.json`.
   - Pembuatan gambar selanjutnya menggunakan visual blueprint sesuai style terpilih.

---

## 🛠️ Automated Quick Smoke Test Command

Untuk melakukan pengujian otomatis (*Automated Health Check*) seluruh modul dalam 1 perintah cepat di terminal, jalankan:

```bash
python -c "
import sys
if sys.stdout.encoding != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass

from core.ai import GeminiClient, AgnesClient, KieChatClient, KieImageClient
from core.youtube import YouTubeProfileManager, YouTubeLiveClient
from core.silo import SiloGenerator, WordPressPublisher

print('🧪 MENJALANKAN SMOKE TEST KESEHATAN SISTEM...')

# 1. AI Test
gc = GeminiClient()
print('✔ Gemini AI       :', gc.get_preferred_model(), f'({len(gc.api_keys)} Keys)')

# 2. Web Projects Test
wp = WordPressPublisher()
print('✔ Website Projects:', len(wp.get_sites()), 'Web terdaftar di projects_web/')

# 3. YouTube Multi-Channel Test
yp = YouTubeProfileManager()
yl = YouTubeLiveClient()
live_cnt = sum(1 for p in yp.get_profiles() if yl.has_saved_token(p.get('id')))
print('✔ YouTube Channels:', f'{len(yp.get_profiles())} Channel ({live_cnt} OAuth Live)')

print('🎉 SELURUH CORE ENGINE & WORKSPACE NORMAL 100%!')
"
```

---

## 📝 Rekomendasi Alur Pengujian Mandiri

1. **Jalankan Aplikasi**: Ketik `python main.py` di terminal.
2. **Coba Modul 1 (Website Projects)**: Masuk ke salah satu website, buat 1 topik Silo baru berisi 2-3 cluster, dan periksa foldernya di `projects_web/<website>/silos/`.
3. **Coba Modul 2 (YouTube Channels)**: Buka salah satu channel, periksa identitas channel live, dan coba generate metadata pack.
4. **Coba Modul 3 (Global Articles)**: Lihat inventori artikel global dan coba fitur export XML.
5. **Coba Modul 4 (Settings)**: Beralih model Gemini atau gaya visual Kie.ai untuk memastikan preferensi tersimpan.
