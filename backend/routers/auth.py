from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from auth import (
    create_access_token, get_admin_user, get_current_user, get_password_hash,
    is_weak_password, login_limiter, validate_password, verify_password,
)
from database import fold_value, folded, get_db, tasinmamis_sqlite_verisi, tr_sort_key
from models import Course, Shipment, User, Warehouse
from schemas import (
    PasswordChange, PasswordReset, SetupRequest, Token, UserCreate, UserLogin,
    UserResponse, UserUpdate, WarehouseAccessUpdate,
)
from settings_store import get_settings, set_setting

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Deneyap atölyelerinde verilen dersler (ilk kurulumda isteğe bağlı eklenir)
STANDART_DERSLER = [
    "Robotik Kodlama",
    "Yapay Zeka",
    "Siber Güvenlik",
    "Malzeme Bilimi ve Nanoteknoloji",
    "Tasarım ve Üretim",
    "Enerji Teknolojileri",
    "Yazılım Teknolojileri",
    "Mobil Uygulama",
    "Elektronik Programlama ve Nesnelerin İnterneti (EPNİ)",
    "İleri Robotik",
    "Havacılık ve Uzay Teknolojileri",
    "Genel",
]


def user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=bool(user.is_active),
        created_at=user.created_at,
        warehouse_ids=[w.id for w in user.warehouses],
    )


def _find_user_by_email(db: Session, email: str):
    return db.query(User).filter(folded(User.email) == fold_value(email)).first()


def _active_admin_count(db: Session) -> int:
    # "== True" bilerek kullanıldı: .is_(True) SQL Server'da geçersiz olan "IS 1" yazımını üretir.
    return db.query(User).filter(User.role == "admin", User.is_active == True).count()  # noqa: E712


# ---------------------------------------------------------------------------
# İlk kurulum
# ---------------------------------------------------------------------------
@router.get("/setup-status")
def setup_status(db: Session = Depends(get_db)):
    """Giriş ekranı bu bilgiyle 'ilk kurulum' formunu gösterip göstermeyeceğine karar verir."""
    s = get_settings(db)
    needs_setup = db.query(User).count() == 0
    return {
        "needs_setup": needs_setup,
        "atolye_adi": s.get("atolye_adi"),
        "il": s.get("il"),
        # Boş bir SQL Server veritabanı açıldı ama eski SQLite verileri taşınmadıysa uyarmak için
        "tasinmamis_veri": tasinmamis_sqlite_verisi() if needs_setup else None,
    }


@router.post("/setup", response_model=Token)
def initial_setup(data: SetupRequest, db: Session = Depends(get_db)):
    if db.query(User).count() > 0:
        raise HTTPException(status_code=400, detail="Kurulum zaten tamamlanmış. Lütfen giriş yapın.")
    validate_password(data.password)

    user = User(
        email=data.email.lower(),
        full_name=data.full_name,
        hashed_password=get_password_hash(data.password),
        role="admin",
        is_active=True,
    )
    db.add(user)
    set_setting(db, "atolye_adi", data.atolye_adi)
    if data.il:
        set_setting(db, "il", data.il)

    if data.standart_dersler:
        mevcut = {c.name for c in db.query(Course).all()}
        for ders in STANDART_DERSLER:
            if ders not in mevcut:
                db.add(Course(name=ders))

    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": user.id}, user=user)
    return Token(access_token=token, token_type="bearer", user=user_to_response(user))


# ---------------------------------------------------------------------------
# Giriş / Kayıt
# ---------------------------------------------------------------------------
@router.post("/login", response_model=Token)
def login(user_data: UserLogin, request: Request, db: Session = Depends(get_db)):
    login_limiter.check(request, user_data.email)
    user = _find_user_by_email(db, user_data.email)
    if not user or not verify_password(user_data.password, user.hashed_password):
        login_limiter.fail(request, user_data.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz e-posta veya şifre")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hesabınız devre dışı bırakılmış. Yöneticinize başvurun.")
    login_limiter.success(request, user_data.email)
    token = create_access_token({"sub": user.id}, user=user)
    # Varsayılan/zayıf şifreyle girildiyse arayüz şifre değiştirmeyi zorunlu tutar
    return Token(access_token=token, token_type="bearer", user=user_to_response(user),
                 must_change_password=is_weak_password(user_data.password))


@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    """Yeni kullanıcıyı yalnızca yönetici oluşturabilir."""
    if _find_user_by_email(db, user_data.email):
        raise HTTPException(status_code=400, detail="Bu e-posta adresi zaten kayıtlı")
    validate_password(user_data.password)

    user = User(
        email=user_data.email.lower(),
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_to_response(user)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return user_to_response(current_user)


@router.post("/change-password")
def change_password(data: PasswordChange, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Mevcut şifreniz hatalı")
    if data.current_password == data.new_password:
        raise HTTPException(status_code=400, detail="Yeni şifre eskisiyle aynı olamaz")
    validate_password(data.new_password)
    current_user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    db.refresh(current_user)
    # Şifre değişince eski oturumlar geçersiz olur; kullanıcıya yeni token verilir.
    token = create_access_token({"sub": current_user.id}, user=current_user)
    return {"message": "Şifreniz değiştirildi", "access_token": token}


# ---------------------------------------------------------------------------
# Kullanıcı yönetimi (yalnızca yönetici)
# ---------------------------------------------------------------------------
@router.get("/users", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    return [user_to_response(u) for u in sorted(db.query(User).all(), key=lambda u: tr_sort_key(u.full_name))]


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_data: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    user = _get_user_or_404(db, user_id)

    removing_admin = (
        (user_data.role is not None and user_data.role != "admin" and user.role == "admin")
        or (user_data.is_active is False and user.role == "admin" and user.is_active)
    )
    if user.id == current_user.id and removing_admin:
        raise HTTPException(status_code=400, detail="Kendi yönetici yetkinizi kaldıramaz veya hesabınızı pasif yapamazsınız")
    if removing_admin and _active_admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="Sistemde en az bir aktif yönetici kalmalıdır")

    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    db.commit()
    db.refresh(user)
    return user_to_response(user)


@router.post("/users/{user_id}/reset-password")
def reset_user_password(user_id: int, data: PasswordReset, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    user = _get_user_or_404(db, user_id)
    validate_password(data.new_password)
    user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    return {"message": f"{user.full_name} kullanıcısının şifresi yenilendi"}


@router.put("/users/{user_id}/warehouses", response_model=UserResponse)
def set_warehouse_access(user_id: int, data: WarehouseAccessUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    """Kullanıcının erişebileceği depoları topluca belirler."""
    user = _get_user_or_404(db, user_id)
    ids = sorted(set(data.warehouse_ids))
    warehouses = db.query(Warehouse).filter(Warehouse.id.in_(ids)).all() if ids else []
    if len(warehouses) != len(ids):
        raise HTTPException(status_code=404, detail="Seçilen depolardan biri bulunamadı")
    user.warehouses = warehouses
    db.commit()
    db.refresh(user)
    return user_to_response(user)


@router.post("/users/{user_id}/warehouses/{warehouse_id}")
def grant_warehouse_access(user_id: int, warehouse_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    user = _get_user_or_404(db, user_id)
    warehouse = db.get(Warehouse, warehouse_id)
    if not warehouse:
        raise HTTPException(status_code=404, detail="Depo bulunamadı")
    if warehouse not in user.warehouses:
        user.warehouses.append(warehouse)
        db.commit()
    return {"message": "Depo erişimi verildi"}


@router.delete("/users/{user_id}/warehouses/{warehouse_id}")
def revoke_warehouse_access(user_id: int, warehouse_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    user = _get_user_or_404(db, user_id)
    warehouse = db.get(Warehouse, warehouse_id)
    if not warehouse:
        raise HTTPException(status_code=404, detail="Depo bulunamadı")
    if warehouse in user.warehouses:
        user.warehouses.remove(warehouse)
        db.commit()
    return {"message": "Depo erişimi kaldırıldı"}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    user = _get_user_or_404(db, user_id)
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Kendi hesabınızı silemezsiniz")
    if user.role == "admin" and user.is_active and _active_admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="Sistemde en az bir aktif yönetici kalmalıdır")
    user.warehouses = []
    # Kullanıcının oluşturduğu kayıtlar silinmez, sadece "oluşturan" bilgisi boşaltılır.
    db.query(Shipment).filter(Shipment.created_by == user.id).update({Shipment.created_by: None}, synchronize_session=False)
    db.delete(user)
    db.commit()
    return {"message": "Kullanıcı silindi"}
