import os
import json
import re
import time
import requests

try:
    from PIL import Image
    from io import BytesIO
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

AGNES_KEY_FILE = "agnes_apikey.txt"
AGNES_CONFIG_FILE = "agnes_config.json"

DEFAULT_AGNES_TEXT_MODELS = [
    ("agnes-3.0-flash", "Agnes 3.0 Flash (Model Tercepat & Cerdas - Rekomendasi)"),
    ("agnes-2.5-flash", "Agnes 2.5 Flash (Stabil & Responsif)"),
    ("agnes-2.5-pro", "Agnes 2.5 Pro (Penalaran Mendalam & Analisis Kompleks)"),
    ("agnes-2.5-pro-beta", "Agnes 2.5 Pro Beta"),
]

DEFAULT_AGNES_IMAGE_MODELS = [
    ("agnes-image-2.0-flash", "Agnes Image 2.0 Flash (Cepat & Bersih)"),
    ("agnes-image-2.5-flash", "Agnes Image 2.5 Flash (Resolusi Tinggi & Detail)"),
]

class AgnesClient:
    def __init__(self, key_file=AGNES_KEY_FILE, config_file=AGNES_CONFIG_FILE, model=None):
        self.key_file = key_file
        self.config_file = config_file
        self.api_keys = self.reload_keys()
        self.current_key_index = 0
        self.config = self._load_config()
        self.custom_model = model

    def get_working_model(self):
        return self.custom_model or self.get_preferred_text_model()

    def _load_config(self):
        default_cfg = {
            "text_model": "agnes-3.0-flash",
            "image_model": "agnes-image-2.0-flash",
            "api_base_url": "https://apihub.agnes-ai.com/v1",
            "image_size": "1024x1024"
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

    def get_preferred_text_model(self):
        return self.config.get("text_model", "agnes-3.0-flash")

    def set_preferred_text_model(self, model_name):
        self.config["text_model"] = model_name.strip()
        self._save_config()

    def get_preferred_image_model(self):
        return self.config.get("image_model", "agnes-image-2.0-flash")

    def set_preferred_image_model(self, model_name):
        self.config["image_model"] = model_name.strip()
        self._save_config()

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
        env_k = os.environ.get("AGNES_API_KEY", "").strip()
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
        endpoint = f"{self.config.get('api_base_url', 'https://apihub.agnes-ai.com/v1')}/models"
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json"
        }
        try:
            resp = requests.get(endpoint, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                models_count = len(data.get("data", []))
                return True, f"Valid ({models_count} Model Tersedia)"
            elif resp.status_code in [401, 403]:
                return False, f"Auth Gagal / Key Tidak Valid (HTTP {resp.status_code})"
            else:
                return False, f"HTTP Error {resp.status_code}: {resp.text[:100]}"
        except requests.exceptions.RequestException as e:
            return False, f"Koneksi Gagal: {str(e)[:100]}"

    def test_all_keys(self):
        results = []
        keys = self.reload_keys()
        if not keys:
            return results

        for i, k in enumerate(keys, 1):
            masked = f"{k[:8]}...{k[-4:]}" if len(k) >= 12 else k
            is_valid, msg = self.check_key_validity(k)
            results.append({
                "index": i,
                "key": k,
                "masked": masked,
                "is_valid": is_valid,
                "message": msg
            })
        return results

    def generate_text(self, prompt, system_instruction=None, temperature=0.7, max_retries=None, model=None):
        if not self.api_keys:
            raise ValueError(f"Tidak ada API Key Agnes AI di '{self.key_file}'.")

        use_model = model or self.custom_model or self.get_preferred_text_model()
        endpoint = f"{self.config.get('api_base_url', 'https://apihub.agnes-ai.com/v1')}/chat/completions"

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": use_model,
            "messages": messages,
            "temperature": temperature
        }

        total_keys = len(self.api_keys)
        retries = max_retries if max_retries is not None else total_keys * 2
        last_error = None

        for attempt in range(retries):
            current_key = self.get_active_key()
            headers = {
                "Authorization": f"Bearer {current_key}",
                "Content-Type": "application/json"
            }

            try:
                resp = requests.post(endpoint, json=payload, headers=headers, timeout=120)
                if resp.status_code == 200:
                    res_json = resp.json()
                    choices = res_json.get("choices", [])
                    if choices and "message" in choices[0]:
                        msg_obj = choices[0]["message"]
                        content = msg_obj.get("content", "")
                        return content.strip()
                    raise ValueError(f"Struktur output Agnes AI tidak dikenali: {res_json}")

                elif resp.status_code in [401, 403]:
                    last_error = f"API Key #{self.current_key_index + 1} tidak valid (HTTP {resp.status_code})"
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
                    time.sleep(1)
                    continue

            except requests.exceptions.RequestException as e:
                last_error = f"Koneksi gagal ({e})"
                self.rotate_key()
                continue

        raise RuntimeError(f"Gagal generate teks dengan Agnes AI setelah {retries} percobaan. Error: {last_error}")

    def generate_json(self, prompt, system_instruction=None, temperature=0.3, model=None):
        json_instruction = (
            "KEMBALIKAN HANYA JSON VALID TANPA MARKDOWN (tanpa ```json ... ``` atau teks tambahan di luar JSON). "
            "Pastikan format JSON benar dan dapat di-parse langsung oleh json.loads."
        )
        full_system = f"{system_instruction}\n\n{json_instruction}" if system_instruction else json_instruction
        raw_text = self.generate_text(prompt, system_instruction=full_system, temperature=temperature, model=model)

        clean_text = raw_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            json_match = re.search(r'(\{.*\}|\[.*\])', clean_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except Exception:
                    pass
            raise ValueError(f"Gagal mem-parsing output JSON dari Agnes AI:\n{clean_text[:400]}")

    def generate_image(self, prompt, model=None, size="1024x1024", max_retries=None):
        if not self.api_keys:
            raise ValueError(f"Tidak ada API Key Agnes AI di '{self.key_file}'.")

        use_model = model or self.get_preferred_image_model()
        endpoint = f"{self.config.get('api_base_url', 'https://apihub.agnes-ai.com/v1')}/images/generations"

        payload = {
            "model": use_model,
            "prompt": prompt,
            "size": size
        }

        total_keys = len(self.api_keys)
        retries = max_retries if max_retries is not None else total_keys * 2
        last_error = None

        for attempt in range(retries):
            current_key = self.get_active_key()
            headers = {
                "Authorization": f"Bearer {current_key}",
                "Content-Type": "application/json"
            }

            try:
                resp = requests.post(endpoint, json=payload, headers=headers, timeout=60)
                if resp.status_code == 200:
                    res_json = resp.json()
                    data_list = res_json.get("data", [])
                    if data_list and isinstance(data_list, list):
                        img_url = data_list[0].get("url") or data_list[0].get("b64_json")
                        if img_url:
                            return img_url
                    raise ValueError(f"URL gambar tidak ditemukan pada output Agnes AI: {res_json}")

                elif resp.status_code in [401, 403]:
                    last_error = f"API Key #{self.current_key_index + 1} tidak valid (HTTP {resp.status_code})"
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

        raise RuntimeError(f"Gagal generate gambar dengan Agnes AI setelah {retries} percobaan. Error: {last_error}")

    def generate_and_save(self, prompt, save_path, model=None, size="1024x1024"):
        save_dir = os.path.dirname(save_path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)

        img_url = self.generate_image(prompt, model=model, size=size)

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

        if PILLOW_AVAILABLE and img_bytes:
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

        with open(save_path, "wb") as f:
            f.write(img_bytes)
        return save_path, img_url
