"""
Şifresini unutan bir kullanıcının şifresini sıfırlar (yalnızca o kullanıcının).

Kullanım (backend klasöründe):
    python sifre_sifirla.py                       -> kullanıcıları listeler
    python sifre_sifirla.py gizem@deneyap.org     -> yeni şifreyi sorar ve kaydeder

.env dosyasındaki veritabanı ayarını kullanır (SQLite, SQL Server veya PostgreSQL).
"""
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth import get_password_hash, password_problem  # noqa: E402
from database import SessionLocal, aktif_baglanti, fold_value, folded, init_db  # noqa: E402
from models import User  # noqa: E402


def main():
    init_db()
    print("Veritabanı:", aktif_baglanti())
    db = SessionLocal()
    try:
        if len(sys.argv) < 2:
            print("\nKullanıcılar:")
            for u in db.query(User).order_by(User.id).all():
                print(f"  {u.email:<35} {u.full_name:<30} {'yönetici' if u.role == 'admin' else 'kullanıcı'}"
                      f"{'' if u.is_active else ' (pasif)'}")
            print("\nŞifre sıfırlamak için: python sifre_sifirla.py <e-posta>")
            return

        email = sys.argv[1]
        user = db.query(User).filter(folded(User.email) == fold_value(email)).first()
        if not user:
            print(f"[HATA] '{email}' adresli kullanıcı bulunamadı.")
            sys.exit(1)

        while True:
            password = getpass.getpass("Yeni şifre (en az 8 karakter, 1 büyük harf, 1 rakam): ")
            problem = password_problem(password)
            if problem:
                print("  ->", problem)
                continue
            if getpass.getpass("Yeni şifre (tekrar): ") != password:
                print("  -> Şifreler aynı değil")
                continue
            break

        user.hashed_password = get_password_hash(password)
        user.is_active = True
        db.commit()
        print(f"[OK] {user.full_name} ({user.email}) kullanıcısının şifresi değiştirildi ve hesap aktif edildi.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
