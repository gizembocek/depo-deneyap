@echo off
setlocal
title Deneyap Depo Sistemi
cd /d "%~dp0"
echo ===================================================
echo   DENEYAP DEPO VE STOK YONETIM SISTEMI
echo ===================================================
echo.

REM ---- 1) Python ve sanal ortam (ilk calistirmada olusturulur) ----
echo [1/3] Python ve sanal ortam kontrol ediliyor...
call "%~dp0_ortam.bat"
if errorlevel 1 ( echo. & pause & exit /b 1 )

REM ---- 2) Paketler ----
echo [2/3] Gerekli paketler kontrol ediliyor (ilk seferde 1-3 dakika surebilir)...
"%VPY%" -m pip install --disable-pip-version-check -q -r backend\requirements.txt
if errorlevel 1 (
    "%VPY%" -c "import fastapi, sqlalchemy, uvicorn, reportlab, openpyxl" >nul 2>&1
    if errorlevel 1 (
        echo [HATA] Paketler kurulamadi. Internet baglantinizi kontrol edip tekrar deneyin.
        pause
        exit /b 1
    )
    echo [UYARI] Paketler guncellenemedi ^(internet yok olabilir^). Mevcut paketlerle devam ediliyor.
)
if exist "backend\.env" (
    findstr /i /r "^DB_BACKEND=mssql" "backend\.env" >nul 2>&1 && "%VPY%" -m pip install --disable-pip-version-check -q -r backend\requirements-mssql.txt
)

REM ---- 3) Sunucu ----
echo [3/3] Sunucu baslatiliyor...
echo.
echo ===================================================
echo   Bu bilgisayardan:  http://localhost:8000
echo   Atolyedeki diger bilgisayar/tabletlerden: http://BU-BILGISAYARIN-IP:8000
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do for /f "tokens=*" %%b in ("%%a") do echo      ornek: http://%%b:8000
echo   (Windows guvenlik duvari sorarsa "Erisime izin ver" deyin.)
echo.
echo   KAPATMAK ICIN: bu pencereyi kapatin.
echo ===================================================
echo.
REM Tarayici, sunucu gercekten hazir olunca acilir (en fazla 2 dakika bekler)
start "" /b "%VPY%" "%~dp0backend\tarayici_ac.py" http://localhost:8000
cd backend
"%VPY%" -m uvicorn main:app --host 0.0.0.0 --port 8000
echo.
echo Sunucu durdu. Yukarida kirmizi bir hata varsa ekran goruntusunu alin.
pause
