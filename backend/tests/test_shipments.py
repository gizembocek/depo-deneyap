def _stock(client, h, pid):
    return client.get(f"/api/products/{pid}", headers=h).json()["current_stock"]


def test_giris_stok_ekler(client, admin, product):
    p = product("Jumper Kablo", 10)
    r = client.post("/api/shipments/", headers=admin, json={
        "name": "Ekim irsaliyesi", "shipment_type": "Giriş",
        "items": [{"product_id": p["id"], "expected_quantity": 50, "actual_quantity": 45}]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["items"][0]["status"] == "missing"
    assert body["status"] == "checked"
    assert _stock(client, admin, p["id"]) == 55


def test_cikis_yetersiz_stokta_reddedilir(client, admin, product):
    """Eski sürümde stok eksiye düşüyordu (ör. -993)."""
    p = product("Multimetre", 6)
    r = client.post("/api/shipments/", headers=admin, json={
        "name": "Garanti", "shipment_type": "Çıkış",
        "items": [{"product_id": p["id"], "expected_quantity": 999, "actual_quantity": 999}]})
    assert r.status_code == 400 and "Yetersiz stok" in r.json()["detail"]
    assert _stock(client, admin, p["id"]) == 6
    assert client.get("/api/shipments/", headers=admin).json() == []


def test_cikis_ayni_urun_iki_satir_toplam_kontrol(client, admin, product):
    p = product("Pil", 5)
    r = client.post("/api/shipments/", headers=admin, json={
        "name": "Çift satır", "shipment_type": "Çıkış",
        "items": [{"product_id": p["id"], "expected_quantity": 3}, {"product_id": p["id"], "expected_quantity": 3}]})
    assert r.status_code == 400
    r = client.post("/api/shipments/", headers=admin, json={
        "name": "Çift satır", "shipment_type": "Çıkış",
        "items": [{"product_id": p["id"], "expected_quantity": 2}, {"product_id": p["id"], "expected_quantity": 3}]})
    assert r.status_code == 200
    assert _stock(client, admin, p["id"]) == 0


def test_bekleyen_giris_kontrol_edilir_fark_stoga_yansir(client, admin, product):
    p = product("Breadboard", 0)
    s = client.post("/api/shipments/", headers=admin, json={
        "name": "Bekleyen koli", "shipment_type": "Giriş",
        "items": [{"product_id": p["id"], "expected_quantity": 20}]}).json()
    assert s["status"] == "pending" and s["items"][0]["status"] == "pending"
    assert _stock(client, admin, p["id"]) == 20  # beklenen miktar eklendi

    r = client.put(f"/api/shipments/{s['id']}/check", headers=admin,
                   json=[{"item_id": s["items"][0]["id"], "actual_quantity": 17}])
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "checked"
    assert r.json()["items"][0]["status"] == "missing"
    assert r.json()["check_date"] is not None
    assert _stock(client, admin, p["id"]) == 17  # 3 eksik geldi, stok düzeltildi

    # Tekrar kontrol (düzeltme) farkı yine doğru uygular
    client.put(f"/api/shipments/{s['id']}/check", headers=admin,
               json=[{"item_id": s["items"][0]["id"], "actual_quantity": 21}])
    assert _stock(client, admin, p["id"]) == 21


def test_kontrol_baska_islemin_satirini_kabul_etmez(client, admin, product):
    p = product()
    a = client.post("/api/shipments/", headers=admin, json={"name": "A", "shipment_type": "Giriş",
                                                           "items": [{"product_id": p["id"], "expected_quantity": 1}]}).json()
    b = client.post("/api/shipments/", headers=admin, json={"name": "B", "shipment_type": "Giriş",
                                                           "items": [{"product_id": p["id"], "expected_quantity": 1}]}).json()
    r = client.put(f"/api/shipments/{a['id']}/check", headers=admin,
                   json=[{"item_id": b["items"][0]["id"], "actual_quantity": 1}])
    assert r.status_code == 400


def test_silme_stoklari_geri_alir(client, admin, product):
    p = product("Motor", 10)
    s = client.post("/api/shipments/", headers=admin, json={
        "name": "Yanlış giriş", "shipment_type": "Giriş",
        "items": [{"product_id": p["id"], "expected_quantity": 5, "actual_quantity": 5}]}).json()
    assert _stock(client, admin, p["id"]) == 15
    assert client.delete(f"/api/shipments/{s['id']}", headers=admin).status_code == 200
    assert _stock(client, admin, p["id"]) == 10

    c = client.post("/api/shipments/", headers=admin, json={
        "name": "Çıkış", "shipment_type": "Çıkış", "items": [{"product_id": p["id"], "expected_quantity": 4}]}).json()
    assert _stock(client, admin, p["id"]) == 6
    client.delete(f"/api/shipments/{c['id']}", headers=admin)
    assert _stock(client, admin, p["id"]) == 10


def test_silme_stok_geri_alinmadan(client, admin, product):
    p = product("Motor", 10)
    s = client.post("/api/shipments/", headers=admin, json={
        "name": "Giriş", "shipment_type": "Giriş", "items": [{"product_id": p["id"], "expected_quantity": 5}]}).json()
    client.delete(f"/api/shipments/{s['id']}", params={"revert_stock": "false"}, headers=admin)
    assert _stock(client, admin, p["id"]) == 15


def test_geri_alma_stok_eksiye_dusurecekse_engellenir(client, admin, product):
    p = product("Kablo", 0)
    s = client.post("/api/shipments/", headers=admin, json={
        "name": "Giriş", "shipment_type": "Giriş", "items": [{"product_id": p["id"], "expected_quantity": 5}]}).json()
    client.post(f"/api/products/{p['id']}/stock", headers=admin, json={"action": "remove", "quantity": 4})
    r = client.delete(f"/api/shipments/{s['id']}", headers=admin)
    assert r.status_code == 400
    assert _stock(client, admin, p["id"]) == 1


def test_kullanici_islem_silemez(client, admin, make_user, product):
    p = product()
    s = client.post("/api/shipments/", headers=admin, json={
        "name": "A", "shipment_type": "Giriş", "items": [{"product_id": p["id"], "expected_quantity": 1}]}).json()
    user_h, _ = make_user()
    assert client.delete(f"/api/shipments/{s['id']}", headers=user_h).status_code == 403


def test_kullanici_yetkisiz_depodaki_urunle_islem_yapamaz(client, admin, make_user, warehouse, product):
    w = warehouse()
    p = product("Gizli", warehouse_id=w)
    user_h, _ = make_user()
    r = client.post("/api/shipments/", headers=user_h, json={
        "name": "X", "shipment_type": "Giriş", "items": [{"product_id": p["id"], "expected_quantity": 1}]})
    assert r.status_code == 403
    # Yönetici işlemi kullanıcı listesinde görünmez
    client.post("/api/shipments/", headers=admin, json={
        "name": "Yönetici", "shipment_type": "Giriş", "items": [{"product_id": p["id"], "expected_quantity": 1}]})
    assert client.get("/api/shipments/", headers=user_h).json() == []


def test_gorseller_listede_degil_detayda(client, admin, product):
    p = product()
    img = "data:image/png;base64,iVBORw0KGgo="
    s = client.post("/api/shipments/", headers=admin, json={
        "name": "Fotoğraflı", "shipment_type": "Giriş", "invoice_image_url": img,
        "items": [{"product_id": p["id"], "expected_quantity": 1}]}).json()
    listed = client.get("/api/shipments/", headers=admin).json()[0]
    assert listed["has_invoice_image"] is True and listed["invoice_image_url"] is None
    detail = client.get(f"/api/shipments/{s['id']}", headers=admin).json()
    assert detail["invoice_image_url"] == img


def test_bos_ve_hatali_istekler(client, admin, product):
    p = product()
    assert client.post("/api/shipments/", headers=admin, json={"name": "Boş", "items": []}).status_code == 422
    assert client.post("/api/shipments/", headers=admin, json={
        "name": "X", "items": [{"product_id": 99999, "expected_quantity": 1}]}).status_code == 400
    assert client.post("/api/shipments/", headers=admin, json={
        "name": "X", "items": [{"product_id": p["id"], "expected_quantity": 0}]}).status_code == 422
    assert client.post("/api/shipments/", headers=admin, json={
        "name": "X", "shipment_type": "Transfer", "items": [{"product_id": p["id"]}]}).status_code == 422
