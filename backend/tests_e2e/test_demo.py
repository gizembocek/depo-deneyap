"""
Çevrim içi deneme sürümü (Netlify, demo/ klasörü): örnek veriler gerçek sunucu kodundan üretilebilmeli
ve deneme sitesi tarayıcıda hatasız açılmalı.
"""
import functools
import http.server
import json
import os
import shutil
import socket
import subprocess
import sys
import threading

import pytest

playwright_api = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect  # noqa: E402

PROJE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEMO = os.path.join(PROJE, "demo")


def _utf8_ortam(**ekstra):
    return {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", **ekstra}


def test_demo_verisi_sunucu_kodundan_uretilir(tmp_path):
    env = _utf8_ortam()
    for k in ("DATABASE_URL", "TEST_DATABASE_URL"):
        env.pop(k, None)
    r = subprocess.run([sys.executable, os.path.join(DEMO, "olustur.py"), str(tmp_path)], cwd=PROJE, env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    veri = json.loads((tmp_path / "demo-veri.json").read_text(encoding="utf-8"))
    assert len(veri["products"]) == 77 and veri["stats"]["low_stock_count"] >= 6
    assert all(p["image_url"] is None for p in veri["products"])
    assert {u["email"] for u in veri["users"]} == {"demo@deneyap.org", "egitmen@deneyap.org"}
    for ad in ("ornek_stok_raporu.pdf", "ornek_stok_raporu.xlsx", "deneyap_urun_sablonu.xlsx"):
        assert (tmp_path / ad).stat().st_size > 1000


@pytest.mark.skipif(shutil.which("sh") is None, reason="sh yok (Windows)")
def test_deneme_sitesi_tarayicida_calisir(tmp_path, browser):
    site = tmp_path / "demo"
    shutil.copytree(DEMO, site, ignore=shutil.ignore_patterns("_site"))
    shutil.copytree(os.path.join(PROJE, "frontend"), tmp_path / "frontend")
    shutil.copytree(os.path.join(PROJE, "assets"), tmp_path / "assets")
    r = subprocess.run(["sh", str(site / "netlify_build.sh")], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site / "_site"))
    handler.log_message = lambda *a: None
    sunucu = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    hatalar = []
    try:
        ctx = browser.new_context(viewport={"width": 1366, "height": 900}, locale="tr-TR")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: hatalar.append(str(e)))
        pg.on("console", lambda m: hatalar.append(m.text) if m.type == "error" else None)
        pg.goto(f"http://127.0.0.1:{port}/")
        expect(pg.locator("h1", has_text="Ana Panel")).to_be_visible(timeout=15000)
        expect(pg.locator("#demoEtiketi")).to_contain_text("DENEME SÜRÜMÜ")
        for sayfa, metin in [("products", "Ürün Yönetimi"), ("warehouses", "Depo"), ("shipments", "Giriş / Çıkış"),
                             ("courses", "Ders"), ("reports", "Rapor"), ("users", "Kullanıcı"), ("settings", "Ayarlar")]:
            pg.click(f"[data-page={sayfa}]")
            expect(pg.locator("#pageContent h1").first).to_contain_text(metin)
        pg.click("[data-page=products]")
        pg.fill("#globalSearch", "GUNES PANELI")
        expect(pg.locator(".product-card", has_text="Güneş Paneli").first).to_be_visible()
        pg.click("#addProductBtn")
        pg.fill("#pfName", "Deneme")
        pg.click("#productSubmitBtn")
        expect(pg.locator("#toastContainer", has_text="deneme sürümüdür")).to_be_visible()
        ctx.close()
    finally:
        sunucu.shutdown()
    assert not hatalar, hatalar
