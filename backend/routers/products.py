import io
import os
import uuid
from datetime import timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, selectinload

from auth import apply_product_access, can_access_warehouse, get_admin_user, get_current_user
from database import contains_text, fold_value, folded, get_db, tr_ordered, tr_sort_key
from excel_import import build_template, course_key, parse_workbook
from models import (
    CATEGORY_VALUES, Cabinet, Compartment, Course, Product, Shelf, ShipmentItem,
    StockLog, User, Warehouse, product_courses,
)
from schemas import CourseResponse, ProductCreate, ProductResponse, ProductUpdate, StockUpdate

router = APIRouter(prefix="/api/products", tags=["Products"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_EXCEL_BYTES = 15 * 1024 * 1024
MAX_IMAGE_SIDE = 1600

SORT_OPTIONS = {
    "newest": [Product.id.desc()],
    "oldest": [Product.id.asc()],
    "name": [tr_ordered(Product.name).asc(), Product.id.asc()],
    "stock_asc": [Product.current_stock.asc(), Product.id.asc()],
    "stock_desc": [Product.current_stock.desc(), Product.id.asc()],
}


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------
def product_to_response(product: Product) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        name=product.name,
        description=product.description,
        image_url=product.image_url,
        category=product.category or "Genel / Dayanıklı Malzeme",
        status=product.status or "Çalışan",
        current_stock=product.current_stock or 0,
        critical_stock=product.critical_stock if product.critical_stock is not None else 0,
        ideal_stock=product.ideal_stock if product.ideal_stock is not None else 0,
        warehouse_id=product.warehouse_id,
        cabinet_id=product.cabinet_id,
        shelf_id=product.shelf_id,
        compartment_id=product.compartment_id,
        created_at=product.created_at,
        updated_at=product.updated_at,
        courses=[CourseResponse(id=c.id, name=c.name) for c in sorted(product.courses, key=lambda c: tr_sort_key(c.name))],
        warehouse_name=product.warehouse.name if product.warehouse else None,
        cabinet_name=product.cabinet.name if product.cabinet else None,
        shelf_name=product.shelf.name if product.shelf else None,
        compartment_name=product.compartment.name if product.compartment else None,
    )


def _loaded_query(db: Session):
    # Koleksiyonlar (dersler) ayrı sorguyla yüklenir; böylece sayfalama satırları bozulmaz.
    return db.query(Product).options(
        selectinload(Product.courses),
        joinedload(Product.warehouse),
        joinedload(Product.cabinet),
        joinedload(Product.shelf),
        joinedload(Product.compartment),
    )


def apply_product_filters(query, *, search=None, category=None, status=None, warehouse_id=None,
                          course_id=None, low_stock=None):
    if search and search.strip():
        term = fold_value(search.strip())
        query = query.filter(or_(
            contains_text(folded(Product.name), term),
            contains_text(folded(Product.description), term),
        ))
    if category and category != "Tümü":
        query = query.filter(Product.category == category)
    if status:
        query = query.filter(Product.status == status)
    if warehouse_id:
        query = query.filter(Product.warehouse_id == warehouse_id)
    if course_id:
        query = query.filter(Product.courses.any(Course.id == course_id))
    if low_stock:
        query = query.filter(Product.current_stock <= Product.critical_stock)
    return query


def _get_product_or_404(db: Session, product_id: int, loaded: bool = False) -> Product:
    q = _loaded_query(db) if loaded else db.query(Product)
    product = q.filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
    return product


def _check_access(user: User, product: Product, action: str = "görüntülemek") -> None:
    if not can_access_warehouse(user, product.warehouse_id):
        raise HTTPException(status_code=403, detail=f"Bu ürünü {action} için depoya erişim yetkiniz yok")


def resolve_location(db: Session, warehouse_id, cabinet_id, shelf_id, compartment_id):
    """Depo > Dolap > Raf > Bölme seçiminin birbiriyle tutarlı olduğunu doğrular."""
    if warehouse_id is not None and not db.get(Warehouse, warehouse_id):
        raise HTTPException(status_code=400, detail="Seçilen depo bulunamadı")
    if cabinet_id is not None:
        cabinet = db.get(Cabinet, cabinet_id)
        if not cabinet or cabinet.warehouse_id != warehouse_id:
            raise HTTPException(status_code=400, detail="Seçilen dolap bu depoya ait değil")
    if shelf_id is not None:
        shelf = db.get(Shelf, shelf_id)
        if cabinet_id is None or not shelf or shelf.cabinet_id != cabinet_id:
            raise HTTPException(status_code=400, detail="Seçilen raf bu dolaba ait değil")
    if compartment_id is not None:
        comp = db.get(Compartment, compartment_id)
        if shelf_id is None or not comp or comp.shelf_id != shelf_id:
            raise HTTPException(status_code=400, detail="Seçilen bölme bu rafa ait değil")
    return warehouse_id, cabinet_id, shelf_id, compartment_id


def _ensure_unique_name(db: Session, name: str, warehouse_id, exclude_id: Optional[int] = None):
    q = db.query(Product.id).filter(folded(Product.name) == fold_value(name))
    q = q.filter(Product.warehouse_id.is_(None)) if warehouse_id is None else q.filter(Product.warehouse_id == warehouse_id)
    if exclude_id is not None:
        q = q.filter(Product.id != exclude_id)
    if q.first():
        raise HTTPException(status_code=400, detail="Bu depoda aynı isimde bir ürün zaten mevcut")


def _courses_by_ids(db: Session, ids: List[int]) -> List[Course]:
    ids = sorted(set(ids or []))
    if not ids:
        return []
    courses = db.query(Course).filter(Course.id.in_(ids)).all()
    if len(courses) != len(ids):
        raise HTTPException(status_code=400, detail="Seçilen derslerden biri bulunamadı")
    return courses


def _log(db: Session, product: Product, user: User, action: str, change: int = 0,
         previous=None, new=None, note: Optional[str] = None) -> None:
    db.add(StockLog(
        product_id=product.id,
        user_id=user.id if user else None,
        action=action,
        quantity_change=change,
        previous_value=None if previous is None else str(previous),
        new_value=None if new is None else str(new),
        note=note,
    ))


# ---------------------------------------------------------------------------
# Listeleme
# ---------------------------------------------------------------------------
@router.get("/", response_model=List[ProductResponse])
def list_products(
    response: Response,
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    warehouse_id: Optional[int] = None,
    course_id: Optional[int] = None,
    low_stock: Optional[bool] = None,
    sort: str = "newest",
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = dict(search=search, category=category, status=status, warehouse_id=warehouse_id,
                   course_id=course_id, low_stock=low_stock)
    base = apply_product_filters(apply_product_access(db.query(Product), current_user), **filters)
    total = base.count()

    query = apply_product_filters(apply_product_access(_loaded_query(db), current_user), **filters)
    products = (query.order_by(*SORT_OPTIONS.get(sort, SORT_OPTIONS["newest"]))
                .offset((page - 1) * per_page).limit(per_page).all())

    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Per-Page"] = str(per_page)
    return [product_to_response(p) for p in products]


@router.get("/count")
def get_product_count(
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    warehouse_id: Optional[int] = None,
    course_id: Optional[int] = None,
    low_stock: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = apply_product_filters(
        apply_product_access(db.query(Product), current_user),
        search=search, category=category, status=status, warehouse_id=warehouse_id,
        course_id=course_id, low_stock=low_stock,
    )
    return {"count": query.count()}


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = apply_product_access(db.query(Product), current_user)
    return {
        "total_products": query.count(),
        "low_stock_count": query.filter(Product.current_stock <= Product.critical_stock).count(),
        "out_of_stock_count": query.filter(Product.current_stock <= 0).count(),
        "broken_count": query.filter(Product.status == "Bozuk / Kırık").count(),
        "categories": {cat: query.filter(Product.category == cat).count() for cat in CATEGORY_VALUES},
    }


# ---------------------------------------------------------------------------
# Excel (sabit yollar, /{product_id} yolundan önce tanımlanmalı)
# ---------------------------------------------------------------------------
@router.get("/import/template")
def download_import_template(current_user: User = Depends(get_current_user)):
    return StreamingResponse(
        io.BytesIO(build_template()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=deneyap_urun_sablonu.xlsx"},
    )


def _match_course(db: Session, name: str, cache: dict) -> Course:
    """Sayfa/ders adını mevcut derslerle eşleştirir; yoksa yeni ders açar.
    Excel sayfa adları 31 karakterle sınırlı olduğu için kısaltılmış adlar da eşleşir."""
    key = course_key(name)
    if key in cache:
        return cache[key]
    for course in db.query(Course).all():
        ck = course_key(course.name)
        if ck == key or (len(name.strip()) >= 28 and ck.startswith(key)):
            cache[key] = course
            return course
    course = Course(name=name.strip()[:255])
    db.add(course)
    db.flush()
    cache[key] = course
    return course


@router.post("/import/excel")
async def import_excel(
    file: UploadFile = File(...),
    warehouse_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Excel dosyasındaki tüm uygun sayfalardan ürünleri içe aktarır."""
    filename = (file.filename or "").lower()
    if filename.endswith(".xls"):
        raise HTTPException(status_code=400, detail="Eski .xls biçimi desteklenmiyor. Dosyayı Excel'de açıp 'Farklı Kaydet > .xlsx' ile kaydedip tekrar yükleyin.")
    if not filename.endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="Lütfen geçerli bir Excel dosyası yükleyin (.xlsx)")
    if warehouse_id is not None and not db.get(Warehouse, warehouse_id):
        raise HTTPException(status_code=400, detail="Seçilen depo bulunamadı")

    contents = await file.read()
    if len(contents) > MAX_EXCEL_BYTES:
        raise HTTPException(status_code=400, detail="Excel dosyası 15 MB'dan büyük olamaz")
    try:
        parsed = parse_workbook(contents)
    except Exception:
        raise HTTPException(status_code=400, detail="Excel dosyası okunamadı. Dosyanın bozuk veya şifreli olmadığından emin olun.")

    if not parsed.rows:
        raise HTTPException(
            status_code=400,
            detail="Excel dosyasında ürün bulunamadı. İlk 20 satırdan birinde 'Malzeme Adı' (veya 'Ürün Adı') başlıklı bir sütun olmalıdır. Şablonu indirip kullanabilirsiniz.",
        )

    # Depodaki mevcut ürünler (Türkçe harf duyarsız karşılaştırma)
    existing_q = db.query(Product).options(selectinload(Product.courses))
    existing_q = existing_q.filter(Product.warehouse_id.is_(None)) if warehouse_id is None else existing_q.filter(Product.warehouse_id == warehouse_id)
    existing = {fold_value(p.name): p for p in existing_q.all()}

    course_cache: dict = {}
    added = skipped = 0
    per_sheet: dict = {}
    new_products: List[Product] = []
    for row in parsed.rows:
        key = fold_value(row.name)
        courses = [_match_course(db, c, course_cache) for c in row.course_names]
        product = existing.get(key)
        if product is not None:
            for c in courses:
                if c not in product.courses:
                    product.courses.append(c)
            skipped += 1
            continue

        critical = row.critical_stock if row.critical_stock is not None else (10 if row.category == "Sarf Malzemesi" else 5)
        ideal = row.ideal_stock if row.ideal_stock is not None else (max(row.current_stock * 2, 10) if row.current_stock > 0 else 10)
        product = Product(
            name=row.name,
            description=row.description or f"Kaynak: {row.sheet}",
            category=row.category,
            status=row.status,
            current_stock=row.current_stock,
            critical_stock=critical,
            ideal_stock=ideal,
            warehouse_id=warehouse_id,
        )
        product.courses = list(dict.fromkeys(courses))
        db.add(product)
        existing[key] = product  # aynı dosyada tekrar eden satırlar ikinci kez eklenmesin
        new_products.append(product)
        added += 1
        per_sheet[row.sheet] = per_sheet.get(row.sheet, 0) + 1

    db.flush()  # yeni ürünlerin id'leri oluşsun
    for p in new_products:
        _log(db, p, current_user, "create", p.current_stock or 0, None, p.current_stock, "Excel'den içe aktarıldı")
    db.commit()

    return {
        "message": "İçe aktarma tamamlandı.",
        "added": added,
        "skipped": skipped,
        "sheets": [f"{name} ({count} ürün)" for name, count in per_sheet.items()],
        "skipped_sheets": parsed.skipped_sheets,
    }


@router.delete("/all")
def delete_all_products(
    warehouse_id: Optional[int] = None,
    unassigned: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Tüm ürünleri, yalnızca bir depodakileri veya depo atanmamış ürünleri siler (ilgili kayıtlarıyla)."""
    ids_q = db.query(Product.id)
    if unassigned:
        ids_q = ids_q.filter(Product.warehouse_id.is_(None))
    elif warehouse_id is not None:
        ids_q = ids_q.filter(Product.warehouse_id == warehouse_id)
    ids = [r[0] for r in ids_q.all()]
    if not ids:
        return {"message": "Silinecek ürün yok.", "deleted_products": 0, "deleted_logs": 0}

    log_count = 0
    for start in range(0, len(ids), 500):  # SQL Server parametre sınırı için parça parça
        chunk = ids[start:start + 500]
        log_count += db.query(StockLog).filter(StockLog.product_id.in_(chunk)).delete(synchronize_session=False)
        db.query(ShipmentItem).filter(ShipmentItem.product_id.in_(chunk)).delete(synchronize_session=False)
        db.execute(product_courses.delete().where(product_courses.c.product_id.in_(chunk)))
        db.query(Product).filter(Product.id.in_(chunk)).delete(synchronize_session=False)
    db.commit()
    return {
        "message": f"{len(ids)} ürün ve {log_count} stok kaydı silindi.",
        "deleted_products": len(ids),
        "deleted_logs": log_count,
    }


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...), current_user: User = Depends(get_admin_user)):
    """Görseli doğrular, gerekirse küçültür ve kaydeder. Dönen adres ürünün image_url alanına yazılır."""
    from PIL import Image, ImageOps, UnidentifiedImageError

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Dosya boş")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Dosya boyutu 5 MB'dan büyük olamaz")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(status_code=400, detail="Geçersiz görsel dosyası. PNG, JPG, GIF veya WEBP yükleyin.")
    if img.format not in {"PNG", "JPEG", "GIF", "WEBP", "MPO"}:
        raise HTTPException(status_code=400, detail="Geçersiz dosya formatı. PNG, JPG, GIF veya WEBP yükleyin.")

    img = ImageOps.exif_transpose(img)
    img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    out = io.BytesIO()
    if has_alpha:
        img.save(out, format="PNG", optimize=True)
        ext, content_type = ".png", "image/png"
    else:
        img.convert("RGB").save(out, format="JPEG", quality=85, optimize=True)
        ext, content_type = ".jpg", "image/jpeg"
    content = out.getvalue()

    # Supabase ayarlıysa oraya yükle (bulut kurulumu), değilse yerel klasöre kaydet
    try:
        from supabase_utils import upload_file_to_supabase
        url = await upload_file_to_supabase(content, f"{uuid.uuid4()}{ext}", content_type)
        if url:
            return {"url": url}
    except Exception as e:  # pragma: no cover - ağ hatası
        print(f"Supabase yüklemesi başarısız, yerel kayda geçiliyor: {e}")

    filename = f"{uuid.uuid4()}{ext}"
    with open(os.path.join(UPLOAD_DIR, filename), "wb") as f:
        f.write(content)
    return {"url": f"/uploads/{filename}"}


# ---------------------------------------------------------------------------
# Tekil ürün işlemleri
# ---------------------------------------------------------------------------
@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = _get_product_or_404(db, product_id, loaded=True)
    _check_access(current_user, product)
    return product_to_response(product)


@router.post("/", response_model=ProductResponse)
def create_product(product_data: ProductCreate, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    wh, cab, shelf, comp = resolve_location(db, product_data.warehouse_id, product_data.cabinet_id,
                                            product_data.shelf_id, product_data.compartment_id)
    _ensure_unique_name(db, product_data.name, wh)

    product = Product(
        name=product_data.name,
        description=product_data.description,
        image_url=product_data.image_url,
        category=product_data.category,
        status=product_data.status,
        current_stock=product_data.current_stock,
        critical_stock=product_data.critical_stock,
        ideal_stock=product_data.ideal_stock,
        warehouse_id=wh, cabinet_id=cab, shelf_id=shelf, compartment_id=comp,
    )
    product.courses = _courses_by_ids(db, product_data.course_ids)
    db.add(product)
    db.flush()
    _log(db, product, current_user, "create", product.current_stock, None, product.current_stock,
         f"Ürün oluşturuldu: {product.name}")
    db.commit()
    return product_to_response(_get_product_or_404(db, product.id, loaded=True))


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product_data: ProductUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    product = _get_product_or_404(db, product_id, loaded=True)
    fields = product_data.model_dump(exclude_unset=True, exclude={"course_ids"})

    # Konum: depo değiştiyse ve dolap belirtilmediyse alt konumlar temizlenir
    loc_keys = ("warehouse_id", "cabinet_id", "shelf_id", "compartment_id")
    if any(k in fields for k in loc_keys):
        wh = fields.get("warehouse_id", product.warehouse_id)
        if "warehouse_id" in fields and wh != product.warehouse_id and "cabinet_id" not in fields:
            cab = shelf = comp = None
        else:
            cab = fields.get("cabinet_id", product.cabinet_id)
            shelf = fields.get("shelf_id", product.shelf_id) if cab is not None else None
            comp = fields.get("compartment_id", product.compartment_id) if shelf is not None else None
        fields.update(zip(loc_keys, resolve_location(db, wh, cab, shelf, comp)))

    for required in ("name", "category", "status", "current_stock", "critical_stock", "ideal_stock"):
        if required in fields and fields[required] is None:
            fields.pop(required)

    new_name = fields.get("name", product.name)
    new_wh = fields.get("warehouse_id", product.warehouse_id)
    if fold_value(new_name) != fold_value(product.name) or new_wh != product.warehouse_id:
        _ensure_unique_name(db, new_name, new_wh, exclude_id=product.id)

    old_stock, old_status = product.current_stock, product.status
    for field_name, value in fields.items():
        setattr(product, field_name, value)

    if product_data.course_ids is not None:
        product.courses = _courses_by_ids(db, product_data.course_ids)

    if "current_stock" in fields and fields["current_stock"] != old_stock:
        _log(db, product, current_user, "set", fields["current_stock"] - (old_stock or 0), old_stock,
             fields["current_stock"], "Ürün düzenleme ekranından değiştirildi")
    if "status" in fields and fields["status"] != old_status:
        _log(db, product, current_user, "status_change", 0, old_status, fields["status"])

    db.commit()
    db.expire_all()
    return product_to_response(_get_product_or_404(db, product_id, loaded=True))


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    product = _get_product_or_404(db, product_id)
    db.query(ShipmentItem).filter(ShipmentItem.product_id == product.id).delete(synchronize_session=False)
    db.delete(product)
    db.commit()
    return {"message": "Ürün silindi"}


@router.post("/{product_id}/stock")
def update_stock(product_id: int, stock_data: StockUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = _get_product_or_404(db, product_id)
    _check_access(current_user, product, "güncellemek")

    previous = product.current_stock or 0
    qty = stock_data.quantity
    action = stock_data.action.value

    if action in ("add", "remove") and qty == 0:
        raise HTTPException(status_code=400, detail="Miktar 0'dan büyük olmalıdır")
    if action == "add":
        product.current_stock = previous + qty
        change = qty
    elif action == "remove":
        if qty > previous:
            raise HTTPException(status_code=400, detail=f"Yetersiz stok. Mevcut: {previous}, çıkarılmak istenen: {qty}")
        product.current_stock = previous - qty
        change = qty
    else:  # set
        product.current_stock = qty
        change = qty - previous

    _log(db, product, current_user, action, change, previous, product.current_stock, stock_data.note)
    db.commit()
    return {
        "current_stock": product.current_stock,
        "is_critical": product.current_stock <= (product.critical_stock or 0),
    }


@router.get("/{product_id}/logs")
def get_product_logs(
    product_id: int,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = _get_product_or_404(db, product_id)
    _check_access(current_user, product)
    logs = (db.query(StockLog).options(joinedload(StockLog.user))
            .filter(StockLog.product_id == product_id)
            .order_by(StockLog.created_at.desc(), StockLog.id.desc()).limit(limit).all())
    return [{
        "id": log.id,
        "product_id": log.product_id,
        "user_id": log.user_id,
        "action": log.action,
        "quantity_change": log.quantity_change,
        "previous_value": log.previous_value,
        "new_value": log.new_value,
        "note": log.note,
        "created_at": log.created_at.replace(tzinfo=timezone.utc).isoformat() if log.created_at else None,
        "user_name": log.user.full_name if log.user else None,
    } for log in logs]
