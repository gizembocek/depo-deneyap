import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session

import database
from auth import get_admin_user, get_current_user
from database import get_db
from models import User
from schemas import SettingsUpdate
from settings_store import get_settings, set_setting
from yedekleme import dump
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["Yönetim"])

APP_VERSION = "2.1.0"


@router.get("/health")
def health(db: Session = Depends(get_db)):
    """Kurulum kontrolü: sunucu ve veritabanı çalışıyor mu?"""
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "db_error", "database": db_ok, "version": APP_VERSION}


@router.get("/settings")
def read_settings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    s = get_settings(db)
    return {"atolye_adi": s.get("atolye_adi"), "il": s.get("il"), "version": APP_VERSION}


@router.put("/settings")
def update_settings(data: SettingsUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    if data.atolye_adi is not None:
        set_setting(db, "atolye_adi", data.atolye_adi)
    if "il" in data.model_fields_set:
        set_setting(db, "il", data.il)
    db.commit()
    return read_settings(db, current_user)


@router.get("/admin/backup")
def download_backup(current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Tüm verilerin JSON yedeği. 'python yedekleme.py yukle dosya.json' ile geri yüklenir."""
    data = dump(database.engine)
    data["atolye_adi"] = get_settings(db).get("atolye_adi")
    data["app_version"] = APP_VERSION
    stamp = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=3))).strftime("%Y%m%d_%H%M")
    return Response(
        content=json.dumps(data, ensure_ascii=False).encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=deneyap_yedek_{stamp}.json"},
    )


# ---------------------------------------------------------------------------
# Veritabanı sağlık kontrolü (veritabani_kontrol.py ile aynı kontroller)
# ---------------------------------------------------------------------------
class DbFixRequest(BaseModel):
    tekrar_urun: bool = False
    bos_gonderim: bool = False
    kopya_aktarim: bool = False
    stok_kurali: str = "max"


@router.get("/admin/db-check")
def db_check(current_user: User = Depends(get_admin_user)):
    from veritabani_kontrol import QUICK_PASSWORDS, kontrol_et
    return [asdict(b) for b in kontrol_et(database.engine, sifre_listesi=QUICK_PASSWORDS)]


@router.post("/admin/db-check/fix")
def db_fix(data: Optional[DbFixRequest] = None, current_user: User = Depends(get_admin_user)):
    """Önce sunucuda yedek alır (backend/yedekler), sonra düzeltmeleri uygular."""
    from veritabani_kontrol import QUICK_PASSWORDS, duzelt, kontrol_et, yedek_al
    data = data or DbFixRequest()
    backup_path = yedek_al(database.engine)
    yapilan = duzelt(database.engine, tekrar_urun=data.tekrar_urun, bos_gonderim=data.bos_gonderim,
                     stok_kurali="topla" if data.stok_kurali == "topla" else "max", sifre_listesi=QUICK_PASSWORDS,
                     kopya_aktarim=data.kopya_aktarim)
    bulgular = kontrol_et(database.engine, sifre_listesi=QUICK_PASSWORDS)
    return {"backup": backup_path, "yapilan": yapilan, "bulgular": [asdict(b) for b in bulgular]}

