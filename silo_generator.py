import json
import os
import re
from datetime import datetime

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')

class SiloGenerator:
    def __init__(self, gemini_client):
        self.client = gemini_client

    def research_silo_cluster(self, seed_keyword, language="Bahasa Indonesia", niche_context="Umum", cluster_count=6, business_profile=None, client=None):
        """
        Melakukan riset mendalam terhadap seed keyword, memetakan arsitektur Silo (Pillar + Supporting Clusters),
        dan memberikan rekomendasi prioritas pembuatan konten dengan jumlah cluster kustom serta grounding profil bisnis.
        """
        from wp_publisher import WordPressPublisher

        ai_client = client or self.client
        system_instruction = (
            "Anda adalah Master SEO Strategist & Topical Authority Specialist tingkat dunia. "
            "Tugas Anda adalah merancang arsitektur Silo Content yang saling terhubung untuk mendominasi peringkat Google."
        )

        grounding_context = ""
        if business_profile:
            grounding_context = f"\n{WordPressPublisher.format_profile_grounding_prompt(business_profile)}\n"

        prompt = f"""
Rancang arsitektur Silo Content berbasis SEO untuk topik/keyword utama: "{seed_keyword}".
Bahasa Target: {language}
Konteks Industri/Niche: {niche_context}
Jumlah Cluster Target: {cluster_count} artikel cluster pendukung
{grounding_context}
Arsitektur Silo WAJIB terdiri dari:
1. Satu (1) Artikel Pilar Utama (Pillar Page, Role: "Pillar") yang menjadi pusat otoritas topik (Core Topic).
2. Tepat {cluster_count} Artikel Pendukung (Supporting Cluster, Role: "Cluster") berupa longtail keyword yang menjawab search intent spesifik, variasi 'how-to', perbandingan, tips, atau studi kasus yang relevan dan menyalurkan link equity ke artikel pilar.

Total seluruh item dalam daftar harus berjumlah {cluster_count + 1} item (1 Pillar + {cluster_count} Clusters).

Kembalikan data dalam format JSON persis seperti skema berikut:
{{
  "seed_keyword": "{seed_keyword}",
  "silo_theme": "Nama kategori/tema silo yang RINGKAS & PADAT (WAJIB 1-3 kata saja untuk kategori WordPress, misal: 'Uji Tanah', 'Geoteknik', 'Investasi Reksadana', JANGAN kalimat panjang)",
  "topical_authority_goal": "Deskripsi singkat tujuan otoritas topik ini",
  "items": [
    {{
      "id": 1,
      "keyword": "Longtail atau seed keyword yang ditargetkan",
      "suggested_title": "Judul artikel SEO yang menarik dan CTR tinggi",
      "role": "Pillar" ATAU "Cluster",
      "search_intent": "Informational" / "Commercial" / "Transactional" / "Navigational",
      "competition_level": "Low" / "Medium" / "High",
      "target_audience": "Profil pembaca sasaran",
      "silo_role_description": "Peran artikel ini dalam silo dan bagaimana menghubungkan topik lainnya",
      "recommendation_rank": 1,
      "recommendation_reason": "Alasan mengapa topik ini sangat direkomendasikan untuk dibuat lebih awal",
      "is_recommended_default": true
    }}
  ]
}}

Pastikan:
- Tiap item memiliki nomor 'id' urut 1 sampai {cluster_count + 1}.
- Item 1 adalah Pillar utama, diikuti oleh {cluster_count} Cluster pendukung.
- Ranking rekomendasi diurutkan secara logis (Pillar biasanya rank 1, diikuti cluster dengan search intent tinggi atau low-hanging fruit).
- Nilai 'is_recommended_default' bernilai true untuk artikel paling krusial untuk fase awal.
"""
        res = ai_client.generate_json(prompt, system_instruction=system_instruction, temperature=0.3)
        if business_profile and isinstance(res, dict):
            res["business_profile"] = business_profile
        return res

    def expand_silo_clusters(self, silo_plan, new_target_count, language="Bahasa Indonesia", niche_context="Umum"):
        """
        Menambah atau mengubah jumlah cluster pada Silo Project yang sudah ada.
        Jika diperluas, Gemini meriset cluster-cluster baru yang unik dan belum ada sebelumnya.
        """
        existing_items = silo_plan.get("items", [])
        existing_clusters = [i for i in existing_items if i["role"].lower() != "pillar"]
        current_cluster_count = len(existing_clusters)

        if new_target_count == current_cluster_count:
            return silo_plan

        # JIKA MENGURANGI: potong hanya cluster pending yang di ujung (tidak menghapus yang sudah selesai dibuat)
        if new_target_count < current_cluster_count:
            pillars = [i for i in existing_items if i["role"].lower() == "pillar"]
            # Pertahankan pilar + cluster sebanyak new_target_count
            kept_clusters = existing_clusters[:new_target_count]
            silo_plan["items"] = pillars + kept_clusters
            # Re-index
            for idx, item in enumerate(silo_plan["items"], 1):
                item["id"] = idx
            self.save_silo_project(silo_plan, new_articles=[])
            return silo_plan

        # JIKA MENAMBAH: minta Gemini riset cluster baru sebanyak selisihnya
        needed = new_target_count - current_cluster_count
        system_instruction = (
            "Anda adalah Master SEO Strategist & Topical Authority Specialist tingkat dunia. "
            "Tugas Anda adalah memperluas arsitektur Silo Content dengan menambahkan cluster baru yang unik dan saling melengkapi."
        )

        existing_keywords = [f"- {i['keyword']} ({i['suggested_title']})" for i in existing_items]
        prompt = f"""
Topik Silo: "{silo_plan.get('seed_keyword')}"
Tema Silo: "{silo_plan.get('silo_theme')}"
Tujuan Otoritas: "{silo_plan.get('topical_authority_goal')}"
Bahasa: {language}

Daftar artikel yang SUDAH ADA di Silo saat ini:
{chr(10).join(existing_keywords)}

TUGAS:
Tambahkan tepat {needed} artikel Cluster Pendukung (Role: "Cluster") BARU yang:
1. Benar-benar unik dan BELUM PERNAH ADA di daftar di atas.
2. Membahas longtail keyword spesifik, sudut pandang berbeda, perbandingan, studi kasus, atau panduan teknis yang relevan.
3. Mendukung dan menyalurkan internal link ke artikel pilar.

Kembalikan format JSON:
{{
  "new_clusters": [
    {{
      "keyword": "Longtail keyword baru",
      "suggested_title": "Judul artikel SEO baru",
      "role": "Cluster",
      "search_intent": "Informational" / "Commercial" / "Transactional" / "Navigational",
      "competition_level": "Low" / "Medium" / "High",
      "target_audience": "Profil pembaca sasaran",
      "silo_role_description": "Peran dalam silo",
      "recommendation_rank": {len(existing_items) + 1},
      "recommendation_reason": "Alasan topik ini bermanfaat",
      "is_recommended_default": false
    }}
  ]
}}
"""
        res = self.client.generate_json(prompt, system_instruction=system_instruction, temperature=0.4)
        new_clusters = res.get("new_clusters", [])

        # Append new clusters
        start_id = len(existing_items) + 1
        for idx, cl in enumerate(new_clusters, start_id):
            cl["id"] = idx
            cl["role"] = "Cluster"
            existing_items.append(cl)

        silo_plan["items"] = existing_items
        self.save_silo_project(silo_plan, new_articles=[])
        return silo_plan

    def generate_content_brief(self, item, silo_plan, language="Bahasa Indonesia", business_profile=None, client=None):
        """
        Menghasilkan Content Brief & Outline mendalam untuk satu artikel terpilih.
        """
        from wp_publisher import WordPressPublisher

        ai_client = client or self.client
        system_instruction = (
            "Anda adalah Senior Content Strategist & Lead SEO Editor. "
            "Tugas Anda adalah menyusun Content Brief komprehensif berstandar enterprise."
        )

        profile = business_profile or silo_plan.get("business_profile")
        grounding_context = ""
        if profile:
            grounding_context = f"\n{WordPressPublisher.format_profile_grounding_prompt(profile)}\n"

        other_items = [
            {"id": i["id"], "keyword": i["keyword"], "title": i["suggested_title"], "role": i["role"]}
            for i in silo_plan.get("items", []) if i["id"] != item["id"]
        ]

        prompt = f"""
Susun Content Brief & Outline lengkap untuk topik berikut:
- Target Keyword: {item['keyword']}
- Judul Usulan: {item['suggested_title']}
- Peran Silo: {item['role']}
- Search Intent: {item['search_intent']}
- Tema Silo: {silo_plan.get('silo_theme', '')}
- Bahasa: {language}
{grounding_context}
Daftar artikel lain dalam Silo ini (untuk referensi internal link):
{json.dumps(other_items, ensure_ascii=False, indent=2)}

Format output JSON harus sebagai berikut:
{{
  "item_id": {item['id']},
  "primary_keyword": "{item['keyword']}",
  "meta_title": "Meta Title SEO (50-60 karakter, memikat)",
  "meta_description": "Meta Description persuasif (140-155 karakter dengan CTA halus)",
  "url_slug": "slug-url-ramah-seo",
  "target_word_count": "1500 - 2000 kata",
  "secondary_keywords": ["keyword turunan 1", "keyword turunan 2", "keyword turunan 3"],
  "semantic_entities_lsi": ["entitas semantik 1", "istilah industri 2", "LSI 3", "LSI 4"],
  "internal_link_strategy": {{
    "target_pillar_link": "Instruksi link ke artikel pilar utama",
    "target_cluster_links": ["Instruksi link ke cluster lain yang relevan"],
    "anchor_variations": {{
      "exact_keyword": "Anchor text kata kunci persis",
      "lsi_synonym": "Anchor text variasi sinonim / istilah semantik",
      "conversational_natural": "Anchor text frasa kalimat natural / mengalir"
    }}
  }},
  "outline": [
    {{
      "heading_tag": "H2",
      "heading_title": "Judul Sub-Bab H2",
      "key_talking_points": ["Poin bahasan A", "Poin bahasan B"],
      "include_element": "Tabel perbandingan / Listicle / Blockquote tips / None"
    }}
  ],
  "faq_questions": [
    "Pertanyaan FAQ 1 yang sering dicari pengguna?",
    "Pertanyaan FAQ 2 yang sering dicari pengguna?",
    "Pertanyaan FAQ 3 yang sering dicari pengguna?"
  ]
}}
"""
        return ai_client.generate_json(prompt, system_instruction=system_instruction, temperature=0.3)

    def write_article_draft(self, brief, silo_plan, tone="Profesional, Informatif, dan Mengalir Natural", language="Bahasa Indonesia", business_profile=None, client=None):
        """
        Menulis draf lengkap artikel berkualitas tinggi sesuai brief, struktur Silo, dan kaidah SEO modern.
        Menerapkan prinsip Zero Hallucination jika profil bisnis disediakan.
        """
        from wp_publisher import WordPressPublisher

        ai_client = client or self.client
        system_instruction = (
            "Anda adalah Penulis Konten SEO & Jurnalis Topik Ahli tingkat dunia. "
            "Gaya tulisan Anda sangat manusiawi, berbobot, mudah dipahami, tidak bertele-tele, bebas dari klise AI "
            "(jangan pernah gunakan kata klise seperti 'Dalam era digital yang serba cepat ini...', 'Tidak dapat dipungkiri bahwa...', 'Mari kita selami...'). "
            "Gunakan format Markdown yang kaya (H2, H3, bold, bullet points, tabel perbandingan, callout box) "
            "dan sisipkan placeholder internal link yang bervariasi secara alami untuk arsitektur Silo."
        )

        profile = business_profile or silo_plan.get("business_profile")
        grounding_prompt = WordPressPublisher.format_profile_grounding_prompt(profile)

        prompt = f"""
Tuliskan artikel lengkap dan mendalam dalam format Markdown murni berdasarkan Content Brief berikut:

{json.dumps(brief, ensure_ascii=False, indent=2)}

Tema Silo: {silo_plan.get('silo_theme', '')}
Tone of Voice: {tone}
Bahasa: {language}

{grounding_prompt}

PANDUAN PENULISAN WAJIB:
1. Mulai langsung dengan Judul H1 (# Judul Artikel).
2. Paragraf Pembuka (Hook): Langsung jawab inti pertanyaan pembaca dalam 2 kalimat pertama. Berikan alasan mengapa artikel ini adalah panduan paling lengkap.
3. Struktur Konten: Ikuti seluruh outline H2 dan H3 pada brief. Bahas setiap poin secara mendalam dan berikan contoh nyata, tips praktis, atau data logis.
4. Elemen Visual & Skimmable:
   - Buat minimal 1 TABEL perbandingan atau ringkasan data dalam format Markdown.
   - Gunakan bullet points atau numbered lists pada langkah-langkah / tips.
   - Gunakan blockquote (`> 💡 **Pro Tip:** ...`) untuk tips krusial.
5. Arsitektur Silo & Variasi Anchor Text (Anti-Overoptimization):
   - Sisipkan internal link ke artikel pilar atau cluster pendukung secara kontekstual di dalam paragraf.
   - WAJIB gunakan variasi anchor text (campuran exact keyword, sinonim LSI, dan frasa mengalir natural). Jangan gunakan kata kunci kaku berulang-ulang. Format: `[Variasi Anchor Text](slug-artikel)`.
6. Bagian FAQ:
   - Masukkan bagian H2 "Pertanyaan yang Sering Diajukan (FAQ)" dengan jawaban tuntas dan padat untuk pertanyaan di brief.
7. Penutup & CTA:
   - Buat kesimpulan ringkas yang memberikan langkah aksi nyata bagi pembaca sesuai panduan profil bisnis atau standar industri di atas.

Tuliskan seluruh isi artikel secara lengkap (BUKAN ringkasan/placeholder), dengan panjang optimal sesuai brief.
"""
        return ai_client.generate_text(prompt, system_instruction=system_instruction, temperature=0.7)

    def curate_and_polish_article(self, draft_markdown, brief, silo_plan, business_profile=None, client=None):
        """
        Tahap Kurasi & Quality Assurance:
        Gemini / GPT-5 bertindak sebagai Lead Editor untuk mengevaluasi draf, menilai kelayakan SEO, Readability,
        dan kepatuhan fakta bisnis (Zero Hallucination), lalu memoles teks menjadi versi final yang siap dipublikasikan.
        """
        from wp_publisher import WordPressPublisher

        ai_client = client or self.client
        system_instruction = (
            "Anda adalah Senior Editorial Director & Chief SEO Auditor. "
            "Tugas Anda adalah mengaudit, mengurasi, dan menyempurnakan artikel agar mencapai kualitas Tier-1 (Human-level perfection, Google Helpful Content compliant)."
        )

        profile = business_profile or silo_plan.get("business_profile")
        grounding_prompt = WordPressPublisher.format_profile_grounding_prompt(profile)

        prompt = f"""
Audit dan kurasi draf artikel berikut berdasarkan Content Brief, standar Google Helpful Content System, dan Fakta Bisnis:

--- DRAF ARTIKEL ---
{draft_markdown}
--- END DRAF ---

--- CONTENT BRIEF ---
Target Keyword: {brief.get('primary_keyword')}
Search Intent: {brief.get('meta_title')}
Internal Links Guide: {json.dumps(brief.get('internal_link_strategy', {}), ensure_ascii=False)}
--- END BRIEF ---

{grounding_prompt}

Lakukan 2 hal:
1. Evaluasi & Skor Kualitas (Skala 1 - 100):
   - Keterikatan dengan Search Intent (1-20)
   - Readability & Tone Alami / Bebas Klise AI (1-20)
   - Kedalaman Informasi & Nilai Tambah (1-20)
   - Struktur Heading & Format Skimmable (1-20)
   - Optimasi SEO, Silo Link Placement, & Kepatuhan Fakta Bisnis (1-20)
2. Poles dan Sempurnakan Draf (Polished Final Content):
   - Hapus kalimat pengisi (fluff) atau bahasa kaku.
   - Pastikan TIDAK ADA nomor telepon palsu atau alamat fiktif.
   - Perbaiki alur transisi antar paragraf.
   - Pastikan tabel dan format Markdown rapi dan konsisten.
   - Pastikan tautan internal link berada di kalimat yang mengalir natural.

Kembalikan hasil dalam format JSON:
{{
  "overall_score": 95,
  "scores": {{
    "search_intent_depth": 19,
    "human_readability": 19,
    "value_and_examples": 19,
    "formatting_and_structure": 19,
    "seo_and_silo_linking": 19
  }},
  "editorial_critique": [
    "Poin kelebihan draf",
    "Penyempurnaan yang telah dilakukan pada versi final"
  ],
  "curation_status": "LULUS_KURASI_PREMIUM",
  "final_article_markdown": "Versi Markdown lengkap yang sudah dipoles sempurna, siap publish."
}}
"""
        return ai_client.generate_json(prompt, system_instruction=system_instruction, temperature=0.3)

    def list_existing_silos(self, output_base_dir="output"):
        """
        Mendeteksi seluruh Silo Project yang tersimpan di folder output,
        dan menghitung progres kelengkapannya (artikel mana yang sudah/belum dibuat).
        """
        if not os.path.exists(output_base_dir):
            return []

        silo_projects = []
        for entry in os.listdir(output_base_dir):
            dir_path = os.path.join(output_base_dir, entry)
            if os.path.isdir(dir_path):
                meta_path = os.path.join(dir_path, "silo_metadata.json")
                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                        
                        silo_plan = meta.get("silo_plan", {})
                        existing_articles = meta.get("articles", [])
                        
                        completed_ids = set()
                        for a in existing_articles:
                            completed_ids.add(a.get("item_id"))

                        for file in os.listdir(dir_path):
                            if file.endswith(".md") and file != "SILO_BLUEPRINT.md":
                                try:
                                    prefix_id = int(file.split("_")[0])
                                    completed_ids.add(prefix_id)
                                except Exception:
                                    pass

                        all_items = silo_plan.get("items", [])
                        pending_items = [it for it in all_items if it["id"] not in completed_ids]

                        silo_projects.append({
                            "folder_name": entry,
                            "dir_path": dir_path,
                            "seed_keyword": silo_plan.get("seed_keyword", entry),
                            "silo_theme": silo_plan.get("silo_theme", entry),
                            "total_topics": len(all_items),
                            "completed_count": len(completed_ids),
                            "pending_count": len(pending_items),
                            "completed_ids": sorted(list(completed_ids)),
                            "pending_items": pending_items,
                            "silo_plan": silo_plan,
                            "existing_articles": existing_articles
                        })
                    except Exception:
                        continue

        return silo_projects

    def save_silo_project(self, silo_plan, new_articles=None, output_base_dir="output"):
        """
        Menyimpan artikel baru dan menggabungkannya secara konsisten dengan artikel yang sudah ada sebelumnya.
        Jika new_articles kosong, menginisialisasi / memperbarui silo_metadata.json & SILO_BLUEPRINT.md.
        """
        if new_articles is None:
            new_articles = []

        seed = silo_plan.get("seed_keyword", "silo_project")
        folder_name = slugify(seed)
        target_dir = os.path.join(output_base_dir, folder_name)
        os.makedirs(target_dir, exist_ok=True)

        json_path = os.path.join(target_dir, "silo_metadata.json")
        existing_articles_map = {}

        # Load existing articles if metadata exists
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    for a in old_data.get("articles", []):
                        existing_articles_map[a["item_id"]] = a
            except Exception:
                pass

        saved_files = []

        # 1. Simpan setiap artikel baru
        for art in new_articles:
            item_id = art["item_id"]
            slug = art["brief"].get("url_slug", f"article-{item_id}")
            file_name = f"{item_id:02d}_{slug}.md"
            file_path = os.path.join(target_dir, file_name)

            frontmatter = (
                "---\n"
                f"title: \"{art['brief'].get('meta_title', art['item']['suggested_title'])}\"\n"
                f"description: \"{art['brief'].get('meta_description', '')}\"\n"
                f"keyword: \"{art['item']['keyword']}\"\n"
                f"silo_role: \"{art['item']['role']}\"\n"
                f"silo_theme: \"{silo_plan.get('silo_theme', '')}\"\n"
                f"url_slug: \"{slug}\"\n"
                f"target_word_count: \"{art['brief'].get('target_word_count', '')}\"\n"
                f"curation_score: {art['curation'].get('overall_score', 0)}\n"
                f"created_at: \"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\"\n"
                "---\n\n"
            )

            full_content = frontmatter + art["curation"].get("final_article_markdown", art["draft"])

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(full_content)
            saved_files.append(file_path)

            existing_articles_map[item_id] = {
                "item_id": item_id,
                "item": art["item"],
                "brief": art["brief"],
                "curation_score": art["curation"].get("overall_score", 0),
                "editorial_critique": art["curation"].get("editorial_critique", [])
            }

        all_completed_articles = list(existing_articles_map.values())
        all_completed_articles.sort(key=lambda x: x["item_id"])

        # 2. Simpan / Perbarui SILO_BLUEPRINT.md
        blueprint_path = os.path.join(target_dir, "SILO_BLUEPRINT.md")
        with open(blueprint_path, "w", encoding="utf-8") as f:
            f.write(self._build_blueprint_markdown(silo_plan, all_completed_articles))
        saved_files.append(blueprint_path)

        # 3. Simpan / Perbarui silo_metadata.json
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "silo_plan": silo_plan,
                "articles": all_completed_articles
            }, f, ensure_ascii=False, indent=2)
        saved_files.append(json_path)

        return target_dir, saved_files

    def _build_blueprint_markdown(self, silo_plan, completed_articles):
        completed_ids = {a["item_id"]: a for a in completed_articles}
        
        md = []
        md.append(f"# 🏛️ Arsitektur Silo: {silo_plan.get('silo_theme', silo_plan.get('seed_keyword'))}\n")
        md.append(f"**Seed Keyword:** `{silo_plan.get('seed_keyword')}`  ")
        md.append(f"**Topical Authority Goal:** {silo_plan.get('topical_authority_goal', '')}  ")

        prof = silo_plan.get("business_profile")
        if prof and isinstance(prof, dict) and any(prof.values()):
            brand = prof.get("brand_name", "").strip()
            wa = prof.get("phone_wa", "").strip()
            area = prof.get("service_area", "").strip()
            pricing = prof.get("pricing_services", "").strip()
            md.append(f"**Brand Grounding:** `{brand if brand else 'Brand Resmi'}` | **WA:** `{wa}` | **Area:** `{area}`  ")
            if pricing:
                md.append(f"**Layanan & Tarif:** {pricing}  ")

        md.append(f"**Update Terakhir:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        md.append("---\n")
        md.append("## 📌 Struktur & Peta Internal Linking\n")
        md.append("| No | Role | Target Keyword | Judul Artikel | Status | Skor Kurasi | URL Slug |")
        md.append("|---|---|---|---|---|---|---|")

        for item in silo_plan.get("items", []):
            i_id = item["id"]
            if i_id in completed_ids:
                art = completed_ids[i_id]
                score = art.get("curation_score", "-")
                slug = art.get("brief", {}).get("url_slug", "-")
                status = "✅ Selesai Dibuat"
            else:
                score = "-"
                slug = slugify(item["keyword"])
                status = "⏳ Belum Dibuat"

            role_badge = "👑 **Pillar**" if item["role"].lower() == "pillar" else "🔗 *Cluster*"
            md.append(f"| {i_id} | {role_badge} | `{item['keyword']}` | {item['suggested_title']} | {status} | {score}/100 | `{slug}` |")

        md.append("\n---\n")
        md.append("## 🧭 Panduan Distribusi Link Equity (Silo Linking Rule)\n")
        md.append("1. **Cluster -> Pillar:** Semua artikel *Cluster* wajib memberikan minimal 1-2 link ke artikel *Pillar Utama* menggunakan variasi anchor text yang relevan.")
        md.append("2. **Pillar -> Cluster:** Artikel *Pillar* memuat daftar/sub-topik yang menautkan ke seluruh artikel *Cluster* pendukung.")
        md.append("3. **Cluster <-> Cluster (Sibling):** Artikel cluster yang berada dalam rumpun topik yang sama saling menautkan satu sama lain untuk memperkuat relevansi semantik.")
        md.append("\n---\n")
        md.append("## 📝 Ringkasan Kurasi Artikel yang Telah Selesai\n")

        for a in completed_articles:
            brief = a.get("brief", {})
            item = a.get("item", {})
            md.append(f"### #{a['item_id']:02d} - {brief.get('meta_title', item.get('suggested_title', ''))}")
            md.append(f"- **Role:** `{item.get('role', '')}` | **Keyword:** `{item.get('keyword', '')}`")
            md.append(f"- **Skor Kurasi:** **{a.get('curation_score', 0)}/100**")
            critique = a.get('editorial_critique', [])
            if critique:
                md.append("- **Catatan Redaksi:**")
                for c in critique:
                    md.append(f"  - {c}")
            md.append("")

        return "\n".join(md)
