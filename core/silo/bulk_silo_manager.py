import os
import re
import json
import time
from core.config_utils import get_config_path

BULK_CONFIG_FILE = "bulk_config.json"

DEFAULT_BULK_CONFIG = {
    "clusters_per_silo": 9,
    "default_language": "Bahasa Indonesia",
    "default_tone": "Informatif, Mengalir Natural & Profesional, Solutif, Bebas Klise AI",
    "target_word_count": 2000,
    "pacing_seconds": 3
}

class BulkSiloManager:
    def __init__(self, config_file=BULK_CONFIG_FILE):
        self.config_file = get_config_path(config_file)
        self.config = self._load_config()

    def _load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cfg = DEFAULT_BULK_CONFIG.copy()
                    cfg.update(data)
                    return cfg
            except Exception:
                pass
        return DEFAULT_BULK_CONFIG.copy()

    def save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def get_config(self):
        return self.config

    def update_config(self, key, value):
        self.config[key] = value
        self.save_config()

    @staticmethod
    def parse_bulk_keywords(raw_text: str):
        """
        Memisahkan input teks menjadi daftar keyword bersih.
        Mendukung pemisah koma (,), titik koma (;), atau baris baru (\n).
        Menghapus duplikasi dengan tetap menjaga urutan awal.
        """
        if not raw_text:
            return []

        # Pisahkan berdasarkan koma, titik koma, pipa, atau newline
        tokens = re.split(r'[,;\n\|]+', raw_text)
        cleaned_list = []
        seen = set()

        for t in tokens:
            kw = t.strip()
            # Bersihkan numbering jika ada (misal: 1. keyword, 2. keyword, - keyword)
            kw = re.sub(r'^(?:\d+[\.\)\-:]|\-|\*)\s*', '', kw).strip()
            if kw and kw.lower() not in seen and kw != "0":
                seen.add(kw.lower())
                cleaned_list.append(kw)

        return cleaned_list
