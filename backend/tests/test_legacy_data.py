"""
Var olan bir atölye veritabanının yeni sürümle sorunsuz çalıştığını doğrular:
  - 'ornek': eski sürümle (v1) oluşmuş veritabanının taklidi (tests/eski_veri.py) — her yerde çalışır
  - 'gercek': atölyenin kendi veritabanı (backend/deneyap_depo.db) — dosya yoksa atlanır
Her zaman bir KOPYA kullanılır; asıl dosyaya dokunulmaz.
"""
import os
import shutil
import subprocess
import sys
import textwrap

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGACY_DB = os.path.join(BACKEND_DIR, "deneyap_depo.db")

SCRIPT = textwrap.dedent(r'''
    import io, sqlite3, sys
    from fastapi.testclient import TestClient
    import main
    from auth import create_access_token
    from database import SessionLocal
    from models import User

    db_path = sys.argv[1]
    before = {t: sqlite3.connect(db_path).execute(f"select count(*) from {t}").fetchone()[0]
              for t in ["users", "products", "warehouses", "shipments", "stock_logs", "courses"]}

    with TestClient(main.app) as c:
        s = SessionLocal()
        admin = s.query(User).filter(User.role == "admin", User.is_active == True).order_by(User.id).first()
        assert admin is not None, "Etkin yönetici hesabı yok"
        h = {"Authorization": "Bearer " + create_access_token({"sub": admin.id}, user=admin)}
        s.close()

        assert c.get("/api/auth/setup-status").json()["needs_setup"] is False

        first = c.get("/api/products/?per_page=200", headers=h)
        total = int(first.headers["X-Total-Count"])
        assert total == before["products"], (total, before)
        seen = set()
        for page in range(1, total // 200 + 2):
            seen |= {p["id"] for p in c.get(f"/api/products/?per_page=200&page={page}", headers=h).json()}
        assert len(seen) == total

        # Türkçe büyük/küçük harf duyarsız arama: ilk ürünün adındaki bir kelimeyi BÜYÜK harfle ara
        word = max(first.json()[0]["name"].split(), key=len)
        upper = word.replace("i", "İ").replace("ı", "I").upper()
        found = c.get("/api/products/", params={"search": upper, "per_page": 200}, headers=h).json()
        assert first.json()[0]["id"] in {p["id"] for p in found}, (upper, found[:3])
        stats = c.get("/api/products/stats", headers=h).json()
        assert stats["total_products"] == total

        for w in c.get("/api/warehouses/", headers=h).json():
            assert c.get(f"/api/warehouses/{w['id']}/structure", headers=h).status_code == 200

        ships = c.get("/api/shipments/", headers=h).json()
        assert len(ships) == before["shipments"]
        for sh in ships:
            assert c.get(f"/api/shipments/{sh['id']}", headers=h).status_code == 200

        pdf = c.get("/api/reports/export/pdf", headers=h)
        assert pdf.status_code == 200 and len(pdf.content) > 10000
        assert c.get("/api/reports/export/excel", headers=h).status_code == 200
        assert c.get("/api/reports/logs", headers=h).status_code == 200
        assert c.get("/api/admin/backup", headers=h).json()["counts"]["products"] == total

        pid = first.json()[0]["id"]
        assert c.get(f"/api/products/{pid}", headers=h).status_code == 200
        assert c.get(f"/api/products/{pid}/logs", headers=h).status_code == 200

    con = sqlite3.connect(db_path)
    after = {t: con.execute(f"select count(*) from {t}").fetchone()[0] for t in before}
    assert after == before, (before, after)
    tables = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
    assert "app_settings" in tables
    print("LEGACY_OK", before)
''')


@pytest.mark.parametrize("kaynak", ["ornek", "gercek"])
def test_eski_veritabani_yeni_surumle_calisir(tmp_path, kaynak):
    copy = tmp_path / "eski_kopya.db"
    if kaynak == "gercek":
        if not os.path.exists(LEGACY_DB):
            pytest.skip("Atölyenin veritabanı dosyası (backend/deneyap_depo.db) yok")
        shutil.copy(LEGACY_DB, copy)
    else:
        from eski_veri import eski_veritabani_olustur
        eski_veritabani_olustur(copy)
    env = dict(os.environ)
    env["DATABASE_URL"] = "sqlite:///" + str(copy).replace("\\", "/")
    env["SECRET_KEY"] = "legacy-test-anahtari-0123456789abcdef"
    r = subprocess.run([sys.executable, "-c", SCRIPT, str(copy)], cwd=BACKEND_DIR, env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    assert "LEGACY_OK" in r.stdout
