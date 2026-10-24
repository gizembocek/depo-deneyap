@echo off
REM Tailwind CSS dosyasini yeniden uretir (Node.js kurulu olmalidir).
cd /d "%~dp0"
npx --yes tailwindcss@3.4.17 -c tailwind.config.js -i src.css -o app.css --minify
pause
