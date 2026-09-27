import json
import os
import time
import requests

GEMINI_CONFIG_FILE = "gemini_config.json"

DEFAULT_FLASH_MODELS = [
    ("gemini-3.8-flash", "Gemini 3.8 Flash (Paling Cepat, Terbaru & Direkomendasikan untuk SEO)"),
    ("gemini-3.7-flash", "Gemini 3.7 Flash (Cepat & Stabil)"),
    ("gemini-3.5-flash", "Gemini 3.5 Flash (Sangat Hemat Kuota)"),
    ("gemini-3-flash-preview", "Gemini 3 Flash Preview"),
    ("gemini-flash-latest", "Gemini Flash Latest (Otomatis Versi Terbaru)")
]

DEFAULT_PRO_MODELS = [
    ("gemini-3.7-pro", "Gemini 3.7 Pro (Penalaran Mendalam & Analisis Kompleks)"),
    ("gemini-pro-latest", "Gemini Pro Latest (Versi Pro Terbaru)"),
    ("gemini-3.1-pro-preview", "Gemini 3.1 Pro Preview"),
    ("gemini-2.5-pro", "Gemini 2.5 Pro")
]

class GeminiClient:
    def __init__(self, key_file="apikey.txt", config_file=GEMINI_CONFIG_FILE):
        self.key_file = key_file
        self.config_file = config_file
        self.api_keys = self._load_keys()
        self.current_key_idx = 0
        self.config = self._load_config()
        self.active_model = self.config.get("preferred_model", "gemini-3.8-flash")

    def _load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {"preferred_model": "gemini-3.8-flash"}

    def _save_config(self):
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def set_preferred_model(self, model_name):
        model_name = model_name.strip()
        if model_name:
            self.config["preferred_model"] = model_name
            self.active_model = model_name
            self._save_config()
            return True
        return False

    def get_preferred_model(self):
        return self.config.get("preferred_model", "gemini-3.8-flash")

    def _load_keys(self):
        if not os.path.exists(self.key_file):
            return []
        with open(self.key_file, "r", encoding="utf-8") as f:
            keys = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        return keys

    def reload_keys(self):
        self.api_keys = self._load_keys()
        if self.current_key_idx >= len(self.api_keys):
            self.current_key_idx = 0
        return self.api_keys

    def add_key(self, new_key):
        new_key = new_key.strip()
        if not new_key:
            return False
        if new_key in self.api_keys:
            return False

        with open(self.key_file, "a", encoding="utf-8") as f:
            f.write(f"\n{new_key}")
        
        self.reload_keys()
        return True

    def remove_key(self, index):
        if 0 <= index < len(self.api_keys):
            removed = self.api_keys.pop(index)
            self._save_keys(self.api_keys)
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
            for k in keys_list:
                f.write(f"{k}\n")

    def get_current_key(self):
        if not self.api_keys:
            self.reload_keys()
        if not self.api_keys:
            raise ValueError(f"Tidak ada API Key Gemini di '{self.key_file}'. Tambahkan minimal 1 API Key.")
        return self.api_keys[self.current_key_idx % len(self.api_keys)]

    def rotate_key(self):
        if len(self.api_keys) > 1:
            old_idx = self.current_key_idx
            self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
            return True, old_idx + 1, self.current_key_idx + 1
        return False, 1, 1

    def test_key(self, key_str):
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key_str}"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                models = [m['name'].replace('models/', '') for m in data.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
                flash_models = [m for m in models if 'flash' in m]
                pro_models = [m for m in models if 'pro' in m]
                return True, f"Valid! Total {len(models)} model aktif ({len(flash_models)} Flash, {len(pro_models)} Pro)"
            elif resp.status_code == 400:
                return False, "Invalid Key (API key tidak valid / salah)"
            elif resp.status_code == 429:
                return False, "Rate Limit / Quota Habis (429)"
            else:
                return False, f"HTTP Error {resp.status_code}"
        except Exception as e:
            return False, f"Error koneksi: {str(e)}"

    def test_all_keys(self):
        self.reload_keys()
        results = []
        for i, k in enumerate(self.api_keys, 1):
            masked = f"{k[:8]}...{k[-4:]}" if len(k) >= 12 else k
            ok, msg = self.test_key(k)
            results.append({
                "index": i,
                "key": k,
                "masked": masked,
                "is_valid": ok,
                "message": msg
            })
        return results

    def get_working_model(self):
        if self.active_model:
            return self.active_model
        self.active_model = self.get_preferred_model()
        return self.active_model

    def generate_text(self, prompt, system_instruction=None, temperature=0.7, max_retries=6):
        contents = []
        if system_instruction:
            contents.append({
                "role": "user",
                "parts": [{"text": f"[INSTRUKSI SISTEM / PANDUAN KERJA]:\n{system_instruction}\n\nLakukan tugas berikut berdasarkan instruksi di atas."}]
            })
            contents.append({
                "role": "model",
                "parts": [{"text": "Baik, saya mengerti seluruh panduan dan instruksi tersebut. Silakan berikan detail tugasnya."}]
            })
            
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 8192
            }
        }

        active_model = self.get_preferred_model()
        flash_names = [m[0] for m in DEFAULT_FLASH_MODELS]
        pro_names = [m[0] for m in DEFAULT_PRO_MODELS]
        fallback_models = [m for m in flash_names + pro_names if m != active_model]
        
        current_model = active_model
        fallback_model_idx = 0
        
        total_keys = max(len(self.api_keys), 1)
        actual_retries = max(max_retries, total_keys * 2)
        last_error = None

        for attempt in range(actual_retries):
            key = self.get_current_key()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={key}"
            
            try:
                resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=120)
                
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        self.active_model = current_model
                        return "".join([p.get("text", "") for p in parts]).strip()
                    return ""
                
                elif resp.status_code in [400, 403, 429]:
                    rotated, old_k, new_k = self.rotate_key()
                    last_error = f"Key #{old_k} (HTTP {resp.status_code})"
                    if rotated:
                        print(f" [Auto-Failover: Key #{old_k} limit/error -> Beralih ke Key #{new_k}]", flush=True)
                    time.sleep(1)

                elif resp.status_code == 404:
                    # Model tidak ditemukan, baru ganti model alternatif
                    if fallback_model_idx < len(fallback_models):
                        current_model = fallback_models[fallback_model_idx]
                        fallback_model_idx += 1
                        last_error = f"Model diganti ke {current_model} (404 pada model sebelumnya)"
                    else:
                        last_error = f"Model {current_model} (HTTP 404)"
                    time.sleep(1)

                elif resp.status_code in [500, 503]:
                    rotated, old_k, new_k = self.rotate_key()
                    last_error = f"Model {current_model} (HTTP {resp.status_code})"
                    time.sleep(2)

                else:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:150]}"
                    self.rotate_key()
                    time.sleep(1)

            except Exception as e:
                rotated, old_k, new_k = self.rotate_key()
                last_error = f"Error ({str(e)})"
                time.sleep(2)
        
        raise Exception(f"Gagal memanggil Gemini API setelah {actual_retries} percobaan ({last_error})")

    def generate_json(self, prompt, system_instruction=None, temperature=0.3):
        json_instruction = (
            "KEMBALIKAN HANYA JSON VALID TANPA MARKDOWN (tanpa ```json ... ``` atau teks tambahan di luar JSON). "
            "Pastikan format JSON benar dan dapat di-parse langsung oleh json.loads."
        )
        full_system = f"{system_instruction}\n\n{json_instruction}" if system_instruction else json_instruction
        raw_text = self.generate_text(prompt, system_instruction=full_system, temperature=temperature)
        
        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            import re
            match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', cleaned)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
            raise Exception(f"Gagal mem-parse JSON dari respons AI: {str(e)}\nRespons Mentah:\n{raw_text[:500]}")
