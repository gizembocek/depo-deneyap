"""
Çevrim içi deneme sürümünün (Netlify) örnek verilerini GERÇEK sunucu kodunu kullanarak üretir.

Geçici bir SQLite veritabanına örnek atölye verisi (seed.py) ve gerçekçi işlemler (stok
hareketleri, giriş/çıkış işlemleri) yüklenir; ardından arayüzün çağırdığı API yanıtları ve örnek
PDF/Excel raporları demo/veri klasörüne kaydedilir. Böylece deneme sürümü, kurulu sistemle aynı
verileri ve ekranları gösterir.

Çalıştırma (proje klasöründe):  python demo/olustur.py   (Python ve backend/requirements.txt paketleri gerekir)
Ardından deneme sitesini yerelde görmek için:  sh demo/netlify_build.sh  ve  python -m http.server -d demo/_site
Gerçek veritabanınıza dokunulmaz.
"""
import contextlib
import io
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

PROJE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(PROJE, "backend")
CIKTI = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PROJE, "demo", "veri")  # testler geçici klasör verir

_TMP = tempfile.mkdtemp(prefix="deneyap_demo_")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_TMP, "demo.db").replace("\\", "/")
os.environ["SECRET_KEY"] = "demo-uretimi-0123456789abcdef0123456789"
os.environ["UPLOAD_DIR"] = os.path.join(_TMP, "uploads")
os.environ["YEDEK_KLASORU"] = os.path.join(_TMP, "yedekler")
sys.path.insert(0, BACKEND)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

import main  # noqa: E402
import seed  # noqa: E402
from auth import create_access_token  # noqa: E402
from database import SessionLocal, engine  # noqa: E402
from models import Product, User  # noqa: E402
from settings_store import set_setting  # noqa: E402


def hazirla_veritabani():
    with contextlib.redirect_stdout(io.StringIO()):  # seed.py'nin geçici şifre çıktısı gereksiz
        seed.seed_database()
    s = SessionLocal()
    try:
        set_setting(s, "atolye_adi", "Örnek Deneyap Teknoloji Atölyesi")
        set_setting(s, "il", "Ankara")
        for u in s.query(User).all():
            if u.role == "admin":
                u.full_name, u.email = "Demo Yönetici", "demo@deneyap.org"
            else:
                u.full_name, u.email = "Ayşe Eğitmen", "egitmen@deneyap.org"
        for p in s.query(Product).all():
            p.image_url = None  # örnek görseller depoda yok
        s.commit()
        admin = s.query(User).filter(User.role == "admin").first()
        return create_access_token({"sub": admin.id}, user=admin), admin.id
    finally:
        s.close()


def islemler_olustur(c, h):
    def ok(r):
        assert r.status_code in (200, 201), (r.request.url, r.status_code, r.text[:300])
        return r.json()

    urunler = c.get("/api/products/?per_page=200&sort=name", headers=h).json()

    def bul(ad):
        """Örnek listedeki (assets/malzeme_listesi.json) ürünü adıyla bulur; yoksa hata verir."""
        for p in urunler:
            if p["name"].strip().lower() == ad.lower():
                return p
        raise AssertionError(f"Örnek listede yok: {ad}")

    def stok(ad, islem, miktar, not_):
        ok(c.post(f"/api/products/{bul(ad)['id']}/stock", json={"action": islem, "quantity": miktar, "note": not_}, headers=h))

    # Derslerde kullanım, yeni alım ve sayım düzeltmeleri (stok hareketleri)
    stok("Krokodil Kablo", "remove", 12, "Enerji Teknolojileri - devre kurma etkinliği")
    stok("Deney Ampulü", "remove", 6, "Enerji Teknolojileri - seri/paralel bağlantı")
    stok("1 W Güneş Paneli", "remove", 4, "Güneş enerjisi proje haftası")
    stok("Sıcak Silikon Mumu", "remove", 40, "Tasarım ve Üretim - maket çalışması")
    stok("Gıda Boyası", "remove", 3, "Malzeme Bilimi deneyi")
    stok("AA Şarj Edilebilir Kalem Pil", "add", 24, "Yeni alım (fatura no: 2026/118)")
    stok("Koli Bandı", "remove", 5, "Ekipman paketleme")
    stok("Dijital Multimetre 600V 10 A", "remove", 2, "Arızalı; tamire ayrıldı")

    # Birkaç sarf malzemesi kritik seviyede (ana paneldeki uyarılar için)
    for ad in ["AAA Kalem Pil", "AA Kalem Pil", "Çakmak", "İspirto Ocağı Yakıtı", "Saf Su", "Plastik Kaşık Seti"]:
        guncel = c.get(f"/api/products/{bul(ad)['id']}", headers=h).json()
        dusur = max(0, guncel["current_stock"] - max(0, guncel["critical_stock"] - 2))
        if dusur:
            stok(ad, "remove", dusur, "Dönem sonu sayımı")

    bozuk = bul("Analog Multimetre")
    ok(c.put(f"/api/products/{bozuk['id']}", json={"status": "Bozuk / Kırık"}, headers=h))

    # Giriş ve çıkış işlemleri
    gelen = ok(c.post("/api/shipments/", json={
        "name": "Ekim 2026 enerji seti gönderimi", "shipment_type": "Giriş",
        "notes": "Bölge koordinatörlüğünden gelen koli (2 koli)",
        "items": [{"product_id": bul("Krokodil Kablo")["id"], "expected_quantity": 50},
                  {"product_id": bul("Deney Ampul Duyu")["id"], "expected_quantity": 30},
                  {"product_id": bul("DC Fan")["id"], "expected_quantity": 20}],
    }, headers=h))
    ayrinti = c.get(f"/api/shipments/{gelen['id']}", headers=h).json()
    ok(c.put(f"/api/shipments/{gelen['id']}/check", json=[
        {"item_id": ayrinti["items"][0]["id"], "actual_quantity": 50},
        {"item_id": ayrinti["items"][1]["id"], "actual_quantity": 26},
        {"item_id": ayrinti["items"][2]["id"], "actual_quantity": 20},
    ], headers=h))
    ok(c.post("/api/shipments/", json={
        "name": "Kasım 2026 ölçüm aletleri", "shipment_type": "Giriş", "notes": "Kargo yolda, gelince sayılacak",
        "items": [{"product_id": bul("Lüxmetre")["id"], "expected_quantity": 6},
                  {"product_id": bul("Anemometre")["id"], "expected_quantity": 6}],
    }, headers=h))
    ok(c.post("/api/shipments/", json={
        "name": "Arızalı multimetreler", "shipment_type": "Çıkış", "outgoing_reason": "Tamir",
        "notes": "Yetkili servise gönderildi",
        "items": [{"product_id": bul("Dijital Multimetre 600V 10 A")["id"], "expected_quantity": 1}],
    }, headers=h))


def tarihleri_yay():
    """Kayıtlar aynı ana yığılmasın: işlemleri son birkaç haftaya dağıt."""
    simdi = datetime.now(timezone.utc).replace(tzinfo=None)
    with engine.begin() as conn:
        ids = [r[0] for r in conn.execute(text("SELECT id FROM stock_logs ORDER BY id"))]
        n = len(ids)
        for i, log_id in enumerate(ids):
            t = simdi - timedelta(days=(n - i) * 0.6, hours=i % 7)
            conn.execute(text("UPDATE stock_logs SET created_at=:t WHERE id=:i"), {"t": t, "i": log_id})
        sids = [r[0] for r in conn.execute(text("SELECT id FROM shipments ORDER BY id"))]
        for i, sid in enumerate(sids):
            t = simdi - timedelta(days=(len(sids) - i) * 4)
            conn.execute(text("UPDATE shipments SET created_at=:t WHERE id=:i"), {"t": t, "i": sid})


def kaydet(c, h):
    os.makedirs(CIKTI, exist_ok=True)

    def al(yol):
        r = c.get(yol, headers=h)
        assert r.status_code == 200, (yol, r.status_code, r.text[:200])
        return r.json()

    urunler = []
    sayfa = 1
    while True:
        r = c.get(f"/api/products/?per_page=200&page={sayfa}&sort=newest", headers=h)
        urunler += r.json()
        if len(urunler) >= int(r.headers["X-Total-Count"]):
            break
        sayfa += 1
    depolar = al("/api/warehouses/")
    gonderimler = al("/api/shipments/")
    veri = {
        "olusturma": datetime.now().isoformat(timespec="seconds"),
        "me": al("/api/auth/me"),
        "setup_status": al("/api/auth/setup-status"),
        "settings": al("/api/settings"),
        "products": urunler,
        "stats": al("/api/products/stats"),
        "warehouses": depolar,
        "structures": {str(w["id"]): al(f"/api/warehouses/{w['id']}/structure") for w in depolar},
        "courses": al("/api/courses/"),
        "shipments": gonderimler,
        "shipment_details": {str(s["id"]): al(f"/api/shipments/{s['id']}") for s in gonderimler},
        "logs": al("/api/reports/logs?limit=1000"),
        "product_logs": {str(p["id"]): al(f"/api/products/{p['id']}/logs") for p in urunler},
        "users": al("/api/auth/users"),
        "db_check": al("/api/admin/db-check"),
    }
    with open(os.path.join(CIKTI, "demo-veri.json"), "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, separators=(",", ":"))
    for yol, ad in [("/api/reports/export/pdf", "ornek_stok_raporu.pdf"),
                    ("/api/reports/export/excel", "ornek_stok_raporu.xlsx"),
                    ("/api/products/import/template", "deneyap_urun_sablonu.xlsx")]:
        r = c.get(yol, headers=h)
        assert r.status_code == 200, yol
        with open(os.path.join(CIKTI, ad), "wb") as f:
            f.write(r.content)
    return veri


def main_():
    token, _ = hazirla_veritabani()
    h = {"Authorization": f"Bearer {token}"}
    with TestClient(main.app) as c:
        islemler_olustur(c, h)
        tarihleri_yay()
        veri = kaydet(c, h)
    print(f"[OK] Demo verisi: {len(veri['products'])} ürün, {len(veri['warehouses'])} depo, "
          f"{len(veri['shipments'])} işlem, {len(veri['logs'])} stok kaydı -> {CIKTI}")


if __name__ == "__main__":
    main_()
