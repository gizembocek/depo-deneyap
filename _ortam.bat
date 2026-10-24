@echo off
REM Ortak hazirlik: Python'u bulur ve sanal ortami (venv klasoru) hazirlar.
REM Diger .bat dosyalari bunu "call _ortam.bat" ile kullanir; basariliysa VPY degiskeni hazirdir.
REM Python kaldirilip baska surum kurulduysa calismayan eski venv klasoru otomatik yenilenir.
set "PY="
python --version >nul 2>&1 && set "PY=python"
if not defined PY ( py -3 --version >nul 2>&1 && set "PY=py -3" )
if not defined PY goto :python_yok
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 goto :python_eski

set "VENV=%~dp0venv"
set "VPY=%~dp0venv\Scripts\python.exe"
if not exist "%VPY%" goto :olustur
"%VPY%" -c "import sys" >nul 2>&1
if not errorlevel 1 exit /b 0

echo [!] Sanal ortam bu bilgisayarda artik bulunmayan bir Python surumuyle kurulmus.
echo     Yuklu Python ile yeniden kuruluyor. Verileriniz bundan etkilenmez.
rmdir /s /q "%VENV%"
if exist "%VENV%" goto :silinemedi

:olustur
echo Sanal ortam olusturuluyor, ilk seferde birkac dakika surebilir...
%PY% -m venv "%VENV%"
if errorlevel 1 goto :olusturulamadi
exit /b 0

:python_yok
echo [HATA] Bilgisayarda Python kurulu degil.
echo Lutfen https://www.python.org/downloads/ adresinden Python 3.10 veya ustunu kurun.
echo ONEMLI: Kurulumun ilk ekraninda "Add python.exe to PATH" kutusunu isaretleyin.
exit /b 1

:python_eski
echo [HATA] Bilgisayardaki Python surumu cok eski. Python 3.10 veya ustu gerekir.
echo https://www.python.org/downloads/ adresinden guncel surumu kurun.
exit /b 1

:silinemedi
echo [HATA] Eski venv klasoru silinemedi. Acik bir siyah pencere veya program onu kullaniyor olabilir.
echo Tum Deneyap pencerelerini kapatin ya da bilgisayari yeniden baslatip tekrar deneyin.
exit /b 1

:olusturulamadi
echo [HATA] Sanal ortam olusturulamadi.
exit /b 1
