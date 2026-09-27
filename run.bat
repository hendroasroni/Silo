@echo off
setlocal
cd /d "%~dp0"
chcp 65001 > nul

:: Cek keberadaan Python di sistem
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo ================================================================
    echo [ERROR] Python tidak terdeteksi di sistem atau belum masuk ke PATH!
    echo Silakan install Python dari https://www.python.org/
    echo ================================================================
    pause
    exit /b 1
)

:: Jika dibuka dari CMD biasa (double click), otomatis alihkan ke PowerShell / Windows Terminal
:: agar seluruh icon emoji, karakter unicode, dan warna ANSI tampil jernih & sempurna 100%
if "%~1"=="" (
    where wt.exe > nul 2>&1
    if %errorlevel% equ 0 (
        start wt.exe -d "%~dp0" powershell.exe -NoExit -ExecutionPolicy Bypass -Command "$Host.UI.RawUI.WindowTitle='🏛️ AI Silo Content & YouTube Suite'; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; python main.py; exit"
        exit /b 0
    )
    
    start powershell.exe -NoExit -ExecutionPolicy Bypass -Command "$Host.UI.RawUI.WindowTitle='🏛️ AI Silo Content & YouTube Suite'; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; python main.py; exit"
    exit /b 0
)

:: Direct execution jika dipanggil langsung dari terminal
python main.py
if %errorlevel% neq 0 (
    echo.
    echo [INFO] Program selesai dengan kode: %errorlevel%
    pause
)
