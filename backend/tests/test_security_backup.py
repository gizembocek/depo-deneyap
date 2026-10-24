import json
import os
import subprocess
import sys

import pytest
from sqlalchemy import create_engine

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.mark.parametrize("path", [
    "/..%2fbackend%2f.env", "/%2e%2e/backend/.env", "/static/../backend/.env",
    "/..%2f..%2fetc%2fpasswd", "/%2e%2e%2f%2e%2e%2fbackend%2fdatabase.py",
])
def test_dizin_disina_cikilamaz(client, path):
    """Eski sürümde /..%2fbackend%2f.env adresi .env dosyasını (gizli anahtarı) veriyordu."""
    r = client.get(path)
    assert r.status_code == 404
    assert "SECRET_KEY" not in r.text and "DATABASE" not in r.text


def test_arayuz_ve_spa(client):
    assert "<html" in client.get("/").text.lower()
    assert "<html" in client.get("/urunler").text.lower()  # SPA yönlendirmesi
    assert client.get("/js/app.js").status_code == 200
    assert client.get("/js/olmayan.js").status_code == 404
    assert client.get("/api/olmayan").status_code == 404


def test_guvenlik_basliklari(client):
    r = client.get("/api/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.json()["database"] is True


def test_yedek_al_ve_bos_veritabanina_yukle(client, admin, product, warehouse, tmp_path):
    w = warehouse("Yedek Depo")
    p = product("Yedeklenecek Ürün", 7, warehouse_id=w)
    client.post("/api/shipments/", headers=admin, json={
        "name": "Ekim", "shipment_type": "Giriş", "items": [{"product_id": p["id"], "expected_quantity": 3}]})

    r = client.get("/api/admin/backup", headers=admin)
    assert r.status_code == 200
    data = r.json()
    assert data["counts"]["products"] == 1 and data["counts"]["shipment_items"] == 1

    from yedekleme import dump, restore
    target = create_engine(f"sqlite:///{tmp_path / 'geri.db'}")
    counts = restore(target, data)
    assert counts["products"] == 1 and counts["users"] == 1
    again = dump(target)
    assert again["tables"]["products"][0]["name"] == "Yedeklenecek Ürün"
    assert again["tables"]["products"][0]["current_stock"] == 10

    with pytest.raises(ValueError):  # dolu veritabanına yükleme reddedilir
        restore(target, data)


def test_yedek_sadece_yonetici(client, make_user):
    user_h, _ = make_user()
    assert client.get("/api/admin/backup", headers=user_h).status_code == 403


def test_yedekleme_komut_satiri(tmp_path, client, admin, product):
    product("CLI Ürünü", 3)
    yedek = tmp_path / "yedek.json"
    env = dict(os.environ)
    run = lambda *args: subprocess.run([sys.executable, "yedekleme.py", *args], cwd=BACKEND_DIR, env=env,
                                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    r = run("al", str(yedek))
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(yedek.read_text(encoding="utf-8"))["counts"]["products"] == 1
    hedef = f"sqlite:///{tmp_path / 'cli.db'}"
    r = run("yukle", str(yedek), "--hedef", hedef)
    assert r.returncode == 0, r.stdout + r.stderr
    r = run("yukle", str(yedek), "--hedef", hedef)
    assert r.returncode == 1 and "boş değil" in r.stdout
