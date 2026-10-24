"""
Tarayıcı ile uçtan uca arayüz testleri (Playwright).

Kurulum:   pip install pytest playwright pypdf openpyxl   ve   python -m playwright install chromium
Çalıştırma (backend klasöründe):   python -m pytest tests_e2e -q

Her test oturumu geçici bir veritabanıyla ayrı bir sunucu başlatır; gerçek verilerinize dokunulmaz.
"""
import os
import re
import socket
import subprocess
import sys
import tempfile
import time

import pytest

playwright_api = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN_EMAIL, ADMIN_PASS = "gizem@deneyap.org", "Deneyap2026"
SERVER_DB_URL = {}
USER_EMAIL, USER_PASS = "egitmen@deneyap.org", "Egitmen2026"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_server(db_url: str, tmp: str):
    port = _free_port()
    env = dict(os.environ)
    env["DATABASE_URL"] = db_url
    env["SECRET_KEY"] = "e2e-anahtar-0123456789abcdef0123456789"
    env["UPLOAD_DIR"] = os.path.join(tmp, "uploads")  # test görselleri gerçek 'uploads' klasörüne yazılmasın
    env["YEDEK_KLASORU"] = os.path.join(tmp, "yedekler")  # düzeltme öncesi yedekler de geçici klasöre
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--port", str(port)],
                            cwd=BACKEND_DIR, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    import httpx
    for _ in range(150):
        try:
            if httpx.get(base + "/api/health", timeout=1).status_code == 200:
                return base, proc
        except Exception:
            time.sleep(0.1)
    proc.kill()
    raise RuntimeError("Sunucu başlamadı")


def _stop_server(proc):
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture(scope="session")
def server():
    tmp = tempfile.mkdtemp(prefix="deneyap_e2e_")
    url = os.getenv("TEST_DATABASE_URL") or ("sqlite:///" + os.path.join(tmp, "e2e.db").replace("\\", "/"))
    SERVER_DB_URL["url"] = url
    base, proc = _start_server(url, tmp)
    yield base
    _stop_server(proc)


class PageWatcher:
    """Konsol hatalarını, JS istisnalarını ve başarısız istekleri toplar."""
    def __init__(self, page):
        self.errors = []
        page.on("pageerror", lambda e: self.errors.append(f"JS hatası: {e}"))
        page.on("console", lambda m: self.errors.append(f"console: {m.text}") if m.type == "error" and "status of 4" not in m.text else None)
        page.on("requestfailed", lambda r: self.errors.append(f"İstek başarısız: {r.url}") if "/api/" not in r.url else None)


@pytest.fixture
def page(browser, server):
    ctx = browser.new_context(viewport={"width": 1366, "height": 900}, accept_downloads=True, locale="tr-TR")
    pg = ctx.new_page()
    pg.set_default_timeout(10000)
    watcher = PageWatcher(pg)
    pg.goto(server)
    yield pg
    ctx.close()
    assert not watcher.errors, watcher.errors


def api(server, token=None):
    import httpx
    return httpx.Client(base_url=server, headers={"Authorization": f"Bearer {token}"} if token else {}, timeout=30)


def admin_token(server):
    r = api(server).post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    return r.json()["access_token"]


def login(pg, email=ADMIN_EMAIL, password=ADMIN_PASS):
    pg.fill("#loginEmail", email)
    pg.fill("#loginPassword", password)
    pg.click("#loginBtn")
    expect(pg.locator("h1", has_text="Ana Panel")).to_be_visible()


def toast(pg, text):
    expect(pg.locator("#toastContainer", has_text=text)).to_be_visible()


# Testler sırayla çalışır ve aynı veritabanını kullanır (gerçek kullanım senaryosu gibi).

def test_01_ilk_kurulum_ekrani(page):
    expect(page.locator("#setupCard")).to_be_visible()
    expect(page.locator("#loginCard")).to_be_hidden()
    page.fill("#setupAtolye", "Artvin Deneyap Teknoloji Atölyesi")
    page.fill("#setupIl", "Artvin")
    page.fill("#setupName", "Gizem Böcek")
    page.fill("#setupEmail", ADMIN_EMAIL)
    page.fill("#setupPassword", "zayif")
    page.fill("#setupPassword2", "zayif")
    page.click("#setupBtn")
    expect(page.locator("#setupError")).to_contain_text("8 karakter")
    page.fill("#setupPassword", ADMIN_PASS)
    page.fill("#setupPassword2", ADMIN_PASS)
    page.click("#setupBtn")
    expect(page.locator("h1", has_text="Ana Panel")).to_be_visible()
    expect(page.locator("#sidebarAtolye")).to_have_text("Artvin Deneyap Teknoloji Atölyesi")
    expect(page.locator("text=Henüz ürün eklenmemiş.")).to_be_visible()


def test_02_kurulumdan_sonra_giris_ekrani(page):
    expect(page.locator("#loginCard")).to_be_visible()
    expect(page.locator("#setupCard")).to_be_hidden()
    expect(page.locator("#loginSubtitle")).to_have_text("Artvin Deneyap Teknoloji Atölyesi")
    page.fill("#loginEmail", ADMIN_EMAIL)
    page.fill("#loginPassword", "YanlisSifre1")
    page.click("#loginBtn")
    expect(page.locator("#loginError")).to_contain_text("Geçersiz")
    login(page)


def test_03_depo_ve_dolap_raf_yapisi(page):
    login(page)
    page.click("[data-page=warehouses]")
    page.click("text=Yeni Depo")
    page.fill("#whName", "Gizem'in \"Ana\" Deposu")  # tırnak işaretleri eski sürümde arayüzü bozuyordu
    page.fill("#whLoc", "Zemin kat")
    page.click("#whSubmit")
    toast(page, "Depo eklendi")
    expect(page.locator("h3", has_text="Gizem'in \"Ana\" Deposu")).to_be_visible()

    page.click("button[title='Düzenle']")
    expect(page.locator("#whName")).to_have_value("Gizem'in \"Ana\" Deposu")
    page.keyboard.press("Escape")

    page.click("text=Dolap/Raf Yapısı")
    page.click("text=Dolap Ekle")
    page.fill("#promptInput", "Dolap A")
    page.click("#promptSubmitBtn")
    expect(page.locator("#modalBody", has_text="Dolap A")).to_be_visible()
    page.click("button[title='Raf ekle']")
    page.fill("#promptInput", "Raf 1")
    page.click("#promptSubmitBtn")
    expect(page.locator("#modalBody", has_text="Raf 1")).to_be_visible()
    page.click("button[title='Bölme ekle']")
    page.fill("#promptInput", "Bölme 1")
    page.click("#promptSubmitBtn")
    expect(page.locator("#modalBody", has_text="Bölme 1")).to_be_visible()


def test_04_urun_ekleme_formu_konum_ile(page):
    login(page)
    page.click("[data-page=products]")
    page.click("#addProductBtn")
    page.fill("#pfName", "Arduino Uno R3")
    page.select_option("#pfCategory", "Elektronik Bileşen")
    page.fill("#pfStock", "10")
    page.fill("#pfCritical", "0")  # eski sürümde 0 girilemiyordu (5'e dönüyordu)
    page.fill("#pfIdeal", "30")
    page.select_option("#pfWarehouse", label="Gizem'in \"Ana\" Deposu")
    page.wait_for_selector("#pfCabinet")
    page.select_option("#pfCabinet", label="Dolap A")
    page.select_option("#pfShelf", label="Raf 1")
    page.select_option("#pfComp", label="Bölme 1")
    page.locator("#productForm label", has_text="Robotik Kodlama").locator("input").check()
    page.click("#productSubmitBtn")
    toast(page, "Ürün eklendi")
    card = page.locator(".product-card", has_text="Arduino Uno R3")
    expect(card).to_contain_text("Dolap A › Raf 1 › Bölme 1")
    card.click()
    expect(page.locator("#modalBody")).to_contain_text("Robotik Kodlama")
    expect(page.locator("#modalBody")).to_contain_text("Bölme: Bölme 1")
    page.click("#modalFooter >> text=Düzenle")
    expect(page.locator("#pfCritical")).to_have_value("0")


def test_05_xss_korumasi(page, server):
    """Ürün adına yazılan HTML/JS kodu çalışmamalı, düz metin olarak görünmeli."""
    payload = '<img src=x onerror="window.__xss=1">'
    c = api(server, admin_token(server))
    assert c.post("/api/products/", json={"name": payload, "description": "<script>window.__xss=2</script>"}).status_code == 200
    login(page)
    page.click("[data-page=products]")
    expect(page.locator(".product-card", has_text=payload)).to_be_visible()
    page.locator(".product-card", has_text=payload).click()
    expect(page.locator("#modalTitle")).to_have_text(payload)
    assert page.evaluate("window.__xss") is None


def test_06_hizli_stok_ve_yetersiz_stok(page):
    login(page)
    page.click("[data-page=products]")
    card = page.locator(".product-card", has_text="Arduino Uno R3")
    card.locator("button[title='1 adet ekle']").click()
    toast(page, "Stok güncellendi: 11")
    card.click()
    page.click("#modalBody >> text=Çıkar")
    page.fill("#promptInput", "500")
    page.click("#promptSubmitBtn")
    toast(page, "Yetersiz stok")
    expect(page.locator("#modalBody")).to_contain_text("11")


def test_07_ana_panel_kartlari_filtreli_acar(page, server):
    """Eski sürümde ana paneldeki kartlara tıklamak JavaScript hatası veriyordu."""
    c = api(server, admin_token(server))
    c.post("/api/products/", json={"name": "Lehim Teli", "current_stock": 1, "critical_stock": 3, "category": "Sarf Malzemesi"})
    login(page)
    critical = c.get("/api/products/count", params={"low_stock": "true"}).json()["count"]
    page.click("button:has-text('Kritik Stok')")
    expect(page.locator("#productsSummary")).to_have_text(f"{critical} ürün bulundu")
    expect(page.locator(".product-card", has_text="Lehim Teli")).to_be_visible()
    expect(page.locator(".product-card", has_text="Arduino Uno R3")).to_have_count(0)
    expect(page.locator("#filterLowStock")).to_have_attribute("aria-pressed", "true")
    page.click("[data-page=dashboard]")
    page.click("button[data-category='Sarf Malzemesi']")
    expect(page.locator("#filterCategory")).to_have_value("Sarf Malzemesi")


def test_08_sayfalama(page, server):
    c = api(server, admin_token(server))
    for i in range(100):
        c.post("/api/products/", json={"name": f"Toplu Ürün {i:03d}", "current_stock": 50})
    login(page)
    page.click("[data-page=products]")
    total = int(c.get("/api/products/count").json()["count"])
    expect(page.locator("#productsSummary")).to_have_text(f"{total} ürün bulundu")
    expect(page.locator(".product-card")).to_have_count(48)
    page.click("#productsPagination button[aria-label='Sonraki sayfa']")
    expect(page.locator("#productsPagination")).to_contain_text("49–96")
    page.click("#productsPagination button:has-text('3')")
    expect(page.locator(".product-card")).to_have_count(total - 96)


def test_09_turkce_arama(page):
    login(page)
    page.fill("#globalSearch", "ARDUİNO")
    expect(page.locator("#productsSummary")).to_have_text("1 ürün bulundu")
    expect(page.locator("#activeSearchChip")).to_contain_text("ARDUİNO")
    page.click("[data-page=warehouses]")
    expect(page.locator("#globalSearch")).to_have_value("")


def test_10_giris_islemi_kontrol_ve_stok(page):
    login(page)
    page.click("[data-page=shipments]")
    page.click("text=Yeni İşlem")
    page.fill("#shName", "Ekim irsaliyesi")
    row = page.locator("#shipmentItems [data-row]").first
    row.locator("[data-search]").fill("Arduino")
    page.click("[data-pick]")
    row.locator("[data-expected]").fill("20")
    page.click("#shipmentSubmit")
    toast(page, "kontrol bekliyor")
    expect(page.locator("text=Kontrol bekliyor").first).to_be_visible()

    page.click("text=Kontrol Et")
    page.locator("#checkForm input[type=number]").fill("17")
    page.click("#checkBtn")
    toast(page, "Kontrol kaydedildi")
    expect(page.locator(".glass", has_text="Ekim irsaliyesi").locator("text=Eksik")).to_be_visible()
    page.fill("#globalSearch", "Arduino")
    expect(page.locator(".product-card", has_text="Arduino Uno R3")).to_contain_text("28")  # 11 + 17


def test_11_cikis_yetersiz_stok_reddedilir(page):
    login(page)
    page.click("[data-page=shipments]")
    page.click("text=Yeni İşlem")
    page.fill("#shName", "Garantiye gönderim")
    page.select_option("#shType", "Çıkış")
    expect(page.locator("#outgoingReasonDiv")).to_be_visible()
    page.select_option("#shReason", "Garanti")
    row = page.locator("#shipmentItems [data-row]").first
    row.locator("[data-search]").fill("Arduino")
    page.click("[data-pick]")
    row.locator("[data-expected]").fill("999")
    page.click("#shipmentSubmit")
    toast(page, "Yetersiz stok")


def test_12_islem_silinince_stok_geri_alinir(page):
    login(page)
    page.click("[data-page=shipments]")
    page.locator(".glass", has_text="Ekim irsaliyesi").locator("button[title='Sil']").click()
    expect(page.locator("#confirmCheckbox")).to_be_checked()
    page.click("#confirmOk")
    toast(page, "stoklar geri alındı")
    page.fill("#globalSearch", "Arduino")
    expect(page.locator(".product-card", has_text="Arduino Uno R3")).to_contain_text("11")


def test_13_kullanici_olusturma_ve_depo_yetkisi(page, server):
    c = api(server, admin_token(server))
    c.post("/api/warehouses/", json={"name": "Gizli Depo"})
    login(page)
    page.click("[data-page=users]")
    page.click("text=Yeni Kullanıcı")
    page.fill("#ufName", "Ayşe Eğitmen")
    page.fill("#ufEmail", USER_EMAIL)
    page.fill("#ufPass", USER_PASS)
    page.locator("#userForm label", has_text="Gizem'in").locator("input").check()
    page.click("#userSubmit")
    toast(page, "Kullanıcı oluşturuldu")
    row = page.locator("tr", has_text=USER_EMAIL)
    expect(row).to_contain_text("Gizem'in \"Ana\" Deposu")
    row.locator("button[title='Depo erişimi']").click()
    expect(page.locator("#accessForm")).to_be_visible()
    page.keyboard.press("Escape")


def test_14_kullanici_sadece_yetkili_depoyu_gorur(page, server):
    c = api(server, admin_token(server))
    gizli = next(w for w in c.get("/api/warehouses/").json() if w["name"] == "Gizli Depo")
    c.post("/api/products/", json={"name": "Gizli Ürün", "warehouse_id": gizli["id"]})
    login(page, USER_EMAIL, USER_PASS)
    expect(page.locator("[data-page=users]")).to_be_hidden()
    expect(page.locator("[data-page=settings]")).to_be_hidden()
    page.click("[data-page=products]")
    expect(page.locator("#addProductBtn")).to_be_hidden()
    page.fill("#globalSearch", "Arduino")
    expect(page.locator(".product-card", has_text="Arduino Uno R3")).to_be_visible()
    page.fill("#globalSearch", "Gizli")
    expect(page.locator("#productsSummary")).to_have_text("0 ürün bulundu")
    page.click("[data-page=warehouses]")
    expect(page.locator("h3", has_text="Gizli Depo")).to_have_count(0)


def test_15_sifre_degistirme(page):
    login(page, USER_EMAIL, USER_PASS)
    page.click("button[title='Şifremi Değiştir']")
    page.fill("#cpCurrent", USER_PASS)
    page.fill("#cpNew", "YeniSifre2026")
    page.fill("#cpNew2", "YeniSifre2026")
    page.click("#cpBtn")
    toast(page, "Şifreniz değiştirildi")
    page.reload()
    expect(page.locator("h1", has_text="Ana Panel")).to_be_visible()  # yeni token ile oturum devam eder
    page.click("button[title='Çıkış']")
    login(page, USER_EMAIL, "YeniSifre2026")


def test_16_rapor_indirme_turkce_pdf(page):
    from pypdf import PdfReader
    login(page)
    page.click("[data-page=reports]")
    with page.expect_download() as d:
        page.click("text=PDF Raporu İndir")
    pdf = d.value
    assert pdf.suggested_filename.endswith(".pdf")
    text = "\n".join(p.extract_text() for p in PdfReader(pdf.path()).pages)
    assert "Artvin Deneyap Teknoloji Atölyesi" in text and "Lehim Teli" in text and "■" not in text
    with page.expect_download() as d:
        page.click("text=Excel Raporu İndir")
    assert d.value.suggested_filename.endswith(".xlsx")
    expect(page.locator("#reportLogs")).to_contain_text("Stok Ekleme")


def test_17_excel_ice_aktarma(page, tmp_path):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Tasarım ve Üretim"
    ws.append(["ARTVİN DENEYAP ENVANTER"])
    ws.append(["Malzeme Adı", "Birim", "Durum"])
    ws.append(["Kontrplak 3mm", "40 Adet", "Çalışıyor"])
    ws.append(["Lazer Kesim Makinesi", "1 adet", "Arızalı"])
    path = tmp_path / "envanter.xlsx"
    wb.save(path)
    login(page)
    page.click("[data-page=products]")
    page.click("text=Excel İle Ekle")
    with page.expect_download() as d:
        page.click("text=Örnek Excel şablonunu indir")
    assert d.value.suggested_filename == "deneyap_urun_sablonu.xlsx"
    page.set_input_files("#excelFile", str(path))
    page.click("#excelImportBtn")
    expect(page.locator("#modalBody")).to_contain_text("yeni ürün eklendi")
    expect(page.locator("#modalBody")).to_contain_text("Tasarım ve Üretim (2 ürün)")
    page.click("#modalFooter >> text=Tamam")
    page.fill("#globalSearch", "lazer kesim")
    expect(page.locator(".product-card", has_text="Lazer Kesim Makinesi")).to_contain_text("Bozuk / Kırık")


def test_18_ayarlar_ve_yedek(page):
    login(page)
    page.click("[data-page=settings]")
    page.fill("#stName", "Artvin Deneyap Atölyesi")
    page.click("#settingsBtn")
    toast(page, "Ayarlar kaydedildi")
    expect(page.locator("#sidebarAtolye")).to_have_text("Artvin Deneyap Atölyesi")
    with page.expect_download() as d:
        page.click("text=Yedek İndir")
    import json
    data = json.loads(open(d.value.path(), encoding="utf-8").read())
    assert data["format"] == "deneyap-depo-yedek" and data["counts"]["products"] > 100


def test_19_mobil_gorunum(browser, server):
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    pg = ctx.new_page()
    watcher = PageWatcher(pg)
    pg.goto(server)
    login(pg)
    expect(pg.locator("#sidebar")).not_to_be_in_viewport()
    pg.click("#mobileMenuBtn")
    expect(pg.locator("#sidebar")).to_be_in_viewport()
    pg.click("[data-page=products]")
    expect(pg.locator("#sidebar")).not_to_be_in_viewport()
    expect(pg.locator(".product-card").first).to_be_visible()
    no_hscroll = pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    ctx.close()
    assert no_hscroll, "Mobilde yatay kaydırma oluşuyor"
    assert not watcher.errors, watcher.errors


def test_20_tarayici_geri_tusu_ve_yenileme(page):
    login(page)
    page.click("[data-page=warehouses]")
    page.click("[data-page=courses]")
    expect(page).to_have_url(re.compile(r"#/courses$"))
    page.go_back()
    expect(page.locator("#pageContent h1", has_text="Depo Yönetimi")).to_be_visible()
    page.reload()
    expect(page.locator("#pageContent h1", has_text="Depo Yönetimi")).to_be_visible()


def test_21_varsayilan_sifreyle_giriste_zorunlu_degistirme(page):
    """Eski kurulumlarda 'admin123' gibi şifreler kalmış olabilir; giriş yapan kişi önce şifresini değiştirmeli."""
    import bcrypt
    from sqlalchemy import create_engine, text
    eng = create_engine(SERVER_DB_URL["url"])
    with eng.begin() as conn:
        conn.execute(text("UPDATE users SET hashed_password = :h WHERE email = :e"),
                     {"h": bcrypt.hashpw(b"admin123", bcrypt.gensalt(4)).decode(), "e": USER_EMAIL})
    eng.dispose()
    page.fill("#loginEmail", USER_EMAIL)
    page.fill("#loginPassword", "admin123")
    page.click("#loginBtn")
    expect(page.locator("#modalTitle")).to_have_text("Yeni Şifre Belirleyin")
    page.keyboard.press("Escape")  # kapatılamaz
    expect(page.locator("#modalTitle")).to_have_text("Yeni Şifre Belirleyin")
    page.mouse.click(5, 5)  # arka plana tıklamak da kapatmaz
    expect(page.locator("#modalTitle")).to_have_text("Yeni Şifre Belirleyin")
    page.fill("#cpNew", "Admin123")
    page.fill("#cpNew2", "Admin123")
    page.click("#cpBtn")
    toast(page, "çok yaygın")
    page.fill("#cpNew", "EgitmenYeni2026")
    page.fill("#cpNew2", "EgitmenYeni2026")
    page.click("#cpBtn")
    toast(page, "Şifreniz değiştirildi")
    expect(page.locator("#modalContainer")).to_be_hidden()


def test_22_ayarlar_veritabani_kontrolu(page, server):
    c = api(server, admin_token(server))
    c.post("/api/products/", json={"name": "Tekrar Ürün"})
    c.post("/api/courses/", json={"name": "Robotik ve Kodlama"})  # 'Robotik Kodlama' ile aynı ders
    login(page)
    page.click("[data-page=settings]")
    page.click("text=Kontrol Et")
    # Şifre taraması (bcrypt) yavaş bilgisayarlarda birkaç saniye sürebilir
    expect(page.locator("#dbCheckResult")).to_contain_text("Aynı dersin farklı yazımları", timeout=30000)
    page.click("#dbCheckResult >> text=Düzeltmeleri Uygula")
    page.click("#confirmOk")
    expect(page.locator("#dbCheckResult")).to_contain_text("Ders 'Robotik ve Kodlama' → 'Robotik Kodlama' ile birleştirildi",
                                                          timeout=30000)
    expect(page.locator("#dbCheckResult")).not_to_contain_text("Aynı dersin farklı yazımları")


def test_23_depo_atanmamis_urunleri_toplu_silme(page, server):
    c = api(server, admin_token(server))
    before = c.get("/api/products/count").json()["count"]
    unassigned = sum(1 for p in c.get("/api/products/?per_page=200").json() if p["warehouse_id"] is None)
    assert unassigned > 0
    login(page)
    page.click("[data-page=products]")
    page.click("text=Toplu Sil")
    page.select_option("#deleteScope", "unassigned")
    page.fill("#deleteConfirmInput", "sil")  # küçük harfle yazılsa da kabul edilir
    page.click("#deleteAllBtn")
    toast(page, f"{unassigned} ürün")
    assert c.get("/api/products/count").json()["count"] == before - unassigned
    assert all(p["warehouse_id"] is not None for p in c.get("/api/products/?per_page=200").json())



def test_24_eski_veritabaninda_kopya_aktarim_temizligi(browser, tmp_path):
    """Aynı Excel'in birkaç kez aktarıldığı eski bir veritabanı Ayarlar sayfasından temizlenir."""
    sys.path.insert(0, os.path.join(BACKEND_DIR, "tests"))
    from eski_veri import FARKLI_MALZEME, GERCEK_SIFRE

    db = tmp_path / "eski.db"
    url = "sqlite:///" + str(db).replace("\\", "/")
    # Eski veritabanını ayrı bir işlemde oluştur (bu işlemin veritabanı ayarlarına dokunmamak için)
    subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'tests'); "
                    "from eski_veri import eski_veritabani_olustur as o; o(sys.argv[1])", str(db)],
                   cwd=BACKEND_DIR, env={**os.environ, "DATABASE_URL": url}, check=True)
    base, proc = _start_server(url, str(tmp_path))
    try:
        ctx = browser.new_context(viewport={"width": 1366, "height": 900}, locale="tr-TR")
        pg = ctx.new_page()
        pg.set_default_timeout(15000)
        watcher = PageWatcher(pg)
        pg.goto(base)
        login(pg, "gizem@deneyap.org", GERCEK_SIFRE)
        pg.click("[data-page=settings]")
        pg.click("text=Kontrol Et")
        result = pg.locator("#dbCheckResult")
        expect(result).to_contain_text("aynı Excel muhtemelen 3 kez aktarılmış", timeout=30000)
        expect(result).to_contain_text("tutulacak")
        for box in ("#fixCopies", "#fixDupProducts", "#fixEmptyShipments"):
            pg.check(box)
        pg.click("#dbCheckResult >> text=Düzeltmeleri Uygula")
        pg.click("#confirmOk")
        expect(result).to_contain_text("kopya ürün silindi", timeout=30000)
        expect(result).not_to_contain_text("aynı Excel muhtemelen")
        ctx.close()
        assert not watcher.errors, watcher.errors

        token = api(base).post("/api/auth/login", json={"email": "gizem@deneyap.org", "password": GERCEK_SIFRE}).json()["access_token"]
        c = api(base, token)
        products = c.get("/api/products/?per_page=200").json()
        assert len(products) == FARKLI_MALZEME
        assert {p["warehouse_id"] for p in products} == {1}
        assert len(c.get("/api/shipments/").json()) == 2  # ürünsüz deneme gönderimleri silindi
        # Varsayılan şifreli örnek hesap artık giriş yapamaz
        assert api(base).post("/api/auth/login", json={"email": "admin@deneyap.org", "password": "admin123"}).status_code != 200
    finally:
        _stop_server(proc)


def test_25_ilk_kurulumda_tasinmamis_veri_uyarisi(browser, server):
    """Boş SQL Server veritabanı açıldığında eski SQLite verileri varsa ilk kurulum ekranı uyarır."""
    import json
    ctx = browser.new_context(viewport={"width": 1366, "height": 900}, locale="tr-TR")
    pg = ctx.new_page()
    watcher = PageWatcher(pg)
    pg.route("**/api/auth/setup-status", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body=json.dumps({"needs_setup": True, "atolye_adi": None, "il": None,
                         "tasinmamis_veri": {"dosya": "deneyap_depo.db", "urun": 1272, "kullanici": 3}})))
    pg.goto(server)
    expect(pg.locator("#setupCard")).to_be_visible()
    warning = pg.locator("#setupMigrationWarning")
    expect(warning).to_be_visible()
    expect(warning).to_contain_text("1.272 ürün")
    expect(warning).to_contain_text("SQL_Server_Kurulum.bat")
    ctx.close()
    assert not watcher.errors, watcher.errors
    # Normal durumda (taşınmamış veri yok) uyarı görünmez
    ctx = browser.new_context(locale="tr-TR")
    pg = ctx.new_page()
    pg.route("**/api/auth/setup-status", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body=json.dumps({"needs_setup": True, "atolye_adi": None, "il": None, "tasinmamis_veri": None})))
    pg.goto(server)
    expect(pg.locator("#setupCard")).to_be_visible()
    expect(pg.locator("#setupMigrationWarning")).to_be_hidden()
    ctx.close()


def test_26_pencere_acilinca_odak_calinmaz(page):
    """Pencere açıldıktan hemen sonra başka bir alana geçilirse, gecikmeli otomatik odak yazılanları
    ilk alana kaydırmamalı (yavaş bilgisayarlarda yazılan şifre 'Ad soyad' alanına gidiyordu)."""
    login(page)
    page.click("[data-page=users]")
    expect(page.locator("text=Yeni Kullanıcı")).to_be_visible()
    page.evaluate("() => { showUserForm(); document.getElementById('ufEmail').focus(); }")
    page.wait_for_timeout(300)
    assert page.evaluate("document.activeElement.id") == "ufEmail"
    page.keyboard.type("hizli@deneyap.org")
    expect(page.locator("#ufEmail")).to_have_value("hizli@deneyap.org")
    expect(page.locator("#ufName")).to_have_value("")
    page.keyboard.press("Escape")
    # Normal açılışta odak yine ilk alandadır
    page.click("text=Yeni Kullanıcı")
    page.wait_for_timeout(300)
    assert page.evaluate("document.activeElement.id") == "ufName"
