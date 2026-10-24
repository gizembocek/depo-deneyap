"""
Bu bilgisayardaki tüm Deneyap Depo veritabanlarını bulur ve karşılaştırır.
Veritabanlarında HİÇBİR ŞEYİ DEĞİŞTİRMEZ (yalnızca okur; kapalı bir SQL Server hizmetini yalnızca başlatır). Veritabanlari_Bul.bat bu dosyayı çalıştırır.

Bakılan yerler:
  - Kurulu tüm SQL Server örnekleri (MSSQLSERVER, SQLEXPRESS, MSSQLSERVER01 ...) ve LocalDB
      * içinde Deneyap tabloları (products, users ...) olan veritabanları
      * SQL Server'ın aldığı yedekler (.bak) ve yedek geçmişi
      * veri klasöründe duran ama SQL Server'a bağlı olmayan .mdf dosyaları
  - backend/deneyap_depo.db ve backend/yedekler/*.db (SQLite)

Hangi veritabanının en güncel olduğunu anlamak için "son işlem" tarihlerine bakın.
"""
import glob
import ntpath  # SQL Server dosya yolları (C:\\...) her sistemde doğru ayrılsın
import os
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

TABLOLAR = ["products", "users", "warehouses", "courses", "shipments", "stock_logs"]
# Kullanıcının yaptığı işlemlerin tarihleri (veri onarımı updated_at'i değiştirebildiği için ona bakılmaz)
TARIHLER = [("Son stok hareketi", "stock_logs", "created_at"),
            ("Son eklenen ürün", "products", "created_at"),
            ("Son gönderim", "shipments", "created_at"),
            ("Son eklenen kullanıcı", "users", "created_at")]


def _q(name: str) -> str:
    return "[" + name.replace("]", "]]") + "]"


def _tarih(v) -> str:
    return str(v)[:16] if v else "-"


# ---------------------------------------------------------------------------
# Özet çıkarma (SQL Server ve SQLite için aynı biçim)
# ---------------------------------------------------------------------------
def _ozet(sorgu) -> dict:
    """sorgu(sql) -> tek değer. Eksik tablo/sütun olursa o bilgi '-' kalır."""
    o = {"sayilar": {}, "tarihler": {}, "farkli_urun": None, "kullanicilar": []}
    for t in TABLOLAR:
        try:
            o["sayilar"][t] = sorgu(f"SELECT COUNT(*) FROM {{{t}}}")
        except Exception:
            o["sayilar"][t] = None
    try:
        o["farkli_urun"] = sorgu("SELECT COUNT(DISTINCT name) FROM {products}")
    except Exception:
        pass
    for etiket, t, c in TARIHLER:
        try:
            o["tarihler"][etiket] = sorgu(f"SELECT MAX({c}) FROM {{{t}}}")
        except Exception:
            o["tarihler"][etiket] = None
    return o


def sqlite_ozeti(path: str) -> dict:
    con = sqlite3.connect(Path(path).absolute().as_uri() + "?mode=ro", uri=True, timeout=5)
    try:
        tablolar = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "products" not in tablolar:
            return None

        def sorgu(sql):
            return con.execute(sql.format(**{t: t for t in TABLOLAR})).fetchone()[0]
        o = _ozet(sorgu)
        try:
            o["kullanicilar"] = [(e, r, bool(a)) for e, r, a in con.execute("SELECT email, role, is_active FROM users")]
        except Exception:
            pass
        return o
    finally:
        con.close()


def mssql_ozeti(cur, db: str) -> dict:
    q = _q(db)

    def sorgu(sql):
        return cur.execute(sql.format(**{t: f"{q}.dbo.{t}" for t in TABLOLAR})).fetchone()[0]
    o = _ozet(sorgu)
    try:
        o["kullanicilar"] = [(r[0], r[1], bool(r[2])) for r in
                             cur.execute(f"SELECT email, role, is_active FROM {q}.dbo.users").fetchall()]
    except Exception:
        pass
    try:
        o["boyut_mb"] = cur.execute(f"SELECT CAST(SUM(CAST(size AS BIGINT)) * 8 / 1024 AS INT) FROM {q}.sys.database_files").fetchone()[0]
    except Exception:
        pass
    return o


def ozet_yazdir(baslik: str, o: dict) -> None:
    s = o["sayilar"]

    def n(k):
        return "-" if s.get(k) is None else str(s[k])
    print(f"\n  >> {baslik}")
    print(f"       Ürün: {n('products')}" + (f" (farklı ad: {o['farkli_urun']})" if o.get("farkli_urun") is not None else "")
          + f" | Kullanıcı: {n('users')} | Depo: {n('warehouses')} | Ders: {n('courses')}"
          + f" | Gönderim: {n('shipments')} | Stok hareketi: {n('stock_logs')}"
          + (f" | Boyut: {o['boyut_mb']} MB" if o.get("boyut_mb") is not None else ""))
    print("       " + " | ".join(f"{k}: {_tarih(v)}" for k, v in o["tarihler"].items()))
    if o["kullanicilar"]:
        print("       Hesaplar: " + ", ".join(f"{e}{'' if a else ' (pasif)'}" for e, _, a in o["kullanicilar"][:8])
              + (" ..." if len(o["kullanicilar"]) > 8 else ""))


def son_islem(o: dict) -> str:
    return max((str(v) for v in o["tarihler"].values() if v), default="")


# ---------------------------------------------------------------------------
# SQL Server
# ---------------------------------------------------------------------------
def sistem_dosyasi(ad: str) -> bool:
    """SQL Server'ın kendi şablon dosyaları (ör. model_msdbdata.mdf) veritabanı olarak bağlı değildir; bunlar normaldir."""
    ad = ad.lower()
    return ad.startswith("model_") or ad.startswith("mssqlsystemresource")


def sunucu_tara(cur, sunucu: str, bulunanlar: list) -> None:
    ed, ver, yedek_yolu, veri_yolu = cur.execute(
        "SELECT CAST(SERVERPROPERTY('Edition') AS NVARCHAR(128)), CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(50)), "
        "CAST(SERVERPROPERTY('InstanceDefaultBackupPath') AS NVARCHAR(400)), "
        "CAST(SERVERPROPERTY('InstanceDefaultDataPath') AS NVARCHAR(400))").fetchone()
    print(f"    Sürüm: {ed} ({ver})")
    if "evaluation" in str(ed).lower():
        print("    [!] DENEME sürümü: kurulumdan 180 gün sonra çalışmayı durdurur.")
    dbs = cur.execute("SELECT name, state_desc, create_date FROM sys.databases WHERE database_id > 4 ORDER BY name").fetchall()
    if not dbs:
        print("    Kullanıcı veritabanı yok.")
    for name, state, created in dbs:
        if str(state).upper() != "ONLINE":
            print(f"    - {name}: {state} (açılamadı)")
            continue
        try:
            erisim = cur.execute("SELECT HAS_DBACCESS(?)", name).fetchone()[0]
            deneyap = erisim and cur.execute("SELECT OBJECT_ID(?)", f"{_q(name)}.dbo.products").fetchone()[0]
        except Exception:
            erisim, deneyap = None, None
        if not erisim:
            print(f"    - {name}: erişim izni yok")
        elif not deneyap:
            print(f"    - {name}: Deneyap veritabanı değil (oluşturulma {_tarih(created)})")
        else:
            o = mssql_ozeti(cur, name)
            ozet_yazdir(f"SQL Server {sunucu} / {name}  (oluşturulma {_tarih(created)})", o)
            bulunanlar.append((f"SQL Server {sunucu} / {name}", o))

    try:
        gecmis = cur.execute(
            "SELECT TOP 10 bs.database_name, bs.backup_finish_date, bmf.physical_device_name "
            "FROM msdb.dbo.backupset bs JOIN msdb.dbo.backupmediafamily bmf ON bs.media_set_id = bmf.media_set_id "
            "ORDER BY bs.backup_finish_date DESC").fetchall()
        if gecmis:
            print("    Yedek geçmişi (son 10):")
            for db, tarih, dosya in gecmis:
                print(f"      {_tarih(tarih)}  {db:<20} {dosya}")
    except Exception:
        pass

    def dosyalar(klasor, uzanti):
        try:
            rows = cur.execute("EXEC master.sys.xp_dirtree ?, 1, 1", klasor).fetchall()
            return [r[0] for r in rows if len(r) > 2 and r[2] == 1 and str(r[0]).lower().endswith(uzanti)]
        except Exception:
            return []
    if yedek_yolu:
        bak = dosyalar(yedek_yolu, ".bak")
        if bak:
            print(f"    Yedek klasöründeki .bak dosyaları ({yedek_yolu}): " + ", ".join(bak))
    if veri_yolu:
        try:
            bagli = {ntpath.basename(str(r[0])).lower() for r in cur.execute("SELECT physical_name FROM sys.master_files").fetchall()}
        except Exception:
            bagli = set()
        bagsiz = [f for f in dosyalar(veri_yolu, ".mdf") if f.lower() not in bagli and not sistem_dosyasi(f)]
        if bagsiz:
            print(f"    [!] Veri klasöründe SQL Server'a bağlı OLMAYAN veritabanı dosyaları ({veri_yolu}): " + ", ".join(bagsiz))


def localdb_var() -> bool:
    """LocalDB'nin varsayılan örneği daha önce oluşturulmuş mu? (Yoksa bağlanıp yenisini oluşturmayalım.)"""
    import subprocess
    try:
        r = subprocess.run(["sqllocaldb", "info"], capture_output=True, text=True, timeout=30)
        return "mssqllocaldb" in r.stdout.lower()
    except Exception:
        return False


def sql_server_tara(bulunanlar: list) -> None:
    try:
        import pyodbc
    except ImportError:
        print("  'pyodbc' kurulu değil; SQL Server'a bakılamadı.")
        return
    from mssql_kurulum import (candidate_servers, choose_driver, connection_string, discover_instances,
                               service_status, start_service)
    driver = choose_driver(pyodbc.drivers())
    if not driver:
        print("  SQL Server ODBC sürücüsü yok; SQL Server'a bakılamadı.")
        return
    ornekler = discover_instances()
    hedefler = [(ad, svc) for ad, svc in ornekler] + ([("LocalDB", None)] if localdb_var() else [])
    if not hedefler:
        print("\n  Bu bilgisayarda kurulu SQL Server bulunamadı.")
    for ad, svc in hedefler:
        print(f"\n[SQL Server örneği: {ad}]")
        if svc:
            durum = service_status(svc)
            if durum and durum.lower() != "running":
                print(f"    Hizmet çalışmıyor ({durum}); başlatılıyor...")
                if not start_service(svc):
                    print("    Başlatılamadı. Bu dosyayı sağ tıklayıp 'Yönetici olarak çalıştır' ile açın.")
                    continue
            adresler = [a for a in candidate_servers([(ad, svc)]) if not a.lower().startswith("(localdb)")]
        else:
            adresler = [r"(localdb)\MSSQLLocalDB"]
        conn = None
        for adres in adresler:
            try:
                conn = pyodbc.connect(connection_string(adres, "master", driver), timeout=10, autocommit=True)
                break
            except Exception as exc:
                son_hata = exc
        if not conn:
            print(f"    Bağlanılamadı: {str(son_hata)[:200]}")
            continue
        print(f"    Adres: {adres}")
        try:
            sunucu_tara(conn.cursor(), adres, bulunanlar)
        except Exception as exc:
            print(f"    Okunamadı: {str(exc)[:200]}")
        finally:
            conn.close()


def sqlite_tara(bulunanlar: list) -> None:
    yollar = [os.path.join(BACKEND_DIR, "deneyap_depo.db")] + sorted(glob.glob(os.path.join(BACKEND_DIR, "yedekler", "*.db")))
    print("\n[SQLite dosyaları]")
    for yol in yollar:
        if not os.path.isfile(yol):
            continue
        try:
            o = sqlite_ozeti(yol)
        except Exception as exc:
            print(f"    {os.path.relpath(yol, BACKEND_DIR)}: okunamadı ({exc})")
            continue
        if o:
            ad = "SQLite " + os.path.relpath(yol, BACKEND_DIR)
            ozet_yazdir(ad, o)
            bulunanlar.append((ad, o))


def main() -> int:
    # Uygulamanın .env'deki veritabanı ayarı devreye girmesin; bu araç kendi bağlantılarını kurar.
    os.environ["DATABASE_URL"] = "sqlite://"
    print("=" * 70)
    print("  DENEYAP DEPO — Bilgisayardaki veritabanlarını bulma (veritabanlarında hiçbir şey değiştirilmez)")
    print("=" * 70)
    try:
        from dotenv import dotenv_values
        env = dotenv_values(os.path.join(BACKEND_DIR, ".env"))
        if (env.get("DB_BACKEND") or "sqlite").lower() == "mssql":
            print(f"\nUygulamanın ayarı (.env): SQL Server -> {env.get('MSSQL_HOST', 'localhost')} / {env.get('MSSQL_DB', 'deneyap_depo')}")
        else:
            print("\nUygulamanın ayarı (.env): SQLite -> backend\\deneyap_depo.db")
    except Exception:
        pass
    bulunanlar = []
    sql_server_tara(bulunanlar)
    sqlite_tara(bulunanlar)

    print("\n" + "=" * 70)
    if not bulunanlar:
        print("  Hiç Deneyap veritabanı bulunamadı.")
    else:
        print("  ÖZET (son işlem tarihine göre, en güncel en üstte):")
        for ad, o in sorted(bulunanlar, key=lambda x: son_islem(x[1]), reverse=True):
            print(f"    {_tarih(son_islem(o)):<17} {o['sayilar'].get('products')!s:>5} ürün   {ad}")
    print("  Hiçbir şey değiştirilmedi. Bu pencerenin ekran görüntüsünü alabilirsiniz.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
