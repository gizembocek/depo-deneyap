from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_admin_user, get_current_user
from database import fold_value, folded, get_db, tr_sort_key
from models import Course, User, product_courses
from schemas import CourseCreate, CourseResponse

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.get("/", response_model=List[CourseResponse])
def list_courses(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    counts = dict(db.query(product_courses.c.course_id, func.count(product_courses.c.product_id))
                  .group_by(product_courses.c.course_id).all())
    courses = sorted(db.query(Course).all(), key=lambda c: tr_sort_key(c.name))
    return [CourseResponse(id=c.id, name=c.name, product_count=counts.get(c.id, 0)) for c in courses]


@router.post("/", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(course: CourseCreate, db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    if db.query(Course).filter(folded(Course.name) == fold_value(course.name)).first():
        raise HTTPException(status_code=400, detail="Bu ders zaten mevcut")
    new_course = Course(name=course.name)
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return CourseResponse(id=new_course.id, name=new_course.name, product_count=0)


@router.put("/{course_id}", response_model=CourseResponse)
def rename_course(course_id: int, course: CourseCreate, db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    db_course = db.get(Course, course_id)
    if not db_course:
        raise HTTPException(status_code=404, detail="Ders bulunamadı")
    clash = db.query(Course).filter(folded(Course.name) == fold_value(course.name), Course.id != course_id).first()
    if clash:
        raise HTTPException(status_code=400, detail="Bu isimde başka bir ders var")
    db_course.name = course.name
    db.commit()
    return CourseResponse(id=db_course.id, name=db_course.name)


@router.delete("/{course_id}")
def delete_course(course_id: int, db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    db_course = db.get(Course, course_id)
    if not db_course:
        raise HTTPException(status_code=404, detail="Ders bulunamadı")
    # Ürünler silinmez, sadece ders bağlantısı kaldırılır
    db.execute(product_courses.delete().where(product_courses.c.course_id == course_id))
    db.delete(db_course)
    db.commit()
    return {"message": "Ders başarıyla silindi"}
