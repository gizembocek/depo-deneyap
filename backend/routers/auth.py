from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import User, user_warehouse_access
from schemas import UserLogin, UserCreate, UserResponse, Token, UserUpdate
from auth import verify_password, get_password_hash, create_access_token, get_current_user, get_admin_user, validate_password
from datetime import timedelta
from typing import List

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz e-posta veya şifre"
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Hesap devre dışı")

    access_token = create_access_token(data={"sub": str(user.id)})

    warehouse_ids = [w.id for w in user.warehouses]

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            warehouse_ids=warehouse_ids
        )
    )


@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bu e-posta adresi zaten kayıtlı")

    # Validate password complexity
    validate_password(user_data.password)

    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        warehouse_ids=[]
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    warehouse_ids = [w.id for w in current_user.warehouses]
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        warehouse_ids=warehouse_ids
    )


@router.get("/users", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    users = db.query(User).all()
    result = []
    for u in users:
        warehouse_ids = [w.id for w in u.warehouses]
        result.append(UserResponse(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at,
            warehouse_ids=warehouse_ids
        ))
    return result


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_data: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    db.commit()
    db.refresh(user)

    warehouse_ids = [w.id for w in user.warehouses]
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        warehouse_ids=warehouse_ids
    )


@router.post("/users/{user_id}/warehouses/{warehouse_id}")
def grant_warehouse_access(user_id: int, warehouse_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    from models import Warehouse
    user = db.query(User).filter(User.id == user_id).first()
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not user or not warehouse:
        raise HTTPException(status_code=404, detail="Kullanıcı veya depo bulunamadı")

    if warehouse not in user.warehouses:
        user.warehouses.append(warehouse)
        db.commit()

    return {"message": "Depo erişimi verildi"}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Kendi hesabınızı silemezsiniz")
    db.delete(user)
    db.commit()
    return {"message": "Kullanıcı silindi"}


@router.delete("/users/{user_id}/warehouses/{warehouse_id}")
def revoke_warehouse_access(user_id: int, warehouse_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    from models import Warehouse
    user = db.query(User).filter(User.id == user_id).first()
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not user or not warehouse:
        raise HTTPException(status_code=404, detail="Kullanıcı veya depo bulunamadı")

    if warehouse in user.warehouses:
        user.warehouses.remove(warehouse)
        db.commit()

    return {"message": "Depo erişimi kaldırıldı"}
