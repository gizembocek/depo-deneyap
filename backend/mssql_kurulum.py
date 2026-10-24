"""
SQL Server kurulum sihirbazı (SQL_Server_Kurulum.bat bu dosyayı çalıştırır).

Yaptıkları:
  1. ODBC sürücüsünü kontrol eder.
  2. Bilgisayardaki SQL Server örneklerini (MSSQLSERVER, SQLEXPRESS...) bulur, hizmet
     kapalıysa başlatmayı dener ve çalışan bir bağlantı adresi bulur.
  3. 'deneyap_depo' veritabanını (yoksa) oluşturur ve tabloları kurar.
  4. İstenirse mevcut SQLite verilerini (backend/deneyap_depo.db) SQL Server'a taşır.
     Taşımadan önce verinin bir KOPYASI üzerinde güvenli düzeltmeler yapılır;
     SQLite dosyanız değiştirilmez.
  5. Türkçe karakter, arama ve sıralamanın SQL Server'da doğru çalıştığını sınar.
  6. backend/.env dosyasını yazar (eskisi .env.yedek_... olarak saklanır).

Kullanım (backend klasöründe):
    python mssql_kurulum.py                     # etkileşimli kurulum
    python mssql_kurulum.py --evet              # tüm sorulara "evet"
    python mssql_kurulum.py --sunucu ".\\SQLEXPRESS" --veritabani deneyap_depo
    python mssql_kurulum.py --sql-kullanici sa  # Windows yerine SQL kimlik doğrulaması
    python mssql_kurulum.py --test              # tüm otomatik testleri GEÇİCİ bir SQL Server
                                                # veritabanında çalıştırır (verilerinize dokunmaz)
"""
import argparse
import getpass
import os
import platform
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import urllib.parse
from datetime import datetime

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BACKEND_DIR)
# (Ortam değişkenleri yalnızca otomatik testlerde kullanılır)
ENV_PATH = os.getenv("DENEYAP_ENV_DOSYASI") or os.path.join(BACKEND_DIR, ".env")
SQLITE_PATH = os.getenv("DENEYAP_SQLITE_KAYNAK") or os.path.join(BACKEND_DIR, "deneyap_depo.db")
sys.path.insert(0, BACKEND_DIR)

DRIVER_PREFERENCE = [
    "ODBC Driver 18 for SQL Server",
    "ODBC Driver 17 for SQL Server",
    "ODBC Driver 13 for SQL Server",
    "SQL Server Native Client 11.0",
    "SQL Server",
]
ODBC_URL = "https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server"
TURKCE_SIRALAMA = ["Cetvel", "Çekiç", "Ihlamur", "İp", "Ok", "Ölçü Kabı", "Şerit", "Zil"]


# ---------------------------------------------------------------------------
# Ekran çıktısı
# ---------------------------------------------------------------------------
def adim(no, metin):
    print(f"\n[{no}] {metin}")


def ok(metin):
    print(f"    [OK]  {metin}")


def uyari(metin):
    print(f"    [!]   {metin}")


def hata(metin):
    print(f"    [X]   {metin}")


def bilgi(metin):
    print(f"          {metin}")


def sor(soru, varsayilan=True, evet_hepsi=False) -> bool:
    if evet_hepsi:
        print(f"    ? {soru} -> {'Evet' if varsayilan else 'Hayır'} (otomatik)")
        return varsayilan
    secenek = "[E/h]" if varsayilan else "[e/H]"
    try:
        cevap = input(f"    ? {soru} {secenek}: ").strip().lower()
    except EOFError:
        return varsayilan
    if not cevap:
        return varsayilan
    return cevap in ("e", "evet", "y", "yes")


# ---------------------------------------------------------------------------
# Yardımcılar (Windows'a özgü kısımlar dışında platformdan bağımsız, test edilebilir)
# ---------------------------------------------------------------------------
def choose_driver(drivers):
    return next((d for d in DRIVER_PREFERENCE if d in drivers), None)


def discover_instances():
    """Kayıt defterinden kurulu SQL Server örneklerini okur: [(örnek_adı, hizmet_adı), ...]"""
    if platform.system() != "Windows":
        return []
    import winreg
    found = []
    for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"SOFTWARE\Microsoft\Microsoft SQL Server\Instance Names\SQL", 0,
                                 winreg.KEY_READ | view)
        except OSError:
            continue
        i = 0
        while True:
            try:
                name, _, _ = winreg.EnumValue(key, i)
            except OSError:
                break
            service = "MSSQLSERVER" if name.upper() == "MSSQLSERVER" else f"MSSQL${name}"
            if (name, service) not in found:
                found.append((name, service))
            i += 1
    return found


def service_status(service):
    if platform.system() != "Windows":
        return None
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            f"(Get-Service -Name '{service}' -ErrorAction SilentlyContinue).Status"],
                           capture_output=True, text=True, timeout=20)
        return r.stdout.strip() or None
    except Exception:
        return None


def start_service(service) -> bool:
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", f"Start-Service -Name '{service}'"],
                           capture_output=True, text=True, timeout=90)
        return r.returncode == 0
    except Exception:
        return False


def candidate_servers(instances, computer=None):
    computer = computer or socket.gethostname()
    out = []
    for name, _ in instances:
        if name.upper() == "MSSQLSERVER":
            out += ["localhost", "(local)", ".", computer]
        else:
            out += [f".\\{name}", f"localhost\\{name}", f"{computer}\\{name}"]
    if not instances:
        out += ["localhost", ".\\SQLEXPRESS", "localhost\\SQLEXPRESS"]
    out.append("(localdb)\\MSSQLLocalDB")
    return list(dict.fromkeys(out))


def connection_string(server, database, driver, sql_user=None, sql_password=""):
    from database import mssql_connection_string
    return mssql_connection_string(server=server, database=database, driver=driver,
                                   windows_auth=not sql_user, user=sql_user or "", password=sql_password or "")


def sqlalchemy_url(conn_str: str) -> str:
    return "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(conn_str)


def explain(exc) -> str:
    from database import describe_db_error
    return describe_db_error(exc)


def read_env_lines(path=None):
    path = path or ENV_PATH
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return f.read().splitlines()


def update_env_lines(lines, updates: dict, comment_out=()):
    """Var olan .env satırlarını korur: anahtarları günceller, olmayanları ekler,
    istenenleri yorum satırına çevirir."""
    out, seen = [], set()
    for line in lines:
        stripped = line.strip()
        key = stripped.split("=", 1)[0].strip() if "=" in stripped and not stripped.startswith("#") else None
        if key in comment_out:
            out.append(f"# {line}  (SQL Server sihirbazı tarafından devre dışı bırakıldı)")
            continue
        if key in updates:
            if key not in seen:
                out.append(f"{key}={updates[key]}")
                seen.add(key)
            continue
        out.append(line)
    missing = [k for k in updates if k not in seen]
    if missing:
        if out and out[-1].strip():
            out.append("")
        out.append(f"# --- SQL Server ayarları ({datetime.now().strftime('%d.%m.%Y %H:%M')}) ---")
        out += [f"{k}={updates[k]}" for k in missing]
    return out


def write_env(updates: dict, comment_out=("DATABASE_URL", "MSSQL_PORT", "MSSQL_DRIVER"), path=None):
    path = path or ENV_PATH
    lines = read_env_lines(path)
    if os.path.exists(path):
        backup = f"{path}.yedek_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(path, backup)
        bilgi(f"Eski ayar dosyası saklandı: {os.path.basename(backup)}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(update_env_lines(lines, updates, comment_out)) + "\n")


def table_counts(engine) -> dict:
    from sqlalchemy import func, inspect, select
    from database import Base
    names = set(inspect(engine).get_table_names())
    counts = {}
    with engine.connect() as conn:
        for t in Base.metadata.sorted_tables:
            if t.name in names:
                counts[t.name] = conn.execute(select(func.count()).select_from(t)).scalar()
    return counts


def source_findings(sqlite_path) -> list:
    """Taşınacak SQLite verisinin sağlık raporu (dosyanın kopyası üzerinde, şifre taraması olmadan)."""
    from sqlalchemy import create_engine
    from veritabani_kontrol import kontrol_et
    tmpdir = tempfile.mkdtemp(prefix="deneyap_kontrol_")
    copy = os.path.join(tmpdir, "kopya.db")
    shutil.copy2(sqlite_path, copy)
    eng = create_engine(f"sqlite:///{copy}")
    try:
        return kontrol_et(eng, sifre_kontrol=False)
    finally:
        eng.dispose()
        shutil.rmtree(tmpdir, ignore_errors=True)


def migrate_sqlite(sqlite_path, target_engine, merge_duplicates=False, delete_empty_shipments=False,
                   remove_copies=False):
    """SQLite dosyasının KOPYASINI düzeltip hedef veritabanına aktarır. (kaynak, hedef) sayılarını döndürür."""
    from sqlalchemy import create_engine
    from veritabani_kontrol import duzelt
    from yedekleme import dump, restore

    tmpdir = tempfile.mkdtemp(prefix="deneyap_tasima_")
    copy = os.path.join(tmpdir, "kopya.db")
    shutil.copy2(sqlite_path, copy)
    src = create_engine(f"sqlite:///{copy}")
    try:
        for satir in duzelt(src, tekrar_urun=merge_duplicates, bos_gonderim=delete_empty_shipments,
                            kopya_aktarim=remove_copies):
            bilgi(f"düzeltme (kopyada): {satir}")
        data = dump(src)
    finally:
        src.dispose()
        shutil.rmtree(tmpdir, ignore_errors=True)
    restore(target_engine, data)
    return data["counts"], table_counts(target_engine)


def verify_database(engine) -> list:
    """Türkçe karakter saklama, arama ve sıralamayı hedef veritabanında sınar. Hata listesini döndürür."""
    from sqlalchemy import Unicode, literal, select, text
    from database import contains_text, folded_for, tr_fold, tr_ordered_for
    from models import Course

    dialect = engine.dialect.name
    problems = []
    sample = "Işıklı Büyüteç ŞĞÜİÖÇ ışığüöç"
    with engine.connect() as conn:
        if dialect == "sqlite":  # uygulamanın SQLite'a eklediği Türkçe fonksiyonlar
            conn.connection.driver_connection.create_function("tr_fold", 1, tr_fold, deterministic=True)
        trans = conn.begin()
        try:
            name = f"__test_{secrets.token_hex(4)} {sample}"
            conn.execute(Course.__table__.insert().values(name=name))
            back = conn.execute(select(Course.__table__.c.name).where(Course.__table__.c.name == name)).scalar()
            if back != name:
                problems.append(f"Türkçe karakterler bozuluyor: '{back}'")
            got = conn.execute(select(folded_for(dialect, literal(sample, Unicode)))).scalar()
            if got != tr_fold(sample):
                problems.append(f"Türkçe arama dönüşümü hatalı: '{got}' (beklenen '{tr_fold(sample)}')")
            found = conn.execute(select(Course.__table__.c.id).where(
                contains_text(folded_for(dialect, Course.__table__.c.name), tr_fold("ISIKLI buyutec"), dialect))).first()
            if not found:
                problems.append("'ISIKLI buyutec' araması 'Işıklı Büyüteç'i bulamadı")
        finally:
            trans.rollback()
        if dialect == "mssql":
            values = ", ".join(f"(N'{v}')" for v in reversed(TURKCE_SIRALAMA))
            order = conn.execute(text(f"SELECT v FROM (VALUES {values}) AS t(v) ORDER BY v COLLATE Turkish_CI_AS")).scalars().all()
            if order != TURKCE_SIRALAMA:
                problems.append(f"Türkçe sıralama hatalı: {order}")
    return problems


# ---------------------------------------------------------------------------
# Ana akış
# ---------------------------------------------------------------------------
def connect_server(args, pyodbc, driver):
    """Çalışan bir sunucu adresi bulur. (sunucu, bağlantı) döndürür."""
    if args.sunucu:
        candidates = [args.sunucu]
    else:
        instances = discover_instances()
        if instances:
            ok("Bulunan SQL Server örnekleri: " + ", ".join(n for n, _ in instances))
            for name, service in instances:
                status = service_status(service)
                if status and status.lower() != "running":
                    uyari(f"'{service}' hizmeti çalışmıyor ({status}). Başlatılıyor...")
                    if start_service(service):
                        ok(f"'{service}' başlatıldı")
                    else:
                        hata("Hizmet başlatılamadı (yönetici izni gerekebilir).")
                        bilgi("Başlat > 'Hizmetler' > 'SQL Server (...)' > sağ tık > Başlat, ya da bu dosyayı "
                              "sağ tıklayıp 'Yönetici olarak çalıştır' ile açın.")
        elif platform.system() == "Windows":
            uyari("Kayıt defterinde SQL Server örneği bulunamadı. SQL Server kurulu mu? Yaygın adresler denenecek.")
        candidates = candidate_servers(instances)

    errors = []
    en_iyi = None  # (sıra, sunucu, bağlantı) — birden fazla SQL Server kuruluysa atölyeye en uygun olan seçilir
    for server in candidates:
        cs = connection_string(server, "master", driver, args.sql_kullanici, args.sql_sifre)
        try:
            conn = pyodbc.connect(cs, timeout=8, autocommit=True)
        except Exception as exc:  # pyodbc.Error
            errors.append((server, exc))
            bilgi(f"{server:<28} -> bağlanılamadı")
            continue
        sira = 0 if args.sunucu else surum_sirasi(server, server_edition(conn))
        if en_iyi is None or sira < en_iyi[0]:
            if en_iyi:
                en_iyi[2].close()
            en_iyi = (sira, server, conn)
        else:
            conn.close()
        if sira == 0:
            break
    if en_iyi:
        return en_iyi[1], en_iyi[2]
    hata("Hiçbir adresle SQL Server'a bağlanılamadı.")
    seen = set()
    for server, exc in errors:
        msg = explain(exc)
        if msg not in seen:
            bilgi(f"- {msg}")
            seen.add(msg)
    bilgi("Ayrıntılı hata (ilk deneme): " + str(errors[0][1])[:300] if errors else "")
    return None, None


def server_edition(conn) -> str:
    try:
        return str(conn.cursor().execute("SELECT CAST(SERVERPROPERTY('Edition') AS NVARCHAR(100))").fetchone()[0] or "")
    except Exception:
        return ""


def is_evaluation(edition: str) -> bool:
    """SQL Server deneme sürümü (Evaluation): 180 gün sonra hizmet kapanır, veritabanlarına erişilemez."""
    return "evaluation" in (edition or "").lower()


def gecici_surum(server: str, edition: str) -> bool:
    """Atölyede kalıcı kullanım için uygun olmayan örnek: LocalDB veya deneme sürümü."""
    return server.lower().startswith("(localdb)") or is_evaluation(edition)


def is_developer(edition: str) -> bool:
    """Developer sürümleri süresizdir ama yalnızca geliştirme/test için lisanslıdır."""
    return "developer" in (edition or "").lower()


def surum_sirasi(server: str, edition: str) -> int:
    """0: atölye için uygun (Express, Standard...), 1: Developer, 2: LocalDB veya deneme sürümü."""
    if gecici_surum(server, edition):
        return 2
    return 1 if is_developer(edition) else 0


def create_database(conn, name) -> bool:
    cur = conn.cursor()
    if cur.execute("SELECT DB_ID(?)", name).fetchone()[0] is not None:
        return False
    cur.execute("DECLARE @sql NVARCHAR(400) = N'CREATE DATABASE ' + QUOTENAME(?); EXEC (@sql);", name)
    return True


def drop_database(conn, name):
    cur = conn.cursor()
    cur.execute("DECLARE @n SYSNAME = ?; IF DB_ID(@n) IS NOT NULL BEGIN "
                "DECLARE @sql NVARCHAR(600) = N'ALTER DATABASE ' + QUOTENAME(@n) + N' SET SINGLE_USER WITH ROLLBACK IMMEDIATE; "
                "DROP DATABASE ' + QUOTENAME(@n); EXEC (@sql); END", name)


def run_tests(args, pyodbc, driver, server, master):
    """Tüm otomatik testleri geçici veritabanlarında çalıştırır; sonunda siler."""
    from sqlalchemy import create_engine
    suffix = secrets.token_hex(3)
    test_db, mig_db, e2e_db = f"deneyap_test_{suffix}", f"deneyap_tasima_test_{suffix}", f"deneyap_e2e_{suffix}"
    results = {}
    try:
        adim("T1", f"Geçici test veritabanı oluşturuluyor: {test_db}")
        create_database(master, test_db)
        url = sqlalchemy_url(connection_string(server, test_db, driver, args.sql_kullanici, args.sql_sifre))
        env = dict(os.environ, TEST_DATABASE_URL=url, DATABASE_URL=url,
                   SECRET_KEY="mssql-test-" + secrets.token_hex(16))
        adim("T2", "API testleri SQL Server üzerinde çalıştırılıyor (birkaç dakika sürebilir)...")
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=BACKEND_DIR, env=env)
        results["API testleri"] = r.returncode == 0

        try:
            import playwright  # noqa: F401
            create_database(master, e2e_db)
            e2e_url = sqlalchemy_url(connection_string(server, e2e_db, driver, args.sql_kullanici, args.sql_sifre))
            adim("T3", "Tarayıcı (arayüz) testleri SQL Server üzerinde çalıştırılıyor...")
            r = subprocess.run([sys.executable, "-m", "pytest", "tests_e2e", "-q", "-p", "no:cacheprovider"],
                               cwd=BACKEND_DIR, env=dict(env, TEST_DATABASE_URL=e2e_url, DATABASE_URL=e2e_url))
            results["Tarayıcı testleri"] = r.returncode == 0
        except ImportError:
            uyari("Tarayıcı testleri atlandı (playwright kurulu değil).")

        if os.path.exists(SQLITE_PATH):
            adim("T4", f"Gerçek verilerin taşınması deneniyor (geçici veritabanı: {mig_db})")
            create_database(master, mig_db)
            eng = create_engine(sqlalchemy_url(connection_string(server, mig_db, driver, args.sql_kullanici, args.sql_sifre)))
            try:
                src_counts, dst_counts = migrate_sqlite(SQLITE_PATH, eng)
                same = all(dst_counts.get(k, 0) == v for k, v in src_counts.items())
                (ok if same else hata)(f"Kayıt sayıları {'eşleşiyor' if same else 'EŞLEŞMİYOR'}: "
                                       + ", ".join(f"{k}={dst_counts.get(k, 0)}" for k in ("products", "users", "shipments", "stock_logs")))
                problems = verify_database(eng)
                for p in problems:
                    hata(p)
                results["Veri taşıma"] = same and not problems
            finally:
                eng.dispose()
    finally:
        adim("T5", "Geçici veritabanları siliniyor")
        for name in (test_db, e2e_db, mig_db):
            try:
                drop_database(master, name)
            except Exception as exc:
                uyari(f"{name} silinemedi: {exc}")
    print("\n" + "=" * 60)
    for k, v in results.items():
        print(f"  {'[OK]' if v else '[X] '}  {k}")
    print("=" * 60)
    return all(results.values()) if results else False


def active_admins(engine) -> list:
    from sqlalchemy import select
    from models import User
    U = User.__table__
    with engine.connect() as conn:
        return [r[0] for r in conn.execute(select(U.c.email).where(U.c.role == "admin", U.c.is_active == True)  # noqa: E712 (.is_(True) SQL Server'da "IS 1" olur)
                                           .order_by(U.c.id)).all()]


def set_admin_password(args, engine) -> None:
    """Taşımadan sonra giriş yapılacak yönetici hesabını gösterir; istenirse şifresini yeniler."""
    from sqlalchemy import update
    from models import User
    admins = active_admins(engine)
    adim("4b", "Yönetici hesabı")
    if not admins:
        bilgi("Henüz kullanıcı yok. Uygulama ilk açıldığında 'İlk Kurulum' ekranından yönetici oluşturulur.")
        return
    ok("Giriş yapabilecek aktif yönetici(ler): " + ", ".join(admins))
    if args.evet or not sor("Bu hesabın şifresini şimdi yenilemek ister misiniz? (şifrenizi hatırlamıyorsanız)", False):
        bilgi("Şifrenizi sonra yenilemek için:  python sifre_sifirla.py <e-posta>")
        return
    email = admins[0]
    if len(admins) > 1:
        for i, e in enumerate(admins, 1):
            bilgi(f"{i}) {e}")
        try:
            secim = int(input("    ? Hangisi (numara): ").strip() or "1")
            email = admins[max(1, min(secim, len(admins))) - 1]
        except (ValueError, EOFError):
            pass
    from auth import KNOWN_WEAK_PASSWORDS, get_password_hash, password_problem
    while True:
        pw = getpass.getpass(f"    Yeni şifre ({email}): ")
        problem = password_problem(pw) or ("Bu şifre çok yaygın" if pw.lower() in KNOWN_WEAK_PASSWORDS else None)
        if problem:
            uyari(problem)
            continue
        if getpass.getpass("    Yeni şifre (tekrar): ") != pw:
            uyari("Şifreler aynı değil")
            continue
        break
    U = User.__table__
    with engine.begin() as conn:
        conn.execute(update(U).where(U.c.email == email).values(hashed_password=get_password_hash(pw)))
    ok(f"{email} şifresi yenilendi")


def son_islem_tarihi(engine) -> str:
    """Kullanıcı işlemlerinin (stok hareketi, ürün/gönderim/kullanıcı ekleme) en son tarihi; yoksa ''."""
    from sqlalchemy import func, inspect, select
    from models import Product, Shipment, StockLog, User
    names = set(inspect(engine).get_table_names())
    tarihler = []
    with engine.connect() as conn:
        for model in (StockLog, Product, Shipment, User):
            t = model.__table__
            if t.name in names:
                try:
                    v = conn.execute(select(func.max(t.c.created_at))).scalar()
                except Exception:
                    v = None
                if v:
                    tarihler.append(str(v)[:19])
    return max(tarihler, default="")


def setup_target(args, engine, server):
    """Adım 3b-6: tablolar, veri taşıma, Türkçe doğrulama ve .env. (SQLite hedefle de test edilebilir.)"""
    from sqlalchemy import create_engine
    from database import Base
    import models  # noqa: F401
    Base.metadata.create_all(engine)
    counts = table_counts(engine)
    ok(f"Tablolar hazır ({len(counts)} tablo). Mevcut ürün: {counts.get('products', 0)}, kullanıcı: {counts.get('users', 0)}")

    adim(4, "Veri taşıma (SQLite -> SQL Server)")
    if counts.get("products", 0) or counts.get("users", 0):
        ok("SQL Server veritabanında zaten veri var; taşıma yapılmadı (mevcut veriler korunur).")
        hedef_son = son_islem_tarihi(engine)
        bilgi(f"SQL Server'da: {counts.get('products', 0)} ürün, {counts.get('users', 0)} kullanıcı, "
              f"{counts.get('stock_logs', 0)} stok kaydı; son işlem: {hedef_son or '-'}")
        if os.path.exists(SQLITE_PATH):
            src = create_engine(f"sqlite:///{SQLITE_PATH}")
            try:
                src_counts, kaynak_son = table_counts(src), son_islem_tarihi(src)
            finally:
                src.dispose()
            bilgi(f"SQLite'ta (deneyap_depo.db): {src_counts.get('products', 0)} ürün, {src_counts.get('users', 0)} "
                  f"kullanıcı, {src_counts.get('stock_logs', 0)} stok kaydı; son işlem: {kaynak_son or '-'}")
            if kaynak_son and (not hedef_son or kaynak_son > hedef_son):
                uyari("SQLite dosyasındaki veriler SQL Server'dakinden DAHA YENİ görünüyor. Uygulama bundan sonra "
                      "SQL Server'daki (eski) verileri kullanacak.")
                bilgi("SQLite verilerini aynı sunucuda yeni bir veritabanına taşımak için:")
                bilgi(f"    SQL_Server_Kurulum.bat --veritabani {args.veritabani}_yeni")
                if not sor("Yine de SQL Server'daki mevcut verilerle devam edilsin mi?", False, args.evet):
                    bilgi("Hiçbir şey değiştirilmedi.")
                    return 6
    elif not os.path.exists(SQLITE_PATH):
        bilgi("Taşınacak SQLite dosyası yok. Uygulamayı açınca 'İlk Kurulum' ekranı gelecek.")
    else:
        src = create_engine(f"sqlite:///{SQLITE_PATH}")
        src_counts = table_counts(src)
        src.dispose()
        bilgi(f"SQLite'ta: {src_counts.get('products', 0)} ürün, {src_counts.get('users', 0)} kullanıcı, "
              f"{src_counts.get('shipments', 0)} gönderim, {src_counts.get('stock_logs', 0)} stok kaydı")
        try:
            findings = [b for b in source_findings(SQLITE_PATH) if b.kod != "OZET"]
        except Exception as exc:
            findings = []
            uyari(f"Veri kontrolü yapılamadı: {exc}")
        kodlar = {b.kod for b in findings}
        if findings:
            bilgi("Veri kontrolü (taşımadan önce):")
            for b in findings:
                bilgi(f"  - [{b.seviye}] {b.baslik}" + (f" ({b.adet})" if b.adet else ""))
            bilgi("Güvenli düzeltmeler (sahipsiz kayıtlar, ders yazımları, boşluklar, durumlar, varsayılan "
                  "şifreli hesaplar) taşınan kopyada otomatik yapılır.")
        else:
            ok("Veri kontrolünde sorun bulunmadı")
        do_it = args.tasima == "evet" or (args.tasima == "sor" and sor("Bu veriler SQL Server'a taşınsın mı?", True, args.evet))
        if do_it:
            soralim = not args.evet and args.tasima == "sor"
            copies = args.kopya_sil or ("KOPYA_AKTARIM" in kodlar and soralim and sor(
                "Aynı Excel birden fazla kez aktarılmış. Stok hareketi olan kopya kalsın, kullanılmamış "
                "kopyalar taşınmasın mı?", False))
            merge = args.birlestir or ("TEKRAR_URUN" in kodlar and soralim and sor(
                "Aynı depoda aynı adla birden fazla olan ürünler tek kayıtta birleştirilsin mi? "
                "(stok olarak en büyük değer alınır)", False))
            empty = args.bos_gonderim_sil or ("BOS_GONDERIM" in kodlar and soralim and sor(
                "Ürünsüz (boş) gönderim kayıtları taşınmasın mı?", False))
            try:
                src_counts, dst_counts = migrate_sqlite(SQLITE_PATH, engine, merge_duplicates=merge,
                                                        delete_empty_shipments=empty, remove_copies=copies)
            except Exception as exc:
                hata(f"Taşıma başarısız: {explain(exc)}")
                bilgi(str(exc)[:500])
                return 5
            ok("Taşındı: " + ", ".join(f"{k}={dst_counts.get(k, 0)}" for k in
                                     ("products", "users", "warehouses", "courses", "shipments", "stock_logs")))
            bilgi("SQLite dosyanız (deneyap_depo.db) değiştirilmedi; yedek olarak durabilir.")
        else:
            bilgi("Taşıma yapılmadı.")

    set_admin_password(args, engine)

    adim(5, "Türkçe karakter, arama ve sıralama sınanıyor")
    problems = verify_database(engine)
    for p in problems:
        hata(p)
    if not problems:
        ok("Türkçe karakterler, Türkçe arama ve Türk alfabesi sıralaması doğru çalışıyor")

    adim(6, "Ayar dosyası (.env) yazılıyor")
    if args.env_yazma:
        bilgi("--env-yazma verildi; .env değiştirilmedi.")
    else:
        updates = {
            "DB_BACKEND": "mssql", "MSSQL_HOST": server, "MSSQL_DB": args.veritabani,
            "MSSQL_WINDOWS_AUTH": "0" if args.sql_kullanici else "1", "MSSQL_TRUST_CERT": "yes",
        }
        if args.sql_kullanici:
            updates.update(MSSQL_USER=args.sql_kullanici, MSSQL_PASSWORD=args.sql_sifre or "")
        write_env(updates)
        ok(f".env güncellendi: DB_BACKEND=mssql, MSSQL_HOST={server}, MSSQL_DB={args.veritabani}")

    print("\n" + "=" * 64)
    if problems:
        print("  Kurulum tamamlandı ancak yukarıdaki uyarıları kontrol edin.")
    else:
        print("  SQL Server HAZIR. Sistemi_Calistir.bat ile uygulamayı başlatabilirsiniz.")
    print("  Veri kontrolü için:  python veritabani_kontrol.py")
    print("=" * 64)
    return 0 if not problems else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="Deneyap Depo - SQL Server kurulum sihirbazı")
    ap.add_argument("--sunucu", help=r"Sunucu adresi (ör. localhost, .\SQLEXPRESS). Verilmezse otomatik bulunur.")
    ap.add_argument("--veritabani", default="deneyap_depo")
    ap.add_argument("--sql-kullanici", help="Windows kimlik doğrulaması yerine SQL kullanıcısı (ör. sa)")
    ap.add_argument("--sql-sifre", help="SQL kullanıcısının şifresi (verilmezse sorulur)")
    ap.add_argument("--evet", action="store_true", help="Tüm sorulara evet de (otomatik kurulum)")
    ap.add_argument("--tasima", choices=["sor", "evet", "hayir"], default="sor", help="SQLite verilerini taşı")
    ap.add_argument("--birlestir", action="store_true", help="Taşırken aynı depodaki tekrar eden ürünleri birleştir")
    ap.add_argument("--kopya-sil", action="store_true", help="Taşırken aynı Excel'in kullanılmamış fazla kopyalarını alma")
    ap.add_argument("--bos-gonderim-sil", action="store_true", help="Taşırken ürünsüz (boş) gönderim kayıtlarını alma")
    ap.add_argument("--env-yazma", action="store_true", help=".env dosyasını değiştirme")
    ap.add_argument("--test", action="store_true", help="Otomatik testleri geçici SQL Server veritabanında çalıştır")
    ap.add_argument("--hedef-url", help=argparse.SUPPRESS)  # yalnızca otomatik testler için
    args = ap.parse_args(argv)
    # Sihirbaz kendi bağlantılarını kurar; uygulamanın .env'deki veritabanı ayarı devreye girmesin.
    os.environ["DATABASE_URL"] = "sqlite://"

    if args.hedef_url:
        from sqlalchemy import create_engine
        engine = create_engine(args.hedef_url)
        try:
            return setup_target(args, engine, args.sunucu or "localhost")
        finally:
            engine.dispose()

    print("=" * 64)
    print("  DENEYAP DEPO — SQL Server Kurulum Sihirbazı" + (" (TEST MODU)" if args.test else ""))
    print("=" * 64)

    adim(1, "ODBC sürücüsü kontrol ediliyor")
    try:
        import pyodbc
    except ImportError:
        hata("'pyodbc' paketi kurulu değil. Komut: pip install -r requirements-mssql.txt")
        return 2
    drivers = pyodbc.drivers()
    driver = choose_driver(drivers)
    if not driver:
        hata("SQL Server ODBC sürücüsü bulunamadı.")
        bilgi(f"'ODBC Driver 18 for SQL Server' indirip kurun: {ODBC_URL}")
        bilgi("Kurduktan sonra bu sihirbazı tekrar çalıştırın.")
        return 2
    ok(f"Sürücü: {driver}")
    if driver in ("SQL Server", "SQL Server Native Client 11.0"):
        uyari(f"Eski sürücü kullanılıyor. Daha güvenilir bağlantı için 'ODBC Driver 18' önerilir: {ODBC_URL}")

    if args.sql_kullanici and args.sql_sifre is None:
        args.sql_sifre = getpass.getpass(f"    '{args.sql_kullanici}' şifresi: ")

    adim(2, "SQL Server aranıyor")
    server, master = connect_server(args, pyodbc, driver)
    if not master:
        return 3
    row = master.cursor().execute(
        "SELECT CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(50)), CAST(SERVERPROPERTY('Edition') AS NVARCHAR(100)), "
        "CAST(SERVERPROPERTY('Collation') AS NVARCHAR(100))").fetchone()
    ok(f"Bağlandı: {server}  (SQL Server {row[0]}, {row[1]})")
    if server.lower().startswith("(localdb)"):
        uyari("Bu bir LocalDB (geliştirici) örneği. Çalışır, ancak yalnızca bu Windows kullanıcısı oturumdayken "
              "açılır. Atölye için 'SQL Server Express' kurmanız önerilir; kurduktan sonra sihirbazı tekrar çalıştırın.")
        if not args.test and not args.sunucu and not sor("Yine de LocalDB ile devam edilsin mi?", varsayilan=False,
                                                         evet_hepsi=args.evet):
            bilgi("SQL Server Express kurulumunu bitirdikten sonra SQL_Server_Kurulum.bat dosyasını tekrar çalıştırın.")
            master.close()
            return 3
    if is_evaluation(row[1]):
        uyari("Bu SQL Server bir DENEME sürümü (Evaluation Edition): kurulumdan 180 gün sonra çalışmayı durdurur ve "
              "içindeki verilere erişilemez. Atölye için ücretsiz ve süresiz 'SQL Server Express' kurun:")
        bilgi("https://www.microsoft.com/tr-tr/sql-server/sql-server-downloads  ->  'Express' -> 'Şimdi indirin' "
              "(dosya adı SQL2025-SSEI-Expr.exe)")
        bilgi("Deneme sürümünü kaldırmak için: Ayarlar > Uygulamalar > 'Microsoft SQL Server 2025' > Kaldır > Remove.")
        if not args.test and not args.sunucu and not sor("Yine de deneme sürümüyle devam edilsin mi?", varsayilan=False,
                                                         evet_hepsi=args.evet):
            bilgi("Express kurulumunu bitirdikten sonra SQL_Server_Kurulum.bat dosyasını tekrar çalıştırın.")
            master.close()
            return 3
    if is_developer(row[1]):
        uyari("Bu SQL Server 'Developer' sürümü: süresizdir ancak lisansı yalnızca geliştirme ve test içindir. "
              "Atölyedeki gerçek kullanım için ücretsiz 'SQL Server Express' önerilir (Express kurulursa sihirbaz onu seçer).")
    major = int(str(row[0]).split(".")[0])
    if major < 11:
        uyari("SQL Server 2012'den eski sürüm. Lütfen SQL Server 2022 veya 2025 Express kurun.")

    try:
        if args.test:
            return 0 if run_tests(args, pyodbc, driver, server, master) else 1

        adim(3, f"'{args.veritabani}' veritabanı hazırlanıyor")
        try:
            created = create_database(master, args.veritabani)
        except Exception as exc:
            hata(f"Veritabanı oluşturulamadı: {explain(exc)}")
            return 4
        ok("Veritabanı oluşturuldu" if created else "Veritabanı zaten var")

        from sqlalchemy import create_engine
        url = sqlalchemy_url(connection_string(server, args.veritabani, driver, args.sql_kullanici, args.sql_sifre))
        engine = create_engine(url, connect_args={"timeout": 15})
        try:
            return setup_target(args, engine, server)
        finally:
            engine.dispose()
    finally:
        master.close()


if __name__ == "__main__":
    sys.exit(main())
