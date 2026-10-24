@echo off
title Deneyap Depo - SQL Server Testleri
REM Tum otomatik testleri SQL Server uzerinde GECICI veritabanlarinda calistirir.
REM Gercek veritabaniniza dokunulmaz; gecici veritabanlari sonunda silinir.

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

"%VPY%" -m pip install --disable-pip-version-check -q -r backend\requirements-dev.txt
cd backend
"%VPY%" mssql_kurulum.py --test %*
echo.
pause
