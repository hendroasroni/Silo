import json
import os
from gemini_api import GeminiClient
from kie_chat_api import KieChatClient
from agnes_api import AgnesClient

PIPELINE_CONFIG_FILE = "pipeline_config.json"

STAGE_NAMES = {
    1: "Tahap 1: Riset Keyword & Content Brief",
    2: "Tahap 2: Penulisan Draf Artikel",
    3: "Tahap 3: Kurasi Kualitas & Polishing Redaksi"
}

DEFAULT_STAGE_CONFIG = {
    "stage_1": "gemini:default",
    "stage_2": "gemini:default",
    "stage_3": "gemini:default"
}

AVAILABLE_ENGINES = [
    ("gemini:default", "Gemini (Sesuai Model Utama Aktif di Pengaturan Gemini)"),
    ("gemini:gemini-3.8-flash", "Gemini 3.8 Flash (Cepat & Hemat Token)"),
    ("gemini:gemini-3.7-pro", "Gemini 3.7 Pro (Penalaran Tinggi & Akurat)"),
    ("agnes:agnes-3.0-flash", "Agnes AI 3.0 Flash (Sangat Cepat, Cerdas & Responsif) ⭐"),
    ("agnes:agnes-2.5-flash", "Agnes AI 2.5 Flash (Stabil & Terstruktur)"),
    ("agnes:agnes-2.5-pro", "Agnes AI 2.5 Pro (Penalaran Mendalam & Analisis Kompleks)"),
    ("kie:gpt-6-luna", "Kie.ai GPT-6 Luna (Sangat Cerdas, Penalaran Tinggi & Akurat)"),
]

class AIPipelineManager:
    def __init__(self, config_file=PIPELINE_CONFIG_FILE):
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # merge with default
                    for k, v in DEFAULT_STAGE_CONFIG.items():
                        if k not in data:
                            data[k] = v
                    return data
            except Exception:
                pass
        return dict(DEFAULT_STAGE_CONFIG)

    def _save_config(self):
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def get_stage_engine(self, stage_num):
        key = f"stage_{stage_num}"
        return self.config.get(key, "gemini:default")

    def set_stage_engine(self, stage_num, engine_key):
        key = f"stage_{stage_num}"
        self.config[key] = engine_key
        self._save_config()

    def get_stage_display_name(self, stage_num):
        engine_key = self.get_stage_engine(stage_num)
        for k, label in AVAILABLE_ENGINES:
            if k == engine_key:
                return label
        if engine_key.startswith("agnes:"):
            return f"Agnes AI ({engine_key[6:]})"
        elif engine_key.startswith("kie:"):
            return f"Kie.ai ({engine_key[4:]})"
        elif engine_key.startswith("gemini:"):
            return f"Gemini ({engine_key[7:]})"
        return engine_key

    def get_client_for_stage(self, stage_num, default_gemini_client=None):
        """
        Mengembalikan instance client AI (GeminiClient, AgnesClient, atau KieChatClient)
        sesuai konfigurasi untuk stage tertentu (1, 2, atau 3).
        """
        engine = self.get_stage_engine(stage_num)

        if engine.startswith("agnes:"):
            model_name = engine.split(":", 1)[1] if ":" in engine else "agnes-3.0-flash"
            return AgnesClient(model=model_name)

        elif engine.startswith("kie:"):
            model_name = engine.split(":", 1)[1] if ":" in engine else "gpt-6-luna"
            return KieChatClient(model=model_name)
        
        elif engine.startswith("gemini:"):
            target_model = engine.split(":", 1)[1] if ":" in engine else "default"
            client = default_gemini_client if default_gemini_client else GeminiClient()
            if target_model != "default":
                # Create a cloned client with specific model
                clone = GeminiClient(key_file=client.key_file)
                clone.active_model = target_model
                return clone
            return client

        # Fallback default
        return default_gemini_client if default_gemini_client else GeminiClient()

    def apply_preset(self, preset_name):
        """
        Menerapkan kombinasi preset cepat:
        - 'all_gemini': Full Gemini Flash (100% Gratis & Cepat)
        - 'all_agnes': Full Agnes AI 3.0 Flash (Cepat & Cerdas)
        - 'hybrid_agnes_curation': Tahap 1-2 Gemini + Tahap 3 Agnes 2.5 Pro
        - 'hybrid_gpt6_curation': Tahap 1-2 Gemini + Tahap 3 Kie.ai GPT-6 Luna
        - 'full_gpt6': Tahap 1-3 Semua Menggunakan Kie.ai GPT-6 Luna
        """
        if preset_name == "all_gemini":
            self.config["stage_1"] = "gemini:default"
            self.config["stage_2"] = "gemini:default"
            self.config["stage_3"] = "gemini:default"
        elif preset_name == "all_agnes":
            self.config["stage_1"] = "agnes:agnes-3.0-flash"
            self.config["stage_2"] = "agnes:agnes-3.0-flash"
            self.config["stage_3"] = "agnes:agnes-3.0-flash"
        elif preset_name == "hybrid_agnes_curation":
            self.config["stage_1"] = "gemini:default"
            self.config["stage_2"] = "gemini:default"
            self.config["stage_3"] = "agnes:agnes-2.5-pro"
        elif preset_name in ["hybrid_gpt5_curation", "hybrid_gpt6_curation"]:
            self.config["stage_1"] = "gemini:default"
            self.config["stage_2"] = "gemini:default"
            self.config["stage_3"] = "kie:gpt-6-luna"
        elif preset_name in ["hybrid_gpt5_draft_curation", "hybrid_gpt6_draft_curation"]:
            self.config["stage_1"] = "gemini:default"
            self.config["stage_2"] = "kie:gpt-6-luna"
            self.config["stage_3"] = "kie:gpt-6-luna"
        elif preset_name in ["full_gpt5", "full_gpt6"]:
            self.config["stage_1"] = "kie:gpt-6-luna"
            self.config["stage_2"] = "kie:gpt-6-luna"
            self.config["stage_3"] = "kie:gpt-6-luna"
        self._save_config()
