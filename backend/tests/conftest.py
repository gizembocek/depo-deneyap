"""
Test ortamı: her test oturumu geçici bir SQLite veritabanı kullanır.
Gerçek veritabanınıza (.env) DOKUNULMAZ.

Çalıştırma (backend klasöründe):   python -m pytest
"""
import os
import sys
import tempfile

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

_TMP = tempfile.mkdtemp(prefix="deneyap_test_")
# TEST_DATABASE_URL verilirse (ör. SQL Server'da geçici bir veritabanı) testler orada çalışır.
# mssql_kurulum.py --test bunu kullanır. Verilmezse geçici bir SQLite dosyası kullanılır.
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL") or (
    "sqlite:///" + os.path.join(_TMP, "test.db").replace("\\", "/"))
os.environ["YEDEK_KLASORU"] = os.path.join(_TMP, "yedekler")
os.environ["UPLOAD_DIR"] = os.path.join(_TMP, "uploads")  # test görselleri gerçek klasöre yazılmasın
os.environ["SECRET_KEY"] = "test-anahtari-0123456789abcdef0123456789"
# Testlerin başlattığı alt işlemler (sihirbaz, yedekleme aracı...) Türkçe çıktıyı her sistemde UTF-8
# yazsın. Windows'ta çıktı bir boruya (pipe) yazılınca varsayılan kod sayfası (cp1254/cp857) kullanılıyor,
# "ı" gibi harfler UTF-8 olarak okunamıyordu.
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"
os.environ.pop("SUPABASE_URL", None)
os.environ.pop("SUPABASE_KEY", None)

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from auth import login_limiter  # noqa: E402
from database import Base, engine  # noqa: E402

ADMIN_PASSWORD = "Deneyap2026"


# ---------------------------------------------------------------------------
# SQL Server uyumluluk bekçisi: testler SQLite'ta çalışırken, çalıştırılan HER sorgu ayrıca
# SQL Server diliyle derlenir. SQLite'ın kabul edip SQL Server'ın reddettiği yazımlar
# (ör. "is_active IS 1", ORDER BY olmadan OFFSET) böylece SQL Server olmadan da yakalanır.
# ---------------------------------------------------------------------------
import re  # noqa: E402

from sqlalchemy import event  # noqa: E402
from sqlalchemy.dialects import mssql as _mssql  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.exc import CompileError  # noqa: E402
from sqlalchemy.sql import ClauseElement  # noqa: E402

MSSQL_UYUMSUZ = []
_MSSQL_YASAK = re.compile(r"\bIS (NOT )?[01]\b")


@event.listens_for(Engine, "before_execute")
def _mssql_derleme_kontrolu(conn, clauseelement, multiparams, params, execution_options):
    if conn.dialect.name == "mssql" or not isinstance(clauseelement, ClauseElement):
        return
    try:
        sql = str(clauseelement.compile(dialect=_mssql.dialect()))
    except CompileError as exc:
        MSSQL_UYUMSUZ.append(f"{exc}")
        return
    except Exception:  # SQL Server'a özgü olmayan yardımcı ifadeler (ör. SQLite PRAGMA) — sorun değil
        return
    m = _MSSQL_YASAK.search(sql)
    if m:
        tek = " ".join(sql.split())
        i = tek.find(m.group(0))
        MSSQL_UYUMSUZ.append("..." + tek[max(0, i - 150):i + 60] + "...")


@pytest.fixture(scope="session", autouse=True)
def _mssql_uyumsuz_sorgu_yok():
    yield
    assert not MSSQL_UYUMSUZ, "SQL Server'da çalışmayacak sorgular:\n" + "\n".join(sorted(set(MSSQL_UYUMSUZ)))


@pytest.fixture(scope="session")
def client():
    with TestClient(main.app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_db(client):
    """Her testten önce tüm tabloları boşalt."""
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    login_limiter.reset()
    yield


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin(client):
    r = client.post("/api/auth/setup", json={
        "atolye_adi": "Artvin Deneyap Atölyesi", "il": "Artvin",
        "full_name": "Gizem Böcek", "email": "gizem@deneyap.org",
        "password": ADMIN_PASSWORD, "standart_dersler": True,
    })
    assert r.status_code == 200, r.text
    return auth_header(r.json()["access_token"])


@pytest.fixture
def make_user(client, admin):
    def _make(email="egitmen@deneyap.org", role="user", warehouse_ids=(), password="Egitmen2026"):
        r = client.post("/api/auth/register", headers=admin,
                        json={"email": email, "full_name": "Eğitmen Kullanıcı", "password": password, "role": role})
        assert r.status_code == 200, r.text
        uid = r.json()["id"]
        if warehouse_ids:
            r = client.put(f"/api/auth/users/{uid}/warehouses", headers=admin, json={"warehouse_ids": list(warehouse_ids)})
            assert r.status_code == 200, r.text
        r = client.post("/api/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        return auth_header(r.json()["access_token"]), uid
    return _make


@pytest.fixture
def warehouse(client, admin):
    def _make(name="Ana Depo"):
        r = client.post("/api/warehouses/", headers=admin, json={"name": name, "location": "Zemin kat"})
        assert r.status_code == 200, r.text
        return r.json()["id"]
    return _make


@pytest.fixture
def product(client, admin):
    def _make(name="Arduino Uno", stock=10, **extra):
        body = {"name": name, "current_stock": stock, "critical_stock": 3, "ideal_stock": 20,
                "category": "Elektronik Bileşen"}
        body.update(extra)
        r = client.post("/api/products/", headers=admin, json=body)
        assert r.status_code == 200, r.text
        return r.json()
    return _make
