@echo off
title Deneyap Depo - SQL Server Kurulum Sihirbazi
REM SQL Server'i bulur, veritabanini olusturur, SQLite verilerini tasir ve .env dosyasini yazar.
REM Ek secenekler icin:  SQL_Server_Kurulum.bat --help

setlocal
cd /d "%~dp0"
call "%~dp0_ortam.bat"
if errorlevel 1 ( echo. & pause & exit /b 1 )

echo Gerekli paketler kontrol ediliyor...
"%VPY%" -m pip install --disable-pip-version-check -q -r backend\requirements.txt -r backend\requirements-mssql.txt
if errorlevel 1 (
    "%VPY%" -c "import fastapi, sqlalchemy, pyodbc" >nul 2>&1
    if errorlevel 1 ( echo [HATA] Paketler kurulamadi. Internet baglantisini kontrol edin. & pause & exit /b 1 )
)

cd backend
"%VPY%" mssql_kurulum.py %*
echo.
pause
