import os
import json
import time
import requests
from datetime import datetime
from core.config_utils import get_web_project_dir, clean_slug

BANK_FILENAME = "keyword_discovery_bank.json"

class KeywordDiscoveryManager:
    def __init__(self, wp_publisher=None):
        self.wp = wp_publisher

    def get_bank_path(self, site):
        ws_dir = get_web_project_dir(site)
        return os.path.join(ws_dir, BANK_FILENAME)

    def load_bank(self, site):
        bank_path = self.get_bank_path(site)
        if os.path.exists(bank_path):
            try:
                with open(bank_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        
        site_id = site.get("id", "default") if isinstance(site, dict) else str(site)
        site_name = site.get("name", "Website") if isinstance(site, dict) else str(site)
        
        return {
            "site_id": site_id,
            "site_name": site_name,
            "last_discovered_at": None,
            "total_keywords": 0,
            "pending_count": 0,
            "processed_count": 0,
            "keywords": []
        }

    def save_bank(self, site, bank_data):
        bank_path = self.get_bank_path(site)
        os.makedirs(os.path.dirname(bank_path), exist_ok=True)
        
        # Recalculate stats
        keywords = bank_data.get("keywords", [])
        pending = [k for k in keywords if k.get("status") == "pending"]
        processed = [k for k in keywords if k.get("status") == "processed"]
        
        bank_data["total_keywords"] = len(keywords)
        bank_data["pending_count"] = len(pending)
        bank_data["processed_count"] = len(processed)
        
        try:
            with open(bank_path, "w", encoding="utf-8") as f:
                json.dump(bank_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def scan_website_footprint(self, site):
        """
        Memindai seluruh jejak konten website yang sudah ada:
        - Profil bisnis (niche, brand, deskripsi layanan)
        - Seluruh Silo lokal (Pillar, Cluster, dan Keyword di folder silos/)
        - Postingan Live WordPress jika terhubung
        """
        footprint = {
            "site_name": site.get("name", ""),
            "site_url": site.get("wp_url") or site.get("content_dir", ""),
            "niche": "Umum",
            "brand_name": "",
            "services": "",
            "notes": "",
            "existing_pillars": [],
            "existing_clusters": [],
            "all_existing_keywords": set(),
            "existing_titles": []
        }

        # 1. Profil Bisnis
        prof = site.get("profile", {})
        if not prof and self.wp:
            prof = self.wp.get_business_profile(site.get("id"))
        
        if prof:
            footprint["brand_name"] = prof.get("brand_name", "")
            footprint["niche"] = prof.get("niche_description") or prof.get("services") or "Spesialis Konstruksi & Layanan Terkait"
            footprint["services"] = prof.get("services", "")
            footprint["notes"] = prof.get("custom_notes", "")

        # 2. Silo Lokal
        ws_dir = get_web_project_dir(site)
        silos_dir = os.path.join(ws_dir, "silos")
        if os.path.exists(silos_dir):
            for item in os.listdir(silos_dir):
                silo_path = os.path.join(silos_dir, item)
                if os.path.isdir(silo_path) and item not in ["images", "temp_images"]:
                    plan_file = os.path.join(silo_path, "silo_plan.json")
                    if os.path.exists(plan_file):
                        try:
                            with open(plan_file, "r", encoding="utf-8") as pf:
                                pdata = json.load(pf)
                                seed_kw = pdata.get("seed_keyword", item)
                                footprint["existing_pillars"].append(seed_kw)
                                footprint["all_existing_keywords"].add(seed_kw.lower())
                                
                                for itm in pdata.get("items", []):
                                    ikw = itm.get("keyword", "")
                                    ititle = itm.get("suggested_title", "")
                                    if ikw:
                                        footprint["all_existing_keywords"].add(ikw.lower())
                                    if ititle:
                                        footprint["existing_titles"].append(ititle)
                                    if itm.get("role", "").lower() != "pillar" and ikw:
                                        footprint["existing_clusters"].append({
                                            "keyword": ikw,
                                            "parent_pillar": seed_kw
                                        })
                        except Exception:
                            pass
                    
                    # Juga scan file .md yang sudah jadi
                    for fname in os.listdir(silo_path):
                        if fname.endswith(".md") and fname != "SILO_BLUEPRINT.md":
                            clean_name = fname.replace(".md", "")
                            parts = clean_name.split("_", 1)
                            slug_kw = parts[1].replace("-", " ") if len(parts) > 1 else parts[0].replace("-", " ")
                            footprint["all_existing_keywords"].add(slug_kw.lower())

        # 3. Postingan Live WP (Scan cepat via REST API jika tipe WordPress)
        if site.get("type") != "astro" and site.get("wp_url"):
            try:
                wp_url = site["wp_url"].rstrip("/")
                resp = requests.get(f"{wp_url}/wp-json/wp/v2/posts?per_page=50&_fields=title,slug", timeout=5)
                if resp.status_code == 200:
                    for post in resp.json():
                        title_rendered = post.get("title", {}).get("rendered", "")
                        slug_rendered = post.get("slug", "").replace("-", " ")
                        if title_rendered:
                            footprint["existing_titles"].append(title_rendered)
                        if slug_rendered:
                            footprint["all_existing_keywords"].add(slug_rendered.lower())
            except Exception:
                pass

        footprint["all_existing_keywords"] = list(footprint["all_existing_keywords"])
        return footprint

    def discover_topical_gaps(self, site, client, count=15):
        """
        Menggunakan Gemini AI untuk menganalisis jejak topik website saat ini,
        menemukan 'Topical Gap' (Pillar Baru) & 'Cluster Expansion' (Sub-topik turunan baru),
        serta otomatis menyimpannya ke database Bank Ide.
        """
        footprint = self.scan_website_footprint(site)
        bank = self.load_bank(site)
        
        # Tambahkan juga keyword yang sudah ada di Bank agar tidak di-generate ulang
        existing_in_bank = [k.get("keyword", "").lower() for k in bank.get("keywords", [])]
        all_blacklist = set(footprint["all_existing_keywords"] + existing_in_bank)

        system_instruction = (
            "Anda adalah Senior SEO & Topical Authority Architect kelas dunia. "
            "Tugas Anda adalah menganalisis arsitektur konten website yang sudah ada, menemukan 'Topical Gaps' (celah topik yang belum terisi), "
            "dan merekomendasikan daftar keyword baru yang potensial untuk meningkatkan Topical Authority di mesin pencari Google. "
            "SANGAT PENTING: JANGAN PERNAH menyarankan keyword yang sudah ada di daftar Blacklist / Konten Eksisting (Zero Cannibalization)."
        )

        prompt = f"""
ANILISIS WEBSITE TARGET:
- Nama Website   : {footprint['site_name']}
- Niche & Fokus  : {footprint['niche']}
- Brand / USP    : {footprint['brand_name']}
- Layanan / Fakta: {footprint['services']}

JEJAK KONTEN YANG SUDAH ADA DI WEB (JANGAN DIBUAT ULANG / BLACKLIST):
- Daftar Pillar Eksisting : {json.dumps(footprint['existing_pillars'], ensure_ascii=False)}
- Daftar Keyword Terpakai : {json.dumps(list(all_blacklist)[:40], ensure_ascii=False)}
- Contoh Judul Eksisting  : {json.dumps(footprint['existing_titles'][:15], ensure_ascii=False)}

INSTRUKSI DISCOVERY:
Rekomendasikan tepat {count} keyword pencarian baru (Bahasa Indonesia) yang sangat relevan dan dicari audiens target:
1. 'pillar_baru': Sub-niche atau topik utama baru yang belum pernah dibahas sama sekali di website ini (Bisa dibuat 1 Silo baru).
2. 'cluster_expansion': Keyword turunan spesifik / longtail baru yang memperkuat salah satu Pillar yang sudah ada (misal: studi kasus, perbandingan, cara hitung, standar SNI, biaya, troubleshooting).

Kembalikan HANYA format JSON valid tanpa markdown seperti berikut:
{{
  "summary_analysis": "Analisis singkat 1-2 kalimat mengenai celah topical authority website ini.",
  "recommended_keywords": [
    {{
      "keyword": "contoh keyword baru tanpa tanda kutip",
      "type": "pillar_baru",
      "parent_pillar": null,
      "search_intent": "Informational / Komersial / Panduan",
      "authority_value": "Sangat Tinggi / Tinggi / Sedang",
      "reason": "Alasan singkat mengapa topik ini penting bagi niche web ini"
    }},
    {{
      "keyword": "contoh keyword turunan spesifik",
      "type": "cluster_expansion",
      "parent_pillar": "nama-pillar-induk",
      "search_intent": "Spesifikasi Teknis / Tutorial",
      "authority_value": "Tinggi",
      "reason": "Memperkuat otoritas teknis pillar induk"
    }}
  ]
}}
"""

        result_json = client.generate_json(prompt, system_instruction=system_instruction, temperature=0.5)
        
        raw_recommendations = result_json.get("recommended_keywords", [])
        now_iso = datetime.now().isoformat()
        
        newly_added = []
        existing_keywords_bank = {k["keyword"].lower(): k for k in bank.get("keywords", [])}
        
        for item in raw_recommendations:
            kw_text = item.get("keyword", "").strip().lower()
            if kw_text and kw_text not in existing_keywords_bank and kw_text not in [k.lower() for k in all_blacklist]:
                new_entry = {
                    "id": f"kw_{int(time.time())}_{len(bank['keywords']) + len(newly_added) + 1}",
                    "keyword": item.get("keyword", "").strip(),
                    "type": item.get("type", "pillar_baru"),
                    "parent_pillar": item.get("parent_pillar"),
                    "search_intent": item.get("search_intent", "Informational"),
                    "authority_value": item.get("authority_value", "Tinggi"),
                    "reason": item.get("reason", ""),
                    "status": "pending",
                    "discovered_at": now_iso,
                    "processed_at": null if False else None,
                    "silo_folder": None
                }
                newly_added.append(new_entry)
                bank["keywords"].append(new_entry)
        
        bank["last_discovered_at"] = now_iso
        bank["last_analysis_summary"] = result_json.get("summary_analysis", "")
        self.save_bank(site, bank)
        
        return newly_added, bank

    def mark_keywords_processed(self, site, keyword_list, silo_folder=None):
        """
        Menandai satu atau beberapa keyword di bank menjadi 'processed'
        setelah berhasil dibuatkan Silo / Artikelnya.
        """
        if not keyword_list:
            return 0

        bank = self.load_bank(site)
        processed_set = set(k.strip().lower() for k in keyword_list if k)
        updated_count = 0
        now_iso = datetime.now().isoformat()

        for item in bank.get("keywords", []):
            if item.get("keyword", "").strip().lower() in processed_set:
                item["status"] = "processed"
                item["processed_at"] = now_iso
                if silo_folder:
                    item["silo_folder"] = silo_folder
                updated_count += 1

        if updated_count > 0:
            self.save_bank(site, bank)
        return updated_count

    def get_pending_keywords(self, site):
        bank = self.load_bank(site)
        return [k for k in bank.get("keywords", []) if k.get("status") == "pending"]

    def get_all_keywords(self, site):
        bank = self.load_bank(site)
        return bank.get("keywords", [])

    def delete_keyword(self, site, keyword_id):
        bank = self.load_bank(site)
        orig_len = len(bank.get("keywords", []))
        bank["keywords"] = [k for k in bank.get("keywords", []) if k.get("id") != keyword_id]
        if len(bank["keywords"]) != orig_len:
            self.save_bank(site, bank)
            return True
        return False
