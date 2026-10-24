"""
Veritabanı sağlık kontrolü ve güvenli onarım aracı.

Kullanım (backend klasöründe):
    python veritabani_kontrol.py                      # yalnızca rapor (hiçbir şeyi değiştirmez)
    python veritabani_kontrol.py --duzelt             # önce yedek alır, sonra GÜVENLİ düzeltmeleri yapar
    python veritabani_kontrol.py --duzelt --tekrar-eden-urunleri-birlestir
    python veritabani_kontrol.py --duzelt --bos-gonderimleri-sil
    python veritabani_kontrol.py --duzelt --kopya-aktarimlari-sil   # aynı Excel'in fazla kopyalarını sil
    python veritabani_kontrol.py --url "sqlite:///baska.db"   # .env yerine başka bir veritabanı

Güvenli düzeltmeler ürün/stok verisini SİLMEZ: yetim (sahipsiz) kayıtları temizler,
geçersiz değerleri düzeltir, tekrar eden dersleri birleştirir, varsayılan şifreli
hesapları pasif yapar. Tekrar eden ürünleri birleştirmek, aynı Excel'in fazla kopyalarını
silmek ve boş gönderimleri silmek ayrıca istenmedikçe yapılmaz.

SQLite, SQL Server ve PostgreSQL'de çalışır.
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bcrypt  # noqa: E402
from sqlalchemy import String, create_engine, delete, func, inspect, select, text, update  # noqa: E402

import models  # noqa: E402
from database import BACKEND_DIR, Base, tr_fold  # noqa: E402
from excel_import import course_key, parse_status  # noqa: E402
from models import (  # noqa: E402
    CATEGORY_VALUES, ROLE_VALUES, STATUS_VALUES, Cabinet, Compartment, Course, Product, Shelf,
    Shipment, ShipmentItem, StockLog, User, Warehouse, product_courses, user_warehouse_access,
)

DEMO_ACCOUNTS = {"admin@deneyap.org": "admin123", "kullanici@deneyap.org": "user123"}
CHECK_PASSWORDS = ["admin123", "user123", "123456", "12345678", "password", "deneyap123"]
QUICK_PASSWORDS = ["admin123", "user123", "123456"]  # arayüzden çalıştırılan hızlı tarama
_BCRYPT_CACHE: dict = {}


def weak_password_of(email: str, hashed: str, candidates=None):
    """Hesabın şifresi bilinen/varsayılan bir şifreyse onu döndürür (sonuçlar önbelleğe alınır)."""
    candidates = ([DEMO_ACCOUNTS[email]] if email in DEMO_ACCOUNTS else []) + list(candidates or CHECK_PASSWORDS)
    for pw in dict.fromkeys(candidates):
        key = (hashed, pw)
        if key not in _BCRYPT_CACHE:
            try:
                _BCRYPT_CACHE[key] = bcrypt.checkpw(pw.encode(), (hashed or "").encode())
            except ValueError:
                _BCRYPT_CACHE[key] = False
        if _BCRYPT_CACHE[key]:
            return pw
    return None
STANDART_DERSLER = [
    "Robotik Kodlama", "Yapay Zeka", "Siber Güvenlik", "Malzeme Bilimi ve Nanoteknoloji", "Tasarım ve Üretim",
    "Enerji Teknolojileri", "Yazılım Teknolojileri", "Mobil Uygulama",
    "Elektronik Programlama ve Nesnelerin İnterneti (EPNİ)", "İleri Robotik",
    "Havacılık ve Uzay Teknolojileri", "Genel",
]
SEVIYE_SIRASI = {"KRİTİK": 0, "UYARI": 1, "BİLGİ": 2}


@dataclass
class Bulgu:
    kod: str
    seviye: str            # KRİTİK | UYARI | BİLGİ
    baslik: str
    adet: int = 0
    detay: List[str] = field(default_factory=list)
    duzeltme: Optional[str] = None   # güvenli düzeltmenin ne yapacağı (None: elle yapılmalı)
    oneri: Optional[str] = None      # elle yapılacaksa ne önerilir


def _norm_spaces(s):
    return re.sub(r"\s+", " ", s).strip() if isinstance(s, str) else s


def _fold(s):
    return tr_fold(_norm_spaces(s) or "")


def _rows(conn, table, *cols):
    return conn.execute(select(*[table.c[c] for c in cols])).all()


# ---------------------------------------------------------------------------
# KONTROLLER
# ---------------------------------------------------------------------------
def kontrol_et(engine, sifre_kontrol: bool = True, sifre_listesi=None) -> List[Bulgu]:
    bulgular: List[Bulgu] = []
    insp = inspect(engine)
    existing_tables = set(insp.get_table_names())

    # 1) Şema
    eksik_tablo = [t.name for t in Base.metadata.sorted_tables if t.name not in existing_tables]
    if eksik_tablo:
        bulgular.append(Bulgu("SEMA_EKSIK_TABLO", "UYARI", "Eksik tablolar", len(eksik_tablo), eksik_tablo,
                              duzeltme="Eksik tablolar oluşturulur."))
    eksik_sutun = []
    for t in Base.metadata.sorted_tables:
        if t.name in existing_tables:
            cols = {c["name"].lower() for c in insp.get_columns(t.name)}
            eksik_sutun += [f"{t.name}.{c.name}" for c in t.columns if c.name.lower() not in cols]
    if eksik_sutun:
        bulgular.append(Bulgu("SEMA_EKSIK_SUTUN", "KRİTİK", "Eksik sütunlar (uygulama bu tablolarda hata verir)",
                              len(eksik_sutun), eksik_sutun, duzeltme="Eksik sütunlar boş değerle eklenir."))
    if eksik_sutun or [t for t in eksik_tablo if t != "app_settings"]:
        # Temel tablolar/sütunlar eksikse diğer kontroller yapılamaz
        return sorted(bulgular, key=lambda b: SEVIYE_SIRASI[b.seviye])

    with engine.connect() as conn:
        T = {t.name: t for t in Base.metadata.sorted_tables}
        has = lambda name: name in existing_tables  # noqa: E731

        # 2) SQLite bütünlük
        if engine.dialect.name == "sqlite":
            res = conn.execute(text("PRAGMA integrity_check")).scalar()
            if res != "ok":
                bulgular.append(Bulgu("SQLITE_BUTUNLUK", "KRİTİK", "SQLite dosyası bozuk", 1, [str(res)[:300]],
                                      oneri="Son yedekten geri yükleyin (yedekleme.py yukle)."))

        # 3) Kullanıcılar
        users = conn.execute(select(User.__table__)).mappings().all()
        active_admins = [u for u in users if u["role"] == "admin" and u["is_active"] in (True, 1, None)]
        if users and not active_admins:
            bulgular.append(Bulgu("AKTIF_YONETICI_YOK", "KRİTİK", "Aktif yönetici hesabı yok", 1,
                                  oneri="python sifre_sifirla.py <e-posta> ile bir yönetici hesabını aktif edin."))
        if sifre_kontrol:
            zayif = []
            for u in users:
                if u["is_active"] in (False, 0):
                    continue
                pw = weak_password_of(u["email"], u["hashed_password"], sifre_listesi)
                if pw:
                    demo = " (örnek/demo hesap)" if u["email"] in DEMO_ACCOUNTS else ""
                    zayif.append(f"{u['email']}{demo} → şifresi '{pw}' "
                                 f"[{'yönetici' if u['role'] == 'admin' else 'kullanıcı'}]")
            if zayif:
                bulgular.append(Bulgu("ZAYIF_SIFRE", "KRİTİK", "Bilinen/varsayılan şifreyle açık hesaplar "
                                      "(ağdaki herkes bu hesaplarla girebilir)", len(zayif), zayif,
                                      duzeltme="Bu hesaplar pasif yapılır (silinmez; yönetici tekrar aktif edebilir). "
                                               "Tek aktif yönetici sizseniz önce kendi şifrenizi değiştirin."))
        emails = Counter(_fold(u["email"]) for u in users)
        dup_mail = [e for e, n in emails.items() if n > 1]
        if dup_mail:
            bulgular.append(Bulgu("TEKRAR_EPOSTA", "KRİTİK", "Büyük/küçük harf farkıyla aynı e-posta "
                                  "(SQL Server'a taşımada hata verir)", len(dup_mail), dup_mail,
                                  oneri="Kullanıcılar sayfasından fazla olan hesabı silin."))
        bad_role = [u["email"] for u in users if u["role"] not in ROLE_VALUES]
        if bad_role:
            bulgular.append(Bulgu("GECERSIZ_ROL", "UYARI", "Geçersiz kullanıcı rolü", len(bad_role), bad_role,
                                  duzeltme="Rol 'user' (kullanıcı) yapılır."))

        # 4) Yetim kayıtlar ve konum tutarlılığı
        wh_ids = {r[0] for r in _rows(conn, T["warehouses"], "id")}
        cab = {r[0]: r[1] for r in _rows(conn, T["cabinets"], "id", "warehouse_id")}
        shelf = {r[0]: r[1] for r in _rows(conn, T["shelves"], "id", "cabinet_id")}
        comp = {r[0]: r[1] for r in _rows(conn, T["compartments"], "id", "shelf_id")}
        user_ids = {u["id"] for u in users}
        prods = conn.execute(select(Product.__table__)).mappings().all()
        prod_ids = {p["id"] for p in prods}
        course_rows = conn.execute(select(Course.__table__)).mappings().all()
        course_ids = {c["id"] for c in course_rows}
        ship_ids = {r[0] for r in _rows(conn, T["shipments"], "id")}

        yetim = []
        yetim += [f"Dolap #{i} (olmayan depo #{w})" for i, w in cab.items() if w not in wh_ids]
        yetim += [f"Raf #{i} (olmayan dolap #{c})" for i, c in shelf.items() if c not in cab]
        yetim += [f"Bölme #{i} (olmayan raf #{s})" for i, s in comp.items() if s not in shelf]
        for p in prods:
            if p["warehouse_id"] is not None and p["warehouse_id"] not in wh_ids:
                yetim.append(f"Ürün #{p['id']} {p['name']} → olmayan depo #{p['warehouse_id']}")
            for col, ids in (("cabinet_id", cab), ("shelf_id", shelf), ("compartment_id", comp)):
                if p[col] is not None and p[col] not in ids:
                    yetim.append(f"Ürün #{p['id']} {p['name']} → olmayan {col.replace('_id', '')} #{p[col]}")
        logs = _rows(conn, T["stock_logs"], "id", "product_id", "user_id")
        yetim += [f"Stok kaydı #{i} → olmayan ürün #{pid}" for i, pid, _ in logs if pid not in prod_ids]
        yetim += [f"Stok kaydı #{i} → olmayan kullanıcı #{uid}" for i, _, uid in logs if uid is not None and uid not in user_ids]
        items = _rows(conn, T["shipment_items"], "id", "shipment_id", "product_id")
        yetim += [f"Gönderim satırı #{i} → olmayan gönderim #{s}" for i, s, _ in items if s not in ship_ids]
        yetim += [f"Gönderim satırı #{i} → olmayan ürün #{p}" for i, _, p in items if p not in prod_ids]
        for sid, cby in _rows(conn, T["shipments"], "id", "created_by"):
            if cby is not None and cby not in user_ids:
                yetim.append(f"Gönderim #{sid} → olmayan kullanıcı #{cby}")
        pc = _rows(conn, product_courses, "product_id", "course_id")
        yetim += [f"Ürün-ders bağı ({p},{c})" for p, c in pc if p not in prod_ids or c not in course_ids]
        if has("user_warehouse_access"):
            uwa = _rows(conn, user_warehouse_access, "user_id", "warehouse_id")
            yetim += [f"Depo yetkisi ({u},{w})" for u, w in uwa if u not in user_ids or w not in wh_ids]
        if yetim:
            bulgular.append(Bulgu("YETIM_KAYIT", "KRİTİK", "Sahipsiz (yetim) kayıtlar — SQL Server'a taşımayı engeller",
                                  len(yetim), yetim[:50], duzeltme="Sahipsiz bağlantılar boşaltılır veya silinir."))

        tutarsiz = []
        for p in prods:
            w, c, s, k = p["warehouse_id"], p["cabinet_id"], p["shelf_id"], p["compartment_id"]
            if c is not None and c in cab and cab[c] != w:
                tutarsiz.append(f"Ürün #{p['id']} {p['name']}: dolap başka depoya ait")
            elif s is not None and s in shelf and shelf[s] != c:
                tutarsiz.append(f"Ürün #{p['id']} {p['name']}: raf seçili dolaba ait değil")
            elif k is not None and k in comp and comp[k] != s:
                tutarsiz.append(f"Ürün #{p['id']} {p['name']}: bölme seçili rafa ait değil")
        if tutarsiz:
            bulgular.append(Bulgu("KONUM_TUTARSIZ", "UYARI", "Tutarsız ürün konumları", len(tutarsiz), tutarsiz[:50],
                                  duzeltme="Tutarsız olan konum seviyesi ve altı boşaltılır."))

        # 5) Geçersiz / eksik değerler
        gecersiz = []
        for p in prods:
            if not _norm_spaces(p["name"]):
                gecersiz.append(f"Ürün #{p['id']}: ad boş")
            if p["category"] not in CATEGORY_VALUES:
                gecersiz.append(f"Ürün #{p['id']} {p['name']}: kategori '{p['category']}'")
            if p["status"] not in STATUS_VALUES:
                gecersiz.append(f"Ürün #{p['id']} {p['name']}: durum '{p['status']}'")
            for col in ("current_stock", "critical_stock", "ideal_stock"):
                if p[col] is None or p[col] < 0:
                    gecersiz.append(f"Ürün #{p['id']} {p['name']}: {col} = {p[col]}")
        for s in conn.execute(select(Shipment.__table__)).mappings().all():
            if s["shipment_type"] not in ("Giriş", "Çıkış"):
                gecersiz.append(f"Gönderim #{s['id']} {s['name']}: tip '{s['shipment_type']}'")
        for u in users:
            if u["is_active"] is None:
                gecersiz.append(f"Kullanıcı {u['email']}: aktiflik bilgisi boş")
        if gecersiz:
            bulgular.append(Bulgu("GECERSIZ_DEGER", "UYARI", "Geçersiz veya eksik değerler", len(gecersiz), gecersiz[:50],
                                  duzeltme="Geçersiz kategori/durum en yakın geçerli değere, eksik/negatif stok 0'a "
                                           "çevrilir; adı boş ürüne geçici ad verilir."))

        # 6) Fazla boşluk ve sütun uzunluğu
        bosluk, uzun = [], []
        for t in Base.metadata.sorted_tables:
            if not has(t.name):
                continue
            str_cols = [c for c in t.columns if isinstance(c.type, String)]
            if not str_cols:
                continue
            pk = list(t.primary_key.columns)
            for row in conn.execute(select(*pk, *str_cols)).all():
                key = ",".join(str(row[i]) for i in range(len(pk)))
                for i, c in enumerate(str_cols, len(pk)):
                    v = row[i]
                    if not isinstance(v, str):
                        continue
                    if c.name in ("name", "full_name") and v != _norm_spaces(v):
                        bosluk.append(f"{t.name} #{key}: '{v}'")
                    length = getattr(c.type, "length", None)
                    if length and len(v) > length:
                        uzun.append(f"{t.name}.{c.name} #{key}: {len(v)} karakter (sınır {length})")
        if bosluk:
            bulgular.append(Bulgu("FAZLA_BOSLUK", "BİLGİ", "Başında/sonunda veya içinde fazla boşluk olan adlar",
                                  len(bosluk), bosluk[:30], duzeltme="Fazla boşluklar temizlenir."))
        if uzun:
            bulgular.append(Bulgu("UZUN_DEGER", "KRİTİK", "Sütun sınırını aşan metinler — SQL Server'a taşımada "
                                  "'String or binary data would be truncated' hatası verir", len(uzun), uzun[:30],
                                  duzeltme="Metin sütun sınırına kısaltılır."))

        # 7) Tekrar eden dersler
        groups = _course_groups(course_rows)
        dup_courses = [" = ".join(f"'{c['name']}'" for c in g) for g in groups if len(g) > 1]
        if dup_courses:
            bulgular.append(Bulgu("TEKRAR_DERS", "UYARI", "Aynı dersin farklı yazımları (ör. kısaltılmış Excel sayfa adı)",
                                  len(dup_courses), dup_courses,
                                  duzeltme="Dersler tek kayıtta birleştirilir, ürün bağlantıları korunur."))

        # 8) Tekrar eden ürünler (aynı depoda aynı ad)
        logs_per = Counter(pid for _, pid, _ in logs)
        items_per = Counter(p for _, _, p in items)
        dup_groups = _product_dup_groups(prods)
        if dup_groups:
            wh_names = {r[0]: r[1] for r in _rows(conn, T["warehouses"], "id", "name")}
            detay = [f"[{wh_names.get(w, 'Depo atanmamış')}] {g[0]['name']}: "
                     + ", ".join(f"#{p['id']} stok {p['current_stock']}" for p in g)
                     for (w, _), g in list(dup_groups.items())[:40]]
            bulgular.append(Bulgu("TEKRAR_URUN", "UYARI",
                                  "Aynı depoda aynı adla birden fazla ürün (çoğunlukla aynı malzemenin birden fazla "
                                  "ders listesinde yazılmasından)", sum(len(g) for g in dup_groups.values()), detay,
                                  oneri=f"{len(dup_groups)} grup var. Aynı malzemeyse --tekrar-eden-urunleri-birlestir "
                                        "ile birleştirin (stok olarak en büyük değer alınır, dersler birleşir)."))

        # 9) Aynı Excel'in birden fazla depoya aktarılması
        for msg in _copied_imports(prods, wh_ids, conn, T, logs_per, items_per):
            bulgular.append(msg)

        # 10) Gönderimler
        ships = conn.execute(select(Shipment.__table__)).mappings().all()
        items_by_ship = defaultdict(list)
        for it in conn.execute(select(ShipmentItem.__table__)).mappings().all():
            items_by_ship[it["shipment_id"]].append(it)
        bos = [f"#{s['id']} '{s['name']}' ({s['shipment_type']})" for s in ships if not items_by_ship.get(s["id"])]
        if bos:
            bulgular.append(Bulgu("BOS_GONDERIM", "BİLGİ", "Ürünsüz (boş) gönderim kayıtları", len(bos), bos,
                                  oneri="Deneme kaydıysa --bos-gonderimleri-sil ile veya Giriş/Çıkış sayfasından silin."))
        durum = []
        for s in ships:
            its = items_by_ship.get(s["id"], [])
            expected = "pending" if any(i["actual_quantity"] is None for i in its) else "checked"
            if its and s["status"] != expected:
                durum.append(f"#{s['id']} '{s['name']}': kayıtlı '{s['status']}', olması gereken '{expected}'")
            for i in its:
                st = _item_status(i["expected_quantity"], i["actual_quantity"])
                if i["status"] != st:
                    durum.append(f"Satır #{i['id']}: kayıtlı '{i['status']}', olması gereken '{st}'")
            if s["outgoing_reason"] == "":
                durum.append(f"#{s['id']} '{s['name']}': boş çıkış sebebi")
        if durum:
            bulgular.append(Bulgu("GONDERIM_DURUMU", "BİLGİ", "Gönderim durum bilgisi güncel değil", len(durum), durum,
                                  duzeltme="Durumlar satırlara göre yeniden hesaplanır."))

        # 11) Büyük görseller
        buyuk = []
        for p in prods:
            if isinstance(p["image_url"], str) and len(p["image_url"]) > 1_000_000:
                buyuk.append(f"Ürün #{p['id']} {p['name']}: {len(p['image_url']) // 1024} KB")
        for s in ships:
            for col in ("arrival_image_url", "visual_image_url", "invoice_image_url"):
                if isinstance(s[col], str) and len(s[col]) > 1_000_000:
                    buyuk.append(f"Gönderim #{s['id']} {col}: {len(s[col]) // 1024} KB")
        if buyuk:
            bulgular.append(Bulgu("BUYUK_GORSEL", "BİLGİ", "Veritabanında saklanan büyük görseller", len(buyuk), buyuk))

        # 12) Genel bilgi
        info = [f"Veritabanı: {engine.dialect.name}", f"Ürün: {len(prods)}", f"Kullanıcı: {len(users)}",
                f"Depo: {len(wh_ids)}", f"Ders: {len(course_rows)}", f"Gönderim: {len(ships)}",
                f"Stok kaydı: {len(logs)}", f"Farklı ürün adı: {len({_fold(p['name']) for p in prods})}"]
        if engine.dialect.name == "mssql":
            try:
                row = conn.execute(text("SELECT CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(50)), "
                                        "CAST(SERVERPROPERTY('Edition') AS NVARCHAR(100)), "
                                        "CAST(DATABASEPROPERTYEX(DB_NAME(), 'Collation') AS NVARCHAR(100))")).one()
                info.append(f"SQL Server {row[0]} – {row[1]} – harmanlama {row[2]}")
            except Exception:
                pass
        bulgular.append(Bulgu("OZET", "BİLGİ", "Özet", 0, info))

    return sorted(bulgular, key=lambda b: SEVIYE_SIRASI[b.seviye])


def _item_status(expected, actual):
    if actual is None:
        return "pending"
    if actual == expected:
        return "complete"
    return "missing" if actual < (expected or 0) else "extra"


def _course_groups(course_rows):
    """Aynı dersin farklı yazımlarını gruplar: 've' farkı, büyük/küçük harf, kısaltılmış sayfa adı."""
    groups = []
    for c in sorted(course_rows, key=lambda c: -len(c["name"] or "")):
        key = course_key(c["name"] or "")
        for g in groups:
            gk = course_key(g[0]["name"])
            # Excel sayfa adları 31 karakterle kesilir: kısaltılmış uzun adlar baş kısmıyla eşleşir
            if key == gk or (len(c["name"] or "") >= 28 and gk.startswith(key)):
                g.append(c)
                break
        else:
            groups.append([c])
    return groups


def _canonical_course(group):
    for c in group:
        if c["name"] in STANDART_DERSLER:
            return c
    return max(group, key=lambda c: (len(c["name"]), -c["id"]))


def _product_dup_groups(prods):
    d = defaultdict(list)
    for p in prods:
        d[(p["warehouse_id"], _fold(p["name"]))].append(p)
    return {k: sorted(v, key=lambda p: p["id"]) for k, v in d.items() if len(v) > 1 and k[1]}


def _copy_clusters(prods):
    """Ürün listeleri birbirinin en az %90 aynısı olan depoları (veya 'depo atanmamış') kümeler.
    Dönüş: (depoya göre ürünler, [[depo_id, ...], ...]) — yalnızca 2+ üyeli kümeler."""
    by_wh = defaultdict(list)
    for p in prods:
        by_wh[p["warehouse_id"]].append(p)
    keys = [k for k, v in by_wh.items() if len(v) >= 10]
    parent = {k: k for k in keys}

    def find(k):
        while parent[k] != k:
            k = parent[k]
        return k

    for i, a in enumerate(keys):
        ca = Counter(_fold(p["name"]) for p in by_wh[a])
        for b in keys[i + 1:]:
            cb = Counter(_fold(p["name"]) for p in by_wh[b])
            if sum((ca & cb).values()) / min(sum(ca.values()), sum(cb.values())) >= 0.9:
                parent[find(b)] = find(a)
    clusters = defaultdict(list)
    for k in keys:
        clusters[find(k)].append(k)
    return by_wh, [m for m in clusters.values() if len(m) >= 2]


def _copy_to_keep(members, by_wh, activity):
    """Kümede tutulacak kopya: en çok stok hareketi/gönderimi olan; eşitse en yeni eklenen."""
    return max(members, key=lambda w: (sum(activity[p["id"]] for p in by_wh[w]),
                                       max(str(p["created_at"] or "") for p in by_wh[w])))


def _copied_imports(prods, wh_ids, conn, T, logs_per, items_per):
    """Aynı ürün listesinin birden fazla depoda bulunmasını (tekrarlanan Excel aktarımı) bulur."""
    wh_names = {r[0]: r[1] for r in _rows(conn, T["warehouses"], "id", "name")}
    label = lambda w: f"'{wh_names.get(w, '?')}'" if w is not None else "'Depo atanmamış'"  # noqa: E731
    by_wh, clusters = _copy_clusters(prods)
    activity = Counter()
    activity.update(logs_per)
    activity.update(items_per)
    out = []
    for members in clusters:
        keep = _copy_to_keep(members, by_wh, activity)
        detay = []
        for w in sorted(members, key=lambda w: min(str(p["created_at"]) for p in by_wh[w])):
            ps = by_wh[w]
            act = sum(logs_per[p["id"]] + items_per[p["id"]] for p in ps)
            dates = sorted(str(p["created_at"])[:16] for p in ps if p["created_at"])
            detay.append(f"{label(w)}: {len(ps)} ürün, eklenme {dates[0] if dates else '?'}"
                         f" → {dates[-1] if dates else '?'}, stok hareketi/gönderim: {act}"
                         + ("  ← tutulacak" if w == keep else ""))
        out.append(Bulgu("KOPYA_AKTARIM", "UYARI",
                         f"Aynı ürün listesi {len(members)} farklı yerde — aynı Excel muhtemelen {len(members)} kez aktarılmış",
                         sum(len(by_wh[w]) for w in members), detay,
                         oneri="--kopya-aktarimlari-sil ile (veya Ayarlar sayfasındaki kutucukla) 'tutulacak' işaretli "
                               "kopya bırakılır, hiç kullanılmamış diğer kopyalar silinir. Önce otomatik yedek alınır."))
    return out


# ---------------------------------------------------------------------------
# DÜZELTMELER
# ---------------------------------------------------------------------------
def duzelt(engine, tekrar_urun: bool = False, bos_gonderim: bool = False, stok_kurali: str = "max",
           sifre_listesi=None, kopya_aktarim: bool = False) -> List[str]:
    """Güvenli düzeltmeleri tek bir işlemde (transaction) uygular. Yapılanların listesini döndürür."""
    yapilan: List[str] = []
    insp = inspect(engine)
    existing = set(insp.get_table_names())
    eksik = [t for t in Base.metadata.sorted_tables if t.name not in existing]
    if eksik:
        Base.metadata.create_all(bind=engine)
        yapilan.append(f"Eksik tablolar oluşturuldu: {', '.join(t.name for t in eksik)}")
        insp = inspect(engine)
    with engine.begin() as conn:
        prep = engine.dialect.identifier_preparer
        for t in Base.metadata.sorted_tables:
            cols = {c["name"].lower() for c in insp.get_columns(t.name)}
            for c in t.columns:
                if c.name.lower() not in cols:
                    keyword = "ADD COLUMN" if engine.dialect.name in ("sqlite", "postgresql") else "ADD"
                    conn.execute(text(f"ALTER TABLE {prep.quote(t.name)} {keyword} {prep.quote(c.name)} "
                                      f"{c.type.compile(dialect=engine.dialect)} NULL"))
                    yapilan.append(f"Sütun eklendi: {t.name}.{c.name}")

        T = {t.name: t for t in Base.metadata.sorted_tables}
        P, U, S, SI = Product.__table__, User.__table__, Shipment.__table__, ShipmentItem.__table__

        # Yetim kayıtlar: önce sahipsiz dolap/raf/bölmeler belirlenir, ürünlerdeki
        # bağlantıları boşaltılır, sonra çocuktan ebeveyne doğru silinir.
        wh_ids = {r[0] for r in _rows(conn, T["warehouses"], "id")}
        cab_all = {r[0]: r[1] for r in _rows(conn, T["cabinets"], "id", "warehouse_id")}
        shelf_all = {r[0]: r[1] for r in _rows(conn, T["shelves"], "id", "cabinet_id")}
        comp_all = {r[0]: r[1] for r in _rows(conn, T["compartments"], "id", "shelf_id")}
        cab_ids = {i for i, w in cab_all.items() if w in wh_ids}
        shelf_ids = {i for i, c in shelf_all.items() if c in cab_ids}
        comp_ids = {i for i, s in comp_all.items() if s in shelf_ids}
        n = 0
        user_ids = {r[0] for r in _rows(conn, U, "id")}
        for p in conn.execute(select(P.c.id, P.c.warehouse_id, P.c.cabinet_id, P.c.shelf_id, P.c.compartment_id)).all():
            vals = {}
            if p.warehouse_id is not None and p.warehouse_id not in wh_ids:
                vals = {"warehouse_id": None, "cabinet_id": None, "shelf_id": None, "compartment_id": None}
            else:
                if p.cabinet_id is not None and p.cabinet_id not in cab_ids:
                    vals.update(cabinet_id=None, shelf_id=None, compartment_id=None)
                if p.shelf_id is not None and p.shelf_id not in shelf_ids:
                    vals.update(shelf_id=None, compartment_id=None)
                if p.compartment_id is not None and p.compartment_id not in comp_ids:
                    vals.update(compartment_id=None)
            if vals:
                conn.execute(update(P).where(P.c.id == p.id).values(**vals))
                n += 1
        for table, alive, everything in ((T["compartments"], comp_ids, comp_all), (T["shelves"], shelf_ids, shelf_all),
                                         (T["cabinets"], cab_ids, cab_all)):
            for obj_id in set(everything) - alive:
                conn.execute(delete(table).where(table.c.id == obj_id)); n += 1
        prod_ids = {r[0] for r in _rows(conn, P, "id")}
        L = T["stock_logs"]
        for lid, pid, uid in _rows(conn, L, "id", "product_id", "user_id"):
            if pid not in prod_ids:
                conn.execute(delete(L).where(L.c.id == lid)); n += 1
            elif uid is not None and uid not in user_ids:
                conn.execute(update(L).where(L.c.id == lid).values(user_id=None)); n += 1
        ship_ids = {r[0] for r in _rows(conn, S, "id")}
        for iid, sid, pid in _rows(conn, SI, "id", "shipment_id", "product_id"):
            if sid not in ship_ids or pid not in prod_ids:
                conn.execute(delete(SI).where(SI.c.id == iid)); n += 1
        for sid, cby in _rows(conn, S, "id", "created_by"):
            if cby is not None and cby not in user_ids:
                conn.execute(update(S).where(S.c.id == sid).values(created_by=None)); n += 1
        course_ids = {r[0] for r in _rows(conn, T["courses"], "id")}
        for pid, cid in _rows(conn, product_courses, "product_id", "course_id"):
            if pid not in prod_ids or cid not in course_ids:
                conn.execute(delete(product_courses).where(product_courses.c.product_id == pid,
                                                           product_courses.c.course_id == cid)); n += 1
        for uid, wid in _rows(conn, user_warehouse_access, "user_id", "warehouse_id"):
            if uid not in user_ids or wid not in wh_ids:
                conn.execute(delete(user_warehouse_access).where(user_warehouse_access.c.user_id == uid,
                                                                 user_warehouse_access.c.warehouse_id == wid)); n += 1
        if n:
            yapilan.append(f"{n} sahipsiz kayıt/bağlantı temizlendi")

        # Konum tutarlılığı
        cab = {r[0]: r[1] for r in _rows(conn, T["cabinets"], "id", "warehouse_id")}
        shelf = {r[0]: r[1] for r in _rows(conn, T["shelves"], "id", "cabinet_id")}
        comp = {r[0]: r[1] for r in _rows(conn, T["compartments"], "id", "shelf_id")}
        n = 0
        for p in conn.execute(select(P.c.id, P.c.warehouse_id, P.c.cabinet_id, P.c.shelf_id, P.c.compartment_id)).all():
            vals = {}
            if p.cabinet_id is not None and cab.get(p.cabinet_id) != p.warehouse_id:
                vals = {"cabinet_id": None, "shelf_id": None, "compartment_id": None}
            elif p.shelf_id is not None and (p.cabinet_id is None or shelf.get(p.shelf_id) != p.cabinet_id):
                vals = {"shelf_id": None, "compartment_id": None}
            elif p.compartment_id is not None and (p.shelf_id is None or comp.get(p.compartment_id) != p.shelf_id):
                vals = {"compartment_id": None}
            if vals:
                conn.execute(update(P).where(P.c.id == p.id).values(**vals)); n += 1
        if n:
            yapilan.append(f"{n} ürünün tutarsız konumu düzeltildi")

        # Geçersiz değerler
        n = 0
        for p in conn.execute(select(P)).mappings().all():
            vals = {}
            if not _norm_spaces(p["name"]):
                vals["name"] = f"(adsız ürün #{p['id']})"
            if p["category"] not in CATEGORY_VALUES:
                vals["category"] = "Genel / Dayanıklı Malzeme"
            if p["status"] not in STATUS_VALUES:
                vals["status"] = parse_status(p["status"])
            for col, default in (("current_stock", 0), ("critical_stock", 5), ("ideal_stock", 10)):
                if p[col] is None:
                    vals[col] = default
                elif p[col] < 0:
                    vals[col] = 0
            if vals:
                conn.execute(update(P).where(P.c.id == p["id"]).values(**vals)); n += 1
        for u in conn.execute(select(U)).mappings().all():
            vals = {}
            if u["role"] not in ROLE_VALUES:
                vals["role"] = "user"
            if u["is_active"] is None:
                vals["is_active"] = True
            if vals:
                conn.execute(update(U).where(U.c.id == u["id"]).values(**vals)); n += 1
        if n:
            yapilan.append(f"{n} kayıtta geçersiz/eksik değer düzeltildi")

        # Tekrar eden dersler (boşluk düzeltmesinden önce; benzersizlik kuralı nedeniyle)
        C = T["courses"]
        groups = _course_groups(conn.execute(select(C)).mappings().all())
        for g in [g for g in groups if len(g) > 1]:
            keep = _canonical_course(g)
            existing_pairs = {pid for (pid,) in conn.execute(select(product_courses.c.product_id)
                                                             .where(product_courses.c.course_id == keep["id"])).all()}
            for c in g:
                if c["id"] == keep["id"]:
                    continue
                for (pid,) in conn.execute(select(product_courses.c.product_id).where(product_courses.c.course_id == c["id"])).all():
                    if pid not in existing_pairs:
                        conn.execute(product_courses.insert().values(product_id=pid, course_id=keep["id"]))
                        existing_pairs.add(pid)
                conn.execute(delete(product_courses).where(product_courses.c.course_id == c["id"]))
                conn.execute(delete(C).where(C.c.id == c["id"]))
                yapilan.append(f"Ders '{c['name']}' → '{keep['name']}' ile birleştirildi")

        # Fazla boşluklar ve uzun metinler
        n_space = n_long = 0
        for t in Base.metadata.sorted_tables:
            str_cols = [c for c in t.columns if isinstance(c.type, String)]
            pk = list(t.primary_key.columns)
            if not str_cols or not pk:
                continue
            for row in conn.execute(select(*pk, *str_cols)).all():
                vals = {}
                for i, c in enumerate(str_cols, len(pk)):
                    v = row[i]
                    if not isinstance(v, str):
                        continue
                    nv = _norm_spaces(v) if c.name in ("name", "full_name") else v
                    length = getattr(c.type, "length", None)
                    if length and len(nv) > length:
                        nv = nv[:length]
                        n_long += 1
                    if nv != v:
                        vals[c.name] = nv
                        if c.name in ("name", "full_name"):
                            n_space += 1
                if vals:
                    where = [pkc == row[i] for i, pkc in enumerate(pk)]
                    conn.execute(update(t).where(*where).values(**vals))
        if n_space:
            yapilan.append(f"{n_space} addaki fazla boşluk temizlendi")
        if n_long:
            yapilan.append(f"{n_long} uzun metin sütun sınırına kısaltıldı")

        # Gönderim durumları
        n = 0
        items_by_ship = defaultdict(list)
        for it in conn.execute(select(SI)).mappings().all():
            items_by_ship[it["shipment_id"]].append(it)
            st = _item_status(it["expected_quantity"], it["actual_quantity"])
            if it["status"] != st:
                conn.execute(update(SI).where(SI.c.id == it["id"]).values(status=st)); n += 1
        for s in conn.execute(select(S)).mappings().all():
            vals = {}
            its = items_by_ship.get(s["id"], [])
            if its:
                expected = "pending" if any(i["actual_quantity"] is None for i in its) else "checked"
                if s["status"] != expected:
                    vals["status"] = expected
            if s["outgoing_reason"] == "":
                vals["outgoing_reason"] = None
            if vals:
                conn.execute(update(S).where(S.c.id == s["id"]).values(**vals)); n += 1
        if n:
            yapilan.append(f"{n} gönderim durum bilgisi güncellendi")

        # Varsayılan/zayıf şifreli hesaplar → pasif (son aktif yönetici hariç)
        users = conn.execute(select(U)).mappings().all()
        active_admins = {u["id"] for u in users if u["role"] == "admin" and u["is_active"] in (True, 1)}
        for u in users:
            if u["is_active"] not in (True, 1):
                continue
            weak = weak_password_of(u["email"], u["hashed_password"], sifre_listesi)
            if not weak:
                continue
            if u["id"] in active_admins and len(active_admins) == 1:
                yapilan.append(f"UYARI: {u['email']} varsayılan şifreli ama tek aktif yönetici; pasif yapılmadı. "
                               "Hemen giriş yapıp şifresini değiştirin.")
                continue
            conn.execute(update(U).where(U.c.id == u["id"]).values(is_active=False))
            active_admins.discard(u["id"])
            yapilan.append(f"{u['email']} hesabı (şifresi '{weak}') pasif yapıldı")

        if kopya_aktarim:  # birleştirmeden önce: önce fazla kopyalar gitsin
            yapilan += _remove_copied_imports(conn)
        if tekrar_urun:
            yapilan += _merge_duplicate_products(conn, stok_kurali)
        if bos_gonderim:
            for s in conn.execute(select(S.c.id, S.c.name)).all():
                if not items_by_ship.get(s.id):
                    conn.execute(delete(S).where(S.c.id == s.id))
                    yapilan.append(f"Boş gönderim silindi: #{s.id} '{s.name}'")
    return yapilan


def _delete_products(conn, ids) -> None:
    P, L, SI = Product.__table__, StockLog.__table__, ShipmentItem.__table__
    ids = list(ids)
    for start in range(0, len(ids), 500):  # SQL Server parametre sınırı (2100) için parça parça
        chunk = ids[start:start + 500]
        conn.execute(delete(product_courses).where(product_courses.c.product_id.in_(chunk)))
        conn.execute(delete(L).where(L.c.product_id.in_(chunk)))
        conn.execute(delete(SI).where(SI.c.product_id.in_(chunk)))
        conn.execute(delete(P).where(P.c.id.in_(chunk)))


def _remove_copied_imports(conn) -> List[str]:
    """Aynı Excel'in fazla kopyalarını siler. Kullanılmış (stok hareketi/gönderimi olan) bir kopya asla silinmez."""
    P, L, SI, W = Product.__table__, StockLog.__table__, ShipmentItem.__table__, Warehouse.__table__
    prods = conn.execute(select(P)).mappings().all()
    activity = Counter(r[0] for r in conn.execute(select(L.c.product_id)).all())
    activity.update(r[0] for r in conn.execute(select(SI.c.product_id)).all())
    names = {r[0]: r[1] for r in conn.execute(select(W.c.id, W.c.name)).all()}
    label = lambda w: f"'{names.get(w, '?')}'" if w is not None else "'Depo atanmamış'"  # noqa: E731
    by_wh, clusters = _copy_clusters(prods)
    out = []
    for members in clusters:
        keep = _copy_to_keep(members, by_wh, activity)
        for w in members:
            if w == keep:
                continue
            used = sum(activity[p["id"]] for p in by_wh[w])
            if used:
                out.append(f"UYARI: {label(w)} kopyasında {used} stok hareketi/gönderim var; silinmedi, elle kontrol edin.")
                continue
            _delete_products(conn, [p["id"] for p in by_wh[w]])
            out.append(f"{label(w)} içindeki {len(by_wh[w])} kopya ürün silindi ({label(keep)} tutuldu)")
    return out


def _merge_duplicate_products(conn, stok_kurali: str) -> List[str]:
    P, L, SI = Product.__table__, StockLog.__table__, ShipmentItem.__table__
    prods = conn.execute(select(P)).mappings().all()
    activity = Counter(r[0] for r in conn.execute(select(L.c.product_id)).all())
    activity.update(r[0] for r in conn.execute(select(SI.c.product_id)).all())
    out = []
    for (_, _), group in _product_dup_groups(prods).items():
        keep = max(group, key=lambda p: (activity[p["id"]], -p["id"]))
        others = [p for p in group if p["id"] != keep["id"]]
        stocks = [p["current_stock"] or 0 for p in group]
        new_stock = sum(stocks) if stok_kurali == "topla" else max(stocks)
        vals = {
            "current_stock": new_stock,
            "critical_stock": max(p["critical_stock"] or 0 for p in group),
            "ideal_stock": max(p["ideal_stock"] or 0 for p in group),
        }
        if all((p["description"] or "").startswith("Kaynak: ") for p in group):
            sources = list(dict.fromkeys(p["description"][8:] for p in group))
            vals["description"] = ("Kaynak: " + ", ".join(sources))[:4000]
        for col in ("image_url", "cabinet_id", "shelf_id", "compartment_id"):
            if keep[col] is None:
                donor = next((p for p in others if p[col] is not None), None)
                if donor is not None:
                    if col == "image_url":
                        vals[col] = donor[col]
                    elif keep["cabinet_id"] is None:  # konumu tek parça halinde al
                        vals.update(cabinet_id=donor["cabinet_id"], shelf_id=donor["shelf_id"],
                                    compartment_id=donor["compartment_id"])
        conn.execute(update(P).where(P.c.id == keep["id"]).values(**vals))
        keep_courses = {r[0] for r in conn.execute(select(product_courses.c.course_id)
                                                   .where(product_courses.c.product_id == keep["id"])).all()}
        other_ids = [p["id"] for p in others]
        for (cid,) in conn.execute(select(product_courses.c.course_id).where(product_courses.c.product_id.in_(other_ids))).all():
            if cid not in keep_courses:
                conn.execute(product_courses.insert().values(product_id=keep["id"], course_id=cid))
                keep_courses.add(cid)
        conn.execute(delete(product_courses).where(product_courses.c.product_id.in_(other_ids)))
        conn.execute(update(L).where(L.c.product_id.in_(other_ids)).values(product_id=keep["id"]))
        conn.execute(update(SI).where(SI.c.product_id.in_(other_ids)).values(product_id=keep["id"]))
        if new_stock != (keep["current_stock"] or 0):
            conn.execute(L.insert().values(
                product_id=keep["id"], user_id=None, action="set", quantity_change=new_stock - (keep["current_stock"] or 0),
                previous_value=str(keep["current_stock"]), new_value=str(new_stock),
                note=f"Tekrar eden kayıtlar birleştirildi (#{', #'.join(map(str, other_ids))})",
                created_at=datetime.utcnow()))
        conn.execute(delete(P).where(P.c.id.in_(other_ids)))
        out.append(f"'{keep['name']}': #{keep['id']} kaldı, {len(others)} tekrar birleştirildi (stok {new_stock})")
    if out:
        out.insert(0, f"{len(out)} tekrar eden ürün grubu birleştirildi")
    return out


# ---------------------------------------------------------------------------
# Yedek ve komut satırı
# ---------------------------------------------------------------------------
def yedek_al(engine, etiket: str = "kontrol_oncesi") -> str:
    from yedekleme import dump
    klasor = os.getenv("YEDEK_KLASORU") or os.path.join(BACKEND_DIR, "yedekler")
    os.makedirs(klasor, exist_ok=True)
    yol = os.path.join(klasor, f"{etiket}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(dump(engine), f, ensure_ascii=False)
    return yol


def rapor_yazdir(bulgular: List[Bulgu]) -> None:
    renk = {"KRİTİK": "!!", "UYARI": " !", "BİLGİ": "  "}
    for b in bulgular:
        print(f"\n[{renk[b.seviye]} {b.seviye}] {b.baslik}" + (f" ({b.adet})" if b.adet else ""))
        for d in b.detay[:15]:
            print(f"      - {d}")
        if len(b.detay) > 15:
            print(f"      ... ve {len(b.detay) - 15} tane daha")
        if b.duzeltme:
            print(f"      → --duzelt ile: {b.duzeltme}")
        if b.oneri:
            print(f"      → Öneri: {b.oneri}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Deneyap Depo veritabanı sağlık kontrolü")
    ap.add_argument("--url", help="Veritabanı adresi (varsayılan: .env ayarı)")
    ap.add_argument("--duzelt", action="store_true", help="Güvenli düzeltmeleri uygula (önce yedek alınır)")
    ap.add_argument("--tekrar-eden-urunleri-birlestir", action="store_true")
    ap.add_argument("--stok", choices=["max", "topla"], default="max",
                    help="Birleştirmede stok: en büyük değer (max) veya toplam (topla)")
    ap.add_argument("--bos-gonderimleri-sil", action="store_true")
    ap.add_argument("--kopya-aktarimlari-sil", action="store_true",
                    help="Aynı Excel'in birden fazla yere aktarılmış kopyalarından kullanılmamış olanları sil")
    ap.add_argument("--sifre-kontrolu-yok", action="store_true", help="Zayıf şifre taramasını atla (hızlı)")
    ap.add_argument("--json", action="store_true", help="Sonucu JSON olarak yazdır")
    ap.add_argument("--yedeksiz", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    if args.url:
        engine = create_engine(args.url)
    else:
        from database import engine, aktif_baglanti
        print("Veritabanı:", aktif_baglanti())

    if args.duzelt:
        if not args.yedeksiz:
            print("Yedek alınıyor:", yedek_al(engine))
        for y in duzelt(engine, args.tekrar_eden_urunleri_birlestir, args.bos_gonderimleri_sil, args.stok,
                        kopya_aktarim=args.kopya_aktarimlari_sil):
            print("  ✓", y)
        print("\nDüzeltme sonrası durum:")
    bulgular = kontrol_et(engine, sifre_kontrol=not args.sifre_kontrolu_yok)
    if args.json:
        print(json.dumps([asdict(b) for b in bulgular], ensure_ascii=False, indent=1))
    else:
        rapor_yazdir(bulgular)
        kritik = sum(1 for b in bulgular if b.seviye == "KRİTİK")
        print(f"\nSonuç: {kritik} kritik, {sum(1 for b in bulgular if b.seviye == 'UYARI')} uyarı.")
    return 1 if any(b.seviye == "KRİTİK" for b in bulgular) else 0


if __name__ == "__main__":
    sys.exit(main())
