@echo off
title AI Silo Builder & YouTube Automation Suite
chcp 65001 > nul
cd /d "%~dp0"

echo ================================================================
echo   🏛️  MEMULAI AI SILO BUILDER & YOUTUBE AUTOMATION SUITE
echo ================================================================
echo.

:: Cek keberadaan Python di sistem
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python tidak terdeteksi di sistem atau belum masuk ke PATH!
    echo Silakan install Python dari https://www.python.org/ atau tambahkan ke PATH.
    echo.
    pause
    exit /b 1
)

:: Jalankan main.py
python main.py

if %errorlevel% neq 0 (
    echo.
    echo [INFO] Program selesai dengan kode keluar: %errorlevel%
    pause
)
