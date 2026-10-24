import os
import sqlite3

import bcrypt
import pytest
from sqlalchemy import create_engine

from conftest import auth_header
from eski_veri import ANA_DEPO_SATIR, FARKLI_MALZEME, SATIR_PER_KOPYA, TOPLAM_URUN, eski_veritabani_olustur
from veritabani_kontrol import duzelt, kontrol_et

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EPNI = "Elektronik Programlama ve Nesnelerin İnterneti (EPNİ)"


def _codes(bulgular):
    return {b.kod: b for b in bulgular}


@pytest.fixture
def legacy_copy(tmp_path):
    """Eski sürüm verisinin sorunlarını içeren veritabanı (bkz. tests/eski_veri.py)."""
    path = tmp_path / "eski.db"
    ids = eski_veritabani_olustur(path)
    eng = create_engine(f"sqlite:///{path}")
    yield eng, path, ids
    eng.dispose()


def test_eski_veride_sorunlar_bulunur(legacy_copy):
    eng, _, _ = legacy_copy
    b = _codes(kontrol_et(eng))
    assert b["ZAYIF_SIFRE"].adet == 2 and "admin123" in " ".join(b["ZAYIF_SIFRE"].detay)
    assert b["TEKRAR_DERS"].adet == 2
    assert b["KOPYA_AKTARIM"].adet == TOPLAM_URUN and len(b["KOPYA_AKTARIM"].detay) == 3
    assert "tutulacak" in [d for d in b["KOPYA_AKTARIM"].detay if "Ana Depo" in d][0]
    assert b["TEKRAR_URUN"].adet > 0
    assert b["BOS_GONDERIM"].adet == 2
    assert b["FAZLA_BOSLUK"].adet >= 2
    assert b["GONDERIM_DURUMU"].adet >= 2
    assert b["SEMA_EKSIK_TABLO"].detay == ["app_settings"]
    assert "YETIM_KAYIT" not in b and "UZUN_DEGER" not in b


def test_guvenli_duzeltme_eski_veride(legacy_copy):
    eng, path, _ = legacy_copy
    con = sqlite3.connect(path)
    epni_links = con.execute("""select count(*) from product_courses pc join courses c on c.id=pc.course_id
                                where c.name='Elektronik Programlama ve Nesne'""").fetchone()[0]
    yapilan = duzelt(eng)
    assert any("admin@deneyap.org" in y and "pasif" in y for y in yapilan)
    b = _codes(kontrol_et(eng))
    for code in ("ZAYIF_SIFRE", "TEKRAR_DERS", "FAZLA_BOSLUK", "GONDERIM_DURUMU", "SEMA_EKSIK_TABLO"):
        assert code not in b, code
    assert con.execute("select count(*) from products").fetchone()[0] == TOPLAM_URUN  # güvenli düzeltme ürün silmez
    assert con.execute("pragma foreign_key_check").fetchall() == []
    assert con.execute("select is_active from users where email='gizem@deneyap.org'").fetchone()[0] == 1
    names = [r[0] for r in con.execute("select name from courses")]
    assert "Robotik ve Kodlama" not in names and "Elektronik Programlama ve Nesne" not in names
    assert con.execute("""select count(*) from product_courses pc join courses c on c.id=pc.course_id
                          where c.name=?""", (EPNI,)).fetchone()[0] == epni_links
    assert con.execute("select count(*) from products where name like '%' || char(10) || '%'").fetchone()[0] == 0


def test_tekrar_eden_urun_birlestirme(legacy_copy):
    eng, path, _ = legacy_copy
    duzelt(eng, tekrar_urun=True, bos_gonderim=True)
    con = sqlite3.connect(path)
    per_wh = dict(con.execute("select coalesce(warehouse_id,0), count(*) from products group by 1").fetchall())
    assert per_wh == {0: FARKLI_MALZEME, 1: FARKLI_MALZEME, 2: FARKLI_MALZEME}
    assert con.execute("select count(*) from stock_logs").fetchone()[0] >= 2
    assert con.execute("select count(*) from shipment_items si left join products p on p.id=si.product_id where p.id is null").fetchone()[0] == 0
    assert con.execute("select count(*) from shipments").fetchone()[0] == 2
    assert con.execute("pragma foreign_key_check").fetchall() == []
    assert "TEKRAR_URUN" not in _codes(kontrol_et(eng, sifre_kontrol=False))


def test_kopya_aktarimlar_silinir_kullanilan_kopya_kalir(legacy_copy):
    """Atölyenin kararı: Ana Depo kalsın, diğer kopyalar silinsin, her malzemeden tek kayıt olsun,
    deneme gönderimleri silinsin."""
    eng, path, ids = legacy_copy
    con = sqlite3.connect(path)
    stok_once = {n: s for n, s in con.execute("select name, current_stock from products where id in (?,?)",
                                              (ids["klemens"], ids["pervane"]))}
    yapilan = duzelt(eng, tekrar_urun=True, bos_gonderim=True, kopya_aktarim=True)
    assert sum("kopya ürün silindi" in y for y in yapilan) == 2
    per_wh = dict(con.execute("select coalesce(warehouse_id,0), count(*) from products group by 1").fetchall())
    assert per_wh == {1: FARKLI_MALZEME}  # yalnızca Ana Depo, her malzemeden bir kayıt
    names = [r[0] for r in con.execute("select name from products")]
    assert len(names) == len(set(names)) and "3 Boyutlu Yazıcı" in names
    # Gönderim satırları ve stok geçmişi Ana Depo ürünlerine bağlı kaldı
    assert con.execute("select count(*) from shipment_items").fetchone()[0] == 2
    assert con.execute("select count(*) from shipments").fetchone()[0] == 2
    assert {n: s for n, s in con.execute("select name, current_stock from products where id in (?,?)",
                                         (ids["klemens"], ids["pervane"]))} == stok_once
    # Farklı ders listelerinde geçen ürünün dersleri birleşti, en büyük stok alındı
    makas = con.execute("select id, current_stock, description from products where name='Makas'").fetchone()
    assert makas[1] == 50 and "Tasarım ve Üretim" in makas[2] and "Malzeme Bilimi" in makas[2]
    assert con.execute("select count(*) from product_courses where product_id=?", (makas[0],)).fetchone()[0] == 2
    assert con.execute("select current_stock from products where name='Batarya'").fetchone()[0] == 20
    assert con.execute("pragma foreign_key_check").fetchall() == []
    b = _codes(kontrol_et(eng))
    for code in ("KOPYA_AKTARIM", "TEKRAR_URUN", "BOS_GONDERIM", "ZAYIF_SIFRE"):
        assert code not in b, code
    assert not [x for x in b.values() if x.seviye in ("KRİTİK", "UYARI")], [x.baslik for x in b.values()]


def test_kullanilmis_kopya_asla_silinmez(legacy_copy):
    eng, path, ids = legacy_copy
    con = sqlite3.connect(path)
    # 'Elektronik' kopyasındaki bir ürüne de stok hareketi eklenmiş olsun
    p = con.execute("select id from products where warehouse_id=2 limit 1").fetchone()[0]
    con.execute("insert into stock_logs (product_id,user_id,action,quantity_change) values (?,3,'add',1)", (p,))
    con.commit()
    yapilan = duzelt(eng, kopya_aktarim=True)
    assert any("silinmedi" in y for y in yapilan)
    assert con.execute("select count(*) from products where warehouse_id=2").fetchone()[0] == SATIR_PER_KOPYA
    assert con.execute("select count(*) from products where warehouse_id is null").fetchone()[0] == 0
    assert con.execute("select count(*) from products where warehouse_id=1").fetchone()[0] == ANA_DEPO_SATIR


def _broken_db(path):
    """Yabancı anahtar denetimi kapalıyken sahipsiz ve hatalı kayıtlar içeren veritabanı."""
    eng = create_engine(f"sqlite:///{path}")
    import models  # noqa: F401
    from database import Base
    Base.metadata.create_all(eng)
    eng.dispose()
    con = sqlite3.connect(path)
    con.execute("pragma foreign_keys=off")
    pw = bcrypt.hashpw(b"Gercek2026", bcrypt.gensalt(4)).decode()
    con.executescript(f"""
        insert into users (id,email,full_name,hashed_password,role,is_active) values
            (1,'yonetici@x.org','Yönetici','{pw}','admin',1), (2,'b@x.org','  Çok   Boşluklu  ','{pw}','super',NULL);
        insert into warehouses (id,name) values (1,'Depo');
        insert into cabinets (id,name,warehouse_id) values (1,'Dolap',1), (2,'Yetim Dolap',99);
        insert into shelves (id,name,cabinet_id) values (1,'Raf',1), (2,'Yetim Raf',2);
        insert into courses (id,name) values (1,'Robotik Kodlama'), (2,'robotik ve kodlama');
        insert into products (id,name,category,status,current_stock,critical_stock,ideal_stock,warehouse_id,cabinet_id,shelf_id) values
            (1,'Normal','Sarf Malzemesi','Çalışan',5,1,10,1,1,1),
            (2,'Yetim depolu','X','Kayıp',-3,NULL,10,77,NULL,NULL),
            (3,'Yetim dolaplı','Elektronik Bileşen','arızalı',1,1,1,1,2,2),
            (4,'{'Ç' * 300}','Elektronik Bileşen','Çalışan',1,1,1,NULL,NULL,NULL),
            (5,'Tutarsız','Sarf Malzemesi','Çalışan',1,1,1,NULL,1,NULL);
        insert into product_courses values (1,2), (999,1);
        insert into stock_logs (id,product_id,user_id,action) values (1,999,1,'add'), (2,1,555,'add');
        insert into shipments (id,name,shipment_type,status,created_by,outgoing_reason) values (1,'S','Giriş','pending',777,'');
        insert into shipment_items (id,shipment_id,product_id,expected_quantity,actual_quantity,status) values
            (1,1,1,5,5,'pending'), (2,1,999,1,1,'complete'), (3,55,1,1,1,'complete');
        insert into user_warehouse_access values (1,1), (1,42);
    """)
    con.commit()
    con.close()


def test_sahipsiz_ve_hatali_kayitlar_onarilir(tmp_path):
    path = tmp_path / "bozuk.db"
    _broken_db(path)
    eng = create_engine(f"sqlite:///{path}")
    b = _codes(kontrol_et(eng, sifre_kontrol=False))
    for code in ("YETIM_KAYIT", "GECERSIZ_DEGER", "KONUM_TUTARSIZ", "UZUN_DEGER", "TEKRAR_DERS", "GECERSIZ_ROL"):
        assert code in b, code
    duzelt(eng)
    b = _codes(kontrol_et(eng, sifre_kontrol=False))
    assert not [x for x in b.values() if x.seviye == "KRİTİK"], [x.baslik for x in b.values()]
    for code in ("YETIM_KAYIT", "GECERSIZ_DEGER", "KONUM_TUTARSIZ", "UZUN_DEGER", "TEKRAR_DERS", "GECERSIZ_ROL", "FAZLA_BOSLUK"):
        assert code not in b, code
    con = sqlite3.connect(path)
    assert con.execute("pragma foreign_key_check").fetchall() == []
    p2 = con.execute("select category,status,current_stock,critical_stock,warehouse_id from products where id=2").fetchone()
    assert p2 == ("Genel / Dayanıklı Malzeme", "Çalışan", 0, 5, None)
    assert con.execute("select status from products where id=3").fetchone()[0] == "Bozuk / Kırık"
    assert con.execute("select cabinet_id from products where id=3").fetchone()[0] is None
    assert len(con.execute("select name from products where id=4").fetchone()[0]) == 255
    assert con.execute("select full_name, role, is_active from users where id=2").fetchone() == ("Çok Boşluklu", "user", 1)
    assert con.execute("select status, outgoing_reason, created_by from shipments").fetchone() == ("checked", None, None)
    eng.dispose()


def test_eksik_sutun_eklenir(tmp_path):
    path = tmp_path / "eski_sema.db"
    con = sqlite3.connect(path)
    con.executescript("""
        create table users (id integer primary key, email varchar(255), full_name varchar(255), hashed_password varchar(255),
                            role varchar(20), is_active boolean, created_at datetime, updated_at datetime);
        create table products (id integer primary key, name varchar(255), category varchar(50), status varchar(50),
                               current_stock integer, critical_stock integer, ideal_stock integer, warehouse_id integer);
    """)
    con.close()
    eng = create_engine(f"sqlite:///{path}")
    b = _codes(kontrol_et(eng, sifre_kontrol=False))
    assert "SEMA_EKSIK_SUTUN" in b and any("products.compartment_id" in d for d in b["SEMA_EKSIK_SUTUN"].detay)
    duzelt(eng)
    b = _codes(kontrol_et(eng, sifre_kontrol=False))
    assert "SEMA_EKSIK_SUTUN" not in b and "SEMA_EKSIK_TABLO" not in b
    eng.dispose()


def test_tek_aktif_yonetici_varsayilan_sifreliyse_pasif_yapilmaz(tmp_path):
    path = tmp_path / "tek.db"
    eng = create_engine(f"sqlite:///{path}")
    import models  # noqa: F401
    from database import Base
    Base.metadata.create_all(eng)
    with eng.begin() as conn:
        conn.exec_driver_sql("insert into users (email,full_name,hashed_password,role,is_active) values (?,?,?,?,?)",
                             ("admin@deneyap.org", "A", bcrypt.hashpw(b"admin123", bcrypt.gensalt(4)).decode(), "admin", 1))
    yapilan = duzelt(eng)
    assert any("tek aktif yönetici" in y for y in yapilan)
    with eng.connect() as conn:
        assert conn.exec_driver_sql("select is_active from users").scalar() == 1
    eng.dispose()


def test_ayarlar_sayfasi_kontrol_api(client, admin, make_user, product):
    product("A")
    product("Normal ürün")
    r = client.get("/api/admin/db-check", headers=admin)
    assert r.status_code == 200
    assert any(b["kod"] == "OZET" for b in r.json())
    r = client.post("/api/admin/db-check/fix", headers=admin, json={})
    assert r.status_code == 200 and "backup" in r.json() and os.path.exists(r.json()["backup"])
    user_h, _ = make_user()
    assert client.get("/api/admin/db-check", headers=user_h).status_code == 403
    assert client.post("/api/admin/db-check/fix", headers=user_h, json={}).status_code == 403


def test_depo_atanmamis_urunleri_toplu_silme(client, admin, product, warehouse):
    w = warehouse()
    product("Depodaki", warehouse_id=w)
    product("Genel 1")
    product("Genel 2")
    r = client.delete("/api/products/all", params={"unassigned": "true"}, headers=admin)
    assert r.json()["deleted_products"] == 2
    assert [p["name"] for p in client.get("/api/products/", headers=admin).json()] == ["Depodaki"]


def test_zayif_sifreyle_giriste_degistirme_istenir(client, admin):
    from database import SessionLocal
    from models import User
    from auth import get_password_hash
    s = SessionLocal()
    u = s.query(User).first()
    u.hashed_password = get_password_hash("admin123")
    s.commit()
    s.close()
    r = client.post("/api/auth/login", json={"email": "gizem@deneyap.org", "password": "admin123"})
    assert r.status_code == 200 and r.json()["must_change_password"] is True
    r = client.post("/api/auth/change-password", headers=auth_header(r.json()["access_token"]),
                    json={"current_password": "admin123", "new_password": "Admin123"})
    assert r.status_code == 400 and "yaygın" in r.json()["detail"]
    r = client.post("/api/auth/login", json={"email": "gizem@deneyap.org", "password": "admin123"})
    r = client.post("/api/auth/change-password", headers=auth_header(r.json()["access_token"]),
                    json={"current_password": "admin123", "new_password": "Guclu2026Sifre"})
    assert r.status_code == 200
    r = client.post("/api/auth/login", json={"email": "gizem@deneyap.org", "password": "Guclu2026Sifre"})
    assert r.json()["must_change_password"] is False
