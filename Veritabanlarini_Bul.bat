@echo off
title Deneyap Depo - Veritabanlarini Bul
REM Bu bilgisayardaki tum Deneyap Depo veritabanlarini (SQL Server ve SQLite) bulur ve karsilastirir.
REM Veritabanlarinda HICBIR SEYI DEGISTIRMEZ, yalnizca okur.

setlocal
cd /d "%~dp0"
call "%~dp0_ortam.bat"
if errorlevel 1 ( echo. & pause & exit /b 1 )
"%VPY%" -c "import sqlalchemy, dotenv, pyodbc" >nul 2>&1
if errorlevel 1 (
    echo Gerekli paketler kuruluyor, internet gerekir...
    "%VPY%" -m pip install --disable-pip-version-check -q -r backend\requirements.txt -r backend\requirements-mssql.txt
)
cd backend
"%VPY%" veritabani_bul.py
echo.
pause
