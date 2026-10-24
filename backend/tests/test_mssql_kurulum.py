"""SQL Server kurulum sihirbazının platformdan bağımsız kısımlarının testleri."""
import os
import sqlite3
import subprocess
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, BACKEND_DIR)
import mssql_kurulum as mk  # noqa: E402
from eski_veri import TOPLAM_URUN, eski_veritabani_olustur  # noqa: E402


ORNEK_ENV = """DB_BACKEND=sqlite
MSSQL_HOST=localhost
MSSQL_PORT=1433
# açıklama satırı korunmalı
SECRET_KEY=benim-gizli-anahtarim-1234567890
DATABASE_URL=postgresql://eski
ACCESS_TOKEN_EXPIRE_MINUTES=43200"""


def test_env_guncelleme_mevcut_ayarlari_korur():
    lines = mk.update_env_lines(ORNEK_ENV.splitlines(),
                                {"DB_BACKEND": "mssql", "MSSQL_HOST": r".\SQLEXPRESS", "MSSQL_DB": "deneyap_depo"},
                                comment_out=("DATABASE_URL", "MSSQL_PORT"))
    text = "\n".join(lines)
    assert "DB_BACKEND=mssql" in lines and r"MSSQL_HOST=.\SQLEXPRESS" in lines and "MSSQL_DB=deneyap_depo" in lines
    assert "SECRET_KEY=benim-gizli-anahtarim-1234567890" in lines
    assert "# açıklama satırı korunmalı" in lines
    assert "ACCESS_TOKEN_EXPIRE_MINUTES=43200" in lines
    assert "\nDATABASE_URL=" not in "\n" + text and "# DATABASE_URL=postgresql://eski" in text
    assert "\nMSSQL_PORT=" not in "\n" + text
    assert text.count("DB_BACKEND=") == 1


def test_env_yazilan_deger_uygulama_tarafindan_okunur(tmp_path):
    path = tmp_path / ".env"
    path.write_text(ORNEK_ENV, encoding="utf-8")
    mk.write_env({"DB_BACKEND": "mssql", "MSSQL_HOST": r".\SQLEXPRESS"}, path=str(path))
    from dotenv import dotenv_values
    values = dotenv_values(path)
    assert values["MSSQL_HOST"] == r".\SQLEXPRESS"  # ters bölü bozulmadan okunuyor
    assert values["SECRET_KEY"] == "benim-gizli-anahtarim-1234567890"
    assert "DATABASE_URL" not in values
    assert any(p.name.startswith(".env.yedek_") for p in tmp_path.iterdir())


def test_aday_sunucu_adresleri():
    assert mk.candidate_servers([("SQLEXPRESS", "MSSQL$SQLEXPRESS")], computer="LENOVO")[:3] == [
        r".\SQLEXPRESS", r"localhost\SQLEXPRESS", r"LENOVO\SQLEXPRESS"]
    assert mk.candidate_servers([("MSSQLSERVER", "MSSQLSERVER")], computer="PC")[0] == "localhost"
    assert r".\SQLEXPRESS" in mk.candidate_servers([])
    assert mk.candidate_servers([])[-1] == r"(localdb)\MSSQLLocalDB"


def test_surucu_secimi():
    assert mk.choose_driver(["SQL Server", "ODBC Driver 17 for SQL Server", "ODBC Driver 18 for SQL Server"]) == "ODBC Driver 18 for SQL Server"
    assert mk.choose_driver(["SQL Server"]) == "SQL Server"
    assert mk.choose_driver(["PostgreSQL Unicode"]) is None


class FakeCursor:
    def __init__(self, existing):
        self.existing, self.calls, self._row = existing, [], None

    def execute(self, sql, *params):
        self.calls.append((sql, params))
        if sql.startswith("SELECT DB_ID"):
            self._row = (1 if params[0] in self.existing else None,)
        return self

    def fetchone(self):
        return self._row


class FakeConn:
    def __init__(self, existing=()):
        self.cur = FakeCursor(set(existing))

    def cursor(self):
        return self.cur


def test_veritabani_olusturma_ve_silme_sql():
    conn = FakeConn(existing={"deneyap_depo"})
    assert mk.create_database(conn, "deneyap_depo") is False
    assert mk.create_database(conn, "yeni_db") is True
    sql, params = conn.cur.calls[-1]
    assert "QUOTENAME(?)" in sql and params == ("yeni_db",)
    mk.drop_database(conn, "deneyap_test_abc")
    sql, params = conn.cur.calls[-1]
    assert "SINGLE_USER WITH ROLLBACK IMMEDIATE" in sql and "DROP DATABASE" in sql and params == ("deneyap_test_abc",)


def test_sihirbaz_tasima_adimlari_uctan_uca(tmp_path):
    """Sihirbazın 3-6. adımları (tablolar, eski verinin taşınması, Türkçe doğrulama, .env yazımı)
    SQLite hedefiyle uçtan uca çalıştırılır. SQL Server'a özgü bağlantı adımları SQL_Server_Test.bat ile sınanır."""
    source = tmp_path / "kaynak.db"
    eski_veritabani_olustur(source)
    before = sqlite3.connect(source).execute("select count(*) from products").fetchone()[0]
    assert before == TOPLAM_URUN
    env_file = tmp_path / ".env"
    env_file.write_text(ORNEK_ENV, encoding="utf-8")
    target = tmp_path / "hedef.db"
    env = dict(os.environ, DENEYAP_SQLITE_KAYNAK=str(source), DENEYAP_ENV_DOSYASI=str(env_file))
    cmd = [sys.executable, "mssql_kurulum.py", "--hedef-url", f"sqlite:///{target}", "--evet", "--tasima", "evet",
           "--sunucu", r".\SQLEXPRESS"]
    r = subprocess.run(cmd, cwd=BACKEND_DIR, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    assert "Taşındı" in r.stdout and "Türkçe karakterler, Türkçe arama" in r.stdout

    con = sqlite3.connect(target)
    assert con.execute("select count(*) from products").fetchone()[0] == before
    assert con.execute("select is_active from users where email='admin@deneyap.org'").fetchone()[0] == 0
    assert con.execute("select is_active from users where email='gizem@deneyap.org'").fetchone()[0] == 1
    assert con.execute("pragma foreign_key_check").fetchall() == []
    assert sqlite3.connect(source).execute("select is_active from users where email='admin@deneyap.org'").fetchone()[0] == 1  # kaynak değişmedi
    text = env_file.read_text(encoding="utf-8")
    assert "DB_BACKEND=mssql" in text and r"MSSQL_HOST=.\SQLEXPRESS" in text and "benim-gizli-anahtarim" in text

    r2 = subprocess.run(cmd, cwd=BACKEND_DIR, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    assert r2.returncode == 0 and "zaten veri var" in r2.stdout
    assert con.execute("select count(*) from products").fetchone()[0] == before  # ikinci çalıştırma çoğaltmaz


def test_sihirbaz_temizlik_secenekleriyle_tasima(tmp_path):
    """--kopya-sil --birlestir --bos-gonderim-sil: fazla kopyalar, tekrarlar ve deneme gönderimleri taşınmaz."""
    from eski_veri import FARKLI_MALZEME
    source = tmp_path / "kaynak.db"
    eski_veritabani_olustur(source)
    env_file = tmp_path / ".env"
    env_file.write_text(ORNEK_ENV, encoding="utf-8")
    target = tmp_path / "hedef.db"
    env = dict(os.environ, DENEYAP_SQLITE_KAYNAK=str(source), DENEYAP_ENV_DOSYASI=str(env_file))
    r = subprocess.run([sys.executable, "mssql_kurulum.py", "--hedef-url", f"sqlite:///{target}", "--evet",
                        "--tasima", "evet", "--kopya-sil", "--birlestir", "--bos-gonderim-sil"],
                       cwd=BACKEND_DIR, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    assert "Veri kontrolü (taşımadan önce)" in r.stdout and "Aynı ürün listesi 3 farklı yerde" in r.stdout
    assert "gizem@deneyap.org" in r.stdout  # giriş yapılacak yönetici gösterilir
    con = sqlite3.connect(target)
    assert con.execute("select count(*), count(distinct name) from products").fetchone() == (FARKLI_MALZEME, FARKLI_MALZEME)
    assert con.execute("select count(*) from shipments").fetchone()[0] == 2
    assert con.execute("select count(*) from shipment_items").fetchone()[0] == 2
    assert con.execute("pragma foreign_key_check").fetchall() == []
    assert sqlite3.connect(source).execute("select count(*) from products").fetchone()[0] == TOPLAM_URUN  # kaynak değişmedi


class _SahteBaglanti:
    def __init__(self, edition="Express Edition (64-bit)"):
        self.kapandi = False
        self.edition = edition

    def cursor(self):
        baglanti = self

        class _Imlec:
            def execute(self, sql, *params):
                self.sql = sql
                return self

            def fetchone(self):
                if "ProductVersion" in self.sql:
                    return ("17.0.1000.7", baglanti.edition, "Turkish_CI_AS")
                return (baglanti.edition,)
        return _Imlec()

    def close(self):
        self.kapandi = True


def _sahte_pyodbc(monkeypatch, sunucular, ornekler=()):
    """sunucular: {adres: sürüm adı} — yalnızca bu adreslere bağlanılabilir."""
    import types
    baglantilar = {}
    denenen = []

    def connect(cs, **_):
        sunucu = cs.split("SERVER=", 1)[1].split(";", 1)[0].strip("{}")
        denenen.append(sunucu)
        if sunucu not in sunucular:
            raise RuntimeError("[08001] Named Pipes Provider: Could not open a connection to SQL Server")
        baglantilar[sunucu] = _SahteBaglanti(sunucular[sunucu])
        return baglantilar[sunucu]

    sahte = types.SimpleNamespace(drivers=lambda: ["ODBC Driver 18 for SQL Server"], connect=connect, Error=RuntimeError)
    monkeypatch.setitem(sys.modules, "pyodbc", sahte)
    monkeypatch.setattr(mk, "discover_instances", lambda: list(ornekler))
    monkeypatch.setattr(mk, "service_status", lambda service: "Running")
    monkeypatch.setenv("DATABASE_URL", os.environ.get("DATABASE_URL", ""))  # main() değiştirir; test sonunda geri alınır
    return baglantilar, denenen


LOCALDB = r"(localdb)\MSSQLLocalDB"
EXPRESS = "Express Edition (64-bit)"
DENEME = "Enterprise Evaluation Edition (64-bit)"


def _veritabani_olusturulmamali(monkeypatch):
    monkeypatch.setattr(mk, "create_database", lambda *a: (_ for _ in ()).throw(AssertionError("veritabanı oluşturulmamalı")))


def _kurulumu_taklit_et(monkeypatch):
    import sqlalchemy
    import types
    cagrilar = []
    monkeypatch.setattr(mk, "create_database", lambda conn, name: cagrilar.append(name) or False)
    monkeypatch.setattr(mk, "setup_target", lambda args, engine, server: cagrilar.append(server) or 0)
    monkeypatch.setattr(sqlalchemy, "create_engine", lambda *a, **k: types.SimpleNamespace(dispose=lambda: None))
    return cagrilar


def test_yalnizca_localdb_bulunursa_onay_istenir(monkeypatch, capsys):
    """SQL Server Express henüz kurulmamışken sihirbaz verileri sessizce LocalDB'ye taşımamalı."""
    baglantilar, denenen = _sahte_pyodbc(monkeypatch, {LOCALDB: EXPRESS})
    monkeypatch.setattr("builtins.input", lambda *_: "")  # Enter = varsayılan (Hayır)
    _veritabani_olusturulmamali(monkeypatch)
    assert mk.main([]) == 3
    out = capsys.readouterr().out
    assert "LocalDB" in out and "tekrar çalıştırın" in out
    assert denenen[-1] == LOCALDB and baglantilar[LOCALDB].kapandi


def test_localdb_acikca_istenirse_devam_eder(monkeypatch):
    _sahte_pyodbc(monkeypatch, {LOCALDB: EXPRESS})
    cagrilar = _kurulumu_taklit_et(monkeypatch)
    assert mk.main(["--sunucu", LOCALDB]) == 0
    assert cagrilar == ["deneyap_depo", LOCALDB]


def test_deneme_surumu_bulunursa_uyarir_ve_onay_ister(monkeypatch, capsys):
    """Evaluation sürümü 180 gün sonra kapanır; veriler oraya sessizce taşınmamalı."""
    baglantilar, _ = _sahte_pyodbc(monkeypatch, {r".\MSSQLSERVER01": DENEME, LOCALDB: EXPRESS},
                                   ornekler=[("MSSQLSERVER01", "MSSQL$MSSQLSERVER01")])
    monkeypatch.setattr("builtins.input", lambda *_: "")
    _veritabani_olusturulmamali(monkeypatch)
    assert mk.main([]) == 3
    out = capsys.readouterr().out
    assert "DENEME sürümü" in out and "180 gün" in out and "SQL2025-SSEI-Expr.exe" in out
    assert all(c.kapandi for c in baglantilar.values())


def test_deneme_surumuyle_devam_onaylanirsa_kurulur(monkeypatch):
    _sahte_pyodbc(monkeypatch, {r".\MSSQLSERVER01": DENEME}, ornekler=[("MSSQLSERVER01", "MSSQL$MSSQLSERVER01")])
    monkeypatch.setattr("builtins.input", lambda *_: "e")
    cagrilar = _kurulumu_taklit_et(monkeypatch)
    assert mk.main([]) == 0
    assert cagrilar == ["deneyap_depo", r".\MSSQLSERVER01"]


def test_birden_fazla_sql_server_varsa_kalici_surum_secilir(monkeypatch):
    """Deneme sürümü kaldırılmadan Express kurulduysa sihirbaz Express'i seçmeli."""
    baglantilar, _ = _sahte_pyodbc(monkeypatch, {r".\MSSQLSERVER01": DENEME, r".\SQLEXPRESS": EXPRESS, LOCALDB: EXPRESS},
                                   ornekler=[("MSSQLSERVER01", "MSSQL$MSSQLSERVER01"), ("SQLEXPRESS", "MSSQL$SQLEXPRESS")])
    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("soru sorulmamalı")))
    cagrilar = _kurulumu_taklit_et(monkeypatch)
    assert mk.main([]) == 0
    assert cagrilar == ["deneyap_depo", r".\SQLEXPRESS"]
    assert baglantilar[r".\MSSQLSERVER01"].kapandi


DEVELOPER = "Standard Developer Edition (64-bit)"


def test_developer_ve_express_varsa_express_secilir(monkeypatch):
    _sahte_pyodbc(monkeypatch, {"localhost": DEVELOPER, r".\SQLEXPRESS": EXPRESS},
                  ornekler=[("MSSQLSERVER", "MSSQLSERVER"), ("SQLEXPRESS", "MSSQL$SQLEXPRESS")])
    cagrilar = _kurulumu_taklit_et(monkeypatch)
    assert mk.main([]) == 0
    assert cagrilar == ["deneyap_depo", r".\SQLEXPRESS"]


def test_yalnizca_developer_varsa_uyarip_devam_eder(monkeypatch, capsys):
    _sahte_pyodbc(monkeypatch, {"localhost": DEVELOPER, LOCALDB: EXPRESS}, ornekler=[("MSSQLSERVER", "MSSQLSERVER")])
    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("soru sorulmamalı")))
    cagrilar = _kurulumu_taklit_et(monkeypatch)
    assert mk.main([]) == 0
    assert cagrilar == ["deneyap_depo", "localhost"]  # Developer, LocalDB'ye tercih edilir
    assert "geliştirme ve test" in capsys.readouterr().out


def test_hedefte_daha_eski_veri_varsa_uyarir_ve_durur(tmp_path):
    """SQL Server'da eski bir veritabanı varken SQLite'taki daha yeni veriler sessizce yok sayılmamalı."""
    source = tmp_path / "kaynak.db"
    eski_veritabani_olustur(source)
    target = tmp_path / "hedef.db"
    eski_veritabani_olustur(target)
    con = sqlite3.connect(target)
    for t in ("products", "users", "shipments", "stock_logs"):
        con.execute(f"update {t} set created_at = '2026-05-01 10:00:00'")
    con.commit()
    con.close()
    env_file = tmp_path / ".env"
    env_file.write_text(ORNEK_ENV, encoding="utf-8")
    env = dict(os.environ, DENEYAP_SQLITE_KAYNAK=str(source), DENEYAP_ENV_DOSYASI=str(env_file))
    cmd = [sys.executable, "mssql_kurulum.py", "--hedef-url", f"sqlite:///{target}", "--evet", "--sunucu", "localhost"]
    r = subprocess.run(cmd, cwd=BACKEND_DIR, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    assert r.returncode == 6, r.stdout[-3000:] + r.stderr[-3000:]
    assert "DAHA YENİ" in r.stdout and "--veritabani deneyap_depo_yeni" in r.stdout
    assert "son işlem: 2026-09-21 08:30:11" in r.stdout and "son işlem: 2026-05-01 10:00:00" in r.stdout
    assert env_file.read_text(encoding="utf-8") == ORNEK_ENV  # .env değişmedi
