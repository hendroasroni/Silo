import sys
import os
import time
import re
import html
import webbrowser
from datetime import datetime, timedelta

# Ensure UTF-8 output encoding for Windows terminal
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from gemini_api import GeminiClient, DEFAULT_FLASH_MODELS, DEFAULT_PRO_MODELS
from kie_image_api import KieImageClient, DEFAULT_KIE_MODELS, DEFAULT_IMAGE_STYLES, IMAGE_STYLE_DESCS, clean_text_for_rendering
from kie_chat_api import KieChatClient
from agnes_api import AgnesClient, DEFAULT_AGNES_TEXT_MODELS, DEFAULT_AGNES_IMAGE_MODELS
from youtube_generator import YouTubeProfileManager, YouTubeGenerator, YOUTUBE_OUTPUT_DIR
from youtube_live_api import YouTubeLiveClient
from ai_pipeline import AIPipelineManager, AVAILABLE_ENGINES, STAGE_NAMES
from silo_generator import SiloGenerator
from wp_publisher import WordPressPublisher

# ANSI color styling
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    print(f"\n{CYAN}{BOLD}🏛️  AI SILO BUILDER & PUBLISHER{RESET}")
    print(f"{DIM}{'=' * 60}{RESET}")

def print_section(title):
    print(f"\n{YELLOW}{BOLD}▶ {title}{RESET}")
    print(f"{DIM}{'-' * 60}{RESET}")

def read_raw_key():
    """
    Membaca satu input tombol dari terminal secara real-time.
    Mengembalikan: 'UP', 'DOWN', 'LEFT', 'RIGHT', 'ENTER', 'ESC', atau karakter string.
    """
    if os.name == 'nt':
        import msvcrt
        ch = msvcrt.getwch()
        if ch in ('\x00', '\xe0'):
            ch2 = msvcrt.getwch()
            if ch2 == 'H': return 'UP'
            if ch2 == 'P': return 'DOWN'
            if ch2 == 'K': return 'LEFT'
            if ch2 == 'M': return 'RIGHT'
            return 'SPECIAL'
        if ch in ('\r', '\n'):
            return 'ENTER'
        if ch == '\x1b':
            return 'ESC'
        if ch == '\x03':
            raise KeyboardInterrupt
        return ch
    else:
        import termios, tty, select
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                r, _, _ = select.select([sys.stdin], [], [], 0.05)
                if r:
                    ch2 = sys.stdin.read(1)
                    if ch2 == '[':
                        ch3 = sys.stdin.read(1)
                        if ch3 == 'A': return 'UP'
                        if ch3 == 'B': return 'DOWN'
                        if ch3 == 'C': return 'RIGHT'
                        if ch3 == 'D': return 'LEFT'
                return 'ESC'
            if ch in ('\r', '\n'):
                return 'ENTER'
            if ch == '\x03':
                raise KeyboardInterrupt
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def select_menu(options, title=None, default_index=0, help_hint=None):
    """
    Komponen pemilih menu interaktif:
    - Navigasi tombol Panah [↑ / ↓]
    - Konfirmasi pilihan dengan tombol [ENTER]
    - Pintasan cepat tekan angka/huruf langsung
    - Tombol '0' atau ESC untuk kembali/batal
    """
    if not options:
        return "0"

    norm_options = []
    for opt in options:
        if isinstance(opt, tuple):
            norm_options.append({'key': str(opt[0]), 'label': str(opt[1])})
        elif isinstance(opt, dict):
            norm_options.append({'key': str(opt.get('key', '')), 'label': str(opt.get('label', ''))})
        else:
            norm_options.append({'key': str(opt), 'label': str(opt)})

    selected_idx = max(0, min(default_index, len(norm_options) - 1))

    if title:
        print_section(title)

    prev_line_count = 0

    while True:
        rendered_lines = []
        for idx, opt in enumerate(norm_options):
            k = opt['key']
            lbl = opt['label']
            if idx == selected_idx:
                rendered_lines.append(f"{CYAN}{BOLD} ➔ [{k}]  {lbl} ◀{RESET}")
            else:
                rendered_lines.append(f"    [{k}]  {lbl}")

        rendered_lines.append(f"{DIM}{'-' * 60}{RESET}")
        if help_hint:
            rendered_lines.append(help_hint)
        else:
            rendered_lines.append(
                f"{DIM}Pilih [{CYAN}↑/↓ + Enter{RESET}{DIM}] atau tekan angka/huruf:{RESET} "
            )

        total_lines = len(rendered_lines)

        if prev_line_count > 0:
            print(f"\033[{prev_line_count}A\r", end="", flush=True)

        for line in rendered_lines:
            print(f"\033[K{line}", flush=True)

        prev_line_count = total_lines

        key = read_raw_key()

        if key == 'UP':
            selected_idx = (selected_idx - 1) % len(norm_options)
        elif key == 'DOWN':
            selected_idx = (selected_idx + 1) % len(norm_options)
        elif key == 'ENTER':
            chosen_key = norm_options[selected_idx]['key']
            print("")
            return chosen_key
        elif key == 'ESC':
            for opt in norm_options:
                if opt['key'] == '0':
                    print("")
                    return '0'
            print("")
            return '0'
        else:
            k_lower = str(key).lower()
            for opt in norm_options:
                if opt['key'].lower() == k_lower:
                    print("")
                    return opt['key']

def get_single_key(prompt="", valid_keys=None):
    """
    Helper untuk membaca 1 karakter dengan prompt.
    Mendukung tombol Enter (default Yes/Confirm) dan '0' / ESC (Cancel).
    """
    if prompt:
        print(prompt, end="", flush=True)

    while True:
        key = read_raw_key()
        if key == 'ENTER':
            if valid_keys and ('\r' in valid_keys or '\n' in valid_keys or 'y' in [str(k).lower() for k in valid_keys]):
                print("")
                return 'y'
            elif valid_keys and '1' in valid_keys:
                print("")
                return '1'
        if key == 'ESC':
            print("0")
            return '0'
        if key in ['UP', 'DOWN', 'LEFT', 'RIGHT', 'SPECIAL']:
            continue
        
        if valid_keys is None:
            print(key)
            return key
        
        valid_lower = [str(k).lower() for k in valid_keys]
        if str(key).lower() in valid_lower:
            print(key)
            return str(key)

def press_any_key(msg="Tekan tombol apa saja untuk kembali..."):
    print(f"\n{DIM}{msg}{RESET}", end="", flush=True)
    read_raw_key()
    print("")
    return ""

def parse_user_selection(input_str, total_items, default_ids=None):
    input_str = input_str.strip().lower()
    if not input_str:
        return default_ids if default_ids is not None else []

    if input_str == "0":
        return []

    if input_str in ["all", "semua", "a"]:
        return list(range(1, total_items + 1))

    if input_str in ["rek", "rekomendasi", "r"] and default_ids:
        return default_ids

    selected = set()
    parts = input_str.split(",")
    for part in parts:
        part = part.strip()
        if "-" in part:
            try:
                start, end = map(int, part.split("-"))
                for num in range(start, end + 1):
                    if 1 <= num <= total_items:
                        selected.add(num)
            except ValueError:
                pass
        else:
            try:
                num = int(part)
                if 1 <= num <= total_items:
                    selected.add(num)
            except ValueError:
                pass

    return sorted(list(selected))

# ==========================================
# MENU 1: GENERATE SILO ARTICLES (NEW & RESUME)
# ==========================================
def menu_generate_silo():
    clear_screen()
    print_banner()

    try:
        client = GeminiClient(key_file="apikey.txt")
        active_model = client.get_working_model()
        total_keys = len(client.api_keys)
        print(f"{GREEN}✔ API Key terhubung! ({total_keys} Key aktif) | Model: {BOLD}{active_model}{RESET}\n")
    except Exception as e:
        print(f"{RED}✖ Error Inisialisasi API: {e}{RESET}")
        print(f"{YELLOW}Pastikan file 'apikey.txt' berisi API Key Gemini yang valid (Menu [5]).{RESET}")
        press_any_key()
        return

    silo_engine = SiloGenerator(client)

    # Check existing Silo projects
    existing_silos = silo_engine.list_existing_silos("output")
    incomplete_silos = [s for s in existing_silos if s["pending_count"] > 0]

    if incomplete_silos:
        options = [
            ("1", "Buat Silo Baru (Keyword Baru)"),
            ("2", f"Lanjutkan Proyek Silo ({len(incomplete_silos)} Belum Selesai)"),
            ("0", "Kembali ke Menu Utama")
        ]
        choice = select_menu(options, title="PILIH MODUS SILO")
        if choice == "0":
            return
        elif choice == "2":
            resume_existing_silo_flow(silo_engine, incomplete_silos, client)
            return

    create_new_silo_flow(silo_engine, client)

def create_new_silo_flow(silo_engine, client):
    active_model = client.get_working_model()

    print_section("LANGKAH 1: Input Keyword & Konteks Website")
    print(f"{DIM}Ketik '0' untuk membatalkan dan kembali ke Menu Utama.{RESET}\n")
    seed_kw = input(f"{BOLD}Masukkan Keyword Utama (Seed Keyword):{RESET} ").strip()
    if seed_kw == "0":
        return
    while not seed_kw:
        seed_kw = input(f"{YELLOW}Keyword tidak boleh kosong. Masukkan keyword (atau 0 untuk batal):{RESET} ").strip()
        if seed_kw == "0":
            return

    lang_input = input(f"{BOLD}Bahasa Artikel [Default: Bahasa Indonesia]:{RESET} ").strip()
    if lang_input == "0":
        return
    language = lang_input if lang_input else "Bahasa Indonesia"

    niche_input = input(f"{BOLD}Konteks Niche / Target Pembaca [Opsional, tekan Enter untuk lewati]:{RESET} ").strip()
    if niche_input == "0":
        return
    niche = niche_input if niche_input else "Umum"

    cluster_input = input(f"{BOLD}Jumlah Artikel Cluster / Longtail [Default: 6, misal: 4, 8, 10, 15]:{RESET} ").strip()
    if cluster_input == "0":
        return
    try:
        cluster_count = int(cluster_input) if cluster_input else 6
        if cluster_count < 1:
            cluster_count = 6
    except ValueError:
        cluster_count = 6

    tone_input = input(f"{BOLD}Gaya Bahasa / Tone [Default: Informatif, Mengalir Natural & Profesional]:{RESET} ").strip()
    if tone_input == "0":
        return
    tone = tone_input if tone_input else "Informatif, Mengalir Natural & Profesional, Solutif, Bebas Klise AI"

    # LANGKAH 1.5: Profil Bisnis & Grounding Knowledge
    print_section("LANGKAH 1.5: Pilih Profil Bisnis & Grounding Knowledge")
    wp = WordPressPublisher()
    sites = wp.get_sites()

    profile_options = []
    for i, s in enumerate(sites, 1):
        prof = s.get("profile", {})
        brand = prof.get("brand_name", "")
        type_tag = "[Astro]" if s.get("type") == "astro" else "[WP]"
        if brand:
            prof_tag = f"{GREEN}[Profil: {brand}]{RESET}"
        else:
            prof_tag = f"{DIM}(Profil Belum Diisi){RESET}"
        profile_options.append((str(i), f"{type_tag} {s['name']} {prof_tag}"))

    profile_options.append(("K", "📝 Catatan Ringkas Cepat / Quick Context (1 Baris)"))
    profile_options.append(("0", "🌐 Standar Industri Obyektif (Tanpa Profil / Edukasi Netral)"))

    p_choice = select_menu(profile_options, title="PILIH PROFIL GROUNDING WEBSITE")
    business_profile = {}

    if p_choice == "0":
        print(f"\n{CYAN}ℹ️ Mode Standar Industri Obyektif aktif (Estimasi pasar & edukatif netral).{RESET}")
        business_profile = {}
    elif p_choice.upper() == "K":
        print_section("INPUT CATATAN RINGKAS (QUICK CONTEXT)")
        quick_note = input(f"{BOLD}Masukkan catatan/fakta singkat (misal: 'Spesialis sondir area Jawa Tengah, tarif mulai 1,5 jt, WA: 0812345678'):{RESET}\n").strip()
        if quick_note:
            business_profile = {"brand_name": "", "custom_notes": quick_note}
            print(f"{GREEN}✔ Catatan ringkas disimpan untuk grounding Silo ini.{RESET}")
    else:
        try:
            site_idx = int(p_choice) - 1
            selected_site = sites[site_idx]
            business_profile = selected_site.get("profile", {})
            if business_profile and any(business_profile.values()):
                b_name = business_profile.get("brand_name", selected_site["name"])
                print(f"\n{GREEN}✔ Profil bisnis '{b_name}' aktif untuk Silo ini! (Zero Hallucination Grounding){RESET}")
            else:
                print(f"\n{YELLOW}⚠️ Website '{selected_site['name']}' belum memiliki data profil lengkap.{RESET}")
                print(f"{CYAN}Silo akan tetap berjalan dengan mode Standar Industri Obyektif.{RESET}")
        except Exception:
            business_profile = {}

    # Riset Silo
    pipeline_mgr = AIPipelineManager()
    stage1_client = pipeline_mgr.get_client_for_stage(1, default_gemini_client=client)
    s1_label = pipeline_mgr.get_stage_display_name(1)

    print_section("LANGKAH 2: Riset Longtail Keyword & Pemetaan Silo")
    print(f"{CYAN}Sedang menganalisis search intent, memetakan 1 Pilar + {cluster_count} Cluster terbaik dengan [{s1_label}]...{RESET}")
    
    try:
        silo_plan = silo_engine.research_silo_cluster(
            seed_kw,
            language=language,
            niche_context=niche,
            cluster_count=cluster_count,
            business_profile=business_profile,
            client=stage1_client
        )
        # AUTO-SAVE SILO PLAN IMMEDIATELY! (Meskipun belum membuat artikel, plan tersimpan aman)
        silo_engine.save_silo_project(silo_plan, new_articles=[])
    except Exception as e:
        print(f"{RED}✖ Gagal melakukan riset keyword: {e}{RESET}")
        press_any_key()
        return

    process_silo_items_generation(silo_engine, silo_plan, completed_existing_ids=[], language=language, tone=tone, client=client)

def resume_existing_silo_flow(silo_engine, incomplete_silos, client):
    options = []
    for i, s in enumerate(incomplete_silos, 1):
        lbl = f"{s['silo_theme']} - {GREEN}{s['completed_count']}/{s['total_topics']} Selesai{RESET} ({YELLOW}{s['pending_count']} Pending{RESET})"
        options.append((str(i), lbl))
    options.append(("0", "Kembali ke Menu Utama"))

    c = select_menu(options, title="PILIH PROYEK SILO")
    if c == "0":
        return

    selected_silo = incomplete_silos[int(c) - 1]
    silo_plan = selected_silo["silo_plan"]
    completed_ids = selected_silo["completed_ids"]
    pending_items = [item for item in silo_plan.get("items", []) if item["id"] not in completed_ids]

    # Action menu for selected Silo project
    action_options = [
        ("1", f"Tulis Sisa Cluster ({len(pending_items)} artikel tersisa)"),
        ("2", "Ubah / Tambah Jumlah Cluster"),
        ("0", "Kembali")
    ]
    action = select_menu(action_options, title=f"KELOLA PROYEK: {selected_silo['silo_theme']}")
    if action == "0":
        return
    elif action == "2":
        expand_silo_flow(silo_engine, silo_plan, completed_ids, client)
        return

    process_silo_items_generation(silo_engine, silo_plan, completed_existing_ids=completed_ids, language="Bahasa Indonesia", tone="Informatif, Mengalir Natural & Profesional, Solutif, Bebas Klise AI", client=client)

def expand_silo_flow(silo_engine, silo_plan, completed_ids, client):
    print_section("UBAH / TAMBAH JUMLAH CLUSTER SILO")
    existing_items = silo_plan.get("items", [])
    existing_clusters = [i for i in existing_items if i["role"].lower() != "pillar"]
    current_count = len(existing_clusters)

    print(f"📌 {BOLD}Topik Silo:{RESET} {silo_plan.get('seed_keyword')}")
    print(f"📊 {BOLD}Jumlah Cluster Saat Ini:{RESET} {BOLD}{current_count} cluster{RESET} (Total item: {len(existing_items)})\n")

    new_count_str = input(f"{BOLD}Masukkan target total cluster baru (misal: 8, 10, 15 - atau 0 untuk batal):{RESET} ").strip()
    if new_count_str == "0" or not new_count_str:
        return

    try:
        new_count = int(new_count_str)
        if new_count < len(completed_ids):
            print(f"{RED}Jumlah cluster tidak boleh kurang dari jumlah artikel yang sudah dibuat ({len(completed_ids)} artikel).{RESET}")
            press_any_key()
            return
    except ValueError:
        print(f"{RED}Input harus berupa angka.{RESET}")
        press_any_key()
        return

    if new_count == current_count:
        print(f"{YELLOW}Jumlah cluster sama dengan saat ini.{RESET}")
        press_any_key()
        return

    print(f"\n{CYAN}Sedang memproses perubahan cluster dengan Gemini [{client.get_working_model()}]...{RESET}")
    try:
        updated_plan = silo_engine.expand_silo_clusters(silo_plan, new_target_count=new_count)
        print(f"{GREEN}✔ Sukses memperbarui Silo Plan menjadi {new_count} cluster! (Tersimpan di metadata & blueprint){RESET}\n")
    except Exception as e:
        print(f"{RED}✖ Gagal memperbarui cluster: {e}{RESET}")
        press_any_key()
        return

    # Lanjut ke pemilihan pembuatan artikel
    process_silo_items_generation(silo_engine, updated_plan, completed_existing_ids=completed_ids, language="Bahasa Indonesia", tone="Informatif, Mengalir Natural & Profesional, Solutif, Bebas Klise AI", client=client)

def process_silo_items_generation(silo_engine, silo_plan, completed_existing_ids, language, tone, client):
    pipeline_mgr = AIPipelineManager()
    stage1_client = pipeline_mgr.get_client_for_stage(1, default_gemini_client=client)
    stage2_client = pipeline_mgr.get_client_for_stage(2, default_gemini_client=client)
    stage3_client = pipeline_mgr.get_client_for_stage(3, default_gemini_client=client)

    s1_name = pipeline_mgr.get_stage_display_name(1)
    s2_name = pipeline_mgr.get_stage_display_name(2)
    s3_name = pipeline_mgr.get_stage_display_name(3)

    items = silo_plan.get("items", [])
    
    print(f"\n{GREEN}✔ Arsitektur Silo Terpilih:{RESET}")
    print(f"📌 {BOLD}Tema Silo:{RESET} {silo_plan.get('silo_theme')}")
    print(f"🎯 {BOLD}Topical Goal:{RESET} {silo_plan.get('topical_authority_goal')}\n")

    default_rec_ids = []
    pending_items = []

    print(f"{BOLD}{'No':<4} {'Role':<10} {'Target Longtail / Keyword':<30} {'Status':<14} {'Prioritas'}{RESET}")
    print("-" * 78)

    for item in items:
        i_id = item["id"]
        role = item["role"]
        kw = item["keyword"]
        is_rec = item.get("is_recommended_default", False)
        rank = item.get("recommendation_rank", i_id)
        is_done = i_id in completed_existing_ids

        role_str = f"{MAGENTA}👑 Pillar{RESET}" if role.lower() == "pillar" else f"{CYAN}🔗 Cluster{RESET}"
        kw_display = (kw[:27] + '...') if len(kw) > 27 else kw

        if is_done:
            status_str = f"{GREEN}✅ SELESAI{RESET}"
            rec_tag = f"{DIM}Sudah Dibuat{RESET}"
        else:
            status_str = f"{YELLOW}⏳ PENDING{RESET}"
            pending_items.append(item)
            if is_rec:
                default_rec_ids.append(i_id)
                rec_tag = f"{YELLOW}⭐ [Rekomendasi #{rank}]{RESET}"
            else:
                rec_tag = f"{DIM}Rank #{rank}{RESET}"

        print(f"{BOLD}#{i_id:<3}{RESET} {role_str:<18} {kw_display:<30} {status_str:<23} {rec_tag}")
        if not is_done:
            print(f"    {DIM}↳ Judul Usulan: {item['suggested_title']}{RESET}")
            print(f"    {DIM}↳ Alasan: {item.get('recommendation_reason', '-')}{RESET}\n")

    if not pending_items:
        print(f"\n{GREEN}{BOLD}🎉 Semua artikel dalam Silo ini sudah selesai dibuat!{RESET}")
        press_any_key()
        return

    # Pemilihan Artikel
    print_section("PILIH ARTIKEL YANG AKAN DIPRODUKSI")
    default_str = ", ".join(map(str, default_rec_ids)) if default_rec_ids else str(pending_items[0]["id"])
    print(f"Pilihan input:")
    print(f" • Ketik nomor pilihan artikel pending (contoh: {CYAN}2, 3{RESET} atau {CYAN}2-5{RESET})")
    print(f" • Ketik {CYAN}all{RESET} atau {CYAN}semua{RESET} untuk membuat SEMUA {len(pending_items)} cluster yang belum dibuat")
    print(f" • Tekan {GREEN}[ENTER]{RESET} langsung untuk memilih default rekomendasi ({CYAN}{default_str}{RESET})")
    print(f" • Ketik {RED}0{RESET} untuk batal (Plan Silo tetap tersimpan aman di disk)")
    
    choice = input(f"\n{BOLD}Pilihan Anda:{RESET} ").strip()
    if choice == "0":
        return

    if not choice:
        selected_ids = default_rec_ids if default_rec_ids else [pending_items[0]["id"]]
    elif choice in ["all", "semua", "a"]:
        selected_ids = [it["id"] for it in pending_items]
    else:
        selected_ids = parse_user_selection(choice, len(items), default_rec_ids)

    selected_items = [it for it in items if it["id"] in selected_ids and it["id"] not in completed_existing_ids]

    if not selected_items:
        print(f"{RED}Tidak ada artikel pending yang dipilih.{RESET}")
        press_any_key()
        return

    print(f"\n{GREEN}✔ Anda memilih {len(selected_items)} artikel untuk diproduksi: {[it['id'] for it in selected_items]}{RESET}")

    confirm_char = get_single_key(f"\n{BOLD}Mulai proses pembuatan konten & kurasi? [Y/N atau 0]:{RESET} ", valid_keys=['y', 'n', '0', '\r', '\n'])
    if confirm_char.lower() in ['n', '0']:
        print(f"\n{YELLOW}Dibatalkan oleh pengguna (Plan Silo tetap tersimpan).{RESET}")
        press_any_key()
        return

    # Generate Brief, Write, Curate
    print_section("PEMBUATAN KONTEN & KURASI KUALITAS MULTI-STAGE")
    print(f"  📝 [Tahap 1 Brief]  : {CYAN}{s1_name}{RESET}")
    print(f"  ✍️  [Tahap 2 Draft]  : {MAGENTA}{s2_name}{RESET}")
    print(f"  🔍 [Tahap 3 Kurasi] : {GREEN}{s3_name}{RESET}")
    new_completed = []

    for idx, item in enumerate(selected_items, 1):
        print(f"\n{BOLD}{CYAN}-------------------------------------------------------{RESET}")
        print(f"{BOLD}[{idx}/{len(selected_items)}] Memproses: #{item['id']} - {item['keyword']} ({item['role']}){RESET}")
        print(f"{BOLD}{CYAN}-------------------------------------------------------{RESET}")

        # A. Brief & Archetype
        print(f"  📝 [1/4] Merancang Content Brief & Format Arketipe...", end="", flush=True)
        try:
            brief = silo_engine.generate_content_brief(
                item,
                silo_plan,
                language=language,
                business_profile=silo_plan.get("business_profile"),
                client=stage1_client
            )
            arch_data = brief.get("content_archetype", {})
            arch_name = arch_data.get("format_label") or arch_data.get("type", "Standard Guide")
            print(f" {GREEN}OK{RESET} (Format: {MAGENTA}{BOLD}{arch_name}{RESET}, Target: {brief.get('target_word_count')})")
        except Exception as e:
            print(f" {RED}FAILED ({e}){RESET}")
            continue

        # B. Write Draft
        print(f"  ✍️  [2/4] Menulis Draf Sesuai Arketipe Konten...", end="", flush=True)
        try:
            draft = silo_engine.write_article_draft(
                brief,
                silo_plan,
                tone=tone,
                language=language,
                business_profile=silo_plan.get("business_profile"),
                client=stage2_client
            )
            word_count = len(draft.split())
            print(f" {GREEN}OK{RESET} ({word_count} kata)")
        except Exception as e:
            print(f" {RED}FAILED ({e}){RESET}")
            continue

        # C. Curate & Polish
        print(f"  🔍 [3/4] Melakukan Kurasi & Polishing Kualitas...", end="", flush=True)
        try:
            curation = silo_engine.curate_and_polish_article(
                draft,
                brief,
                silo_plan,
                business_profile=silo_plan.get("business_profile"),
                client=stage3_client
            )
            score = curation.get("overall_score", 90)
            status = curation.get("curation_status", "LULUS")
            print(f" {GREEN}OK{RESET} (Skor: {BOLD}{score}/100{RESET} - {status})")
            
            critiques = curation.get("editorial_critique", [])
            for crit in critiques[:2]:
                print(f"     {DIM}• {crit}{RESET}")
        except Exception as e:
            print(f" {YELLOW}Warning: Kurasi dilewati ({e}){RESET}")
            curation = {"overall_score": 85, "final_article_markdown": draft, "curation_status": "DRAFT_ORIGINAL"}

        # D. Featured Image Generator (Kie.ai AI Photo + Mesh Gradient Fallback)
        kie_client = KieImageClient()
        slug = brief.get("url_slug", f"article_{item['id']}")
        from silo_generator import slugify
        silo_folder_name = slugify(silo_plan.get("seed_keyword", silo_plan.get("silo_theme", "silo")))
        img_save_path = os.path.join("output", silo_folder_name, "images", f"{slug}.webp")
        category_label = silo_plan.get("silo_theme", "Silo Pillar" if item.get("role", "").lower() == "pillar" else "Silo Cluster")

        print(f"  🖼️  [4/4] Generate Featured Image...", end="", flush=True)
        try:
            saved_path, method_used = kie_client.generate_featured_image_auto(
                title=item["suggested_title"],
                keyword=item["keyword"],
                category=category_label,
                save_path=img_save_path,
                gemini_client=client
            )
            if method_used == "kie_ai":
                st_name = kie_client.get_image_style().replace("_", " ").title()
                print(f" {GREEN}OK - Kie.ai ({st_name}){RESET} (`{os.path.basename(img_save_path)}`)")
            else:
                print(f" {CYAN}OK - Mesh Gradient Banner (Fallback){RESET} (`{os.path.basename(img_save_path)}`)")
        except Exception as ie:
            print(f" {YELLOW}Dilewati ({ie}){RESET}")

        new_completed.append({
            "item_id": item["id"],
            "item": item,
            "brief": brief,
            "draft": draft,
            "curation": curation
        })

    # Simpan hasil incremental
    if not new_completed:
        print(f"{RED}Tidak ada artikel yang berhasil dibuat.{RESET}")
    else:
        try:
            output_dir, saved_files = silo_engine.save_silo_project(silo_plan, new_completed)
            print(f"\n{GREEN}{BOLD}🎉 ARTIKEL BERHASIL DITAMBAHKAN KE SILO!{RESET}")
            print(f"📁 Direktori: {CYAN}{output_dir}{RESET}\n")
            print(f"{BOLD}File artikel baru & blueprint yang diperbarui:{RESET}")
            for fpath in saved_files:
                fname = os.path.basename(fpath)
                print(f"  • {fname}")
            
            print(f"\n{YELLOW}💡 File {BOLD}SILO_BLUEPRINT.md{RESET}{YELLOW} telah otomatis diperbarui dengan internal link terbaru!{RESET}")
        except Exception as e:
            print(f"{RED}✖ Gagal menyimpan file: {e}{RESET}")

    press_any_key()

# ==========================================
# MENU 2: PUSH TO WORDPRESS (GLOBAL UNSENT)
# ==========================================
def menu_push_wordpress():
    clear_screen()
    print_banner()
    print_section("KIRIM ARTIKEL KE WORDPRESS (HANYA ARTIKEL BELUM DIKIRIM)")

    wp = WordPressPublisher()
    sites = wp.get_sites()

    if not sites:
        print(f"{YELLOW}⚠️  Belum ada website WordPress yang didaftarkan.{RESET}")
        print(f" [{CYAN}1{RESET}] Tambah Website WordPress Sekarang")
        print(f" [{CYAN}0{RESET}] Kembali ke Menu Utama")
        c = get_single_key(f"\nPilih [1/0]: ", valid_keys=['1', '0'])
        if c == "1":
            menu_add_website_flow(wp)
            sites = wp.get_sites()
            if not sites:
                return
        else:
            return

    # 1. Pindai artikel yang belum pernah dikirim secara GLOBAL
    print(f"{CYAN}Memindai folder output untuk artikel yang belum pernah dikirim ke web manapun...{RESET}")
    pending_articles, sent_articles = wp.scan_articles_global("output")

    print(f"• Total Artikel Sudah Terkirim (Global) : {BOLD}{GREEN}{len(sent_articles)}{RESET}")
    print(f"• Total Artikel {BOLD}Belum Terkirim (Pending){RESET}   : {BOLD}{YELLOW}{len(pending_articles)}{RESET}\n")

    if not pending_articles:
        print(f"{YELLOW}Semua artikel di folder 'output/' sudah pernah dikirim ke web.{RESET}")
        print(f"{DIM}Tidak ada artikel pending yang tersedia untuk dipublish.{RESET}")
        press_any_key()
        return

    # 2. Pilih Target Website
    target_site = None
    if len(sites) == 1:
        target_site = sites[0]
        type_tag = f"{CYAN}[Astro]{RESET}" if target_site.get("type") == "astro" else f"{MAGENTA}[WP]{RESET}"
        print(f"Website Target: {type_tag} {CYAN}{BOLD}{target_site['name']}{RESET} ({target_site.get('wp_url', '')})")
    else:
        active_id = wp.config.get("active_site_id")
        site_options = []
        default_site_idx = 0
        for i, s in enumerate(sites, 1):
            is_def = f" {GREEN}[Default]{RESET}" if s["id"] == active_id else ""
            type_tag = f"{CYAN}[Astro]{RESET}" if s.get("type") == "astro" else f"{MAGENTA}[WP]{RESET}"
            if s.get("type") == "astro":
                user_info = f" - Folder: {os.path.basename(s.get('content_dir', ''))}"
            else:
                user_info = f" - User: {s.get('username', 'admin')}"
            lbl = f"{type_tag} {BOLD}{s['name']}{RESET} ({s.get('wp_url', '')}){user_info}{is_def}"
            site_options.append((str(i), lbl))
            if s["id"] == active_id:
                default_site_idx = i - 1
        site_options.append(("0", "Kembali ke Menu Utama"))

        site_choice = select_menu(site_options, title="PILIH WEBSITE TARGET", default_index=default_site_idx)
        if site_choice == "0":
            return
        
        site_idx = int(site_choice) - 1
        target_site = sites[site_idx]
        type_tag = f"{CYAN}[Astro]{RESET}" if target_site.get("type") == "astro" else f"{MAGENTA}[WP]{RESET}"
        print(f"\nWebsite Target: {type_tag} {CYAN}{BOLD}{target_site['name']}{RESET} ({target_site.get('wp_url', '')})")

    # 3. Test koneksi ke target website
    print(f"\n{CYAN}Menguji koneksi ke {target_site['wp_url']}...{RESET}")
    ok, msg = wp.test_connection(target_site)
    if not ok:
        print(f"{RED}✖ {msg}{RESET}")
        print(f"{YELLOW}Silakan periksa kembali pengaturan website di Menu [6].{RESET}")
        press_any_key()
        return
    
    print(f"{GREEN}✔ {msg}{RESET}\n")

    # 4. Tampilkan daftar artikel pending
    print(f"{BOLD}DAFTAR ARTIKEL YANG BELUM DIKIRIM ({len(pending_articles)} Artikel):{RESET}")
    print(f"{BOLD}{'No':<4} {'Tema Silo':<20} {'Role':<10} {'Judul Artikel':<38} {'Skor'}{RESET}")
    print("-" * 78)

    for i, art in enumerate(pending_articles, 1):
        role_str = f"{MAGENTA}👑 Pillar{RESET}" if art["silo_role"].lower() == "pillar" else f"{CYAN}🔗 Cluster{RESET}"
        title_disp = (art["title"][:35] + '...') if len(art["title"]) > 35 else art["title"]
        silo_disp = (art["silo_theme"][:18] + '...') if len(art["silo_theme"]) > 18 else art["silo_theme"]
        score_disp = f"{art['curation_score']}/100" if art['curation_score'] != '-' else '-'
        print(f"{BOLD}#{i:<3}{RESET} {silo_disp:<20} {role_str:<18} {title_disp:<38} {score_disp}")

    print(f"\n{YELLOW}Pilihan Kirim:{RESET}")
    print(f" • Nomor artikel (contoh: {CYAN}1, 2{RESET} atau {CYAN}1-3{RESET})")
    print(f" • Ketik {CYAN}all{RESET} atau tekan {GREEN}[ENTER]{RESET} untuk SEMUA ({len(pending_articles)} artikel)")
    print(f" • Ketik {RED}0{RESET} untuk batal")
    
    choice = input(f"\n{BOLD}Pilih artikel yang akan dikirim (atau 0 untuk batal):{RESET} ").strip()
    if choice == "0":
        return

    if not choice:
        selected_indices = list(range(1, len(pending_articles) + 1))
    else:
        selected_indices = parse_user_selection(choice, len(pending_articles))

    if not selected_indices:
        print(f"{RED}Tidak ada artikel yang dipilih.{RESET}")
        press_any_key()
        return

    selected_to_send = [pending_articles[i - 1] for i in selected_indices]
    print(f"\n{GREEN}✔ Anda memilih {len(selected_to_send)} artikel untuk dikirim ke '{target_site['name']}'.{RESET}")

    # 5. Pilih status publish
    status_options = [
        ("1", "Draft (Simpan Draf)"),
        ("2", "Publish Langsung"),
        ("3", "Jadwalkan Terbit (Drip Feed)"),
        ("0", "Batal")
    ]
    status_key = select_menu(status_options, title="STATUS POSTINGAN WORDPRESS")
    if status_key == "0":
        return

    interval_hours = 12
    is_drip = (status_key == "3")
    if is_drip:
        int_input = input(f"\n{BOLD}Masukkan jeda waktu antar artikel dalam JAM [Default: 12 jam, misal: 6, 12, 24]:{RESET} ").strip()
        if int_input == "0":
            return
        try:
            interval_hours = float(int_input) if int_input else 12.0
            if interval_hours <= 0:
                interval_hours = 12.0
        except ValueError:
            interval_hours = 12.0
        post_status = "future"
        status_label = f"DRIP FEED (Tiap {interval_hours} Jam)"
    elif status_key == "2":
        post_status = "publish"
        status_label = "PUBLISH INSTAN"
    else:
        post_status = "draft"
        status_label = "DRAFT"

    confirm_char = get_single_key(f"\n{BOLD}Kirim {len(selected_to_send)} artikel sebagai '{status_label}' ke {target_site['wp_url']}? [Y/N atau 0]:{RESET} ", valid_keys=['y', 'n', '0', '\r', '\n'])
    if confirm_char.lower() in ['n', '0']:
        print(f"\n{YELLOW}Pengiriman dibatalkan.{RESET}")
        press_any_key()
        return

    # 6. Eksekusi pengiriman
    print_section(f"PROSES PENGIRIMAN KE '{target_site['name']}' ({status_label})")
    print(f"{CYAN}Fitur Otomatis Aktif:{RESET} {GREEN}✔ Rank Math & Yoast SEO Sync | ✔ Auto-Category Silo | ✔ Live Link Equity | ✔ FAQ Schema JSON-LD{RESET}\n")

    success_count = 0
    fail_count = 0
    base_time = datetime.now()

    for idx, art in enumerate(selected_to_send, 1):
        scheduled_dt = None
        if is_drip:
            # Artikel pertama terbit 1 jam dari sekarang (atau bertahap)
            scheduled_dt = base_time + timedelta(hours=idx * interval_hours)
            drip_info = f" (Jadwal: {scheduled_dt.strftime('%d-%m-%Y %H:%M')})"
        else:
            drip_info = ""

        print(f"[{idx}/{len(selected_to_send)}] Mengirim: '{art['title'][:35]}...' {drip_info}...", end="", flush=True)
        ok, res = wp.publish_article(art, target_site=target_site, status=post_status, scheduled_date=scheduled_dt)
        if ok:
            success_count += 1
            print(f" {GREEN}SUKSES!{RESET}")
            cat_str = f" | Cat ID: {res.get('category_id')}" if res.get('category_id') else ""
            print(f"     ↳ {DIM}ID: {res['post_id']} | Status: {res['status']}{cat_str} | URL: {res['post_url']}{RESET}")
        else:
            fail_count += 1
            print(f" {RED}GAGAL!{RESET}")
            print(f"     ↳ {RED}Error: {res}{RESET}")
        time.sleep(0.5)

    print(f"\n{GREEN}{BOLD}🎉 PENGIRIMAN SELESAI!{RESET}")
    print(f"• Berhasil dikirim ke {target_site['name']}: {GREEN}{success_count}{RESET}")
    print(f"• Gagal: {RED if fail_count > 0 else GREEN}{fail_count}{RESET}")
    print(f"\n{YELLOW}💡 Artikel yang berhasil dikirim telah ditandai secara GLOBAL dan tidak akan muncul lagi di antrean publish.{RESET}")
    press_any_key()

# ==========================================
# MENU 3: EXPORT SILO TO WORDPRESS XML (WXR)
# ==========================================
def menu_export_silo_wxr():
    clear_screen()
    print_banner()
    print_section("EXPORT SILO KE FORMAT WORDPRESS XML (WXR)")

    output_dir = "output"
    if not os.path.exists(output_dir):
        print(f"{YELLOW}Belum ada folder 'output/' atau artikel Silo yang dibuat.{RESET}")
        press_any_key()
        return

    # Cari semua folder Silo di output/
    silo_folders = []
    for item in os.listdir(output_dir):
        item_path = os.path.join(output_dir, item)
        if os.path.isdir(item_path):
            md_files = [f for f in os.listdir(item_path) if f.endswith(".md") and f != "SILO_BLUEPRINT.md"]
            if md_files:
                meta_file = os.path.join(item_path, "silo_metadata.json")
                silo_title = item
                if os.path.exists(meta_file):
                    try:
                        with open(meta_file, "r", encoding="utf-8") as f:
                            m = json.load(f)
                            silo_title = m.get("silo_theme", item)
                    except Exception:
                        pass
                silo_folders.append({
                    "path": item_path,
                    "folder_name": item,
                    "theme": silo_title,
                    "article_count": len(md_files)
                })

    if not silo_folders:
        print(f"{YELLOW}Tidak ditemukan folder Silo yang berisi artikel di '{output_dir}/'.{RESET}")
        press_any_key()
        return

    options = []
    for i, s in enumerate(silo_folders, 1):
        lbl = f"{BOLD}{s['theme']}{RESET} ({CYAN}{s['article_count']} Artikel{RESET} di `{s['folder_name']}`)"
        options.append((str(i), lbl))
    options.append(("0", "Kembali ke Menu Utama"))

    choice = select_menu(options, title="PILIH PROYEK UNTUK EXPORT XML")
    if choice == "0":
        return

    selected = silo_folders[int(choice) - 1]
    wp = WordPressPublisher()

    print(f"\n{CYAN}Sedang mengompilasi {selected['article_count']} artikel menjadi format WordPress XML (WXR 1.2)...{RESET}")
    try:
        xml_path, count, theme = wp.export_silo_to_wxr(selected["path"])
        fsize_kb = os.path.getsize(xml_path) / 1024
        print(f"\n{GREEN}{BOLD}🎉 EXPORT WORDPRESS XML BERHASIL!{RESET}")
        print(f"📁 Lokasi File  : {CYAN}{BOLD}{xml_path}{RESET}")
        print(f"📊 Total Artikel: {BOLD}{count} artikel{RESET}")
        print(f"📦 Ukuran File  : {BOLD}{fsize_kb:.1f} KB{RESET}")
        print(f"\n{YELLOW}💡 Cara Import ke WordPress:{RESET}")
        print(f" 1. Buka WP Admin ➔ {BOLD}Tools ➔ Import{RESET}")
        print(f" 2. Pilih {BOLD}WordPress{RESET} (Run Importer)")
        print(f" 3. Upload file: {CYAN}{os.path.basename(xml_path)}{RESET}")
        print(f" 4. Klik {BOLD}'Submit'{RESET} ➔ Artikel & meta SEO otomatis terpasang!")
    except Exception as e:
        print(f"\n{RED}✖ Gagal export XML: {e}{RESET}")

    press_any_key()

# ==========================================
# MENU: VIEW INVENTORY / STATUS
# ==========================================
def menu_view_inventory():
    clear_screen()
    print_banner()
    print_section("INVENTORI ARTIKEL SILO")

    wp = WordPressPublisher()
    pending, sent = wp.scan_articles_global("output")

    total = len(pending) + len(sent)
    print(f"📊 {BOLD}Ringkasan Inventori Global:{RESET}")
    print(f" • Total Artikel Dibuat          : {BOLD}{total}{RESET}")
    print(f" • Belum Dikirim (Pending Global): {BOLD}{YELLOW}{len(pending)}{RESET}")
    print(f" • Sudah Terkirim ke Web (Sent)  : {BOLD}{GREEN}{len(sent)}{RESET}\n")

    if pending:
        print(f"{YELLOW}{BOLD}📋 DAFTAR ARTIKEL PENDING (BELUM PERNAH DIKIRIM KE WEB MANAPUN):{RESET}")
        print(f"{BOLD}{'No':<4} {'Tema Silo':<20} {'Role':<10} {'Judul Artikel':<38} {'Skor'}{RESET}")
        print("-" * 78)
        for i, art in enumerate(pending, 1):
            role_str = f"{MAGENTA}👑 Pillar{RESET}" if art["silo_role"].lower() == "pillar" else f"{CYAN}🔗 Cluster{RESET}"
            title_disp = (art["title"][:35] + '...') if len(art["title"]) > 35 else art["title"]
            silo_disp = (art["silo_theme"][:18] + '...') if len(art["silo_theme"]) > 18 else art["silo_theme"]
            score_disp = f"{art['curation_score']}/100" if art['curation_score'] != '-' else '-'
            print(f"#{i:<3} {silo_disp:<20} {role_str:<18} {title_disp:<38} {score_disp}")

    if sent:
        print(f"\n{GREEN}{BOLD}✅ DAFTAR ARTIKEL YANG SUDAH DIKIRIM KE WEB:{RESET}")
        print(f"{BOLD}{'No':<4} {'Judul Artikel':<33} {'Target Web':<18} {'WP ID':<8} {'Waktu Kirim'}{RESET}")
        print("-" * 78)
        for i, art in enumerate(sent, 1):
            wp_info = art.get("wp_info", {})
            title_disp = (art["title"][:30] + '...') if len(art["title"]) > 30 else art["title"]
            sname = str(wp_info.get("site_name", "WordPress"))
            pid = str(wp_info.get("post_id", "-"))
            p_time = str(wp_info.get("published_at", "-"))
            print(f"#{i:<3} {title_disp:<33} {sname:<18} {pid:<8} {p_time}")

    if total == 0:
        print(f"{DIM}Belum ada artikel yang dibuat. Gunakan Menu [1] untuk membuat artikel Silo baru.{RESET}")

    press_any_key("Tekan tombol apa saja (atau 0) untuk kembali ke Menu Utama...")

# ==========================================
# MENU: CONFIGURE MULTI-SITE & LIVE WP MANAGER
# ==========================================
def menu_configure_wordpress():
    while True:
        clear_screen()
        print_banner()
        print_section("PENGATURAN WEBSITE")

        wp = WordPressPublisher()
        sites = wp.get_sites()
        active_id = wp.config.get("active_site_id")

        if not sites:
            print(f"{YELLOW}Belum ada website yang terdaftar.{RESET}\n")
        else:
            print(f"{BOLD}Daftar Website ({len(sites)} Web):{RESET}")
            print(f"{BOLD}{'No':<4} {'Tipe':<8} {'Nama Website':<22} {'URL / Path':<30} {'Status'}{RESET}")
            print("-" * 75)
            for i, s in enumerate(sites, 1):
                badge = f"{GREEN}[Aktif]{RESET}" if s["id"] == active_id else ""
                type_tag = f"{CYAN}[Astro]{RESET}" if s.get("type") == "astro" else f"{MAGENTA}[WP]{RESET}"
                s_name = (s["name"][:20] + '..') if len(s["name"]) > 20 else s["name"]
                s_url = s.get("wp_url", "")
                if s.get("type") == "astro":
                    s_url = (s.get("content_dir", "")[:28] + '..') if len(s.get("content_dir", "")) > 28 else s.get("content_dir", "")
                else:
                    s_url = (s_url[:28] + '..') if len(s_url) > 28 else s_url
                print(f"#{i:<3} {type_tag:<17} {BOLD}{s_name:<22}{RESET} {s_url:<30} {badge}")
            print("")

        options = [
            ("1", "Tambah Website Baru"),
            ("2", "Ganti Website Default"),
            ("3", "Uji Koneksi Website"),
            ("4", "Kelola Postingan Live WP"),
            ("5", "Kelola Kategori Live WP"),
            ("6", "Kelola Profil Bisnis Website (NAP, Tarif, Kontak, Legalitas)"),
            ("7", "Edit Data Website"),
            ("8", "Hapus Website"),
            ("0", "Kembali ke Menu Utama")
        ]
        opt = select_menu(options, title="PENGATURAN WEBSITE")

        if opt == "1":
            menu_add_website_flow(wp)
        elif opt == "2":
            menu_set_active_site(wp)
        elif opt == "3":
            menu_test_site_connection(wp)
        elif opt == "4":
            menu_manage_live_wp(wp)
        elif opt == "5":
            menu_manage_wp_categories(wp)
        elif opt == "6":
            menu_manage_site_profiles(wp)
        elif opt == "7":
            menu_edit_website_flow(wp)
        elif opt == "8":
            menu_delete_website_flow(wp)
        elif opt == "0":
            break

def menu_add_website_flow(wp):
    add_options = [
        ("1", "WordPress (REST API)"),
        ("2", "Static Astro / Cloudflare / Netlify"),
        ("0", "Batal")
    ]
    type_choice = select_menu(add_options, title="PILIH TIPE WEBSITE")
    if type_choice == "0":
        return

    if type_choice == "1":
        print_section("TAMBAH WEBSITE WORDPRESS BARU")
        print(f"{DIM}Ketik '0' untuk batal.{RESET}\n")

        name = input(f"{BOLD}Nama / Label Website (misal: 'Blog Kopi Jogja'):{RESET} ").strip()
        if name == "0":
            return

        url = input(f"{BOLD}URL Website WordPress (misal: https://domainanda.com):{RESET} ").strip()
        if url == "0":
            return

        user = input(f"{BOLD}Username WordPress:{RESET} ").strip()
        if user == "0":
            return

        pwd = input(f"{BOLD}Application Password (16 karakter):{RESET} ").strip()
        if pwd == "0":
            return

        if not (url and user and pwd):
            print(f"{RED}URL, Username, dan Application Password wajib diisi.{RESET}")
            press_any_key()
            return

        new_site = wp.add_site(name=name, wp_url=url, username=user, app_password=pwd)
        print(f"\n{GREEN}✔ Website '{new_site['name']}' berhasil ditambahkan!{RESET}")

        print(f"{CYAN}Menguji koneksi ke {new_site['wp_url']}...{RESET}")
        ok, msg = wp.test_connection(new_site)
        if ok:
            print(f"{GREEN}✔ {msg}{RESET}")
        else:
            print(f"{YELLOW}⚠️ {msg}{RESET}")

        press_any_key()

    elif type_choice == "2":
        print_section("TAMBAH WEBSITE STATIK ASTRO (CLOUDFLARE PAGES / NETLIFY)")
        print(f"{DIM}Ketik '0' untuk batal.{RESET}\n")

        name = input(f"{BOLD}Nama / Label Website (misal: 'Astro Blog Jogja'):{RESET} ").strip()
        if name == "0":
            return

        content_dir = input(f"{BOLD}Path Folder Content Astro (misal: C:/Projects/my-astro/src/content/blog):{RESET} ").strip()
        if content_dir == "0":
            return
        while not content_dir:
            content_dir = input(f"{YELLOW}Folder content wajib diisi:{RESET} ").strip()
            if content_dir == "0":
                return

        img_dir = input(f"{BOLD}Path Folder Image Astro [Kosongkan untuk auto-detect di public/images/silo]:{RESET} ").strip()
        if img_dir == "0":
            return

        live_url = input(f"{BOLD}Domain / URL Live [Opsional, misal: https://myblog.pages.dev]:{RESET} ").strip()
        if live_url == "0":
            return

        auto_git_char = get_single_key(f"\n{BOLD}Aktifkan Git Auto-Commit & Push saat publish? [Y/N]:{RESET} ", valid_keys=['y', 'n', '0'])
        auto_git = (auto_git_char.lower() == 'y')

        new_site = wp.add_astro_site(
            name=name,
            content_dir=content_dir,
            image_dir=img_dir if img_dir else None,
            site_url=live_url if live_url else None,
            auto_git=auto_git
        )
        print(f"\n{GREEN}✔ Website Astro '{new_site['name']}' berhasil ditambahkan!{RESET}")

        print(f"{CYAN}Memverifikasi folder Astro & status Git...{RESET}")
        ok, msg = wp.test_connection(new_site)
        if ok:
            print(f"{GREEN}✔ {msg}{RESET}")
        else:
            print(f"{YELLOW}⚠️ {msg}{RESET}")

        press_any_key()

def menu_set_active_site(wp):
    sites = wp.get_sites()
    if not sites:
        print(f"{YELLOW}Belum ada website yang didaftarkan.{RESET}")
        press_any_key()
        return

    active_id = wp.config.get("active_site_id")
    options = []
    default_idx = 0
    for i, s in enumerate(sites, 1):
        is_def = f" {GREEN}[Aktif]{RESET}" if s["id"] == active_id else ""
        type_tag = f"{CYAN}[Astro]{RESET}" if s.get("type") == "astro" else f"{MAGENTA}[WP]{RESET}"
        options.append((str(i), f"{type_tag} {s['name']} ({s.get('wp_url', '')}){is_def}"))
        if s["id"] == active_id:
            default_idx = i - 1
    options.append(("0", "↩️  Kembali"))
    
    choice = select_menu(options, title="GANTI WEBSITE DEFAULT / AKTIF", default_index=default_idx)
    if choice == "0":
        return

    idx = int(choice) - 1
    wp.set_active_site(sites[idx]["id"])
    print(f"\n{GREEN}✔ Website default diubah menjadi: '{sites[idx]['name']}'{RESET}")
    press_any_key()

def menu_test_site_connection(wp):
    sites = wp.get_sites()
    if not sites:
        print(f"{YELLOW}Belum ada website yang didaftarkan.{RESET}")
        press_any_key()
        return

    options = [("A", f"🌐 {BOLD}Uji Semua Website Sekaligus{RESET}")]
    for i, s in enumerate(sites, 1):
        type_tag = f"{CYAN}[Astro]{RESET}" if s.get("type") == "astro" else f"{MAGENTA}[WP]{RESET}"
        options.append((str(i), f"{type_tag} {s['name']} ({s.get('wp_url', '')})"))
    options.append(("0", "↩️  Kembali"))

    c = select_menu(options, title="UJI KONEKSI WEBSITE (WORDPRESS & ASTRO)")
    if c == "0":
        return

    if c.lower() == "a":
        for s in sites:
            print(f"\n{CYAN}Menguji '{s['name']}' ({s.get('wp_url', '')})...{RESET}")
            ok, msg = wp.test_connection(s)
            if ok:
                print(f"{GREEN}✔ {msg}{RESET}")
            else:
                print(f"{RED}✖ {msg}{RESET}")
    else:
        idx = int(c) - 1
        s = sites[idx]
        print(f"\n{CYAN}Menguji '{s['name']}' ({s.get('wp_url', '')})...{RESET}")
        ok, msg = wp.test_connection(s)
        if ok:
            print(f"{GREEN}✔ {msg}{RESET}")
        else:
            print(f"{RED}✖ {msg}{RESET}")

    press_any_key()

def menu_edit_website_flow(wp):
    sites = wp.get_sites()
    if not sites:
        print(f"{YELLOW}Belum ada website yang didaftarkan.{RESET}")
        press_any_key()
        return

    options = [(str(i), f"{s['name']} ({s.get('wp_url', '')})") for i, s in enumerate(sites, 1)]
    options.append(("0", "↩️  Kembali"))

    c = select_menu(options, title="EDIT DATA WEBSITE")
    if c == "0":
        return

    idx = int(c) - 1
    target = sites[idx]

    print(f"\n{DIM}Tekan Enter langsung jika tidak ingin mengubah field tertentu (Ketik 0 untuk batal).{RESET}")
    new_name = input(f"Nama Website [{target['name']}]: ").strip()
    if new_name == "0":
        return

    new_url = input(f"URL Website [{target.get('wp_url', '')}]: ").strip()
    if new_url == "0":
        return

    if target.get("type") == "astro":
        new_cdir = input(f"Content Folder [{target.get('content_dir', '')}]: ").strip()
        if new_cdir == "0":
            return
        new_idir = input(f"Image Folder [{target.get('image_dir', '')}]: ").strip()
        if new_idir == "0":
            return
        wp.update_site(
            target["id"],
            name=new_name if new_name else None,
            wp_url=new_url if new_url else None,
            content_dir=new_cdir if new_cdir else None,
            image_dir=new_idir if new_idir else None
        )
    else:
        new_user = input(f"Username [{target.get('username', '')}]: ").strip()
        if new_user == "0":
            return
        new_pwd = input(f"App Password [Biarkan kosong jika tidak diubah]: ").strip()
        if new_pwd == "0":
            return
        wp.update_site(
            target["id"],
            name=new_name if new_name else None,
            wp_url=new_url if new_url else None,
            username=new_user if new_user else None,
            app_password=new_pwd if new_pwd else None
        )

    print(f"\n{GREEN}✔ Data website berhasil diperbarui!{RESET}")
    press_any_key()

def menu_delete_website_flow(wp):
    sites = wp.get_sites()
    if not sites:
        print(f"{YELLOW}Belum ada website yang didaftarkan.{RESET}")
        press_any_key()
        return

    options = [(str(i), f"{s['name']} ({s.get('wp_url', '')})") for i, s in enumerate(sites, 1)]
    options.append(("0", "↩️  Kembali"))

    c = select_menu(options, title="HAPUS WEBSITE")
    if c == "0":
        return

    idx = int(c) - 1
    target = sites[idx]
    
    confirm = get_single_key(f"\n{RED}Yakin ingin menghapus website '{target['name']}'? [Y/N atau 0]: {RESET}", valid_keys=['y', 'n', '0'])
    if confirm.lower() == "y":
        wp.delete_site(target["id"])
        print(f"\n{GREEN}✔ Website '{target['name']}' berhasil dihapus.{RESET}")
    else:
        print(f"\n{YELLOW}Penghapusan dibatalkan.{RESET}")

    press_any_key()

# ==========================================
# WEBSITE BUSINESS PROFILE & GROUNDING UI
# ==========================================
def menu_manage_site_profiles(wp):
    while True:
        sites = wp.get_sites()
        if not sites:
            print(f"{YELLOW}Belum ada website yang didaftarkan.{RESET}")
            press_any_key()
            return

        options = []
        for i, s in enumerate(sites, 1):
            prof = s.get("profile", {})
            brand = prof.get("brand_name", "")
            type_tag = f"{CYAN}[Astro]{RESET}" if s.get("type") == "astro" else f"{MAGENTA}[WP]{RESET}"
            if brand:
                status_tag = f"{GREEN}✔ Terisi: {brand}{RESET}"
            else:
                status_tag = f"{YELLOW}⚠️ Belum Diisi{RESET}"
            options.append((str(i), f"{type_tag} {s['name']} - {status_tag}"))
        options.append(("0", "↩️  Kembali"))

        c = select_menu(options, title="KELOLA PROFIL BISNIS WEBSITE (GROUNDING KNOWLEDGE)")
        if c == "0":
            break

        idx = int(c) - 1
        target_site = sites[idx]
        manage_single_site_profile_flow(wp, target_site)

def manage_single_site_profile_flow(wp, site):
    fields_def = [
        ("brand_name", "Nama Brand / Bisnis", "Spotty Soil Test"),
        ("niche", "Niche / Bidang Usaha", "Jasa Sondir & Uji Tanah"),
        ("tagline", "Tagline / Slogan", "Ahli Uji Tanah Terpercaya & Akurat"),
        ("address", "Alamat Kantor / Base", "Jl. Ringroad Barat No. 88, Yogyakarta"),
        ("service_area", "Wilayah / Area Layanan", "Yogyakarta, Solo, Semarang, Jawa Tengah"),
        ("phone_wa", "Nomor WhatsApp Resmi (CTA)", "0812-3456-7890"),
        ("email", "Email Resmi", "info@spottysoil.com"),
        ("legalities", "Legalitas / NIB / Sertifikasi", "NIB: 1234567890, Anggota HATTI"),
        ("pricing_services", "Layanan & Tarif Resmi", "Sondir 2.5 Ton (Rp 1,5 Jt/titik), Boring SPT (Rp 350rb/m)"),
        ("usp_strengths", "Keunggulan Utama (USP)", "Alat kalibrasi resmi, laporan cepat 2x24 jam, teknisi bersertifikat"),
        ("cta_message", "Pesan Call to Action (CTA)", "Hubungi WhatsApp 0812-3456-7890 untuk konsultasi & penawaran terbaik!"),
        ("custom_notes", "Catatan Khusus AI (Grounding)", "Jangan pernah sebut diskon lebih dari 10%, fokus pada keamanan konstruksi")
    ]

    while True:
        clear_screen()
        print_banner()
        print_section(f"PROFIL BISNIS: {site['name']}")
        print(f"🌐 {BOLD}URL / Path:{RESET} {site.get('wp_url', site.get('content_dir', ''))}\n")

        prof = site.get("profile", {})
        has_any = any(str(v).strip() for v in prof.values() if v) if prof else False

        if not has_any:
            print(f"{YELLOW}⚠️  Profil bisnis untuk website ini masih KOSONG.{RESET}")
            print(f"{DIM}Artikel akan menggunakan mode Standar Industri Obyektif & Edukatif.{RESET}\n")
        else:
            print(f"{BOLD}Data Profil Bisnis Resmi (Ground Truth Knowledge):{RESET}")
            for key, label, _ in fields_def:
                val = prof.get(key, "")
                val_display = f"{GREEN}{val}{RESET}" if val else f"{DIM}(Kosong){RESET}"
                print(f" • {BOLD}{label:<32}:{RESET} {val_display}")
            print("")

        options = [
            ("1", "📝 Isi / Perbarui Seluruh Profil (Wizard Berurutan)"),
            ("2", "✏️  Edit Field Tertentu"),
            ("3", "🗑️  Kosongkan / Reset Profil"),
            ("0", "↩️  Kembali")
        ]

        action = select_menu(options, title="PILIH AKSI PROFIL")
        if action == "0":
            break
        elif action == "1":
            print_section(f"WIZARD PROFIL BISNIS: {site['name']}")
            print(f"{DIM}Tekan [ENTER] langsung untuk mempertahankan nilai lama. Ketik '-' untuk mengosongkan. Ketik '0' untuk batal.{RESET}\n")
            new_prof = dict(prof) if prof else {}
            cancelled = False

            for key, label, example in fields_def:
                cur_val = new_prof.get(key, "")
                prompt_str = f"{BOLD}{label}{RESET}\n{DIM}[Contoh: {example}]{RESET}\n[Nilai saat ini: {CYAN}{cur_val if cur_val else 'Kosong'}{RESET}]: "
                val_in = input(prompt_str).strip()
                if val_in == "0":
                    cancelled = True
                    break
                if val_in == "-":
                    new_prof[key] = ""
                elif val_in:
                    new_prof[key] = val_in
                print("")

            if not cancelled:
                wp.update_site_profile(site["id"], new_prof)
                site["profile"] = new_prof
                print(f"{GREEN}✔ Profil bisnis '{site['name']}' berhasil diperbarui!{RESET}")
                press_any_key()
            else:
                print(f"{YELLOW}Pengeditan wizard dibatalkan.{RESET}")
                press_any_key()

        elif action == "2":
            field_opts = []
            for i, (key, label, _) in enumerate(fields_def, 1):
                cur_val = prof.get(key, "") if prof else ""
                short_val = (cur_val[:30] + '..') if len(cur_val) > 30 else (cur_val if cur_val else '-')
                field_opts.append((str(i), f"{label} ({DIM}{short_val}{RESET})"))
            field_opts.append(("0", "↩️  Batal"))

            f_choice = select_menu(field_opts, title="PILIH FIELD YANG INGIN DIEDIT")
            if f_choice == "0":
                continue

            f_idx = int(f_choice) - 1
            f_key, f_label, f_example = fields_def[f_idx]
            new_prof = dict(prof) if prof else {}
            cur_val = new_prof.get(f_key, "")

            print_section(f"EDIT: {f_label}")
            print(f"{DIM}Contoh: {f_example}{RESET}")
            print(f"{DIM}Ketik '-' untuk mengosongkan, atau 0 untuk batal.{RESET}\n")
            val_in = input(f"[Nilai saat ini: {CYAN}{cur_val if cur_val else 'Kosong'}{RESET}]\n{BOLD}Nilai baru:{RESET} ").strip()

            if val_in == "0":
                continue
            if val_in == "-":
                new_prof[f_key] = ""
            elif val_in:
                new_prof[f_key] = val_in

            wp.update_site_profile(site["id"], new_prof)
            site["profile"] = new_prof
            print(f"\n{GREEN}✔ Field '{f_label}' berhasil diperbarui!{RESET}")
            press_any_key()

        elif action == "3":
            confirm = get_single_key(f"\n{RED}Yakin ingin MENGOSONGKAN seluruh data profil bisnis '{site['name']}'? [Y/N atau 0]: {RESET}", valid_keys=['y', 'n', '0'])
            if confirm.lower() == 'y':
                wp.update_site_profile(site["id"], {})
                site["profile"] = {}
                print(f"\n{GREEN}✔ Profil bisnis berhasil direset ke mode Standar Industri Obyektif.{RESET}")
                press_any_key()
def select_wp_site_if_multiple(wp, action_title="PILIH WEBSITE TARGET"):
    sites = [s for s in wp.get_sites() if s.get("type") != "astro"]
    if not sites:
        print(f"{YELLOW}Belum ada website WordPress yang terdaftar.{RESET}")
        press_any_key()
        return None
    
    if len(sites) == 1:
        return sites[0]

    active_id = wp.config.get("active_site_id")
    options = []
    default_idx = 0
    for i, s in enumerate(sites, 1):
        is_active = f" {GREEN}[Aktif]{RESET}" if s["id"] == active_id else ""
        options.append((str(i), f"{s['name']} ({s.get('wp_url', '')}){is_active}"))
        if s["id"] == active_id:
            default_idx = i - 1
    options.append(("0", "Kembali"))

    c = select_menu(options, title=action_title, default_index=default_idx)
    if c == "0":
        return None
    return sites[int(c) - 1]

def menu_manage_live_wp(wp=None):
    if wp is None:
        wp = WordPressPublisher()

    target_site = select_wp_site_if_multiple(wp, "PILIH WEBSITE WORDPRESS")
    if not target_site:
        return

    status_filter = "any"
    search_keyword = ""
    current_page = 1
    per_page = 10

    while True:
        clear_screen()
        print_banner()
        print_section(f"KELOLA POSTINGAN: {target_site['name']}")
        print(f"🌐 {BOLD}URL:{RESET} {target_site['wp_url']} | {BOLD}Status:{RESET} {CYAN}{status_filter.upper()}{RESET} | {BOLD}Cari:{RESET} {YELLOW}{search_keyword if search_keyword else '(Semua)'}{RESET}")
        print(f"{DIM}Memuat data dari WordPress REST API...{RESET}\n")

        ok, posts, total_posts, total_pages = wp.get_live_posts(
            target_site=target_site,
            status=status_filter,
            per_page=per_page,
            page=current_page,
            search=search_keyword
        )

        if not ok:
            print(f"{RED}✖ Gagal mengambil postingan: {posts}{RESET}")
            press_any_key()
            break

        if not posts:
            print(f"{YELLOW}Tidak ditemukan artikel dengan filter saat ini.{RESET}\n")
        else:
            print(f"{BOLD}Daftar Post (Hal {current_page}/{max(1, total_pages)} - Total {total_posts} Post):{RESET}")
            print(f"{BOLD}{'No':<4} {'ID':<8} {'Status':<12} {'Tanggal':<12} {'Judul Artikel'}{RESET}")
            print("-" * 75)
            
            for i, p in enumerate(posts, 1):
                p_id = p.get("id", "-")
                p_status = p.get("status", "unknown")
                if p_status == "publish":
                    status_badge = f"{GREEN}Published{RESET}"
                elif p_status == "draft":
                    status_badge = f"{YELLOW}Draft{RESET}"
                elif p_status == "future":
                    status_badge = f"{CYAN}Scheduled{RESET}"
                elif p_status == "trash":
                    status_badge = f"{RED}Trash{RESET}"
                else:
                    status_badge = f"{DIM}{p_status}{RESET}"

                raw_title = p.get("title", {}).get("rendered", "Tanpa Judul")
                clean_title = clean_text_for_rendering(raw_title)
                if len(clean_title) > 40:
                    clean_title = clean_title[:38] + ".."

                raw_date = p.get("date", "")[:10]
                print(f"#{i:<3} {str(p_id):<8} {status_badge:<21} {raw_date:<12} {BOLD}{clean_title}{RESET}")
            print("-" * 75)

        # Action options
        options = []
        for i in range(1, len(posts) + 1):
            options.append((str(i), f"Pilih Post #{i} (ID: {posts[i-1]['id']})"))

        if total_pages > current_page:
            options.append(("N", f"Halaman Berikutnya (Next -> {current_page + 1}/{total_pages})"))
        if current_page > 1:
            options.append(("P", f"Halaman Sebelumnya (Prev <- {current_page - 1}/{total_pages})"))

        options.append(("F", "Filter Status (All/Publish/Draft/Scheduled/Trash)"))
        options.append(("S", "Cari Kata Kunci / Judul"))
        if search_keyword:
            options.append(("R", "Reset Pencarian"))
        options.append(("0", "Kembali"))

        c = select_menu(options, title="PILIH AKSI POSTINGAN")

        if c == "0":
            break
        elif c.upper() == "N" and current_page < total_pages:
            current_page += 1
        elif c.upper() == "P" and current_page > 1:
            current_page -= 1
        elif c.upper() == "F":
            f_opts = [
                ("1", "Semua Status (All)"),
                ("2", "Published"),
                ("3", "Draft"),
                ("4", "Scheduled"),
                ("5", "Trash"),
                ("0", "Batal")
            ]
            fc = select_menu(f_opts, title="FILTER STATUS POST")
            if fc == "1": status_filter = "any"
            elif fc == "2": status_filter = "publish"
            elif fc == "3": status_filter = "draft"
            elif fc == "4": status_filter = "future"
            elif fc == "5": status_filter = "trash"
            current_page = 1
        elif c.upper() == "S":
            kw = input(f"\n{BOLD}Kata kunci pencarian (0 untuk batal):{RESET} ").strip()
            if kw != "0" and kw:
                search_keyword = kw
                current_page = 1
        elif c.upper() == "R":
            search_keyword = ""
            current_page = 1
        elif c.isdigit() and 1 <= int(c) <= len(posts):
            selected_post = posts[int(c) - 1]
            menu_single_post_detail(wp, target_site, selected_post)

def menu_single_post_detail(wp, target_site, post_summary):
    post_id = post_summary.get("id")
    
    while True:
        clear_screen()
        print_banner()
        print_section(f"DETAIL POST #{post_id}")

        ok, post_data = wp.get_single_live_post(post_id, target_site)
        if not ok:
            print(f"{RED}✖ Gagal mengambil detail: {post_data}{RESET}\n")
            press_any_key()
            break

        title = clean_text_for_rendering(post_data.get("title", {}).get("rendered", "-"))
        slug = post_data.get("slug", "-")
        status = post_data.get("status", "-")
        date_str = post_data.get("date", "-")
        modified_str = post_data.get("modified", "-")
        link = post_data.get("link", "-")

        cat_names = []
        try:
            terms = post_data.get("_embedded", {}).get("wp:term", [])
            for term_list in terms:
                for term in term_list:
                    if term.get("taxonomy") == "category":
                        cat_names.append(term.get("name"))
        except Exception:
            pass
        cat_str = ", ".join(cat_names) if cat_names else "(Default)"

        meta = post_data.get("meta", {})
        rm_kw = meta.get("rank_math_focus_keyword") or meta.get("_yoast_wpseo_focuskw") or "-"

        print(f"📌 {BOLD}Judul Post   :{RESET} {CYAN}{BOLD}{title}{RESET}")
        print(f"🔗 {BOLD}URL Link     :{RESET} {link}")
        print(f"🏷️  {BOLD}Kategori     :{RESET} {cat_str}")
        print(f"📊 {BOLD}Status Live  :{RESET} {GREEN if status == 'publish' else YELLOW}{BOLD}{status.upper()}{RESET}")
        print(f"📅 {BOLD}Tanggal      :{RESET} {date_str} (Update: {modified_str})")
        if rm_kw != "-":
            print(f"🎯 {BOLD}Focus Keyword:{RESET} {GREEN}{rm_kw}{RESET}")
        print("-" * 75)

        options = [
            ("1", "Buka di Browser"),
            ("2", "Ubah Status Post (Publish/Draft/Private/Pending)"),
            ("3", "Edit Judul Postingan"),
            ("4", "Update / Ganti Featured Image (Thumbnail Baru)"),
            ("5", "Update Isi Konten (Sinkronisasi dari File Markdown Lokal)"),
            ("6", "Pindahkan ke Trash"),
            ("7", "Hapus Permanen"),
            ("0", "Kembali ke Daftar Post")
        ]

        action = select_menu(options, title="AKSI POSTINGAN")

        if action == "0":
            break
        elif action == "1":
            try:
                webbrowser.open(link)
                print(f"\n{GREEN}✔ Membuka di browser: {link}{RESET}")
            except Exception as e:
                print(f"{YELLOW}Gagal membuka browser: {e}{RESET}")
            press_any_key()
        elif action == "2":
            status_opts = [
                ("1", "Publish (Terbitkan Langsung)"),
                ("2", "Draft (Simpan Draf)"),
                ("3", "Pending Review"),
                ("4", "Private"),
                ("0", "Batal")
            ]
            st_choice = select_menu(status_opts, title=f"UBAH STATUS POST #{post_id}")
            new_st = None
            if st_choice == "1": new_st = "publish"
            elif st_choice == "2": new_st = "draft"
            elif st_choice == "3": new_st = "pending"
            elif st_choice == "4": new_st = "private"

            if new_st:
                print(f"\n{CYAN}Mengubah status ke '{new_st}'...{RESET}")
                ok_u, msg_u = wp.update_post_status(post_id, new_st, target_site)
                if ok_u:
                    print(f"{GREEN}✔ {msg_u}{RESET}")
                else:
                    print(f"{RED}✖ {msg_u}{RESET}")
                press_any_key()

        elif action == "3":
            print_section(f"EDIT JUDUL POST #{post_id}")
            print(f"Judul saat ini: {CYAN}{title}{RESET}\n")
            new_title = input(f"{BOLD}Masukkan judul baru (0 untuk batal):{RESET} ").strip()
            if new_title and new_title != "0":
                print(f"\n{CYAN}Memperbarui judul di WordPress...{RESET}")
                ok_u, res_u = wp.update_live_post(post_id, {"title": new_title}, target_site)
                if ok_u:
                    print(f"{GREEN}✔ Judul artikel #{post_id} berhasil diperbarui menjadi: {BOLD}{new_title}{RESET}")
                else:
                    print(f"{RED}✖ Gagal update judul: {res_u}{RESET}")
                press_any_key()

        elif action == "4":
            print_section(f"GANTI FEATURED IMAGE POST #{post_id}")
            print(f"📌 {BOLD}Artikel:{RESET} {CYAN}{title}{RESET}\n")
            
            img_menu_opts = [
                ("1", "Generate Otomatis Sekarang (Kie.ai AI Photo / Mesh Gradient) -> Pasang ke Live"),
                ("2", "Pilih File Gambar yang Sudah Ada di Komputer / Folder Silo"),
                ("0", "Batal")
            ]
            img_choice = select_menu(img_menu_opts, title=f"OPSI FEATURED IMAGE POST #{post_id}")
            
            if img_choice == "1":
                kie = KieImageClient()
                current_mode = kie.get_image_mode()
                mode_names = {
                    "hybrid": "Hybrid (Kie.ai AI Photo + Fallback Mesh Gradient)",
                    "mesh_gradient": "Always Mesh Gradient (Lokal & Cepat)",
                    "kie_only": "Kie.ai Photo Saja"
                }
                print_section("GENERATE & PASANG FEATURED IMAGE")
                print(f"⚙️  Mode Gambar: {CYAN}{BOLD}{mode_names.get(current_mode, current_mode)}{RESET}\n")
                
                kw_use = rm_kw if (rm_kw and rm_kw != "-") else title
                cat_use = cat_names[0] if cat_names else "WordPress Article"
                from silo_generator import slugify
                clean_slug = slug if (slug and slug != "-") else slugify(title)
                
                temp_dir = os.path.join("output", "temp_images")
                os.makedirs(temp_dir, exist_ok=True)
                temp_img_path = os.path.join(temp_dir, f"wp_{post_id}_{clean_slug}.webp")
                
                print(f"🎨 {BOLD}[1/2] Sedang men-generate gambar...{RESET}", end="", flush=True)
                try:
                    gemini_c = GeminiClient(key_file="apikey.txt")
                    saved_path, method_used = kie.generate_featured_image_auto(
                        title=title,
                        keyword=kw_use,
                        category=cat_use,
                        save_path=temp_img_path,
                        gemini_client=gemini_c
                    )
                    st_label = kie.get_image_style().replace("_", " ").title()
                    method_tag = f"{GREEN}Kie.ai ({st_label}){RESET}" if method_used == "kie_ai" else f"{CYAN}Mesh Gradient Card{RESET}"
                    print(f" {GREEN}OK{RESET} ({method_tag})")
                    
                    print(f"🚀 {BOLD}[2/2] Mengunggah & memasang ke WordPress Live...{RESET}", end="", flush=True)
                    media_id = wp.upload_wp_media(target_site, saved_path, title=title)
                    if media_id:
                        ok_u, res_u = wp.update_live_post(post_id, {"featured_media": media_id}, target_site)
                        if ok_u:
                            print(f" {GREEN}SUKSES!{RESET}")
                            print(f"\n{GREEN}{BOLD}🎉 Featured image berhasil dibuat & dipasang di Post #{post_id}!{RESET}")
                            print(f"🖼️  File Lokal: {CYAN}{saved_path}{RESET}")
                            print(f"🔗 Media ID  : {BOLD}{media_id}{RESET}")
                        else:
                            print(f" {RED}GAGAL ({res_u}){RESET}")
                    else:
                        print(f" {RED}GAGAL (Upload Media Gagal){RESET}")
                except Exception as e:
                    print(f" {RED}GAGAL ({e}){RESET}")
                press_any_key()
                
            elif img_choice == "2":
                print_section(f"PILIH FILE GAMBAR DARI DISK")
                print(f"{DIM}Masukkan path file gambar (.webp, .png, .jpg) dari folder output/ atau disk lokal.{RESET}\n")
                img_input = input(f"{BOLD}Path file gambar (0 untuk batal):{RESET} ").strip().strip('"').strip("'")
                if img_input and img_input != "0":
                    if not os.path.exists(img_input):
                        print(f"\n{RED}✖ File gambar tidak ditemukan di '{img_input}'.{RESET}")
                    else:
                        print(f"\n{CYAN}Mengunggah gambar ke WordPress Media Library...{RESET}")
                        media_id = wp.upload_wp_media(target_site, img_input, title=title)
                        if media_id:
                            print(f"{CYAN}Menghubungkan media ID {media_id} ke post #{post_id}...{RESET}")
                            ok_u, res_u = wp.update_live_post(post_id, {"featured_media": media_id}, target_site)
                            if ok_u:
                                print(f"{GREEN}✔ Featured image artikel #{post_id} berhasil diperbarui!{RESET}")
                            else:
                                print(f"{RED}✖ Gagal menghubungkan media: {res_u}{RESET}")
                        else:
                            print(f"{RED}✖ Gagal mengunggah media ke WordPress.{RESET}")
                    press_any_key()

        elif action == "5":
            print_section(f"SINKRONISASI ISI POST #{post_id} DARI MARKDOWN")
            print(f"{DIM}Pilih atau masukkan path file .md lokal untuk memperbarui konten postingan ini.{RESET}\n")
            md_path_input = input(f"{BOLD}Path file markdown (0 untuk batal):{RESET} ").strip().strip('"').strip("'")
            if md_path_input and md_path_input != "0":
                if not os.path.exists(md_path_input):
                    print(f"\n{RED}✖ File tidak ditemukan di '{md_path_input}'.{RESET}")
                else:
                    try:
                        with open(md_path_input, "r", encoding="utf-8") as f:
                            raw_md = f.read()
                        
                        # Parse Markdown & Convert ke WordPress HTML
                        parsed = wp.parse_markdown_file(md_path_input)
                        new_body_md = parsed["body"]
                        new_title_md = parsed["frontmatter"].get("title", title)
                        resolved_md = wp.resolve_internal_links(new_body_md, target_site)
                        wp_html = wp.markdown_to_wp_html(resolved_md, title=new_title_md, target_site=target_site)
                        
                        update_payload = {
                            "title": new_title_md,
                            "content": wp_html,
                            "excerpt": parsed["frontmatter"].get("description", "")
                        }
                        
                        print(f"\n{CYAN}Memperbarui konten artikel #{post_id} di WordPress...{RESET}")
                        ok_u, res_u = wp.update_live_post(post_id, update_payload, target_site)
                        if ok_u:
                            print(f"{GREEN}✔ Konten artikel #{post_id} berhasil disinkronisasi ulang dari `{os.path.basename(md_path_input)}`!{RESET}")
                        else:
                            print(f"{RED}✖ Gagal memperbarui konten: {res_u}{RESET}")
                    except Exception as e:
                        print(f"{RED}✖ Terjadi kesalahan: {e}{RESET}")
                press_any_key()

        elif action == "6":
            confirm = get_single_key(f"\n{YELLOW}Pindahkan post #{post_id} ke Trash? [Y/N]: {RESET}", valid_keys=['y', 'n', '0'])
            if confirm.lower() == 'y':
                print(f"\n{CYAN}Memindahkan ke Trash...{RESET}")
                ok_d, msg_d = wp.delete_live_post(post_id, force=False, target_site=target_site)
                if ok_d:
                    print(f"{GREEN}✔ {msg_d}{RESET}")
                else:
                    print(f"{RED}✖ {msg_d}{RESET}")
                press_any_key()
                break
        elif action == "7":
            confirm = get_single_key(f"\n{RED}{BOLD}Hapus post #{post_id} secara PERMANEN? [Y/N]: {RESET}", valid_keys=['y', 'n', '0'])
            if confirm.lower() == 'y':
                print(f"\n{CYAN}Menghapus permanen...{RESET}")
                ok_d, msg_d = wp.delete_live_post(post_id, force=True, target_site=target_site)
                if ok_d:
                    print(f"{GREEN}✔ {msg_d}{RESET}")
                else:
                    print(f"{RED}✖ {msg_d}{RESET}")
                press_any_key()
                break

def menu_manage_wp_categories(wp=None):
    if wp is None:
        wp = WordPressPublisher()

    target_site = select_wp_site_if_multiple(wp, "PILIH WEBSITE WORDPRESS")
    if not target_site:
        return

    while True:
        clear_screen()
        print_banner()
        print_section(f"KELOLA KATEGORI: {target_site['name']}")
        print(f"🌐 {BOLD}URL:{RESET} {target_site['wp_url']}")
        print(f"{DIM}Memuat daftar kategori...{RESET}\n")

        ok, categories = wp.get_live_categories(target_site)
        if not ok:
            print(f"{RED}✖ Gagal mengambil kategori: {categories}{RESET}")
            press_any_key()
            break

        print(f"{BOLD}Daftar Kategori ({len(categories)} Kategori):{RESET}")
        print(f"{BOLD}{'No':<4} {'ID':<6} {'Nama Kategori':<28} {'Slug':<24} {'Jumlah Post'}{RESET}")
        print("-" * 75)
        for i, cat in enumerate(categories, 1):
            c_name = (cat.get("name", "")[:26] + '..') if len(cat.get("name", "")) > 26 else cat.get("name", "")
            c_slug = (cat.get("slug", "")[:22] + '..') if len(cat.get("slug", "")) > 22 else cat.get("slug", "")
            count = cat.get("count", 0)
            print(f"#{i:<3} {str(cat.get('id')):<6} {BOLD}{c_name:<28}{RESET} {c_slug:<24} {count} post")
        print("-" * 75)

        options = [
            ("1", "Tambah Kategori Baru"),
            ("2", "Hapus Kategori"),
            ("0", "Kembali")
        ]

        action = select_menu(options, title="AKSI KATEGORI")

        if action == "0":
            break
        elif action == "1":
            print_section("TAMBAH KATEGORI BARU")
            print(f"{DIM}Ketik '0' untuk batal.{RESET}\n")
            cat_name = input(f"{BOLD}Nama Kategori (misal: 'Panduan Kopi'):{RESET} ").strip()
            if cat_name == "0" or not cat_name:
                continue
            cat_slug = input(f"{BOLD}Slug Kategori [Kosongkan untuk otomatis]:{RESET} ").strip()
            if cat_slug == "0":
                continue
            cat_desc = input(f"{BOLD}Deskripsi Kategori [Opsional]:{RESET} ").strip()
            if cat_desc == "0":
                continue

            print(f"\n{CYAN}Membuat kategori di WordPress...{RESET}")
            ok_c, res_c = wp.create_live_category(
                name=cat_name,
                slug=cat_slug if cat_slug else None,
                description=cat_desc if cat_desc else None,
                target_site=target_site
            )
            if ok_c:
                print(f"{GREEN}✔ Kategori '{cat_name}' (ID: {res_c.get('id')}) berhasil dibuat!{RESET}")
            else:
                print(f"{RED}✖ Gagal: {res_c}{RESET}")
            press_any_key()
        elif action == "2":
            del_opts = [(str(i), f"{cat.get('name')} (ID: {cat.get('id')}, {cat.get('count', 0)} post)") for i, cat in enumerate(categories, 1)]
            del_opts.append(("0", "Batal"))
            c_idx = select_menu(del_opts, title="PILIH KATEGORI UNTUK DIHAPUS")
            if c_idx == "0":
                continue
            target_cat = categories[int(c_idx) - 1]
            confirm = get_single_key(f"\n{RED}Yakin ingin menghapus kategori '{target_cat.get('name')}'? [Y/N]: {RESET}", valid_keys=['y', 'n', '0'])
            if confirm.lower() == 'y':
                print(f"\n{CYAN}Menghapus kategori...{RESET}")
                ok_d, msg_d = wp.delete_live_category(target_cat.get("id"), target_site=target_site)
                if ok_d:
                    print(f"{GREEN}✔ {msg_d}{RESET}")
                else:
                    print(f"{RED}✖ {msg_d}{RESET}")
                press_any_key()

# ==========================================
# MENU: API KEY & MODEL MANAGER (GEMINI & KIE.AI)
# ==========================================
# MENU: API KEY & MODEL MANAGER (GEMINI, KIE.AI & AGNES AI)
# ==========================================
def menu_ai_settings():
    while True:
        options = [
            ("1", "Model & API Key Gemini"),
            ("2", "Model & API Key Kie.ai (Featured Image)"),
            ("3", "Model & API Key Agnes AI (Teks, JSON & Gambar)"),
            ("4", "Konfigurasi Model Tiap Tahap (Pipeline Multi-Model: Gemini / Agnes AI / GPT-6 Luna)"),
            ("0", "Kembali ke Menu Utama")
        ]
        choice = select_menu(options, title="PENGATURAN AI & API KEY")
        if choice == "0":
            break
        elif choice == "1":
            menu_gemini_keys()
        elif choice == "2":
            gemini_c = GeminiClient(key_file="apikey.txt")
            menu_kie_keys(gemini_client=gemini_c)
        elif choice == "3":
            menu_agnes_keys()
        elif choice == "4":
            menu_pipeline_settings()

def menu_pipeline_settings():
    pipeline_mgr = AIPipelineManager()

    while True:
        clear_screen()
        print_banner()
        print_section("KONFIGURASI MODEL AI TIAP TAHAPAN (MULTI-MODEL PIPELINE)")
        print(f"{DIM}Atur model AI yang berbeda untuk masing-masing tahapan penulisan Silo.{RESET}\n")

        s1_name = pipeline_mgr.get_stage_display_name(1)
        s2_name = pipeline_mgr.get_stage_display_name(2)
        s3_name = pipeline_mgr.get_stage_display_name(3)

        print(f"📝 {BOLD}Tahap 1: Riset & Content Brief{RESET}   ➔ {CYAN}{BOLD}{s1_name}{RESET}")
        print(f"✍️  {BOLD}Tahap 2: Penulisan Draf Artikel{RESET}  ➔ {MAGENTA}{BOLD}{s2_name}{RESET}")
        print(f"🔍 {BOLD}Tahap 3: Kurasi Kualitas & Redaksi{RESET} ➔ {GREEN}{BOLD}{s3_name}{RESET}")
        print(f"🖼️  {BOLD}Tahap 4: Featured Image Banner{RESET}    ➔ {YELLOW}{BOLD}Kie.ai Z-Image / Agnes Image / Mesh Gradient{RESET}\n")

        options = [
            ("1", "Ubah Model Tahap 1 (Riset & Content Brief)"),
            ("2", "Ubah Model Tahap 2 (Penulisan Draf Artikel)"),
            ("3", "Ubah Model Tahap 3 (Kurasi Kualitas & Redaksi)"),
            ("P", "⚡ Pilih Preset Cepat (Gemini / Agnes AI / Hybrid / Full GPT-6)"),
            ("0", "Kembali")
        ]

        choice = select_menu(options, title="PILIH AKSI PIPELINE")
        if choice == "0":
            break
        elif choice in ["1", "2", "3"]:
            stage_num = int(choice)
            change_stage_model_flow(pipeline_mgr, stage_num)
        elif choice.upper() == "P":
            preset_options = [
                ("1", "Full Gemini (100% Gratis, Cepat & Tanpa Biaya)"),
                ("2", "Full Agnes AI 3.0 Flash (Cepat, Cerdas & Ringan) ⭐"),
                ("3", "Hybrid Agnes (Tahap 1-2 Gemini + Tahap 3 Agnes 2.5 Pro Kurasi)"),
                ("4", "Hybrid Smart GPT-6 (Tahap 1-2 Gemini + Tahap 3 Kie.ai GPT-6 Luna) ⭐"),
                ("5", "Hybrid Draft & Kurasi GPT-6 (Tahap 1 Gemini + Tahap 2-3 GPT-6 Luna)"),
                ("6", "Full Kie.ai GPT-6 Luna (Tahap 1, 2, 3 Semua GPT-6 Luna)"),
                ("0", "Batal")
            ]
            p_choice = select_menu(preset_options, title="PILIH PRESET PIPELINE")
            if p_choice == "1":
                pipeline_mgr.apply_preset("all_gemini")
                print(f"\n{GREEN}✔ Preset 'Full Gemini' berhasil diterapkan!{RESET}")
                press_any_key()
            elif p_choice == "2":
                pipeline_mgr.apply_preset("all_agnes")
                print(f"\n{GREEN}✔ Preset 'Full Agnes AI 3.0 Flash' berhasil diterapkan!{RESET}")
                press_any_key()
            elif p_choice == "3":
                pipeline_mgr.apply_preset("hybrid_agnes_curation")
                print(f"\n{GREEN}✔ Preset 'Hybrid Agnes (Kurasi Agnes 2.5 Pro)' berhasil diterapkan!{RESET}")
                press_any_key()
            elif p_choice == "4":
                pipeline_mgr.apply_preset("hybrid_gpt6_curation")
                print(f"\n{GREEN}✔ Preset 'Hybrid Smart (Kie.ai GPT-6 Luna pada Kurasi)' berhasil diterapkan!{RESET}")
                press_any_key()
            elif p_choice == "5":
                pipeline_mgr.apply_preset("hybrid_gpt6_draft_curation")
                print(f"\n{GREEN}✔ Preset 'Hybrid Draft & Kurasi GPT-6 Luna' berhasil diterapkan!{RESET}")
                press_any_key()
            elif p_choice == "6":
                pipeline_mgr.apply_preset("full_gpt6")
                print(f"\n{GREEN}✔ Preset 'Full Kie.ai GPT-6 Luna' berhasil diterapkan!{RESET}")
                press_any_key()

def change_stage_model_flow(pipeline_mgr, stage_num):
    print_section(f"UBAH MODEL: {STAGE_NAMES.get(stage_num)}")
    current = pipeline_mgr.get_stage_engine(stage_num)
    print(f"Model saat ini: {CYAN}{pipeline_mgr.get_stage_display_name(stage_num)}{RESET}\n")

    options = []
    default_idx = 0
    for idx, (k, label) in enumerate(AVAILABLE_ENGINES):
        is_cur = f" {GREEN}[Aktif]{RESET}" if k == current else ""
        options.append((str(idx + 1), f"{label}{is_cur}"))
        if k == current:
            default_idx = idx
    options.append(("0", "Batal"))

    c = select_menu(options, title="PILIH ENGINE / MODEL UNTUK TAHAP INI", default_index=default_idx)
    if c == "0":
        return

    chosen_idx = int(c) - 1
    chosen_key = AVAILABLE_ENGINES[chosen_idx][0]
    pipeline_mgr.set_stage_engine(stage_num, chosen_key)
    print(f"\n{GREEN}✔ {STAGE_NAMES.get(stage_num)} diubah menjadi '{AVAILABLE_ENGINES[chosen_idx][1]}'!{RESET}")
    press_any_key()

def menu_gemini_keys():
    while True:
        clear_screen()
        print_banner()
        print_section("PENGATURAN GEMINI")

        client = GeminiClient(key_file="apikey.txt")
        keys = client.reload_keys()
        current_model = client.get_preferred_model()

        print(f"🤖 {BOLD}Model AI Aktif:{RESET} {CYAN}{BOLD}{current_model}{RESET}\n")

        print(f"{BOLD}Daftar API Key Gemini ({len(keys)} Key Terdaftar):{RESET}")
        if not keys:
            print(f"{YELLOW}Belum ada API Key di 'apikey.txt'.{RESET}\n")
        else:
            print(f"{BOLD}{'No':<4} {'API Key (Masked)':<25} {'Posisi'}{RESET}")
            print("-" * 50)
            for i, k in enumerate(keys, 1):
                masked = f"{k[:8]}...{k[-4:]}" if len(k) >= 12 else k
                active_tag = f"{GREEN}[Sedang Digunakan]{RESET}" if i == 1 else f"{DIM}(Cadangan #{i}){RESET}"
                print(f"#{i:<3} {masked:<25} {active_tag}")
            print("")

        options = [
            ("1", "Tambah API Key Baru"),
            ("2", "Uji Semua API Key"),
            ("3", "Hapus API Key"),
            ("4", "Ganti Model Gemini"),
            ("0", "Kembali")
        ]
        opt = select_menu(options, title="PENGATURAN GEMINI")

        if opt == "1":
            print_section("TAMBAH API KEY GEMINI")
            print(f"{DIM}Dapatkan API Key di https://aistudio.google.com/ (0 untuk batal){RESET}\n")
            new_key = input(f"{BOLD}API Key Gemini baru:{RESET} ").strip()
            if new_key == "0":
                continue
            if not new_key:
                print(f"{RED}API Key tidak boleh kosong.{RESET}")
            elif not new_key.startswith("AIzaSy"):
                print(f"{YELLOW}Peringatan: Format key Google diawali 'AIzaSy...'{RESET}")
                confirm = get_single_key("Tetap simpan? [Y/N]: ", valid_keys=['y', 'n'])
                if confirm.lower() == "y":
                    ok = client.add_key(new_key)
                    if ok:
                        print(f"\n{GREEN}✔ API Key berhasil ditambahkan!{RESET}")
                    else:
                        print(f"\n{YELLOW}API Key sudah ada di daftar.{RESET}")
            else:
                ok = client.add_key(new_key)
                if ok:
                    print(f"\n{GREEN}✔ API Key berhasil ditambahkan!{RESET}")
                else:
                    print(f"\n{YELLOW}API Key sudah ada di daftar.{RESET}")
            press_any_key()

        elif opt == "2":
            print_section("UJI API KEY GEMINI")
            print(f"{CYAN}Menguji API key ke endpoint Gemini...{RESET}\n")
            results = client.test_all_keys()
            valid_keys = []
            invalid_keys = []
            for r in results:
                if r["is_valid"]:
                    st_icon = f"{GREEN}✔ VALID{RESET}"
                    valid_keys.append(r)
                else:
                    st_icon = f"{RED}✖ GAGAL{RESET}"
                    invalid_keys.append(r)
                print(f"• Key #{r['index']} ({r['masked']}): {st_icon} -> {r['message']}")
            
            print("-" * 60)
            print(f"📊 {BOLD}Ringkasan:{RESET} {GREEN}{len(valid_keys)} Valid{RESET} | {RED}{len(invalid_keys)} Gagal/Invalid{RESET}")

            if invalid_keys:
                print(f"\n{YELLOW}⚠️  Ditemukan {len(invalid_keys)} key yang tidak valid / gagal.{RESET}")
                del_choice = get_single_key(f"{BOLD}Hapus otomatis semua {len(invalid_keys)} key invalid tersebut? [Y/N]:{RESET} ", valid_keys=['y', 'n', '0'])
                if del_choice.lower() == 'y':
                    keys_to_del = [r["key"] for r in invalid_keys]
                    cnt = client.remove_keys_by_values(keys_to_del)
                    print(f"\n{GREEN}✔ Berhasil menghapus {cnt} API key invalid! (Sisa {len(valid_keys)} key aktif){RESET}")
            press_any_key()

        elif opt == "3":
            if not keys:
                print(f"{YELLOW}Tidak ada API key untuk dihapus.{RESET}")
                press_any_key()
                continue
            
            del_options = [
                ("A", "🧹 Bersihkan Otomatis Semua Key Invalid (Scan Cepat)"),
            ]
            for i, k in enumerate(keys, 1):
                masked = f"{k[:8]}...{k[-4:]}" if len(k) >= 12 else k
                del_options.append((str(i), f"Hapus #{i} ({masked})"))
            del_options.append(("0", "Kembali"))

            c = select_menu(del_options, title="HAPUS API KEY GEMINI")
            if c == "0":
                continue
            elif c.upper() == "A":
                print(f"\n{CYAN}Memindai seluruh API key Gemini...{RESET}")
                results = client.test_all_keys()
                bad_keys = [r["key"] for r in results if not r["is_valid"]]
                if bad_keys:
                    cnt = client.remove_keys_by_values(bad_keys)
                    print(f"\n{GREEN}✔ Berhasil menghapus {cnt} key invalid!{RESET}")
                else:
                    print(f"\n{GREEN}✔ Semua key ({len(keys)}) valid! Tidak ada yang dihapus.{RESET}")
                press_any_key()
            else:
                idx = int(c) - 1
                del_k = client.remove_key(idx)
                print(f"\n{GREEN}✔ Key #{idx + 1} berhasil dihapus.{RESET}")
                press_any_key()

        elif opt == "4":
            menu_change_model_flow(client)

        elif opt == "0":
            break

def menu_kie_keys(gemini_client=None):
    while True:
        clear_screen()
        print_banner()
        print_section("PENGATURAN GAMBAR (KIE.AI & MESH GRADIENT)")

        kie = KieImageClient()
        keys = kie.reload_keys()
        current_model = kie.get_preferred_model()
        current_mode = kie.get_image_mode()
        current_style = kie.get_image_style()
        style_desc = IMAGE_STYLE_DESCS.get(current_style, current_style)

        mode_labels = {
            "hybrid": "Hybrid (Kie.ai AI Visual + Mesh Gradient Fallback)",
            "mesh_gradient": "Always Mesh Gradient (Lokal, Gratis, Instan)",
            "kie_only": "Kie.ai AI Visual Saja (Tanpa Fallback)"
        }
        mode_str = mode_labels.get(current_mode, current_mode)

        print(f"🖼️  {BOLD}Mode Gambar Aktif :{RESET} {GREEN}{BOLD}{mode_str}{RESET}")
        print(f"🎨 {BOLD}Gaya Visual Gambar:{RESET} {MAGENTA}{BOLD}{style_desc}{RESET}")
        print(f"🤖 {BOLD}Model Kie.ai Aktif:{RESET} {CYAN}{BOLD}{current_model}{RESET}\n")

        print(f"{BOLD}Daftar API Key Kie.ai ({len(keys)} Key Terdaftar):{RESET}")
        if not keys:
            print(f"{YELLOW}Belum ada API Key di 'kie_apikey.txt' (Auto fallback ke Mesh Gradient).{RESET}\n")
        else:
            print(f"{BOLD}{'No':<4} {'API Key (Masked)':<25} {'Posisi'}{RESET}")
            print("-" * 50)
            for i, k in enumerate(keys, 1):
                masked = f"{k[:8]}...{k[-4:]}" if len(k) >= 12 else k
                active_tag = f"{GREEN}[Aktif]{RESET}" if i == 1 else f"{DIM}(Cadangan #{i}){RESET}"
                print(f"#{i:<3} {masked:<25} {active_tag}")
            print("")

        options = [
            ("1", "Tambah API Key Baru"),
            ("2", "Uji Semua API Key"),
            ("3", "Hapus API Key"),
            ("4", "Ganti Mode Gambar (Hybrid / Mesh / Kie.ai)"),
            ("5", "Ganti Gaya Visual (Ilustrasi Vector / 3D Isometric / Line Art / Foto)"),
            ("6", "Ganti Model Kie.ai (Z-Image / Flux)"),
            ("7", "Preview Sampel Banner Mesh Gradient"),
            ("8", "Generate Thumbnail untuk Artikel Lama (Batch Scan)"),
            ("0", "Kembali")
        ]
        opt = select_menu(options, title="PENGATURAN GAMBAR FEATURED")

        if opt == "1":
            print_section("TAMBAH API KEY KIE.AI")
            print(f"{DIM}Dapatkan API Key di https://kie.ai/ (0 untuk batal){RESET}\n")
            new_key = input(f"{BOLD}API Key Kie.ai baru:{RESET} ").strip()
            if new_key == "0" or not new_key:
                continue
            ok = kie.add_key(new_key)
            if ok:
                print(f"\n{GREEN}✔ API Key berhasil ditambahkan!{RESET}")
            else:
                print(f"\n{YELLOW}API Key sudah ada di daftar.{RESET}")
            press_any_key()

        elif opt == "2":
            print_section("UJI API KEY & KREDIT KIE.AI")
            print(f"{CYAN}Menguji status API key & mengecek sisa saldo/kredit Kie.ai...{RESET}\n")
            results = kie.test_all_keys()
            valid_keys = []
            zero_or_invalid_keys = []

            for r in results:
                credit_val = r.get("credit")
                if r["is_valid"]:
                    st_icon = f"{GREEN}✔ VALID{RESET}"
                    valid_keys.append(r)
                elif credit_val is not None and credit_val == 0:
                    st_icon = f"{YELLOW}✖ KREDIT 0{RESET}"
                    zero_or_invalid_keys.append(r)
                elif credit_val is not None and credit_val < 0:
                    st_icon = f"{RED}✖ MINUS{RESET}"
                    zero_or_invalid_keys.append(r)
                else:
                    st_icon = f"{RED}✖ GAGAL{RESET}"
                    zero_or_invalid_keys.append(r)
                print(f"• Key #{r['index']} ({r['masked']}): {st_icon} -> {r['message']}")
            
            print("-" * 60)
            print(f"📊 {BOLD}Ringkasan:{RESET} {GREEN}{len(valid_keys)} Valid / Ada Kredit{RESET} | {RED}{len(zero_or_invalid_keys)} Habis / Minus / Invalid{RESET}")

            if zero_or_invalid_keys:
                print(f"\n{YELLOW}⚠️  Ditemukan {len(zero_or_invalid_keys)} key yang kreditnya 0, minus, atau tidak valid.{RESET}")
                del_choice = get_single_key(f"{BOLD}Hapus otomatis semua {len(zero_or_invalid_keys)} key tersebut dari daftar? [Y/N]:{RESET} ", valid_keys=['y', 'n', '0'])
                if del_choice.lower() == 'y':
                    keys_to_del = [r["key"] for r in zero_or_invalid_keys]
                    removed_count = kie.remove_keys_by_values(keys_to_del)
                    print(f"\n{GREEN}✔ Berhasil menghapus {removed_count} API key yang habis/invalid! (Sisa {len(valid_keys)} key aktif){RESET}")
            press_any_key()

        elif opt == "3":
            if not keys:
                print(f"{YELLOW}Tidak ada API key untuk dihapus.{RESET}")
                press_any_key()
                continue
            
            del_options = [
                ("A", "🧹 Bersihkan Otomatis Semua Key Habis / 0 / Invalid (Scan Cepat)"),
            ]
            for i, k in enumerate(keys, 1):
                masked = f"{k[:8]}...{k[-4:]}" if len(k) >= 12 else k
                del_options.append((str(i), f"Hapus #{i} ({masked})"))
            del_options.append(("0", "Kembali"))

            c = select_menu(del_options, title="HAPUS API KEY KIE.AI")
            if c == "0":
                continue
            elif c.upper() == "A":
                print(f"\n{CYAN}Memindai seluruh key untuk mencari key yang 0/minus/invalid...{RESET}")
                results = kie.test_all_keys()
                bad_keys = [r["key"] for r in results if not r["is_valid"] or (r.get("credit") is not None and r.get("credit") <= 0)]
                if bad_keys:
                    cnt = kie.remove_keys_by_values(bad_keys)
                    print(f"\n{GREEN}✔ Berhasil menghapus {cnt} key yang habis/invalid! (Sisa {len(results) - cnt} key aktif){RESET}")
                else:
                    print(f"\n{GREEN}✔ Semua key ({len(keys)}) masih memiliki kredit aktif! Tidak ada yang dihapus.{RESET}")
                press_any_key()
            else:
                idx = int(c) - 1
                del_k = kie.remove_key(idx)
                print(f"\n{GREEN}✔ Key #{idx + 1} berhasil dihapus.{RESET}")
                press_any_key()

        elif opt == "4":
            mode_opts = [
                ("1", "Hybrid (Kie.ai AI Visual -> Fallback Mesh Gradient) [Rekomendasi]"),
                ("2", "Always Mesh Gradient (100% Lokal, Gratis, 50ms)"),
                ("3", "Kie.ai AI Visual Saja (Tanpa Fallback)"),
                ("0", "Batal")
            ]
            mc = select_menu(mode_opts, title="PILIH MODE GENERATOR GAMBAR")
            if mc == "1":
                kie.set_image_mode("hybrid")
                print(f"\n{GREEN}✔ Mode diubah ke: Hybrid (Kie.ai + Fallback Mesh Gradient){RESET}")
            elif mc == "2":
                kie.set_image_mode("mesh_gradient")
                print(f"\n{GREEN}✔ Mode diubah ke: Always Mesh Gradient (Gratis & Instan){RESET}")
            elif mc == "3":
                kie.set_image_mode("kie_only")
                print(f"\n{GREEN}✔ Mode diubah ke: Kie.ai Visual Saja{RESET}")
            if mc != "0":
                press_any_key()

        elif opt == "5":
            current_s = kie.get_image_style()
            s_options = []
            for idx, (code, desc, _) in enumerate(DEFAULT_IMAGE_STYLES, 1):
                badge = f" {GREEN}[Aktif]{RESET}" if code == current_s else ""
                s_options.append((str(idx), f"{desc}{badge}"))
            s_options.append(("0", "Batal"))

            s_choice = select_menu(s_options, title="PILIH GAYA VISUAL GAMBAR (KIE.AI)")
            if s_choice == "0":
                continue
            chosen_style = DEFAULT_IMAGE_STYLES[int(s_choice) - 1][0]
            chosen_desc = DEFAULT_IMAGE_STYLES[int(s_choice) - 1][1]
            kie.set_image_style(chosen_style)
            print(f"\n{GREEN}✔ Gaya visual diubah ke: {BOLD}{chosen_desc}{RESET}")
            press_any_key()

        elif opt == "6":
            current_m = kie.get_preferred_model()
            m_options = []
            for idx, (code, desc) in enumerate(DEFAULT_KIE_MODELS, 1):
                badge = f" {GREEN}[Aktif]{RESET}" if code == current_m else ""
                m_options.append((str(idx), f"{code:<15} - {desc}{badge}"))
            m_options.append(("C", "Ketik Nama Model Kustom"))
            m_options.append(("0", "Batal"))

            m_choice = select_menu(m_options, title="PILIH MODEL GAMBAR KIE.AI")
            if m_choice == "0":
                continue
            elif m_choice.upper() == "C":
                custom_m = input("\nNama model gambar (misal: z-image): ").strip()
                if custom_m and custom_m != "0":
                    kie.set_preferred_model(custom_m)
                    print(f"\n{GREEN}✔ Model gambar diubah ke: {BOLD}{custom_m}{RESET}")
            else:
                chosen_code = DEFAULT_KIE_MODELS[int(m_choice) - 1][0]
                kie.set_preferred_model(chosen_code)
                print(f"\n{GREEN}✔ Model gambar diubah ke: {BOLD}{chosen_code}{RESET}")
            press_any_key()

        elif opt == "7":
            print_section("PREVIEW BANNER MESH GRADIENT (5 LAYOUT PRESETS)")
            print(f"{CYAN}Membuat 5 variasi sampel banner (10 Palet & 5 Layout Desain)...{RESET}\n")
            
            sample_topics = [
                ("Panduan Lengkap Arsitektur SEO Silo Modern", "arsitektur seo silo", "SEO STRATEGY"),
                ("Strategi Internal Linking untuk Meningkatkan Authority Domain", "internal linking seo", "LINK BUILDING"),
                ("Optimasi Kecepatan Astro Web & Core Web Vitals", "astro web optimization", "WEB PERFORMANCE"),
                ("Riset Keyword Berbasis Search Intent & Topik Silo", "keyword research intent", "CONTENT MARKETING"),
                ("Automasi Publikasi Konten Multi Platform Secara Aman", "automasi konten website", "AUTOMATION"),
            ]
            
            try:
                for idx, (title, kw, cat) in enumerate(sample_topics):
                    l_name = LAYOUT_NAMES[idx]
                    p_idx = idx * 2 % len(MESH_PALETTES)
                    sample_path = f"output/sample_layout_{idx + 1}_{l_name}.webp"
                    kie.create_mesh_gradient_banner(
                        title=title,
                        keyword=kw,
                        category=cat,
                        output_path=sample_path,
                        palette_idx=p_idx,
                        layout_idx=idx
                    )
                    print(f" {GREEN}✔ Layout #{idx + 1} ({l_name:<16}){RESET} -> {CYAN}{sample_path}{RESET}")

                print(f"\n{GREEN}{BOLD}🎉 5 Sampel Banner Berhasil Dibuat di folder 'output/'!{RESET}")
                try:
                    first_sample = os.path.abspath("output/sample_layout_1_center_card.webp")
                    webbrowser.open(f"file:///{first_sample.replace('\\', '/')}")
                    print(f"{DIM}Membuka sampel #1 di image viewer...{RESET}")
                except Exception:
                    pass
            except Exception as e:
                print(f"{RED}✖ Gagal membuat sampel: {e}{RESET}")
            press_any_key()

        elif opt == "8":
            menu_batch_generate_missing_thumbnails(gemini_client)

        elif opt == "0":
            break

def menu_agnes_keys():
    while True:
        clear_screen()
        print_banner()
        print_section("PENGATURAN AGNES AI (TEKS, JSON & GAMBAR)")

        agnes = AgnesClient(key_file="agnes_apikey.txt")
        keys = agnes.reload_keys()
        current_text_model = agnes.get_preferred_text_model()
        current_image_model = agnes.get_preferred_image_model()

        print(f"📝 {BOLD}Model Teks Aktif   :{RESET} {CYAN}{BOLD}{current_text_model}{RESET}")
        print(f"🖼️  {BOLD}Model Gambar Aktif :{RESET} {MAGENTA}{BOLD}{current_image_model}{RESET}\n")

        print(f"{BOLD}Daftar API Key Agnes AI ({len(keys)} Key Terdaftar):{RESET}")
        if not keys:
            print(f"{YELLOW}Belum ada API Key di 'agnes_apikey.txt'. Tambahkan minimal 1 API Key.{RESET}\n")
        else:
            print(f"{BOLD}{'No':<4} {'API Key (Masked)':<25} {'Posisi'}{RESET}")
            print("-" * 50)
            for i, k in enumerate(keys, 1):
                masked = f"{k[:8]}...{k[-4:]}" if len(k) >= 12 else k
                active_tag = f"{GREEN}[Aktif]{RESET}" if i == 1 else f"{DIM}(Cadangan #{i}){RESET}"
                print(f"#{i:<3} {masked:<25} {active_tag}")
            print("")

        options = [
            ("1", "Tambah API Key Baru"),
            ("2", "Uji Semua API Key & Koneksi Agnes AI"),
            ("3", "Hapus API Key"),
            ("4", "Ganti Model Teks Agnes AI (3.0 Flash / 2.5 Flash / 2.5 Pro)"),
            ("5", "Ganti Model Gambar Agnes AI (Image 2.0 Flash / 2.5 Flash)"),
            ("6", "Test Generate Gambar Agnes AI (Simpan ke output/test_agnes.webp)"),
            ("0", "Kembali")
        ]
        opt = select_menu(options, title="PENGATURAN AGNES AI")

        if opt == "1":
            print_section("TAMBAH API KEY AGNES AI")
            print(f"{DIM}Dapatkan API Key di https://agnes-ai.com/ (0 untuk batal){RESET}\n")
            new_key = input(f"{BOLD}API Key Agnes AI baru:{RESET} ").strip()
            if new_key == "0" or not new_key:
                continue
            ok = agnes.add_key(new_key)
            if ok:
                print(f"\n{GREEN}✔ API Key Agnes AI berhasil ditambahkan!{RESET}")
            else:
                print(f"\n{YELLOW}API Key sudah ada di daftar.{RESET}")
            press_any_key()

        elif opt == "2":
            print_section("UJI API KEY & KONEKSI AGNES AI")
            print(f"{CYAN}Menguji koneksi ke endpoint Agnes AI (apihub.agnes-ai.com)...{RESET}\n")
            results = agnes.test_all_keys()
            valid_keys = []
            invalid_keys = []
            for r in results:
                if r["is_valid"]:
                    st_icon = f"{GREEN}✔ VALID{RESET}"
                    valid_keys.append(r)
                else:
                    st_icon = f"{RED}✖ GAGAL{RESET}"
                    invalid_keys.append(r)
                print(f"• Key #{r['index']} ({r['masked']}): {st_icon} -> {r['message']}")
            
            print("-" * 60)
            print(f"📊 {BOLD}Ringkasan:{RESET} {GREEN}{len(valid_keys)} Valid{RESET} | {RED}{len(invalid_keys)} Gagal/Invalid{RESET}")

            if invalid_keys:
                print(f"\n{YELLOW}⚠️  Ditemukan {len(invalid_keys)} key yang tidak valid / gagal.{RESET}")
                del_choice = get_single_key(f"{BOLD}Hapus otomatis semua {len(invalid_keys)} key invalid tersebut? [Y/N]:{RESET} ", valid_keys=['y', 'n', '0'])
                if del_choice.lower() == 'y':
                    keys_to_del = [r["key"] for r in invalid_keys]
                    cnt = agnes.remove_keys_by_values(keys_to_del)
                    print(f"\n{GREEN}✔ Berhasil menghapus {cnt} API key invalid! (Sisa {len(valid_keys)} key aktif){RESET}")
            press_any_key()

        elif opt == "3":
            if not keys:
                print(f"{YELLOW}Tidak ada API key untuk dihapus.{RESET}")
                press_any_key()
                continue
            
            del_options = [
                ("A", "🧹 Bersihkan Otomatis Semua Key Invalid (Scan Cepat)"),
            ]
            for i, k in enumerate(keys, 1):
                masked = f"{k[:8]}...{k[-4:]}" if len(k) >= 12 else k
                del_options.append((str(i), f"Hapus #{i} ({masked})"))
            del_options.append(("0", "Kembali"))

            c = select_menu(del_options, title="HAPUS API KEY AGNES AI")
            if c == "0":
                continue
            elif c.upper() == "A":
                print(f"\n{CYAN}Memindai seluruh API key Agnes AI...{RESET}")
                results = agnes.test_all_keys()
                bad_keys = [r["key"] for r in results if not r["is_valid"]]
                if bad_keys:
                    cnt = agnes.remove_keys_by_values(bad_keys)
                    print(f"\n{GREEN}✔ Berhasil menghapus {cnt} key invalid!{RESET}")
                else:
                    print(f"\n{GREEN}✔ Semua key ({len(keys)}) valid! Tidak ada yang dihapus.{RESET}")
                press_any_key()
            else:
                idx = int(c) - 1
                del_k = agnes.remove_key(idx)
                print(f"\n{GREEN}✔ Key #{idx + 1} berhasil dihapus.{RESET}")
                press_any_key()

        elif opt == "4":
            current_m = agnes.get_preferred_text_model()
            m_options = []
            for idx, (code, desc) in enumerate(DEFAULT_AGNES_TEXT_MODELS, 1):
                badge = f" {GREEN}[Aktif]{RESET}" if code == current_m else ""
                m_options.append((str(idx), f"{code:<20} - {desc}{badge}"))
            m_options.append(("C", "Ketik Nama Model Kustom"))
            m_options.append(("0", "Batal"))

            m_choice = select_menu(m_options, title="PILIH MODEL TEKS AGNES AI")
            if m_choice == "0":
                continue
            elif m_choice.upper() == "C":
                custom_m = input("\nNama model teks Agnes AI: ").strip()
                if custom_m and custom_m != "0":
                    agnes.set_preferred_text_model(custom_m)
                    print(f"\n{GREEN}✔ Model teks diubah ke: {BOLD}{custom_m}{RESET}")
            else:
                chosen_code = DEFAULT_AGNES_TEXT_MODELS[int(m_choice) - 1][0]
                agnes.set_preferred_text_model(chosen_code)
                print(f"\n{GREEN}✔ Model teks diubah ke: {BOLD}{chosen_code}{RESET}")
            press_any_key()

        elif opt == "5":
            current_m = agnes.get_preferred_image_model()
            m_options = []
            for idx, (code, desc) in enumerate(DEFAULT_AGNES_IMAGE_MODELS, 1):
                badge = f" {GREEN}[Aktif]{RESET}" if code == current_m else ""
                m_options.append((str(idx), f"{code:<25} - {desc}{badge}"))
            m_options.append(("C", "Ketik Nama Model Gambar Kustom"))
            m_options.append(("0", "Batal"))

            m_choice = select_menu(m_options, title="PILIH MODEL GAMBAR AGNES AI")
            if m_choice == "0":
                continue
            elif m_choice.upper() == "C":
                custom_m = input("\nNama model gambar Agnes AI: ").strip()
                if custom_m and custom_m != "0":
                    agnes.set_preferred_image_model(custom_m)
                    print(f"\n{GREEN}✔ Model gambar diubah ke: {BOLD}{custom_m}{RESET}")
            else:
                chosen_code = DEFAULT_AGNES_IMAGE_MODELS[int(m_choice) - 1][0]
                agnes.set_preferred_image_model(chosen_code)
                print(f"\n{GREEN}✔ Model gambar diubah ke: {BOLD}{chosen_code}{RESET}")
            press_any_key()

        elif opt == "6":
            print_section("TEST GENERATE GAMBAR AGNES AI")
            test_prompt = input(f"{BOLD}Masukkan prompt gambar (Enter untuk default):{RESET} ").strip()
            if not test_prompt:
                test_prompt = "modern flat vector illustration of digital marketing strategy, clean gradient background, minimal, 4k"
            print(f"\n{CYAN}Sedang generate gambar dengan Agnes AI [{agnes.get_preferred_image_model()}]...{RESET}")
            try:
                out_path = "output/test_agnes_preview.webp"
                saved, url = agnes.generate_and_save(test_prompt, out_path)
                print(f"{GREEN}✔ Gambar berhasil dibuat & disimpan di: {saved}{RESET}")
                try:
                    webbrowser.open(f"file:///{os.path.abspath(saved).replace('\\', '/')}")
                except Exception:
                    pass
            except Exception as e:
                print(f"{RED}✖ Gagal generate gambar: {e}{RESET}")
            press_any_key()

        elif opt == "0":
            break

def scan_all_articles_for_missing_images(base_dir="output"):
    """
    Memindai seluruh folder proyek Silo di `output/` untuk menemukan artikel
    yang belum memiliki file featured image (images/<slug>.webp).
    """
    silos_summary = []
    if not os.path.exists(base_dir):
        return silos_summary

    for folder_name in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue

        md_files = [f for f in os.listdir(folder_path) if f.endswith(".md") and f != "SILO_BLUEPRINT.md"]
        if not md_files:
            continue

        silo_theme = folder_name
        meta_file = os.path.join(folder_path, "silo_metadata.json")
        if os.path.exists(meta_file):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta_data = json.load(f)
                    silo_theme = meta_data.get("silo_plan", {}).get("silo_theme", meta_data.get("silo_theme", folder_name))
            except Exception:
                pass

        images_dir = os.path.join(folder_path, "images")
        missing_articles = []
        existing_count = 0

        for md_file in md_files:
            file_path = os.path.join(folder_path, md_file)
            title = None
            keyword = None
            role = "Cluster"
            slug = None

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            fm = parts[1]
                            for line in fm.splitlines():
                                if line.startswith("title:"):
                                    title = line.replace("title:", "").strip().strip('"').strip("'")
                                elif line.startswith("keyword:"):
                                    keyword = line.replace("keyword:", "").strip().strip('"').strip("'")
                                elif line.startswith("silo_role:"):
                                    role = line.replace("silo_role:", "").strip().strip('"').strip("'")
                                elif line.startswith("url_slug:"):
                                    slug = line.replace("url_slug:", "").strip().strip('"').strip("'")
            except Exception:
                pass

            if not slug:
                clean_name = re.sub(r'^\d+_', '', md_file).replace('.md', '')
                slug = clean_name
            if not title:
                title = slug.replace('-', ' ').title()
            if not keyword:
                keyword = slug.replace('-', ' ')

            img_webp = os.path.join(images_dir, f"{slug}.webp")
            img_png = os.path.join(images_dir, f"{slug}.png")
            img_jpg = os.path.join(images_dir, f"{slug}.jpg")

            if os.path.exists(img_webp) or os.path.exists(img_png) or os.path.exists(img_jpg):
                existing_count += 1
            else:
                missing_articles.append({
                    "file_path": file_path,
                    "filename": md_file,
                    "title": title,
                    "keyword": keyword,
                    "role": role,
                    "slug": slug,
                    "silo_theme": silo_theme,
                    "target_img_path": img_webp
                })

        silos_summary.append({
            "folder_name": folder_name,
            "folder_path": folder_path,
            "silo_theme": silo_theme,
            "total_articles": len(md_files),
            "existing_images": existing_count,
            "missing_articles": missing_articles
        })

    return silos_summary

def menu_batch_generate_missing_thumbnails(gemini_client=None):
    clear_screen()
    print_banner()
    print_section("GENERATE THUMBNAIL UNTUK ARTIKEL LAMA (BATCH SCAN)")

    silos = scan_all_articles_for_missing_images("output")
    if not silos:
        print(f"{YELLOW}Tidak ditemukan folder artikel Silo di 'output/'.{RESET}")
        press_any_key()
        return

    total_articles = sum(s["total_articles"] for s in silos)
    total_missing = sum(len(s["missing_articles"]) for s in silos)
    total_existing = total_articles - total_missing

    print(f"📊 {BOLD}Status Thumbnail Global di Seluruh Silo:{RESET}")
    print(f" • Total Artikel Dibuat        : {BOLD}{total_articles}{RESET}")
    print(f" • Sudah Memiliki Thumbnail     : {BOLD}{GREEN}{total_existing}{RESET}")
    print(f" • Belum Memiliki Thumbnail    : {BOLD}{YELLOW}{total_missing}{RESET}\n")

    if total_missing == 0:
        print(f"{GREEN}✔ Semua artikel di seluruh Silo sudah memiliki featured image! 🎉{RESET}")
        press_any_key()
        return

    print(f"{BOLD}Daftar Proyek Silo & Status Gambar:{RESET}")
    print(f"{BOLD}{'No':<4} {'Folder Proyek':<28} {'Total':<8} {'Sudah Ada':<12} {'Belum Ada'}{RESET}")
    print("-" * 75)
    for i, s in enumerate(silos, 1):
        miss_count = len(s['missing_articles'])
        miss_str = f"{YELLOW}{miss_count} Belum{RESET}" if miss_count > 0 else f"{GREEN}Lengkap{RESET}"
        exist_str = f"{GREEN}{s['existing_images']}{RESET}"
        print(f"#{i:<3} {s['folder_name']:<28} {s['total_articles']:<8} {exist_str:<21} {miss_str}")
    print("")

    options = [
        ("1", f"Generate Semua Thumbnail yang Belum Ada ({total_missing} Artikel)"),
        ("2", "Pilih Proyek Silo Tertentu Saja"),
        ("0", "Batal / Kembali")
    ]
    opt = select_menu(options, title="PILIH AKSI GENERASI THUMBNAIL")

    to_process = []
    if opt == "1":
        for s in silos:
            to_process.extend(s["missing_articles"])
    elif opt == "2":
        silo_opts = []
        for i, s in enumerate(silos, 1):
            miss = len(s["missing_articles"])
            silo_opts.append((str(i), f"{s['folder_name']} ({miss} gambar belum dibuat)"))
        silo_opts.append(("0", "Batal"))
        sc = select_menu(silo_opts, title="PILIH PROYEK SILO")
        if sc == "0":
            return
        chosen_silo = silos[int(sc) - 1]
        to_process = chosen_silo["missing_articles"]
    else:
        return

    if not to_process:
        print(f"\n{GREEN}Tidak ada artikel yang perlu digenerate.{RESET}")
        press_any_key()
        return

    kie = KieImageClient()
    current_mode = kie.get_image_mode()
    mode_names = {
        "hybrid": "Hybrid (Kie.ai + Fallback Mesh Gradient)",
        "mesh_gradient": "Always Mesh Gradient (Lokal & Cepat)",
        "kie_only": "Kie.ai Photo Saja"
    }

    print_section(f"PROSES GENERATE {len(to_process)} THUMBNAIL")
    print(f"⚙️  Mode Gambar: {CYAN}{BOLD}{mode_names.get(current_mode, current_mode)}{RESET}\n")

    success_count = 0
    fail_count = 0

    for idx, item in enumerate(to_process, 1):
        cat_label = item["silo_theme"]
        if item.get("role", "").lower() == "pillar":
            cat_label += " (Pillar)"
        
        t_disp = item["title"][:38] + "..." if len(item["title"]) > 38 else item["title"]
        print(f"[{idx}/{len(to_process)}] 🖼️  {t_disp}...", end="", flush=True)

        try:
            saved_path, method_used = kie.generate_featured_image_auto(
                title=item["title"],
                keyword=item["keyword"],
                category=cat_label,
                save_path=item["target_img_path"],
                gemini_client=gemini_client
            )
            if method_used == "kie_ai":
                st_label = kie.get_image_style().replace("_", " ").title()
                print(f" {GREEN}OK - Kie.ai ({st_label}){RESET}")
            else:
                print(f" {CYAN}OK - Mesh Gradient{RESET}")
            success_count += 1
        except Exception as e:
            print(f" {RED}GAGAL ({e}){RESET}")
            fail_count += 1

    print(f"\n{GREEN}{BOLD}🎉 PROSES SELESAI!{RESET}")
    print(f" • Berhasil Dibuat: {GREEN}{BOLD}{success_count}{RESET} Gambar")
    if fail_count > 0:
        print(f" • Gagal          : {RED}{BOLD}{fail_count}{RESET} Gambar")
    print(f"📁 Lokasi Gambar  : Tersimpan di subfolder `images/` masing-masing proyek.")
    press_any_key()

def menu_change_model_flow(client):
    current = client.get_preferred_model()
    
    options = []
    idx_counter = 1
    model_choices = {}
    default_idx = 0

    for code, desc in DEFAULT_FLASH_MODELS:
        active_badge = f" {GREEN}[Aktif]{RESET}" if code == current else ""
        options.append((str(idx_counter), f"⚡ {code:<22} - {desc}{active_badge}"))
        model_choices[str(idx_counter)] = code
        if code == current:
            default_idx = idx_counter - 1
        idx_counter += 1

    for code, desc in DEFAULT_PRO_MODELS:
        active_badge = f" {GREEN}[Aktif]{RESET}" if code == current else ""
        options.append((str(idx_counter), f"🧠 {code:<22} - {desc}{active_badge}"))
        model_choices[str(idx_counter)] = code
        if code == current:
            default_idx = idx_counter - 1
        idx_counter += 1

    options.append(("C", "Ketik Nama Model Kustom"))
    options.append(("0", "Kembali"))

    choice = select_menu(options, title=f"PILIH MODEL GEMINI (Aktif: {current})", default_index=default_idx)

    if choice == "0":
        return

    chosen_model = None
    if choice.upper() == "C":
        chosen_model = input("\nNama model Gemini (misal: gemini-2.5-flash): ").strip()
        if chosen_model == "0" or not chosen_model:
            return
    elif choice in model_choices:
        chosen_model = model_choices[choice]

    if chosen_model:
        client.set_preferred_model(chosen_model)
        print(f"\n{GREEN}✔ Model diubah menjadi: {BOLD}{chosen_model}{RESET}")
        
        print(f"{CYAN}Menguji model '{chosen_model}'...{RESET}")
        try:
            test_resp = client.generate_text("Tes respon singkat 3 kata.", max_retries=2)
            print(f"{GREEN}✔ Model siap digunakan! (Respon: \"{test_resp}\"){RESET}")
        except Exception as e:
            print(f"{YELLOW}⚠️ Catatan: {e}{RESET}")
    else:
        print(f"{RED}Pilihan tidak valid.{RESET}")

    press_any_key()

# ==========================================
# MENU: YOUTUBE CREATOR & METADATA SUITE
# ==========================================
def menu_youtube():
    yt_profile_mgr = YouTubeProfileManager()
    pipeline_mgr = AIPipelineManager()
    yt_live = YouTubeLiveClient()

    while True:
        clear_screen()
        print_banner()
        print_section("YOUTUBE CREATOR & METADATA SUITE")

        active_profile = yt_profile_mgr.get_active_profile()
        ch_id = active_profile.get("id", "default")
        has_token = yt_live.has_saved_token(ch_id)
        oauth_status = f"{GREEN}[OAuth Terhubung]{RESET}" if has_token else f"{YELLOW}[OAuth Belum Login]{RESET}"

        ai_client = pipeline_mgr.get_client_for_stage(1)
        engine_name = pipeline_mgr.get_stage_display_name(1)

        print(f"🎬 {BOLD}Channel Aktif:{RESET} {GREEN}{BOLD}{active_profile.get('name')}{RESET} (Niche: {active_profile.get('niche')}) {oauth_status}")
        print(f"🎯 {BOLD}Tagline      :{RESET} {DIM}{active_profile.get('branding_tagline')}{RESET}")
        print(f"🤖 {BOLD}AI Engine    :{RESET} {CYAN}{engine_name}{RESET}\n")

        options = [
            ("1", "🎬 Generate Metadata Video Baru (Judul, Deskripsi, Tags, Thumbnail Concept)"),
            ("2", "🔄 Optimasi / Regenerasi Video Manual (Berdasarkan Judul/Topik Lama)"),
            ("3", "🔴 Kelola & Update Live Video Channel (Tarik Video Live, AI Refresh & Push Langsung)"),
            ("4", "📢 Optimasi Profil Channel (Halaman About Bio & Channel Keywords Studio)"),
            ("5", "🔐 Pengaturan OAuth & Koneksi Akun Google YouTube"),
            ("6", "⚙️ Kelola Profil Identitas Channel (Ganti / Tambah / Edit Channel)"),
            ("7", "📂 Lihat Riwayat File Metadata Video YouTube Tersimpan"),
            ("0", "Kembali ke Menu Utama")
        ]

        choice = select_menu(options, title="PILIH AKSI YOUTUBE")
        if choice == "0":
            break
        elif choice == "1":
            menu_yt_generate_new_video(ai_client, active_profile)
        elif choice == "2":
            menu_yt_optimize_existing_video(ai_client, active_profile)
        elif choice == "3":
            menu_yt_manage_live_videos(ai_client, yt_live, active_profile)
        elif choice == "4":
            menu_yt_optimize_channel(ai_client, yt_profile_mgr, active_profile)
        elif choice == "5":
            menu_yt_oauth_settings(yt_live, active_profile, yt_profile_mgr)
        elif choice == "6":
            menu_yt_manage_profiles(yt_profile_mgr)
        elif choice == "7":
            menu_yt_view_history()

def menu_yt_generate_new_video(ai_client, active_profile):
    print_section(f"GENERATE METADATA VIDEO BARU - [{active_profile.get('name')}]")
    print(f"{DIM}Ketik '0' untuk membatalkan.{RESET}\n")

    topic = input(f"{BOLD}Topik / Konsep Video:{RESET} ").strip()
    if topic == "0" or not topic:
        return

    key_points = input(f"{BOLD}Poin Pembahasan Kunci [Opsional, tekan Enter untuk lewati]:{RESET} ").strip()
    if key_points == "0":
        return

    focus_kw = input(f"{BOLD}Target Keyword Fokus [Opsional, tekan Enter untuk lewati]:{RESET} ").strip()
    if focus_kw == "0":
        return

    print(f"\n{CYAN}Sedang merancang paket metadata YouTube terbaik (Judul, Deskripsi, Tags, Thumbnail)...{RESET}")
    
    try:
        yt_gen = YouTubeGenerator(ai_client=ai_client)
        data = yt_gen.generate_new_video_metadata(
            video_topic=topic,
            key_points=key_points,
            focus_keyword=focus_kw,
            channel_profile=active_profile
        )
    except Exception as e:
        print(f"{RED}✖ Gagal membuat metadata: {e}{RESET}")
        press_any_key()
        return

    # Tampilkan Hasil
    clear_screen()
    print_banner()
    print_section(f"HASIL METADATA VIDEO: {topic}")

    print(f"\n📌 {BOLD}5 REKOMENDASI JUDUL VIDEO (HIGH CTR & SEO):{RESET}")
    titles = data.get("titles", [])
    for idx, t in enumerate(titles, 1):
        print(f"  {BOLD}#{idx} [{t.get('type')}]{RESET} : {GREEN}{t.get('title')}{RESET}")
    
    rec_title = data.get("recommended_primary_title", "")
    if rec_title:
        print(f"  ⭐ {BOLD}Rekomendasi Paling Kuat:{RESET} {CYAN}{BOLD}{rec_title}{RESET}")

    desc = data.get("description", {})
    print(f"\n📝 {BOLD}HOOK 2 BARIS PERTAMA (ABOVE THE FOLD):{RESET}")
    print(f"  {YELLOW}{desc.get('above_the_fold_hook')}{RESET}")

    print(f"\n🏷️  {BOLD}TAGS VIDEO ({len(data.get('tags_comma_separated', ''))} karakter):{RESET}")
    print(f"  {DIM}{data.get('tags_comma_separated')}{RESET}")

    print(f"\n🔖 {BOLD}HASHTAGS:{RESET}")
    print(f"  {CYAN}{' '.join(data.get('hashtags', []))}{RESET}")

    print(f"\n🖼️  {BOLD}REKOMENDASI THUMBNAIL & TEXT OVERLAY:{RESET}")
    thumbs = data.get("thumbnail_recommendations", [])
    for idx, th in enumerate(thumbs, 1):
        print(f"  {BOLD}Konsep #{idx}: {th.get('concept_name')}{RESET}")
        print(f"  • Tulisan Thumbnail (Max 3-4 Kata) : {MAGENTA}{BOLD}\"{th.get('overlay_text')}\"{RESET}")
        print(f"  • Komposisi Visual                 : {th.get('visual_description')}")
        print(f"  • AI Image Prompt                  : {DIM}{th.get('ai_image_prompt_en')}{RESET}\n")

    if data.get("pinned_comment"):
        print(f"💬 {BOLD}PINNED COMMENT PANCINGAN DISKUSI:{RESET}")
        print(f"  {data.get('pinned_comment')}")

    # Simpan File
    txt_path, json_path = yt_gen.save_video_pack(data, active_profile.get("name"), topic)
    print(f"\n{GREEN}✔ Paket metadata berhasil disimpan di:{RESET}\n  📁 {CYAN}{txt_path}{RESET}")

    open_choice = get_single_key(f"\n{BOLD}Buka file teks sekarang di Notepad/Editor? [Y/N]:{RESET} ", valid_keys=['y', 'n', '0', '\r', '\n'])
    if open_choice.lower() == 'y':
        try:
            if os.name == 'nt':
                os.startfile(txt_path)
            else:
                webbrowser.open(f"file:///{os.path.abspath(txt_path).replace('\\', '/')}")
        except Exception:
            pass

    press_any_key()

def menu_yt_optimize_existing_video(ai_client, active_profile):
    print_section(f"OPTIMASI / REGENERASI VIDEO PUBLISH - [{active_profile.get('name')}]")
    print(f"{DIM}Ketik '0' untuk membatalkan.{RESET}\n")

    old_title = input(f"{BOLD}Judul Video Lama Saat Ini:{RESET} ").strip()
    if old_title == "0" or not old_title:
        return

    old_desc = input(f"{BOLD}Deskripsi Lama [Opsional, tekan Enter untuk lewati]:{RESET} ").strip()
    if old_desc == "0":
        return

    issue = input(f"{BOLD}Masalah / Keluhan [misal: 'CTR rendah', 'View mandek']: {RESET}").strip()
    if issue == "0":
        return

    print(f"\n{CYAN}Sedang membedah dan meregenerasi variasi judul, deskripsi & thumbnail baru...{RESET}")
    
    try:
        yt_gen = YouTubeGenerator(ai_client=ai_client)
        data = yt_gen.optimize_existing_video(
            old_title=old_title,
            old_description=old_desc,
            current_issue=issue,
            channel_profile=active_profile
        )
    except Exception as e:
        print(f"{RED}✖ Gagal optimasi video: {e}{RESET}")
        press_any_key()
        return

    # Tampilkan Hasil
    clear_screen()
    print_banner()
    print_section(f"HASIL OPTIMASI VIDEO: {old_title}")

    analysis = data.get("analysis", {})
    print(f"\n🔍 {BOLD}ANALISIS KELEMAHAN JUDUL LAMA:{RESET}")
    print(f"  {YELLOW}{analysis.get('old_title_weakness')}{RESET}")
    print(f"  {CYAN}Strategi:{RESET} {analysis.get('improvement_strategy')}")

    print(f"\n📌 {BOLD}5 REKOMENDASI JUDUL BARU (REFRESH CTR):{RESET}")
    titles = data.get("new_titles", [])
    for idx, t in enumerate(titles, 1):
        print(f"  {BOLD}#{idx} [{t.get('type')}]{RESET} : {GREEN}{t.get('title')}{RESET}")
    
    rec_title = data.get("recommended_new_title", "")
    if rec_title:
        print(f"  ⭐ {BOLD}Judul Rekomendasi Utama:{RESET} {CYAN}{BOLD}{rec_title}{RESET}")

    print(f"\n🖼️  {BOLD}REKOMENDASI RE-DESIGN THUMBNAIL:{RESET}")
    thumbs = data.get("new_thumbnail_recommendations", [])
    for idx, th in enumerate(thumbs, 1):
        print(f"  {BOLD}Konsep #{idx}: {th.get('concept_name')}{RESET}")
        print(f"  • Tulisan Thumbnail Baru : {MAGENTA}{BOLD}\"{th.get('overlay_text')}\"{RESET}")
        print(f"  • Komposisi Visual       : {th.get('visual_description')}")
        print(f"  • AI Image Prompt        : {DIM}{th.get('ai_image_prompt_en')}{RESET}\n")

    if data.get("action_advice"):
        print(f"💡 {BOLD}SARAN STRATEGI PENGGANTIAN METADATA:{RESET}")
        print(f"  {data.get('action_advice')}")

    # Simpan File
    txt_path, json_path = yt_gen.save_video_pack(data, active_profile.get("name"), f"REFRESH_{old_title}")
    print(f"\n{GREEN}✔ Paket optimasi berhasil disimpan di:{RESET}\n  📁 {CYAN}{txt_path}{RESET}")

    open_choice = get_single_key(f"\n{BOLD}Buka file teks sekarang di Notepad/Editor? [Y/N]:{RESET} ", valid_keys=['y', 'n', '0', '\r', '\n'])
    if open_choice.lower() == 'y':
        try:
            if os.name == 'nt':
                os.startfile(txt_path)
            else:
                webbrowser.open(f"file:///{os.path.abspath(txt_path).replace('\\', '/')}")
        except Exception:
            pass

    press_any_key()

def menu_yt_optimize_channel(ai_client, yt_profile_mgr, active_profile):
    print_section("OPTIMASI PROFIL CHANNEL (ABOUT & KEYWORDS)")
    print(f"{DIM}Membuat copywriting halaman About dan Channel Keywords untuk YouTube Studio.{RESET}\n")

    ch_name = input(f"{BOLD}Nama Channel [{active_profile.get('name')}]:{RESET} ").strip()
    if ch_name == "0": return
    ch_name = ch_name if ch_name else active_profile.get("name")

    niche = input(f"{BOLD}Niche / Industri [{active_profile.get('niche')}]:{RESET} ").strip()
    if niche == "0": return
    niche = niche if niche else active_profile.get("niche")

    audience = input(f"{BOLD}Target Penonton [{active_profile.get('target_audience')}]:{RESET} ").strip()
    if audience == "0": return
    audience = audience if audience else active_profile.get("target_audience")

    core_topics = input(f"{BOLD}Topik Utama yang Dibahas [Tekan Enter untuk lewati]:{RESET} ").strip()
    if core_topics == "0": return

    print(f"\n{CYAN}Sedang merancang bio channel & kata kunci YouTube Studio...{RESET}")
    try:
        yt_gen = YouTubeGenerator(ai_client=ai_client)
        res = yt_gen.optimize_channel_profile(
            channel_name=ch_name,
            niche=niche,
            target_audience=audience,
            core_topics=core_topics
        )
    except Exception as e:
        print(f"{RED}✖ Gagal optimasi channel: {e}{RESET}")
        press_any_key()
        return

    clear_screen()
    print_banner()
    print_section(f"HASIL OPTIMASI CHANNEL: {ch_name}")

    print(f"\n📖 {BOLD}DESKRIPSI HALAMAN ABOUT (LENGKAP):{RESET}")
    print(f"{res.get('about_bio_long')}\n")

    print(f"📌 {BOLD}DESKRIPSI RINGKAS (SHORT BIO):{RESET}")
    print(f"{res.get('about_bio_short')}\n")

    print(f"🎯 {BOLD}PILIHAN TAGLINE BRANDING:{RESET}")
    for idx, tag in enumerate(res.get("tagline_options", []), 1):
        print(f"  {idx}. {CYAN}{tag}{RESET}")

    print(f"\n🏷️  {BOLD}CHANNEL KEYWORDS (STUDIO SETTINGS - SIAP SALIN):{RESET}")
    print(f"{GREEN}{res.get('channel_keywords_comma_separated')}{RESET}\n")

    print(f"📂 {BOLD}SARAN STRUKTUR PLAYLIST:{RESET}")
    for pl in res.get("suggested_playlists", []):
        print(f"  • {BOLD}{pl.get('playlist_name')}{RESET}: {DIM}{pl.get('description')}{RESET}")

    apply_choice = get_single_key(f"\n{BOLD}Simpan Channel Keywords & Tagline ini ke Profil Channel aktif? [Y/N]:{RESET} ", valid_keys=['y', 'n', '0'])
    if apply_choice.lower() == 'y':
        update_data = {
            "channel_keywords": res.get("channel_keywords_comma_separated", ""),
        }
        taglines = res.get("tagline_options", [])
        if taglines:
            update_data["branding_tagline"] = taglines[0]
        yt_profile_mgr.update_profile(active_profile.get("id"), update_data)
        print(f"\n{GREEN}✔ Profil Channel berhasil diperbarui dengan keywords baru!{RESET}")

    press_any_key()

def menu_yt_oauth_settings(yt_live, active_profile, yt_profile_mgr):
    while True:
        clear_screen()
        print_banner()
        print_section("PENGATURAN OAUTH & KONEKSI AKUN GOOGLE YOUTUBE")

        ch_id = active_profile.get("id", "default")
        has_token = yt_live.has_saved_token(ch_id)
        has_secret = yt_live.is_secret_file_present()

        print(f"🎬 {BOLD}Channel Lokal:{RESET} {GREEN}{BOLD}{active_profile.get('name')}{RESET} (ID: {ch_id})\n")

        if not has_secret:
            print(f"{YELLOW}⚠️  File 'client_secret.json' belum ditemukan di root folder.{RESET}")
            print(f"{DIM}Cara mendapatkan client_secret.json (Google Cloud Console):{RESET}")
            print(f" 1. Buka Google Cloud Console: {CYAN}https://console.cloud.google.com/{RESET}")
            print(f" 2. Buat project baru dan aktifkan {BOLD}YouTube Data API v3{RESET}.")
            print(f" 3. Di menu 'Credentials' ➔ Klik '+ Create Credentials' ➔ 'OAuth client ID'.")
            print(f" 4. Pada Application type, pilih: {BOLD}'Desktop app'{RESET} (atau Web App dengan redirect URI 'http://localhost').")
            print(f" 5. Unduh JSON kredensial dan simpan di folder Silo dengan nama {BOLD}'client_secret.json'{RESET}.\n")
        else:
            print(f"{GREEN}✔ File 'client_secret.json' terdeteksi.{RESET}")

        if has_token:
            print(f"{GREEN}✔ Status Koneksi: TERHUBUNG KE AKUN GOOGLE (OAuth Token Aktif){RESET}\n")
            try:
                ch_info = yt_live.get_channel_profile_live(ch_id)
                print(f"📌 {BOLD}Info Live YouTube Channel:{RESET}")
                print(f" • Nama Channel : {CYAN}{BOLD}{ch_info.get('title')}{RESET} ({ch_info.get('custom_url')})")
                print(f" • Channel ID   : {ch_info.get('channel_id')}")
                print(f" • Subscribers  : {GREEN}{ch_info.get('subscriber_count'):,}{RESET}")
                print(f" • Total Video  : {ch_info.get('video_count'):,} Video")
                print(f" • Total Views  : {ch_info.get('view_count'):,} Views\n")
            except Exception as e:
                print(f"{YELLOW}⚠️ Catatan: {e}{RESET}\n")
        else:
            print(f"{YELLOW}Status Koneksi: BELUM TERHUBUNG (Pilih menu 1 untuk login instan){RESET}\n")

        options = [
            ("1", "🚀 Login Otomatis (1-Click Browser - Tanpa Copy Paste) ⭐ [Rekomendasi]"),
            ("2", "📋 Login Manual (Paste URL / Auth Code di CLI)"),
            ("3", "🔄 Sinkronkan Nama & Deskripsi Channel dari YouTube ke Profil Silo"),
            ("4", "🔓 Putuskan Koneksi OAuth (Logout)"),
            ("0", "Kembali")
        ]

        c = select_menu(options, title="PILIH AKSI OAUTH")
        if c == "0":
            break
        elif c == "1":
            print_section("LOGIN OTOMATIS YOUTUBE (1-CLICK BROWSER)")
            try:
                ok, msg = yt_live.authenticate_auto(channel_id=ch_id)
                print(f"\n{GREEN}✔ {msg}{RESET}")
                try:
                    info = yt_live.get_channel_profile_live(ch_id)
                    if info.get("title") and active_profile.get("name") in ["My YouTube Channel", "Default Channel", ""]:
                        yt_profile_mgr.update_profile(ch_id, {"name": info.get("title")})
                        print(f"{GREEN}✔ Nama channel lokal diperbarui menjadi '{info.get('title')}'!{RESET}")
                except Exception:
                    pass
            except Exception as e:
                print(f"\n{RED}✖ Gagal otentikasi: {e}{RESET}")
            press_any_key()
        elif c == "2":
            print_section("LOGIN MANUAL (PASTE DI CLI)")
            try:
                ok, msg = yt_live.authenticate_manual(channel_id=ch_id)
                print(f"\n{GREEN}✔ {msg}{RESET}")
                try:
                    info = yt_live.get_channel_profile_live(ch_id)
                    if info.get("title") and active_profile.get("name") in ["My YouTube Channel", "Default Channel", ""]:
                        yt_profile_mgr.update_profile(ch_id, {"name": info.get("title")})
                        print(f"{GREEN}✔ Nama channel lokal diperbarui menjadi '{info.get('title')}'!{RESET}")
                except Exception:
                    pass
            except Exception as e:
                print(f"\n{RED}✖ Gagal otentikasi: {e}{RESET}")
            press_any_key()
        elif c == "3":
            try:
                print(f"\n{CYAN}Mengambil data profil dari YouTube...{RESET}")
                info = yt_live.get_channel_profile_live(ch_id)
                up_dict = {
                    "name": info.get("title"),
                }
                if info.get("description"):
                    up_dict["branding_tagline"] = info.get("description").split("\n")[0][:100]
                yt_profile_mgr.update_profile(ch_id, up_dict)
                print(f"\n{GREEN}✔ Berhasil menyinkronkan profil channel '{info.get('title')}'!{RESET}")
            except Exception as e:
                print(f"\n{RED}✖ Gagal sinkronisasi: {e}{RESET}")
            press_any_key()
        elif c == "4":
            ok, msg = yt_live.disconnect_channel(ch_id)
            print(f"\n{GREEN}✔ {msg}{RESET}")
            press_any_key()

def menu_yt_manage_live_videos(ai_client, yt_live, active_profile):
    ch_id = active_profile.get("id", "default")
    if not yt_live.has_saved_token(ch_id):
        print_section("KONEKSI YOUTUBE OAUTH DIBUTUHKAN")
        print(f"{YELLOW}Channel '{active_profile.get('name')}' belum terhubung via OAuth Google.{RESET}")
        conn = get_single_key("Hubungkan sekarang? [Y/N]: ", valid_keys=['y', 'n', '0'])
        if conn.lower() == 'y':
            try:
                ok, msg = yt_live.authenticate(channel_id=ch_id)
                print(f"\n{GREEN}✔ {msg}{RESET}")
            except Exception as e:
                print(f"\n{RED}✖ Gagal koneksi: {e}{RESET}")
                press_any_key()
                return
        else:
            return

    while True:
        clear_screen()
        print_banner()
        print_section(f"KELOLA & UPDATE LIVE VIDEO YOUTUBE - [{active_profile.get('name')}]")
        print(f"{DIM}Mengambil daftar video terbaru langsung dari channel Anda...{RESET}\n")

        try:
            videos, next_page = yt_live.list_my_videos(channel_id=ch_id, max_results=25)
        except Exception as e:
            print(f"{RED}✖ Gagal mengambil daftar video: {e}{RESET}")
            press_any_key()
            break

        if not videos:
            print(f"{YELLOW}Tidak ditemukan video di channel ini.{RESET}")
            press_any_key()
            break

        print(f"{BOLD}Daftar Video Live Channel ({len(videos)} Video Terbaru):{RESET}")
        print(f"{BOLD}{'No':<4} {'Views':<9} {'Likes':<7} {'Status':<10} {'Judul Video'}{RESET}")
        print("-" * 75)

        for idx, v in enumerate(videos, 1):
            st_color = GREEN if v.get("privacy_status") == "public" else (YELLOW if v.get("privacy_status") == "unlisted" else DIM)
            st_str = f"{st_color}{v.get('privacy_status', 'public').capitalize()}{RESET}"
            title_disp = (v.get("title", "")[:42] + '..') if len(v.get("title", "")) > 42 else v.get("title", "")
            print(f"#{idx:<3} {v.get('view_count', 0):<9,} {v.get('like_count', 0):<7,} {st_str:<19} {BOLD}{title_disp}{RESET}")
        print("-" * 75)

        vid_options = [(str(i), f"{v.get('title')[:45]} ({v.get('view_count', 0):,} views)") for i, v in enumerate(videos, 1)]
        vid_options.append(("0", "Kembali"))

        c = select_menu(vid_options, title="PILIH VIDEO UNTUK DIKELOLA / DI-OPTIMASI")
        if c == "0":
            break

        chosen_vid = videos[int(c) - 1]
        process_single_live_video_flow(ai_client, yt_live, chosen_vid, active_profile)

def process_single_live_video_flow(ai_client, yt_live, video, active_profile):
    ch_id = active_profile.get("id", "default")
    v_id = video.get("video_id")

    while True:
        clear_screen()
        print_banner()
        print_section(f"KELOLA LIVE VIDEO: {video.get('title')}")

        print(f"🎬 {BOLD}Judul Saat Ini :{RESET} {GREEN}{BOLD}{video.get('title')}{RESET}")
        print(f"🌐 {BOLD}URL Video      :{RESET} {CYAN}{video.get('video_url')}{RESET}")
        print(f"📊 {BOLD}Statistik      :{RESET} {video.get('view_count', 0):,} Views | {video.get('like_count', 0):,} Likes | {video.get('comment_count', 0):,} Komentar")
        print(f"🔒 {BOLD}Status Publik  :{RESET} {video.get('privacy_status', 'public').upper()}")
        print(f"🏷️  {BOLD}Tags Saat Ini  :{RESET} {', '.join(video.get('tags', [])) if video.get('tags') else '(Tidak ada tag)'}\n")

        options = [
            ("1", "🤖 AI Optimasi & Regenerasi Judul, Deskripsi & Tags (Analisis CTR & Live Push)"),
            ("2", "✏️ Edit Langsung Judul Video Live"),
            ("3", "📝 Edit Langsung Deskripsi Video Live"),
            ("4", "🏷️ Edit Langsung Tags Video Live"),
            ("5", "🖼️ Upload Custom Thumbnail Baru ke Video Live (Pilih File Gambar)"),
            ("6", "🌐 Buka Video di Browser (YouTube.com)"),
            ("0", "Kembali")
        ]

        choice = select_menu(options, title="AKSI LIVE VIDEO")
        if choice == "0":
            break
        elif choice == "1":
            print_section(f"AI OPTIMASI VIDEO: {video.get('title')}")
            issue = input(f"{BOLD}Keluhan / Masalah Video [misal: 'CTR rendah, view mandek']: {RESET}").strip()
            print(f"\n{CYAN}Sedang membedah dan meregenerasi variasi judul, deskripsi & tags baru...{RESET}")
            try:
                yt_gen = YouTubeGenerator(ai_client=ai_client)
                data = yt_gen.optimize_existing_video(
                    old_title=video.get("title"),
                    old_description=video.get("description"),
                    current_issue=issue,
                    channel_profile=active_profile
                )
            except Exception as e:
                print(f"{RED}✖ Gagal optimasi video: {e}{RESET}")
                press_any_key()
                continue

            clear_screen()
            print_banner()
            print_section("HASIL REGENERASI AI (SIAP UPDATE KE LIVE YOUTUBE)")

            analysis = data.get("analysis", {})
            print(f"\n🔍 {BOLD}ANALISIS KELEMAHAN JUDUL LAMA:{RESET}")
            print(f"  {YELLOW}{analysis.get('old_title_weakness')}{RESET}")
            print(f"  {CYAN}Strategi:{RESET} {analysis.get('improvement_strategy')}\n")

            new_titles = data.get("new_titles", [])
            print(f"📌 {BOLD}5 PILIHAN JUDUL BARU (HIGH CTR):{RESET}")
            for idx, t in enumerate(new_titles, 1):
                print(f"  {BOLD}[{idx}] [{t.get('type')}]{RESET} ➔ {GREEN}{BOLD}{t.get('title')}{RESET}")
            
            new_desc = data.get("new_description", {}).get("full_formatted_description", "")
            new_tags = data.get("new_tags_comma_separated", "")

            print(f"\n🏷️  {BOLD}TAGS BARU:{RESET} {DIM}{new_tags}{RESET}")

            # Pilihan Push Live
            print_section("PILIHAN PENERAPAN")
            print(f" • Ketik angka {GREEN}1 - {len(new_titles)}{RESET} untuk menerapkan judul tersebut dan {BOLD}UPDATE LIVE LANGSUNG KE YOUTUBE{RESET}")
            print(f" • Ketik {CYAN}S{RESET} untuk simpan ke file teks lokal saja")
            print(f" • Ketik {RED}0{RESET} untuk batal")

            apply_sel = input(f"\n{BOLD}Pilihan Anda:{RESET} ").strip()
            if apply_sel.isdigit() and 1 <= int(apply_sel) <= len(new_titles):
                chosen_idx = int(apply_sel) - 1
                chosen_title = new_titles[chosen_idx].get("title")

                confirm = get_single_key(f"\n{YELLOW}Konfirmasi: Update video '{v_id}' di YouTube dengan judul '{chosen_title}'? [Y/N]: {RESET}", valid_keys=['y', 'n', '0'])
                if confirm.lower() == 'y':
                    print(f"\n{CYAN}Mengirim update ke server YouTube Data API...{RESET}")
                    ok_u, res_u = yt_live.update_video_metadata(
                        video_id=v_id,
                        title=chosen_title,
                        description=new_desc if new_desc else None,
                        tags=new_tags if new_tags else None,
                        channel_id=ch_id
                    )
                    if ok_u:
                        print(f"\n{GREEN}{BOLD}🎉 SUKSES! Video YouTube telah diperbarui secara LIVE!{RESET}")
                        print(f" 🎬 Judul Baru : {GREEN}{chosen_title}{RESET}")
                        video["title"] = chosen_title
                        if new_desc: video["description"] = new_desc
                        if new_tags: video["tags"] = [t.strip() for t in new_tags.split(",")]
                    else:
                        print(f"\n{RED}✖ Gagal update live YouTube: {res_u}{RESET}")
            elif apply_sel.upper() == "S":
                txt_p, _ = yt_gen.save_video_pack(data, active_profile.get("name"), f"LIVE_{video.get('title')}")
                print(f"\n{GREEN}✔ Paket optimasi disimpan di: {txt_p}{RESET}")

            press_any_key()

        elif choice == "2":
            print_section("EDIT JUDUL VIDEO LIVE")
            print(f"Judul lama: {CYAN}{video.get('title')}{RESET}\n")
            new_t = input(f"{BOLD}Masukkan Judul Baru:{RESET} ").strip()
            if new_t and new_t != "0":
                print(f"\n{CYAN}Mengupdate judul di YouTube...{RESET}")
                ok_u, res_u = yt_live.update_video_metadata(video_id=v_id, title=new_t, channel_id=ch_id)
                if ok_u:
                    print(f"{GREEN}✔ Judul video live berhasil diperbarui!{RESET}")
                    video["title"] = new_t
                else:
                    print(f"{RED}✖ Gagal: {res_u}{RESET}")
                press_any_key()

        elif choice == "3":
            print_section("EDIT DESKRIPSI VIDEO LIVE")
            print(f"{DIM}Ketik deskripsi baru (atau 0 untuk batal):{RESET}\n")
            new_d = input(f"{BOLD}Deskripsi Baru:{RESET} ").strip()
            if new_d and new_d != "0":
                print(f"\n{CYAN}Mengupdate deskripsi di YouTube...{RESET}")
                ok_u, res_u = yt_live.update_video_metadata(video_id=v_id, description=new_d, channel_id=ch_id)
                if ok_u:
                    print(f"{GREEN}✔ Deskripsi video live berhasil diperbarui!{RESET}")
                    video["description"] = new_d
                else:
                    print(f"{RED}✖ Gagal: {res_u}{RESET}")
                press_any_key()

        elif choice == "4":
            print_section("EDIT TAGS VIDEO LIVE")
            print(f"Tags saat ini: {CYAN}{', '.join(video.get('tags', []))}{RESET}\n")
            new_tags_input = input(f"{BOLD}Tags Baru (pisahkan dengan koma):{RESET} ").strip()
            if new_tags_input and new_tags_input != "0":
                print(f"\n{CYAN}Mengupdate tags di YouTube...{RESET}")
                ok_u, res_u = yt_live.update_video_metadata(video_id=v_id, tags=new_tags_input, channel_id=ch_id)
                if ok_u:
                    print(f"{GREEN}✔ Tags video live berhasil diperbarui!{RESET}")
                    video["tags"] = [t.strip() for t in new_tags_input.split(",")]
                else:
                    print(f"{RED}✖ Gagal: {res_u}{RESET}")
                press_any_key()

        elif choice == "5":
            print_section("UPLOAD CUSTOM THUMBNAIL KE VIDEO LIVE")
            img_path = input(f"{BOLD}Path file gambar thumbnail (WebP / JPG / PNG):{RESET} ").strip().strip('"').strip("'")
            if img_path and img_path != "0" and os.path.exists(img_path):
                print(f"\n{CYAN}Mengunggah thumbnail ke video '{v_id}'...{RESET}")
                ok_t, res_t = yt_live.update_video_thumbnail(video_id=v_id, image_path=img_path, channel_id=ch_id)
                if ok_t:
                    print(f"\n{GREEN}{BOLD}🎉 SUKSES! Custom Thumbnail berhasil dipasang ke video YouTube!{RESET}")
                else:
                    print(f"\n{RED}✖ Gagal upload thumbnail: {res_t}{RESET}")
            else:
                if img_path != "0":
                    print(f"{RED}File gambar tidak ditemukan di path: {img_path}{RESET}")
            press_any_key()

        elif choice == "6":
            webbrowser.open(video.get("video_url"))
            print(f"\n{GREEN}✔ Membuka video di browser...{RESET}")
            press_any_key()

def menu_yt_manage_profiles(yt_profile_mgr):
    while True:
        clear_screen()
        print_banner()
        print_section("KELOLA PROFIL IDENTITAS CHANNEL YOUTUBE")

        profiles = yt_profile_mgr.get_profiles()
        print(f"{BOLD}Daftar Channel Terdaftar ({len(profiles)} Channel):{RESET}")
        print(f"{BOLD}{'No':<4} {'Nama Channel':<26} {'Niche':<24} {'Status'}{RESET}")
        print("-" * 65)
        for i, p in enumerate(profiles, 1):
            is_def = f"{GREEN}[Aktif]{RESET}" if p.get("is_default") else f"{DIM}(Tersimpan){RESET}"
            p_name = (p.get("name", "")[:24] + '..') if len(p.get("name", "")) > 24 else p.get("name", "")
            p_niche = (p.get("niche", "")[:22] + '..') if len(p.get("niche", "")) > 22 else p.get("niche", "")
            print(f"#{i:<3} {BOLD}{p_name:<26}{RESET} {p_niche:<24} {is_def}")
        print("-" * 65)

        options = [
            ("1", "Pilih Channel Aktif"),
            ("2", "Tambah Profil Channel Baru"),
            ("3", "Edit Profil Channel"),
            ("4", "Hapus Profil Channel"),
            ("0", "Kembali")
        ]

        choice = select_menu(options, title="AKSI PROFIL CHANNEL")
        if choice == "0":
            break
        elif choice == "1":
            p_opts = [(str(i), f"{p.get('name')} ({p.get('niche')})") for i, p in enumerate(profiles, 1)]
            p_opts.append(("0", "Batal"))
            sel = select_menu(p_opts, title="PILIH CHANNEL AKTIF")
            if sel != "0":
                target_p = profiles[int(sel) - 1]
                yt_profile_mgr.set_active_profile(target_p["id"])
                print(f"\n{GREEN}✔ Channel aktif diubah ke '{target_p.get('name')}'!{RESET}")
                press_any_key()
        elif choice == "2":
            print_section("TAMBAH PROFIL CHANNEL YOUTUBE BARU")
            print(f"{DIM}Ketik '0' untuk batal.{RESET}\n")
            name = input(f"{BOLD}Nama Channel:{RESET} ").strip()
            if name == "0" or not name: continue
            niche = input(f"{BOLD}Niche / Topik Industri:{RESET} ").strip()
            if niche == "0" or not niche: continue
            audience = input(f"{BOLD}Target Penonton:{RESET} ").strip()
            if audience == "0": continue
            tone = input(f"{BOLD}Gaya Bicara / Tone [Default: Informatif, Praktis & Profesional]:{RESET} ").strip()
            if tone == "0": continue
            tagline = input(f"{BOLD}Tagline Branding / Slogan:{RESET} ").strip()
            if tagline == "0": continue
            cta = input(f"{BOLD}Link Standar & CTA Footer [Website / WA / Sosmed]:{RESET} ").strip()
            if cta == "0": continue

            new_prof = {
                "name": name,
                "niche": niche,
                "target_audience": audience if audience else "Umum",
                "tone_of_voice": tone if tone else "Informatif, Praktis & Profesional",
                "branding_tagline": tagline if tagline else "",
                "default_links_cta": cta if cta else "",
                "channel_keywords": "",
                "is_default": False
            }
            yt_profile_mgr.add_profile(new_prof)
            print(f"\n{GREEN}✔ Channel '{name}' berhasil ditambahkan!{RESET}")
            press_any_key()
        elif choice == "3":
            p_opts = [(str(i), f"{p.get('name')} ({p.get('niche')})") for i, p in enumerate(profiles, 1)]
            p_opts.append(("0", "Batal"))
            sel = select_menu(p_opts, title="PILIH CHANNEL UNTUK DI-EDIT")
            if sel != "0":
                target_p = profiles[int(sel) - 1]
                print_section(f"EDIT CHANNEL: {target_p.get('name')}")
                print(f"{DIM}Tekan Enter untuk mempertahankan nilai lama, ketik '0' untuk batal.{RESET}\n")

                n = input(f"Nama Channel [{target_p.get('name')}]: ").strip()
                if n == "0": continue
                nic = input(f"Niche [{target_p.get('niche')}]: ").strip()
                if nic == "0": continue
                aud = input(f"Target Penonton [{target_p.get('target_audience')}]: ").strip()
                if aud == "0": continue
                ton = input(f"Tone [{target_p.get('tone_of_voice')}]: ").strip()
                if ton == "0": continue
                tag = input(f"Tagline [{target_p.get('branding_tagline')}]: ").strip()
                if tag == "0": continue
                links = input(f"Default Links / CTA [{target_p.get('default_links_cta')}]: ").strip()
                if links == "0": continue

                up_data = {}
                if n: up_data["name"] = n
                if nic: up_data["niche"] = nic
                if aud: up_data["target_audience"] = aud
                if ton: up_data["tone_of_voice"] = ton
                if tag: up_data["branding_tagline"] = tag
                if links: up_data["default_links_cta"] = links

                yt_profile_mgr.update_profile(target_p["id"], up_data)
                print(f"\n{GREEN}✔ Profil Channel berhasil diperbarui!{RESET}")
                press_any_key()
        elif choice == "4":
            p_opts = [(str(i), f"{p.get('name')} ({p.get('niche')})") for i, p in enumerate(profiles, 1)]
            p_opts.append(("0", "Batal"))
            sel = select_menu(p_opts, title="PILIH CHANNEL UNTUK DIHAPUS")
            if sel != "0":
                target_p = profiles[int(sel) - 1]
                confirm = get_single_key(f"\n{RED}Yakin ingin menghapus channel '{target_p.get('name')}'? [Y/N]: {RESET}", valid_keys=['y', 'n', '0'])
                if confirm.lower() == 'y':
                    ok, msg = yt_profile_mgr.delete_profile(target_p["id"])
                    if ok:
                        print(f"\n{GREEN}✔ {msg}{RESET}")
                    else:
                        print(f"\n{RED}✖ {msg}{RESET}")
                    press_any_key()

def menu_yt_view_history():
    print_section("RIWAYAT FILE METADATA YOUTUBE TERSIMPAN")
    if not os.path.exists(YOUTUBE_OUTPUT_DIR):
        print(f"{YELLOW}Belum ada metadata video yang pernah digenerate.{RESET}")
        press_any_key()
        return

    files_list = []
    for root, dirs, files in os.walk(YOUTUBE_OUTPUT_DIR):
        for f in files:
            if f.endswith(".txt"):
                f_path = os.path.join(root, f)
                ch_name = os.path.basename(root)
                files_list.append((f, f_path, ch_name))

    if not files_list:
        print(f"{YELLOW}Belum ada file metadata video di folder '{YOUTUBE_OUTPUT_DIR}/'.{RESET}")
        press_any_key()
        return

    # Sort descending by filename timestamp
    files_list.sort(key=lambda x: x[0], reverse=True)

    print(f"{BOLD}{'No':<4} {'Channel':<18} {'Nama File Metadata':<45}{RESET}")
    print("-" * 70)
    for idx, (fname, fpath, ch) in enumerate(files_list[:20], 1):
        fn_disp = (fname[:42] + '..') if len(fname) > 42 else fname
        print(f"#{idx:<3} {CYAN}{ch:<18}{RESET} {fn_disp:<45}")
    print("-" * 70)

    options = [(str(i), f"Buka #{i}: {fname}") for i, (fname, _, _) in enumerate(files_list[:15], 1)]
    options.append(("0", "Kembali"))

    c = select_menu(options, title="PILIH FILE METADATA UNTUK DIBUKA")
    if c != "0":
        target_fpath = files_list[int(c) - 1][1]
        try:
            if os.name == 'nt':
                os.startfile(target_fpath)
            else:
                webbrowser.open(f"file:///{os.path.abspath(target_fpath).replace('\\', '/')}")
            print(f"\n{GREEN}✔ Membuka {target_fpath}...{RESET}")
        except Exception as e:
            print(f"{RED}✖ Gagal membuka file: {e}{RESET}")
        press_any_key()

# ==========================================
# MAIN ENTRYPOINT
# ==========================================
def main():
    if os.name == 'nt':
        os.system('')

    while True:
        clear_screen()
        print_banner()

        # Status Bar
        wp = WordPressPublisher()
        sites = wp.get_sites()
        active_site = wp.get_active_site()

        client = GeminiClient(key_file="apikey.txt")
        gemini_keys_count = len(client.api_keys)
        active_model = client.get_preferred_model()

        kie = KieImageClient()
        kie_keys_count = len(kie.api_keys)
        kie_model = kie.get_preferred_model()

        yt_mgr = YouTubeProfileManager()
        active_yt_channel = yt_mgr.get_active_profile()

        if active_site:
            total_str = f" ({len(sites)} Web)" if len(sites) > 1 else ""
            type_tag = f"{CYAN}[Astro]{RESET}" if active_site.get("type") == "astro" else f"{MAGENTA}[WP]{RESET}"
            wp_status_str = f"{type_tag} {GREEN}{active_site['name']}{total_str}{RESET}"
        else:
            wp_status_str = f"{YELLOW}Belum Terdaftar{RESET}"
        
        gemini_status_str = f"{GREEN}{gemini_keys_count} Key{RESET}" if gemini_keys_count > 0 else f"{RED}0 Key (Tambahkan Key){RESET}"
        
        kie_style = kie.get_image_style()
        kie_style_name = IMAGE_STYLE_DESCS.get(kie_style, kie_style).split("(")[0].strip()
        kie_status_str = f"{GREEN}{kie_keys_count} Key{RESET} | Gaya: {MAGENTA}{kie_style_name}{RESET}" if kie_keys_count > 0 else f"{DIM}0 Key (Mesh Gradient Fallback){RESET}"

        yt_status_str = f"{GREEN}{active_yt_channel.get('name')}{RESET} ({active_yt_channel.get('niche')})"

        print(f"🤖 Gemini  : {CYAN}{BOLD}{active_model}{RESET} ({gemini_status_str})")
        print(f"🖼️  Kie.ai   : {CYAN}{BOLD}{kie_model}{RESET} ({kie_status_str})")
        print(f"🎬 YouTube : {yt_status_str}")
        print(f"🌐 Web     : {wp_status_str}")
        print(f"{DIM}{'-' * 60}{RESET}")

        menu_options = [
            ("1", "Riset & Buat Artikel Silo"),
            ("2", "Publish Artikel ke Web"),
            ("3", "Export ke WordPress XML"),
            ("4", "Kelola Live WordPress"),
            ("5", "Inventori & Status Artikel"),
            ("6", "Pengaturan Website"),
            ("7", "Pengaturan AI & API Key"),
            ("8", "🎬 YouTube Channel & Metadata Suite"),
            ("0", "Keluar")
        ]

        pilihan = select_menu(menu_options, title="MENU UTAMA")

        if pilihan == "1":
            menu_generate_silo()
        elif pilihan == "2":
            menu_push_wordpress()
        elif pilihan == "3":
            menu_export_silo_wxr()
        elif pilihan == "4":
            menu_manage_live_wp(wp)
        elif pilihan == "5":
            menu_view_inventory()
        elif pilihan == "6":
            menu_configure_wordpress()
        elif pilihan == "7":
            menu_ai_settings()
        elif pilihan == "8":
            menu_youtube()
        elif pilihan == "0":
            print(f"\n{GREEN}Terima kasih telah menggunakan AI Silo Builder! Sampai jumpa.{RESET}\n")
            sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Program dihentikan oleh pengguna.{RESET}")
        sys.exit(0)
