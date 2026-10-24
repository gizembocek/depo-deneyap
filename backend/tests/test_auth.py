from conftest import ADMIN_PASSWORD, auth_header


def test_ilk_kurulum_durumu_ve_kurulum(client):
    r = client.get("/api/auth/setup-status")
    assert r.json()["needs_setup"] is True

    r = client.post("/api/auth/setup", json={
        "atolye_adi": "Artvin Deneyap Atölyesi", "full_name": "Gizem", "email": "Gizem@Deneyap.org",
        "password": ADMIN_PASSWORD,
    })
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "admin"

    status = client.get("/api/auth/setup-status").json()
    assert status["needs_setup"] is False
    assert status["atolye_adi"] == "Artvin Deneyap Atölyesi"

    # Standart Deneyap dersleri eklendi
    courses = client.get("/api/courses/", headers=auth_header(r.json()["access_token"])).json()
    assert any(c["name"] == "Robotik Kodlama" for c in courses)


def test_kurulum_ikinci_kez_yapilamaz(client, admin):
    r = client.post("/api/auth/setup", json={
        "atolye_adi": "Sahte", "full_name": "Saldırgan", "email": "x@x.com", "password": "Saldirgan123"})
    assert r.status_code == 400


def test_kimliksiz_kayit_engellenir(client, admin):
    """Eski sürümde herkes kendine yönetici hesabı açabiliyordu."""
    r = client.post("/api/auth/register", json={
        "email": "saldirgan@x.com", "full_name": "Hacker", "password": "Hacker123", "role": "admin"})
    assert r.status_code == 401


def test_normal_kullanici_kayit_yapamaz(client, make_user):
    user_h, _ = make_user()
    r = client.post("/api/auth/register", headers=user_h, json={
        "email": "yeni@x.com", "full_name": "Yeni", "password": "Yenisifre1", "role": "admin"})
    assert r.status_code == 403


def test_gecersiz_rol_reddedilir(client, admin):
    r = client.post("/api/auth/register", headers=admin, json={
        "email": "a@b.com", "full_name": "A", "password": "Gecerli123", "role": "superadmin"})
    assert r.status_code == 422
    assert "Rol" in r.json()["detail"]


def test_sifre_kurallari(client, admin):
    for bad, msg in [("kisa1A", "8 karakter"), ("kucukharf1", "büyük harf"), ("BuyukHarfsiz", "rakam")]:
        r = client.post("/api/auth/register", headers=admin, json={
            "email": "a@b.com", "full_name": "A", "password": bad})
        assert r.status_code == 400
        assert msg in r.json()["detail"]


def test_giris_e_posta_buyuk_kucuk_harf_duyarsiz(client, admin):
    r = client.post("/api/auth/login", json={"email": "GIZEM@deneyap.org", "password": ADMIN_PASSWORD})
    assert r.status_code == 200


def test_hatali_giris_ve_kaba_kuvvet_korumasi(client, admin):
    for _ in range(10):
        r = client.post("/api/auth/login", json={"email": "gizem@deneyap.org", "password": "Yanlis123"})
        assert r.status_code == 401
    r = client.post("/api/auth/login", json={"email": "gizem@deneyap.org", "password": ADMIN_PASSWORD})
    assert r.status_code == 429  # doğru şifre bile geçici olarak engellenir


def test_sifre_degistirme_eski_oturumu_gecersiz_kilar(client, admin):
    r = client.post("/api/auth/change-password", headers=admin,
                    json={"current_password": ADMIN_PASSWORD, "new_password": "YeniSifre2026"})
    assert r.status_code == 200
    new_token = r.json()["access_token"]

    assert client.get("/api/auth/me", headers=admin).status_code == 401  # eski token
    assert client.get("/api/auth/me", headers=auth_header(new_token)).status_code == 200
    assert client.post("/api/auth/login", json={"email": "gizem@deneyap.org", "password": "YeniSifre2026"}).status_code == 200


def test_sifre_degistirme_yanlis_mevcut_sifre(client, admin):
    r = client.post("/api/auth/change-password", headers=admin,
                    json={"current_password": "Yanlis123", "new_password": "YeniSifre2026"})
    assert r.status_code == 400


def test_yonetici_sifre_sifirlama(client, admin, make_user):
    user_h, uid = make_user()
    r = client.post(f"/api/auth/users/{uid}/reset-password", headers=admin, json={"new_password": "Sifirlandi1"})
    assert r.status_code == 200
    assert client.get("/api/auth/me", headers=user_h).status_code == 401
    assert client.post("/api/auth/login", json={"email": "egitmen@deneyap.org", "password": "Sifirlandi1"}).status_code == 200


def test_pasif_kullanici_giremez_ve_oturumu_kapanir(client, admin, make_user):
    user_h, uid = make_user()
    client.put(f"/api/auth/users/{uid}", headers=admin, json={"is_active": False})
    assert client.get("/api/auth/me", headers=user_h).status_code == 401
    r = client.post("/api/auth/login", json={"email": "egitmen@deneyap.org", "password": "Egitmen2026"})
    assert r.status_code == 403


def test_son_yonetici_korunur(client, admin):
    me = client.get("/api/auth/me", headers=admin).json()
    assert client.put(f"/api/auth/users/{me['id']}", headers=admin, json={"role": "user"}).status_code == 400
    assert client.put(f"/api/auth/users/{me['id']}", headers=admin, json={"is_active": False}).status_code == 400
    assert client.delete(f"/api/auth/users/{me['id']}", headers=admin).status_code == 400


def test_ikinci_yonetici_varken_rol_degisebilir(client, admin, make_user):
    _, uid = make_user(email="ikinci@deneyap.org", role="admin")
    r = client.put(f"/api/auth/users/{uid}", headers=admin, json={"role": "user"})
    assert r.status_code == 200 and r.json()["role"] == "user"


def test_depo_erisimi_toplu_atama(client, admin, make_user, warehouse):
    w1, w2 = warehouse("A"), warehouse("B")
    _, uid = make_user()
    r = client.put(f"/api/auth/users/{uid}/warehouses", headers=admin, json={"warehouse_ids": [w1, w2]})
    assert sorted(r.json()["warehouse_ids"]) == sorted([w1, w2])
    r = client.put(f"/api/auth/users/{uid}/warehouses", headers=admin, json={"warehouse_ids": [w2]})
    assert r.json()["warehouse_ids"] == [w2]
    r = client.put(f"/api/auth/users/{uid}/warehouses", headers=admin, json={"warehouse_ids": [99999]})
    assert r.status_code == 404


def test_kullanici_silme(client, admin, make_user):
    _, uid = make_user()
    assert client.delete(f"/api/auth/users/{uid}", headers=admin).status_code == 200
    assert all(u["id"] != uid for u in client.get("/api/auth/users", headers=admin).json())


def test_sahte_token_reddedilir(client, admin):
    from jose import jwt
    fake = jwt.encode({"sub": "1"}, "baska-anahtar", algorithm="HS256")
    assert client.get("/api/auth/me", headers=auth_header(fake)).status_code == 401
    assert client.get("/api/auth/me", headers=auth_header("bozuk.token")).status_code == 401
    assert client.get("/api/auth/me").status_code == 401
