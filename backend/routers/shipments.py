"""
Gönderim / İşlem modülü (Giriş = stoğa ekle, Çıkış = stoktan düş).

Stok kuralları:
  - Giriş: "gelen" miktar girildiyse o kadar, girilmediyse "beklenen" kadar stok eklenir.
    Gelen miktar sonradan "Kontrol Et" ile girilirse aradaki fark stoğa yansıtılır.
  - Çıkış: stok yetersizse işlem yapılmaz (stok eksiye düşmez).
  - İşlem silinirken stok hareketleri isteğe bağlı olarak geri alınır.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from auth import accessible_warehouse_ids, can_access_warehouse, get_admin_user, get_current_user
from database import get_db
from models import Product, Shipment, ShipmentItem, StockLog, User
from schemas import ShipmentCheckItem, ShipmentCreate, ShipmentResponse

router = APIRouter(prefix="/api/shipments", tags=["Shipments"])

GIRIS = "Giriş"
CIKIS = "Çıkış"


def _item_status(expected: int, actual: Optional[int]) -> str:
    if actual is None:
        return "pending"
    if actual == expected:
        return "complete"
    return "missing" if actual < expected else "extra"


def _applied_qty(item: ShipmentItem) -> int:
    """Bu satır için stoğa daha önce yansıtılmış miktar."""
    return item.actual_quantity if item.actual_quantity is not None else (item.expected_quantity or 0)


def _shipment_status(s: Shipment) -> str:
    return "pending" if any(i.actual_quantity is None for i in s.items) else "checked"


def build_shipment_response(s: Shipment, include_images: bool = False) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "shipment_type": s.shipment_type or GIRIS,
        "outgoing_reason": s.outgoing_reason,
        "arrival_image_url": s.arrival_image_url if include_images else None,
        "visual_image_url": s.visual_image_url if include_images else None,
        "invoice_image_url": s.invoice_image_url if include_images else None,
        "has_arrival_image": bool(s.arrival_image_url),
        "has_visual_image": bool(s.visual_image_url),
        "has_invoice_image": bool(s.invoice_image_url),
        "shipment_date": s.shipment_date,
        "check_date": s.check_date,
        "status": _shipment_status(s),
        "notes": s.notes,
        "created_by": s.created_by,
        "creator_name": s.creator.full_name if s.creator else None,
        "created_at": s.created_at,
        "items": [{
            "id": item.id,
            "product_id": item.product_id,
            "expected_quantity": item.expected_quantity,
            "actual_quantity": item.actual_quantity,
            "status": item.status or _item_status(item.expected_quantity, item.actual_quantity),
            "product_name": item.product.name if item.product else None,
        } for item in sorted(s.items, key=lambda i: i.id or 0)],
    }


def _load_shipment(db: Session, shipment_id: int) -> Shipment:
    s = (db.query(Shipment)
         .options(joinedload(Shipment.items).joinedload(ShipmentItem.product), joinedload(Shipment.creator))
         .filter(Shipment.id == shipment_id).first())
    if not s:
        raise HTTPException(status_code=404, detail="Gönderim bulunamadı")
    return s


def _can_see(user: User, s: Shipment) -> bool:
    if user.role == "admin" or s.created_by == user.id:
        return True
    return any(i.product and can_access_warehouse(user, i.product.warehouse_id) for i in s.items)


def _stock_log(db, product, user, action, qty, previous, note):
    db.add(StockLog(
        product_id=product.id, user_id=user.id, action=action, quantity_change=qty,
        previous_value=str(previous), new_value=str(product.current_stock), note=note,
    ))


def _apply(db, product: Product, user: User, delta: int, note: str):
    """Stoğu delta kadar değiştirir (+ ekle / - çıkar) ve log yazar."""
    if delta == 0:
        return
    previous = product.current_stock or 0
    product.current_stock = previous + delta
    _stock_log(db, product, user, "add" if delta > 0 else "remove", abs(delta), previous, note)


@router.get("/", response_model=List[ShipmentResponse])
def list_shipments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = (db.query(Shipment)
             .options(joinedload(Shipment.items).joinedload(ShipmentItem.product), joinedload(Shipment.creator))
             .order_by(Shipment.created_at.desc(), Shipment.id.desc()))
    if current_user.role != "admin":
        ids = accessible_warehouse_ids(current_user)
        visible_items = db.query(ShipmentItem.shipment_id).join(Product, ShipmentItem.product_id == Product.id)
        visible_items = visible_items.filter(or_(Product.warehouse_id.is_(None), Product.warehouse_id.in_(ids)) if ids
                                             else Product.warehouse_id.is_(None))
        query = query.filter(or_(Shipment.created_by == current_user.id, Shipment.id.in_(visible_items)))
    return [build_shipment_response(s) for s in query.all()]


@router.get("/{shipment_id}", response_model=ShipmentResponse)
def get_shipment(shipment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    s = _load_shipment(db, shipment_id)
    if not _can_see(current_user, s):
        raise HTTPException(status_code=403, detail="Bu işlemi görüntüleme yetkiniz yok")
    return build_shipment_response(s, include_images=True)


@router.post("/", response_model=ShipmentResponse)
def create_shipment(data: ShipmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    shipment_type = data.shipment_type.value
    product_ids = sorted({i.product_id for i in data.items})
    products = {p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()}

    missing = [pid for pid in product_ids if pid not in products]
    if missing:
        raise HTTPException(status_code=400, detail=f"Ürün bulunamadı (id: {', '.join(map(str, missing))})")
    for p in products.values():
        if not can_access_warehouse(current_user, p.warehouse_id):
            raise HTTPException(status_code=403, detail=f"'{p.name}' ürününün deposuna erişim yetkiniz yok")

    # Çıkışta stok yeterliliği (aynı ürün birden fazla satırda olabilir)
    if shipment_type == CIKIS:
        needed: dict = {}
        for i in data.items:
            qty = i.actual_quantity if i.actual_quantity is not None else i.expected_quantity
            needed[i.product_id] = needed.get(i.product_id, 0) + qty
        shortages = [f"{products[pid].name} (mevcut {products[pid].current_stock or 0}, istenen {qty})"
                     for pid, qty in needed.items() if qty > (products[pid].current_stock or 0)]
        if shortages:
            raise HTTPException(status_code=400, detail="Yetersiz stok: " + "; ".join(shortages))

    shipment = Shipment(
        name=data.name,
        shipment_type=shipment_type,
        outgoing_reason=data.outgoing_reason if shipment_type == CIKIS else None,
        arrival_image_url=data.arrival_image_url,
        visual_image_url=data.visual_image_url,
        invoice_image_url=data.invoice_image_url,
        shipment_date=data.shipment_date,
        check_date=data.check_date,
        notes=data.notes,
        created_by=current_user.id,
    )
    db.add(shipment)
    db.flush()

    note = f"Gönderim: {shipment.name}"
    for i in data.items:
        actual = i.actual_quantity
        if shipment_type == CIKIS and actual is None:
            actual = i.expected_quantity  # çıkışta beklenen = çıkan
        item = ShipmentItem(
            shipment_id=shipment.id,
            product_id=i.product_id,
            expected_quantity=i.expected_quantity,
            actual_quantity=actual,
            status=_item_status(i.expected_quantity, actual),
        )
        db.add(item)
        qty = actual if actual is not None else i.expected_quantity
        _apply(db, products[i.product_id], current_user, qty if shipment_type == GIRIS else -qty, note)

    db.flush()
    db.refresh(shipment)
    shipment.status = _shipment_status(shipment)
    db.commit()
    return build_shipment_response(_load_shipment(db, shipment.id))


@router.put("/{shipment_id}/check", response_model=ShipmentResponse)
def check_shipment(shipment_id: int, items: List[ShipmentCheckItem], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Gelen/çıkan gerçek miktarları kaydeder ve farkı stoğa yansıtır."""
    s = _load_shipment(db, shipment_id)
    if not _can_see(current_user, s):
        raise HTTPException(status_code=403, detail="Bu işlemi kontrol etme yetkiniz yok")
    if not items:
        raise HTTPException(status_code=400, detail="Kontrol edilecek satır yok")

    by_id = {i.id: i for i in s.items}
    unknown = [c.item_id for c in items if c.item_id not in by_id]
    if unknown:
        raise HTTPException(status_code=400, detail="Bu işleme ait olmayan satır gönderildi")

    sign = 1 if (s.shipment_type or GIRIS) == GIRIS else -1
    # Önce tüm değişiklikleri hesapla, sonra uygula (yarım kalan işlem olmasın)
    plan = []
    for c in items:
        item = by_id[c.item_id]
        delta = sign * (c.actual_quantity - _applied_qty(item))
        product = item.product
        if product is not None and (product.current_stock or 0) + delta < 0:
            raise HTTPException(status_code=400, detail=f"Yetersiz stok: {product.name} (mevcut {product.current_stock})")
        plan.append((item, c.actual_quantity, delta))

    note = f"Gönderim kontrolü: {s.name}"
    for item, actual, delta in plan:
        if item.product is not None:
            _apply(db, item.product, current_user, delta, note)
        item.actual_quantity = actual
        item.status = _item_status(item.expected_quantity, actual)

    s.check_date = s.check_date or datetime.utcnow()
    s.status = _shipment_status(s)
    db.commit()
    return build_shipment_response(_load_shipment(db, shipment_id))


@router.delete("/{shipment_id}")
def delete_shipment(
    shipment_id: int,
    revert_stock: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    s = _load_shipment(db, shipment_id)
    reverted = 0
    if revert_stock:
        sign = 1 if (s.shipment_type or GIRIS) == GIRIS else -1
        plan = []
        for item in s.items:
            if item.product is None:
                continue
            delta = -sign * _applied_qty(item)
            if (item.product.current_stock or 0) + delta < 0:
                raise HTTPException(
                    status_code=400,
                    detail=(f"'{item.product.name}' için stok geri alınamıyor (mevcut {item.product.current_stock}). "
                            "Stokları değiştirmeden silmek için 'stokları geri al' seçeneğini kapatın."),
                )
            plan.append((item.product, delta))
        for product, delta in plan:
            _apply(db, product, current_user, delta, f"Gönderim silindi (geri alındı): {s.name}")
            reverted += 1
    db.delete(s)
    db.commit()
    return {"message": "Gönderim silindi", "reverted_items": reverted}
