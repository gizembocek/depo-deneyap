"""Mevcut ürünleri description alanındaki kaynak bilgisine göre derslere bağlar."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Product, Course

db = SessionLocal()

products = db.query(Product).all()
updated_count = 0

for p in products:
    if p.description and p.description.startswith("Kaynak: "):
        course_name = p.description.replace("Kaynak: ", "").strip()
        
        course = db.query(Course).filter(Course.name == course_name).first()
        if not course:
            course = Course(name=course_name)
            db.add(course)
            db.commit()
            db.refresh(course)
            
        if course not in p.courses:
            p.courses.append(course)
            updated_count += 1

db.commit()
print(f"Güncellenen ürün sayısı: {updated_count}")

db.close()
