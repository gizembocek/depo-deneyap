"""
Veritabanı bağlantısı.

Desteklenen veritabanları:
  - SQLite      (varsayılan; kurulum gerektirmez, tek atölye için idealdir)
  - SQL Server  (DB_BACKEND=mssql, pyodbc + ODBC sürücüsü gerekir)
  - PostgreSQL  (DATABASE_URL=postgresql://..., bulut kurulumları için)

Öncelik sırası:
  1. DATABASE_URL tanımlıysa o kullanılır.
  2. Yoksa DB_BACKEND değerine bakılır (sqlite | mssql). Varsayılan: sqlite.
"""
import os
import urllib.parse

from sqlalchemy import create_engine, event, func, literal_column
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

# .env dosyaları her zaman backend klasöründen okunur (hangi klasörden
# başlatılırsa başlatılsın). Ortam değişkenleri .env'den önceliklidir.
load_dotenv(dotenv_path=os.path.join(BACKEND_DIR, ".env.local"), override=False)
load_dotenv(dotenv_path=os.path.join(BACKEND_DIR, ".env"), override=False)

DB_BACKEND = os.getenv("DB_BACKEND", "sqlite").strip().lower()

MSSQL_DRIVER_PREFERENCE = [
    "ODBC Driver 18 for SQL Server",
    "ODBC Driver 17 for SQL Server",
    "ODBC Driver 13 for SQL Server",
    "SQL Server Native Client 11.0",
    "SQL Server Native Client RDA 11.0",
    "SQL Server",
]


def _sqlite_url() -> str:
    db_path = os.getenv("SQLITE_PATH") or os.path.join(BACKEND_DIR, "deneyap_depo.db")
    return f"sqlite:///{db_path}"


def _mssql_driver() -> str:
    env_driver = os.getenv("MSSQL_DRIVER")
    if env_driver:
        return env_driver
    import pyodbc  # yalnızca SQL Server kullanılıyorsa gerekir
    available = pyodbc.drivers()
    return next((d for d in MSSQL_DRIVER_PREFERENCE if d in available), "SQL Server")


def mssql_connection_string(server: str, database: str, driver: str, windows_auth: bool = True,
                            user: str = "", password: str = "", trust_cert: str = "yes",
                            port: str = "") -> str:
    """pyodbc bağlantı metni. Kurulum sihirbazı da bu fonksiyonu kullanır."""
    # Port verilmezse ODBC sırasıyla Shared Memory -> Named Pipes -> TCP dener.
    server_part = f"{server},{port}" if port else server
    parts = [f"DRIVER={{{driver}}}", f"SERVER={server_part}", f"DATABASE={database}"]
    # Eski "SQL Server" sürücüsü Encrypt/TrustServerCertificate parametrelerini tanımaz
    if driver != "SQL Server":
        parts.append("Encrypt=yes")
        parts.append(f"TrustServerCertificate={trust_cert}")
    if windows_auth:
        parts.append("Trusted_Connection=yes")
    else:
        parts.append(f"UID={user}")
        parts.append("PWD={" + password.replace("}", "}}") + "}")
    return ";".join(parts)


def _mssql_settings() -> dict:
    return {
        "server": os.getenv("MSSQL_HOST", "localhost"),
        "database": os.getenv("MSSQL_DB", "deneyap_depo"),
        "windows_auth": os.getenv("MSSQL_WINDOWS_AUTH", "1") == "1",
        "user": os.getenv("MSSQL_USER", "sa"),
        "password": os.getenv("MSSQL_PASSWORD", ""),
        "trust_cert": os.getenv("MSSQL_TRUST_CERT", "yes"),
        "port": os.getenv("MSSQL_PORT", ""),
    }


def _mssql_url() -> str:
    cfg = _mssql_settings()
    try:
        driver = _mssql_driver()
    except ImportError:
        raise SystemExit("[HATA] SQL Server için 'pyodbc' paketi kurulu değil.\n"
                         "backend klasöründe şunu çalıştırın:  pip install -r requirements-mssql.txt\n"
                         "(Sistemi_Calistir.bat .env'de DB_BACKEND=mssql görürse bunu otomatik yapar.)")
    conn = mssql_connection_string(driver=driver, **cfg)
    return "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(conn)


DATABASE_URL = os.getenv("DATABASE_URL") or (_mssql_url() if DB_BACKEND == "mssql" else _sqlite_url())

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

IS_SQLITE = DATABASE_URL.startswith("sqlite")
IS_MSSQL = DATABASE_URL.startswith("mssql")

# ---------------------------------------------------------------------------
# Motor
# ---------------------------------------------------------------------------
connect_args: dict = {}
engine_kwargs: dict = {"pool_pre_ping": True}

if IS_SQLITE:
    connect_args["check_same_thread"] = False
    connect_args["timeout"] = 30  # aynı anda iki işlem olursa kilit için bekle
elif IS_MSSQL:
    engine_kwargs["pool_recycle"] = 3600
    connect_args["timeout"] = 15  # sunucuya ulaşılamazsa 15 sn sonra anlaşılır hata ver
    # Not: fast_executemany bilerek KAPALI. NVARCHAR(MAX) sütunlarda (görseller,
    # açıklamalar) bazı sürücü sürümlerinde bellek/kesilme hatalarına yol açabiliyor.

engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)


# ---------------------------------------------------------------------------
# Türkçe karakter duyarsız arama
# ---------------------------------------------------------------------------
_TR_FOLD_TABLE = str.maketrans({
    "İ": "i", "I": "i", "ı": "i",
    "Ç": "c", "ç": "c", "Ğ": "g", "ğ": "g", "Ö": "o", "ö": "o",
    "Ş": "s", "ş": "s", "Ü": "u", "ü": "u", "Â": "a", "â": "a",
    "Î": "i", "î": "i", "Û": "u", "û": "u",
})


def tr_fold(text):
    """'Işıklı Büyüteç' -> 'isikli buyutec'. Arama ve tekrar kontrolünde kullanılır."""
    if text is None:
        return None
    return str(text).translate(_TR_FOLD_TABLE).lower().strip()


_TR_ALPHABET = "0123456789aâbcçdefgğhıiîjklmnoöpqrsştuûüvwxyz"
_TR_ORDER = {ch: i for i, ch in enumerate(_TR_ALPHABET)}


def tr_sort_key(text) -> list:
    """Türk alfabesine göre sıralama anahtarı (ç, ğ, ı, ö, ş, ü doğru yerde)."""
    text = (text or "").replace("I", "ı").replace("İ", "i").lower()
    return [_TR_ORDER.get(ch, 100 + ord(ch)) for ch in text]


def _tr_collation(a, b) -> int:
    ka, kb = tr_sort_key(a), tr_sort_key(b)
    return (ka > kb) - (ka < kb)


if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def _sqlite_on_connect(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        # SQLite'ın lower() fonksiyonu Türkçe harfleri tanımaz; kendi fonksiyonumuzu ekliyoruz.
        dbapi_connection.create_function("tr_fold", 1, tr_fold, deterministic=True)
        dbapi_connection.create_collation("TR", _tr_collation)


_FOLD_PAIRS = [
    ("İ", "i"), ("I", "i"), ("ı", "i"), ("Ç", "c"), ("ç", "c"), ("Ğ", "g"), ("ğ", "g"),
    ("Ö", "o"), ("ö", "o"), ("Ş", "s"), ("ş", "s"), ("Ü", "u"), ("ü", "u"),
    ("Â", "a"), ("â", "a"), ("Î", "i"), ("î", "i"), ("Û", "u"), ("û", "u"),
]


def _dialect_name() -> str:
    return DATABASE_URL.split(":", 1)[0].split("+", 1)[0]


def folded_for(dialect: str, column):
    """folded()'ın belirli bir veritabanı türü için hali (kurulum sihirbazı da kullanır)."""
    if dialect == "sqlite":
        return func.tr_fold(column)
    if dialect == "mssql":
        # İkili (BIN2) karşılaştırmayla harf harf değiştir, sonra küçült
        expr = column.collate("Latin1_General_100_BIN2")
        for src, dst in _FOLD_PAIRS:
            expr = func.replace(expr, literal_column(f"N'{src}'"), literal_column(f"N'{dst}'"))
        return func.lower(expr)
    if dialect == "postgresql":
        src = "".join(a for a, _ in _FOLD_PAIRS)
        dst = "".join(b for _, b in _FOLD_PAIRS)
        return func.lower(func.translate(column, src, dst))
    return func.lower(column)


def folded(column):
    """Bir sütunun aramaya uygun (Türkçe harf ve büyük/küçük harf duyarsız) SQL ifadesi.
    Python tarafındaki tr_fold() ile birebir aynı sonucu üretir."""
    return folded_for(_dialect_name(), column)


def contains_text(expr, term: str, dialect: str = None):
    """expr LIKE '%term%' — kullanıcının yazdığı % _ / karakterleri (SQL Server'da ayrıca [ ) joker
    olarak değil, düz metin olarak aranır."""
    dialect = dialect or _dialect_name()
    escaped = term.replace("/", "//").replace("%", "/%").replace("_", "/_")
    if dialect == "mssql":
        escaped = escaped.replace("[", "/[")
    return expr.like(f"%{escaped}%", escape="/")


def tr_ordered_for(dialect: str, column):
    if dialect == "sqlite":
        return column.collate("TR")
    if dialect == "mssql":
        return column.collate("Turkish_CI_AS")
    return column


def tr_ordered(column):
    """ORDER BY için Türk alfabesi sıralaması."""
    return tr_ordered_for(_dialect_name(), column)


def fold_value(text: str) -> str:
    """folded() ile karşılaştırılacak Python tarafı değer."""
    return tr_fold(text) or ""


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_mssql_database() -> bool:
    """SQL Server'da veritabanı yoksa oluşturur. Oluşturduysa True döner."""
    if not (IS_MSSQL and DB_BACKEND == "mssql" and not os.getenv("DATABASE_URL")):
        return False
    if os.getenv("MSSQL_AUTO_CREATE", "1") != "1":
        return False
    import pyodbc
    cfg = _mssql_settings()
    name = cfg["database"]
    master = mssql_connection_string(driver=_mssql_driver(), **{**cfg, "database": "master"})
    conn = pyodbc.connect(master, autocommit=True, timeout=15)
    try:
        cur = conn.cursor()
        if cur.execute("SELECT DB_ID(?)", name).fetchone()[0] is not None:
            return False
        cur.execute("DECLARE @sql NVARCHAR(400) = N'CREATE DATABASE ' + QUOTENAME(?); EXEC (@sql);", name)
        return True
    finally:
        conn.close()


def init_db() -> None:
    """Gerekirse veritabanını (SQL Server) ve eksik tabloları oluşturur.
    Var olan tablolara ve verilere dokunmaz."""
    import models  # noqa: F401  (tabloların Base'e kaydolması için)
    if ensure_mssql_database():
        print(f"[BİLGİ] SQL Server'da '{os.getenv('MSSQL_DB', 'deneyap_depo')}' veritabanı oluşturuldu.")
    Base.metadata.create_all(bind=engine)


def describe_db_error(exc: Exception) -> str:
    """Veritabanı bağlantı hatasını kullanıcının anlayacağı Türkçe açıklamaya çevirir."""
    text = str(exc)
    low = text.lower()
    if isinstance(exc, ModuleNotFoundError) and "pyodbc" in low:
        return ("SQL Server için 'pyodbc' paketi kurulu değil. backend klasöründe: "
                "pip install -r requirements-mssql.txt  (Sistemi_Calistir.bat bunu otomatik yapar)")
    if "im002" in low or "data source name not found" in low or "veri kaynağı adı bulunamadı" in low:
        return ("ODBC sürücüsü bulunamadı. 'ODBC Driver 18 for SQL Server' kurun: "
                "https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server")
    if "cannot open database" in low or "4060" in low:
        return ("Veritabanı açılamadı. MSSQL_DB adını kontrol edin veya SQL_Server_Kurulum.bat ile "
                "veritabanını oluşturun.")
    if "login failed" in low or "oturum açma başarısız" in low or "18456" in low:
        return ("SQL Server oturum açma reddedildi. Windows kimlik doğrulaması kullanılıyorsa bu Windows "
                "kullanıcısının SQL Server'da yetkisi olmalı; SQL kullanıcısı kullanılıyorsa .env'deki "
                "MSSQL_USER / MSSQL_PASSWORD değerlerini kontrol edin.")
    if "certificate" in low or "ssl" in low or "sertifika" in low:
        return "Şifreli bağlantı sertifikası doğrulanamadı. .env içinde MSSQL_TRUST_CERT=yes olmalı."
    if ("named pipes" in low or "tcp provider" in low or "server does not exist" in low
            or "08001" in low or "hyt00" in low or "timeout" in low or "zaman aşımı" in low):
        return ("SQL Server'a ulaşılamadı. Şunları kontrol edin: (1) 'SQL Server (...)' hizmeti çalışıyor mu? "
                "(2) Sunucu adı doğru mu? Express kurulumunda genelde MSSQL_HOST=.\\SQLEXPRESS olur. "
                "(3) Gerekirse SQL Server Configuration Manager'dan TCP/IP'yi etkinleştirin. "
                "En kolayı: SQL_Server_Kurulum.bat dosyasını çalıştırın, sunucuyu kendisi bulur.")
    return f"Veritabanına bağlanılamadı: {text[:300]}"


def tasinmamis_sqlite_verisi():
    """Uygulama SQL Server/PostgreSQL kullanırken bilgisayarda içi dolu eski bir SQLite dosyası
    (backend/deneyap_depo.db) varsa ürün ve kullanıcı sayılarını döndürür, yoksa None.
    İlk kurulum ekranı bununla 'verilerinizi taşımayı unutmayın' uyarısı gösterir."""
    if IS_SQLITE:
        return None
    import sqlite3
    path = _sqlite_url().split("///", 1)[1]
    if not os.path.isfile(path):
        return None
    try:
        from pathlib import Path
        con = sqlite3.connect(Path(path).absolute().as_uri() + "?mode=ro", uri=True, timeout=2)  # salt okunur
        try:
            urun = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            kullanici = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        finally:
            con.close()
    except Exception:
        return None
    if not (urun or kullanici):
        return None
    return {"dosya": os.path.basename(path), "urun": urun, "kullanici": kullanici}


def aktif_baglanti() -> str:
    if IS_SQLITE:
        return f"SQLite -> {DATABASE_URL.split('///')[-1]}"
    if IS_MSSQL:
        try:
            driver = _mssql_driver()
        except Exception:
            driver = "bilinmiyor"
        return (f"SQL Server -> {os.getenv('MSSQL_HOST', 'localhost')}/"
                f"{os.getenv('MSSQL_DB', 'deneyap_depo')} [surucu: {driver}]")
    return DATABASE_URL.split("@")[-1]
