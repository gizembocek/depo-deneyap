from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Shipment, ShipmentItem, Product, User
from schemas import ShipmentCreate, ShipmentResponse, ShipmentItemResponse
from auth import get_current_user, get_admin_user
from typing import List

router = APIRouter(prefix="/api/shipments", tags=["Shipments"])


@router.get("/", response_model=List[ShipmentResponse])
def list_shipments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    shipments = db.query(Shipment).order_by(Shipment.created_at.desc()).all()
    result = []
    for s in shipments:
        items = []
        for item in s.items:
            items.append(ShipmentItemResponse(
                id=item.id,
                product_id=item.product_id,
                expected_quantity=item.expected_quantity,
                actual_quantity=item.actual_quantity,
                status=item.status,
                product_name=item.product.name if item.product else None
            ))
        result.append(ShipmentResponse(
            id=s.id,
            name=s.name,
            shipment_date=s.shipment_date,
            check_date=s.check_date,
            status=s.status,
            notes=s.notes,
            created_by=s.created_by,
            created_at=s.created_at,
            items=items
        ))
    return result


@router.post("/", response_model=ShipmentResponse)
def create_shipment(data: ShipmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    shipment = Shipment(
        name=data.name,
        shipment_date=data.shipment_date,
        check_date=data.check_date,
        notes=data.notes,
        created_by=current_user.id
    )
    db.add(shipment)
    db.flush()

    for item_data in data.items:
        item = ShipmentItem(
            shipment_id=shipment.id,
            product_id=item_data.product_id,
            expected_quantity=item_data.expected_quantity
        )
        db.add(item)

    db.commit()
    db.refresh(shipment)

    items = []
    for item in shipment.items:
        items.append(ShipmentItemResponse(
            id=item.id,
            product_id=item.product_id,
            expected_quantity=item.expected_quantity,
            actual_quantity=item.actual_quantity,
            status=item.status,
            product_name=item.product.name if item.product else None
        ))

    return ShipmentResponse(
        id=shipment.id,
        name=shipment.name,
        shipment_date=shipment.shipment_date,
        check_date=shipment.check_date,
        status=shipment.status,
        notes=shipment.notes,
        created_by=shipment.created_by,
        created_at=shipment.created_at,
        items=items
    )


@router.put("/{shipment_id}/check")
def check_shipment(shipment_id: int, items: List[dict], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Gönderim bulunamadı")
    
    # Authorization: Only admin or shipment creator can check
    if current_user.role != "admin" and shipment.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Bu gönderimi kontrol etme yetkisi yok")

    for item_data in items:
        item = db.query(ShipmentItem).filter(ShipmentItem.id == item_data["id"]).first()
        if item:
            item.actual_quantity = item_data.get("actual_quantity", 0)
            if item.actual_quantity == item.expected_quantity:
                item.status = "complete"
            elif item.actual_quantity < item.expected_quantity:
                item.status = "missing"
            else:
                item.status = "extra"

    shipment.status = "checked"
    from datetime import datetime
    shipment.check_date = datetime.utcnow()
    db.commit()

    return {"message": "Gönderim kontrol edildi"}


@router.delete("/{shipment_id}")
def delete_shipment(shipment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Gönderim bulunamadı")
    db.delete(shipment)
    db.commit()
    return {"message": "Gönderim silindi"}
