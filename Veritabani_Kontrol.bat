@echo off
title Deneyap Depo - Veritabani Kontrolu
REM Veritabanini denetler (hicbir seyi degistirmez). Duzeltmek icin:  Veritabani_Kontrol.bat --duzelt
setlocal
cd /d "%~dp0"
call "%~dp0_ortam.bat"
if errorlevel 1 ( echo. & pause & exit /b 1 )
"%VPY%" -c "import fastapi, sqlalchemy, dotenv" >nul 2>&1
if errorlevel 1 (
    echo Gerekli paketler kuruluyor...
    "%VPY%" -m pip install --disable-pip-version-check -q -r backend\requirements.txt
)
if exist "backend\.env" (
    findstr /i /r "^DB_BACKEND=mssql" "backend\.env" >nul 2>&1 && "%VPY%" -m pip install --disable-pip-version-check -q -r backend\requirements-mssql.txt
)
cd backend
"%VPY%" veritabani_kontrol.py %*
echo.
pause
