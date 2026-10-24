"""
Kimlik doğrulama ve yetkilendirme yardımcıları.

- Şifreler bcrypt ile saklanır.
- Oturumlar JWT ile yönetilir. Token içinde şifrenin parmak izi (ph) bulunur;
  kullanıcı şifresini değiştirdiğinde eski oturumlar otomatik geçersiz olur.
- SECRET_KEY .env'de yoksa (veya örnek değer bırakılmışsa) otomatik üretilip
  backend/.secret_key dosyasına kaydedilir. Böylece her kurulumun anahtarı farklıdır.
"""
import hashlib
import os
import re
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import or_
from sqlalchemy.orm import Session

import database  # .env dosyasını yükler
from database import get_db
from models import Product, User

_PLACEHOLDER_KEYS = {
    "", "deneyap-depo-yonetim-gizli-anahtar-2024", "buraya_cok_gizli_bir_anahtar_yazin",
    "buraya-cok-uzun-ve-rastgele-bir-sifre-yazin", "changeme", "secret",
}
_SECRET_FILE = os.path.join(database.BACKEND_DIR, ".secret_key")


def _load_secret_key() -> str:
    env_key = (os.getenv("SECRET_KEY") or "").strip()
    if env_key and env_key not in _PLACEHOLDER_KEYS and "buraya" not in env_key and len(env_key) >= 16:
        return env_key
    try:
        with open(_SECRET_FILE, "r", encoding="utf-8") as f:
            key = f.read().strip()
            if len(key) >= 32:
                return key
    except FileNotFoundError:
        pass
    key = secrets.token_hex(32)
    try:
        # 'x' modu: aynı anda iki süreç başlarsa yalnızca biri yazar, diğeri onu okur
        with open(_SECRET_FILE, "x", encoding="utf-8") as f:
            f.write(key)
    except FileExistsError:
        for _ in range(20):  # diğer süreç yazmayı bitirene kadar kısa süre bekle
            with open(_SECRET_FILE, "r", encoding="utf-8") as f:
                existing = f.read().strip()
            if len(existing) >= 32:
                return existing
            time.sleep(0.05)
    except OSError:
        # Dosyaya yazılamıyorsa (salt okunur disk vb.) anahtar yalnızca bellekte tutulur.
        pass
    return key


SECRET_KEY = _load_secret_key()
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

security = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Şifre işlemleri
# ---------------------------------------------------------------------------
def password_problem(password: str) -> Optional[str]:
    """Şifre kurallara uymuyorsa sebebini döndürür, uyuyorsa None."""
    if password is None or len(password) < 8:
        return "Şifre en az 8 karakter olmalıdır"
    if len(password) > 72:
        return "Şifre en fazla 72 karakter olabilir"
    if not re.search(r"[A-ZÇĞİÖŞÜ]", password):
        return "Şifre en az bir büyük harf içermelidir"
    if not re.search(r"[0-9]", password):
        return "Şifre en az bir rakam içermelidir"
    return None


# Kurulum/demo betiklerinin eskiden kullandığı veya çok yaygın olan şifreler
KNOWN_WEAK_PASSWORDS = {
    "admin123", "user123", "123456", "1234567", "12345678", "123456789", "password", "parola",
    "admin", "deneyap", "deneyap123", "qwerty", "111111", "000000", "sifre", "şifre",
}


def is_weak_password(password: str) -> bool:
    """Giriş sırasında kullanılır: şifre bilinen/zayıf bir şifreyse True."""
    return (password or "").lower() in KNOWN_WEAK_PASSWORDS or password_problem(password) is not None


def validate_password(password: str) -> None:
    problem = password_problem(password)
    if not problem and password.lower() in KNOWN_WEAK_PASSWORDS:
        problem = "Bu şifre çok yaygın, lütfen başka bir şifre seçin"
    if problem:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=problem)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8")[:72], hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def _password_fingerprint(user: User) -> str:
    return hashlib.sha256((user.hashed_password or "").encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Token işlemleri
# ---------------------------------------------------------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, user: Optional[User] = None) -> str:
    to_encode = data.copy()
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    if user is not None:
        to_encode["ph"] = _password_fingerprint(user)
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _credentials_exception(detail: str = "Oturum geçersiz, lütfen tekrar giriş yapın") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def user_from_token(token: Optional[str], db: Session) -> User:
    if not token:
        raise _credentials_exception("Giriş yapmanız gerekiyor")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise _credentials_exception()

    user = db.get(User, user_id)
    if user is None:
        raise _credentials_exception()
    if "ph" in payload and payload["ph"] != _password_fingerprint(user):
        raise _credentials_exception("Şifreniz değiştirildi, lütfen tekrar giriş yapın")
    if not user.is_active:
        raise _credentials_exception("Hesabınız devre dışı bırakılmış")
    return user


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    return user_from_token(credentials.credentials if credentials else None, db)


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bu işlem için yönetici yetkisi gereklidir")
    return current_user


# ---------------------------------------------------------------------------
# Depo erişim kuralları
#   - Yönetici her şeyi görür.
#   - Kullanıcı yalnızca kendisine yetki verilen depoları ve
#     herhangi bir depoya atanmamış (genel) ürünleri görür.
# ---------------------------------------------------------------------------
def accessible_warehouse_ids(user: User) -> list:
    return [w.id for w in user.warehouses]


def can_access_warehouse(user: User, warehouse_id: Optional[int]) -> bool:
    if user.role == "admin" or warehouse_id is None:
        return True
    return warehouse_id in accessible_warehouse_ids(user)


def apply_product_access(query, user: User):
    """Ürün sorgusuna kullanıcının erişebileceği depolar filtresini ekler."""
    if user.role == "admin":
        return query
    ids = accessible_warehouse_ids(user)
    if ids:
        return query.filter(or_(Product.warehouse_id.in_(ids), Product.warehouse_id.is_(None)))
    return query.filter(Product.warehouse_id.is_(None))


# ---------------------------------------------------------------------------
# Kaba kuvvet (brute-force) koruması: 15 dakikada 10 hatalı deneme
# ---------------------------------------------------------------------------
class LoginLimiter:
    def __init__(self, max_attempts: int = 10, window_seconds: int = 15 * 60):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._fails: dict = {}
        self._lock = threading.Lock()

    def _key(self, request: Request, email: str) -> str:
        ip = request.client.host if request.client else "?"
        return f"{ip}|{(email or '').lower()}"

    def check(self, request: Request, email: str) -> None:
        key = self._key(request, email)
        now = time.time()
        with self._lock:
            attempts = [t for t in self._fails.get(key, []) if now - t < self.window]
            self._fails[key] = attempts
            if len(attempts) >= self.max_attempts:
                wait = int(self.window - (now - attempts[0])) // 60 + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Çok fazla hatalı giriş denemesi. Lütfen {wait} dakika sonra tekrar deneyin.",
                )

    def fail(self, request: Request, email: str) -> None:
        with self._lock:
            self._fails.setdefault(self._key(request, email), []).append(time.time())

    def success(self, request: Request, email: str) -> None:
        with self._lock:
            self._fails.pop(self._key(request, email), None)

    def reset(self) -> None:
        with self._lock:
            self._fails.clear()


login_limiter = LoginLimiter()
