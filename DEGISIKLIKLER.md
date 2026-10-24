# Değişiklikler — Sürüm 2.1 (Ekim 2026): SQL Server ve veritabanı denetimi

Bu sürümde veritabanı katmanı SQL Server için baştan sona incelendi, gerçek atölye verisiyle karşılaşılan veri sorunları için denetim ve onarım aracı yazıldı.

## SQL Server'da düzeltilen hatalar

| Sorun | Durum |
|---|---|
| **SQL Server'da tablolar hiç oluşturulamıyordu** (hata 1785 "multiple cascade paths": ürünlere depolardan hem doğrudan hem dolaplar üzerinden zincirleme silme yolu vardı). | SQL Server'da yabancı anahtarlar zincirleme kural olmadan kurulur; bağlı kayıtları uygulama temizler. Aynı davranış SQLite'ta `DB_FK_NO_ACTION=1` ile tüm testlerden geçirildi. |
| Türkçe arama SQL Server'ın harmanlamasına (collation) göre değişiyordu; "ışık", "ISIK", "isik" her sunucuda aynı sonucu vermiyordu. | Arama, harmanlamadan bağımsız Türkçe harf katlamasıyla yapılır. |
| Ürün listesi Türk alfabesine göre sıralanmıyordu (Ç, Ğ, İ, Ö, Ş, Ü yanlış yerde). | SQL Server'da `Turkish_CI_AS` ile sıralanır. |
| Aramada `[`, `%`, `_` karakterleri joker gibi davranıyordu (ör. "[Yedek]" araması). | Kullanıcının yazdığı her karakter düz metin olarak aranır. |
| Çok sayıda ürünü silme/birleştirme SQL Server'ın 2100 parametre sınırına takılıyordu. | İşlemler 500'lük parçalar halinde yapılır. |
| Etkin yönetici sorgusu SQL Server'da geçersiz SQL üretiyordu (`is_active IS 1`): sihirbazın şifre adımı ve kullanıcı rolü/pasif yapma işlemleri hata veriyordu. | `= 1` ile sorgulanıyor. Testler artık çalıştırılan her sorguyu SQL Server diliyle de derleyip bu tür hataları SQL Server olmadan yakalıyor. |
| ODBC Driver 18 ile "sertifika güvenilir değil" bağlantı hatası. | `MSSQL_TRUST_CERT=yes` desteklenir; sihirbaz otomatik yazar. |
| Veritabanı yoksa uygulama anlaşılmaz bir hatayla kapanıyordu. | Yetki varsa veritabanı otomatik oluşturulur; bağlantı hataları ne yapılacağını söyleyen Türkçe mesajlarla gösterilir. |
| Yedekten geri yüklemede kimlik (IDENTITY) sütunları için gereksiz elle komut gönderiliyordu. | Kaldırıldı; kayıt numaraları korunarak yüklenir. |

## Yeni araçlar

- **`SQL_Server_Kurulum.bat`** — SQL Server kurulum sihirbazı: ODBC sürücüsünü ve SQL Server örneğini bulur, hizmeti başlatır, `deneyap_depo` veritabanını oluşturur, SQLite verilerini önce denetleyip taşır (SQLite dosyası değişmez), yönetici şifresini yenileme imkânı verir, Türkçe arama/sıralamayı sınar ve `.env` dosyasını yazar (eskisi yedeklenir). Yalnızca LocalDB veya 180 gün sonra kapanan **deneme sürümü (Evaluation)** bulunursa uyarır ve devam etmeden önce onay ister; birden fazla SQL Server kuruluysa atölyeye uygun sürümü (Express/Standard; yoksa Developer) seçer. Hedef veritabanında zaten veri varsa SQLite ile karşılaştırır; SQLite'taki veriler daha yeniyse uyarıp durur.
- **`Veritabanlarini_Bul.bat`** — bilgisayardaki tüm Deneyap veritabanlarını (her SQL Server örneği, LocalDB, SQLite dosyaları ve yedekleri) bulur; ürün sayılarını ve son işlem tarihlerini yan yana göstererek en güncel olanı belirlemeyi kolaylaştırır. Hiçbir veritabanını değiştirmez.
- **`SQL_Server_Test.bat`** — tüm otomatik testleri ve gerçek verinin taşınmasını SQL Server'da geçici veritabanlarında çalıştırır, sonra bu veritabanlarını siler.
- **Veritabanı kontrolü** (Ayarlar sayfası ve `Veritabani_Kontrol.bat`): eksik tablo/sütun, sahipsiz kayıtlar, tutarsız depo/dolap/raf bağlantıları, varsayılan şifreyle açık kalmış örnek hesaplar, aynı dersin farklı yazımları, **aynı Excel'in birden çok kez aktarılması**, aynı depoda aynı adlı ürünler, ürünsüz gönderimler, güncel olmayan gönderim durumları ve ad boşlukları denetlenir. Düzeltmeden önce otomatik yedek alınır; ürün silen/birleştiren düzeltmeler yalnızca istenirse yapılır, stok hareketi olan bir kopya asla silinmez.
- SQL Server'a geçilip veriler taşınmadan uygulama açılırsa, **İlk Kurulum ekranı** bilgisayardaki eski veritabanında kaç ürün olduğunu söyleyip sihirbazı çalıştırmanızı ister (yanlışlıkla boş veritabanında yeni kurulum yapılmasını önler).
- Python kaldırılıp başka bir sürüm kurulduğunda tüm `.bat` dosyaları "No Python at ..." hatasıyla açılmıyordu. Ortak `_ortam.bat` çalışmayan sanal ortamı fark edip yüklü Python ile yeniden kurar. Testler Python 3.10, 3.12 ve 3.13'te çalıştırıldı.
- `Sistemi_Calistir.bat` tarayıcıyı sabit 4 saniye sonra açıyordu; SQL Server'a ilk bağlantı uzun sürünce "Bu siteye ulaşılamıyor" hatası görünüyordu. Tarayıcı artık sunucu yanıt vermeye başlayınca açılır.
- Pencere açılınca ilk alana yapılan gecikmeli odaklama, yavaş bilgisayarlarda kullanıcı başka alana geçmişken odağı geri alıyor ve yazılanlar (ör. şifre) yanlış alana gidiyordu. Düzeltildi.
- **Çevrim içi deneme sürümü** (`demo/`, Netlify): örnek atölye verileriyle tüm ekranlar kurulum yapmadan tarayıcıda gezilebilir. Veriler gerçek sunucu kodundan üretilir; değişiklikler kaydedilmez.
- **Varsayılan/zayıf şifreyle giriş** yapan kullanıcıdan devam etmeden önce yeni şifre belirlemesi istenir.
- **Toplu silme**de "Sadece depo atanmamış ürünler" seçeneği ve depo başına ürün sayısı.

## Testler

- `backend/tests`: 137 API testi. Testler artık belirli bir atölyenin veri dosyasına bağlı değildir; eski sürüm veritabanının sorunlarını taşıyan örnek bir veritabanı (`tests/eski_veri.py`) her bilgisayarda oluşturulur.
- `backend/tests_e2e`: 28 tarayıcı testi (Ayarlar sayfasından eski veritabanı temizliği dahil).
- Tüm testler Python 3.10, 3.12 ve 3.13'te, ayrıca SQL Server'ın yabancı anahtar davranışını taklit eden kipte çalıştırıldı.
- Test sırasında oluşan görseller ve yedekler artık gerçek `uploads` / `yedekler` klasörlerine yazılmaz.
- Tüm testler gerçek bir SQL Server 2025 Express üzerinde de çalıştırıldı. Windows'ta Türkçe çıktı okunamadığı için 4 testin hatalı sonuç vermesine yol açan kod sayfası sorunu giderildi.

---

# Değişiklikler — Sürüm 2.0 (Ekim 2026)

Bu sürümde projenin tamamı incelendi; hatalar gerçek verilerle (884 ürünlük veritabanı) tekrarlanıp düzeltildi ve her düzeltme otomatik testle güvenceye alındı.

## Kritik güvenlik düzeltmeleri

| Sorun (eski sürüm) | Durum |
|---|---|
| **Giriş yapmadan herkes kendine yönetici hesabı açabiliyordu** (`/api/auth/register` herkese açıktı ve rol seçilebiliyordu). | Kullanıcıyı artık yalnızca yönetici oluşturur. İlk yönetici "İlk Kurulum" ekranında, sadece veritabanı boşken oluşturulur. |
| **Tarayıcıdan `.env` dosyası okunabiliyordu** (`/..%2fbackend%2f.env`). Gizli anahtar ele geçirilince sahte oturum açılabiliyordu. | Yalnızca `frontend` klasörü içindeki dosyalar verilir. |
| Gizli anahtar (SECRET_KEY) örnek değerde kalmıştı / koda sabit yazılmıştı. | Her kurulum için rastgele anahtar otomatik üretilir (`backend/.secret_key`). |
| Ürün adı, not, depo adı gibi alanlara yazılan HTML/JS kodu sayfada çalışıyordu (XSS). | Tüm kullanıcı metinleri güvenli biçimde ekrana basılıyor. |
| Görsel yükleme yalnızca dosya uzantısına bakıyordu. | Dosya içeriği doğrulanıyor, büyük görseller küçültülüyor. |
| `sifre_sifirla.py` sistemdeki **tüm** hesapların şifresini `123456` yapıyordu. | Yalnızca seçilen kullanıcının şifresini, güçlü şifre kuralıyla değiştiriyor. |
| Hatalı girişlere sınır yoktu. | 15 dakikada 10 hatalı denemeden sonra geçici kilit. |
| Kullanıcı kendi yönetici yetkisini kaldırıp sistemi yöneticisiz bırakabiliyordu. | En az bir aktif yönetici kalması zorunlu. |
| Yetkisi olmayan kullanıcı başka depoların ürün geçmişini ve yapısını görebiliyordu. | Depo yetkileri tüm uç noktalarda uygulanıyor. |

## Hata düzeltmeleri

- **884 üründen yalnızca 50'si listeleniyordu.** Sayfalama eklendi (toplam sayı, sayfa numaraları).
- **Çıkış işlemi stoğu eksiye düşürüyordu** (örnek: Multimetre −993). Artık stok yetersizse işlem yapılmaz.
- **PDF raporunda Türkçe harfler (ş, ğ, ı, İ) "■" olarak çıkıyordu.** Türkçe destekli yazı tipi eklendi.
- **Boş veritabanıyla ilk çalıştırmada 500 hatası** (tablolar oluşturulmuyordu). Eksik tablolar her açılışta güvenle oluşturuluyor.
- **`supabase` paketi kurulu değilse uygulama hiç açılmıyordu.** Supabase isteğe bağlı hale getirildi.
- **`Oto_Kurulum_Baslat.bat` ön yüzü 3000 portunda açtığı için uygulama çalışmıyordu.** Tek pencerede çalışan kurulum betiği yazıldı.
- Gönderim "kontrol" özelliği arayüzde vardı ama sunucuda karşılığı yoktu (`/check`). Eklendi.
- Kullanıcılar sayfasındaki "Depo erişimi" düğmesi tanımsız bir fonksiyonu çağırıyordu. Ekran yazıldı.
- Ana paneldeki kartlara tıklamak JavaScript hatası veriyordu (filtreler sıfırlanırken).
- Gönderim formunda yalnızca ilk 50 ürün seçilebiliyordu. Sunucuda arama yapan ürün seçici yazıldı.
- Kritik stok 0 girilemiyordu (5'e dönüyordu).
- Depo adında tırnak işareti (ör. *Gizem'in Deposu*) varsa düzenleme düğmesi bozuluyordu.
- Excel içe aktarmada aynı dosyada tekrar eden ürünler iki kez ekleniyordu; "Sayfa1" gibi sayfa adları ders olarak açılıyordu; .xls dosyası anlamsız hata veriyordu.
- Türkçe arama: "ışık", "ISIK", "isik" aramaları artık "Işıklı Büyüteç"i buluyor.
- Silinen gönderim kaydının stok hareketleri geri alınmıyordu (artık isteğe bağlı geri alınıyor).
- Ürün düzenlemede stok veya durum değişikliği geçmişe yazılmıyordu.
- Dolap/depo seçimi tutarsız olabiliyordu (başka depoya ait dolap seçilebiliyordu).
- Toplu silme SQL Server'da yabancı anahtar hatası verebiliyordu.
- Doğrulama hataları "[object Object]" olarak görünüyordu; artık anlaşılır Türkçe mesajlar.

## Yeni özellikler

- **İlk Kurulum sihirbazı:** atölye adı, il, yönetici hesabı, standart Deneyap dersleri.
- **Şifremi değiştir** (herkes) ve **şifre sıfırla** (yönetici).
- **Depo erişimi** ekranı ve yeni kullanıcı oluştururken depo seçimi.
- **Gönderim kontrolü:** "Kontrol Et" ile gelen miktar girilir, fark stoğa yansır; koli/fatura fotoğrafları görüntülenebilir.
- **Ayarlar ve Yedek** sayfası: atölye adı, tek tıkla yedek indirme; `yedekleme.py` ile geri yükleme ve veritabanı taşıma.
- **Excel şablonu** indirme; Miktar/Kategori/Durum/Kritik/İdeal/Ders/Açıklama sütunlarını tanıyan içe aktarma.
- Raporlarda durum ve "yalnızca kritik stok" filtresi, konum ve eksik miktar sütunları, kritik satırların vurgulanması.
- Ana panelde son işlemler; ders ve depo kartlarında ürün sayıları; ürünlerde sıralama ve ders filtresi.
- Dolap/raf/bölme yeniden adlandırma; ders yeniden adlandırma.
- Arayüz artık **internetsiz** çalışır (Tailwind CSS, yazı tipleri ve ikonlar yerel).
- Tarayıcı geri tuşu ve sayfa yenileme bulunduğunuz sayfayı korur; mobil uyum iyileştirildi.

## Testler

- `backend/tests`: 81 API testi (güvenlik, yetki, stok kuralları, gönderim, rapor, Excel, yedek ve **eski veritabanı uyumluluğu**).
- `backend/tests_e2e`: 20 tarayıcı testi (ilk kurulumdan rapor indirmeye kadar gerçek kullanım akışları, konsol hatası kontrolü dahil).
- Testler hem Python 3.13 hem de mevcut kurulumdaki sürümlerle (Python 3.10, FastAPI 0.136, SQLAlchemy 2.0) çalıştırıldı.

## Mevcut kurulum için notlar

- Veritabanı yapısı değişmedi; yalnızca yeni `app_settings` tablosu otomatik eklenir. Mevcut veriler korunur.
- Güvenlik anahtarı yenilendiği için güncellemeden sonra herkes **bir kez** yeniden giriş yapar.
- `sifre_sifirla.py`'nin eski sürümüyle tüm şifreler `123456` yapıldıysa, giriş yaptıktan sonra **Şifremi Değiştir** ile değiştirin.
