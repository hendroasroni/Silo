import os
import sys
import json
import time
import base64
import urllib.parse
import webbrowser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from core.ai.kie_image_api import clean_text_for_rendering, IMAGE_STYLE_MAP

try:
    from PIL import Image
    import io
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

FLOW_BRIDGE_PORT = 7860

# ==========================================
# 1. FLOW PROMPT GENERATOR
# ==========================================
def generate_flow_prompt(keyword, article_title, niche="", style="photo", brand=""):
    """
    Menghasilkan prompt gambar berkualitas tinggi yang dioptimasi
    khusus untuk karakteristik model Imagen 3 / Google Flow.
    """
    clean_kw = clean_text_for_rendering(keyword)
    clean_title = clean_text_for_rendering(article_title)
    
    style_info = IMAGE_STYLE_MAP.get(style, {})
    suffix = style_info.get("suffix", "modern photography, cinematic natural lighting, 8k resolution, minimalist editorial aesthetic, no text, no letters, no words, no watermark")
    
    if style == "photo":
        base_prompt = f"Professional commercial editorial photography illustrating {clean_kw} in the context of {clean_title}"
        if niche:
            base_prompt += f", {niche} industry theme"
        prompt = f"{base_prompt}, clean subject focus, natural soft cinematic lighting, elegant composition, 8k high resolution, hyperrealistic, shallow depth of field, award-winning editorial visual, no text, no watermark, no logo"
    elif style == "illustration":
        prompt = f"Modern minimalist vector art illustration of {clean_kw} for {clean_title}, vibrant harmonious color palette, clean sleek geometric lines, elegant digital artwork, Behance trending vector art, high resolution, no text, no watermark"
    elif style == "isometric_3d":
        prompt = f"Clean modern 3D isometric studio render representing {clean_kw}, themed for {clean_title}, smooth claymorphism textures, soft studio ambient occlusion, pastel accents, premium 3D design, 8k render, no text, no watermark"
    elif style == "line_art":
        prompt = f"Minimalist elegant line art editorial illustration of {clean_kw} - {clean_title}, refined duotone pastel aesthetics, sophisticated magazine outline art, sleek composition, no text, no watermark"
    elif style == "cyberpunk_tech":
        prompt = f"Futuristic high-tech visual of {clean_kw}, glowing subtle neon accents, sleek digital cyber aesthetic, holographic UI atmosphere, cinematic dark backdrop, 8k resolution, no text, no watermark"
    else:
        prompt = f"High-quality editorial visual representation of {clean_kw} for {clean_title}, professional aesthetic composition, {suffix}"

    return prompt

# ==========================================
# 2. FLOW TASK MODEL & QUEUE
# ==========================================
class FlowTask:
    def __init__(self, task_id, keyword, title, prompt, target_path, md_path=None, site_name="", silo_name=""):
        self.task_id = task_id
        self.keyword = keyword
        self.title = title
        self.prompt = prompt
        self.target_path = target_path
        self.md_path = md_path
        self.site_name = site_name
        self.silo_name = silo_name
        self.status = "pending"  # pending, completed, skipped
        self.saved_path = None
        self.completed_at = None

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "keyword": self.keyword,
            "title": self.title,
            "prompt": self.prompt,
            "target_path": self.target_path,
            "md_path": self.md_path,
            "site_name": self.site_name,
            "silo_name": self.silo_name,
            "status": self.status,
            "saved_path": self.saved_path,
            "completed_at": self.completed_at
        }


class FlowQueueManager:
    def __init__(self, tasks=None):
        self.tasks = tasks or []
        self.current_idx = 0
        self.lock = threading.Lock()

    def add_task(self, task):
        with self.lock:
            self.tasks.append(task)

    def get_current_task(self):
        with self.lock:
            if not self.tasks:
                return None
            # Cari task pertama yang pending dimulai dari current_idx
            for i in range(len(self.tasks)):
                idx = (self.current_idx + i) % len(self.tasks)
                if self.tasks[idx].status == "pending":
                    self.current_idx = idx
                    return self.tasks[idx]
            # Jika semua sudah selesai/skip, kembalikan task di current_idx
            if 0 <= self.current_idx < len(self.tasks):
                return self.tasks[self.current_idx]
            return None

    def get_task_by_id(self, task_id):
        with self.lock:
            for t in self.tasks:
                if t.task_id == task_id:
                    return t
            return None

    def mark_completed(self, task_id, saved_path):
        with self.lock:
            for i, t in enumerate(self.tasks):
                if t.task_id == task_id:
                    t.status = "completed"
                    t.saved_path = saved_path
                    t.completed_at = time.strftime("%Y-%m-%d %H:%M:%S")
                    # Geser current_idx ke task pending berikutnya
                    for next_i in range(len(self.tasks)):
                        next_idx = (i + 1 + next_i) % len(self.tasks)
                        if self.tasks[next_idx].status == "pending":
                            self.current_idx = next_idx
                            return t
                    return t
            return None

    def skip_current(self):
        with self.lock:
            if not self.tasks:
                return None
            cur = self.tasks[self.current_idx]
            cur.status = "skipped"
            # Geser ke pending berikutnya
            for next_i in range(len(self.tasks)):
                next_idx = (self.current_idx + 1 + next_i) % len(self.tasks)
                if self.tasks[next_idx].status == "pending":
                    self.current_idx = next_idx
                    return self.tasks[self.current_idx]
            return cur

    def prev_task(self):
        with self.lock:
            if not self.tasks:
                return None
            self.current_idx = (self.current_idx - 1) % len(self.tasks)
            return self.tasks[self.current_idx]

    def next_task(self):
        with self.lock:
            if not self.tasks:
                return None
            self.current_idx = (self.current_idx + 1) % len(self.tasks)
            return self.tasks[self.current_idx]

    def get_stats(self):
        with self.lock:
            total = len(self.tasks)
            completed = sum(1 for t in self.tasks if t.status == "completed")
            pending = sum(1 for t in self.tasks if t.status == "pending")
            skipped = sum(1 for t in self.tasks if t.status == "skipped")
            return {
                "total": total,
                "completed": completed,
                "pending": pending,
                "skipped": skipped,
                "current_index": self.current_idx + 1 if total > 0 else 0
            }


# ==========================================
# 3. HTTP REQUEST HANDLER FOR EXTENSION
# ==========================================
class FlowBridgeHTTPHandler(BaseHTTPRequestHandler):
    queue_manager = None
    on_upload_callback = None

    def log_message(self, format, *args):
        # Mute default HTTP access logs to keep terminal clean
        return

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Requested-With, Authorization")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/status":
            stats = self.queue_manager.get_stats() if self.queue_manager else {}
            cur = self.queue_manager.get_current_task() if self.queue_manager else None
            data = {
                "online": True,
                "server": "Google Flow Silo Bridge",
                "version": "1.0",
                "stats": stats,
                "current_task": cur.to_dict() if cur else None
            }
            self._send_json(200, data)

        elif path == "/api/current":
            cur = self.queue_manager.get_current_task() if self.queue_manager else None
            stats = self.queue_manager.get_stats() if self.queue_manager else {}
            if cur:
                data = {
                    "has_task": True,
                    "task": cur.to_dict(),
                    "stats": stats
                }
            else:
                data = {
                    "has_task": False,
                    "task": None,
                    "stats": stats,
                    "message": "Semua task sudah selesai!"
                }
            self._send_json(200, data)

        elif path == "/api/tasks":
            tasks = [t.to_dict() for t in self.queue_manager.tasks] if self.queue_manager else []
            self._send_json(200, {"tasks": tasks, "stats": self.queue_manager.get_stats() if self.queue_manager else {}})

        else:
            self._send_json(404, {"error": "Endpoint tidak ditemukan"})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        if path == "/api/upload":
            try:
                # Handle JSON payload (base64 image or direct URL/data)
                content_type = self.headers.get('Content-Type', '')
                image_bytes = None
                task_id = None

                if 'application/json' in content_type:
                    payload = json.loads(body.decode('utf-8'))
                    task_id = payload.get("task_id")
                    b64_data = payload.get("image_base64", "")
                    
                    if "," in b64_data:
                        b64_data = b64_data.split(",", 1)[1]
                    image_bytes = base64.b64decode(b64_data)
                
                elif 'image/' in content_type:
                    # Raw image binary
                    image_bytes = body
                    # Task ID dari query string jika ada
                    qs = urllib.parse.parse_qs(parsed.query)
                    task_id = qs.get("task_id", [None])[0]

                if not image_bytes:
                    self._send_json(400, {"success": False, "error": "Data gambar tidak ditemukan."})
                    return

                # Dapatkan task terkait
                task = None
                if task_id:
                    task = self.queue_manager.get_task_by_id(task_id)
                if not task:
                    task = self.queue_manager.get_current_task()

                if not task:
                    self._send_json(404, {"success": False, "error": "Tidak ada antrean task aktif."})
                    return

                # Simpan gambar ke file tujuan
                saved_filepath = self._save_image_file(image_bytes, task.target_path)
                
                # Update markdown frontmatter jika artikel ada
                if task.md_path and os.path.exists(task.md_path):
                    self._update_markdown_frontmatter(task.md_path, saved_filepath)

                # Update status antrean
                self.queue_manager.mark_completed(task.task_id, saved_filepath)

                # Panggil callback monitor jika ada
                if self.on_upload_callback:
                    try:
                        self.on_upload_callback(task, saved_filepath)
                    except Exception:
                        pass

                next_task = self.queue_manager.get_current_task()
                self._send_json(200, {
                    "success": True,
                    "message": f"Gambar berhasil disimpan ke {os.path.basename(saved_filepath)}!",
                    "saved_path": saved_filepath,
                    "next_task": next_task.to_dict() if next_task else None,
                    "stats": self.queue_manager.get_stats()
                })

            except Exception as e:
                self._send_json(500, {"success": False, "error": str(e)})

        elif path == "/api/skip":
            next_t = self.queue_manager.skip_current()
            self._send_json(200, {
                "success": True,
                "current_task": next_t.to_dict() if next_t else None,
                "stats": self.queue_manager.get_stats()
            })

        elif path == "/api/next":
            next_t = self.queue_manager.next_task()
            self._send_json(200, {
                "success": True,
                "current_task": next_t.to_dict() if next_t else None,
                "stats": self.queue_manager.get_stats()
            })

        elif path == "/api/prev":
            prev_t = self.queue_manager.prev_task()
            self._send_json(200, {
                "success": True,
                "current_task": prev_t.to_dict() if prev_t else None,
                "stats": self.queue_manager.get_stats()
            })

        else:
            self._send_json(404, {"error": "Endpoint tidak ditemukan"})

    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _save_image_file(self, image_bytes, target_path):
        """
        Menyimpan byte gambar menjadi format WebP teroptimasi.
        """
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        # Pastikan ekstensi .webp
        base, _ = os.path.splitext(target_path)
        final_path = f"{base}.webp"

        if PILLOW_AVAILABLE:
            try:
                img = Image.open(io.BytesIO(image_bytes))
                # Convert RGBA to RGB if needed for saving
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    # Keep RGBA for transparent webp or convert cleanly
                    img.save(final_path, "WEBP", quality=88, method=6)
                else:
                    img = img.convert("RGB")
                    img.save(final_path, "WEBP", quality=88, method=6)
                return final_path
            except Exception:
                pass

        # Fallback raw write
        with open(final_path, "wb") as f:
            f.write(image_bytes)
        return final_path

    def _update_markdown_frontmatter(self, md_path, image_path):
        """
        Memperbarui referensi heroImage/image pada frontmatter markdown artikel.
        """
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()

            rel_img = f"images/{os.path.basename(image_path)}"
            # Ganti heroImage dan image di frontmatter
            if "heroImage:" in content:
                content = re.sub(r'heroImage:\s*["\']?[^"\'\n\r]*["\']?', f'heroImage: "{rel_img}"', content)
            if "image:" in content:
                content = re.sub(r'image:\s*["\']?[^"\'\n\r]*["\']?', f'image: "{rel_img}"', content)
            if "coverImage:" in content:
                content = re.sub(r'coverImage:\s*["\']?[^"\'\n\r]*["\']?', f'coverImage: "{rel_img}"', content)

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass


# ==========================================
# 4. FLOW BRIDGE SERVER CONTROLLER
# ==========================================
class FlowBridgeServer:
    def __init__(self, port=FLOW_BRIDGE_PORT):
        self.port = port
        self.server = None
        self.thread = None
        self.queue_manager = FlowQueueManager()
        self.is_running = False

    def start(self, tasks=None, on_upload_callback=None):
        if tasks:
            self.queue_manager = FlowQueueManager(tasks)

        # Configure handler
        FlowBridgeHTTPHandler.queue_manager = self.queue_manager
        FlowBridgeHTTPHandler.on_upload_callback = on_upload_callback

        try:
            self.server = HTTPServer(("0.0.0.0", self.port), FlowBridgeHTTPHandler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            self.is_running = True
            return True
        except Exception as e:
            # Coba port alternatif jika 7860 sedang dipakai
            try:
                self.port = 7861
                self.server = HTTPServer(("0.0.0.0", self.port), FlowBridgeHTTPHandler)
                self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
                self.thread.start()
                self.is_running = True
                return True
            except Exception:
                self.is_running = False
                return False

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        self.is_running = False


# ==========================================
# 5. SCANNER HELPER: ARTIKEL TANPA GAMBAR
# ==========================================
def scan_articles_for_flow_bridge(base_silos_dir, site_info=None, default_style="photo"):
    """
    Memindai artikel yang belum memiliki gambar fisik dan membungkusnya ke dalam FlowTask.
    """
    tasks = []
    if not os.path.exists(base_silos_dir):
        return tasks

    site_name = site_info.get("name", "") if site_info else ""
    site_niche = site_info.get("profile", {}).get("niche", "") if site_info else ""
    site_brand = site_info.get("profile", {}).get("brand_name", "") if site_info else ""

    for root, dirs, files in os.walk(base_silos_dir):
        for f in files:
            if f.endswith(".md") and f != "SILO_BLUEPRINT.md":
                md_path = os.path.join(root, f)
                slug = os.path.splitext(f)[0]
                
                # Lokasi gambar yang diharapkan
                img_dir = os.path.join(os.path.dirname(md_path), "images")
                target_img_path = os.path.join(img_dir, f"{slug}.webp")

                # Cek apakah gambar sudah ada dan ukurannya > 0
                if os.path.exists(target_img_path) and os.path.getsize(target_img_path) > 1000:
                    continue

                # Baca metadata artikel
                try:
                    with open(md_path, "r", encoding="utf-8") as mdf:
                        md_content = mdf.read()
                    
                    title_match = re.search(r'title:\s*["\']?([^"\'\n\r]+)["\']?', md_content)
                    title = title_match.group(1).strip() if title_match else slug.replace("-", " ").title()

                    kw_match = re.search(r'keyword:\s*["\']?([^"\'\n\r]+)["\']?', md_content)
                    kw = kw_match.group(1).strip() if kw_match else title

                    silo_folder = os.path.basename(os.path.dirname(root)) if os.path.basename(root) == "images" else os.path.basename(root)

                    prompt = generate_flow_prompt(
                        keyword=kw,
                        article_title=title,
                        niche=site_niche,
                        style=default_style,
                        brand=site_brand
                    )

                    task = FlowTask(
                        task_id=f"task_{len(tasks) + 1}_{slug}",
                        keyword=kw,
                        title=title,
                        prompt=prompt,
                        target_path=target_img_path,
                        md_path=md_path,
                        site_name=site_name,
                        silo_name=silo_folder
                    )
                    tasks.append(task)
                except Exception:
                    continue

    return tasks


# ==========================================
# 6. INTERACTIVE CLI RUNNER FOR FLOW BRIDGE
# ==========================================
def run_flow_bridge_session(tasks, site_info=None, auto_open_browser=True):
    """
    Menjalankan sesi server lokal Google Flow Bridge secara interaktif di CLI.
    Menampilkan monitor progres real-time saat pengguna memilih gambar di flow.google.com.
    """
    if not tasks:
        print("\nTidak ada artikel yang membutuhkan generate gambar (Semua artikel sudah memiliki gambar).")
        return {"total": 0, "completed": 0, "skipped": 0, "pending": 0}

    # ANSI Colors
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    server = FlowBridgeServer(port=FLOW_BRIDGE_PORT)
    
    last_event = "Server siap. Menunggu koneksi dari Chrome Extension..."
    event_lock = threading.Lock()

    def on_upload_event(task, saved_path):
        nonlocal last_event
        with event_lock:
            last_event = f"{GREEN}[✓ DITERIMA]{RESET} Gambar disimpan: {CYAN}{os.path.basename(saved_path)}{RESET} untuk \"{task.keyword}\""

    ok = server.start(tasks=tasks, on_upload_callback=on_upload_event)
    if not ok:
        print(f"\n{RED}[X] Gagal memulai Flow Bridge Server di port {FLOW_BRIDGE_PORT} atau {FLOW_BRIDGE_PORT + 1}.{RESET}")
        return {"total": len(tasks), "completed": 0, "skipped": 0, "pending": len(tasks)}

    if auto_open_browser:
        try:
            webbrowser.open("https://flow.google.com/")
        except Exception:
            pass

    print(f"\n{GREEN}{BOLD}[!] Flow Bridge Server Aktif di http://localhost:{server.port}{RESET}")
    print(f"{DIM}Pastikan Chrome Extension 'Google Flow to AI Silo Bridge' sudah terpasang.{RESET}\n")

    try:
        while True:
            stats = server.queue_manager.get_stats()
            cur_task = server.queue_manager.get_current_task()

            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"\n{CYAN}{BOLD}=== GOOGLE FLOW EXTENSION BRIDGE (WORKER AKTIF) ==={RESET}")
            print(f"{DIM}{'=' * 65}{RESET}")
            print(f" {BOLD}Server Lokal :{RESET} {GREEN}http://localhost:{server.port}{RESET} {DIM}(Online & Siap Menerima Gambar){RESET}")
            print(f" {BOLD}Status Antrean:{RESET} Total: {BOLD}{stats['total']}{RESET} | Selesai: {GREEN}{BOLD}{stats['completed']}{RESET} | Sisa: {YELLOW}{BOLD}{stats['pending']}{RESET} | Lewat: {DIM}{stats['skipped']}{RESET}\n")

            if cur_task:
                print(f" {YELLOW}{BOLD}[ARTIKEL AKTIF SAAT INI - #{stats['current_index']}/{stats['total']}]{RESET}")
                print(f"  - {BOLD}Keyword :{RESET} {CYAN}{cur_task.keyword}{RESET}")
                print(f"  - {BOLD}Artikel :{RESET} {cur_task.title}")
                print(f"  - {BOLD}Lokasi  :{RESET} {DIM}{cur_task.target_path}{RESET}")
                print(f"  - {BOLD}Prompt  :{RESET} {DIM}{cur_task.prompt[:120]}...{RESET}\n")
            else:
                print(f" {GREEN}{BOLD}[🎉 SEMUA TUGAS SELESAI]{RESET}")
                print(f" Seluruh {stats['completed']} artikel telah berhasil dipasangi gambar!\n")

            print(f" {BOLD}Aktivitas Terbaru:{RESET}")
            with event_lock:
                print(f"  {last_event}\n")

            print(f"{DIM}{'-' * 65}{RESET}")
            print(f" {BOLD}Petunjuk di Browser flow.google.com:{RESET}")
            print(f"  1. Buka {CYAN}flow.google.com{RESET} di browser.")
            print(f"  2. Klik tombol {GREEN}[⚡ Auto-Fill]{RESET} pada floating dock extension untuk memasukkan prompt.")
            print(f"  3. Klik tombol {GREEN}[📸 Kirim ke Silo]{RESET} pada variasi gambar favorit Anda.")
            print(f"{DIM}{'-' * 65}{RESET}")
            print(f" Kontrol Keyboard: [{BOLD}N{RESET}] Next/Skip | [{BOLD}P{RESET}] Prev | [{BOLD}B{RESET}] Buka Browser | [{BOLD}0/Q{RESET}] Selesai & Keluar")

            # Non-blocking or short timeout key check
            # Menggunakan short sleep / key check
            if os.name == 'nt':
                import msvcrt
                # Wait up to 1 second for keypress while polling
                start_t = time.time()
                key_pressed = None
                while time.time() - start_t < 1.0:
                    if msvcrt.kbhit():
                        ch = msvcrt.getwch()
                        if ch in ('\x00', '\xe0'):
                            ch = msvcrt.getwch()
                            if ch == 'M': key_pressed = 'n'
                            elif ch == 'K': key_pressed = 'p'
                        else:
                            key_pressed = ch.lower()
                        break
                    time.sleep(0.08)

                if key_pressed in ['q', '0', '\x1b']:
                    break
                elif key_pressed == 'n':
                    server.queue_manager.skip_current()
                elif key_pressed == 'p':
                    server.queue_manager.prev_task()
                elif key_pressed == 'b':
                    webbrowser.open("https://flow.google.com/")
            else:
                # Linux fallback
                time.sleep(1.5)

            # Auto break if all done
            if stats['total'] > 0 and stats['completed'] == stats['total']:
                time.sleep(1)
                break

    except KeyboardInterrupt:
        pass
    finally:
        server.stop()

    final_stats = server.queue_manager.get_stats()
    print(f"\n{GREEN}[OK] Sesi Flow Bridge ditutup. Total {final_stats['completed']} gambar berhasil tersimpan.{RESET}")
    return final_stats

