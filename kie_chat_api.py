import json
import os
import re
import time
import requests

KIE_KEY_FILE = "kie_apikey.txt"

class KieChatClient:
    def __init__(self, key_file=KIE_KEY_FILE, model="gpt-6-luna"):
        self.key_file = key_file
        self.model = model
        self.api_keys = self._load_keys()
        self.current_key_idx = 0
        self.endpoint_map = {
            "gpt-6-luna": "https://api.kie.ai/gpt-5-2/v1/chat/completions",
            "gpt-6": "https://api.kie.ai/gpt-5-2/v1/chat/completions",
            "gpt-5.2": "https://api.kie.ai/gpt-5-2/v1/chat/completions",
            "gpt-5.6": "https://api.kie.ai/gpt-5-2/v1/chat/completions",
            "gpt-5": "https://api.kie.ai/gpt-5-2/v1/chat/completions",
            "gpt-5-luna": "https://api.kie.ai/gpt-5-2/v1/chat/completions"
        }

    def _load_keys(self):
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
        return keys

    def reload_keys(self):
        self.api_keys = self._load_keys()
        if self.current_key_idx >= len(self.api_keys):
            self.current_key_idx = 0
        return self.api_keys

    def get_current_key(self):
        if not self.api_keys:
            self.reload_keys()
        if not self.api_keys:
            raise ValueError(f"Tidak ada API Key Kie.ai di '{self.key_file}'. Tambahkan minimal 1 API Key Kie.ai.")
        return self.api_keys[self.current_key_idx % len(self.api_keys)]

    def rotate_key(self):
        if len(self.api_keys) > 1:
            old_idx = self.current_key_idx
            self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
            return True, old_idx + 1, self.current_key_idx + 1
        return False, 1, 1

    def get_working_model(self):
        return f"Kie.ai GPT-6 Luna"

    def generate_text(self, prompt, system_instruction=None, temperature=0.7, max_retries=5):
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "messages": messages,
            "temperature": temperature
        }

        url = self.endpoint_map.get(self.model, "https://api.kie.ai/gpt-5-2/v1/chat/completions")
        last_error = None

        for attempt in range(max_retries):
            key = self.get_current_key()
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }

            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=120)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices and "message" in choices[0]:
                        return choices[0]["message"].get("content", "").strip()
                    elif "data" in data and isinstance(data["data"], str):
                        return data["data"].strip()
                    elif data.get("code") == 422:
                        last_error = f"Kie Error: {data.get('msg')}"
                    else:
                        return resp.text.strip()

                elif resp.status_code in [401, 403, 429]:
                    rotated, old_k, new_k = self.rotate_key()
                    last_error = f"Key #{old_k} (HTTP {resp.status_code})"
                    if rotated:
                        print(f" [Auto-Failover: Kie Key #{old_k} limit/error -> Beralih ke Key #{new_k}]", flush=True)
                    time.sleep(1)

                else:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:120]}"
                    time.sleep(2)

            except Exception as e:
                rotated, old_k, new_k = self.rotate_key()
                last_error = f"Error: {str(e)}"
                time.sleep(2)

        raise Exception(f"Gagal memanggil Kie.ai GPT-5 setelah {max_retries} percobaan ({last_error})")

    def generate_json(self, prompt, system_instruction=None, temperature=0.3):
        json_guide = (
            "KEMBALIKAN HANYA OBJEK JSON VALID TANPA TEKS LAIN ATAU BACKTICKS (```json ... ```). "
            "Format JSON harus bersih dan dapat di-parse langsung oleh Python json.loads."
        )
        full_system = f"{system_instruction}\n\n{json_guide}" if system_instruction else json_guide
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
        except json.JSONDecodeError:
            match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', cleaned)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
            raise Exception(f"Gagal parse JSON dari Kie.ai GPT-5. Respons: {raw_text[:200]}...")
