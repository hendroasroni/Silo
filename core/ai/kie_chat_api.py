import json
import os
import re
import time
import requests
from core.config_utils import get_config_path

KIE_KEY_FILE = "kie_apikey.txt"

class KieChatClient:
    def __init__(self, key_file=KIE_KEY_FILE, model="gpt-6-luna"):
        self.key_file = get_config_path(key_file)
        self.model = model or "gpt-6-luna"
        self.api_keys = self._load_keys()
        self.current_key_idx = 0
        self.codex_endpoint = "https://api.kie.ai/codex/v1/responses"

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
        return f"Kie.ai ({self.model})"

    def generate_text(self, prompt, system_instruction=None, temperature=0.7, max_retries=5):
        """
        Menjalankan chat completions menggunakan model Kie.ai (GPT-6 Luna via Codex Responses API).
        Mendukung parsing SSE streaming & raw JSON response, serta auto-failover antar key.
        """
        inputs = []
        if system_instruction:
            inputs.append({
                "role": "system",
                "content": [{"type": "input_text", "text": system_instruction}]
            })
        inputs.append({
            "role": "user",
            "content": [{"type": "input_text", "text": prompt}]
        })

        payload = {
            "model": self.model,
            "input": inputs,
            "temperature": temperature
        }

        total_keys = max(len(self.api_keys), 1)
        actual_retries = max(max_retries, total_keys * 2)
        last_error = None

        for attempt in range(actual_retries):
            key = self.get_current_key()
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }

            try:
                resp = requests.post(
                    self.codex_endpoint,
                    json=payload,
                    headers=headers,
                    stream=True,
                    timeout=60
                )

                if resp.status_code == 200:
                    collected_deltas = []
                    final_text = None
                    error_detected = None

                    for line in resp.iter_lines(decode_unicode=True):
                        if not line:
                            continue
                        line_str = line.strip()

                        # 1. Deteksi respons error raw JSON (tanpa prefix data:)
                        if line_str.startswith("{") and line_str.endswith("}"):
                            try:
                                raw_obj = json.loads(line_str)
                                if raw_obj.get("code") in [401, 402, 403, 422, 429, 500] or "insufficient" in str(raw_obj.get("msg", "")).lower():
                                    error_detected = f"Kredit Habis / Limit ({raw_obj.get('msg', 'Code ' + str(raw_obj.get('code')))})"
                                    break
                            except Exception:
                                pass

                        # 2. Deteksi respons SSE data:
                        if line_str.startswith("data:"):
                            data_str = line_str[5:].strip()
                            if not data_str or data_str == "[DONE]":
                                continue
                            try:
                                ev = json.loads(data_str)
                                if ev.get("code") in [401, 402, 403, 429] or "insufficient" in str(ev.get("msg", "")).lower():
                                    error_detected = f"Kredit Habis / Limit ({ev.get('msg', 'Code ' + str(ev.get('code')))})"
                                    break
                                elif ev.get("code") in [422, 500]:
                                    error_detected = f"Kie Error ({ev.get('msg')})"
                                    break
                                
                                ev_type = ev.get("type", "")
                                if ev_type == "response.completed":
                                    resp_obj = ev.get("response", {})
                                    for out in resp_obj.get("output", []):
                                        if out.get("type") == "message":
                                            for c in out.get("content", []):
                                                if c.get("type") == "output_text" and c.get("text"):
                                                    final_text = c.get("text").strip()
                                elif ev_type == "response.output_text.delta":
                                    d = ev.get("delta")
                                    if isinstance(d, str):
                                        collected_deltas.append(d)
                                    elif isinstance(d, dict) and d.get("text"):
                                        collected_deltas.append(d["text"])
                                elif "delta" in ev and isinstance(ev["delta"], str):
                                    collected_deltas.append(ev["delta"])
                            except Exception:
                                pass

                    if error_detected:
                        rotated, old_k, new_k = self.rotate_key()
                        last_error = f"Key #{old_k} ({error_detected})"
                        if rotated:
                            print(f" [Auto-Failover: Kie Key #{old_k} limit/habis -> Beralih ke Key #{new_k}]", flush=True)
                        time.sleep(1)
                        continue

                    full_res = final_text or "".join(collected_deltas).strip()
                    if full_res:
                        return full_res
                    else:
                        last_error = "Respons kosong dari Kie.ai Codex API"

                elif resp.status_code in [401, 402, 403, 429]:
                    rotated, old_k, new_k = self.rotate_key()
                    last_error = f"Key #{old_k} (HTTP {resp.status_code})"
                    if rotated:
                        print(f" [Auto-Failover: Kie Key #{old_k} limit/error -> Beralih ke Key #{new_k}]", flush=True)
                    time.sleep(1)

                else:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:120]}"
                    self.rotate_key()
                    time.sleep(1)

            except requests.exceptions.Timeout:
                rotated, old_k, new_k = self.rotate_key()
                last_error = f"Timeout 60s pada Key #{old_k}"
                print(f" [Kie.ai Timeout -> Mencoba Key #{new_k}]", flush=True)
                time.sleep(1)
            except Exception as e:
                rotated, old_k, new_k = self.rotate_key()
                last_error = f"Error: {str(e)}"
                time.sleep(1)

        raise Exception(f"Gagal memanggil Kie.ai {self.model} setelah {actual_retries} percobaan ({last_error})")

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
            raise Exception(f"Gagal parse JSON dari Kie.ai {self.model}. Respons: {raw_text[:200]}...")
