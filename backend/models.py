import os

from sqlalchemy import (
    Column, Integer, Unicode, UnicodeText, DateTime, Boolean, ForeignKey, Table, event
)
from sqlalchemy.dialects.mssql import DATETIME2, NVARCHAR as MSSQL_NVARCHAR
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from database import Base


# ---------------------------------------------------------------------------
# Tip notları (SQLite -> SQL Server geçişi)
#
#   String    -> Unicode      : SQL Server'da VARCHAR yerine NVARCHAR üretir.
#                               Türkçe karakterler bozulmadan saklanır.
#   Text      -> UTEXT         : SQL Server'da NVARCHAR(MAX). Düz UnicodeText
#                               kullanılsaydı kullanımdan kalkmış NTEXT üretirdi.
#   DateTime  -> DT            : SQL Server'da DATETIME2(6), diğerlerinde
#                               normal DATETIME. Mikrosaniye hassasiyeti korunur.
#
# with_variant sayesinde SQLite'a geri dönmek istersen hiçbir şey değişmiyor.
# ---------------------------------------------------------------------------
DT = DateTime().with_variant(DATETIME2(precision=6), "mssql")
UTEXT = UnicodeText().with_variant(MSSQL_NVARCHAR(None), "mssql")


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


class ShipmentType(str, enum.Enum):
    GIRIS = "Giriş"
    CIKIS = "Çıkış"


# Formlarda ve doğrulamada kullanılan sabit listeler
CATEGORY_VALUES = [c.value for c in ProductCategory]
STATUS_VALUES = [s.value for s in ProductStatus]
ROLE_VALUES = [r.value for r in UserRole]


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
    email = Column(Unicode(255), unique=True, index=True, nullable=False)
    full_name = Column(Unicode(255), nullable=False)
    hashed_password = Column(Unicode(255), nullable=False)
    role = Column(Unicode(20), default=UserRole.USER.value, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DT, default=datetime.utcnow)
    updated_at = Column(DT, default=datetime.utcnow, onupdate=datetime.utcnow)

    warehouses = relationship("Warehouse", secondary=user_warehouse_access, back_populates="users")
    stock_logs = relationship("StockLog", back_populates="user")


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Unicode(255), nullable=False)
    description = Column(UTEXT, nullable=True)
    location = Column(Unicode(255), nullable=True)
    created_at = Column(DT, default=datetime.utcnow)
    updated_at = Column(DT, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("User", secondary=user_warehouse_access, back_populates="warehouses")
    cabinets = relationship("Cabinet", back_populates="warehouse", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="warehouse", cascade="all, delete-orphan")


class Cabinet(Base):
    __tablename__ = "cabinets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Unicode(255), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)

    warehouse = relationship("Warehouse", back_populates="cabinets")
    shelves = relationship("Shelf", back_populates="cabinet", cascade="all, delete-orphan")
    # Dolap silinince içindeki ürünlerin konumu boşalsın. SQL Server'da çoklu
    # cascade yolu yasak olduğundan bu işlem ORM seviyesinde (FK = NULL) yapılır.
    products = relationship("Product", back_populates="cabinet")


class Shelf(Base):
    __tablename__ = "shelves"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Unicode(255), nullable=False)
    cabinet_id = Column(Integer, ForeignKey("cabinets.id", ondelete="CASCADE"), nullable=False)

    cabinet = relationship("Cabinet", back_populates="shelves")
    compartments = relationship("Compartment", back_populates="shelf", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="shelf")


class Compartment(Base):
    __tablename__ = "compartments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Unicode(255), nullable=False)
    shelf_id = Column(Integer, ForeignKey("shelves.id", ondelete="CASCADE"), nullable=False)

    shelf = relationship("Shelf", back_populates="compartments")
    products = relationship("Product", back_populates="compartment")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Unicode(255), unique=True, nullable=False)

    products = relationship("Product", secondary=product_courses, back_populates="courses")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Unicode(255), nullable=False, index=True)
    description = Column(UTEXT, nullable=True)
    # base64 data-URL tutulabildiği için uzunluk sınırı yok
    image_url = Column(UTEXT, nullable=True)
    category = Column(Unicode(50), default=ProductCategory.GENEL.value)
    status = Column(Unicode(50), default=ProductStatus.CALISAN.value)

    # Stock info
    current_stock = Column(Integer, default=0)
    critical_stock = Column(Integer, default=5)
    ideal_stock = Column(Integer, default=100)

    # Location
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=True)
    cabinet_id = Column(Integer, ForeignKey("cabinets.id", ondelete="SET NULL"), nullable=True)
    shelf_id = Column(Integer, ForeignKey("shelves.id", ondelete="SET NULL"), nullable=True)
    compartment_id = Column(Integer, ForeignKey("compartments.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DT, default=datetime.utcnow)
    updated_at = Column(DT, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    warehouse = relationship("Warehouse", back_populates="products")
    cabinet = relationship("Cabinet", back_populates="products")
    shelf = relationship("Shelf", back_populates="products")
    compartment = relationship("Compartment", back_populates="products")
    courses = relationship("Course", secondary=product_courses, back_populates="products")
    stock_logs = relationship("StockLog", back_populates="product", cascade="all, delete-orphan")


class StockLog(Base):
    __tablename__ = "stock_logs"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(Unicode(50), nullable=False)  # "add", "remove", "set", "status_change"
    quantity_change = Column(Integer, default=0)
    previous_value = Column(Unicode(255), nullable=True)
    new_value = Column(Unicode(255), nullable=True)
    note = Column(UTEXT, nullable=True)
    created_at = Column(DT, default=datetime.utcnow)

    product = relationship("Product", back_populates="stock_logs")
    user = relationship("User", back_populates="stock_logs")


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Unicode(255), nullable=False)
    shipment_type = Column(Unicode(50), default=ShipmentType.CIKIS.value)
    reason = Column(Unicode(255), nullable=True)
    # Bu dört alan base64 görsel tutuyor (184 KB'a kadar görüldü) — sınırsız olmalı
    invoice_image_url = Column(UTEXT, nullable=True)
    cargo_image_url = Column(UTEXT, nullable=True)
    shipment_date = Column(DT, nullable=True)
    check_date = Column(DT, nullable=True)
    status = Column(Unicode(50), default="pending")  # pending, shipped, checked
    notes = Column(UTEXT, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DT, default=datetime.utcnow)
    updated_at = Column(DT, default=datetime.utcnow, onupdate=datetime.utcnow)

    outgoing_reason = Column(Unicode(255), nullable=True)
    arrival_image_url = Column(UTEXT, nullable=True)
    visual_image_url = Column(UTEXT, nullable=True)

    items = relationship("ShipmentItem", back_populates="shipment", cascade="all, delete-orphan")
    creator = relationship("User")


class ShipmentItem(Base):
    __tablename__ = "shipment_items"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    expected_quantity = Column(Integer, default=0)
    actual_quantity = Column(Integer, nullable=True)
    status = Column(Unicode(50), default="pending")  # pending, complete, missing, extra

    shipment = relationship("Shipment", back_populates="items")
    product = relationship("Product")


class AppSetting(Base):
    """Atölyeye özel ayarlar (atölye adı, il vb.). Anahtar/değer olarak tutulur."""
    __tablename__ = "app_settings"

    key = Column(Unicode(100), primary_key=True)
    value = Column(UTEXT, nullable=True)
    updated_at = Column(DT, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# SQL Server uyumluluğu: zincirleme silme (ON DELETE CASCADE / SET NULL)
#
# SQL Server, bir tabloya birden fazla zincirleme silme yolu olan yabancı
# anahtarları reddeder (hata 1785 "multiple cascade paths"). Örn. products
# tablosuna warehouses'tan hem doğrudan hem dolaplar (cabinets) üzerinden yol var.
# Bu yüzden SQL Server'da tablolar zincirleme kural OLMADAN (NO ACTION) oluşturulur;
# bağlı kayıtları uygulama (ORM ve router'lardaki açık silmeler) temizler.
# DB_FK_NO_ACTION=1 ile aynı davranış SQLite'ta da denenebilir (testler bunu kullanır).
# ---------------------------------------------------------------------------
@event.listens_for(Base.metadata, "before_create")
def _fk_actions_for_dialect(target, connection, **kw):
    if connection.dialect.name == "mssql" or os.getenv("DB_FK_NO_ACTION") == "1":
        for table in target.tables.values():
            for fk in table.foreign_keys:
                fk.ondelete = None
                if fk.constraint is not None:
                    fk.constraint.ondelete = None
