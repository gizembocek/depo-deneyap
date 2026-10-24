def test_depo_hiyerarsisi(client, admin, warehouse):
    w = warehouse("Ana Depo")
    cab = client.post("/api/warehouses/cabinets", headers=admin, json={"name": "Dolap A", "warehouse_id": w}).json()
    shelf = client.post("/api/warehouses/shelves", headers=admin, json={"name": "Raf 1", "cabinet_id": cab["id"]}).json()
    client.post("/api/warehouses/compartments", headers=admin, json={"name": "Bölme 1", "shelf_id": shelf["id"]})
    s = client.get(f"/api/warehouses/{w}/structure", headers=admin).json()
    assert s["cabinets"][0]["shelves"][0]["compartments"][0]["name"] == "Bölme 1"


def test_olmayan_ust_birime_ekleme_404(client, admin):
    assert client.post("/api/warehouses/cabinets", headers=admin, json={"name": "X", "warehouse_id": 999}).status_code == 404
    assert client.post("/api/warehouses/shelves", headers=admin, json={"name": "X", "cabinet_id": 999}).status_code == 404
    assert client.post("/api/warehouses/compartments", headers=admin, json={"name": "X", "shelf_id": 999}).status_code == 404


def test_bos_isim_reddedilir(client, admin, warehouse):
    assert client.post("/api/warehouses/", headers=admin, json={"name": "   "}).status_code == 422
    w = warehouse()
    assert client.post("/api/warehouses/cabinets", headers=admin, json={"name": "", "warehouse_id": w}).status_code == 422


def test_dolap_silinince_urun_silinmez_konumu_bosalir(client, admin, warehouse):
    w = warehouse()
    cab = client.post("/api/warehouses/cabinets", headers=admin, json={"name": "Dolap", "warehouse_id": w}).json()
    shelf = client.post("/api/warehouses/shelves", headers=admin, json={"name": "Raf", "cabinet_id": cab["id"]}).json()
    p = client.post("/api/products/", headers=admin, json={
        "name": "Raftaki", "warehouse_id": w, "cabinet_id": cab["id"], "shelf_id": shelf["id"]}).json()
    assert client.delete(f"/api/warehouses/cabinets/{cab['id']}", headers=admin).status_code == 200
    after = client.get(f"/api/products/{p['id']}", headers=admin).json()
    assert after["cabinet_id"] is None and after["shelf_id"] is None and after["warehouse_id"] == w


def test_depo_silme_icindekileri_temizler(client, admin, warehouse, product):
    w = warehouse()
    p = product("Depodaki", warehouse_id=w)
    client.post("/api/shipments/", headers=admin, json={
        "name": "İşlem", "shipment_type": "Giriş", "items": [{"product_id": p["id"], "expected_quantity": 1}]})
    r = client.delete(f"/api/warehouses/{w}", headers=admin)
    assert r.status_code == 200 and r.json()["deleted_products"] == 1
    assert client.get(f"/api/products/{p['id']}", headers=admin).status_code == 404


def test_depo_listesi_urun_sayisi(client, admin, warehouse, product):
    w = warehouse()
    product("1", warehouse_id=w)
    product("2", warehouse_id=w)
    lst = client.get("/api/warehouses/", headers=admin).json()
    assert lst[0]["product_count"] == 2


def test_kullanici_yetkisiz_depo_yapisini_goremez(client, admin, make_user, warehouse):
    w1, w2 = warehouse("Benim"), warehouse("Başkası")
    user_h, _ = make_user(warehouse_ids=[w1])
    assert [x["id"] for x in client.get("/api/warehouses/", headers=user_h).json()] == [w1]
    assert client.get(f"/api/warehouses/{w1}/structure", headers=user_h).status_code == 200
    assert client.get(f"/api/warehouses/{w2}/structure", headers=user_h).status_code == 403
    assert client.post("/api/warehouses/", headers=user_h, json={"name": "X"}).status_code == 403


def test_ders_islemleri(client, admin, product):
    r = client.post("/api/courses/", headers=admin, json={"name": "Drone Teknolojileri"})
    assert r.status_code == 201
    cid = r.json()["id"]
    assert client.post("/api/courses/", headers=admin, json={"name": "DRONE teknolojileri"}).status_code == 400
    p = product("Pervane", course_ids=[cid])
    courses = {c["id"]: c for c in client.get("/api/courses/", headers=admin).json()}
    assert courses[cid]["product_count"] == 1
    assert client.put(f"/api/courses/{cid}", headers=admin, json={"name": "İHA Teknolojileri"}).status_code == 200
    assert client.delete(f"/api/courses/{cid}", headers=admin).status_code == 200
    assert client.get(f"/api/products/{p['id']}", headers=admin).json()["courses"] == []


def test_ayarlar(client, admin, make_user):
    r = client.put("/api/settings", headers=admin, json={"atolye_adi": "Artvin Deneyap Teknoloji Atölyesi", "il": "Artvin"})
    assert r.status_code == 200
    user_h, _ = make_user()
    assert client.get("/api/settings", headers=user_h).json()["atolye_adi"] == "Artvin Deneyap Teknoloji Atölyesi"
    assert client.put("/api/settings", headers=user_h, json={"atolye_adi": "X"}).status_code == 403
