import os
import json
import base64
import re
import requests
from datetime import datetime
import markdown

CONFIG_FILE = "wp_config.json"
PUBLISH_LOG_FILE = "wp_publish_log.json"

class WordPressPublisher:
    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file
        self.config = self._load_and_migrate_config()
        self.current_site_id = self.config.get("active_site_id")

    def _load_and_migrate_config(self):
        if not os.path.exists(self.config_file):
            return {"active_site_id": None, "sites": []}

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return {"active_site_id": None, "sites": []}

        if "wp_url" in data and "sites" not in data:
            old_url = data.get("wp_url", "").strip()
            if old_url:
                site_name = self._extract_domain_name(old_url)
                migrated = {
                    "active_site_id": "site_1",
                    "sites": [
                        {
                            "id": "site_1",
                            "name": site_name,
                            "wp_url": old_url,
                            "username": data.get("username", ""),
                            "app_password": data.get("app_password", ""),
                            "default_status": data.get("default_status", "draft")
                        }
                    ]
                }
                self._save_raw_config(migrated)
                return migrated

        if "sites" not in data:
            data["sites"] = []
        if "active_site_id" not in data and data["sites"]:
            data["active_site_id"] = data["sites"][0]["id"]

        return data

    def _save_raw_config(self, data):
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _extract_domain_name(self, url):
        clean = url.replace("https://", "").replace("http://", "").split("/")[0]
        return clean if clean else "WordPress Site"

    def get_sites(self):
        return self.config.get("sites", [])

    def get_site(self, site_id):
        for s in self.get_sites():
            if s["id"] == site_id:
                return s
        return None

    def get_active_site(self):
        active_id = self.config.get("active_site_id")
        if active_id:
            site = self.get_site(active_id)
            if site:
                return site
        sites = self.get_sites()
        return sites[0] if sites else None

    def set_active_site(self, site_id):
        if self.get_site(site_id):
            self.config["active_site_id"] = site_id
            self._save_raw_config(self.config)
            return True
        return False

    def add_site(self, name, wp_url, username, app_password, default_status="draft"):
        wp_url = wp_url.strip().rstrip("/")
        if wp_url.endswith("/wp-json"):
            wp_url = wp_url[:-8]
        if not wp_url.startswith("http://") and not wp_url.startswith("https://"):
            wp_url = "https://" + wp_url

        sites = self.get_sites()
        new_id = f"site_{len(sites) + 1}_{int(datetime.now().timestamp())}"
        site_name = name.strip() if name.strip() else self._extract_domain_name(wp_url)

        new_site = {
            "id": new_id,
            "type": "wordpress",
            "name": site_name,
            "wp_url": wp_url,
            "username": username.strip(),
            "app_password": app_password.strip(),
            "default_status": default_status
        }

        sites.append(new_site)
        self.config["sites"] = sites
        if not self.config.get("active_site_id"):
            self.config["active_site_id"] = new_id

        self._save_raw_config(self.config)
        return new_site

    def add_astro_site(self, name, content_dir, image_dir=None, site_url=None, auto_git=False):
        """
        Menambahkan profil website statis Astro (Cloudflare Pages / Netlify).
        """
        content_dir = os.path.abspath(content_dir.strip().strip('"').strip("'"))
        if image_dir:
            image_dir = os.path.abspath(image_dir.strip().strip('"').strip("'"))
        else:
            # Default auto detect Astro public/images
            astro_root = os.path.dirname(os.path.dirname(content_dir)) if "src" in content_dir else os.path.dirname(content_dir)
            image_dir = os.path.join(astro_root, "public", "images", "silo")

        sites = self.get_sites()
        new_id = f"astro_{len(sites) + 1}_{int(datetime.now().timestamp())}"
        clean_url = site_url.strip().rstrip("/") if site_url else "https://my-astro-site.pages.dev"
        if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
            clean_url = "https://" + clean_url

        new_site = {
            "id": new_id,
            "type": "astro",
            "name": name.strip() if name.strip() else f"Astro ({os.path.basename(content_dir)})",
            "wp_url": clean_url,
            "content_dir": content_dir,
            "image_dir": image_dir,
            "auto_git": bool(auto_git),
            "default_status": "publish"
        }

        sites.append(new_site)
        self.config["sites"] = sites
        if not self.config.get("active_site_id"):
            self.config["active_site_id"] = new_id

        self._save_raw_config(self.config)
        return new_site

    def update_site(self, site_id, name=None, wp_url=None, username=None, app_password=None, default_status=None, content_dir=None, image_dir=None, auto_git=None):
        site = self.get_site(site_id)
        if not site:
            return False

        if name is not None:
            site["name"] = name.strip()
        if wp_url is not None:
            wp_url = wp_url.strip().rstrip("/")
            if wp_url.endswith("/wp-json"):
                wp_url = wp_url[:-8]
            if not wp_url.startswith("http://") and not wp_url.startswith("https://"):
                wp_url = "https://" + wp_url
            site["wp_url"] = wp_url
        if username is not None:
            site["username"] = username.strip()
        if app_password is not None:
            site["app_password"] = app_password.strip()
        if default_status is not None:
            site["default_status"] = default_status
        if content_dir is not None:
            site["content_dir"] = os.path.abspath(content_dir.strip().strip('"').strip("'"))
        if image_dir is not None:
            site["image_dir"] = os.path.abspath(image_dir.strip().strip('"').strip("'"))
        if auto_git is not None:
            site["auto_git"] = bool(auto_git)

        self._save_raw_config(self.config)
        return True

    def get_site_profile(self, site_id):
        """
        Mengambil data profil bisnis / brand untuk satu website.
        """
        site = self.get_site(site_id)
        if not site:
            return {}
        return site.get("profile", {})

    def update_site_profile(self, site_id, profile_data):
        """
        Menyimpan / memperbarui profil bisnis valid untuk satu website.
        """
        site = self.get_site(site_id)
        if not site:
            return False
        site["profile"] = profile_data
        self._save_raw_config(self.config)
        return True

    @staticmethod
    def format_profile_grounding_prompt(profile_dict):
        """
        Menyusun blok instruksi 'Ground Truth Business Knowledge' untuk Gemini.
        Jika profil kosong / None, menghasilkan instruksi Fallback 'Objective Industry Standard'.
        """
        if not profile_dict or not any(str(v).strip() for v in profile_dict.values() if v):
            return """
[MODE PENULISAN: STANDAR INDUSTRI OBYEKTIF & EDUKATIF (TANPA PROFIL BISNIS SPESIFIK)]
- Anda bertindak sebagai Jurnalis / Pakar Industri Independen yang obyektif, netral, dan terpercaya.
- DILARANG mengarang alamat fiktif, nomor WhatsApp/telepon palsu, atau nomor izin usaha khayalan.
- Untuk data biaya/tarif: Gunakan estimasi kisaran rata-rata pasar di Indonesia yang realistis dengan penjelasan faktor penentu harga.
- Call-to-Action (CTA): Berikan anjuran edukatif umum (misal: pentingnya berkonsultasi dengan penyedia jasa berizin resmi).
"""

        brand = profile_dict.get("brand_name", "").strip()
        niche = profile_dict.get("niche", "").strip()
        tagline = profile_dict.get("tagline", "").strip()
        address = profile_dict.get("address", "").strip()
        area = profile_dict.get("service_area", "").strip()
        phone_wa = profile_dict.get("phone_wa", "").strip()
        email = profile_dict.get("email", "").strip()
        legal = profile_dict.get("legalities", "").strip()
        pricing = profile_dict.get("pricing_services", "").strip()
        strengths = profile_dict.get("usp_strengths", "").strip()
        cta = profile_dict.get("cta_message", "").strip()
        notes = profile_dict.get("custom_notes", "").strip()

        p_text = f"""
[FAKTA BISNIS RESMI & GROUND TRUTH KNOWLEDGE BASE (WAJIB DIGUNAKAN SECARA AKURAT)]
- Nama Brand / Bisnis : {brand if brand else '(Gunakan identitas otoritas industri)'}
- Niche & Bidang Usaha: {niche if niche else '(Sesuai topik artikel)'}
- Tagline / Slogan    : {tagline}
- Alamat Resmi / Base : {address if address else '(Tidak disebutkan)'}
- Area Jangkauan      : {area if area else 'Seluruh Indonesia'}
- Kontak Resmi (WA)   : {phone_wa if phone_wa else '(Konsultasi via web)'}
- Email Resmi         : {email}
- Legalitas & Izin    : {legal if legal else '(Tersertifikasi & Berizin Resmi)'}
- Layanan & Tarif     : {pricing if pricing else '(Hubungi admin untuk penawaran khusus)'}
- Keunggulan Utama/USP: {strengths}
- Call-to-Action (CTA): {cta if cta else f'Hubungi tim kami di {phone_wa} untuk konsultasi dan penawaran terbaik!'}
- Catatan Tambahan    : {notes}

[INSTRUKSI KETAT KEBENARAN DATA (ZERO HALLUCINATION)]:
1. Anda adalah Technical Content Specialist resmi dari '{brand}'.
2. Gunakan data alamat, area jangkauan, nomor WhatsApp ({phone_wa}), tarif, dan legalitas di atas sebagai FAKTA PASTI.
3. DILARANG KERAS mengarang alamat palsu, nomor telepon lain, atau harga di luar daftar resmi di atas.
4. Sisipkan Call-to-Action (CTA) yang meyakinkan di bagian penutup atau sub-bab rekomendasi yang mengarah ke kontak resmi di atas.
"""
        return p_text.strip()

    def delete_site(self, site_id):
        sites = [s for s in self.get_sites() if s["id"] != site_id]
        self.config["sites"] = sites
        if self.config.get("active_site_id") == site_id:
            self.config["active_site_id"] = sites[0]["id"] if sites else None
        self._save_raw_config(self.config)
        return True

    def _get_auth_header(self, site):
        username = site.get("username", "")
        app_password = site.get("app_password", "")
        token = base64.b64encode(f"{username}:{app_password}".encode("utf-8")).decode("utf-8")
        return {"Authorization": f"Basic {token}"}

    def test_connection(self, site=None):
        target_site = site or self.get_active_site()
        if not target_site:
            return False, "Belum ada website yang dikonfigurasi."

        site_type = target_site.get("type", "wordpress")

        # 1. Test Static Web / Astro
        if site_type == "astro":
            content_dir = target_site.get("content_dir", "")
            if not os.path.exists(content_dir):
                return False, f"Folder Content Astro tidak ditemukan: '{content_dir}'"
            
            git_msg = "Manual Sync"
            if target_site.get("auto_git"):
                # Cek git CLI & repository
                import subprocess
                try:
                    res = subprocess.run(["git", "status"], cwd=content_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                    if res.returncode == 0:
                        git_msg = "Git Auto-Push AKTIF (Cloudflare/Netlify Deploy Siap)"
                    else:
                        git_msg = "Folder bukan Git Repo (Sync Lokal Aktif)"
                except Exception:
                    git_msg = "Git CLI tidak terdeteksi (Sync Lokal Aktif)"

            return True, f"Astro Content Folder Valid! ({content_dir}) | Status: {git_msg}"

        # 2. Test WordPress REST API
        wp_url = target_site["wp_url"]
        endpoint = f"{wp_url}/wp-json/wp/v2/users/me"
        headers = self._get_auth_header(target_site)

        try:
            resp = requests.get(endpoint, headers=headers, timeout=15)
            if resp.status_code == 200:
                user_data = resp.json()
                return True, f"Koneksi Sukses! Terhubung sebagai '{user_data.get('name', target_site.get('username', 'User'))}' (ID: {user_data.get('id')})"
            elif resp.status_code == 401:
                return False, "Autentikasi Gagal (401): Username atau App Password tidak valid."
            elif resp.status_code == 403:
                return False, "Akses Ditolak (403): Pengguna tidak memiliki izin untuk REST API."
            elif resp.status_code == 404:
                return False, f"REST API tidak ditemukan di {wp_url} (404). Pastikan permalink WordPress tidak default/plain."
            else:
                return False, f"HTTP Error {resp.status_code}: {resp.text[:200]}"
        except requests.exceptions.RequestException as e:
            return False, f"Gagal menghubungi server WordPress: {str(e)}"

    def parse_markdown_file(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        frontmatter = {}
        body = content

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                raw_fm = parts[1]
                body = parts[2].strip()
                for line in raw_fm.split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        frontmatter[key] = val

        return frontmatter, body

    def scan_articles_global(self, output_dir="output"):
        """
        Memindai seluruh artikel di folder output secara GLOBAL:
        - Artikel yang SUDAH pernah dikirim ke web MANAPUN tidak akan masuk ke pending list.
        - Hanya artikel yang BENAR-BENAR BELUM PERNAH DIKIRIM yang masuk ke pending_articles.
        """
        if not os.path.exists(output_dir):
            return [], []

        publish_log = self._load_publish_log()
        pending_articles = []
        sent_articles = []

        for root, _, files in os.walk(output_dir):
            for file in files:
                if file.endswith(".md") and file != "SILO_BLUEPRINT.md":
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, os.getcwd())
                    norm_path = os.path.normpath(file_path)

                    frontmatter, body = self.parse_markdown_file(file_path)
                    
                    is_sent = False
                    wp_info = None

                    # 1. Cek di file publish log (format flat atau nested)
                    if norm_path in publish_log:
                        is_sent = True
                        wp_info = publish_log[norm_path]
                    else:
                        # Cek jika tersimpan dalam struktur nested URL sebelumnya
                        for key_domain, domain_data in publish_log.items():
                            if isinstance(domain_data, dict) and norm_path in domain_data:
                                is_sent = True
                                wp_info = domain_data[norm_path]
                                break

                    # 2. Cek di frontmatter file markdown
                    if not is_sent:
                        if frontmatter.get("wp_post_id") or frontmatter.get("wp_published_at") or frontmatter.get("wp_post_url"):
                            is_sent = True
                            wp_info = {
                                "post_id": frontmatter.get("wp_post_id"),
                                "published_at": frontmatter.get("wp_published_at"),
                                "post_url": frontmatter.get("wp_post_url"),
                                "site_name": frontmatter.get("wp_target_site", "WordPress"),
                                "status": frontmatter.get("wp_status", "published")
                            }

                    article_info = {
                        "file_path": file_path,
                        "rel_path": rel_path,
                        "file_name": file,
                        "folder_name": os.path.basename(root),
                        "title": frontmatter.get("title", file.replace(".md", "")),
                        "keyword": frontmatter.get("keyword", "-"),
                        "silo_role": frontmatter.get("silo_role", "Cluster"),
                        "silo_theme": frontmatter.get("silo_theme", os.path.basename(root)),
                        "url_slug": frontmatter.get("url_slug", file.replace(".md", "")),
                        "description": frontmatter.get("description", ""),
                        "curation_score": frontmatter.get("curation_score", "-"),
                        "frontmatter": frontmatter,
                        "body_markdown": body,
                        "wp_info": wp_info
                    }

                    if is_sent:
                        sent_articles.append(article_info)
                    else:
                        pending_articles.append(article_info)

        return pending_articles, sent_articles

    def get_or_create_category(self, target_site, category_name):
        """
        Mencari atau otomatis membuat Kategori di WordPress sesuai tema Silo.
        Menjaga agar nama kategori tetap ringkas (1-3 kata) sesuai standar WordPress.
        """
        if not category_name or category_name in ["Umum", "General", "output"]:
            return None

        # Sanitasi nama kategori agar ringkas, rapi, dan sesuai standar WordPress
        clean_cat = str(category_name).strip()
        words = clean_cat.split()
        if len(words) > 4 or len(clean_cat) > 35:
            filtered = [w for w in words if w.lower() not in ["layanan", "profesional", "dan", "di", "yang", "terbaik", "lengkap", "untuk", "dalam", "seputar"]]
            if 1 <= len(filtered) <= 3:
                clean_cat = " ".join(filtered).title()
            else:
                clean_cat = " ".join(words[:3]).title()
        else:
            clean_cat = clean_cat.title()

        wp_url = target_site["wp_url"]
        endpoint = f"{wp_url}/wp-json/wp/v2/categories"
        headers = self._get_auth_header(target_site)

        try:
            # 1. Cari kategori yang sudah ada
            resp = requests.get(f"{endpoint}?search={requests.utils.quote(clean_cat)}", headers=headers, timeout=10)
            if resp.status_code == 200:
                categories = resp.json()
                for cat in categories:
                    if cat.get("name", "").lower() == clean_cat.lower():
                        return cat.get("id")

            # 2. Buat kategori baru jika belum ada
            create_payload = {"name": clean_cat}
            resp_create = requests.post(endpoint, json=create_payload, headers=headers, timeout=10)
            if resp_create.status_code in [200, 201]:
                return resp_create.json().get("id")
        except Exception:
            pass
        return None

    def resolve_internal_links(self, md_text, target_site, publish_log=None):
        """
        Mengubah placeholder link internal [Anchor](slug) menjadi URL live WordPress yang valid.
        """
        if not target_site or not target_site.get("wp_url"):
            return md_text

        if publish_log is None:
            publish_log = self._load_publish_log()

        base_wp_url = target_site["wp_url"].rstrip("/")

        # Mapping slug -> live_url dari log (mendukung struktur flat maupun nested domain)
        slug_to_url = {}
        for file_key, log_item in publish_log.items():
            if isinstance(log_item, dict) and log_item.get("post_url"):
                p_url = log_item.get("post_url")
                fname = os.path.basename(file_key).replace(".md", "")
                fname_clean = re.sub(r'^\d+_', '', fname)
                slug_to_url[fname] = p_url
                slug_to_url[fname_clean] = p_url
                slug_to_url[f"/{fname_clean}"] = p_url
            elif isinstance(log_item, dict):
                for sub_key, sub_item in log_item.items():
                    if isinstance(sub_item, dict) and sub_item.get("post_url"):
                        p_url = sub_item.get("post_url")
                        fname = os.path.basename(sub_key).replace(".md", "")
                        fname_clean = re.sub(r'^\d+_', '', fname)
                        slug_to_url[fname] = p_url
                        slug_to_url[fname_clean] = p_url
                        slug_to_url[f"/{fname_clean}"] = p_url

        def replace_link(match):
            anchor = match.group(1)
            target = match.group(2).strip()

            # Lewati link eksternal, email, atau anchor lokal
            if target.startswith("http://") or target.startswith("https://") or target.startswith("mailto:") or target.startswith("#"):
                return f"[{anchor}]({target})"

            # Bersihkan slug
            clean_slug = target.replace(".md", "").lstrip("/")
            clean_slug = re.sub(r'^\d+_', '', clean_slug)

            # 1. Gunakan live URL dari log jika artikel target SUDAH TERBIT di web
            if clean_slug in slug_to_url and slug_to_url[clean_slug]:
                return f"[{anchor}]({slug_to_url[clean_slug]})"

            # 2. Jika artikel target BELUM TERBIT / BELUM ADA, ubah jadi teks biasa (plain text)
            # agar tidak terjadi Broken Link (404 Not Found)
            return anchor

        # Regex mencari format [Anchor Text](target-slug)
        pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        return re.sub(pattern, replace_link, md_text)

    def extract_faq_json_ld(self, md_text):
        """
        Mendeteksi bagian FAQ di artikel dan menghasilkan Schema JSON-LD FAQPage untuk Google Rich Snippets.
        """
        lines = md_text.split("\n")
        in_faq = False
        faqs = []
        current_q = None
        current_a_lines = []

        for line in lines:
            line_str = line.strip()
            if line_str.startswith("## ") and any(k in line_str.lower() for k in ["faq", "pertanyaan", "tanya jawab"]):
                in_faq = True
                continue

            if in_faq and line_str.startswith("## ") and not any(k in line_str.lower() for k in ["faq", "pertanyaan"]):
                # Keluar dari section FAQ jika bertemu H2 lain
                if current_q and current_a_lines:
                    faqs.append({"q": current_q, "a": " ".join(current_a_lines).strip()})
                    current_q, current_a_lines = None, []
                break

            if in_faq:
                if line_str.startswith("### "):
                    if current_q and current_a_lines:
                        faqs.append({"q": current_q, "a": " ".join(current_a_lines).strip()})
                    # Bersihkan angka atau prefix "1. ", "Q: "
                    raw_q = line_str[4:].strip()
                    cleaned_q = re.sub(r'^\d+[\.\)]\s*', '', raw_q)
                    cleaned_q = re.sub(r'^[Qq]\s*:\s*', '', cleaned_q)
                    current_q = cleaned_q
                    current_a_lines = []
                elif current_q and line_str:
                    current_a_lines.append(line_str)

        if current_q and current_a_lines:
            faqs.append({"q": current_q, "a": " ".join(current_a_lines).strip()})

        if not faqs:
            return ""

        entities = []
        for item in faqs:
            entities.append({
                "@type": "Question",
                "name": item["q"],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": item["a"]
                }
            })

        schema_dict = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": entities
        }

        json_str = json.dumps(schema_dict, ensure_ascii=False, indent=2)
        return f'\n\n<script type="application/ld+json">\n{json_str}\n</script>'

    def markdown_to_wp_html(self, md_text, title="", target_site=None):
        """
        Mengonversi Markdown artikel menjadi HTML WordPress dengan:
        - Pembersihan duplikat H1
        - Resolusi link internal ke live URL WordPress
        - Injeksi otomatis FAQ Schema JSON-LD
        """
        # 1. Resolusi link internal Silo
        if target_site:
            md_text = self.resolve_internal_links(md_text, target_site)

        # 2. Filter H1 duplikat
        lines = md_text.split("\n")
        filtered_lines = []
        h1_found = False
        for line in lines:
            if line.strip().startswith("# ") and not h1_found:
                h1_found = True
                continue
            filtered_lines.append(line)

        cleaned_md = "\n".join(filtered_lines)

        # 3. Render HTML
        html = markdown.markdown(
            cleaned_md,
            extensions=["tables", "fenced_code", "nl2br", "sane_lists"]
        )

        # 4. Injeksi FAQ Schema jika ada
        faq_schema = self.extract_faq_json_ld(cleaned_md)
        if faq_schema:
            html += faq_schema

        return html

    def upload_wp_media(self, target_site, image_path, title=None):
        """
        Mengunggah file gambar ke WordPress Media Library via REST API.
        Mendeteksi tipe konten asli secara akurat via Magic Bytes.
        """
        if not os.path.exists(image_path):
            return None

        wp_url = target_site["wp_url"]
        endpoint = f"{wp_url}/wp-json/wp/v2/media"
        headers = self._get_auth_header(target_site)
        fname = os.path.basename(image_path)
        base_name, _ = os.path.splitext(fname)

        try:
            with open(image_path, "rb") as f:
                img_data = f.read()

            # Deteksi MIME Type asli dari Magic Bytes
            if img_data.startswith(b'\x89PNG'):
                content_type = "image/png"
                upload_fname = f"{base_name}.png"
            elif img_data.startswith(b'RIFF') and b'WEBP' in img_data[:16]:
                content_type = "image/webp"
                upload_fname = f"{base_name}.webp"
            elif img_data.startswith(b'\xff\xd8\xff'):
                content_type = "image/jpeg"
                upload_fname = f"{base_name}.jpg"
            else:
                content_type = "image/webp" if fname.endswith(".webp") else "image/png"
                upload_fname = fname

            headers["Content-Disposition"] = f'attachment; filename="{upload_fname}"'
            headers["Content-Type"] = content_type

            resp = requests.post(endpoint, data=img_data, headers=headers, timeout=40)
            if resp.status_code in [200, 201]:
                return resp.json().get("id")
        except Exception:
            pass
        return None

    def publish_article(self, article_data, target_site, status="draft", scheduled_date=None):
        """
        Mengirim artikel ke website target (WordPress ATAU Static Web Astro):
        - WordPress: REST API + Meta SEO + Category + FAQ Schema + Featured Media + Two-Way Link.
        - Astro: Local Content Collection Sync + Image Copy + Git Commit & Push (Cloudflare/Netlify).
        """
        site_type = target_site.get("type", "wordpress")

        # ==========================================
        # TARGET 1: STATIC WEB (ASTRO / CLOUDFLARE)
        # ==========================================
        if site_type == "astro":
            content_dir = target_site.get("content_dir")
            image_dir = target_site.get("image_dir")
            os.makedirs(content_dir, exist_ok=True)
            if image_dir:
                os.makedirs(image_dir, exist_ok=True)

            slug = article_data["url_slug"]
            target_md_path = os.path.join(content_dir, f"{slug}.md")

            # Cek apakah ada file gambar dari Kie.ai di folder artikel
            folder = os.path.dirname(article_data["file_path"])
            local_img_webp = os.path.join(folder, "images", f"{slug}.webp")
            local_img_png = os.path.join(folder, "images", f"{slug}.png")
            
            hero_image_rel = "/images/silo/placeholder.webp"
            if os.path.exists(local_img_webp) and image_dir:
                import shutil
                dest_img = os.path.join(image_dir, f"{slug}.webp")
                shutil.copy2(local_img_webp, dest_img)
                hero_image_rel = f"/images/silo/{slug}.webp"
            elif os.path.exists(local_img_png) and image_dir:
                import shutil
                dest_img = os.path.join(image_dir, f"{slug}.png")
                shutil.copy2(local_img_png, dest_img)
                hero_image_rel = f"/images/silo/{slug}.png"

            # Format Frontmatter berstandar Universal Astro (Kompatibel dengan semua template Astro)
            now_dt = scheduled_date or datetime.now()
            pub_date_iso = now_dt.strftime("%Y-%m-%d")
            
            clean_silo_theme = str(article_data.get("silo_theme", "Umum")).split("(")[0].strip()
            kw_tag = str(article_data.get("keyword", "")).strip()
            tags_list = [f'"{t}"' for t in [kw_tag, clean_silo_theme] if t]
            tags_str = f"[{', '.join(tags_list)}]"

            site_author = target_site.get("author") or target_site.get("profile", {}).get("business_name") or f"Tim {target_site.get('name', 'Redaksi')}"

            astro_frontmatter = (
                f"---\n"
                f"title: \"{article_data['title'].replace('\"', '')}\"\n"
                f"description: \"{article_data.get('description', '').replace('\"', '')}\"\n"
                f"pubDate: {pub_date_iso}\n"
                f"date: {pub_date_iso}\n"
                f"author: \"{site_author}\"\n"
                f"category: \"{clean_silo_theme}\"\n"
                f"image: \"{hero_image_rel}\"\n"
                f"heroImage: \"{hero_image_rel}\"\n"
                f"coverImage: \"{hero_image_rel}\"\n"
                f"tags: {tags_str}\n"
                f"siloRole: \"{article_data.get('silo_role', 'Cluster')}\"\n"
                f"draft: false\n"
                f"---\n\n"
            )

            # Resolusi link internal untuk Astro
            body_astro = self.resolve_internal_links(article_data["body_markdown"], target_site)
            astro_full_content = astro_frontmatter + body_astro

            with open(target_md_path, "w", encoding="utf-8") as f:
                f.write(astro_full_content)

            # Auto Git Commit & Push jika diaktifkan
            git_status_msg = "Disimpan Lokal"
            if target_site.get("auto_git"):
                import subprocess
                try:
                    astro_root = os.path.dirname(os.path.dirname(content_dir)) if "src" in content_dir else os.path.dirname(content_dir)
                    subprocess.run(["git", "add", "."], cwd=astro_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
                    commit_msg = f"feat(silo): publish {article_data['title']}"
                    subprocess.run(["git", "commit", "-m", commit_msg], cwd=astro_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
                    push_res = subprocess.run(["git", "push"], cwd=astro_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
                    if push_res.returncode == 0:
                        git_status_msg = "Git Push Sukses (Auto Deploy Triggered)"
                    else:
                        git_status_msg = f"Git Push Gagal: {push_res.stderr[:80]}"
                except Exception as ge:
                    git_status_msg = f"Git Error: {str(ge)[:80]}"

            base_site_url = target_site.get("wp_url", "https://my-astro-site.com").rstrip("/")
            route_prefix = target_site.get("route_prefix", "/blog").strip().rstrip("/")
            if route_prefix and not route_prefix.startswith("/"):
                route_prefix = "/" + route_prefix
            post_url = f"{base_site_url}{route_prefix}/{slug}/" if route_prefix else f"{base_site_url}/{slug}/"

            # Update frontmatter di file markdown agar permanen
            self._update_article_frontmatter(article_data["file_path"], f"astro_{slug}", post_url, target_site, "published")
            self._record_publish_log(target_site, article_data["file_path"], f"astro_{slug}", post_url, "published")

            return True, {
                "post_id": f"astro_{slug}",
                "post_url": post_url,
                "status": "published",
                "title": article_data["title"],
                "site_name": target_site["name"],
                "git_status": git_status_msg
            }

        # ==========================================
        # TARGET 2: WORDPRESS REST API
        # ==========================================
        wp_url = target_site["wp_url"]
        endpoint = f"{wp_url}/wp-json/wp/v2/posts"
        headers = self._get_auth_header(target_site)
        headers["Content-Type"] = "application/json"

        html_content = self.markdown_to_wp_html(article_data["body_markdown"], title=article_data["title"], target_site=target_site)

        final_status = status
        post_date_str = None
        if scheduled_date:
            final_status = "future"
            post_date_str = scheduled_date.strftime("%Y-%m-%dT%H:%M:%S")

        payload = {
            "title": article_data["title"],
            "content": html_content,
            "status": final_status,
            "slug": article_data["url_slug"],
            "excerpt": article_data.get("description", "")
        }

        if post_date_str:
            payload["date"] = post_date_str

        # 1. Hubungkan Kategori Silo
        silo_theme = article_data.get("silo_theme")
        cat_id = self.get_or_create_category(target_site, silo_theme)
        if cat_id:
            payload["categories"] = [cat_id]

        # 2. Upload Featured Image jika tersedia dari Kie.ai
        slug = article_data["url_slug"]
        folder = os.path.dirname(article_data["file_path"])
        local_img = os.path.join(folder, "images", f"{slug}.webp")
        if not os.path.exists(local_img):
            local_img = os.path.join(folder, "images", f"{slug}.png")

        if os.path.exists(local_img):
            media_id = self.upload_wp_media(target_site, local_img, title=article_data["title"])
            if media_id:
                payload["featured_media"] = media_id

        # 3. Meta Data untuk Rank Math & Yoast SEO
        focus_kw = article_data.get("keyword", "")
        meta_desc = article_data.get("description", "")
        meta_title = article_data.get("title", "")

        meta_payload = {
            # Rank Math SEO
            "rank_math_title": meta_title,
            "rank_math_description": meta_desc,
            "rank_math_focus_keyword": focus_kw,
            "rank_math_robots": ["index", "follow"],
            # Yoast SEO
            "_yoast_wpseo_title": meta_title,
            "_yoast_wpseo_metadesc": meta_desc,
            "_yoast_wpseo_focuskw": focus_kw
        }
        payload["meta"] = meta_payload

        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
            
            # Jika gagal karena 'meta' field tidak diizinkan di WP tertentu, retry tanpa meta
            if resp.status_code == 400 and "meta" in resp.text:
                payload.pop("meta", None)
                resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)

            if resp.status_code in [200, 201]:
                res_json = resp.json()
                post_id = res_json.get("id")
                post_url = res_json.get("link", "")
                
                # Pastikan featured_media terhubung 100% jika diunggah
                if payload.get("featured_media") and res_json.get("featured_media") != payload.get("featured_media"):
                    try:
                        requests.post(f"{endpoint}/{post_id}", json={"featured_media": payload["featured_media"]}, headers=headers, timeout=15)
                    except Exception:
                        pass

                # Update frontmatter di file markdown agar permanen
                self._update_article_frontmatter(article_data["file_path"], post_id, post_url, target_site, final_status)

                # Catat ke global publish log
                self._record_publish_log(target_site, article_data["file_path"], post_id, post_url, final_status)

                # 4. Two-Way Linking: Jika ini artikel Cluster, update artikel Pilar di WP dengan link balik
                two_way_status = None
                if article_data.get("silo_role", "").lower() == "cluster":
                    pillar_post_id = self._find_pillar_post_id_for_silo(article_data, target_site)
                    if pillar_post_id:
                        ok_2way, msg_2way = self.update_pillar_with_cluster_link(
                            target_site, pillar_post_id, article_data["title"], post_url
                        )
                        two_way_status = msg_2way if ok_2way else None

                return True, {
                    "post_id": post_id,
                    "post_url": post_url,
                    "status": final_status,
                    "title": article_data["title"],
                    "site_name": target_site["name"],
                    "scheduled_date": post_date_str,
                    "category_id": cat_id,
                    "two_way_status": two_way_status
                }
            else:
                err_msg = resp.text
                try:
                    err_json = resp.json()
                    err_msg = err_json.get("message", resp.text)
                except Exception:
                    pass
                return False, f"Gagal mengirim (HTTP {resp.status_code}): {err_msg}"
        except requests.exceptions.RequestException as e:
            return False, f"Koneksi terputus: {str(e)}"

    def _find_pillar_post_id_for_silo(self, cluster_article, target_site):
        """
        Mencari post_id dari artikel Pilar dalam satu Silo yang sama di WordPress target.
        """
        folder = os.path.dirname(cluster_article["file_path"])
        publish_log = self._load_publish_log()

        for file in os.listdir(folder):
            if file.endswith(".md") and file != "SILO_BLUEPRINT.md":
                fpath = os.path.join(folder, file)
                norm_p = os.path.normpath(fpath)
                fm, _ = self.parse_markdown_file(fpath)
                if fm.get("silo_role", "").lower() == "pillar":
                    # Cek di log atau frontmatter
                    if norm_p in publish_log and publish_log[norm_p].get("post_id"):
                        return publish_log[norm_p].get("post_id")
                    elif fm.get("wp_post_id"):
                        return fm.get("wp_post_id")
        return None

    def update_pillar_with_cluster_link(self, target_site, pillar_post_id, cluster_title, cluster_url):
        """
        Two-Way Linking: Menambahkan tautan balik dari artikel Pilar ke artikel Cluster yang baru diterbitkan.
        """
        if not target_site or not pillar_post_id or not cluster_url:
            return False, "Parameter tidak lengkap"

        wp_url = target_site["wp_url"]
        endpoint = f"{wp_url}/wp-json/wp/v2/posts/{pillar_post_id}"
        headers = self._get_auth_header(target_site)

        try:
            # 1. Ambil konten artikel pilar terkini
            resp = requests.get(endpoint, headers=headers, timeout=15)
            if resp.status_code != 200:
                return False, f"Gagal mengambil artikel pilar (HTTP {resp.status_code})"

            pillar_data = resp.json()
            raw_content = pillar_data.get("content", {}).get("rendered", "")

            # Jika cluster_url sudah ada di dalam konten pilar, tidak perlu ditambah lagi
            if cluster_url in raw_content or f'href="{cluster_url}"' in raw_content:
                return True, "Tautan sudah ada di artikel pilar."

            # 2. Sisipkan link cluster baru ke dalam blok referensi pilar
            link_item_html = f'<li><a href="{cluster_url}">{cluster_title}</a></li>'
            
            if 'class="silo-cluster-box"' in raw_content:
                # Update blok list yang sudah ada
                updated_content = re.sub(
                    r'(<ul[^>]*class="silo-cluster-list"[^>]*>)(.*?)(</ul>)',
                    rf'\1\2{link_item_html}\3',
                    raw_content,
                    flags=re.DOTALL
                )
                if updated_content == raw_content:
                    updated_content = raw_content + f'\n<div class="silo-cluster-box" style="margin-top:25px;padding:15px;background:#f4f6f8;border-left:4px solid #0073aa;border-radius:4px;"><strong>📚 Topik Terkait:</strong><ul class="silo-cluster-list">{link_item_html}</ul></div>'
            else:
                # Buat blok baru di akhir artikel pilar
                new_box = f'\n<div class="silo-cluster-box" style="margin-top:25px;padding:15px;background:#f4f6f8;border-left:4px solid #0073aa;border-radius:4px;"><strong>📚 Topik Terkait dalam Silo:</strong><ul class="silo-cluster-list">{link_item_html}</ul></div>'
                updated_content = raw_content + new_box

            # 3. Update postingan pilar via REST API
            update_payload = {"content": updated_content}
            put_headers = dict(headers)
            put_headers["Content-Type"] = "application/json"

            resp_put = requests.post(endpoint, json=update_payload, headers=put_headers, timeout=20)
            if resp_put.status_code in [200, 201]:
                return True, f"Artikel Pilar #{pillar_post_id} terhubung link balik."
            else:
                return False, f"Gagal update pilar (HTTP {resp_put.status_code})"
        except Exception as e:
            return False, f"Gagal update pilar: {str(e)}"

    def export_silo_to_wxr(self, silo_folder_path, output_xml_path=None):
        """
        Mengekspor seluruh artikel dalam satu folder Silo ke file WordPress eXtended RSS (WXR XML).
        File XML ini 100% kompatibel dengan fitur import WordPress Admin (Tools -> Import -> WordPress).
        """
        if not os.path.exists(silo_folder_path):
            raise FileNotFoundError(f"Folder silo '{silo_folder_path}' tidak ditemukan.")

        # Ambil metadata silo jika ada
        meta_path = os.path.join(silo_folder_path, "silo_metadata.json")
        silo_meta = {}
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    silo_meta = json.load(f)
            except Exception:
                pass

        silo_theme = silo_meta.get("silo_theme", os.path.basename(silo_folder_path))
        cat_slug = re.sub(r'[\s_]+', '-', silo_theme.lower())
        cat_slug = re.sub(r'[^\w-]', '', cat_slug).strip('-')
        if not cat_slug:
            cat_slug = "silo"

        # Kumpulkan semua file artikel
        md_files = []
        for file in sorted(os.listdir(silo_folder_path)):
            if file.endswith(".md") and file != "SILO_BLUEPRINT.md":
                md_files.append(os.path.join(silo_folder_path, file))

        if not md_files:
            raise ValueError(f"Tidak ada file artikel .md di '{silo_folder_path}'.")

        now_utc = datetime.utcnow()
        pub_date_str = now_utc.strftime("%a, %d %b %Y %H:%M:%S +0000")

        items_xml = []
        for idx, fpath in enumerate(md_files, 1):
            frontmatter, body = self.parse_markdown_file(fpath)
            title = frontmatter.get("title", os.path.basename(fpath).replace(".md", ""))
            slug = frontmatter.get("url_slug", re.sub(r'^\d+_', '', os.path.basename(fpath).replace(".md", "")))
            description = frontmatter.get("description", "")
            keyword = frontmatter.get("keyword", "")

            # Render HTML dengan FAQ Schema & pembersihan H1
            html_content = self.markdown_to_wp_html(body, title=title)

            art_date = datetime.now()
            date_str = art_date.strftime("%Y-%m-%d %H:%M:%S")
            date_gmt_str = art_date.strftime("%Y-%m-%d %H:%M:%S")

            item_xml = f"""
	<item>
		<title><![CDATA[{title}]]></title>
		<link>http://localhost/{slug}/</link>
		<pubDate>{pub_date_str}</pubDate>
		<dc:creator><![CDATA[admin]]></dc:creator>
		<guid isPermaLink="false">http://localhost/?p={idx}</guid>
		<description></description>
		<content:encoded><![CDATA[{html_content}]]></content:encoded>
		<excerpt:encoded><![CDATA[{description}]]></excerpt:encoded>
		<wp:post_id>{idx}</wp:post_id>
		<wp:post_date>{date_str}</wp:post_date>
		<wp:post_date_gmt>{date_gmt_str}</wp:post_date_gmt>
		<wp:comment_status>open</wp:comment_status>
		<wp:ping_status>open</wp:ping_status>
		<wp:post_name><![CDATA[{slug}]]></wp:post_name>
		<wp:status><![CDATA[publish]]></wp:status>
		<wp:post_parent>0</wp:post_parent>
		<wp:menu_order>0</wp:menu_order>
		<wp:post_type><![CDATA[post]]></wp:post_type>
		<wp:post_password></wp:post_password>
		<wp:is_sticky>0</wp:is_sticky>
		<category domain="category" nicename="{cat_slug}"><![CDATA[{silo_theme}]]></category>
		<wp:postmeta>
			<wp:meta_key><![CDATA[rank_math_title]]></wp:meta_key>
			<wp:meta_value><![CDATA[{title}]]></wp:meta_value>
		</wp:postmeta>
		<wp:postmeta>
			<wp:meta_key><![CDATA[rank_math_description]]></wp:meta_key>
			<wp:meta_value><![CDATA[{description}]]></wp:meta_value>
		</wp:postmeta>
		<wp:postmeta>
			<wp:meta_key><![CDATA[rank_math_focus_keyword]]></wp:meta_key>
			<wp:meta_value><![CDATA[{keyword}]]></wp:meta_value>
		</wp:postmeta>
		<wp:postmeta>
			<wp:meta_key><![CDATA[_yoast_wpseo_title]]></wp:meta_key>
			<wp:meta_value><![CDATA[{title}]]></wp:meta_value>
		</wp:postmeta>
		<wp:postmeta>
			<wp:meta_key><![CDATA[_yoast_wpseo_metadesc]]></wp:meta_key>
			<wp:meta_value><![CDATA[{description}]]></wp:meta_value>
		</wp:postmeta>
		<wp:postmeta>
			<wp:meta_key><![CDATA[_yoast_wpseo_focuskw]]></wp:meta_key>
			<wp:meta_value><![CDATA[{keyword}]]></wp:meta_value>
		</wp:postmeta>
	</item>"""
            items_xml.append(item_xml)

        wxr_content = f"""<?xml version="1.0" encoding="UTF-8" ?>
<!-- generator="WordPress/6.4" created="{datetime.now().strftime('%Y-%m-%d %H:%M')}" -->
<rss version="2.0"
	xmlns:excerpt="http://wordpress.org/export/1.2/excerpt/"
	xmlns:content="http://purl.org/rss/1.0/modules/content/"
	xmlns:wfw="http://wellformedweb.org/CommentAPI/"
	xmlns:dc="http://purl.org/dc/elements/1.1/"
	xmlns:wp="http://wordpress.org/export/1.2/"
>
<channel>
	<title><![CDATA[{silo_theme}]]></title>
	<link>http://localhost</link>
	<description><![CDATA[Export Arsitektur SEO Silo]]></description>
	<pubDate>{pub_date_str}</pubDate>
	<language>id</language>
	<wp:wxr_version>1.2</wp:wxr_version>
	<wp:base_site_url>http://localhost</wp:base_site_url>
	<wp:base_blog_url>http://localhost</wp:base_blog_url>
	<wp:category>
		<wp:term_id>1</wp:term_id>
		<wp:category_nicename>{cat_slug}</wp:category_nicename>
		<wp:category_parent></wp:category_parent>
		<wp:cat_name><![CDATA[{silo_theme}]]></wp:cat_name>
	</wp:category>
{''.join(items_xml)}
</channel>
</rss>"""

        if not output_xml_path:
            output_xml_path = os.path.join(silo_folder_path, f"wordpress_import_{cat_slug}.xml")

        with open(output_xml_path, "w", encoding="utf-8") as f:
            f.write(wxr_content)

        return output_xml_path, len(md_files), silo_theme

    def _update_article_frontmatter(self, file_path, post_id, post_url, target_site, status):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            published_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    raw_fm = parts[1].rstrip()
                    # Append global sent metadata
                    new_fm = (
                        f"{raw_fm}\n"
                        f"wp_post_id: {post_id}\n"
                        f"wp_published_at: \"{published_at}\"\n"
                        f"wp_post_url: \"{post_url}\"\n"
                        f"wp_target_site: \"{target_site['name']}\"\n"
                        f"wp_target_url: \"{target_site['wp_url']}\"\n"
                        f"wp_status: \"{status}\"\n"
                    )
                    new_content = f"---{new_fm}---{parts[2]}"
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
        except Exception:
            pass

    def _load_publish_log(self):
        if os.path.exists(PUBLISH_LOG_FILE):
            try:
                with open(PUBLISH_LOG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _record_publish_log(self, target_site, file_path, post_id, post_url, status):
        log = self._load_publish_log()
        norm_path = os.path.normpath(file_path)
        
        # Save flat entry for fast global lookup
        log[norm_path] = {
            "post_id": post_id,
            "post_url": post_url,
            "status": status,
            "site_name": target_site["name"],
            "site_url": target_site["wp_url"],
            "published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            with open(PUBLISH_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(log, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ==========================================
    # LIVE WORDPRESS MANAGEMENT METHODS
    # ==========================================
    def get_live_posts(self, target_site=None, status="any", per_page=15, page=1, search=""):
        """
        Mengambil daftar postingan aktual secara langsung dari WordPress REST API.
        status: 'any', 'publish', 'draft', 'future', 'trash', 'pending', 'private'
        """
        site = target_site or self.get_active_site()
        if not site:
            return False, "Website target belum dikonfigurasi.", 0, 0
        if site.get("type") == "astro":
            return False, "Website aktif bertipe Static Astro (tidak menggunakan WordPress REST API).", 0, 0

        wp_url = site["wp_url"]
        endpoint = f"{wp_url}/wp-json/wp/v2/posts"
        headers = self._get_auth_header(site)

        params = {
            "status": status,
            "per_page": per_page,
            "page": page,
            "_embed": "author,wp:term"
        }
        if search.strip():
            params["search"] = search.strip()

        try:
            resp = requests.get(endpoint, headers=headers, params=params, timeout=15)
            if resp.status_code == 200:
                posts = resp.json()
                total_posts = int(resp.headers.get("X-WP-Total", len(posts)))
                total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
                return True, posts, total_posts, total_pages
            elif resp.status_code == 401:
                return False, "Autentikasi gagal (401). Periksa Application Password.", 0, 0
            elif resp.status_code == 403:
                return False, "Akses ditolak (403). Akun WordPress tidak memiliki izin membaca post.", 0, 0
            elif resp.status_code == 400 and page > 1:
                return True, [], 0, 0
            else:
                return False, f"HTTP Error {resp.status_code}: {resp.text[:200]}", 0, 0
        except requests.exceptions.RequestException as e:
            return False, f"Gagal menghubungi server WordPress: {str(e)}", 0, 0

    def get_single_live_post(self, post_id, target_site=None):
        """
        Mengambil detail lengkap 1 artikel live dari WordPress.
        """
        site = target_site or self.get_active_site()
        if not site or site.get("type") == "astro":
            return False, "Website target bukan WordPress."

        wp_url = site["wp_url"]
        endpoint = f"{wp_url}/wp-json/wp/v2/posts/{post_id}"
        headers = self._get_auth_header(site)

        try:
            resp = requests.get(f"{endpoint}?_embed=1", headers=headers, timeout=15)
            if resp.status_code == 200:
                return True, resp.json()
            else:
                return False, f"HTTP Error {resp.status_code}: {resp.text[:200]}"
        except requests.exceptions.RequestException as e:
            return False, f"Gagal menghubungi server WordPress: {str(e)}"

    def update_live_post(self, post_id, update_fields, target_site=None):
        """
        Mengupdate field postingan live di WordPress via REST API:
        update_fields: dict (title, content, excerpt, status, featured_media, meta, categories, etc.)
        """
        site = target_site or self.get_active_site()
        if not site or site.get("type") == "astro":
            return False, "Website target bukan WordPress."

        wp_url = site["wp_url"]
        endpoint = f"{wp_url}/wp-json/wp/v2/posts/{post_id}"
        headers = self._get_auth_header(site)

        try:
            resp = requests.post(endpoint, json=update_fields, headers=headers, timeout=25)
            if resp.status_code in [200, 201]:
                return True, resp.json()
            else:
                return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
        except requests.exceptions.RequestException as e:
            return False, f"Koneksi error: {str(e)}"

    def update_post_status(self, post_id, new_status, target_site=None):
        """
        Mengubah status postingan live di WordPress (publish, draft, pending, private).
        """
        site = target_site or self.get_active_site()
        if not site or site.get("type") == "astro":
            return False, "Website target bukan WordPress."

        wp_url = site["wp_url"]
        endpoint = f"{wp_url}/wp-json/wp/v2/posts/{post_id}"
        headers = self._get_auth_header(site)

        payload = {"status": new_status}
        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=15)
            if resp.status_code in [200, 201]:
                return True, f"Status artikel #{post_id} berhasil diubah menjadi '{new_status}'."
            else:
                return False, f"Gagal mengubah status: HTTP {resp.status_code} - {resp.text[:200]}"
        except requests.exceptions.RequestException as e:
            return False, f"Koneksi error: {str(e)}"

    def delete_live_post(self, post_id, force=False, target_site=None):
        """
        Menghapus postingan live dari WordPress:
        force=False -> Pindahkan ke Trash (Sampah)
        force=True  -> Hapus Permanen dari Database
        """
        site = target_site or self.get_active_site()
        if not site or site.get("type") == "astro":
            return False, "Website target bukan WordPress."

        wp_url = site["wp_url"]
        endpoint = f"{wp_url}/wp-json/wp/v2/posts/{post_id}"
        headers = self._get_auth_header(site)

        params = {"force": "true" if force else "false"}
        try:
            resp = requests.delete(endpoint, headers=headers, params=params, timeout=15)
            if resp.status_code in [200, 201]:
                action_text = "dihapus permanen" if force else "dipindahkan ke Trash"
                return True, f"Artikel #{post_id} berhasil {action_text}."
            else:
                return False, f"Gagal menghapus: HTTP {resp.status_code} - {resp.text[:200]}"
        except requests.exceptions.RequestException as e:
            return False, f"Koneksi error: {str(e)}"

    def get_live_categories(self, target_site=None, per_page=100):
        """
        Mengambil semua kategori aktual dari WordPress.
        """
        site = target_site or self.get_active_site()
        if not site or site.get("type") == "astro":
            return False, "Website target bukan WordPress."

        wp_url = site["wp_url"]
        endpoint = f"{wp_url}/wp-json/wp/v2/categories"
        headers = self._get_auth_header(site)

        try:
            resp = requests.get(f"{endpoint}?per_page={per_page}", headers=headers, timeout=15)
            if resp.status_code == 200:
                return True, resp.json()
            else:
                return False, f"HTTP Error {resp.status_code}: {resp.text[:200]}"
        except requests.exceptions.RequestException as e:
            return False, f"Gagal menghubungi server WordPress: {str(e)}"

    def create_live_category(self, name, slug=None, description=None, target_site=None):
        """
        Membuat kategori baru langsung di WordPress via REST API.
        """
        site = target_site or self.get_active_site()
        if not site or site.get("type") == "astro":
            return False, "Website target bukan WordPress."

        wp_url = site["wp_url"]
        endpoint = f"{wp_url}/wp-json/wp/v2/categories"
        headers = self._get_auth_header(site)

        payload = {"name": name.strip()}
        if slug:
            payload["slug"] = slug.strip()
        if description:
            payload["description"] = description.strip()

        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=15)
            if resp.status_code in [200, 201]:
                return True, resp.json()
            else:
                return False, f"HTTP Error {resp.status_code}: {resp.text[:200]}"
        except requests.exceptions.RequestException as e:
            return False, f"Koneksi error: {str(e)}"

    def delete_live_category(self, category_id, force=True, target_site=None):
        """
        Menghapus kategori langsung dari WordPress via REST API.
        """
        site = target_site or self.get_active_site()
        if not site or site.get("type") == "astro":
            return False, "Website target bukan WordPress."

        wp_url = site["wp_url"]
        endpoint = f"{wp_url}/wp-json/wp/v2/categories/{category_id}"
        headers = self._get_auth_header(site)

        params = {"force": "true" if force else "false"}
        try:
            resp = requests.delete(endpoint, headers=headers, params=params, timeout=15)
            if resp.status_code in [200, 201]:
                return True, f"Kategori #{category_id} berhasil dihapus."
            else:
                return False, f"Gagal menghapus: HTTP {resp.status_code} - {resp.text[:200]}"
        except requests.exceptions.RequestException as e:
            return False, f"Koneksi error: {str(e)}"

