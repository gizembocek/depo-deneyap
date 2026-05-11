"""Debug script: veritabanındaki ürünleri ve yapıyı kontrol eder."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Product

db = SessionLocal()

products = db.query(Product).order_by(Product.id.desc()).limit(20).all()
print(f"\n=== Toplam ürün sayısı: {db.query(Product).count()} ===\n")
print(f"{'ID':<6} {'İSİM':<35} {'KATEGORİ':<30} {'STOK':<6} {'DEPO_ID':<8}")
print("-" * 90)
for p in products:
    print(f"{p.id:<6} {p.name[:33]:<35} {p.category[:28]:<30} {p.current_stock:<6} {str(p.warehouse_id):<8}")

db.close()
