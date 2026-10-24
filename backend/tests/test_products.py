from conftest import auth_header


def test_urun_olusturma_ve_okuma(client, admin, product):
    p = product("Lehim Teli", 4, category="Sarf Malzemesi")
    r = client.get(f"/api/products/{p['id']}", headers=admin)
    assert r.status_code == 200
    assert r.json()["name"] == "Lehim Teli"
    logs = client.get(f"/api/products/{p['id']}/logs", headers=admin).json()
    assert logs[0]["action"] == "create"


def test_dogrulama_hatalari_turkce(client, admin):
    r = client.post("/api/products/", headers=admin, json={"name": "  ", "current_stock": -5, "category": "Yanlış"})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "Ürün adı boş olamaz" in detail
    assert "Mevcut stok en az 0" in detail
    assert "Geçersiz kategori" in detail


def test_ayni_depoda_ayni_isim_engellenir_turkce_harf_duyarsiz(client, admin, product, warehouse):
    w = warehouse()
    product("Işıklı Büyüteç", warehouse_id=w)
    r = client.post("/api/products/", headers=admin, json={"name": "IŞIKLI BÜYÜTEÇ", "warehouse_id": w})
    assert r.status_code == 400
    # Başka depoda aynı isim serbest
    w2 = warehouse("İkinci Depo")
    r = client.post("/api/products/", headers=admin, json={"name": "Işıklı Büyüteç", "warehouse_id": w2})
    assert r.status_code == 200


def test_sayfalama_ve_toplam_sayi(client, admin, product):
    for i in range(130):
        product(f"Ürün {i:03d}", i)
    r = client.get("/api/products/?per_page=50&page=1", headers=admin)
    assert r.headers["X-Total-Count"] == "130"
    assert len(r.json()) == 50
    r3 = client.get("/api/products/?per_page=50&page=3", headers=admin)
    assert len(r3.json()) == 30
    ids = {p["id"] for page in (1, 2, 3)
           for p in client.get(f"/api/products/?per_page=50&page={page}", headers=admin).json()}
    assert len(ids) == 130  # sayfalar çakışmıyor, eksik yok


def test_dersli_urunlerde_sayfalama_bozulmaz(client, admin, product):
    courses = client.get("/api/courses/", headers=admin).json()
    cids = [c["id"] for c in courses[:4]]
    for i in range(60):
        product(f"Dersli {i}", course_ids=cids)
    r = client.get("/api/products/?per_page=25", headers=admin)
    assert len(r.json()) == 25
    assert all(len(p["courses"]) == 4 for p in r.json())


def test_arama_turkce_karakter_duyarsiz(client, admin, product):
    product("Işıklı Büyüteç")
    product("Çalışma Masası")
    product("Şarj Aleti")
    for q, expected in [("ışık", "Işıklı Büyüteç"), ("ISIK", "Işıklı Büyüteç"), ("buyutec", "Işıklı Büyüteç"),
                        ("çalış", "Çalışma Masası"), ("CALISMA", "Çalışma Masası"), ("şarj", "Şarj Aleti")]:
        names = [p["name"] for p in client.get("/api/products/", params={"search": q}, headers=admin).json()]
        assert names == [expected], (q, names)


def test_arama_ozel_karakterler(client, admin, product):
    product("%50 indirimli kutu")
    product("Normal kutu")
    names = [p["name"] for p in client.get("/api/products/", params={"search": "%"}, headers=admin).json()]
    assert names == ["%50 indirimli kutu"]


def test_filtreler(client, admin, product, warehouse):
    w = warehouse()
    product("A", 1, warehouse_id=w)  # kritik (1 <= 3)
    product("B", 50, status="Bozuk / Kırık")
    product("C", 30, category="Sarf Malzemesi")
    def names(**params):
        return sorted(p["name"] for p in client.get("/api/products/", params=params, headers=admin).json())
    assert names(low_stock="true") == ["A"]
    assert names(status="Bozuk / Kırık") == ["B"]
    assert names(category="Sarf Malzemesi") == ["C"]
    assert names(warehouse_id=w) == ["A"]
    assert client.get("/api/products/count", params={"low_stock": "true"}, headers=admin).json()["count"] == 1
    stats = client.get("/api/products/stats", headers=admin).json()
    assert stats["total_products"] == 3 and stats["low_stock_count"] == 1 and stats["broken_count"] == 1


def test_siralama_turkce_alfabe(client, admin, product):
    for n in ["Zil", "Çekiç", "Cetvel", "Ölçü Kabı", "Ok", "İp", "Ihlamur"]:
        product(n)
    names = [p["name"] for p in client.get("/api/products/?sort=name", headers=admin).json()]
    assert names == ["Cetvel", "Çekiç", "Ihlamur", "İp", "Ok", "Ölçü Kabı", "Zil"]


def test_konum_tutarliligi(client, admin, warehouse):
    w1, w2 = warehouse("Depo 1"), warehouse("Depo 2")
    cab = client.post("/api/warehouses/cabinets", headers=admin, json={"name": "Dolap 1", "warehouse_id": w1}).json()
    shelf = client.post("/api/warehouses/shelves", headers=admin, json={"name": "Raf 1", "cabinet_id": cab["id"]}).json()
    comp = client.post("/api/warehouses/compartments", headers=admin, json={"name": "Bölme 1", "shelf_id": shelf["id"]}).json()

    ok = client.post("/api/products/", headers=admin, json={
        "name": "Konumlu", "warehouse_id": w1, "cabinet_id": cab["id"], "shelf_id": shelf["id"], "compartment_id": comp["id"]})
    assert ok.status_code == 200
    assert ok.json()["compartment_name"] == "Bölme 1"

    bad = client.post("/api/products/", headers=admin, json={"name": "Yanlış", "warehouse_id": w2, "cabinet_id": cab["id"]})
    assert bad.status_code == 400 and "dolap" in bad.json()["detail"]

    # Depo değişince alt konumlar temizlenir
    moved = client.put(f"/api/products/{ok.json()['id']}", headers=admin, json={"warehouse_id": w2})
    assert moved.status_code == 200
    assert moved.json()["warehouse_id"] == w2 and moved.json()["cabinet_id"] is None


def test_duzenleme_log_kaydi_tutar(client, admin, product):
    p = product("Servo Motor", 10)
    r = client.put(f"/api/products/{p['id']}", headers=admin, json={"current_stock": 4, "status": "Garantide"})
    assert r.status_code == 200
    actions = [l["action"] for l in client.get(f"/api/products/{p['id']}/logs", headers=admin).json()]
    assert "set" in actions and "status_change" in actions


def test_kritik_stok_sifir_olabilir(client, admin, product):
    p = product("Demirbaş Masa", 1, critical_stock=0)
    assert p["critical_stock"] == 0


def test_stok_guncelleme_kurallari(client, admin, product):
    p = product("LED", 5)
    url = f"/api/products/{p['id']}/stock"
    assert client.post(url, headers=admin, json={"action": "add", "quantity": 3}).json()["current_stock"] == 8
    assert client.post(url, headers=admin, json={"action": "remove", "quantity": 2}).json()["current_stock"] == 6
    r = client.post(url, headers=admin, json={"action": "remove", "quantity": 100})
    assert r.status_code == 400 and "Yetersiz stok" in r.json()["detail"]
    assert client.post(url, headers=admin, json={"action": "set", "quantity": 0}).json()["is_critical"] is True
    assert client.post(url, headers=admin, json={"action": "add", "quantity": -4}).status_code == 422
    assert client.post(url, headers=admin, json={"action": "sil", "quantity": 1}).status_code == 422
    assert client.post(url, headers=admin, json={"action": "add", "quantity": 0}).status_code == 400


def test_kullanici_sadece_yetkili_deposunu_gorur(client, admin, make_user, warehouse, product):
    w1, w2 = warehouse("Yetkili"), warehouse("Yetkisiz")
    product("Bende", warehouse_id=w1)
    gizli = product("Gizli", warehouse_id=w2)
    product("Genel")  # depo atanmamış: herkes görür
    user_h, _ = make_user(warehouse_ids=[w1])

    names = sorted(p["name"] for p in client.get("/api/products/", headers=user_h).json())
    assert names == ["Bende", "Genel"]
    assert client.get(f"/api/products/{gizli['id']}", headers=user_h).status_code == 403
    assert client.get(f"/api/products/{gizli['id']}/logs", headers=user_h).status_code == 403
    assert client.post(f"/api/products/{gizli['id']}/stock", headers=user_h, json={"action": "add", "quantity": 1}).status_code == 403
    assert client.get("/api/products/count", headers=user_h).json()["count"] == 2
    assert client.get("/api/products/stats", headers=user_h).json()["total_products"] == 2


def test_depo_yetkisi_olmayan_kullanici(client, admin, make_user, warehouse, product):
    w = warehouse()
    product("Depodaki", warehouse_id=w)
    product("Genel")
    user_h, _ = make_user()  # hiç depo yetkisi yok
    assert [p["name"] for p in client.get("/api/products/", headers=user_h).json()] == ["Genel"]
    assert client.get("/api/products/count", headers=user_h).json()["count"] == 1


def test_kullanici_urun_ekleyemez_silemez(client, make_user, product):
    p = product()
    user_h, _ = make_user()
    assert client.post("/api/products/", headers=user_h, json={"name": "X"}).status_code == 403
    assert client.delete(f"/api/products/{p['id']}", headers=user_h).status_code == 403
    assert client.delete("/api/products/all", headers=user_h).status_code == 403


def test_urun_silme(client, admin, product):
    p = product()
    assert client.delete(f"/api/products/{p['id']}", headers=admin).status_code == 200
    assert client.get(f"/api/products/{p['id']}", headers=admin).status_code == 404


def test_tum_urunleri_silme_depoya_gore(client, admin, product, warehouse):
    w = warehouse()
    product("Depodaki 1", warehouse_id=w)
    product("Depodaki 2", warehouse_id=w)
    product("Genel")
    r = client.delete("/api/products/all", params={"warehouse_id": w}, headers=admin)
    assert r.json()["deleted_products"] == 2
    assert [p["name"] for p in client.get("/api/products/", headers=admin).json()] == ["Genel"]


def test_gorsel_yukleme(client, admin):
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (3000, 2000), (200, 30, 30)).save(buf, format="PNG")
    r = client.post("/api/products/upload-image", headers=admin, files={"file": ("foto.png", buf.getvalue(), "image/png")})
    assert r.status_code == 200, r.text
    url = r.json()["url"]
    img = client.get(url)
    assert img.status_code == 200
    saved = Image.open(io.BytesIO(img.content))
    assert max(saved.size) == 1600  # büyük görsel küçültüldü


def test_sahte_gorsel_reddedilir(client, admin):
    r = client.post("/api/products/upload-image", headers=admin,
                    files={"file": ("zararli.png", b"<script>alert(1)</script>", "image/png")})
    assert r.status_code == 400


def test_data_url_disinda_zararli_gorsel_adresi(client, admin):
    r = client.post("/api/products/", headers=admin, json={"name": "X", "image_url": "javascript:alert(1)"})
    assert r.status_code == 422
    r = client.post("/api/products/", headers=admin, json={"name": "Y", "image_url": "data:text/html,<b>x</b>"})
    assert r.status_code == 422
