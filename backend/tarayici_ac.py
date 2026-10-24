"""
Sistemi_Calistir.bat tarafından arka planda çalıştırılır: sunucu gerçekten yanıt vermeye
başlayınca tarayıcıyı açar. (Sabit bir süre beklemek yetmiyordu; SQL Server'a ilk bağlantı
birkaç saniye sürdüğünde tarayıcı "Bu siteye ulaşılamıyor" hatasıyla açılıyordu.)

Kullanım:  python tarayici_ac.py [adres] [en_fazla_bekleme_saniyesi]
"""
import sys
import time
import urllib.request
import webbrowser


# Okul/kurum ağındaki proxy ayarları yerel sunucuya erişimi engellemesin
_ACICI = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def sunucu_hazir(saglik_adresi: str, zaman_asimi: float = 1.0) -> bool:
    try:
        with _ACICI.open(saglik_adresi, timeout=zaman_asimi) as yanit:
            return yanit.status < 500
    except Exception:
        return False


def bekle_ve_ac(adres: str = "http://localhost:8000", en_fazla: float = 120, aralik: float = 0.5,
                ac=webbrowser.open) -> bool:
    """Sunucu hazır olunca tarayıcıyı açar. Sunucu hiç açılmazsa tarayıcı açılmaz
    (hata siyah pencerede görünür)."""
    saglik = adres.replace("://localhost", "://127.0.0.1").rstrip("/") + "/api/health"
    bitis = time.monotonic() + en_fazla
    hazir = False
    while time.monotonic() < bitis:
        if sunucu_hazir(saglik):
            hazir = True
            break
        time.sleep(aralik)
    if hazir:
        ac(adres)
    return hazir


if __name__ == "__main__":
    adres = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    en_fazla = float(sys.argv[2]) if len(sys.argv) > 2 else 120
    bekle_ve_ac(adres, en_fazla)
