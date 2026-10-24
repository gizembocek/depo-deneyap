"""veritabani_bul.py: bilgisayardaki Deneyap veritabanlarını bulan salt okunur aracın testleri."""
import os
import re
import sqlite3

import veritabani_bul as vb
from eski_veri import TOPLAM_URUN, eski_veritabani_olustur


def test_sqlite_ozeti(tmp_path):
    db = tmp_path / "eski.db"
    eski_veritabani_olustur(db)
    once = db.read_bytes()
    o = vb.sqlite_ozeti(str(db))
    assert o["sayilar"]["products"] == TOPLAM_URUN and o["sayilar"]["users"] == 3
    assert o["farkli_urun"] == 12
    assert str(o["tarihler"]["Son stok hareketi"]).startswith("2026-06-08 13:06")
    assert ("gizem@deneyap.org", "admin", True) in o["kullanicilar"]
    assert db.read_bytes() == once  # salt okunur


class _SahteSqlServer:
    """T-SQL sorgularını yanıtlar; '[vt].dbo.tablo' sorgularını bir SQLite dosyasında çalıştırır."""

    def __init__(self, sqlite_path):
        self.con = sqlite3.connect(sqlite_path)
        self._rows = []

    def execute(self, sql, *params):
        if "SERVERPROPERTY" in sql:
            self._rows = [("Standard Developer Edition (64-bit)", "17.0.1000.7", r"C:\Yedek", r"C:\Veri")]
        elif "sys.databases" in sql:
            self._rows = [("deneyap_depo", "ONLINE", "2026-09-22 10:00:00"), ("muhasebe", "ONLINE", "2025-01-01"),
                          ("kapali_vt", "OFFLINE", "2025-01-01")]
        elif "HAS_DBACCESS" in sql:
            self._rows = [(1,)]
        elif "OBJECT_ID" in sql:
            self._rows = [(42,) if "[deneyap_depo]" in params[0] else (None,)]
        elif "msdb" in sql:
            self._rows = [("deneyap_depo", "2026-09-25 10:00:00", r"C:\Yedek\deneyap_depo.bak")]
        elif "xp_dirtree" in sql:
            self._rows = ([("deneyap_depo.bak", 1, 1)] if params[0] == r"C:\Yedek"
                          else [("deneyap_depo.mdf", 1, 1), ("eski_depo.mdf", 1, 1), ("alt", 1, 0),
                                ("model_msdbdata.mdf", 1, 1), ("model_replicatedmaster.mdf", 1, 1)])
        elif "sys.master_files" in sql:
            self._rows = [(r"C:\Veri\deneyap_depo.mdf",), (r"C:\Veri\master.mdf",)]
        elif "database_files" in sql:
            self._rows = [(12,)]
        else:
            self._rows = self.con.execute(re.sub(r"\[[^\]]+\]\.dbo\.", "", sql)).fetchall()
        return self

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


def test_sql_server_taramasi(tmp_path, capsys):
    db = tmp_path / "eski.db"
    eski_veritabani_olustur(db)
    bulunanlar = []
    vb.sunucu_tara(_SahteSqlServer(str(db)), "localhost", bulunanlar)
    out = capsys.readouterr().out
    assert [ad for ad, _ in bulunanlar] == ["SQL Server localhost / deneyap_depo"]
    o = bulunanlar[0][1]
    assert o["sayilar"]["products"] == TOPLAM_URUN and o["boyut_mb"] == 12
    assert "muhasebe: Deneyap veritabanı değil" in out
    assert "kapali_vt: OFFLINE" in out
    assert r"C:\Yedek\deneyap_depo.bak" in out          # yedek geçmişi
    assert "eski_depo.mdf" in out and "bağlı OLMAYAN" in out  # bağlı olmayan veri dosyası
    assert "deneyap_depo.mdf" not in out.split("bağlı OLMAYAN", 1)[1]
    assert "model_msdbdata" not in out  # SQL Server'ın kendi şablon dosyaları uyarı sayılmaz


def test_ana_akis_yalnizca_okur(tmp_path, monkeypatch, capsys):
    backend = tmp_path / "backend"
    (backend / "yedekler").mkdir(parents=True)
    eski_veritabani_olustur(backend / "yedekler" / "temizlik_oncesi.db")
    eski_veritabani_olustur(backend / "deneyap_depo.db")
    (backend / ".env").write_text("DB_BACKEND=mssql\nMSSQL_HOST=localhost\n", encoding="utf-8")
    once = {p: p.read_bytes() for p in backend.rglob("*") if p.is_file()}
    monkeypatch.setattr(vb, "BACKEND_DIR", str(backend))
    monkeypatch.setattr(vb, "sql_server_tara", lambda bulunanlar: None)
    monkeypatch.setenv("DATABASE_URL", os.environ.get("DATABASE_URL", ""))
    assert vb.main() == 0
    out = capsys.readouterr().out
    assert "SQL Server -> localhost / deneyap_depo" in out
    assert "SQLite deneyap_depo.db" in out and "temizlik_oncesi.db" in out
    assert "Hiçbir şey değiştirilmedi" in out
    assert {p: p.read_bytes() for p in backend.rglob("*") if p.is_file()} == once
