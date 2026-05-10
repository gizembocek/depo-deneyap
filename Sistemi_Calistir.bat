@echo off
title Deneyap Depo Sistemi
echo ===================================================
echo Deneyap Depo Sistemi Baslatiliyor...
echo Lutfen bekleyin. Eger ilk kez calistiriyorsaniz, 
echo gerekli kutuphanelerin inmesi 1-2 dakika surebilir.
echo ===================================================

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [HATA] Bilgisayarinda Python kurulu degil!
    echo Sistemi calistirmak icin Python'a ihtiyacimiz var.
    echo Lutfen https://www.python.org/downloads/ adresinden Python'i indirip kurun.
    echo.
    echo ONEMLI: Kurulum sirasinda en alttaki "Add python.exe to PATH" secenegini isaretlemeyi kesinlikle unutmayin.
    echo.
    pause
    exit /b
)

echo.
echo [1/2] Kutuphaneler kontrol ediliyor...
cd backend
python -m pip install -r requirements.txt >nul 2>&1

echo.
echo [2/2] Sunucu baslatiliyor...
echo ===================================================
echo Tarayiciniz otomatik olarak acilacaktir.
echo.
echo CIKIS YAPMAK ICIN: Bu siyah ekrani kapatmaniz yeterlidir.
echo ===================================================

:: Start the browser with a 2 second delay to ensure server is up
start "" "http://localhost:8000"

:: Start the Uvicorn server
python -m uvicorn main:app --host 0.0.0.0 --port 8000

pause
