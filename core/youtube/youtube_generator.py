import os
import json
import re
from datetime import datetime
from core.config_utils import get_config_path, CHANNELS_DIR, LEGACY_YOUTUBE_OUTPUT_DIR

CHANNELS_BASE_DIR = CHANNELS_DIR
YOUTUBE_CONFIG_FILE = "youtube_channels.json"
YOUTUBE_OUTPUT_DIR = LEGACY_YOUTUBE_OUTPUT_DIR

def clean_channel_slug(channel_name, channel_id=""):
    """
    Menghasilkan nama folder yang aman dan bersih untuk channel di filesystem.
    """
    clean_name = re.sub(r'[^\w\-_\. ]', '_', str(channel_name)).strip().replace(' ', '_')
    if not clean_name or clean_name in ["_", "default"]:
        clean_name = f"channel_{channel_id}" if channel_id else "default_channel"
    return clean_name

def get_channel_dir(channel_profile_or_name_or_id):
    """
    Mengembalikan path folder fisik terisolasi untuk channel dan memastikan
    seluruh subfolder esensial (videos, thumbnails, metadata_packs) tersedia.
    """
    if isinstance(channel_profile_or_name_or_id, dict):
        name = channel_profile_or_name_or_id.get("name", "")
        cid = channel_profile_or_name_or_id.get("id", "")
        slug = clean_channel_slug(name, cid)
    else:
        slug = clean_channel_slug(str(channel_profile_or_name_or_id))
    
    path = os.path.join(CHANNELS_BASE_DIR, slug)
    os.makedirs(path, exist_ok=True)
    os.makedirs(os.path.join(path, "videos"), exist_ok=True)
    os.makedirs(os.path.join(path, "thumbnails"), exist_ok=True)
    os.makedirs(os.path.join(path, "metadata_packs"), exist_ok=True)
    return path

DEFAULT_CHANNEL_PROFILE = {
    "id": "default_ch",
    "name": "My YouTube Channel",
    "niche": "Edukasi & Bisnis",
    "target_audience": "Praktisi, Profesional, dan Pemula yang mencari solusi praktis",
    "tone_of_voice": "Informatif, Praktis, Profesional & Lugas",
    "branding_tagline": "Wawasan Praktis & Solusi Nyata",
    "default_links_cta": "🌐 Website: https://example.com\n📲 Konsultasi / Kontak: https://wa.me/628123456789\n📌 Jangan lupa Like, Subscribe & Nyalakan Lonceng Notifikasi!",
    "channel_keywords": "edukasi, bisnis, panduan praktis, tutorial indonesia",
    "is_default": True
}

class YouTubeProfileManager:
    def __init__(self, config_file=YOUTUBE_CONFIG_FILE):
        self.config_file = get_config_path(config_file)
        self.profiles = self._load_profiles()
        self._sync_physical_folders()

    def _load_profiles(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and data:
                        return data
                    elif isinstance(data, dict):
                        return [data]
            except Exception:
                pass
        # Default starter profile
        default_data = [dict(DEFAULT_CHANNEL_PROFILE)]
        self._save_profiles(default_data)
        return default_data

    def _sync_physical_folders(self):
        """
        Memastikan setiap channel memiliki folder fisik tersendiri di `channels_youtube/<nama_channel>/`
        lengkap dengan `profile.json`, `videos/`, `thumbnails/`, `metadata_packs/`, dan token terduplikasi.
        """
        for p in self.profiles:
            try:
                ch_dir = get_channel_dir(p)
                p_file = os.path.join(ch_dir, "profile.json")
                with open(p_file, "w", encoding="utf-8") as f:
                    json.dump(p, f, ensure_ascii=False, indent=2)

                # Sync token dari youtube_tokens jika ada
                p_id = p.get("id")
                if p_id:
                    global_token = os.path.join("youtube_tokens", f"token_{p_id}.json")
                    local_token = os.path.join(ch_dir, "token.json")
                    if os.path.exists(global_token) and not os.path.exists(local_token):
                        try:
                            import shutil
                            shutil.copy2(global_token, local_token)
                        except Exception:
                            pass
            except Exception:
                pass

    def _save_profiles(self, profiles_list=None):
        data = profiles_list if profiles_list is not None else self.profiles
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._sync_physical_folders()
        except Exception:
            pass

    def get_profiles(self):
        return self.profiles

    def get_profile_by_id(self, channel_id):
        for p in self.profiles:
            if p.get("id") == channel_id:
                return p
        return None

    def get_active_profile(self):
        for p in self.profiles:
            if p.get("is_default", False):
                return p
        if self.profiles:
            return self.profiles[0]
        return DEFAULT_CHANNEL_PROFILE

    def set_active_profile(self, channel_id):
        found = False
        for p in self.profiles:
            if p.get("id") == channel_id:
                p["is_default"] = True
                found = True
            else:
                p["is_default"] = False
        if found:
            self._save_profiles()
        return found

    def add_profile(self, profile_dict):
        p_id = profile_dict.get("id") or f"ch_{int(datetime.now().timestamp())}"
        profile_dict["id"] = p_id
        
        # If set as default or first profile
        if profile_dict.get("is_default") or len(self.profiles) == 0:
            for p in self.profiles:
                p["is_default"] = False
            profile_dict["is_default"] = True
            
        self.profiles.append(profile_dict)
        self._save_profiles()
        return profile_dict

    def update_profile(self, channel_id, updated_fields):
        for p in self.profiles:
            if p.get("id") == channel_id:
                p.update(updated_fields)
                self._save_profiles()
                return p
        return None

    def delete_profile(self, channel_id):
        if len(self.profiles) <= 1:
            return False, "Tidak dapat menghapus profile terakhir. Minimal harus ada 1 profile channel."
        
        target = None
        for p in self.profiles:
            if p.get("id") == channel_id:
                target = p
                break
        
        if not target:
            return False, "Profile tidak ditemukan."
            
        was_default = target.get("is_default", False)
        self.profiles = [p for p in self.profiles if p.get("id") != channel_id]
        if was_default and self.profiles:
            self.profiles[0]["is_default"] = True
            
        self._save_profiles()
        return True, "Profile berhasil dihapus."


class YouTubeGenerator:
    def __init__(self, ai_client=None):
        self.client = ai_client
        self.profile_mgr = YouTubeProfileManager()

    def set_ai_client(self, client):
        self.client = client

    def generate_new_video_metadata(self, video_topic, key_points="", focus_keyword="", channel_profile=None):
        """
        Menghasilkan metadata lengkap untuk video baru berdasarkan konsep/topik video
        dan identitas channel.
        """
        if not self.client:
            raise ValueError("AI Client belum diatur.")

        profile = channel_profile or self.profile_mgr.get_active_profile()

        system_instruction = f"""
Anda adalah YouTube SEO Strategist & Algorithm Optimization Expert kelas dunia.
Tugas Anda: Merancang paket metadata video YouTube yang memiliki CTR tinggi, durasi tonton optimal (retensi tinggi), dan mudah ditemukan di YouTube Search & Rekomendasi (Browse Features).

IDENTITAS CHANNEL:
- Nama Channel: {profile.get('name')}
- Niche/Topik: {profile.get('niche')}
- Target Penonton: {profile.get('target_audience')}
- Tone & Gaya Bahasa: {profile.get('tone_of_voice')}
- Tagline Branding: {profile.get('branding_tagline')}
- Standard CTA & Links: {profile.get('default_links_cta')}

ATURAN METADATA YOUTUBE:
1. JUDUL VIDEO (5 Pilihan Variasi):
   - Maksimal 60-70 karakter agar tidak terpotong di smartphone.
   - Pilihan 1: High CTR & Curiosity Hook (Memicu rasa ingin tahu tanpa clickbait palsu).
   - Pilihan 2: Search Intent / SEO Focus (Target pencarian kata kunci).
   - Pilihan 3: How-To / Solutif Praktis (Panduan langkah demi langkah).
   - Pilihan 4: Angka / Listicle / Studi Kasus.
   - Pilihan 5: Singkat, Tajam & Kuat (Punchy).

2. BRIEF & DESKRIPSI VIDEO:
   - 2 Baris Pertama (Above The Fold / Hook): Sangat krusial! Buat kalimat pengait yang kuat sebelum tombol "...more" / "...selengkapnya".
   - Ringkasan Isi Video (2-3 paragraf mengalir dan natural).
   - Timestamps / Chapter Template perkiraan (misal: 00:00 Intro, 01:20 Masalah, 03:45 Solusi, dst).
   - Key Takeaways (Poin kunci apa yang didapat penonton).
   - Call to Action & Link Standar Channel.
   - Hashtags (3-5 buah di akhir deskripsi).

3. TAGS VIDEO:
   - Kumpulan tag relevan dipisahkan tanda koma.
   - Total panjang karakter gabungan harus DI BAWAH 500 KARAKTER (limit YouTube Studio).

4. REKOMENDASI THUMBNAIL:
   - Konsep visual Thumbnail yang mencolok & berorientasi klik.
   - Teks Thumbnail (Overlay Text): Maksimal 3-4 KATA SAJA, kontras, dan TIDAK MENGULANG kata demi kata dari judul.
   - Prompt Gambar AI (dalam bahasa Inggris): Prompt berkualitas tinggi untuk di-generate menggunakan generator gambar AI.

5. PINNED COMMENT:
   - Komentar pertama dari pembuat video untuk memancing diskusi & interaksi penonton di kolom komentar.
"""

        user_prompt = f"""
Rancang paket metadata YouTube untuk video berikut:
- Topik / Konsep Video: {video_topic}
- Poin Pembahasan Kunci: {key_points if key_points else video_topic}
- Target Keyword Fokus: {focus_keyword if focus_keyword else video_topic}

KEMBALIKAN DALAM FORMAT JSON VALID BERIKUT:
{{
  "topic": "{video_topic}",
  "channel_name": "{profile.get('name')}",
  "titles": [
    {{"type": "High CTR / Hook", "title": "Judul 1..."}},
    {{"type": "SEO Search Intent", "title": "Judul 2..."}},
    {{"type": "How-To / Panduan", "title": "Judul 3..."}},
    {{"type": "Listicle / Angka", "title": "Judul 4..."}},
    {{"type": "Singkat & Punchy", "title": "Judul 5..."}}
  ],
  "recommended_primary_title": "Pilihan judul nomor 1 atau yang paling direkomendasikan",
  "description": {{
    "above_the_fold_hook": "2 baris pertama yang memikat sebelum tombol more",
    "video_summary": "Ringkasan isi video 2-3 paragraf",
    "timestamps": [
      {{"time": "00:00", "label": "Pembuka / Hook"}},
      {{"time": "01:15", "label": "Poin 1..."}},
      {{"time": "03:30", "label": "Poin 2..."}},
      {{"time": "06:00", "label": "Kesimpulan & Solusi"}}
    ],
    "key_takeaways": [
      "Poin penting 1",
      "Poin penting 2",
      "Poin penting 3"
    ],
    "full_formatted_description": "Teks lengkap deskripsi siap copy-paste termasuk hook, summary, timestamps, takeaways, link standar channel, dan hashtags"
  }},
  "tags_comma_separated": "tag1, tag2, tag3, tag4, tag5...",
  "hashtags": ["#Tag1", "#Tag2", "#Tag3", "#Tag4"],
  "thumbnail_recommendations": [
    {{
      "concept_name": "Konsep 1 (Fokus Ekspresi & Kontras)",
      "overlay_text": "3-4 KATA MAKSIMAL",
      "visual_description": "Deskripsi visual komposisi gambar",
      "ai_image_prompt_en": "English AI image generation prompt for thumbnail visual, high contrast, vibrant, 8k..."
    }},
    {{
      "concept_name": "Konsep 2 (Fokus Objek / Sebelum-Sesudah)",
      "overlay_text": "3-4 KATA MAKSIMAL",
      "visual_description": "Deskripsi visual komposisi gambar",
      "ai_image_prompt_en": "English AI image generation prompt..."
    }}
  ],
  "pinned_comment": "Pertanyaan pancingan komentar pembuat video untuk mendongkrak algoritma engagement..."
}}
"""
        return self.client.generate_json(user_prompt, system_instruction=system_instruction, temperature=0.7)

    def optimize_existing_video(self, old_title, old_description="", current_issue="", channel_profile=None):
        """
        Menganalisis dan memperbarui (regenerate) video yang sudah publish agar CTR
        dan jangkauan penontonnya naik kembali.
        """
        if not self.client:
            raise ValueError("AI Client belum diatur.")

        profile = channel_profile or self.profile_mgr.get_active_profile()

        system_instruction = f"""
Anda adalah YouTube Video Optimization & CTR Recovery Consultant.
Tugas Anda: Membedah judul, deskripsi, dan metadata video YouTube yang SUDAH PUBLISH, lalu meregenerasi variasi judul baru, deskripsi baru, tags baru, dan konsep thumbnail baru yang jauh lebih kuat untuk mendongkrak traffic video lama tersebut.

IDENTITAS CHANNEL:
- Nama Channel: {profile.get('name')}
- Niche/Topik: {profile.get('niche')}
- Target Penonton: {profile.get('target_audience')}
- Tone & Gaya Bahasa: {profile.get('tone_of_voice')}
- Standard CTA & Links: {profile.get('default_links_cta')}
"""

        user_prompt = f"""
Lakukan optimasi & regenerasi metadata untuk video YouTube yang sudah publish berikut:
- Judul Lama Saat Ini: {old_title}
- Deskripsi Lama (jika ada): {old_description if old_description else '(Tidak disertakan)'}
- Masalah / Keluhan Utama: {current_issue if current_issue else 'CTR rendah dan view mulai melandai, butuh judul & thumbnail yang lebih menarik'}

KEMBALIKAN DALAM FORMAT JSON VALID BERIKUT:
{{
  "analysis": {{
    "old_title_weakness": "Analisis ringkas kenapa judul lama kurang maksimal",
    "improvement_strategy": "Strategi perbaikan untuk menaikkan CTR & penonton baru"
  }},
  "new_titles": [
    {{"type": "High CTR / Refresh Hook", "title": "Judul baru 1..."}},
    {{"type": "SEO Search Intent", "title": "Judul baru 2..."}},
    {{"type": "Curiosity / Pemicu Penasaran", "title": "Judul baru 3..."}},
    {{"type": "Problem-Solving", "title": "Judul baru 4..."}},
    {{"type": "Short & Impactful", "title": "Judul baru 5..."}}
  ],
  "recommended_new_title": "Judul terbaik yang direkomendasikan",
  "new_description": {{
    "above_the_fold_hook": "2 baris pertama baru yang memikat",
    "full_formatted_description": "Teks lengkap deskripsi baru yang sudah diperbaiki"
  }},
  "new_tags_comma_separated": "tag_baru1, tag_baru2, tag_baru3...",
  "new_hashtags": ["#Hashtag1", "#Hashtag2", "#Hashtag3"],
  "new_thumbnail_recommendations": [
    {{
      "concept_name": "Konsep Thumbnail Re-design 1",
      "overlay_text": "3-4 KATA MAKSIMAL",
      "visual_description": "Deskripsi visual thumbnail baru",
      "ai_image_prompt_en": "English AI image generation prompt for new thumbnail visual..."
    }},
    {{
      "concept_name": "Konsep Thumbnail Re-design 2",
      "overlay_text": "3-4 KATA MAKSIMAL",
      "visual_description": "Deskripsi visual alternatif",
      "ai_image_prompt_en": "English AI image generation prompt..."
    }}
  ],
  "action_advice": "Saran langkah terbaik saat mengganti judul & thumbnail video lama agar tidak kaget di algoritma."
}}
"""
        return self.client.generate_json(user_prompt, system_instruction=system_instruction, temperature=0.7)

    def optimize_channel_profile(self, channel_name, niche, target_audience, core_topics=""):
        """
        Menghasilkan teks About Channel dan kumpulan Channel Keywords untuk YouTube Studio.
        """
        if not self.client:
            raise ValueError("AI Client belum diatur.")

        system_instruction = """
Anda adalah YouTube Branding & Channel Positioning Strategist.
Tugas Anda: Membuat copywriting halaman 'About' (Tentang Channel) YouTube yang memikat penonton untuk menekan tombol Subscribe, serta menyusun kata kunci channel (Channel Keywords) berbobot SEO tinggi untuk pengaturan YouTube Studio.
"""

        user_prompt = f"""
Rancang profil optimasi channel YouTube:
- Nama Channel: {channel_name}
- Niche / Industri: {niche}
- Target Penonton: {target_audience}
- Topik Utama Pembahasan: {core_topics if core_topics else niche}

KEMBALIKAN DALAM FORMAT JSON VALID BERIKUT:
{{
  "channel_name": "{channel_name}",
  "about_bio_long": "Copywriting halaman About lengkap (2-3 paragraf yang memperkenalkan siapa channel ini, apa manfaat yang didapat subscriber, jadwal upload, dan CTA subscribe)",
  "about_bio_short": "Versi ringkas (1 paragraf padat untuk deskripsi singkat / bio sosial)",
  "tagline_options": [
    "Tagline opsi 1",
    "Tagline opsi 2",
    "Tagline opsi 3"
  ],
  "channel_keywords_comma_separated": "keyword1, keyword2, keyword3, keyword4, keyword5... (sekitar 300-450 karakter untuk Channel Keywords di YouTube Studio)",
  "suggested_playlists": [
    {{"playlist_name": "Nama Playlist 1", "description": "Deskripsi singkat playlist"}},
    {{"playlist_name": "Nama Playlist 2", "description": "Deskripsi singkat playlist"}},
    {{"playlist_name": "Nama Playlist 3", "description": "Deskripsi singkat playlist"}}
  ]
}}
"""
        return self.client.generate_json(user_prompt, system_instruction=system_instruction, temperature=0.6)

    def generate_channel_bio_optimization(self, channel_profile=None, channel_name=None, niche=None, target_audience=None, additional_goals=""):
        """
        Wrapper fleksibel yang menerima dictionary channel_profile ataupun individual parameters.
        """
        if channel_profile and isinstance(channel_profile, dict):
            c_name = channel_profile.get("name", "My Channel")
            c_niche = channel_profile.get("niche", "Edukasi")
            c_aud = channel_profile.get("target_audience", "Umum")
            c_topics = f"{c_niche}. {additional_goals}" if additional_goals else c_niche
        else:
            c_name = channel_name or "My Channel"
            c_niche = niche or "Edukasi"
            c_aud = target_audience or "Umum"
            c_topics = additional_goals or c_niche

        res = self.optimize_channel_profile(c_name, c_niche, c_aud, c_topics)
        # Normalisasi key agar kompatibel dengan berbagai pemanggil
        if isinstance(res, dict):
            if "long_bio" not in res and "about_bio_long" in res:
                res["long_bio"] = res["about_bio_long"]
            if "tagline" not in res and "tagline_options" in res and res["tagline_options"]:
                res["tagline"] = res["tagline_options"][0]
        return res


    def save_video_pack(self, data, channel_name, video_identifier):
        """
        Menyimpan hasil generate ke file teks & JSON di folder fisik channel `channels_youtube/<channel_slug>/metadata_packs/`.
        """
        ch_dir = get_channel_dir(channel_name)
        meta_dir = os.path.join(ch_dir, "metadata_packs")
        os.makedirs(meta_dir, exist_ok=True)

        clean_slug = re.sub(r'[^a-zA-Z0-9_-]', '_', video_identifier).strip('_')[:50]
        if not clean_slug:
            clean_slug = f"video_{int(datetime.now().timestamp())}"

        filename_base = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{clean_slug}"
        txt_path = os.path.join(meta_dir, f"{filename_base}.txt")
        json_path = os.path.join(meta_dir, f"{filename_base}.json")

        # Also mirror to output_youtube for legacy paths
        legacy_dir = os.path.join(YOUTUBE_OUTPUT_DIR, clean_channel_slug(channel_name))
        os.makedirs(legacy_dir, exist_ok=True)
        legacy_txt = os.path.join(legacy_dir, f"{filename_base}.txt")
        legacy_json = os.path.join(legacy_dir, f"{filename_base}.json")

        # Save JSON
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            with open(legacy_json, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        # Format Human-Readable TXT
        lines = []
        lines.append("=" * 70)
        lines.append(f"🎬 YOUTUBE METADATA PACK - {channel_name.upper()}")
        lines.append(f"📅 Tanggal Dibuat: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        lines.append("")

        # Titles
        lines.append("📌 PILIHAN JUDUL VIDEO:")
        titles_list = data.get("titles") or data.get("new_titles") or []
        for idx, t in enumerate(titles_list, 1):
            t_type = t.get("type", f"Variasi #{idx}")
            t_text = t.get("title", "")
            lines.append(f"  {idx}. [{t_type}]")
            lines.append(f"     ➔ {t_text}")
        
        rec_title = data.get("recommended_primary_title") or data.get("recommended_new_title")
        if rec_title:
            lines.append(f"\n  ⭐ REKOMENDASI UTAMA: {rec_title}")
        lines.append("\n" + "-" * 70)

        # Description
        desc_obj = data.get("description") or data.get("new_description") or {}
        full_desc = desc_obj.get("full_formatted_description", "")
        hook = desc_obj.get("above_the_fold_hook", "")

        lines.append("📝 DESKRIPSI VIDEO (SIAP SALIN KE YOUTUBE STUDIO):")
        if hook:
            lines.append(f"[Hook 2 Baris Pertama]:\n{hook}\n")
        lines.append("[Teks Lengkap Deskripsi]:")
        lines.append(full_desc if full_desc else str(desc_obj))
        lines.append("\n" + "-" * 70)

        # Tags
        tags_str = data.get("tags_comma_separated") or data.get("new_tags_comma_separated") or ""
        lines.append("🏷️  TAGS VIDEO (< 500 Karakter):")
        lines.append(tags_str)
        lines.append("\n" + "-" * 70)

        # Hashtags
        hashtags = data.get("hashtags") or data.get("new_hashtags") or []
        lines.append("🔖 HASHTAGS:")
        lines.append(" ".join(hashtags))
        lines.append("\n" + "-" * 70)

        # Thumbnails
        thumbs = data.get("thumbnail_recommendations") or data.get("new_thumbnail_recommendations") or []
        lines.append("🖼️  REKOMENDASI THUMBNAIL & PROMPT GAMBAR AI:")
        for idx, th in enumerate(thumbs, 1):
            lines.append(f"\n  Konsep #{idx}: {th.get('concept_name', '-')}")
            lines.append(f"  • Tulisan Thumbnail (Overlay Text) : \"{th.get('overlay_text', '-')}\"")
            lines.append(f"  • Komposisi Visual                 : {th.get('visual_description', '-')}")
            lines.append(f"  • AI Image Prompt (English)         : {th.get('ai_image_prompt_en', '-')}")
        lines.append("\n" + "-" * 70)

        # Pinned Comment / Action Advice
        if "pinned_comment" in data:
            lines.append("💬 PINNED COMMENT (KOMENTAR SEMATAN):")
            lines.append(data["pinned_comment"])
            lines.append("\n" + "-" * 70)
        elif "action_advice" in data:
            lines.append("💡 SARAN STRATEGI UPDATE:")
            lines.append(data["action_advice"])
            lines.append("\n" + "-" * 70)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return txt_path, json_path
