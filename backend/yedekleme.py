"""
Yedekleme ve veri taşıma aracı.

Uygulama içinden: Ayarlar > "Yedek İndir" (JSON dosyası).
Komut satırından (backend klasöründe):

    # Mevcut veritabanının yedeğini al
    python yedekleme.py al yedek.json

    # Yedeği BOŞ bir veritabanına geri yükle (.env'deki veritabanına)
    python yedekleme.py yukle yedek.json

    # Yedeği belirli bir veritabanına yükle
    python yedekleme.py yukle yedek.json --hedef "sqlite:///yeni.db"

    # Bir veritabanından diğerine doğrudan taşı (ör. SQLite -> SQL Server)
    python yedekleme.py tasi --kaynak "sqlite:///deneyap_depo.db" --hedef "mssql+pyodbc://..."

Geri yükleme yalnızca boş veritabanına yapılır; mevcut veriler asla silinmez.
"""
import argparse
import json
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import DateTime, create_engine, func, select, text  # noqa: E402

import models  # noqa: E402,F401  (tabloları kaydeder)
from database import Base  # noqa: E402

FORMAT_VERSION = 1


def _jsonable(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value


def dump(engine) -> dict:
    """Tüm tabloları sözlük olarak döndürür."""
    data = {"format": "deneyap-depo-yedek", "version": FORMAT_VERSION,
            "created_at": datetime.utcnow().isoformat(), "tables": {}}
    with engine.connect() as conn:
        existing = set(engine.dialect.get_table_names(conn))
        for table in Base.metadata.sorted_tables:
            if table.name not in existing:
                data["tables"][table.name] = []
                continue
            rows = conn.execute(select(table)).mappings().all()
            data["tables"][table.name] = [{k: _jsonable(v) for k, v in row.items()} for row in rows]
    data["counts"] = {name: len(rows) for name, rows in data["tables"].items()}
    return data


def _convert(table, row: dict) -> dict:
    out = {}
    for col in table.columns:
        if col.name not in row:
            continue
        value = row[col.name]
        if value is not None and isinstance(col.type, DateTime) and isinstance(value, str):
            value = datetime.fromisoformat(value)
        out[col.name] = value
    return out


def restore(engine, data: dict) -> dict:
    """Yedeği boş bir veritabanına yükler. Doluysa hata verir."""
    if data.get("format") != "deneyap-depo-yedek":
        raise ValueError("Bu dosya bir Deneyap Depo yedeği değil")
    Base.metadata.create_all(bind=engine)
    tables = data.get("tables", {})
    dialect = engine.dialect.name
    inserted = {}
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if conn.execute(select(func.count()).select_from(table)).scalar():
                raise ValueError(f"Hedef veritabanı boş değil ('{table.name}' tablosunda kayıt var). "
                                 "Geri yükleme yalnızca boş veritabanına yapılabilir.")
        for table in Base.metadata.sorted_tables:
            rows = [_convert(table, r) for r in tables.get(table.name, [])]
            inserted[table.name] = len(rows)
            if not rows:
                continue
            # Not: SQL Server'da 'id' değerleri korunarak yazılır. Gerekli "SET IDENTITY_INSERT ON/OFF"
            # komutlarını SQLAlchemy her INSERT için kendisi gönderir.
            for start in range(0, len(rows), 500):
                conn.execute(table.insert(), rows[start:start + 500])
            if dialect == "postgresql" and "id" in table.columns:
                conn.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {table.name}), 1))"))
    return inserted


def _engine(url: str):
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    eng = create_engine(url)
    if url.startswith("sqlite"):
        from sqlalchemy import event

        @event.listens_for(eng, "connect")
        def _fk(dbapi_connection, _):
            dbapi_connection.execute("PRAGMA foreign_keys=ON")
    return eng


def main(argv=None):
    parser = argparse.ArgumentParser(description="Deneyap Depo yedekleme aracı")
    sub = parser.add_subparsers(dest="komut", required=True)

    p_al = sub.add_parser("al", help="Yedek al")
    p_al.add_argument("dosya")
    p_al.add_argument("--kaynak", help="Veritabanı adresi (varsayılan: .env ayarı)")

    p_yukle = sub.add_parser("yukle", help="Yedeği boş veritabanına yükle")
    p_yukle.add_argument("dosya")
    p_yukle.add_argument("--hedef", help="Veritabanı adresi (varsayılan: .env ayarı)")

    p_tasi = sub.add_parser("tasi", help="Bir veritabanından diğerine taşı")
    p_tasi.add_argument("--kaynak", required=True)
    p_tasi.add_argument("--hedef", required=True)

    args = parser.parse_args(argv)

    def default_engine():
        from database import engine
        return engine

    if args.komut == "al":
        eng = _engine(args.kaynak) if args.kaynak else default_engine()
        data = dump(eng)
        with open(args.dosya, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"[OK] Yedek alındı: {args.dosya}")
        for name, count in data["counts"].items():
            print(f"  {name}: {count}")
    elif args.komut == "yukle":
        with open(args.dosya, "r", encoding="utf-8") as f:
            data = json.load(f)
        eng = _engine(args.hedef) if args.hedef else default_engine()
        counts = restore(eng, data)
        print("[OK] Yedek geri yüklendi.")
        for name, count in counts.items():
            print(f"  {name}: {count}")
    elif args.komut == "tasi":
        counts = restore(_engine(args.hedef), dump(_engine(args.kaynak)))
        print("[OK] Veriler taşındı.")
        for name, count in counts.items():
            print(f"  {name}: {count}")


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print(f"[HATA] {e}")
        sys.exit(1)
