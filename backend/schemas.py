from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum

# --- Auth Schemas ---
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "user"

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    warehouse_ids: List[int] = []

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# --- Warehouse Schemas ---
class WarehouseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    location: Optional[str] = None

class WarehouseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None

class WarehouseResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- Cabinet/Shelf/Compartment Schemas ---
class CabinetCreate(BaseModel):
    name: str
    warehouse_id: int

class CabinetResponse(BaseModel):
    id: int
    name: str
    warehouse_id: int

    class Config:
        from_attributes = True

class ShelfCreate(BaseModel):
    name: str
    cabinet_id: int

class ShelfResponse(BaseModel):
    id: int
    name: str
    cabinet_id: int

    class Config:
        from_attributes = True

class CompartmentCreate(BaseModel):
    name: str
    shelf_id: int

class CompartmentResponse(BaseModel):
    id: int
    name: str
    shelf_id: int

    class Config:
        from_attributes = True

# --- Course Schemas ---
class CourseCreate(BaseModel):
    name: str

class CourseResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

# --- Product Schemas ---
class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    category: str = "Genel / Dayanıklı Malzeme"
    status: str = "Çalışan"
    current_stock: int = 0
    critical_stock: int = 5
    ideal_stock: int = 100
    warehouse_id: Optional[int] = None
    cabinet_id: Optional[int] = None
    shelf_id: Optional[int] = None
    compartment_id: Optional[int] = None
    course_ids: List[int] = []

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    current_stock: Optional[int] = None
    critical_stock: Optional[int] = None
    ideal_stock: Optional[int] = None
    warehouse_id: Optional[int] = None
    cabinet_id: Optional[int] = None
    shelf_id: Optional[int] = None
    compartment_id: Optional[int] = None
    course_ids: Optional[List[int]] = None

class ProductResponse(BaseModel):
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
    created_at: datetime
    updated_at: datetime
    courses: List[CourseResponse] = []
    warehouse_name: Optional[str] = None
    cabinet_name: Optional[str] = None
    shelf_name: Optional[str] = None
    compartment_name: Optional[str] = None

    class Config:
        from_attributes = True

# --- Stock Log Schemas ---
class StockLogCreate(BaseModel):
    action: str
    quantity_change: int = 0
    note: Optional[str] = None

class StockLogResponse(BaseModel):
    id: int
    product_id: int
    user_id: Optional[int] = None
    action: str
    quantity_change: int
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime
    user_name: Optional[str] = None
    product_name: Optional[str] = None

    class Config:
        from_attributes = True

# --- Shipment Schemas (MODEL UYUMLU) ---

class ShipmentTypeSchema(str, Enum):
    GIRIS = "Giriş"
    CIKIS = "Çıkış"
    
class ShipmentItemCreate(BaseModel):
    product_id: int
    expected_quantity: int = 1
    actual_quantity: Optional[int] = None

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

class ShipmentItemResponse(BaseModel):
    id: int
    product_id: int
    expected_quantity: int
    actual_quantity: Optional[int] = None
    status: str
    product_name: Optional[str] = None

    class Config:
        from_attributes = True

class ShipmentResponse(BaseModel):
    id: int
    name: str
    shipment_type: ShipmentTypeSchema
    outgoing_reason: Optional[str] = None
    arrival_image_url: Optional[str] = None
    visual_image_url: Optional[str] = None
    invoice_image_url: Optional[str] = None
    shipment_date: Optional[datetime] = None
    check_date: Optional[datetime] = None
    status: str
    notes: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    items: List[ShipmentItemResponse] = []

    class Config:
        from_attributes = True

# --- Stock Update ---
class StockUpdate(BaseModel):
    action: str  # "add", "remove", "set"
    quantity: int
    note: Optional[str] = None
