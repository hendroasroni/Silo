import os
import json
import re
import html
import time
import textwrap
import requests

def clean_text_for_rendering(text):
    """
    Membersihkan HTML entities, emoji, dan karakter unicode khusus
    sehingga teks yang dirender di thumbnail bersih, rapi, dan 100% kompatibel font (tanpa kotak/tofu).
    """
    if not text:
        return ""
    # 1. Decode numeric & named HTML entities
    cleaned = html.unescape(str(text))
    # 2. Tangani entity tanpa titik koma & variasinya
    cleaned = re.sub(r'&#0*38;?', '&', cleaned)
    cleaned = re.sub(r'&#0*8211;?', '-', cleaned)
    cleaned = re.sub(r'&#0*8212;?', '-', cleaned)
    cleaned = re.sub(r'&#0*8216;?', "'", cleaned)
    cleaned = re.sub(r'&#0*8217;?', "'", cleaned)
    cleaned = re.sub(r'&#0*8220;?', '"', cleaned)
    cleaned = re.sub(r'&#0*8221;?', '"', cleaned)
    cleaned = re.sub(r'&amp;?', '&', cleaned)
    # 3. Normalisasi unicode dash & smart quotes ke ASCII aman font
    cleaned = cleaned.replace('–', '-').replace('—', '-').replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    # 4. Hapus tag HTML jika ada
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    # 5. Hapus Emojis & Variation Selectors yang menyebabkan kotak/tofu pada font TrueType Pillow
    emoji_pattern = re.compile(
        "["
        "\U00010000-\U0010ffff"
        "\u2600-\u27ff"
        "\u2300-\u23ff"
        "\u2b50-\u2b55"
        "\ufe00-\ufe0f"
        "\u200d"
        "]+",
        flags=re.UNICODE
    )
    cleaned = emoji_pattern.sub('', cleaned)
    # 6. Rapikan spasi berlebih
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

KIE_KEY_FILE = "kie_apikey.txt"
KIE_CONFIG_FILE = "kie_config.json"

DEFAULT_KIE_MODELS = [
    ("z-image", "Z-Image Fast & Photorealistic / Illustration (Rekomendasi Utama)"),
    ("flux1-kontext", "Flux 1 Kontext (High Quality)"),
    ("flux-2/pro-image-to-image", "Flux 2 Pro"),
]

DEFAULT_IMAGE_STYLES = [
    ("illustration", "Ilustrasi Modern Vector & Flat Art (Bersih, Rapi & Elegan)", {
        "art_director": "expert AI Art Director & Digital Vector Illustrator",
        "description": "modern digital vector illustration, clean lines, vibrant harmonious color palette, minimalist editorial aesthetic, flat and semi-flat vector art, professional modern artwork",
        "suffix": "modern clean vector art illustration, minimalist editorial art style, vibrant harmonious colors, sleek aesthetic, high resolution, no text, no letters, no words, no watermark",
        "fallback": "Modern clean vector art illustration representing {keyword} for {article_title}, vibrant flat colors, minimalist digital editorial illustration, sleek geometric composition, high resolution, no text, no watermark"
    }),
    ("isometric_3d", "Ilustrasi 3D Isometric & Studio Render (Tech & Clean 3D)", {
        "art_director": "expert 3D Digital Artist & Creative Visualizer",
        "description": "modern 3D isometric render, clean claymorphism, soft studio lighting, smooth materials, ambient occlusion, Behance trending 3D style",
        "suffix": "modern 3D isometric render, claymorphism studio lighting, soft ambient occlusion, cute clean minimalist 3D style, high resolution, no text, no letters, no words, no watermark",
        "fallback": "Modern 3D isometric render illustrating {keyword} for {article_title}, clean studio clay render, soft pastel lighting, minimalist 3D aesthetic, 8k render, no text, no watermark"
    }),
    ("line_art", "Minimalist Line Art & Duotone Editorial (Simpel & Elegan)", {
        "art_director": "expert Editorial Magazine Graphic Designer",
        "description": "minimalist line art illustration, clean aesthetic outline, elegant duotone pastel palette, sophisticated editorial magazine style",
        "suffix": "minimalist line art illustration, elegant duotone vector aesthetics, clean geometric shapes, sophisticated editorial magazine art, no text, no letters, no words, no watermark",
        "fallback": "Minimalist editorial line art illustration for {keyword} - {article_title}, clean duotone color palette, modern outline art, sophisticated aesthetics, no text, no watermark"
    }),
    ("cyberpunk_tech", "Futuristic Tech / Cyber Glow (Modern High-Tech)", {
        "art_director": "expert Futuristic Concept Artist",
        "description": "modern futuristic tech illustration, glowing neon accents, sleek dark background, holographic UI elements, cutting-edge digital aesthetic",
        "suffix": "futuristic digital technology illustration, glowing neon accents, sleek high-tech aesthetic, modern cyber concept art, 8k resolution, no text, no letters, no words, no watermark",
        "fallback": "Futuristic digital technology illustration representing {keyword} for {article_title}, glowing neon accents, sleek dark UI elements, cutting-edge digital concept art, no text, no watermark"
    }),
    ("photo", "Photorealistic Photography (Foto Realistis)", {
        "art_director": "expert AI Art Director & Commercial Photographer",
        "description": "pure visual photography, photorealistic, 8k, modern clean natural lighting, shallow depth of field, commercial photography style",
        "suffix": "professional commercial photography, 8k resolution, photorealistic, natural lighting, shallow depth of field, no text, no letters, no words, no watermark",
        "fallback": "Professional modern photography illustrating {keyword} for {article_title}, clean minimalist aesthetic, natural lighting, shallow depth of field, 8k resolution, photorealistic, commercial style, no text, no watermark"
    })
]
IMAGE_STYLE_MAP = {code: data for code, desc, data in DEFAULT_IMAGE_STYLES}
IMAGE_STYLE_DESCS = {code: desc for code, desc, data in DEFAULT_IMAGE_STYLES}

# 10 Curated Color Palettes for Mesh Gradient: [Base_Dark_BG, Blob_1, Blob_2, Blob_3, Accent_Color]
MESH_PALETTES = [
    [(15, 23, 42), (99, 102, 241), (236, 72, 153), (14, 165, 233), (99, 102, 241)],   # 0: Cyber Violet & Sunset
    [(10, 25, 30), (16, 185, 129), (59, 130, 246), (139, 92, 246), (16, 185, 129)],   # 1: Aurora & Mint Teal
    [(24, 24, 27), (249, 115, 22), (239, 68, 68), (217, 70, 239), (249, 115, 22)],    # 2: Neon Blaze & Amber
    [(10, 20, 45), (14, 165, 233), (59, 130, 246), (99, 102, 241), (14, 165, 233)],   # 3: Nordic Deep Ocean
    [(26, 16, 43), (217, 70, 239), (168, 85, 247), (244, 63, 94), (217, 70, 239)],   # 4: Electric Dusk & Magenta
    [(13, 28, 20), (34, 197, 94), (16, 185, 129), (234, 179, 8), (34, 197, 94)],      # 5: Emerald Forest & Gold
    [(35, 15, 22), (244, 63, 94), (251, 146, 60), (236, 72, 153), (244, 63, 94)],    # 6: Rose Gold & Ruby
    [(12, 12, 18), (139, 92, 246), (99, 102, 241), (168, 85, 247), (139, 92, 246)],   # 7: Obsidian & Ultra Violet
    [(18, 14, 38), (236, 72, 153), (249, 115, 22), (6, 182, 212), (249, 115, 22)],    # 8: Retro Synthwave Sunset
    [(12, 30, 36), (6, 182, 212), (245, 158, 11), (244, 63, 94), (6, 182, 212)],      # 9: Tropical Lagoon Flare
]

LAYOUT_NAMES = [
    "center_card",     # 0: Glassmorphic Center Card
    "left_editorial",  # 1: Split Left Editorial Card
    "pill_centered",   # 2: Symmetrical Minimalist Studio
    "accent_bar",      # 3: Neon Sidebar Accent Bar
    "bottom_dock",     # 4: Lower-Third Glass Studio Dock
]

def build_dynamic_footer_text(title, keyword, category, silo_role=None):
    """
    Menghasilkan teks footer dinamis & kontekstual untuk thumbnail (Opsi 2).
    Bervariasi secara deterministik berdasarkan judul artikel agar tidak ada yang monoton/statis.
    Menggunakan tipografi bersih (tanpa emoji) agar 100% bebas kotak/tofu glyph.
    """
    clean_t = clean_text_for_rendering(title)
    clean_cat = clean_text_for_rendering(category)
    
    # Hitung perkiraan durasi baca dinamis (4 - 8 menit) berdasarkan bobot karakter
    read_mins = 4 + (abs(hash(clean_t)) % 5)
    
    # Format variasi konteks dinamis
    variant = abs(hash(clean_t + clean_cat + "footer_variant")) % 5
    
    is_pillar = "pillar" in str(silo_role).lower() or "pillar" in clean_cat.lower()
    role_label = "Panduan Pilar Utama" if is_pillar else "Seri Silo Terstruktur"

    if variant == 0:
        return f"{read_mins} Menit Baca • {role_label}"
    elif variant == 1:
        return f"Panduan Lengkap • {clean_cat}"
    elif variant == 2:
        return f"Wawasan & Analisis • {clean_cat}"
    elif variant == 3:
        return f"{read_mins} Menit Baca • {clean_cat}"
    else:
        return f"Edukasi Praktis • {role_label}"

class KieImageClient:
    def __init__(self, key_file=KIE_KEY_FILE, config_file=KIE_CONFIG_FILE):
        self.key_file = key_file
        self.config_file = config_file
        self.api_keys = self.reload_keys()
        self.current_key_index = 0
        self.config = self._load_config()

    def _load_config(self):
        default_cfg = {
            "model": "z-image",
            "api_base_url": "https://api.kie.ai",
            "aspect_ratio": "16:9",
            "quality": "standard",
            "image_mode": "hybrid",  # "hybrid" (Kie.ai + Mesh Fallback), "mesh_gradient", "kie_only"
            "image_style": "illustration"  # "illustration", "isometric_3d", "line_art", "cyberpunk_tech", "photo"
        }
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    default_cfg.update(data)
            except Exception:
                pass
        return default_cfg

    def _save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_preferred_model(self):
        return self.config.get("model", "z-image")

    def set_preferred_model(self, model_name):
        self.config["model"] = model_name.strip()
        self._save_config()

    def get_image_mode(self):
        return self.config.get("image_mode", "hybrid")

    def set_image_mode(self, mode):
        if mode in ["hybrid", "mesh_gradient", "kie_only"]:
            self.config["image_mode"] = mode
            self._save_config()
            return True
        return False

    def get_image_style(self):
        return self.config.get("image_style", "illustration")

    def set_image_style(self, style_name):
        self.config["image_style"] = style_name.strip()
        self._save_config()
        return True

    def reload_keys(self):
        keys = []
        if os.path.exists(self.key_file):
            try:
                with open(self.key_file, "r", encoding="utf-8") as f:
                    for line in f:
                        k = line.strip()
                        if k and not k.startswith("#") and k not in keys:
                            keys.append(k)
            except Exception:
                pass
        env_k = os.environ.get("KIE_API_KEY", "").strip()
        if env_k and env_k not in keys:
            keys.append(env_k)

        self.api_keys = keys
        return keys

    def add_key(self, new_key):
        new_key = new_key.strip()
        if not new_key:
            return False
        keys = self.reload_keys()
        if new_key in keys:
            return False
        with open(self.key_file, "a", encoding="utf-8") as f:
            f.write(f"\n{new_key}")
        self.reload_keys()
        return True

    def remove_key(self, index):
        keys = self.reload_keys()
        if 0 <= index < len(keys):
            removed = keys.pop(index)
            self._save_keys(keys)
            self.reload_keys()
            return removed
        return None

    def remove_keys_by_values(self, keys_to_remove):
        """
        Menghapus sekumpulan key berdasarkan string key-nya secara bersamaan.
        """
        keys_set = set(k.strip() for k in keys_to_remove if k and k.strip())
        if not keys_set:
            return 0
        current_keys = self.reload_keys()
        remaining_keys = [k for k in current_keys if k not in keys_set]
        removed_count = len(current_keys) - len(remaining_keys)
        self._save_keys(remaining_keys)
        self.reload_keys()
        return removed_count

    def _save_keys(self, keys_list):
        # Mempertahankan baris komentar di file key jika ada
        header_lines = []
        if os.path.exists(self.key_file):
            try:
                with open(self.key_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("#"):
                            header_lines.append(line.rstrip())
            except Exception:
                pass
        
        with open(self.key_file, "w", encoding="utf-8") as f:
            if header_lines:
                f.write("\n".join(header_lines) + "\n\n")
            f.write("\n".join(keys_list) + "\n")

    def get_active_key(self):
        if not self.api_keys:
            return None
        return self.api_keys[self.current_key_index % len(self.api_keys)]

    def rotate_key(self):
        if not self.api_keys:
            return None
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return self.get_active_key()

    def check_key_validity(self, api_key):
        endpoint = "https://api.kie.ai/api/v1/chat/credit"
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json"
        }
        try:
            resp = requests.get(endpoint, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 200:
                    credit = data.get("data")
                    try:
                        credit_num = float(credit) if credit is not None else 0.0
                    except (ValueError, TypeError):
                        credit_num = 0.0
                    
                    if credit_num > 0:
                        return True, f"Kredit Tersedia: {credit}", credit_num
                    elif credit_num == 0:
                        return False, f"Kredit Habis (Saldo: {credit})", credit_num
                    else:
                        return False, f"Kredit Minus / Limit (Saldo: {credit})", credit_num
                else:
                    return False, f"Respon Error ({data.get('code')}): {data.get('msg', 'Unknown')}", None
            elif resp.status_code in [401, 403]:
                return False, f"Auth Gagal / Key Tidak Valid (HTTP {resp.status_code})", None
            else:
                return False, f"HTTP Error {resp.status_code}: {resp.text[:100]}", None
        except requests.exceptions.RequestException as e:
            return False, f"Koneksi Gagal: {str(e)[:100]}", None

    def test_all_keys(self):
        results = []
        keys = self.reload_keys()
        if not keys:
            return results

        for i, k in enumerate(keys, 1):
            masked = f"{k[:8]}...{k[-4:]}" if len(k) >= 12 else k
            is_valid, msg, credit_num = self.check_key_validity(k)
            results.append({
                "index": i,
                "key": k,
                "masked": masked,
                "is_valid": is_valid,
                "message": msg,
                "credit": credit_num
            })
        return results

    def build_image_prompt(self, article_title, keyword, silo_theme, gemini_client=None, style=None):
        article_title = clean_text_for_rendering(article_title)
        keyword = clean_text_for_rendering(keyword)
        silo_theme = clean_text_for_rendering(silo_theme)

        style_key = style or self.get_image_style()
        style_info = IMAGE_STYLE_MAP.get(style_key, IMAGE_STYLE_MAP["illustration"])

        if gemini_client:
            sys_inst = (
                f"You are an {style_info['art_director']}. "
                f"Your job is to generate a single high-quality English image prompt for an article header visual. "
                f"CRITICAL: The image MUST BE a {style_info['description']}. "
                f"STRICT NEGATIVE CONSTRAINT: NO TEXT, NO LETTERS, NO TYPOGRAPHY, NO WORDS, NO SIGNS, NO WATERMARKS."
            )
            user_prompt = f"""
Create a compelling visual image prompt for this article:
- Topic: {article_title}
- Focus Keyword: {keyword}
- Silo Theme: {silo_theme}
- Visual Art Style: {style_key} ({style_info['description']})

Output ONLY the prompt text in English (1-2 descriptive sentences focusing on visual subjects, metaphor, composition, harmonious colors, and clean aesthetic).
Do NOT include any explanations, quotes, or text elements.
"""
            try:
                prompt_res = gemini_client.generate_text(user_prompt, system_instruction=sys_inst, temperature=0.7)
                clean_p = prompt_res.strip().strip('"').strip("'")
                if clean_p and len(clean_p) > 10:
                    return f"{clean_p}, {style_info['suffix']}"
            except Exception:
                pass

        return style_info["fallback"].format(keyword=keyword, article_title=article_title)

    def _extract_image_url(self, task_data):
        if not task_data:
            return None

        # 1. Cek di resultJson (string JSON)
        result_json_raw = task_data.get("resultJson")
        if result_json_raw:
            if isinstance(result_json_raw, str):
                try:
                    parsed = json.loads(result_json_raw)
                    if isinstance(parsed, dict):
                        for k in ["resultUrls", "resultUrl", "image_urls", "image_url", "urls", "url", "images", "results"]:
                            val = parsed.get(k)
                            if isinstance(val, list) and val:
                                return val[0]
                            elif isinstance(val, str) and (val.startswith("http://") or val.startswith("https://")):
                                return val
                    elif isinstance(parsed, list) and parsed:
                        return parsed[0]
                except Exception:
                    if result_json_raw.startswith("http://") or result_json_raw.startswith("https://"):
                        return result_json_raw
            elif isinstance(result_json_raw, dict):
                for k in ["resultUrls", "resultUrl", "image_urls", "image_url", "urls", "url", "images", "results"]:
                    val = result_json_raw.get(k)
                    if isinstance(val, list) and val:
                        return val[0]
                    elif isinstance(val, str) and (val.startswith("http://") or val.startswith("https://")):
                        return val

        # 2. Cek di response objek jika ada
        resp_obj = task_data.get("response")
        if isinstance(resp_obj, dict):
            for k in ["resultUrls", "resultUrl", "image_urls", "image_url", "urls", "url", "images"]:
                val = resp_obj.get(k)
                if isinstance(val, list) and val:
                    return val[0]
                elif isinstance(val, str) and (val.startswith("http://") or val.startswith("https://")):
                    return val

        # 3. Cek langsung di task_data
        for k in ["resultUrls", "resultUrl", "image_urls", "urls", "images", "results"]:
            val = task_data.get(k)
            if isinstance(val, list) and val:
                return val[0]
        for k in ["image_url", "url", "image", "result", "resultUrl"]:
            val = task_data.get(k)
            if isinstance(val, str) and (val.startswith("http://") or val.startswith("https://")):
                return val

        return None

    def generate_image(self, prompt, model=None, aspect_ratio="16:9", max_retries=None):
        if not self.api_keys:
            raise ValueError(f"Tidak ada API Key Kie.ai di '{self.key_file}'. Tambahkan key terlebih dahulu.")

        use_model = model or self.get_preferred_model()
        create_task_url = "https://api.kie.ai/api/v1/jobs/createTask"
        record_info_url = "https://api.kie.ai/api/v1/jobs/recordInfo"

        total_keys = len(self.api_keys)
        retries = max_retries if max_retries is not None else total_keys * 2
        last_error = None

        for attempt in range(retries):
            current_key = self.get_active_key()
            headers = {
                "Authorization": f"Bearer {current_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": use_model,
                "input": {
                    "prompt": prompt,
                    "aspect_ratio": aspect_ratio
                }
            }

            try:
                resp = requests.post(create_task_url, json=payload, headers=headers, timeout=30)
                
                if resp.status_code == 200:
                    res_json = resp.json()
                    if res_json.get("code") != 200:
                        err_msg = res_json.get("msg", "Unknown error")
                        last_error = f"Kie.ai error: {err_msg}"
                        if "credit" in err_msg.lower() or "balance" in err_msg.lower() or "auth" in err_msg.lower():
                            self.rotate_key()
                            continue
                        raise RuntimeError(f"Kie.ai createTask gagal: {err_msg}")

                    data_obj = res_json.get("data", {})
                    task_id = data_obj.get("taskId") if isinstance(data_obj, dict) else str(data_obj)
                    if not task_id:
                        raise ValueError(f"Tidak mendapatkan taskId dari Kie.ai: {res_json}")

                    max_poll_time = 90
                    poll_interval = 2.5
                    start_time = time.time()

                    while time.time() - start_time < max_poll_time:
                        time.sleep(poll_interval)
                        poll_resp = requests.get(f"{record_info_url}?taskId={task_id}", headers=headers, timeout=15)
                        if poll_resp.status_code == 200:
                            poll_json = poll_resp.json()
                            if poll_json.get("code") == 200:
                                task_record = poll_json.get("data", {})
                                state = (task_record.get("state") or task_record.get("status") or "").lower()

                                if state in ["success", "completed", "done"]:
                                    img_url = self._extract_image_url(task_record)
                                    if img_url:
                                        return img_url
                                    else:
                                        raise ValueError(f"Task sukses tapi URL gambar tidak ditemukan: {task_record}")
                                elif state in ["fail", "failed", "error"]:
                                    err_detail = task_record.get("errMsg") or task_record.get("msg") or "Generasi gambar gagal di sisi server"
                                    raise RuntimeError(f"Kie.ai job failed: {err_detail}")

                    raise TimeoutError(f"Generasi gambar timeout ({max_poll_time}s) pada taskId: {task_id}")

                elif resp.status_code in [401, 403]:
                    last_error = f"API Key #{self.current_key_index + 1} tidak valid/kuota habis (HTTP {resp.status_code})"
                    self.rotate_key()
                    continue

                elif resp.status_code == 429:
                    last_error = f"API Key #{self.current_key_index + 1} rate limit (HTTP 429)"
                    self.rotate_key()
                    time.sleep(2)
                    continue

                else:
                    err_text = resp.text[:200]
                    last_error = f"HTTP {resp.status_code}: {err_text}"
                    self.rotate_key()
                    continue

            except requests.exceptions.RequestException as e:
                last_error = f"Koneksi gagal ({e})"
                self.rotate_key()
                continue

        raise RuntimeError(f"Gagal generate gambar dengan Kie.ai setelah {retries} percobaan. Error terakhir: {last_error}")

    def _get_system_font(self, size, bold=True):
        for font_path in [
            'C:/Windows/Fonts/segoeuib.ttf' if bold else 'C:/Windows/Fonts/segoeui.ttf',
            'C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf',
            'C:/Windows/Fonts/calibrib.ttf' if bold else 'C:/Windows/Fonts/calibri.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
        ]:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, size)
                except Exception:
                    pass
        return ImageFont.load_default()

    def create_mesh_gradient_banner(self, title, keyword, category="Silo Topic", output_path=None, width=1280, height=720, palette_idx=None, layout_idx=None, footer_mode=None):
        """
        Membuat Featured Image berdesain Mesh Gradient + Glassmorphism secara lokal (Pillow).
        Mendukung 10 Palet Warna & 5 Layout Desain Preset (Anti-Duplicate Engine).
        Footer bergantian antara:
        - Mode 0 (Opsi 1): Clean Minimalist (Tanpa footer, judul ekstra lega & fokus).
        - Mode 1 (Opsi 2): Dynamic Context Deck (Menampilkan estimasi durasi baca & topik kontekstual).
        """
        if not PILLOW_AVAILABLE:
            raise ImportError("Pillow belum terinstall. Jalankan: pip install pillow")

        # 0. Bersihkan HTML entities agar teks thumbnail rapi & bersih
        title = clean_text_for_rendering(title)
        keyword = clean_text_for_rendering(keyword)
        category = clean_text_for_rendering(category)

        # 1. Tentukan Palet Warna, Layout Presets, & Mode Footer
        if palette_idx is None:
            palette_idx = abs(hash(title + keyword + "palette")) % len(MESH_PALETTES)
        else:
            palette_idx = palette_idx % len(MESH_PALETTES)

        if layout_idx is None:
            layout_idx = abs(hash(keyword + title + "layout")) % len(LAYOUT_NAMES)
        else:
            layout_idx = layout_idx % len(LAYOUT_NAMES)

        if footer_mode is None:
            footer_mode = abs(hash(title + keyword + "footer_mode")) % 2

        base_bg, c1, c2, c3, accent_c = MESH_PALETTES[palette_idx]
        layout_mode = LAYOUT_NAMES[layout_idx]

        # 2. Render mesh gradient beresolusi rendah lalu Gaussian Blur untuk gradasi super lembut
        small_w, small_h = 320, 180
        bg = Image.new('RGB', (small_w, small_h), base_bg)
        draw = ImageDraw.Draw(bg)

        blob_seed = abs(hash(keyword + title + "blob")) % 4
        if blob_seed == 0:
            draw.ellipse([small_w * 0.45, -small_h * 0.35, small_w * 1.35, small_h * 0.95], fill=c1)
            draw.ellipse([-small_w * 0.35, small_h * 0.35, small_w * 0.65, small_h * 1.35], fill=c2)
            draw.ellipse([small_w * 0.25, small_h * 0.25, small_w * 1.15, small_h * 1.25], fill=c3)
        elif blob_seed == 1:
            draw.ellipse([-small_w * 0.2, -small_h * 0.3, small_w * 0.8, small_h * 0.8], fill=c1)
            draw.ellipse([small_w * 0.35, small_h * 0.2, small_w * 1.3, small_h * 1.3], fill=c2)
            draw.ellipse([small_w * 0.1, -small_h * 0.1, small_w * 0.9, small_h * 0.9], fill=c3)
        elif blob_seed == 2:
            draw.ellipse([small_w * 0.2, -small_h * 0.4, small_w * 1.1, small_h * 0.7], fill=c2)
            draw.ellipse([-small_w * 0.3, small_h * 0.2, small_w * 0.6, small_h * 1.2], fill=c1)
            draw.ellipse([small_w * 0.5, small_h * 0.4, small_w * 1.2, small_h * 1.2], fill=c3)
        else:
            draw.ellipse([small_w * 0.1, small_h * 0.3, small_w * 0.9, small_h * 1.2], fill=c3)
            draw.ellipse([small_w * 0.4, -small_h * 0.2, small_w * 1.2, small_h * 0.8], fill=c2)
            draw.ellipse([-small_w * 0.3, -small_h * 0.3, small_w * 0.6, small_h * 0.7], fill=c1)

        bg = bg.filter(ImageFilter.GaussianBlur(radius=38))
        bg = bg.resize((width, height), Image.Resampling.BICUBIC)

        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)

        # Vignette lembut di bawah
        for y in range(height):
            alpha = int(120 * (y / height) ** 1.6)
            odraw.line([(0, y), (width, y)], fill=(10, 15, 28, alpha))

        # 3. Setup Koordinat & Desain Berdasarkan Preset Layout
        if layout_mode == "left_editorial":
            pad_x = int(width * 0.055)
            pad_y = int(height * 0.09)
            card_w = int(width * 0.68)
            card_h = height - (2 * pad_y)
            odraw.rounded_rectangle(
                [pad_x, pad_y, pad_x + card_w, pad_y + card_h],
                radius=24,
                fill=(12, 18, 34, 160),
                outline=(255, 255, 255, 40),
                width=2
            )
            accent_x = width - int(pad_x * 1.4)
            odraw.rounded_rectangle([accent_x, pad_y + 40, accent_x + 4, height - pad_y - 40], radius=2, fill=accent_c)

        elif layout_mode == "pill_centered":
            pad_x = int(width * 0.10)
            pad_y = int(height * 0.11)
            card_w = width - (2 * pad_x)
            card_h = height - (2 * pad_y)
            odraw.rounded_rectangle(
                [pad_x, pad_y, width - pad_x, height - pad_y],
                radius=32,
                fill=(15, 23, 42, 150),
                outline=(255, 255, 255, 48),
                width=2
            )

        elif layout_mode == "accent_bar":
            pad_x = int(width * 0.075)
            pad_y = int(height * 0.10)
            card_w = width - (2 * pad_x)
            card_h = height - (2 * pad_y)
            odraw.rounded_rectangle(
                [pad_x, pad_y, width - pad_x, height - pad_y],
                radius=24,
                fill=(14, 20, 36, 140),
                outline=(255, 255, 255, 42),
                width=2
            )
            odraw.rounded_rectangle(
                [pad_x + 36, pad_y + 40, pad_x + 44, height - pad_y - 40],
                radius=4,
                fill=accent_c
            )

        elif layout_mode == "bottom_dock":
            pad_x = int(width * 0.065)
            dock_y = int(height * 0.28)
            pad_y = dock_y
            card_w = width - (2 * pad_x)
            card_h = height - dock_y - int(height * 0.06)
            odraw.rounded_rectangle(
                [pad_x, dock_y, width - pad_x, height - int(height * 0.06)],
                radius=24,
                fill=(10, 16, 30, 165),
                outline=(255, 255, 255, 50),
                width=2
            )
            odraw.line([(pad_x + 30, dock_y + 1), (width - pad_x - 30, dock_y + 1)], fill=accent_c, width=3)

        else:
            pad_x = int(width * 0.075)
            pad_y = int(height * 0.11)
            card_w = width - (2 * pad_x)
            card_h = height - (2 * pad_y)
            odraw.rounded_rectangle(
                [pad_x, pad_y, width - pad_x, height - pad_y],
                radius=26,
                fill=(15, 23, 42, 145),
                outline=(255, 255, 255, 45),
                width=2
            )

        final_img = Image.alpha_composite(bg.convert('RGBA'), overlay)
        fdraw = ImageDraw.Draw(final_img)

        # 4. Dynamic Auto-Fit Typography Engine
        inner_pad_x = int(card_w * 0.075)
        if layout_mode == "accent_bar":
            inner_pad_x = int(card_w * 0.075) + 30
        
        content_w = card_w - (2 * inner_pad_x)
        footer_h = 28 if footer_mode == 1 else 0
        usable_h = card_h - (120 if footer_mode == 1 else 90)

        dummy_img = Image.new('RGB', (10, 10))
        dt = ImageDraw.Draw(dummy_img)

        best_font = None
        best_size = 44
        best_lines = []
        best_line_h = 54
        best_total_h = 54

        max_font_try = 66 if footer_mode == 0 else 60
        for font_size in range(max_font_try, 28, -2):
            f = self._get_system_font(font_size, bold=True)
            chars_per_line = max(14, int(content_w / (font_size * 0.52)))
            lines = textwrap.wrap(title.strip(), width=chars_per_line)
            if not lines or len(lines) > 3:
                continue
            max_line_w = max(dt.textlength(line, font=f) for line in lines)
            line_h = int(font_size * 1.26)
            total_h = len(lines) * line_h

            if max_line_w <= content_w and total_h <= usable_h:
                best_font = f
                best_size = font_size
                best_lines = lines
                best_line_h = line_h
                best_total_h = total_h
                break

        if not best_font:
            best_size = 32
            best_font = self._get_system_font(32, bold=True)
            best_lines = textwrap.wrap(title.strip(), width=int(content_w / 18))[:3]
            best_line_h = int(32 * 1.26)
            best_total_h = len(best_lines) * best_line_h

        # 5. Proportional Vertical Centering & Element Placement
        badge_h = 36
        combined_elements_h = badge_h + best_total_h + footer_h
        available_space = card_h - combined_elements_h

        top_margin = max(30, int(available_space * (0.35 if footer_mode == 0 else 0.28)))
        badge_y = pad_y + top_margin
        title_gap = max(18, int(available_space * (0.26 if footer_mode == 0 else 0.22)))
        title_start_y = badge_y + badge_h + title_gap

        # A. Pill Badge (Kategori / Silo Role)
        clean_cat = category.strip().upper()
        if clean_cat in ["UNCATEGORIZED", "DEFAULT", "TANPA KATEGORI"]:
            clean_cat = "FEATURED TOPIC"
        elif len(clean_cat) > 28:
            clean_cat = clean_cat[:26] + ".."
        
        badge_text = clean_cat
        badge_font = self._get_system_font(max(13, int(best_size * 0.35)), bold=True)
        
        # Hitung bounding box teks dengan presisi pixel
        badge_bbox = dt.textbbox((0, 0), badge_text, font=badge_font)
        btw = badge_bbox[2] - badge_bbox[0]
        bth = badge_bbox[3] - badge_bbox[1]
        
        badge_pad_h = 16  # Padding horizontal
        badge_pad_v = 7   # Padding vertical
        badge_w = int(btw + (2 * badge_pad_h))
        badge_h = int(bth + (2 * badge_pad_v))

        if layout_mode == "pill_centered":
            badge_x = (width - badge_w) // 2
        else:
            badge_x = pad_x + inner_pad_x

        # Render Pill Background dengan radius melengkung halus
        fdraw.rounded_rectangle(
            [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
            radius=int(badge_h / 2),
            fill=accent_c
        )
        
        # Render Teks tepat di titik pusat geometris pill
        btx = badge_x + (badge_w - btw) / 2 - badge_bbox[0]
        bty = badge_y + (badge_h - bth) / 2 - badge_bbox[1]
        fdraw.text((btx, bty), badge_text, fill=(255, 255, 255), font=badge_font)

        # B. Wrapped Headline Title Lines
        curr_y = title_start_y
        for line in best_lines:
            line_w = dt.textlength(line, font=best_font)
            if layout_mode == "pill_centered":
                line_x = (width - line_w) // 2
            else:
                line_x = pad_x + inner_pad_x
            fdraw.text((line_x, curr_y), line, fill=(255, 255, 255), font=best_font)
            curr_y += best_line_h

        # C. Footer Deck (Hanya dirender jika footer_mode == 1)
        if footer_mode == 1:
            dynamic_footer_text = build_dynamic_footer_text(title, keyword, category)
            footer_font = self._get_system_font(max(16, int(best_size * 0.42)), bold=False)
            footer_y = pad_y + card_h - max(34, int(available_space * 0.24))

            if layout_mode == "pill_centered":
                fw = dt.textlength(dynamic_footer_text, font=footer_font)
                fx = (width - fw) // 2
            else:
                fx = pad_x + inner_pad_x

            fdraw.text((fx, footer_y), dynamic_footer_text, fill=(203, 213, 225), font=footer_font)

        # Simpan file
        if output_path:
            out_dir = os.path.dirname(output_path)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            rgb_img = final_img.convert('RGB')
            if output_path.lower().endswith(".webp"):
                rgb_img.save(output_path, "WEBP", quality=90)
            else:
                rgb_img.save(output_path, "JPEG", quality=92)
            return output_path
        return final_img

    def generate_and_save(self, prompt, save_path, model=None, aspect_ratio="16:9"):
        """
        Men-generate gambar dari Kie.ai dan langsung mendownload serta menyimpannya ke disk lokal
        dengan konversi format otomatis (WebP / JPEG / PNG) yang valid.
        """
        save_dir = os.path.dirname(save_path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
        img_url = self.generate_image(prompt, model=model, aspect_ratio=aspect_ratio)

        # Download gambar
        img_bytes = None
        if img_url.startswith("http://") or img_url.startswith("https://"):
            resp = requests.get(img_url, timeout=30)
            if resp.status_code == 200:
                img_bytes = resp.content
            else:
                raise RuntimeError(f"Gagal mendownload gambar dari URL {img_url} (HTTP {resp.status_code})")
        elif img_url.startswith("data:image") or len(img_url) > 500:
            import base64
            b64_data = re.sub(r'^data:image/.+;base64,', '', img_url)
            img_bytes = base64.b64decode(b64_data)
        else:
            raise ValueError(f"URL gambar tidak valid: {img_url}")

        # Konversi ke WebP / format target yang sesuai menggunakan PIL
        if PILLOW_AVAILABLE and img_bytes:
            from io import BytesIO
            try:
                im = Image.open(BytesIO(img_bytes))
                if save_path.lower().endswith(".webp"):
                    if im.mode in ("RGBA", "LA", "P"):
                        im = im.convert("RGB")
                    im.save(save_path, "WEBP", quality=90, method=6)
                elif save_path.lower().endswith((".jpg", ".jpeg")):
                    if im.mode in ("RGBA", "LA", "P"):
                        im = im.convert("RGB")
                    im.save(save_path, "JPEG", quality=92)
                else:
                    im.save(save_path)
                return save_path, img_url
            except Exception:
                pass

        # Fallback raw write jika PIL tidak tersedia
        with open(save_path, "wb") as f:
            f.write(img_bytes)
        return save_path, img_url

    def generate_featured_image_auto(self, title, keyword, category, save_path, gemini_client=None, model=None):
        """
        Generator Featured Image terpadu dengan 3 mode:
        1. 'hybrid': Coba Kie.ai AI Photo -> Jika gagal/tanpa key ➔ Otomatis buat Mesh Gradient Banner (100% Reliable).
        2. 'mesh_gradient': Langsung buat Mesh Gradient Banner lokal (0 Biaya, instan).
        3. 'kie_only': Hanya buat lewat Kie.ai.
        
        Returns: (saved_path, method_used: 'kie_ai' | 'mesh_gradient')
        """
        save_dir = os.path.dirname(save_path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
        mode = self.get_image_mode()

        # Mode 2: Always Mesh Gradient
        if mode == "mesh_gradient":
            self.create_mesh_gradient_banner(
                title=title,
                keyword=keyword,
                category=category,
                output_path=save_path
            )
            return save_path, "mesh_gradient"

        # Mode 1 & 3: Try Kie.ai first
        if self.api_keys and mode in ["hybrid", "kie_only"]:
            try:
                img_prompt = self.build_image_prompt(title, keyword, category, gemini_client=gemini_client)
                self.generate_and_save(img_prompt, save_path, model=model or self.get_preferred_model(), aspect_ratio="16:9")
                return save_path, "kie_ai"
            except Exception as e:
                if mode == "kie_only":
                    raise e
                # Fallback to mesh gradient in hybrid mode
                pass

        # Hybrid fallback: Generate local Mesh Gradient
        if mode == "hybrid":
            self.create_mesh_gradient_banner(
                title=title,
                keyword=keyword,
                category=category,
                output_path=save_path
            )
            return save_path, "mesh_gradient"

        raise RuntimeError("Gagal menghasilkan gambar.")
