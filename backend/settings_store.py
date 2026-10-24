"""Atölye ayarlarını (app_settings tablosu) okuyup yazan küçük yardımcılar."""
from sqlalchemy.orm import Session

from models import AppSetting

DEFAULTS = {
    "atolye_adi": None,
    "il": None,
}


def get_settings(db: Session) -> dict:
    values = dict(DEFAULTS)
    for row in db.query(AppSetting).all():
        values[row.key] = row.value
    return values


def set_setting(db: Session, key: str, value) -> None:
    row = db.get(AppSetting, key)
    if row is None:
        db.add(AppSetting(key=key, value=value))
    else:
        row.value = value
