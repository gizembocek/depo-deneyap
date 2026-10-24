import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from database import aktif_baglanti, describe_db_error, init_db
from routers import admin, auth, courses, products, reports, shipments, warehouses

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BACKEND_DIR)
assets_dir = os.path.join(PROJECT_DIR, "assets")
uploads_dir = os.getenv("UPLOAD_DIR") or os.path.join(BACKEND_DIR, "uploads")
frontend_dir = os.path.realpath(os.path.join(PROJECT_DIR, "frontend"))
os.makedirs(uploads_dir, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Eksik tabloları (SQL Server'da gerekirse veritabanını da) oluşturur;
    # var olan tablolara ve verilere dokunmaz.
    try:
        init_db()
    except Exception as exc:
        print("\n" + "=" * 70)
        print("[HATA] Veritabanı hazırlanamadı.")
        print("Bağlantı:", aktif_baglanti())
        print(describe_db_error(exc))
        print("=" * 70 + "\n")
        raise
    yield


app = FastAPI(
    title="Deneyap Atölyesi - Depo ve Stok Yönetimi",
    description="Deneyap Atölyesi için kapsamlı depo ve stok yönetimi API'si",
    version=admin.APP_VERSION,
    lifespan=lifespan,
)

# Token tabanlı kimlik doğrulama kullanıldığı için çerez (credentials) gerekmez.
_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Total-Count", "Content-Disposition"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


# ---------------------------------------------------------------------------
# Doğrulama hatalarını kullanıcının anlayacağı Türkçe mesaja çevir
# ---------------------------------------------------------------------------
FIELD_LABELS = {
    "name": "Ad", "email": "E-posta", "password": "Şifre", "new_password": "Yeni şifre",
    "current_password": "Mevcut şifre", "full_name": "Ad soyad", "quantity": "Miktar",
    "current_stock": "Mevcut stok", "critical_stock": "Kritik stok", "ideal_stock": "İdeal stok",
    "expected_quantity": "Beklenen miktar", "actual_quantity": "Gelen miktar", "items": "Ürünler",
    "action": "İşlem", "warehouse_id": "Depo", "shipment_type": "İşlem tipi", "role": "Rol",
    "category": "Kategori", "status": "Durum", "atolye_adi": "Atölye adı", "product_id": "Ürün",
}


def _readable_error(err: dict) -> str:
    loc = [p for p in err.get("loc", []) if isinstance(p, str) and p not in ("body", "query", "path")]
    label = FIELD_LABELS.get(loc[-1], loc[-1]) if loc else "Değer"
    etype, msg, ctx = err.get("type", ""), err.get("msg", ""), err.get("ctx") or {}
    if etype == "value_error":
        if "email" in msg.lower():
            return "Geçerli bir e-posta adresi girin"
        return msg.replace("Value error, ", "")
    if etype == "missing":
        return f"{label} zorunludur"
    if etype == "greater_than_equal":
        return f"{label} en az {ctx.get('ge')} olmalıdır"
    if etype == "less_than_equal":
        return f"{label} en fazla {ctx.get('le')} olabilir"
    if etype in ("int_parsing", "int_type", "int_from_float"):
        return f"{label} tam sayı olmalıdır"
    if etype == "enum":
        return f"{label} için geçersiz değer"
    if etype in ("json_invalid", "model_attributes_type", "list_type", "dict_type"):
        return "Gönderilen veri biçimi hatalı"
    return f"{label}: {msg}"


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    messages = list(dict.fromkeys(_readable_error(e) for e in errors))
    return JSONResponse(status_code=422, content={"detail": " • ".join(messages) or "Geçersiz istek",
                                                  "errors": [{"loc": e.get("loc"), "msg": e.get("msg")} for e in errors]})


# ---------------------------------------------------------------------------
# Statik dosyalar ve API
# ---------------------------------------------------------------------------
app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

for r in (auth, products, warehouses, shipments, reports, courses, admin):
    app.include_router(r.router)


def _index_response():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, headers={"Cache-Control": "no-cache"})
    return JSONResponse({"message": "Deneyap Atölyesi Depo Yönetimi API", "docs": "/docs"})


@app.get("/", include_in_schema=False)
async def root():
    return _index_response()


@app.get("/{path:path}", include_in_schema=False)
async def serve_frontend(path: str):
    if path.startswith("api/") or path == "api":
        return JSONResponse(status_code=404, content={"detail": "Bulunamadı"})

    # Güvenlik: yalnızca frontend klasörünün İÇİNDEKİ dosyalar verilir (../ ile dışarı çıkılamaz).
    file_path = os.path.realpath(os.path.join(frontend_dir, path))
    try:
        inside = os.path.normcase(os.path.commonpath([file_path, frontend_dir])) == os.path.normcase(frontend_dir)
    except ValueError:  # Windows'ta farklı sürücü harfi
        inside = False
    if not inside:
        return JSONResponse(status_code=404, content={"detail": "Bulunamadı"})
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    if "." in os.path.basename(path):  # olmayan dosya (ör. /js/yok.js) -> 404
        return JSONResponse(status_code=404, content={"detail": "Bulunamadı"})
    return _index_response()  # SPA


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
