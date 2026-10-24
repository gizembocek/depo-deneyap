from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import can_access_warehouse, get_admin_user, get_current_user
from database import get_db, tr_sort_key
from models import Cabinet, Compartment, Product, Shelf, ShipmentItem, StockLog, User, Warehouse, product_courses
from schemas import (
    CabinetCreate, CabinetResponse, CompartmentCreate, CompartmentResponse,
    LocationRename, ShelfCreate, ShelfResponse, WarehouseCreate, WarehouseResponse,
    WarehouseUpdate,
)

router = APIRouter(prefix="/api/warehouses", tags=["Warehouses"])


def _product_counts(db: Session) -> dict:
    rows = db.query(Product.warehouse_id, func.count(Product.id)).group_by(Product.warehouse_id).all()
    return {wid: count for wid, count in rows}


def _to_response(w: Warehouse, counts: dict) -> WarehouseResponse:
    return WarehouseResponse(
        id=w.id, name=w.name, description=w.description, location=w.location,
        created_at=w.created_at, product_count=counts.get(w.id, 0),
    )


def _get_or_404(db: Session, model, obj_id: int, label: str):
    obj = db.get(model, obj_id)
    if not obj:
        raise HTTPException(status_code=404, detail=f"{label} bulunamadı")
    return obj


@router.get("/", response_model=List[WarehouseResponse])
def list_warehouses(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == "admin":
        warehouses = db.query(Warehouse).all()
    else:
        warehouses = list(current_user.warehouses)
    warehouses.sort(key=lambda w: tr_sort_key(w.name))
    counts = _product_counts(db)
    return [_to_response(w, counts) for w in warehouses]


@router.post("/", response_model=WarehouseResponse)
def create_warehouse(data: WarehouseCreate, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    warehouse = Warehouse(name=data.name, description=data.description, location=data.location)
    db.add(warehouse)
    current_user.warehouses.append(warehouse)
    db.commit()
    db.refresh(warehouse)
    return _to_response(warehouse, {})


@router.put("/{warehouse_id}", response_model=WarehouseResponse)
def update_warehouse(warehouse_id: int, data: WarehouseUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    warehouse = _get_or_404(db, Warehouse, warehouse_id, "Depo")
    if data.name is not None:
        warehouse.name = data.name
    if data.description is not None:
        warehouse.description = data.description or None
    if data.location is not None:
        warehouse.location = data.location or None
    db.commit()
    db.refresh(warehouse)
    return _to_response(warehouse, _product_counts(db))


@router.delete("/{warehouse_id}")
def delete_warehouse(warehouse_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    """Depoyu, içindeki dolap/raf/bölmeleri ve ürünleri siler."""
    warehouse = _get_or_404(db, Warehouse, warehouse_id, "Depo")
    product_ids = [pid for (pid,) in db.query(Product.id).filter(Product.warehouse_id == warehouse_id).all()]
    for start in range(0, len(product_ids), 500):
        chunk = product_ids[start:start + 500]
        db.query(ShipmentItem).filter(ShipmentItem.product_id.in_(chunk)).delete(synchronize_session=False)
        db.query(StockLog).filter(StockLog.product_id.in_(chunk)).delete(synchronize_session=False)
        db.execute(product_courses.delete().where(product_courses.c.product_id.in_(chunk)))
    warehouse.users = []
    db.delete(warehouse)
    db.commit()
    return {"message": "Depo silindi", "deleted_products": len(product_ids)}


@router.get("/{warehouse_id}/structure")
def get_warehouse_structure(warehouse_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    warehouse = _get_or_404(db, Warehouse, warehouse_id, "Depo")
    if not can_access_warehouse(current_user, warehouse_id):
        raise HTTPException(status_code=403, detail="Bu depoya erişim yetkiniz yok")

    cabinets = db.query(Cabinet).filter(Cabinet.warehouse_id == warehouse_id).order_by(Cabinet.name, Cabinet.id).all()
    cab_ids = [c.id for c in cabinets]
    shelves = db.query(Shelf).filter(Shelf.cabinet_id.in_(cab_ids)).order_by(Shelf.name, Shelf.id).all() if cab_ids else []
    shelf_ids = [s.id for s in shelves]
    comps = (db.query(Compartment).filter(Compartment.shelf_id.in_(shelf_ids)).order_by(Compartment.name, Compartment.id).all()
             if shelf_ids else [])

    comps_by_shelf: dict = {}
    for c in comps:
        comps_by_shelf.setdefault(c.shelf_id, []).append({"id": c.id, "name": c.name})
    shelves_by_cab: dict = {}
    for s in shelves:
        shelves_by_cab.setdefault(s.cabinet_id, []).append(
            {"id": s.id, "name": s.name, "compartments": comps_by_shelf.get(s.id, [])})

    return {
        "warehouse": {"id": warehouse.id, "name": warehouse.name},
        "cabinets": [{"id": c.id, "name": c.name, "shelves": shelves_by_cab.get(c.id, [])} for c in cabinets],
    }


# --- Dolaplar ---
@router.post("/cabinets", response_model=CabinetResponse)
def create_cabinet(data: CabinetCreate, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    _get_or_404(db, Warehouse, data.warehouse_id, "Depo")
    cabinet = Cabinet(name=data.name, warehouse_id=data.warehouse_id)
    db.add(cabinet)
    db.commit()
    db.refresh(cabinet)
    return cabinet


@router.put("/cabinets/{cabinet_id}", response_model=CabinetResponse)
def update_cabinet(cabinet_id: int, data: LocationRename, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    cabinet = _get_or_404(db, Cabinet, cabinet_id, "Dolap")
    cabinet.name = data.name
    db.commit()
    db.refresh(cabinet)
    return cabinet


@router.delete("/cabinets/{cabinet_id}")
def delete_cabinet(cabinet_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    cabinet = _get_or_404(db, Cabinet, cabinet_id, "Dolap")
    # İçindeki ürünler silinmez; sadece konumları boşaltılır.
    db.query(Product).filter(Product.cabinet_id == cabinet_id).update(
        {Product.cabinet_id: None, Product.shelf_id: None, Product.compartment_id: None}, synchronize_session=False)
    db.delete(cabinet)
    db.commit()
    return {"message": "Dolap silindi"}


# --- Raflar ---
@router.post("/shelves", response_model=ShelfResponse)
def create_shelf(data: ShelfCreate, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    _get_or_404(db, Cabinet, data.cabinet_id, "Dolap")
    shelf = Shelf(name=data.name, cabinet_id=data.cabinet_id)
    db.add(shelf)
    db.commit()
    db.refresh(shelf)
    return shelf


@router.put("/shelves/{shelf_id}", response_model=ShelfResponse)
def update_shelf(shelf_id: int, data: LocationRename, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    shelf = _get_or_404(db, Shelf, shelf_id, "Raf")
    shelf.name = data.name
    db.commit()
    db.refresh(shelf)
    return shelf


@router.delete("/shelves/{shelf_id}")
def delete_shelf(shelf_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    shelf = _get_or_404(db, Shelf, shelf_id, "Raf")
    db.query(Product).filter(Product.shelf_id == shelf_id).update(
        {Product.shelf_id: None, Product.compartment_id: None}, synchronize_session=False)
    db.delete(shelf)
    db.commit()
    return {"message": "Raf silindi"}


# --- Bölmeler ---
@router.post("/compartments", response_model=CompartmentResponse)
def create_compartment(data: CompartmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    _get_or_404(db, Shelf, data.shelf_id, "Raf")
    compartment = Compartment(name=data.name, shelf_id=data.shelf_id)
    db.add(compartment)
    db.commit()
    db.refresh(compartment)
    return compartment


@router.put("/compartments/{compartment_id}", response_model=CompartmentResponse)
def update_compartment(compartment_id: int, data: LocationRename, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    compartment = _get_or_404(db, Compartment, compartment_id, "Bölme")
    compartment.name = data.name
    db.commit()
    db.refresh(compartment)
    return compartment


@router.delete("/compartments/{compartment_id}")
def delete_compartment(compartment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    compartment = _get_or_404(db, Compartment, compartment_id, "Bölme")
    db.query(Product).filter(Product.compartment_id == compartment_id).update(
        {Product.compartment_id: None}, synchronize_session=False)
    db.delete(compartment)
    db.commit()
    return {"message": "Bölme silindi"}
