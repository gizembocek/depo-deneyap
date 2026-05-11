"""Tüm ürünleri, stok loglarını ve product_courses ilişkilerini siler."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Product, StockLog, product_courses

db = SessionLocal()

log_count = db.query(StockLog).delete()
db.execute(product_courses.delete())
product_count = db.query(Product).delete()
db.commit()

print(f"\n=== TEMİZLİK TAMAMLANDI ===")
print(f"Silinen ürün: {product_count}")
print(f"Silinen stok logu: {log_count}")
print(f"Kalan ürün sayısı: {db.query(Product).count()}")

db.close()
