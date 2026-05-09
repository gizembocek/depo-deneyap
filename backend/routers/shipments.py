from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models import Shipment, ShipmentItem, Product, User, StockLog
from schemas import ShipmentCreate, ShipmentResponse, ShipmentItemResponse, ShipmentTypeSchema
from auth import get_current_user
from typing import List
from datetime import datetime

router = APIRouter(prefix="/api/shipments", tags=["Shipments"])


def build_shipment_response(s: Shipment) -> dict:
    """Shipment ORM nesnesini, product_name dahil tam bir dict'e çevirir."""
    items = []
    for item in s.items:
        items.append({
            "id": item.id,
            "product_id": item.product_id,
            "expected_quantity": item.expected_quantity,
            "actual_quantity": item.actual_quantity,
            "status": item.status,
            "product_name": item.product.name if item.product else None
        })
    return {
        "id": s.id,
        "name": s.name,
        "shipment_type": s.shipment_type,
        "outgoing_reason": s.outgoing_reason,
        "arrival_image_url": s.arrival_image_url,
        "visual_image_url": s.visual_image_url,
        "invoice_image_url": s.invoice_image_url,
        "shipment_date": s.shipment_date,
        "check_date": s.check_date,
        "status": s.status,
        "notes": s.notes,
        "created_by": s.created_by,
        "created_at": s.created_at,
        "items": items
    }


@router.get("/", response_model=List[ShipmentResponse])
def list_shipments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    shipments = (
        db.query(Shipment)
        .options(joinedload(Shipment.items).joinedload(ShipmentItem.product))
        .order_by(Shipment.created_at.desc())
        .all()
    )
    return [build_shipment_response(s) for s in shipments]


@router.post("/", response_model=ShipmentResponse)
def create_shipment(data: ShipmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Ana Gönderimi Oluştur
    new_shipment = Shipment(
        name=data.name,
        shipment_type=data.shipment_type,
        outgoing_reason=data.outgoing_reason,
        arrival_image_url=data.arrival_image_url,
        visual_image_url=data.visual_image_url,
        invoice_image_url=data.invoice_image_url,
        shipment_date=data.shipment_date,
        check_date=data.check_date,
        notes=data.notes,
        created_by=current_user.id,
        status="pending"
    )
    db.add(new_shipment)
    db.flush()

    # 2. Ürünleri İşle ve LOG Oluştur
    for item_data in data.items:
        # actual_quantity varsa onu kullan, yoksa expected_quantity
        qty_to_use = item_data.actual_quantity if item_data.actual_quantity is not None else item_data.expected_quantity

        # Durum hesapla
        if item_data.actual_quantity is None:
            item_status = "pending"
        elif item_data.actual_quantity == item_data.expected_quantity:
            item_status = "complete"
        elif item_data.actual_quantity < item_data.expected_quantity:
            item_status = "missing"
        else:
            item_status = "extra"

        item = ShipmentItem(
            shipment_id=new_shipment.id,
            product_id=item_data.product_id,
            expected_quantity=item_data.expected_quantity,
            actual_quantity=item_data.actual_quantity,
            status=item_status
        )
        db.add(item)

        # Ürünü bul ve stoğu güncelle (actual_quantity üzerinden)
        product = db.query(Product).filter(Product.id == item_data.product_id).first()
        if product:
            old_stock = product.current_stock

            if data.shipment_type == "Giriş":
                product.current_stock += qty_to_use
                action_type = "add"
            else:
                product.current_stock -= qty_to_use
                action_type = "remove"

            # Stok log kaydı
            log = StockLog(
                product_id=product.id,
                user_id=current_user.id,
                action=action_type,
                quantity_change=qty_to_use,
                previous_value=str(old_stock),
                new_value=str(product.current_stock),
                note=f"Gönderim: {new_shipment.name}"
            )
            db.add(log)

    db.commit()

    # İlişkileriyle birlikte tekrar çek
    shipment = (
        db.query(Shipment)
        .options(joinedload(Shipment.items).joinedload(ShipmentItem.product))
        .filter(Shipment.id == new_shipment.id)
        .first()
    )
    return build_shipment_response(shipment)


@router.delete("/{shipment_id}")
def delete_shipment(shipment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Gönderim bulunamadı")
    db.delete(shipment)
    db.commit()
    return {"message": "Gönderim silindi"}