@echo off
REM Otomatik testleri calistirir. Gercek veritabaniniza dokunulmaz (gecici veritabani kullanilir).
setlocal
cd /d "%~dp0"
call "%~dp0_ortam.bat"
if errorlevel 1 ( echo. & pause & exit /b 1 )
"%VPY%" -m pip install --disable-pip-version-check -q -r backend\requirements-dev.txt
cd backend
"%VPY%" -m pytest
echo.
echo Tarayici (arayuz) testleri icin:  pip install playwright  ve  python -m playwright install chromium
echo ardindan backend klasorunde:     python -m pytest tests_e2e
pause
