@echo off
REM Gelistirici modu: kod degisince sunucu otomatik yeniden baslar. Sadece bu bilgisayardan erisilir.
setlocal
cd /d "%~dp0"
call "%~dp0_ortam.bat"
if errorlevel 1 ( echo. & pause & exit /b 1 )
"%VPY%" -c "import fastapi, uvicorn" >nul 2>&1 || "%VPY%" -m pip install --disable-pip-version-check -q -r backend\requirements.txt
cd backend
"%VPY%" -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
pause
