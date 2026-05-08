import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import engine, Base
from routers import auth, products, warehouses, shipments, reports, courses

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Deneyap Atölyesi - Depo ve Stok Yönetimi",
    description="Deneyap Atölyesi için kapsamlı depo ve stok yönetimi API'si",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

os.makedirs(uploads_dir, exist_ok=True)

app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# Include routers
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(warehouses.router)
app.include_router(shipments.router)
app.include_router(reports.router)
app.include_router(courses.router)




@app.get("/")
async def root():
    from fastapi.responses import FileResponse
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Deneyap Atölyesi Depo Yönetimi API", "docs": "/docs"}


@app.get("/{path:path}")
async def serve_frontend(path: str):
    from fastapi.responses import FileResponse, JSONResponse
    
    # Don't catch API routes
    if path.startswith("api/"):
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    
    file_path = os.path.join(frontend_dir, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # SPA fallback
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    return JSONResponse(status_code=404, content={"detail": "Not found"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
