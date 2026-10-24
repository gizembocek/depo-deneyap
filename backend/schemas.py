from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from models import CATEGORY_VALUES, ROLE_VALUES, STATUS_VALUES

MAX_IMAGE_DATA_URL = 6 * 1024 * 1024  # base64 görsel için ~4.5 MB dosya


def _clean_required(value: Optional[str], field_label: str, max_len: int = 255) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError(f"{field_label} boş olamaz")
    if len(value) > max_len:
        raise ValueError(f"{field_label} en fazla {max_len} karakter olabilir")
    return value


def _clean_optional(value: Optional[str], max_len: Optional[int] = None) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    if max_len and len(value) > max_len:
        raise ValueError(f"En fazla {max_len} karakter girilebilir")
    return value or None


# --- Auth Schemas ---
class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "user"

    @field_validator("full_name")
    @classmethod
    def _name(cls, v):
        return _clean_required(v, "Ad soyad")

    @field_validator("role")
    @classmethod
    def _role(cls, v):
        if v not in ROLE_VALUES:
            raise ValueError("Rol 'admin' veya 'user' olmalıdır")
        return v


class SetupRequest(BaseModel):
    """İlk kurulum: atölye bilgileri + ilk yönetici hesabı."""
    atolye_adi: str
    il: Optional[str] = None
    full_name: str
    email: EmailStr
    password: str
    standart_dersler: bool = True

    @field_validator("atolye_adi")
    @classmethod
    def _atolye(cls, v):
        return _clean_required(v, "Atölye adı")

    @field_validator("full_name")
    @classmethod
    def _name(cls, v):
        return _clean_required(v, "Ad soyad")

    @field_validator("il")
    @classmethod
    def _il(cls, v):
        return _clean_optional(v, 100)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("full_name")
    @classmethod
    def _name(cls, v):
        return None if v is None else _clean_required(v, "Ad soyad")

    @field_validator("role")
    @classmethod
    def _role(cls, v):
        if v is not None and v not in ROLE_VALUES:
            raise ValueError("Rol 'admin' veya 'user' olmalıdır")
        return v


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class PasswordReset(BaseModel):
    new_password: str


class WarehouseAccessUpdate(BaseModel):
    warehouse_ids: List[int] = []


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: Optional[datetime] = None
    warehouse_ids: List[int] = []


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse
    must_change_password: bool = False


# --- Settings ---
class SettingsUpdate(BaseModel):
    atolye_adi: Optional[str] = None
    il: Optional[str] = None

    @field_validator("atolye_adi")
    @classmethod
    def _atolye(cls, v):
        return None if v is None else _clean_required(v, "Atölye adı")

    @field_validator("il")
    @classmethod
    def _il(cls, v):
        return _clean_optional(v, 100)


# --- Warehouse Schemas ---
class WarehouseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    location: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _name(cls, v):
        return _clean_required(v, "Depo adı")

    @field_validator("description")
    @classmethod
    def _desc(cls, v):
        return _clean_optional(v, 2000)

    @field_validator("location")
    @classmethod
    def _loc(cls, v):
        return _clean_optional(v, 255)


class WarehouseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _name(cls, v):
        return None if v is None else _clean_required(v, "Depo adı")

    @field_validator("description", "location")
    @classmethod
    def _opt(cls, v):
        # Boş metin gönderilirse alan temizlenir
        return None if v is None else v.strip()


class WarehouseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    created_at: Optional[datetime] = None
    product_count: int = 0


# --- Cabinet/Shelf/Compartment Schemas ---
class _NamedLocation(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def _name(cls, v):
        return _clean_required(v, "Ad")


class CabinetCreate(_NamedLocation):
    warehouse_id: int


class LocationRename(_NamedLocation):
    pass


class CabinetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    warehouse_id: int


class ShelfCreate(_NamedLocation):
    cabinet_id: int


class ShelfResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    cabinet_id: int


class CompartmentCreate(_NamedLocation):
    shelf_id: int


class CompartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    shelf_id: int


# --- Course Schemas ---
class CourseCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def _name(cls, v):
        return _clean_required(v, "Ders adı")


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    product_count: Optional[int] = None


# --- Product Schemas ---
def _check_category(v):
    if v is not None and v not in CATEGORY_VALUES:
        raise ValueError("Geçersiz kategori. Seçenekler: " + ", ".join(CATEGORY_VALUES))
    return v


def _check_status(v):
    if v is not None and v not in STATUS_VALUES:
        raise ValueError("Geçersiz durum. Seçenekler: " + ", ".join(STATUS_VALUES))
    return v


def _check_image(v):
    if v is None or v == "":
        return None
    if len(v) > MAX_IMAGE_DATA_URL:
        raise ValueError("Görsel çok büyük (en fazla ~4 MB)")
    if v.startswith("data:") and not v.startswith("data:image/"):
        raise ValueError("Yalnızca görsel dosyaları eklenebilir")
    if v.lower().startswith("javascript:"):
        raise ValueError("Geçersiz görsel adresi")
    return v


class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    category: str = "Genel / Dayanıklı Malzeme"
    status: str = "Çalışan"
    current_stock: int = Field(0, ge=0, le=10_000_000)
    critical_stock: int = Field(5, ge=0, le=10_000_000)
    ideal_stock: int = Field(100, ge=0, le=10_000_000)
    warehouse_id: Optional[int] = None
    cabinet_id: Optional[int] = None
    shelf_id: Optional[int] = None
    compartment_id: Optional[int] = None
    course_ids: List[int] = []

    @field_validator("name")
    @classmethod
    def _name(cls, v):
        return _clean_required(v, "Ürün adı")

    @field_validator("description")
    @classmethod
    def _desc(cls, v):
        return _clean_optional(v, 4000)

    @field_validator("category")
    @classmethod
    def _cat(cls, v):
        return _check_category(v)

    @field_validator("status")
    @classmethod
    def _sta(cls, v):
        return _check_status(v)

    @field_validator("image_url")
    @classmethod
    def _img(cls, v):
        return _check_image(v)


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    current_stock: Optional[int] = Field(None, ge=0, le=10_000_000)
    critical_stock: Optional[int] = Field(None, ge=0, le=10_000_000)
    ideal_stock: Optional[int] = Field(None, ge=0, le=10_000_000)
    warehouse_id: Optional[int] = None
    cabinet_id: Optional[int] = None
    shelf_id: Optional[int] = None
    compartment_id: Optional[int] = None
    course_ids: Optional[List[int]] = None

    @field_validator("name")
    @classmethod
    def _name(cls, v):
        return None if v is None else _clean_required(v, "Ürün adı")

    @field_validator("description")
    @classmethod
    def _desc(cls, v):
        return None if v is None else (v.strip() if len(v) <= 4000 else _clean_optional(v, 4000))

    @field_validator("category")
    @classmethod
    def _cat(cls, v):
        return _check_category(v)

    @field_validator("status")
    @classmethod
    def _sta(cls, v):
        return _check_status(v)

    @field_validator("image_url")
    @classmethod
    def _img(cls, v):
        return _check_image(v)


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    category: str
    status: str
    current_stock: int
    critical_stock: int
    ideal_stock: int
    warehouse_id: Optional[int] = None
    cabinet_id: Optional[int] = None
    shelf_id: Optional[int] = None
    compartment_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    courses: List[CourseResponse] = []
    warehouse_name: Optional[str] = None
    cabinet_name: Optional[str] = None
    shelf_name: Optional[str] = None
    compartment_name: Optional[str] = None


# --- Stock Log Schemas ---
class StockLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    user_id: Optional[int] = None
    action: str
    quantity_change: int
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    user_name: Optional[str] = None
    product_name: Optional[str] = None


# --- Shipment Schemas ---
class ShipmentTypeSchema(str, Enum):
    GIRIS = "Giriş"
    CIKIS = "Çıkış"


class ShipmentItemCreate(BaseModel):
    product_id: int
    expected_quantity: int = Field(1, ge=1, le=10_000_000)
    actual_quantity: Optional[int] = Field(None, ge=0, le=10_000_000)


class ShipmentCreate(BaseModel):
    name: str
    shipment_type: ShipmentTypeSchema = ShipmentTypeSchema.CIKIS
    outgoing_reason: Optional[str] = None
    arrival_image_url: Optional[str] = None
    visual_image_url: Optional[str] = None
    invoice_image_url: Optional[str] = None
    shipment_date: Optional[datetime] = None
    check_date: Optional[datetime] = None
    notes: Optional[str] = None
    items: List[ShipmentItemCreate] = []

    @field_validator("name")
    @classmethod
    def _name(cls, v):
        return _clean_required(v, "İşlem adı")

    @field_validator("outgoing_reason")
    @classmethod
    def _reason(cls, v):
        return _clean_optional(v, 255)

    @field_validator("notes")
    @classmethod
    def _notes(cls, v):
        return _clean_optional(v, 4000)

    @field_validator("items")
    @classmethod
    def _items(cls, v):
        if not v:
            raise ValueError("En az bir ürün eklemelisiniz")
        if len(v) > 500:
            raise ValueError("Bir işlemde en fazla 500 satır olabilir")
        return v

    @field_validator("arrival_image_url", "visual_image_url", "invoice_image_url")
    @classmethod
    def _images(cls, v):
        return _check_image(v)


class ShipmentCheckItem(BaseModel):
    item_id: int
    actual_quantity: int = Field(..., ge=0, le=10_000_000)


class ShipmentItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    expected_quantity: int
    actual_quantity: Optional[int] = None
    status: str
    product_name: Optional[str] = None


class ShipmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    shipment_type: str
    outgoing_reason: Optional[str] = None
    arrival_image_url: Optional[str] = None
    visual_image_url: Optional[str] = None
    invoice_image_url: Optional[str] = None
    has_arrival_image: bool = False
    has_visual_image: bool = False
    has_invoice_image: bool = False
    shipment_date: Optional[datetime] = None
    check_date: Optional[datetime] = None
    status: str
    notes: Optional[str] = None
    created_by: Optional[int] = None
    creator_name: Optional[str] = None
    created_at: Optional[datetime] = None
    items: List[ShipmentItemResponse] = []


# --- Stock Update ---
class StockAction(str, Enum):
    ADD = "add"
    REMOVE = "remove"
    SET = "set"


class StockUpdate(BaseModel):
    action: StockAction
    quantity: int = Field(..., ge=0, le=10_000_000)
    note: Optional[str] = None

    @field_validator("note")
    @classmethod
    def _note(cls, v):
        return _clean_optional(v, 1000)
