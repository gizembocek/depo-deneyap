"""
SQL Server uyumluluk testleri.

Bu ortamda gerçek SQL Server yoksa bile:
  - SQL Server için üretilen şema (DDL) derlenip kurallara uygunluğu denetlenir,
  - Türkçe arama dönüşümünün T-SQL karşılığı Python ile birebir karşılaştırılır,
  - Uygulamanın ana sorguları SQL Server diyalektinde derlenir,
  - SQL Server'ın "zincirleme silme yok" (NO ACTION) kuralı SQLite'ta taklit edilerek
    tüm silme senaryoları çalıştırılır.
Gerçek SQL Server'da tam test için: SQL_Server_Test.bat (mssql_kurulum.py --test).
"""
import os
import re
import sqlite3
import subprocess
import sys

import pytest
from sqlalchemy import Unicode, create_mock_engine, literal, select
from sqlalchemy.dialects import mssql

import database
from database import Base, _FOLD_PAIRS, describe_db_error, folded_for, mssql_connection_string, tr_fold, tr_ordered_for
from models import Product, StockLog

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _mssql_ddl() -> str:
    out = []
    saved = [(fk, fk.ondelete, fk.constraint.ondelete) for t in Base.metadata.tables.values() for fk in t.foreign_keys]
    eng = create_mock_engine("mssql+pyodbc://", lambda sql, *a, **k: out.append(str(sql.compile(dialect=eng.dialect))))
    try:
        Base.metadata.create_all(eng, checkfirst=False)
    finally:  # SQL Server derlemesi ortak şema nesnesini değiştirir; diğer testler için geri al
        for fk, a, b in saved:
            fk.ondelete, fk.constraint.ondelete = a, b
    return "\n".join(out)


def test_sql_server_semasinda_zincirleme_silme_yok():
    """SQL Server 'multiple cascade paths' (hata 1785) nedeniyle ON DELETE kuralı içeren şemayı reddeder."""
    ddl = _mssql_ddl()
    assert ddl.count("CREATE TABLE") == len(Base.metadata.tables) == 13
    assert "ON DELETE" not in ddl
    assert "NVARCHAR(max)" in ddl and "DATETIME2(6)" in ddl
    assert "[key] NVARCHAR(100)" in ddl  # ayrılmış kelime tırnaklanıyor


def test_sqlite_semasi_zincirleme_silmeyi_korur():
    if os.getenv("DB_FK_NO_ACTION") == "1":
        pytest.skip("NO ACTION emülasyon modunda çalışıyor")
    code = ("import os; os.environ['DATABASE_URL']='sqlite://'; import models; from database import Base;"
            "from sqlalchemy import create_mock_engine; o=[];"
            "e=create_mock_engine('sqlite://', lambda s,*a,**k: o.append(str(s.compile(dialect=e.dialect))));"
            "Base.metadata.create_all(e, checkfirst=False); print('\\n'.join(o).count('ON DELETE CASCADE'))")
    r = subprocess.run([sys.executable, "-c", code], cwd=BACKEND_DIR, capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       env={k: v for k, v in os.environ.items() if k != "DB_FK_NO_ACTION"})
    assert int(r.stdout.strip()) >= 8, r.stderr


@pytest.mark.parametrize("sample", [
    "Işıklı Büyüteç", "IŞIK", "ışık", "İstanbul", "ÇĞÖŞÜ çğöşü", "Âlet Îmalat Ûmit", "Arduino UNO R3", "%50_indirim",
])
def test_sql_server_turkce_arama_donusumu_python_ile_ayni(sample):
    # T-SQL: LOWER(REPLACE(...REPLACE(x COLLATE BIN2, a, b)...)) -> Python'da aynı adımlar
    s = sample
    for a, b in _FOLD_PAIRS:
        s = s.replace(a, b)
    assert s.lower() == tr_fold(sample)


def test_sql_server_sorgulari_derlenir():
    q = (select(Product)
         .where(folded_for("mssql", Product.name).contains(tr_fold("ışık"), autoescape=True))
         .order_by(tr_ordered_for("mssql", Product.name).asc(), Product.id.asc())
         .offset(48).limit(48))
    sql = str(q.compile(dialect=mssql.dialect()))
    assert "COLLATE Latin1_General_100_BIN2" in sql
    assert "COLLATE Turkish_CI_AS" in sql
    assert "ESCAPE '/'" in sql
    logs = select(StockLog).order_by(StockLog.created_at.desc()).limit(100)
    assert "TOP" in str(logs.compile(dialect=mssql.dialect()))
    e = folded_for("mssql", literal("Işık", Unicode))
    assert str(select(e).compile(dialect=mssql.dialect(), compile_kwargs={"literal_binds": True})).count("replace(") == len(_FOLD_PAIRS)


def test_baglanti_metni():
    cs = mssql_connection_string(server=r".\SQLEXPRESS", database="deneyap_depo", driver="ODBC Driver 18 for SQL Server")
    assert cs == (r"DRIVER={ODBC Driver 18 for SQL Server};SERVER=.\SQLEXPRESS;DATABASE=deneyap_depo;"
                  "Encrypt=yes;TrustServerCertificate=yes;Trusted_Connection=yes")
    cs = mssql_connection_string(server="localhost", database="d", driver="SQL Server", windows_auth=False,
                                 user="sa", password="a;b}c", port="1433")
    assert "SERVER=localhost,1433" in cs and "Encrypt" not in cs and "PWD={a;b}}c}" in cs


@pytest.mark.parametrize("message, expected", [
    ("('08001', '[08001] [Microsoft][ODBC Driver 18 for SQL Server]Named Pipes Provider: Could not open a connection to SQL Server [2].')", "ulaşılamadı"),
    ("('HYT00', '[HYT00] [Microsoft][ODBC Driver 18 for SQL Server]Login timeout expired (0) (SQLDriverConnect)')", "ulaşılamadı"),
    ("('28000', \"[28000] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]Login failed for user 'PC\\\\gizem'. (18456)\")", "oturum açma reddedildi"),
    ("('42000', '[42000] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]Cannot open database \"deneyap_depo\" requested by the login. The login failed. (4060)')", "Veritabanı açılamadı"),
    ("('IM002', '[IM002] [Microsoft][ODBC Driver Manager] Data source name not found and no default driver specified')", "ODBC sürücüsü bulunamadı"),
    ("('08001', '[08001] [Microsoft][ODBC Driver 18 for SQL Server]SSL Provider: The certificate chain was issued by an authority that is not trusted.')", "sertifika"),
])
def test_baglanti_hatalari_turkce_aciklanir(message, expected):
    assert expected.lower() in describe_db_error(Exception(message)).lower()


@pytest.mark.skipif(os.getenv("DB_FK_NO_ACTION") == "1" or os.getenv("TEST_DATABASE_URL") is not None,
                    reason="Zaten emülasyon modunda veya gerçek sunucuda")
def test_sql_server_silme_kurallari_emulasyonu():
    """Tüm silme/güncelleme senaryoları, SQL Server'daki gibi zincirleme kuralı OLMAYAN yabancı
    anahtarlarla (SQLite + foreign_keys=ON) yeniden çalıştırılır. Bir işlem veritabanının otomatik
    silmesine güveniyorsa burada yabancı anahtar hatası verir."""
    env = dict(os.environ, DB_FK_NO_ACTION="1")
    env.pop("DATABASE_URL", None)
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-x",
                        "tests/test_products.py", "tests/test_shipments.py", "tests/test_warehouses.py",
                        "tests/test_auth.py", "tests/test_veritabani_kontrol.py"],
                       cwd=BACKEND_DIR, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=900)
    assert r.returncode == 0, r.stdout[-4000:] + r.stderr[-2000:]


def test_sql_server_like_koseli_parantez_kacisi():
    """SQL Server'da LIKE içinde [ ] karakter aralığı demektir; kullanıcının yazdığı [ düz metin aranmalı."""
    from sqlalchemy import column
    from database import contains_text
    expr = contains_text(column("name"), "kablo [10 adet] %50_", dialect="mssql")
    params = expr.compile(dialect=mssql.dialect()).params
    assert list(params.values()) == ["%kablo /[10 adet] /%50/_%"]
    assert "ESCAPE '/'" in str(expr.compile(dialect=mssql.dialect()))
    sqlite_params = contains_text(column("name"), "a[b]", dialect="sqlite").compile().params
    assert list(sqlite_params.values()) == ["%a[b]%"]


def test_koseli_parantezli_urun_aranir(client, admin, product):
    product("Jumper Kablo [40 adet]")
    product("Kablo")
    names = [p["name"] for p in client.get("/api/products/", params={"search": "[40"}, headers=admin).json()]
    assert names == ["Jumper Kablo [40 adet]"]


def test_bos_sql_server_acilinca_tasinmamis_sqlite_verisi_uyarisi(client, tmp_path, monkeypatch):
    """SQL Server'a geçildi ama veriler taşınmadıysa ilk kurulum ekranı bunu söylemeli
    (yoksa kullanıcı boş veritabanında yeni kurulum yapıp eski verilerini 'kaybettiğini' sanar)."""
    import database
    from eski_veri import TOPLAM_URUN, eski_veritabani_olustur

    eski = tmp_path / "deneyap_depo.db"
    eski_veritabani_olustur(eski)
    monkeypatch.setenv("SQLITE_PATH", str(eski))
    monkeypatch.setattr(database, "IS_SQLITE", False)  # uygulama SQL Server kullanıyormuş gibi
    status = client.get("/api/auth/setup-status").json()
    assert status["needs_setup"] is True
    assert status["tasinmamis_veri"] == {"dosya": "deneyap_depo.db", "urun": TOPLAM_URUN, "kullanici": 3}
    # Dosya salt okunur açıldı: değişmedi
    assert sqlite3.connect(eski).execute("select count(*) from products").fetchone()[0] == TOPLAM_URUN

    # Kurulum yapıldıktan sonra (veya uygulama zaten SQLite kullanıyorsa) uyarı yok
    monkeypatch.setattr(database, "IS_SQLITE", True)
    assert client.get("/api/auth/setup-status").json()["tasinmamis_veri"] is None
    monkeypatch.setattr(database, "IS_SQLITE", False)
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "yok.db"))
    assert client.get("/api/auth/setup-status").json()["tasinmamis_veri"] is None
    assert not (tmp_path / "yok.db").exists()  # olmayan dosya oluşturulmamalı


def test_kaynakta_sql_servera_uymayan_bool_karsilastirma_yok():
    """`.is_(True)` SQLite'ta çalışır ama SQL Server'da geçersiz "IS 1" üretir (gerçek kurulumda
    sihirbazın 4b adımı bu yüzden çöktü). Bool sütunlar `== True` ile karşılaştırılmalı."""
    desen = re.compile(r"\.(is_|is_not|isnot)\((True|False|1|0)\)")
    bulunan = []
    for kok, _, dosyalar in os.walk(BACKEND_DIR):
        if any(p in kok for p in ("venv", "__pycache__", "alembic")):
            continue
        for ad in dosyalar:
            if ad.endswith(".py") and ad != "test_mssql_uyum.py":
                yol = os.path.join(kok, ad)
                with open(yol, encoding="utf-8") as f:
                    for no, satir in enumerate(f, 1):
                        if desen.search(satir.split("#", 1)[0]):  # yorum satırlarındaki açıklamalar sayılmaz
                            bulunan.append(f"{os.path.relpath(yol, BACKEND_DIR)}:{no}: {satir.strip()}")
    assert not bulunan, "\n".join(bulunan)


def test_aktif_yonetici_sorgulari_sql_server_icin_dogru_derlenir():
    from sqlalchemy import select
    from models import User
    U = User.__table__
    sql = str(select(U.c.email).where(U.c.role == "admin", U.c.is_active == True)  # noqa: E712
              .compile(dialect=mssql.dialect()))
    assert "is_active = 1" in sql and " IS 1" not in sql
