#!/usr/bin/env bash
# ==============================================================================
#  AUTO SETUP & RUN SCRIPT UNTUK LINUX VPS (Ubuntu / Debian / CentOS / AlmaLinux)
#  AI Silo Content & YouTube Automation Suite
# ==============================================================================

set -e

# Warna Terminal
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

clear 2>/dev/null || true
echo -e "${CYAN}${BOLD}===========================================================================${NC}"
echo -e "${CYAN}${BOLD}     🚀 AUTO-INSTALLER & REQUIREMENT CHECKER - LINUX VPS SETUP            ${NC}"
echo -e "${CYAN}${BOLD}===========================================================================${NC}"
echo ""

# 1. Deteksi Direktori Script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 2. Deteksi Package Manager & OS
echo -e "${YELLOW}[1/5] Memeriksa Paket Sistem & Lingkungan OS...${NC}"
PKG_MANAGER=""
INSTALL_CMD=""

if command -v apt-get &> /dev/null; then
    PKG_MANAGER="apt"
    INSTALL_CMD="sudo apt-get update -y && sudo apt-get install -y"
elif command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
    INSTALL_CMD="sudo dnf install -y"
elif command -v yum &> /dev/null; then
    PKG_MANAGER="yum"
    INSTALL_CMD="sudo yum install -y"
elif command -v pacman &> /dev/null; then
    PKG_MANAGER="pacman"
    INSTALL_CMD="sudo pacman -Sy --noconfirm"
fi

# 3. Cek & Install Python3, Pip, Venv, Git
MISSING_PKGS=()

if ! command -v python3 &> /dev/null; then
    MISSING_PKGS+=("python3")
fi

if ! command -v git &> /dev/null; then
    MISSING_PKGS+=("git")
fi

if ! command -v curl &> /dev/null; then
    MISSING_PKGS+=("curl")
fi

if [ ${#MISSING_PKGS[@]} -ne 0 ]; then
    echo -e "${YELLOW}[!] Paket sistem belum lengkap: ${MISSING_PKGS[*]}.${NC}"
    echo -e "${CYAN}[*] Menginstall dependensi sistem via ${PKG_MANAGER}...${NC}"
    if [ "$PKG_MANAGER" == "apt" ]; then
        sudo apt-get update -y
        sudo apt-get install -y python3 python3-pip python3-venv git curl
    elif [ "$PKG_MANAGER" == "dnf" ] || [ "$PKG_MANAGER" == "yum" ]; then
        $INSTALL_CMD python3 python3-pip git curl
    fi
    echo -e "${GREEN}[OK] Dependensi sistem berhasil dipasang!${NC}"
else
    echo -e "${GREEN}[OK] Python3, Git, dan Curl sudah terpasang di VPS.${NC}"
fi

# 4. Verifikasi Versi Python
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}[OK] Versi Python terdeteksi: Python ${PY_VER}${NC}"

# 5. Setup Python Virtual Environment (.venv) - Standar Modern Linux
echo -e "\n${YELLOW}[2/5] Mengatur Virtual Environment Python (.venv)...${NC}"
if [ ! -d ".venv" ]; then
    echo -e "${CYAN}[*] Membuat virtual environment baru di .venv/...${NC}"
    # Pastikan python3-venv terinstall jika di Ubuntu/Debian
    if [ "$PKG_MANAGER" == "apt" ]; then
        sudo apt-get install -y python3-venv python3-full 2>/dev/null || true
    fi
    python3 -m venv .venv
    echo -e "${GREEN}[OK] Virtual environment .venv berhasil dibuat.${NC}"
fi

# Aktivasi Venv
source .venv/bin/activate
echo -e "${GREEN}[OK] Virtual environment aktif: $(which python)${NC}"

# 6. Upgrade Pip & Install Dependensi Python
echo -e "\n${YELLOW}[3/5] Memeriksa & Menginstall Dependensi Python (requirements.txt)...${NC}"
pip install --upgrade pip --quiet 2>/dev/null || true

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
    echo -e "${GREEN}[OK] Seluruh dependensi Python (requests, markdown, pillow, google-api) siap!${NC}"
else
    pip install requests markdown pillow google-auth google-auth-oauthlib google-api-python-client --quiet
    echo -e "${GREEN}[OK] Dependensi default berhasil dipasang.${NC}"
fi

# 7. Memeriksa Kunci API (config/apikey.txt)
echo -e "\n${YELLOW}[4/5] Memeriksa Konfigurasi Kunci API...${NC}"
APIKEY_FILE="config/apikey.txt"
if [ ! -f "$APIKEY_FILE" ] || [ ! -s "$APIKEY_FILE" ]; then
    echo -e "${YELLOW}[!] File '${APIKEY_FILE}' belum berisi API Key Gemini.${NC}"
    mkdir -p config
    read -rp "Masukkan Google Gemini API Key Anda (atau tekan Enter untuk lewati): " user_key
    if [ -n "$user_key" ]; then
        echo "$user_key" > "$APIKEY_FILE"
        echo -e "${GREEN}[OK] API Key berhasil disimpan ke ${APIKEY_FILE}!${NC}"
    else
        echo -e "${YELLOW}[INFO] Anda dapat menambahkan key nanti di menu aplikasi atau via 'nano config/apikey.txt'.${NC}"
    fi
else
    KEY_COUNT=$(grep -v '^#' "$APIKEY_FILE" | grep -v '^[[:space:]]*$' | wc -l)
    echo -e "${GREEN}[OK] File '${APIKEY_FILE}' ditemukan (${KEY_COUNT} Key aktif).${NC}"
fi

# 8. Siap Dijalankan
echo -e "\n${GREEN}${BOLD}[5/5] SELURUH REQUIREMENT TERPENUHI! SISTEM SIAP DIGUNAKAN.${NC}"
echo -e "${CYAN}---------------------------------------------------------------------------${NC}"
echo -e "${BOLD}Tips Menjalankan di Background VPS (24/7 Autopilot):${NC}"
echo -e "  1. Buat session tmux:   ${YELLOW}tmux new -s silo${NC}"
echo -e "  2. Jalankan aplikasi :  ${YELLOW}./setup_vps.sh${NC} (atau ${YELLOW}python3 main.py${NC})"
echo -e "  3. Detach session    :  Tekan ${BOLD}Ctrl+B${NC} lalu tekan ${BOLD}D${NC}"
echo -e "  4. Buka kembali nanti:  ${YELLOW}tmux attach -t silo${NC}"
echo -e "${CYAN}---------------------------------------------------------------------------${NC}"
echo ""

read -rp "Tekan [ENTER] untuk langsung menjalankan aplikasi (atau Ctrl+C untuk keluar)..." dummy
echo ""

# Jalankan main.py
python3 main.py
