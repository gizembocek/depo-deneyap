from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Table, Float, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from database import Base


# --- Enum Definitions ---
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class ProductCategory(str, enum.Enum):
    SARF = "Sarf Malzemesi"
    GENEL = "Genel / Dayanıklı Malzeme"
    ELEKTRONIK = "Elektronik Bileşen"


class ProductStatus(str, enum.Enum):
    CALISAN = "Çalışan"
    BOZUK = "Bozuk / Kırık"
    GARANTIDE = "Garantide"
    DEMIRBAS_DUSULECEK = "Demirbaştan düşülecek"
    KIRIK_KUTUSUNDA = "Kırık ürün kutusunda"

# --- YENİ EKLENEN SINIF BURAYA GELİYOR ---
class ShipmentType(str, enum.Enum):
    GIRIS = "Giriş"
    CIKIS = "Çıkış"



# --- Association Tables ---
product_courses = Table(
    'product_courses',
    Base.metadata,
    Column('product_id', Integer, ForeignKey('products.id', ondelete='CASCADE'), primary_key=True),
    Column('course_id', Integer, ForeignKey('courses.id', ondelete='CASCADE'), primary_key=True)
)

user_warehouse_access = Table(
    'user_warehouse_access',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('warehouse_id', Integer, ForeignKey('warehouses.id', ondelete='CASCADE'), primary_key=True)
)


# --- Models ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default=UserRole.USER.value, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    warehouses = relationship("Warehouse", secondary=user_warehouse_access, back_populates="users")
    stock_logs = relationship("StockLog", back_populates="user")


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("User", secondary=user_warehouse_access, back_populates="warehouses")
    cabinets = relationship("Cabinet", back_populates="warehouse", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="warehouse", cascade="all, delete-orphan")


class Cabinet(Base):
    __tablename__ = "cabinets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)

    warehouse = relationship("Warehouse", back_populates="cabinets")
    shelves = relationship("Shelf", back_populates="cabinet", cascade="all, delete-orphan")


class Shelf(Base):
    __tablename__ = "shelves"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    cabinet_id = Column(Integer, ForeignKey("cabinets.id", ondelete="CASCADE"), nullable=False)

    cabinet = relationship("Cabinet", back_populates="shelves")
    compartments = relationship("Compartment", back_populates="shelf", cascade="all, delete-orphan")


class Compartment(Base):
    __tablename__ = "compartments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    shelf_id = Column(Integer, ForeignKey("shelves.id", ondelete="CASCADE"), nullable=False)

    shelf = relationship("Shelf", back_populates="compartments")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)

    products = relationship("Product", secondary=product_courses, back_populates="courses")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    category = Column(String(50), default=ProductCategory.GENEL.value)
    status = Column(String(50), default=ProductStatus.CALISAN.value)
    
    # Stock info
    current_stock = Column(Integer, default=0)
    critical_stock = Column(Integer, default=5)
    ideal_stock = Column(Integer, default=100)
    
    # Location
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=True)
    cabinet_id = Column(Integer, ForeignKey("cabinets.id", ondelete="SET NULL"), nullable=True)
    shelf_id = Column(Integer, ForeignKey("shelves.id", ondelete="SET NULL"), nullable=True)
    compartment_id = Column(Integer, ForeignKey("compartments.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    warehouse = relationship("Warehouse", back_populates="products")
    cabinet = relationship("Cabinet")
    shelf = relationship("Shelf")
    compartment = relationship("Compartment")
    courses = relationship("Course", secondary=product_courses, back_populates="products")
    stock_logs = relationship("StockLog", back_populates="product", cascade="all, delete-orphan")


class StockLog(Base):
    __tablename__ = "stock_logs"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False)  # "add", "remove", "set", "status_change"
    quantity_change = Column(Integer, default=0)
    previous_value = Column(String(255), nullable=True)
    new_value = Column(String(255), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="stock_logs")
    user = relationship("User", back_populates="stock_logs")


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    shipment_type = Column(String(50), default=ShipmentType.CIKIS.value)
    reason = Column(String(255), nullable=True)
    invoice_image_url = Column(String(500), nullable=True)
    cargo_image_url = Column(String(500), nullable=True)
    shipment_date = Column(DateTime, nullable=True)
    check_date = Column(DateTime, nullable=True)
    status = Column(String(50), default="pending")  # pending, shipped, checked
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("ShipmentItem", back_populates="shipment", cascade="all, delete-orphan")
    creator = relationship("User")
    outgoing_reason = Column(String(255), nullable=True)
    arrival_image_url = Column(String(500), nullable=True)
    visual_image_url = Column(String(500), nullable=True)


class ShipmentItem(Base):
    __tablename__ = "shipment_items"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    expected_quantity = Column(Integer, default=0)
    actual_quantity = Column(Integer, nullable=True)
    status = Column(String(50), default="pending")  # pending, complete, missing, extra

    shipment = relationship("Shipment", back_populates="items")
    product = relationship("Product")
    
