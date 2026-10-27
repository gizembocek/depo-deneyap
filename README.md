# Deneyap Atölyesi – Depo ve Stok Yönetim Sistemi

![Deneyap Depo Sistemi](assets/deneyap_logo.png)

Deneyap Teknoloji Atölyelerindeki elektronik bileşenlerin, sarf malzemelerinin ve demirbaşların kaydını tutan; hangi malzemenin **hangi depoda, hangi dolapta, hangi rafta** olduğunu gösteren; kritik seviyeye düşen malzemeleri otomatik uyaran web tabanlı bir stok yönetim sistemidir.

Her atölye sistemi **kendi bilgisayarına** kurar. Kurulum tek bir dosyaya çift tıklamakla yapılır, ek veritabanı kurulumu gerekmez ve sistem **internet olmadan da** çalışır. Atölyedeki diğer bilgisayar ve tabletler aynı ağ üzerinden tarayıcıyla erişebilir.

## Neden gerekli?

Bir Deneyap atölyesinde yüzlerce farklı malzeme bulunur. Bugün bu malzemeler çoğunlukla dağınık Excel dosyaları ve sözlü iletişimle takip ediliyor. Bunun sonuçları:

- **Malzeme aranırken ders zamanı kaybediliyor.** Hangi dolapta, hangi rafta olduğu bilinmiyor.
- **Biten malzeme geç fark ediliyor.** Sarf malzemesi ders günü bittiğinde ders aksıyor.
- **Bozuk, garantide veya tamirdeki cihazların izi kayboluyor.** Demirbaştan düşülecekler raporlanamıyor.
- **Gelen kolilerde eksik/fazla kontrolü kayıt altına alınmıyor.**
- **Eğitmen ve görevli değiştiğinde bilgi de gidiyor.**

Bu sistem tüm bunları tek bir yerde, herkesin anlayacağı bir arayüzle çözer.

## Özellikler

| Alan | Ne yapar? |
|---|---|
| **Ürün yönetimi** | Fotoğraf, açıklama, kategori, durum (Çalışan / Bozuk / Garantide / Demirbaştan düşülecek…), mevcut / kritik / ideal stok, ders bağlantısı |
| **Konum** | Depo › Dolap › Raf › Bölme hiyerarşisi; her ürünün tam yeri |
| **Arama ve filtre** | Türkçe karakter duyarsız arama ("isik" yazınca "Işıklı" bulunur), kategori/durum/depo/ders filtreleri, sayfalama, Türk alfabesine göre sıralama |
| **Stok hareketleri** | Ekleme, çıkarma, sayım; her hareket kim / ne zaman / önceki → yeni değer / not ile kayıt altında |
| **Giriş / Çıkış işlemleri** | Gelen koli (beklenen vs gelen miktar, koli/fatura fotoğrafı), garantiye/tamire gönderim, demirbaştan düşme, başka atölyeye transfer. Sonradan "Kontrol Et" ile gelen miktar girilir, fark stoğa yansır. Stok eksiye düşmez. |
| **Kritik stok** | Kritik seviyeye düşen ürünler ana panelde ve menüde uyarı olarak görünür |
| **Raporlar** | Depo/kategori/durum/kritik stok filtreli **PDF** (Türkçe karakter destekli) ve **Excel** raporu; "sipariş listesi" için yalnızca kritik stok raporu |
| **Excel'den içe aktarma** | Atölyenin mevcut envanter dosyası doğrudan yüklenir. Başlık satırı otomatik bulunur, tüm sayfalar taranır, "6 Adet" gibi yazımlar okunur. Örnek şablon indirilebilir. |
| **Kullanıcılar** | Yönetici ve kullanıcı (eğitmen/görevli) rolleri, depo bazlı yetki, şifre değiştirme/sıfırlama |
| **Yedekleme** | Tek tıkla tüm verilerin yedeği; format sonrası geri yükleme; veritabanları arası taşıma |
| **Veritabanı kontrolü** | Tutarsız kayıtları, tekrar eden ürünleri, birden çok kez aktarılmış Excel listelerini ve varsayılan şifreli hesapları bulur; yedek alıp güvenle düzeltir |
| **SQL Server desteği** | İsteğe bağlı: `SQL_Server_Kurulum.bat` sihirbazı SQL Server'ı bulur, veritabanını kurar ve verileri taşır |
| **İlk kurulum sihirbazı** | İlk açılışta atölye adı ve yönetici hesabı oluşturulur, Deneyap dersleri otomatik eklenir |

## Kurmadan deneyin

**👉 [deneyap-depo.netlify.app](https://deneyap-depo.netlify.app)**: kurulum gerekmez, bağlantıyı açmanız yeterli.

`demo/` klasörü, sistemin **tarayıcıda çalışan bir deneme sürümünü** içerir: örnek bir atölyenin verileriyle tüm ekranlar gezilebilir, rapor örnekleri indirilebilir; değişiklikler kaydedilmez. Bu klasör Netlify'a bağlıdır (`netlify.toml`); GitHub'a her yüklemede deneme sitesi kendiliğinden güncellenir. Örnek veriler gerçek sunucu kodundan `python demo/olustur.py` ile üretilir.

## Hızlı kurulum (Windows)

1. [Python 3.10 veya üstünü](https://www.python.org/downloads/) kurun (**"Add python.exe to PATH"** kutusunu işaretleyin).
2. Bu sayfada **Code → Download ZIP** ile projeyi indirip bir klasöre çıkarın (ör. `Belgeler\depo-deneyap`).
3. Proje klasöründeki **`Sistemi_Calistir.bat`** dosyasına çift tıklayın.
4. Tarayıcı açılınca **İlk Kurulum** ekranında atölye adını ve yönetici hesabını oluşturun.

İlk çalıştırmada paketlerin inmesi için internet gerekir (1–3 dakika). Sonraki açılışlarda internet gerekmez.

Atölyedeki diğer cihazlardan erişmek için siyah pencerede yazan adresi (ör. `http://192.168.1.20:8000`) kullanın.

Ayrıntılı kurulum, SQL Server kullanımı, yedekten geri yükleme ve sorun giderme için: **[KURULUM.md](KURULUM.md)**

### Diğer işletim sistemleri / elle kurulum

```bash
git clone https://github.com/gizembocek/depo-deneyap.git
cd depo-deneyap
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

Örnek verilerle denemek için (boş veritabanında): `python seed.py`

## Testler

Sistem 137 otomatik API testi ve 28 tarayıcı (arayüz) testi ile doğrulanmıştır. Testler gerçek veritabanınıza dokunmaz.

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest                      # API, güvenlik, rapor, Excel, yedek ve eski veri uyumluluk testleri

pip install playwright && python -m playwright install chromium
python -m pytest tests_e2e            # tarayıcıda uçtan uca arayüz testleri
```

Windows'ta `Testleri_Calistir.bat` dosyası da kullanılabilir. SQL Server kullanıyorsanız `SQL_Server_Test.bat` aynı testleri SQL Server'da geçici veritabanlarında çalıştırır.

## Teknolojiler

- **Sunucu:** Python, FastAPI, SQLAlchemy 2, bcrypt + JWT, OpenPyXL, ReportLab, Pillow
- **Veritabanı:** SQLite (varsayılan) · SQL Server · PostgreSQL
- **Arayüz:** Vanilla JavaScript (tek sayfa uygulama), Tailwind CSS (önceden derlenmiş, yerel), Inter ve Material Icons (yerel)

## Güvenlik

- Yeni kullanıcıları yalnızca yönetici oluşturabilir; ilk yönetici ilk kurulum ekranında oluşturulur.
- Şifreler bcrypt ile saklanır; şifre değişince eski oturumlar geçersiz olur; hatalı girişlere karşı geçici kilit vardır.
- Her kurulumun gizli anahtarı otomatik ve benzersiz üretilir (`backend/.secret_key` – paylaşmayın).
- Kullanıcıların girdiği metinler ekrana güvenli şekilde basılır (XSS koruması); yüklenen görseller doğrulanır.
- Kullanıcılar yalnızca yetki verilen depoları görür.

## Proje yapısı

```
depo-deneyap/
├── Sistemi_Calistir.bat      # tek tıkla kurulum + başlatma
├── SQL_Server_Kurulum.bat    # (isteğe bağlı) SQL Server'a geçiş sihirbazı
├── Veritabani_Kontrol.bat    # veritabanı denetimi / onarımı
├── Veritabanlarini_Bul.bat   # bilgisayardaki tüm veritabanlarını bulup karşılaştırır
├── backend/
│   ├── main.py               # uygulama girişi
│   ├── database.py           # veritabanı bağlantısı (SQLite / SQL Server / PostgreSQL)
│   ├── models.py, schemas.py # tablolar ve doğrulama kuralları
│   ├── auth.py               # kimlik doğrulama ve yetki
│   ├── excel_import.py       # Excel okuma
│   ├── yedekleme.py          # yedek al / geri yükle / taşı
│   ├── veritabani_kontrol.py # veritabanı denetimi ve onarımı
│   ├── mssql_kurulum.py      # SQL Server kurulum sihirbazı
│   ├── sifre_sifirla.py      # unutulan şifreyi sıfırlama
│   ├── routers/              # API uç noktaları
│   ├── tests/, tests_e2e/    # otomatik testler
│   └── uploads/              # ürün fotoğrafları
├── frontend/                 # arayüz (index.html, js/, css/, vendor/)
├── demo/                     # çevrim içi deneme sürümü (Netlify): örnek veriler + demo.js
└── assets/                   # logo, yazı tipleri, örnek görseller
```

API belgeleri sunucu çalışırken `http://localhost:8000/docs` adresindedir.

---
**Geliştirici:** Gizem Böcek — Artvin Deneyap Atölyesi
