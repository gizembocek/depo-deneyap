"""
Eski sürümle (v1) oluşmuş bir atölye veritabanının küçük ama gerçekçi bir taklidi.

Gerçek bir atölyenin verisinde görülen sorunların hepsini içerir; böylece testler belirli bir
atölyenin veri dosyasına bağlı kalmadan her bilgisayarda çalışır:
  - Aynı Excel 3 kez aktarılmış: 'depo atanmamış', 'Elektronik' deposu ve 'Ana Depo' (yalnızca
    Ana Depo'dakiler kullanılmış: stok hareketi ve irsaliye var)
  - Ana Depo'da aynı listeden iki kez girilmiş (aynı sayfa) ve farklı ders listelerinde geçen ürünler
  - Varsayılan şifreli örnek hesaplar (admin@deneyap.org/admin123, kullanici@deneyap.org/user123)
  - Aynı dersin farklı yazımları ('Robotik ve Kodlama', 31 karakterde kesilmiş Excel sayfa adı)
  - Ad içinde satır sonu olan ürünler, ürünsüz deneme gönderimleri, güncel olmayan gönderim durumları
  - Yeni sürümde eklenen 'app_settings' tablosu yok
"""
import sqlite3

import bcrypt

GERCEK_SIFRE = "Gercek2026Sifre"

SAYFALAR = {
    "Tasarım ve Üretim": [("Makas", 50), ("Sıcak Silikon Tabancası", 6), ("Lehim Teli", 1), ("Şarjlı Pil", 14)],
    "Malzeme Bilimi ve Nanoteknoloji": [("Makas", 50), ("Işıklı Büyüteç", 3), ("Balon", 10), ("Direnç", 270)],
    "Elektronik Programlama ve Nesne": [("Batarya", 20), ("Şarjlı Pil", 14), ("Arduino Uno", 12)],
    "Robotik ve Kodlama": [("Servo Motor", 20)],
    "Demirbaş Listesi": [("3 Boyutlu\nYazıcı", 2), ("Pleksi Kabin \nEn: 40 cm", 1)],
}
# Ana Depo'ya ikinci aktarımda aynı sayfadan tekrar girenler
ANA_DEPO_TEKRAR = [("Tasarım ve Üretim", "Makas", 50), ("Malzeme Bilimi ve Nanoteknoloji", "Işıklı Büyüteç", 3),
                   ("Elektronik Programlama ve Nesne", "Batarya", 18)]
STANDART = ["Robotik Kodlama", "Yapay Zeka", "Siber Güvenlik", "Malzeme Bilimi ve Nanoteknoloji", "Tasarım ve Üretim",
            "Enerji Teknolojileri", "Yazılım Teknolojileri", "Mobil Uygulama",
            "Elektronik Programlama ve Nesnelerin İnterneti (EPNİ)", "İleri Robotik",
            "Havacılık ve Uzay Teknolojileri", "Genel"]

FARKLI_MALZEME = 12          # farklı ürün adı sayısı
SATIR_PER_KOPYA = 14         # bir Excel aktarımındaki satır sayısı
ANA_DEPO_SATIR = SATIR_PER_KOPYA + len(ANA_DEPO_TEKRAR)
TOPLAM_URUN = 2 * SATIR_PER_KOPYA + ANA_DEPO_SATIR  # 45


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(4)).decode()


def eski_veritabani_olustur(path) -> dict:
    """Verilen yola eski sürüm veritabanı yazar. Bazı kimlik numaralarını döndürür."""
    import models  # noqa: F401
    from database import Base
    from sqlalchemy import create_engine

    eng = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(eng)
    eng.dispose()
    con = sqlite3.connect(path)
    con.execute("drop table app_settings")  # v1'de yoktu
    con.executemany("insert into users (id,email,full_name,hashed_password,role,is_active,created_at) values (?,?,?,?,?,?,?)", [
        (1, "admin@deneyap.org", "Admin Kullanıcı", _hash("admin123"), "admin", 1, "2026-05-11 09:55:01"),
        (2, "kullanici@deneyap.org", "Deneyap Eğitmeni", _hash("user123"), "user", 1, "2026-05-11 09:55:01"),
        (3, "gizem@deneyap.org", "Gizem Böcek", _hash(GERCEK_SIFRE), "admin", 1, "2026-09-21 08:30:11"),
    ])
    con.executemany("insert into warehouses (id,name,location,created_at) values (?,?,?,?)", [
        (1, "Deneyap Atölyesi Ana Depo", "Atölye Katı", "2026-05-11 09:55:01"),
        (2, "Elektronik Malzeme Deposu", "Oda 2", "2026-05-11 09:55:01"),
    ])
    con.executemany("insert into cabinets (id,name,warehouse_id) values (?,?,?)", [(1, "Dolap 1", 1), (2, "Dolap 1", 2)])
    con.executemany("insert into user_warehouse_access values (?,?)", [(1, 1), (1, 2), (2, 1)])
    courses = STANDART + ["Demirbaş Listesi", "Robotik ve Kodlama", "Elektronik Programlama ve Nesne"]
    con.executemany("insert into courses (id,name) values (?,?)", list(enumerate(courses, 1)))
    course_id = {name: i for i, name in enumerate(courses, 1)}

    pid = 0
    ids = {}

    def add(warehouse, sheet, name, stock, created):
        nonlocal pid
        pid += 1
        con.execute("insert into products (id,name,description,category,status,current_stock,critical_stock,ideal_stock,"
                    "warehouse_id,created_at,updated_at) values (?,?,?,?,?,?,?,?,?,?,?)",
                    (pid, name, f"Kaynak: {sheet}", "Genel / Dayanıklı Malzeme", "Çalışan", stock, 5, 100,
                     warehouse, created, created))
        con.execute("insert into product_courses values (?,?)", (pid, course_id[sheet]))
        ids.setdefault((warehouse, name), pid)
        return pid

    for warehouse, created in ((None, "2026-05-12 09:05:00"), (2, "2026-06-08 12:40:00"), (1, "2026-06-08 13:03:00")):
        for sheet, rows in SAYFALAR.items():
            for name, stock in rows:
                add(warehouse, sheet, name, stock, created)
    for sheet, name, stock in ANA_DEPO_TEKRAR:
        add(1, sheet, name, stock, "2026-06-08 13:21:00")

    klemens = ids[(1, "Direnç")]
    pervane = ids[(1, "Servo Motor")]
    con.executemany("insert into shipments (id,name,shipment_type,outgoing_reason,invoice_image_url,status,notes,created_by,created_at) "
                    "values (?,?,?,?,?,?,?,?,?)", [
        (1, "product-images", "Giriş", None, "data:image/png;base64,iVBORw0KGgo=", "pending", "eksik geldi", 1, "2026-05-11 10:33:54"),
        (2, "mayıs", "Çıkış", "Garanti", None, "pending", "bozuk", 1, "2026-05-11 10:38:03"),
        (3, "ağustos irsaliyesi", "Giriş", None, None, "pending", None, 1, "2026-06-08 13:05:42"),
        (4, "eylül irsaliyesi", "Çıkış", "", None, "pending", None, 1, "2026-06-08 13:06:25"),
    ])
    con.executemany("insert into shipment_items (id,shipment_id,product_id,expected_quantity,actual_quantity,status) values (?,?,?,?,?,?)",
                    [(1, 3, klemens, 50, 20, "missing"), (2, 4, pervane, 8, 8, "complete")])
    con.executemany("insert into stock_logs (id,product_id,user_id,action,quantity_change,previous_value,new_value,note,created_at) "
                    "values (?,?,?,?,?,?,?,?,?)", [
        (1, klemens, 1, "add", 20, "250", "270", "Gönderim: ağustos irsaliyesi", "2026-06-08 13:05:42"),
        (2, pervane, 1, "remove", 8, "28", "20", "Gönderim: eylül irsaliyesi", "2026-06-08 13:06:25"),
    ])
    con.commit()
    con.close()
    return {"ana_depo": 1, "elektronik": 2, "klemens": klemens, "pervane": pervane}
