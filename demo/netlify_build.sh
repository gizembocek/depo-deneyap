#!/bin/sh
# Netlify için çevrim içi deneme sitesini (_site) hazırlar.
# Sunucu ve Python gerekmez: arayüz dosyaları + örnek veriler + demo.js birleştirilir.
# Yerelde denemek için (demo klasöründe):  sh netlify_build.sh  ve  python -m http.server -d _site
set -e
cd "$(dirname "$0")"
rm -rf ./_site
mkdir -p ./_site/static ./_site/demo
cp -R ../frontend/. ./_site/static/
cp -R ../assets ./_site/assets
cp ./veri/* ./_site/demo/
cp ./demo.js ./_site/static/js/demo.js
# Deneme betiğini api.js'den hemen sonra yükle
sed 's#\(<script src="/static/js/api.js[^"]*"></script>\)#\1\n    <script src="/static/js/demo.js"></script>#' ../frontend/index.html > ./_site/index.html
grep -q 'static/js/demo.js' ./_site/index.html || { echo "demo.js index.html'e eklenemedi"; exit 1; }
echo "Deneme sitesi hazır: $(pwd)/_site"
