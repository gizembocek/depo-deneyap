# Deneyap Depo Yönetimi — Kurulum Rehberi

Bu rehber, sistemi bir atölye bilgisayarına sıfırdan kurmak, atölyedeki diğer cihazlardan kullanmak, yedek almak ve sorunları çözmek için gereken her şeyi içerir.

---

## 1. En kolay kurulum (önerilen: SQLite, ek program gerekmez)

1. **Python kurun:** https://www.python.org/downloads/ → Python 3.10 veya üstü.
   Kurulumun ilk ekranında **"Add python.exe to PATH"** kutusunu mutlaka işaretleyin.
2. Proje klasörünü bilgisayara kopyalayın (ör. `Belgeler\depo-deneyap`).
3. **`Sistemi_Calistir.bat`** dosyasına çift tıklayın.
   - İlk çalıştırmada `venv` klasörü oluşturulur ve paketler indirilir (internet gerekir, 1–3 dk).
   - Ardından tarayıcı `http://localhost:8000` adresinde açılır.
4. **İlk Kurulum** ekranında atölye adını, ilinizi ve yönetici hesabını oluşturun.
   "Deneyap derslerini otomatik ekle" seçeneği açıksa standart dersler hazır gelir.
5. Kullanmaya başlayın:
   - **Depolar** → depo ekleyin, "Dolap/Raf Yapısı"ndan dolap, raf, bölme tanımlayın.
   - **Ürünler** → "Excel İle Ekle" ile mevcut envanter dosyanızı yükleyin veya tek tek ürün ekleyin.
   - **Kullanıcılar** → eğitmen/görevli hesapları açın ve hangi depoları görebileceklerini seçin.

Veriler `backend\deneyap_depo.db` dosyasında tutulur. Sistemi kapatmak için siyah pencereyi kapatmanız yeterlidir.

### Atölyedeki diğer bilgisayar ve tabletlerden erişim

Sistemi çalıştıran bilgisayar açık olduğu sürece, aynı Wi‑Fi/ağdaki cihazlar tarayıcıdan `http://<bilgisayarın-IP-adresi>:8000` adresine girebilir. IP adresi siyah pencerede "ornek:" satırında yazar.
Windows Güvenlik Duvarı ilk seferde sorarsa **"Erişime izin ver"** deyin (Özel ağlar).

### Bilgisayar açılınca otomatik başlasın (isteğe bağlı)

`Win + R` → `shell:startup` yazın → açılan klasöre `Sistemi_Calistir.bat` dosyasının **kısayolunu** koyun.

---

## 2. Yedekleme ve geri yükleme

### Yedek alma
- Uygulamada **Ayarlar ve Yedek → Yedek İndir**. Tek bir `.json` dosyası iner; tüm ürünler, depolar, kullanıcılar ve işlem geçmişi içindedir.
- Yedeği **ayda en az bir kez** alın ve bilgisayar dışında (USB bellek, Google Drive vb.) saklayın.
- SQLite kullanıyorsanız sistem kapalıyken `backend\deneyap_depo.db` dosyasını kopyalamak da tam yedektir.

### Format sonrası / yeni bilgisayara geri yükleme
1. Bölüm 1'deki adımlarla sistemi kurun, **ilk kurulum ekranını doldurmadan** pencereyi kapatın.
2. `backend` klasöründe bir komut penceresi açın (klasörün adres çubuğuna `cmd` yazıp Enter) ve:
   ```cmd
   ..\venv\Scripts\python.exe yedekleme.py yukle C:\Yol\deneyap_yedek_20261022_1530.json
   ```
3. `Sistemi_Calistir.bat` ile başlatın ve eski hesabınızla giriş yapın.

> Geri yükleme yalnızca **boş** veritabanına yapılır; dolu bir veritabanının üzerine yazmaz.

### Veritabanları arası taşıma (ör. SQLite → SQL Server)
SQL Server'a geçiş için en kolay yol **`SQL_Server_Kurulum.bat`** sihirbazıdır (Bölüm 4). Elle taşımak isterseniz (`backend` klasöründe):
```cmd
..\venv\Scripts\python.exe yedekleme.py tasi --kaynak "sqlite:///deneyap_depo.db" --hedef "mssql+pyodbc://..."
```

---

## 3. Şifre unutulursa

- **Kullanıcı** şifresini unuttuysa: yönetici **Kullanıcılar** sayfasında kullanıcının satırındaki "Şifre sıfırla" (kilit simgeli) düğmesini kullanır.
- **Yönetici** şifresini unuttuysa (sunucu bilgisayarında, `backend` klasöründe):
  ```cmd
  ..\venv\Scripts\python.exe sifre_sifirla.py                     (kullanıcıları listeler)
  ..\venv\Scripts\python.exe sifre_sifirla.py yonetici@deneyap.org  (yeni şifre sorar)
  ```

---

## 4. SQL Server ile kurulum (isteğe bağlı)

Çoğu atölye için SQLite yeterlidir ve hiçbir ek program gerektirmez. Kurumunuz SQL Server istiyorsa veya verileri SQL Server'da tutmak istiyorsanız aşağıdaki adımlar yeterlidir; komut yazmanız gerekmez.

### 4.1 SQL Server Express'i kurun (ücretsiz)
1. https://www.microsoft.com/tr-tr/sql-server/sql-server-downloads adresinde **SQL Server 2025 Express** başlığının altındaki **Şimdi indirin** düğmesine tıklayın (dosya adı `SQL2025-SSEI-Expr.exe`). SQL Server 2022 Express de çalışır.
2. Dosyayı açın, kurulum türü olarak **Temel (Basic)** seçin, lisansı kabul edip **Yükle** deyin. Kurulum 5–15 dk sürer.
3. Kurulum bitince ekranda **Express Edition** ve **Örnek adı: SQLEXPRESS** yazar. Bu pencereyi kapatabilirsiniz; SSMS kurmanız gerekmez.

> **Dikkat — "Evaluation Edition" kurmayın.** İndirme sayfasındaki "Ücretsiz deneme / Free trial" bağlantısı **deneme sürümünü** indirir: kurulum sonunda "Evaluation Edition" yazar ve **180 gün sonra çalışmayı durdurur**, içindeki verilere erişilemez. Yanlışlıkla kurduysanız *Ayarlar → Uygulamalar → Microsoft SQL Server 2025 → Kaldır → Remove* ile kaldırıp Express'i kurun. Sihirbaz deneme sürümünü tanır ve uyarır; hem deneme hem Express kuruluysa Express'i seçer. "Developer" sürümleri süresizdir ama lisansı yalnızca geliştirme/test içindir; atölye için yine Express önerilir.

> Gereksinimler: Windows 10/11 (64 bit), en az 6 GB boş disk. Express sürümünde veritabanı başına 50 GB sınırı vardır; bir atölye için fazlasıyla yeterlidir.
> Bilgisayarda yalnızca **LocalDB** (Visual Studio ile gelen geliştirici sürümü) varsa sihirbaz bunu söyler ve devam etmeden önce onay ister. Atölye için Express kurun.

### 4.2 Sihirbazı çalıştırın: `SQL_Server_Kurulum.bat`
Proje klasöründeki **`SQL_Server_Kurulum.bat`** dosyasına çift tıklayın. Sihirbaz sırayla:

1. **ODBC sürücüsünü** kontrol eder. Bulamazsa indirme adresini yazar: [ODBC Driver 18 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server) (Windows x64 sürümünü kurup sihirbazı tekrar çalıştırın).
2. **SQL Server'ı bulur** (`.\SQLEXPRESS` gibi). Hizmet kapalıysa başlatmayı dener; izin hatası alırsanız dosyaya sağ tıklayıp **Yönetici olarak çalıştır** deyin.
3. **`deneyap_depo` veritabanını** oluşturur ve tabloları kurar.
4. **Mevcut verilerinizi taşır** (`backend\deneyap_depo.db`). Önce bir veri kontrolü raporu gösterir; güvenli düzeltmeleri taşınan *kopyada* yapar. SQLite dosyanız değiştirilmez ve yedek olarak durur.
   - SQL Server'daki veritabanında zaten veri varsa taşıma yapılmaz; iki veritabanının ürün sayıları ve son işlem tarihleri gösterilir. SQLite'taki veriler daha yeniyse sihirbaz uyarıp durur ve verileri yeni bir veritabanına taşıma komutunu yazar.
   - **4b.** Giriş yapabilecek yönetici hesabını gösterir; şifrenizi hatırlamıyorsanız burada yenileyebilirsiniz.
5. **Türkçe karakter, Türkçe arama** (ı/İ, ş/Ş…) ve **Türk alfabesi sıralamasının** SQL Server'da doğru çalıştığını sınar.
6. **`backend\.env`** dosyasını yazar (`DB_BACKEND=mssql` …). Eski `.env` dosyanız `.env.yedek_<tarih>` adıyla saklanır; içindeki güvenlik anahtarı ve diğer ayarlar korunur.

> **Önemli:** SQL Server'ı kurduktan sonra uygulamayı açmadan **önce** sihirbazı çalıştırın. Uygulama boş bir SQL Server veritabanıyla açılırsa "İlk Kurulum" ekranı gelir; bilgisayarda taşınmamış eski veriler varsa bu ekran sarı bir uyarıyla bunu söyler. Bu durumda yeni kurulum yapmayın, sihirbazı çalıştırın.

Ekranda **"SQL Server HAZIR"** yazınca `Sistemi_Calistir.bat` ile uygulamayı başlatın. Uygulama artık SQL Server'ı kullanır; **Ayarlar ve Yedek → Veritabanı Kontrolü → Kontrol Et** satırında `Veritabanı: mssql` görünür.

İleri seviye seçenekler (komut penceresinde `SQL_Server_Kurulum.bat --help`):

| Seçenek | Ne yapar |
|---|---|
| `--sunucu ".\SQLEXPRESS"` | Sunucuyu kendiniz belirtin (otomatik bulma yerine) |
| `--sql-kullanici sa` | Windows yerine SQL Server kullanıcısıyla bağlan (şifre sorulur) |
| `--kopya-sil` / `--birlestir` / `--bos-gonderim-sil` | Taşırken aynı Excel'in kullanılmamış kopyalarını, aynı adlı ürün tekrarlarını, ürünsüz gönderimleri alma |
| `--evet` | Tüm sorulara varsayılan cevabı ver (otomatik kurulum) |
| `--env-yazma` | `.env` dosyasını değiştirme |

### 4.3 SQL Server üzerinde testleri çalıştırın: `SQL_Server_Test.bat`
Kurulumdan sonra **`SQL_Server_Test.bat`** dosyasına çift tıklayın. Tüm otomatik testler SQL Server'da **geçici** veritabanlarında çalışır, gerçek verilerinizin bir kopyası da geçici veritabanına taşınarak denenir; işlem bitince geçici veritabanları silinir. Gerçek `deneyap_depo` veritabanınıza dokunulmaz. Sonunda tüm satırlar `passed` olmalıdır.

### 4.4 SQLite'a geri dönmek
`backend\.env` dosyasında `DB_BACKEND=sqlite` yazıp uygulamayı yeniden başlatın (veya sihirbazın sakladığı `.env.yedek_<tarih>` dosyasını `.env` adıyla geri koyun). SQLite dosyanız SQL Server'a geçtikten sonraki kayıtları içermez; SQL Server'daki güncel verileri SQLite'a almak için önce **Yedek İndir** ile yedek alıp Bölüm 2'deki gibi boş bir SQLite veritabanına yükleyin.

### 4.5 Elle kurulum (sihirbaz kullanmadan)
1. SQL Server ve ODBC Driver 18'i kurun (4.1).
2. `backend\.env.example` dosyasını `backend\.env` olarak kopyalayıp şunları yazın:
   ```env
   DB_BACKEND=mssql
   MSSQL_HOST=.\SQLEXPRESS
   MSSQL_DB=deneyap_depo
   MSSQL_WINDOWS_AUTH=1
   MSSQL_TRUST_CERT=yes
   ```
   - Varsayılan örnek (MSSQLSERVER) kullanıyorsanız: `MSSQL_HOST=localhost`
   - `MSSQL_PORT` ve `MSSQL_DRIVER` satırlarını boş bırakın (sürücü otomatik bulunur; port yazılırsa yalnızca TCP denenir).
   - `DATABASE_URL` satırı varsa MSSQL ayarlarını geçersiz kılar; kullanmıyorsanız silin.
3. `Sistemi_Calistir.bat` ile başlatın. Veritabanı yoksa ve yetkiniz varsa otomatik oluşturulur; tablolar ilk açılışta kurulur. `.env` içinde `DB_BACKEND=mssql` görülürse `pyodbc` paketi de otomatik kurulur.
4. SQL Server başka bir bilgisayardaysa: **SQL Server Configuration Manager** → `SQL Server Ağ Yapılandırması` → `SQLEXPRESS İçin Protokoller` → **TCP/IP: Etkin** → hizmeti yeniden başlatın ve güvenlik duvarında 1433 portuna izin verin. Uygulama ile SQL Server aynı bilgisayardaysa bu adım gerekmez.

---

## 5. Veritabanı kontrolü ve onarım

Veritabanını (SQLite veya SQL Server) tutarsız kayıtlara, tekrar eden ürünlere ve güvenlik sorunlarına karşı denetlemek için:

- Uygulamada **Ayarlar ve Yedek → Veritabanı Kontrolü → Kontrol Et**. Bulunan sorunlar önem sırasıyla listelenir; **Düzeltmeleri Uygula** önce sunucuda otomatik yedek alır (`backend\yedekler`), sonra güvenli düzeltmeleri yapar. Ürün silen/birleştiren düzeltmeler yalnızca kutucuğu işaretlerseniz yapılır.
- Ya da **`Veritabani_Kontrol.bat`** dosyasına çift tıklayın (yalnızca rapor verir, hiçbir şeyi değiştirmez). Düzeltmek için komut penceresinde:
  ```cmd
  Veritabani_Kontrol.bat --duzelt
  Veritabani_Kontrol.bat --duzelt --kopya-aktarimlari-sil --tekrar-eden-urunleri-birlestir --bos-gonderimleri-sil
  ```

Bilgisayarda birden fazla veritabanı varsa (ör. eski bir SQL Server ve SQLite dosyası) hangisinin en güncel olduğunu görmek için **`Veritabanlarini_Bul.bat`** dosyasına çift tıklayın. Kurulu tüm SQL Server örneklerindeki ve `backend` klasöründeki Deneyap veritabanlarını, ürün/kullanıcı sayılarını, son işlem tarihlerini, SQL Server yedeklerini (.bak) ve bağlı olmayan veritabanı dosyalarını listeler; hiçbir veritabanını değiştirmez.

Neler denetlenir: kayıp/eksik tablo ve sütunlar, sahipsiz kayıtlar, yanlış depo/dolap/raf bağlantıları, varsayılan şifreyle açık kalmış örnek hesaplar, aynı dersin farklı yazımları, aynı Excel'in birden çok kez aktarılması, aynı depoda aynı adlı ürünler, ürünsüz gönderimler, güncel olmayan gönderim durumları, ad başındaki/sonundaki boşluklar.

> Stok hareketi veya gönderimi olan bir ürün kopyası **asla** otomatik silinmez; böyle bir durumda rapor elle kontrol etmenizi ister.

---

## 6. Sorun giderme

| Belirti | Çözüm |
|---|---|
| `.bat` dosyasını açınca "Windows bilgisayarınızı korudu" uyarısı | İnternetten (ör. GitHub'dan ZIP olarak) indirilen dosyalarda normaldir. **Ek bilgi → Yine de çalıştır** deyin. |
| `Python kurulu degil` | Python'u kurarken "Add python.exe to PATH" işaretlenmemiş. Python'u kaldırıp işaretleyerek tekrar kurun. |
| `No Python at 'C:\...\Python310\python.exe'` | Python kaldırılıp başka sürüm kurulmuş; `venv` klasörü eski Python'u arıyor. `.bat` dosyaları bunu kendisi fark edip `venv` klasörünü yüklü Python ile yeniden kurar (internet gerekir). Verileriniz etkilenmez. |
| `Paketler kurulamadi` | İlk kurulumda internet gerekir. Okul ağı engelliyorsa telefondan internet paylaşarak deneyin. |
| Tarayıcı açılıyor ama sayfa gelmiyor | Siyah pencerede hata var mı bakın. Port 8000'i başka program kullanıyor olabilir; bilgisayarı yeniden başlatın. |
| Diğer cihazlardan açılmıyor | Cihazlar aynı ağda mı? Güvenlik duvarında Python'a izin verildi mi? Adres `http://` ile başlamalı. |
| `Oturumunuz sona erdi` | Güncellemeden sonra bir kez yeniden giriş yapılması normaldir (güvenlik anahtarı yenilenir). |
| PDF'te Türkçe harfler bozuk | `assets\fonts\DejaVuSans.ttf` dosyasının yerinde olduğundan emin olun. |
| `IM002 ... Veri kaynağı adı bulunamadı` (SQL Server) | ODBC sürücüsü kurulu değil. [ODBC Driver 18 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server) kurun (Windows x64). |
| `Named Pipes / TCP Provider ... erişilemiyor` (SQL Server) | SQL Server hizmeti çalışıyor mu? (Başlat → "Hizmetler" → `SQL Server (SQLEXPRESS)` → Başlat). Adres `.\SQLEXPRESS` olmalı. |
| `Login failed for user` (SQL Server) | Windows hesabınızın SQL Server'da yetkisi yok. SQL Server'ı kuran Windows hesabıyla oturum açın veya `--sql-kullanici` seçeneğini kullanın. |
| `CREATE DATABASE permission denied` | Sihirbazı SQL Server'ı kuran Windows hesabıyla çalıştırın veya veritabanını yöneticinize oluşturtun. |
| `certificate chain ... not trusted` (SQL Server) | `.env` içinde `MSSQL_TRUST_CERT=yes` olmalı (sihirbaz bunu kendisi yazar). |
| Sihirbaz "DENEME sürümü (Evaluation Edition)" diyor | Yanlış sürüm kurulmuş. 4.1'deki uyarıya göre kaldırıp **Express** sürümünü kurun. |
| Sihirbaz "LocalDB" buldu diyor | SQL Server Express kurulumu bitmemiş veya hiç kurulmamış. 4.1'deki adımları tamamlayıp sihirbazı tekrar çalıştırın. |
---

## 7. Güncelleme

1. Ayarlar sayfasından **yedek alın**.
2. Yeni sürümün dosyalarını eski klasörün üzerine kopyalayın (`venv`, `backend\deneyap_depo.db`, `backend\.env`, `backend\.secret_key` ve `backend\uploads` korunur).
3. `Sistemi_Calistir.bat` ile başlatın. Eksik tablolar otomatik eklenir; mevcut veriler değişmez.
