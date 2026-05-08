from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Warehouse, Cabinet, Shelf, Compartment, User
from schemas import (
    WarehouseCreate, WarehouseUpdate, WarehouseResponse,
    CabinetCreate, CabinetResponse,
    ShelfCreate, ShelfResponse,
    CompartmentCreate, CompartmentResponse
)
from auth import get_current_user, get_admin_user
from typing import List

router = APIRouter(prefix="/api/warehouses", tags=["Warehouses"])


@router.get("/", response_model=List[WarehouseResponse])
def list_warehouses(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == "admin":
        warehouses = db.query(Warehouse).all()
    else:
        warehouses = current_user.warehouses
    return warehouses


@router.post("/", response_model=WarehouseResponse)
def create_warehouse(data: WarehouseCreate, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    warehouse = Warehouse(name=data.name, description=data.description, location=data.location)
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    # Auto-grant admin access
    current_user.warehouses.append(warehouse)
    db.commit()
    return warehouse


@router.put("/{warehouse_id}", response_model=WarehouseResponse)
def update_warehouse(warehouse_id: int, data: WarehouseUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Depo bulunamadı")

    if data.name is not None:
        warehouse.name = data.name
    if data.description is not None:
        warehouse.description = data.description
    if data.location is not None:
        warehouse.location = data.location

    db.commit()
    db.refresh(warehouse)
    return warehouse


@router.delete("/{warehouse_id}")
def delete_warehouse(warehouse_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Depo bulunamadı")
    db.delete(warehouse)
    db.commit()
    return {"message": "Depo silindi"}


@router.get("/{warehouse_id}/structure")
def get_warehouse_structure(warehouse_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Depo bulunamadı")

    cabinets = db.query(Cabinet).filter(Cabinet.warehouse_id == warehouse_id).all()
    result = []
    for cab in cabinets:
        shelves_data = []
        shelves = db.query(Shelf).filter(Shelf.cabinet_id == cab.id).all()
        for shelf in shelves:
            compartments = db.query(Compartment).filter(Compartment.shelf_id == shelf.id).all()
            shelves_data.append({
                "id": shelf.id,
                "name": shelf.name,
                "compartments": [{"id": c.id, "name": c.name} for c in compartments]
            })
        result.append({
            "id": cab.id,
            "name": cab.name,
            "shelves": shelves_data
        })

    return {"warehouse": {"id": warehouse.id, "name": warehouse.name}, "cabinets": result}


# --- Cabinets ---
@router.post("/cabinets", response_model=CabinetResponse)
def create_cabinet(data: CabinetCreate, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    cabinet = Cabinet(name=data.name, warehouse_id=data.warehouse_id)
    db.add(cabinet)
    db.commit()
    db.refresh(cabinet)
    return cabinet


@router.put("/cabinets/{cabinet_id}", response_model=CabinetResponse)
def update_cabinet(cabinet_id: int, data: CabinetCreate, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    cabinet = db.query(Cabinet).filter(Cabinet.id == cabinet_id).first()
    if not cabinet:
        raise HTTPException(status_code=404, detail="Dolap bulunamadı")
    cabinet.name = data.name
    db.commit()
    db.refresh(cabinet)
    return cabinet


@router.delete("/cabinets/{cabinet_id}")
def delete_cabinet(cabinet_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    cabinet = db.query(Cabinet).filter(Cabinet.id == cabinet_id).first()
    if not cabinet:
        raise HTTPException(status_code=404, detail="Dolap bulunamadı")
    db.delete(cabinet)
    db.commit()
    return {"message": "Dolap silindi"}


# --- Shelves ---
@router.post("/shelves", response_model=ShelfResponse)
def create_shelf(data: ShelfCreate, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    shelf = Shelf(name=data.name, cabinet_id=data.cabinet_id)
    db.add(shelf)
    db.commit()
    db.refresh(shelf)
    return shelf


@router.put("/shelves/{shelf_id}", response_model=ShelfResponse)
def update_shelf(shelf_id: int, data: ShelfCreate, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    shelf = db.query(Shelf).filter(Shelf.id == shelf_id).first()
    if not shelf:
        raise HTTPException(status_code=404, detail="Raf bulunamadı")
    shelf.name = data.name
    db.commit()
    db.refresh(shelf)
    return shelf


@router.delete("/shelves/{shelf_id}")
def delete_shelf(shelf_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    shelf = db.query(Shelf).filter(Shelf.id == shelf_id).first()
    if not shelf:
        raise HTTPException(status_code=404, detail="Raf bulunamadı")
    db.delete(shelf)
    db.commit()
    return {"message": "Raf silindi"}


# --- Compartments ---
@router.post("/compartments", response_model=CompartmentResponse)
def create_compartment(data: CompartmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    compartment = Compartment(name=data.name, shelf_id=data.shelf_id)
    db.add(compartment)
    db.commit()
    db.refresh(compartment)
    return compartment


@router.put("/compartments/{compartment_id}", response_model=CompartmentResponse)
def update_compartment(compartment_id: int, data: CompartmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    compartment = db.query(Compartment).filter(Compartment.id == compartment_id).first()
    if not compartment:
        raise HTTPException(status_code=404, detail="Bölme bulunamadı")
    compartment.name = data.name
    db.commit()
    db.refresh(compartment)
    return compartment


@router.delete("/compartments/{compartment_id}")
def delete_compartment(compartment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    compartment = db.query(Compartment).filter(Compartment.id == compartment_id).first()
    if not compartment:
        raise HTTPException(status_code=404, detail="Bölme bulunamadı")
    db.delete(compartment)
    db.commit()
    return {"message": "Bölme silindi"}


# --- Courses ---
@router.get("/courses", response_model=List[CabinetResponse])
def list_courses(db: Session = Depends(get_db)):
    from models import Course
    courses = db.query(Course).all()
    return [{"id": c.id, "name": c.name, "warehouse_id": 0} for c in courses]
