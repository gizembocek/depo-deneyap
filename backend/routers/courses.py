from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Course, User
from schemas import CourseCreate, CourseResponse
from auth import get_admin_user

router = APIRouter(
    prefix="/api/courses",
    tags=["courses"]
)

@router.get("/", response_model=List[CourseResponse])
def list_courses(db: Session = Depends(get_db)):
    return db.query(Course).all()

@router.post("/", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    course: CourseCreate, 
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    # Aynı isimde ders var mı kontrol et
    db_course = db.query(Course).filter(Course.name == course.name).first()
    if db_course:
        raise HTTPException(status_code=400, detail="Bu ders zaten mevcut")
    
    new_course = Course(name=course.name)
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course

@router.delete("/{course_id}")
def delete_course(
    course_id: int, 
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Ders bulunamadı")
    
    db.delete(db_course)
    db.commit()
    return {"message": "Ders başarıyla silindi"}
