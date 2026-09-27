import os
import json
import webbrowser
from datetime import datetime

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

DEFAULT_CLIENT_SECRETS_FILE = "client_secret.json"
DEFAULT_TOKENS_DIR = "youtube_tokens"

class YouTubeLiveClient:
    def __init__(self, client_secrets_file=DEFAULT_CLIENT_SECRETS_FILE, tokens_dir=DEFAULT_TOKENS_DIR):
        self.client_secrets_file = client_secrets_file
        self.tokens_dir = tokens_dir
        os.makedirs(self.tokens_dir, exist_ok=True)
        self.service = None
        self.creds = None

    def is_library_installed(self):
        return GOOGLE_API_AVAILABLE

    def is_secret_file_present(self):
        return os.path.exists(self.client_secrets_file)

    def get_token_path(self, channel_id="default"):
        clean_id = str(channel_id).replace(" ", "_").replace("/", "_")
        return os.path.join(self.tokens_dir, f"token_{clean_id}.json")

    def has_saved_token(self, channel_id="default"):
        token_path = self.get_token_path(channel_id)
        return os.path.exists(token_path)

    def load_credentials(self, channel_id="default"):
        token_path = self.get_token_path(channel_id)
        if not os.path.exists(token_path):
            return None

        try:
            creds = Credentials.from_authorized_user_file(token_path, YOUTUBE_SCOPES)
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self.save_credentials(creds, channel_id)
                except Exception:
                    return None
            if creds and creds.valid:
                return creds
        except Exception:
            pass
        return None

    def save_credentials(self, creds, channel_id="default"):
        token_path = self.get_token_path(channel_id)
        try:
            with open(token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            return True
        except Exception:
            return False

    def _extract_client_credentials(self):
        if not os.path.exists(self.client_secrets_file):
            return None, None

        try:
            with open(self.client_secrets_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Bisa di bawah 'installed', 'web', 'device', atau root
            obj = data.get("installed") or data.get("web") or data.get("device") or data
            client_id = obj.get("client_id", "").strip()
            client_secret = obj.get("client_secret", "").strip()
            if client_id and client_secret:
                return client_id, client_secret
        except Exception:
            pass
        return None, None

    def authenticate(self, channel_id="default", force_new=False, on_code_display=None):
        """
        Otentikasi OAuth 2.0 menggunakan TV & Limited Input Device Flow (Headless / Device Code Flow).
        Bekerja 100% di terminal CLI / VPS tanpa butuh local redirect server.
        Pengguna cukup membuka https://www.google.com/device dan memasukkan kode di layar.
        """
        if not GOOGLE_API_AVAILABLE:
            raise RuntimeError("Library Google API belum terpasang. Jalankan: pip install google-api-python-client google-auth-oauthlib")

        if not force_new:
            existing_creds = self.load_credentials(channel_id)
            if existing_creds:
                self.creds = existing_creds
                self.service = build("youtube", "v3", credentials=self.creds)
                return True, "Otentikasi berhasil menggunakan token tersimpan."

        client_id, client_secret = self._extract_client_credentials()
        if not client_id or not client_secret:
            raise FileNotFoundError(
                f"File kredensial '{self.client_secrets_file}' tidak valid atau belum ada.\n"
                "Pastikan file tersebut berisi 'client_id' dan 'client_secret' dari Google Cloud Console."
            )

        # 1. Request Device Code dari Google OAuth
        import requests
        device_code_url = "https://oauth2.googleapis.com/device/code"
        device_payload = {
            "client_id": client_id,
            "scope": " ".join(YOUTUBE_SCOPES)
        }

        try:
            resp = requests.post(device_code_url, data=device_payload, timeout=20)
            if resp.status_code != 200:
                raise RuntimeError(f"Gagal meminta Device Code dari Google: (HTTP {resp.status_code}) {resp.text}")
            device_data = resp.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Koneksi ke endpoint OAuth Google gagal: {e}")

        device_code = device_data.get("device_code")
        user_code = device_data.get("user_code")
        verification_url = device_data.get("verification_url", "https://www.google.com/device")
        expires_in = int(device_data.get("expires_in", 1800))
        interval = int(device_data.get("interval", 5))

        if on_code_display:
            on_code_display(verification_url, user_code, expires_in)
        else:
            print("\n" + "=" * 65)
            print("📺 OTENTIKASI OAUTH YOUTUBE (TV & LIMITED DEVICE / HEADLESS)")
            print("=" * 65)
            print(f"1. Buka tautan berikut di browser Anda (HP / Laptop / PC):")
            print(f"   👉 \033[96m\033[1m{verification_url}\033[0m")
            print(f"\n2. Masukkan kode berikut:")
            print(f"   🔑 \033[92m\033[1m[ {user_code} ]\033[0m")
            print(f"\n3. Login dengan akun Google channel Anda dan klik 'Allow / Izinkan'.")
            print("=" * 65)
            print(f"\n⏳ Menunggu otorisasi dari perangkat Anda (Polling setiap {interval}s)...", end="", flush=True)

        # 2. Polling Token Endpoint
        import time
        token_url = "https://oauth2.googleapis.com/token"
        token_payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
        }

        start_time = time.time()
        creds_obj = None

        while (time.time() - start_time) < expires_in:
            time.sleep(interval)
            print(".", end="", flush=True)

            try:
                t_resp = requests.post(token_url, data=token_payload, timeout=20)
                if t_resp.status_code == 200:
                    t_data = t_resp.json()
                    access_token = t_data.get("access_token")
                    refresh_token = t_data.get("refresh_token")
                    token_expiry = t_data.get("expires_in")
                    
                    # Buat Credentials objek
                    creds_obj = Credentials(
                        token=access_token,
                        refresh_token=refresh_token,
                        token_uri=token_url,
                        client_id=client_id,
                        client_secret=client_secret,
                        scopes=YOUTUBE_SCOPES
                    )
                    break
                else:
                    err_json = {}
                    try:
                        err_json = t_resp.json()
                    except Exception:
                        pass
                    
                    err_type = err_json.get("error")
                    if err_type == "authorization_pending":
                        continue
                    elif err_type == "slow_down":
                        interval += 5
                        continue
                    elif err_type == "expired_token":
                        raise RuntimeError("\nWaktu otentikasi telah habis (expired). Silakan coba lagi.")
                    elif err_type == "access_denied":
                        raise RuntimeError("\nOtentikasi ditolak oleh pengguna di browser (access_denied).")
                    else:
                        err_desc = err_json.get("error_description", t_resp.text)
                        raise RuntimeError(f"\nError OAuth: {err_type} - {err_desc}")
            except requests.exceptions.RequestException as e:
                continue

        if not creds_obj:
            raise RuntimeError("\nWaktu otentikasi habis sebelum selesai.")

        print("\n\033[92m✔ Otentikasi Berhasil Diterima!\033[0m")
        self.creds = creds_obj
        self.save_credentials(creds_obj, channel_id)
        self.service = build("youtube", "v3", credentials=self.creds)
        return True, "Otentikasi Headless (Device Flow) YouTube berhasil diselesaikan!"

    def get_service(self, channel_id="default"):
        if not self.service:
            creds = self.load_credentials(channel_id)
            if creds:
                self.creds = creds
                self.service = build("youtube", "v3", credentials=creds)
            else:
                ok, msg = self.authenticate(channel_id=channel_id)
        return self.service

    def get_channel_profile_live(self, channel_id="default"):
        """
        Mengambil informasi lengkap channel YouTube yang sedang login.
        """
        service = self.get_service(channel_id)
        resp = service.channels().list(
            mine=True,
            part="snippet,contentDetails,statistics"
        ).execute()

        items = resp.get("items", [])
        if not items:
            raise ValueError("Tidak dapat menemukan data channel untuk akun Google yang login.")

        ch_data = items[0]
        snippet = ch_data.get("snippet", {})
        stats = ch_data.get("statistics", {})
        content_details = ch_data.get("contentDetails", {})

        uploads_id = content_details.get("relatedPlaylists", {}).get("uploads", "")

        return {
            "channel_id": ch_data.get("id"),
            "title": snippet.get("title"),
            "description": snippet.get("description"),
            "custom_url": snippet.get("customUrl", ""),
            "published_at": snippet.get("publishedAt"),
            "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "view_count": int(stats.get("viewCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
            "uploads_playlist_id": uploads_id
        }

    def list_my_videos(self, channel_id="default", max_results=20, page_token=None):
        """
        Mengambil daftar video terbaru dari channel (menggunakan Uploads playlist, hemat kuota).
        """
        service = self.get_service(channel_id)
        
        # 1. Dapatkan uploads playlist
        ch_info = self.get_channel_profile_live(channel_id)
        uploads_id = ch_info.get("uploads_playlist_id")
        if not uploads_id:
            return [], None

        # 2. Ambil playlist items
        pl_resp = service.playlistItems().list(
            playlistId=uploads_id,
            part="snippet,contentDetails",
            maxResults=min(max_results, 50),
            pageToken=page_token
        ).execute()

        pl_items = pl_resp.get("items", [])
        next_page = pl_resp.get("nextPageToken")

        if not pl_items:
            return [], next_page

        video_ids = [item.get("contentDetails", {}).get("videoId") for item in pl_items if item.get("contentDetails", {}).get("videoId")]
        if not video_ids:
            return [], next_page

        # 3. Ambil detail video lengkap (views, privacy status, tags, statistics)
        v_resp = service.videos().list(
            id=",".join(video_ids),
            part="snippet,statistics,status,contentDetails"
        ).execute()

        videos_map = {v["id"]: v for v in v_resp.get("items", [])}

        results = []
        for pl_item in pl_items:
            v_id = pl_item.get("contentDetails", {}).get("videoId")
            v_detail = videos_map.get(v_id)
            if not v_detail:
                continue

            snippet = v_detail.get("snippet", {})
            stats = v_detail.get("statistics", {})
            status = v_detail.get("status", {})

            thumbs = snippet.get("thumbnails", {})
            best_thumb = (
                thumbs.get("maxres", {}).get("url") or
                thumbs.get("standard", {}).get("url") or
                thumbs.get("high", {}).get("url") or
                thumbs.get("medium", {}).get("url") or
                thumbs.get("default", {}).get("url") or ""
            )

            results.append({
                "video_id": v_id,
                "title": snippet.get("title"),
                "description": snippet.get("description"),
                "published_at": snippet.get("publishedAt"),
                "tags": snippet.get("tags", []),
                "category_id": snippet.get("categoryId"),
                "privacy_status": status.get("privacyStatus", "public"),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "thumbnail_url": best_thumb,
                "video_url": f"https://www.youtube.com/watch?v={v_id}"
            })

        return results, next_page

    def get_video_details(self, video_id, channel_id="default"):
        """
        Mengambil detail satu video secara lengkap.
        """
        service = self.get_service(channel_id)
        resp = service.videos().list(
            id=video_id,
            part="snippet,statistics,status,contentDetails"
        ).execute()

        items = resp.get("items", [])
        if not items:
            return None

        v = items[0]
        snippet = v.get("snippet", {})
        stats = v.get("statistics", {})
        status = v.get("status", {})

        thumbs = snippet.get("thumbnails", {})
        best_thumb = (
            thumbs.get("maxres", {}).get("url") or
            thumbs.get("standard", {}).get("url") or
            thumbs.get("high", {}).get("url") or
            thumbs.get("default", {}).get("url") or ""
        )

        return {
            "video_id": video_id,
            "title": snippet.get("title"),
            "description": snippet.get("description"),
            "published_at": snippet.get("publishedAt"),
            "tags": snippet.get("tags", []),
            "category_id": snippet.get("categoryId"),
            "privacy_status": status.get("privacyStatus", "public"),
            "view_count": int(stats.get("viewCount", 0)),
            "like_count": int(stats.get("likeCount", 0)),
            "comment_count": int(stats.get("commentCount", 0)),
            "thumbnail_url": best_thumb,
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
            "raw_snippet": snippet
        }

    def update_video_metadata(self, video_id, title=None, description=None, tags=None, category_id=None, channel_id="default"):
        """
        Memperbarui metadata video (Judul, Deskripsi, Tags, Kategori) langsung ke server YouTube secara live.
        """
        service = self.get_service(channel_id)

        # 1. Ambil snippet yang ada saat ini agar field wajib (categoryId, defaultLanguage) tidak hilang
        resp = service.videos().list(
            id=video_id,
            part="snippet,status"
        ).execute()

        items = resp.get("items", [])
        if not items:
            return False, f"Video #{video_id} tidak ditemukan di channel ini."

        current_item = items[0]
        snippet = current_item.get("snippet", {})

        # 2. Update field yang diberikan
        if title:
            snippet["title"] = title.strip()[:100]  # YouTube limit 100 chars
        if description is not None:
            snippet["description"] = description.strip()[:5000]  # YouTube limit 5000 chars
        if tags is not None:
            if isinstance(tags, str):
                parsed_tags = [t.strip() for t in tags.split(",") if t.strip()]
            else:
                parsed_tags = [str(t).strip() for t in tags if str(t).strip()]
            snippet["tags"] = parsed_tags
        if category_id:
            snippet["categoryId"] = str(category_id)

        # 3. Kirim update ke YouTube API
        try:
            update_resp = service.videos().update(
                part="snippet",
                body={
                    "id": video_id,
                    "snippet": snippet
                }
            ).execute()
            return True, update_resp
        except Exception as e:
            return False, str(e)

    def update_video_thumbnail(self, video_id, image_path, channel_id="default"):
        """
        Mengunggah thumbnail baru langsung ke video YouTube secara live.
        """
        if not os.path.exists(image_path):
            return False, f"File gambar thumbnail '{image_path}' tidak ditemukan."

        service = self.get_service(channel_id)

        # Convert webp to PNG/JPEG if required by YouTube API upload
        upload_path = image_path
        temp_converted = None

        if image_path.lower().endswith(".webp"):
            try:
                from PIL import Image
                im = Image.open(image_path)
                temp_converted = os.path.splitext(image_path)[0] + "_yt_upload.jpg"
                if im.mode in ("RGBA", "LA", "P"):
                    im = im.convert("RGB")
                im.save(temp_converted, "JPEG", quality=95)
                upload_path = temp_converted
            except Exception:
                pass

        try:
            media = MediaFileUpload(
                upload_path,
                mimetype="image/jpeg" if upload_path.lower().endswith((".jpg", ".jpeg")) else "image/png",
                resumable=True
            )
            thumb_resp = service.thumbnails().set(
                videoId=video_id,
                media_body=media
            ).execute()

            if temp_converted and os.path.exists(temp_converted):
                try:
                    os.remove(temp_converted)
                except Exception:
                    pass

            return True, thumb_resp
        except Exception as e:
            if temp_converted and os.path.exists(temp_converted):
                try:
                    os.remove(temp_converted)
                except Exception:
                    pass
            return False, f"Gagal upload thumbnail: {str(e)}"

    def disconnect_channel(self, channel_id="default"):
        token_path = self.get_token_path(channel_id)
        if os.path.exists(token_path):
            try:
                os.remove(token_path)
                return True, "Koneksi OAuth channel berhasil diputuskan."
            except Exception as e:
                return False, f"Gagal menghapus token: {e}"
        return True, "Channel belum terhubung."
