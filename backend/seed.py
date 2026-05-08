import json
import os
import sys
import glob
from database import engine, SessionLocal, Base
from models import User, Warehouse, Cabinet, Shelf, Compartment, Course, Product
from auth import get_password_hash

# List of courses from requirements
COURSES = [
    "Robotik Kodlama",
    "Yapay Zeka",
    "Siber Güvenlik",
    "Malzeme Bilimi ve Nanoteknoloji",
    "Tasarım ve Üretim",
    "Enerji Teknolojileri",
    "Yazılım Teknolojileri",
    "Mobil Uygulama",
    "Elektronik Programlama ve Nesnelerin İnterneti (EPNİ)",
    "İleri Robotik",
    "Havacılık ve Uzay Teknolojileri",
    "Genel"
]


def seed_database():
    # Create tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already seeded
        existing_users = db.query(User).count()
        if existing_users > 0:
            print("Veritabani zaten doldurulmus. Seed islemi atlaniyor.")
            print(f"Mevcut kullanici sayisi: {existing_users}")
            return

        print("Veritabani seed islemi basliyor...")

        # 1. Create admin user
        admin = User(
            email="admin@deneyap.org",
            full_name="Admin Kullanıcı",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            is_active=True
        )
        db.add(admin)

        # 2. Create sample user
        user = User(
            email="kullanici@deneyap.org",
            full_name="Deneyap Eğitmeni",
            hashed_password=get_password_hash("user123"),
            role="user",
            is_active=True
        )
        db.add(user)
        db.flush()

        # 3. Create warehouses
        warehouse1 = Warehouse(name="Deneyap Atölyesi Ana Depo", description="Ana atölye deposu", location="Atölye Katı")
        warehouse2 = Warehouse(name="Elektronik Malzeme Deposu", description="Elektronik bileşenler", location="Atölye Katı - Oda 2")
        warehouse3 = Warehouse(name="Enerji Laboratuvarı", description="Enerji teknolojileri malzemeleri", location="Laboratuvar Katı")
        db.add_all([warehouse1, warehouse2, warehouse3])
        db.flush()

        # Grant warehouse access
        admin.warehouses.extend([warehouse1, warehouse2, warehouse3])
        user.warehouses.extend([warehouse1, warehouse2])

        # 4. Create cabinets, shelves, compartments for warehouse1
        for i in range(1, 4):
            cabinet = Cabinet(name=f"Dolap {i}", warehouse_id=warehouse1.id)
            db.add(cabinet)
            db.flush()
            for j in range(1, 4):
                shelf = Shelf(name=f"Raf {j}", cabinet_id=cabinet.id)
                db.add(shelf)
                db.flush()
                for k in range(1, 3):
                    comp = Compartment(name=f"Bölme {k}", shelf_id=shelf.id)
                    db.add(comp)

        # Cabinets for warehouse2
        for i in range(1, 3):
            cabinet = Cabinet(name=f"Dolap {i}", warehouse_id=warehouse2.id)
            db.add(cabinet)
            db.flush()
            for j in range(1, 3):
                shelf = Shelf(name=f"Raf {j}", cabinet_id=cabinet.id)
                db.add(shelf)

        db.flush()

        # 5. Create courses
        course_objects = {}
        for course_name in COURSES:
            course = Course(name=course_name)
            db.add(course)
            db.flush()
            course_objects[course_name] = course

        # 6. Load products from JSON
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
        json_path = os.path.join(assets_dir, "malzeme_listesi.json")
        images_dir = os.path.join(assets_dir, "images")

        with open(json_path, "r", encoding="utf-8") as f:
            materials = json.load(f)

        # Map image files (check actual extensions)
        image_map = {}
        for i in range(1, 100):
            for ext in ['.png', '.jpg', '.jpeg']:
                candidate = os.path.join(images_dir, f"image{i}{ext}")
                if os.path.exists(candidate):
                    image_map[i] = f"/assets/images/image{i}{ext}"
                    break

        # Category assignment based on product name keywords
        def guess_category(name):
            name_lower = name.lower()
            sarf_keywords = ["pil", "bant", "koli", "silikon", "mum", "yapıştırıcı", "lehim", "boya", "ispirto", "çakmak", "su ", "saf su", "sodyum"]
            elektronik_keywords = ["motor", "arduino", "sensör", "direnç", "led", "modül", "fan", "dinamo", "şarj", "kablo", "konnektör", "multimetre", "inverter", "dimmer"]
            
            for kw in sarf_keywords:
                if kw in name_lower:
                    return "Sarf Malzemesi"
            for kw in elektronik_keywords:
                if kw in name_lower:
                    return "Elektronik Bileşen"
            return "Genel / Dayanıklı Malzeme"

        # Course assignment based on product name
        def guess_courses(name):
            name_lower = name.lower()
            assigned = []
            if any(kw in name_lower for kw in ["güneş", "enerji", "türbin", "panel", "akü", "inverter", "buhar", "hidrojen", "rüzgar", "jeneratör", "su çarkı"]):
                assigned.append("Enerji Teknolojileri")
            if any(kw in name_lower for kw in ["motor", "servo", "arduino", "sensör", "direnç", "led", "fan"]):
                assigned.append("Robotik Kodlama")
            if any(kw in name_lower for kw in ["elektronik", "kablo", "konnektör", "modül", "direnç", "dinamo", "multimetre", "anahtar"]):
                assigned.append("Elektronik Programlama ve Nesnelerin İnterneti (EPNİ)")
            if any(kw in name_lower for kw in ["mdf", "montaj", "çelik", "kanat", "pervane", "laboratuvar"]):
                assigned.append("Tasarım ve Üretim")
            if any(kw in name_lower for kw in ["havacılık", "uzay", "kanat"]):
                assigned.append("Havacılık ve Uzay Teknolojileri")
            if not assigned:
                assigned.append("Genel")
            return assigned

        for idx, material in enumerate(materials):
            name = material["isim"].strip()
            stock = material.get("miktar", 100)
            image_num = idx + 1

            # Get actual image path
            image_url = image_map.get(image_num, None)

            category = guess_category(name)
            critical_stock = 10 if category == "Sarf Malzemesi" else 5

            # Assign to warehouses based on category
            if idx < 20:
                wh_id = warehouse3.id  # Enerji ürünleri
            elif idx < 50:
                wh_id = warehouse1.id  # Ana depo
            else:
                wh_id = warehouse2.id  # Elektronik depo

            product = Product(
                name=name,
                description=f"{name} - Deneyap Atölyesi malzemesi",
                image_url=image_url,
                category=category,
                status="Çalışan",
                current_stock=stock,
                critical_stock=critical_stock,
                ideal_stock=100,
                warehouse_id=wh_id,
            )

            # Assign courses
            course_names = guess_courses(name)
            for cn in course_names:
                if cn in course_objects:
                    product.courses.append(course_objects[cn])

            db.add(product)

        db.commit()
        print(f"[OK] Seed islemi tamamlandi!")
        print(f"  - {len(materials)} urun eklendi")
        print(f"  - {len(COURSES)} ders eklendi")
        print(f"  - 3 depo olusturuldu")
        print(f"  - 2 kullanici olusturuldu")
        print(f"  - Admin: admin@deneyap.org / admin123")
        print(f"  - Kullanici: kullanici@deneyap.org / user123")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Seed hatasi: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
