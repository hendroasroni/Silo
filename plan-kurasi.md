# 📝 Cetak Biru Alur Pembuatan, Kurasi, dan Standar Kualitas Artikel
*(Blueprint & Technical Specification for Standalone Article Generator & Curation Tool)*

Dokumen ini memuat spesifikasi lengkap alur kerja (*workflow*), arsitektur *prompting*, mekanisme pemolesan redaksional, rubrik penilaian, dan skema data kurasi artikel. Dokumen ini dirancang sebagai acuan teknis independen apabila ingin mengembangkan **tools khusus/mandiri** untuk produksi dan kurasi konten.

---

## 📑 Daftar Isi
1. [Arsitektur Konseptual & Alur Pipeline](#1-arsitektur-konseptual--alur-pipeline)
2. [Tahap 1: Content Briefing & Dynamic Archetype Engine](#2-tahap-1-content-briefing--dynamic-archetype-engine)
3. [Tahap 2: Penulisan Draf (Deep Drafting & Zero Hallucination)](#3-tahap-2-penulisan-draf-deep-drafting--zero-hallucination)
4. [Tahap 3: Alur Kurasi Redaksional & Polishing Kualitas](#4-tahap-3-alur-kurasi-redaksional--polishing-kualitas)
5. [Standar & Rubrik Penilaian Kurasi (Skala 1 - 100)](#5-standar--rubrik-penilaian-kurasi-skala-1---100)
6. [Skema Data & Output JSON Kurator](#6-skema-data--output-json-kurator)
7. [Blueprint Teknis untuk Pengembangan Standalone Tool](#7-blueprint-teknis-untuk-pengembangan-standalone-tool)

---

## 1. Arsitektur Konseptual & Alur Pipeline

Setiap artikel diproses melalui pipeline 3-tahap sekuensial yang saling terisolasi. Hal ini memastikan model AI fokus pada satu peran spesifik pada setiap fase:

```text
[ Input Topik & Profil Bisnis ]
             │
             ▼
┌──────────────────────────────────────────────┐
│  TAHAP 1: Strategic Content Briefing        │
│  - Peran: Senior Content Strategist          │
│  - Pemilihan 1 dari 8 Arketipe Konten        │
│  - Pemetaan Search Intent & Outline H2/H3    │
│  - Strategi Anchor Text 3 Variasi            │
└──────────────────────┬───────────────────────┘
                       │ Brief JSON
                       ▼
┌──────────────────────────────────────────────┐
│  TAHAP 2: Deep Drafting (Penulisan Draf)     │
│  - Peran: Jurnalis Topik Ahli                │
│  - Hook 2 kalimat pertama                    │
│  - Anti-Klise AI & Grounding Fakta Bisnis    │
│  - Elemen Visual (Tabel, Resep, Callout Box) │
└──────────────────────┬───────────────────────┘
                       │ Draf Markdown
                       ▼
┌──────────────────────────────────────────────┐
│  TAHAP 3: Lead Editorial Curation & Polishing│
│  - Peran: Chief SEO Auditor & Lead Editor    │
│  - Audit Rubrik 5 Pilar (Skor 1 - 100)       │
│  - Fluff Removal & Perapian Transisi         │
│  - Verifikasi Tautan Internal & Fakta Bisnis │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
[ Output Final: Polished Markdown Siap Publish ]
```

---

## 2. Tahap 1: Content Briefing & Dynamic Archetype Engine

### 🎭 8 Arketipe Konten Dinamis (*Dynamic Content Archetype*)
Untuk menghindari format artikel yang kaku dan seragam, sistem secara cerdas menetapkan format anatomi artikel berdasarkan *Search Intent*:

| Nama Arketipe | Kriteria Pemilihan & Search Intent | Elemen Format Wajib |
|---|---|---|
| **1. `comparison_head_to_head`** | Topik komparasi ("A vs B", "Perbedaan X dan Y", "Mana yang lebih baik") | Minimal 1 tabel komparasi 6–8 parameter teknis, box pro & kontra, panduan memilih skenario A vs B, kesimpulan verdict objektif. |
| **2. `step_by_step_workflow`** | Alur kerja, prosedur teknis, atau izin bertahap ("Cara Melakukan X", "Syarat PBG") | Tahapan bernomor (Tahap 1 ➔ Tahap 2), checklist dokumen/alat persiapan, callout peringatan fatal: `> ⚠️ **Peringatan / Kesalahan Fatal:**`. |
| **3. `buyers_guide_pricing`** | Biaya, tarif, estimasi harga jasa, atau panduan memilih vendor | Tabel rentang harga pasar realistis, simulasi perhitungan biaya proyek, tips menghindari *hidden costs*. |
| **4. `problem_solution_diagnostic`** | Bahaya, risiko, diagnosis kerusakan, atau mitigasi darurat | Gejala lapangan, analisis akar masalah (*Root Cause Analysis*), langkah mitigasi darurat & pencegahan permanen. |
| **5. `ultimate_pillar_guide`** | **WAJIB untuk artikel Pilar** (Pusat Otoritas Topik) | *Executive Summary* di awal, cakupan fundamental 360° (definisi, regulasi, metode, evaluasi), hub internal linking ke seluruh cluster. |
| **6. `deep_technical_explainer`** | Konsep teknis rumit, rumus, atau fungsi alat berat/laboratorium | Terjemahan konsep sulit ke analogi sederhana bahasa awam, box "Fakta Kunci & Parameter Teknis". |
| **7. `actionable_listicle_insights`** | Kumpulan tips kunci, faktor penting, atau wawasan praktis | Poin bernilai tinggi dengan ulasan mendalam, box *key takeaways* di setiap akhir bab. |
| **8. `legal_compliance_guide`** | Regulasi pemerintah, standar SNI/ISO, atau perizinan legalitas | Acuan pasal/regulasi resmi, checklist tabel kepatuhan dokumen wajib. |

### 🔗 Strategi Internal Linking 3 Dimensi (Anti-Overoptimization)
Setiap brief mewajibkan 3 variasi *anchor text* agar tautan tidak dianggap manipulasi mesin pencari:
1. **Exact Keyword:** Kata kunci pencarian persis target artikel tujuan.
2. **LSI Synonym:** Istilah semantik turunan / sinonim industri.
3. **Conversational Natural:** Frasa kalimat mengalir bebas yang kontekstual dengan alinea baca.

---

## 3. Tahap 2: Penulisan Draf (Deep Drafting & Zero Hallucination)

### 📌 Standar Aturan Penulisan
1. **Paragraf Pembuka (*Direct Answer Hook*):**
   * Langsung menjawab inti pertanyaan pengguna dalam **2 kalimat pertama**.
   * Memberikan justifikasi otoritas mengapa artikel ini adalah panduan paling terpercaya.
2. **Kaidah Anti-Klise AI (*No Robotic Fluff*):**
   * DILARANG KERAS menggunakan frasa klise AI seperti:
     * ❌ *"Dalam era digital yang serba cepat ini..."*
     * ❌ *"Tidak dapat dipungkiri bahwa..."*
     * ❌ *"Mari kita selami lebih dalam..."*
     * ❌ *"Dalam artikel ini, kita akan membahas..."*
3. **Ground Truth Business Knowledge (*Zero Hallucination*):**
   * **Jika Profil Bisnis Diberikan:** Gunakan data nama brand, nomor WhatsApp resmi, alamat kantor, daftar legalitas, dan rentang tarif resmi sebagai fakta absolut. AI dilarang keras mengarang nomor WhatsApp/alamat alternatif.
   * **Jika Profil Bisnis Tidak Ada:** AI bertindak sebagai jurnalis independen yang netral, menggunakan estimasi rata-rata industri yang logis di Indonesia tanpa mencantumkan kontak fiktif.
4. **Struktur Markdown Skimmable:**
   * Wajib memuat minimal 1 **Tabel Markdown** yang terstruktur rapi.
   * Jika artikel bertema Resep/Kuliner: Wajib membagi bahan ke dalam sub-kategori spesifik (Bahan Utama, Bumbu Halus, Bumbu Pelengkap) dengan format tebal (**Nama Bahan:** `Takaran`) dan dilengkapi tabel ringkasan bahan.
   * Menggunakan blockquote untuk informasi penting:
     * `> 💡 **Pro Tip:** [Tips praktis lapangan]`
     * `> ⚠️ **Catatan Penting:** [Peringatan atau risiko]`

---

## 4. Tahap 3: Alur Kurasi Redaksional & Polishing Kualitas

Tahap kurasi tidak hanya memberikan nilai evaluasi, melainkan **langsung memoles dan memperbaiki artikel** secara otonom (*Automated Self-Correction & Polishing*).

```text
[ Draf Mentah Tahap 2 ]
           │
           ▼
[ Evaluasi Audit Kualitas ] ➔ Cek 5 Pilar Penilaian & Google Helpful Content
           │
           ▼
[ Pemolesan Teks (Polishing) ]
  ├── 1. Fluff Removal (Hapus kata pengisi & pengulangan hampa)
  ├── 2. Smooth Transitions (Perhalus perpindahan antar paragraf)
  ├── 3. Structured Data Align (Rapikan tabel Markdown & daftar takaran)
  └── 4. Link & Fact Sanity Check (Pastikan anchor text natural & nol data palsu)
           │
           ▼
[ Output: Skor 1-100, Critique Notes, & Final Markdown ]
```

---

## 5. Standar & Rubrik Penilaian Kurasi (Skala 1 - 100)

AI Kurator mengevaluasi draf menggunakan rubrik 5 pilar dengan bobot setara (masing-masing 1 - 20 poin):

| No | Pilar Kriteria | Bobot | Aspek Standar yang Dinilai |
|:---:|---|:---:|---|
| **1** | **Search Intent Depth** | **1 - 20** | Seberapa tepat artikel menjawab maksud utama pencarian pengguna? Menghindari penyimpangan topik (*topic drift*) dan memberikan kepuasan jawaban menyeluruh. |
| **2** | **Human Readability & Natural Tone** | **1 - 20** | Keluwesan bahasa manusia, kekayaan kosa kata, variasi panjang kalimat, serta 100% bebas dari frasa klise robotik AI. |
| **3** | **Value, Insights, & Examples** | **1 - 20** | Keberadaan studi kasus riil, analogi logis, tips praktis, data numerik yang masuk akal, dan panduan aplikatif di lapangan. |
| **4** | **Formatting & Skimmability** | **1 - 20** | Hierarki heading (H1, H2, H3), keberadaan tabel Markdown yang proporsional, daftar berpoin/angka, dan kotak *callout* pro-tip. |
| **5** | **SEO, Silo Links, & Fact Integrity** | **1 - 20** | Penempatan *internal link* secara kontekstual, variasi *anchor text*, serta kepatuhan ketat terhadap fakta bisnis (*Zero Hallucination*). |

### 🏆 Klasifikasi Status Kelulusan
* **Skor 90 – 100 : `LULUS_KURASI_PREMIUM`** (Standar tertinggi, siap terbit langsung).
* **Skor 80 – 89  : `LULUS_STANDAR`** (Cukup layak, siap terbit dengan sedikit polesan).
* **Skor < 80    : `PERLU_REVISI`** (Draf tidak memenuhi standar kedalaman atau melanggar kaidah penulisan).

---

## 6. Skema Data & Output JSON Kurator

Model kurator mengembalikan respons dalam format JSON terstruktur yang memisahkan skor audit, catatan kritik, dan teks final artikel:

```json
{
  "overall_score": 95,
  "scores": {
    "search_intent_depth": 19,
    "human_readability": 19,
    "value_and_examples": 19,
    "formatting_and_structure": 19,
    "seo_and_silo_linking": 19
  },
  "editorial_critique": [
    "Paragraf pembuka sangat tajam dan langsung menjawab maksud pencarian pembaca.",
    "Tabel komparasi parameter teknis telah dirapikan dan format takaran resep diseragamkan.",
    "Internal link berhasil disisipkan secara natural tanpa merusak ritme kalimat."
  ],
  "curation_status": "LULUS_KURASI_PREMIUM",
  "final_article_markdown": "# Judul Artikel Lengkap...\n\nParagraf pembuka yang memikat...\n\n## Sub-Bab H2..."
}
```

---

## 7. Blueprint Teknis untuk Pengembangan Standalone Tool

Jika Anda ingin membungkus alur ini menjadi **aplikasi khusus (Dedicated CLI / GUI / Web Service / FastAPI)**, berikut rekomendasi pembagian modulnya:

### 📁 Struktur Modul Mandiri yang Direkomendasikan
```text
article_curator_tool/
├── config/
│   ├── api_keys.json              # Gemini, OpenAI, Claude, atau Kie.ai keys
│   └── business_profile.json      # Ground truth identitas brand / usaha
├── engine/
│   ├── brief_generator.py         # Module Tahap 1: Dynamic Archetype & Brief
│   ├── article_drafter.py         # Module Tahap 2: Deep Drafting
│   ├── content_curator.py         # Module Tahap 3: Lead Editorial & Polisher
│   └── prompts.py                 # Kumpulan System Prompts & User Prompts
├── storage/
│   ├── checkpoints/               # Checkpoint bertahap per item untuk resume
│   └── output/                    # Hasil akhir artikel (.md, .json)
├── app.py                         # Entry point (CLI interaktif / FastAPI backend)
└── requirements.txt
```

### 💡 Fitur Kunci yang Wajib Diterapkan pada Tool Baru:
1. **Granular Checkpointing:** Simpan hasil tiap tahap (`item_X_stage_1.json`, `item_X_stage_2.json`, `item_X_stage_3.json`). Jika API terputus atau koneksi drop, proses bisa di-*resume* tanpa membakar ulang token AI.
2. **Multi-Model Support:** Kemampuan memilih model berbeda untuk tugas berbeda:
   * *Drafting:* Model dengan kreativitas tinggi dan kosakata kaya (misal: GPT-4o / GPT-6 Luna / Gemini Pro).
   * *Curation:* Model dengan *reasoning* analitis tinggi dan evaluasi kritis (misal: Gemini 3.7 Pro / Claude 3.5 Sonnet).
3. **Strict JSON Parsing Fallback:** Gunakan *regex markdown stripper* untuk mengekstrak JSON dari AI jika model mengembalikan pembungkus triple-backtick (````json ... ````).
