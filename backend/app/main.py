from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
import logging

from app.database import init_db, get_db, check_db_connection
from app.auth import check_permission
from app.routers import (
    channel_integrations,
    channel_monitoring,
    profiles,
    products,
    orders,
    faq,
    customers,
    reports,
    auth_router,
    stock_transfers,
    suppliers,
    stock_history,
    locations,
    sales_profiles,
    returns,
    imeis,
    ai_intelligence,
    financing,
    public,
    forecasting,
    analytics,
    photo_requests,
    websocket,
    daily_close,
    multistore_control,
)
from app.models import Profile, Product, Stock, Location
from app.config import settings
from app.utils.logging_config import setup_logging
from app.utils.observability import initialize_observability
from app.utils.sentry_config import init_sentry
from app.config_production import prod_settings
from app.middleware.request_context import RequestContextMiddleware
from app.utils.auto_migrations import run_auto_migrations
from sqlalchemy.orm import Session
from app.jobs.forecasting_job import start_forecasting_job

# Configurar logging al inicio
setup_logging()
initialize_observability()
init_sentry()  # ✅ Inicializar Sentry para monitoreo
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up application...")
    init_db()
    app.state.forecast_cache = None
    
    # Run auto-migrations
    run_auto_migrations()

    scheduler = None
    if prod_settings.ENABLE_FORECAST_SCHEDULER:
        scheduler = start_forecasting_job(app)

    try:
        yield
    finally:
        if scheduler:
            scheduler.shutdown(wait=False)
        logger.info("Shutting down application...")


app = FastAPI(
    title="Sistema de Inventario API",
    description="API REST para gestión de inventario de celulares y accesorios con ubicaciones físicas y perfiles de venta",
    version="2.0.0",
    lifespan=lifespan
)

uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

app.add_middleware(RequestContextMiddleware)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # No capturar HTTPException (dejar que FastAPI lo maneje)
    # Pero sí loguear errores inesperados
    logger.error(f"Unhandled exception in {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error. Please check logs for details."}
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # Evitar "*" + credenciales (riesgo CORS). La API usa Authorization header,
    # no cookies, así que no se requieren credenciales.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if prod_settings.is_production() and settings.allowed_hosts != ["*"]:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts,
    )

if prod_settings.is_production():
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        for header, value in prod_settings.SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response

app.include_router(auth_router.router)
app.include_router(locations.router)
app.include_router(sales_profiles.router)
app.include_router(profiles.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(faq.router, prefix="/api/faq", tags=["FAQ"])
app.include_router(customers.router)
app.include_router(reports.router)
app.include_router(stock_transfers.router)
app.include_router(returns.router)
app.include_router(imeis.router)
app.include_router(public.router)
app.include_router(suppliers.router)
app.include_router(financing.router)
app.include_router(stock_history.router)
app.include_router(ai_intelligence.router)
app.include_router(channel_integrations.router)
app.include_router(channel_monitoring.router)
app.include_router(photo_requests.router)
app.include_router(websocket.router)
app.include_router(forecasting.router)
app.include_router(analytics.router)
app.include_router(daily_close.router)
app.include_router(multistore_control.router)

@app.get("/")
def read_root():
    """
    Root endpoint with API information.
    
    Returns:
        Basic API information and documentation link
    """
    return {
        "message": "Sistema de Inventario API",
        "version": "2.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check básico para monitoreo e infraestructura."""
    return {
        "status": "ok",
        "service": "inventory-api",
        "version": "2.0.0"
    }


@app.get("/api/health")
def api_health_check():
    """Alias legado/compatibilidad para health check bajo prefijo /api."""
    return health_check()

@app.post("/api/init-data", tags=["Inicialización"], dependencies=[Depends(check_permission("settings:edit"))])
def initialize_sample_data(db: Session = Depends(get_db)):
    """
    Inicializa datos de ejemplo en la base de datos.
    Bloqueado en producción para evitar datos no autorizados.
    """
    if prod_settings.is_production():
        raise HTTPException(
            status_code=403,
            detail="Endpoint deshabilitado en producción"
        )

    try:
        existing_profile = db.query(Profile).filter(Profile.slug == "softmobile").first()
        if existing_profile:
            return {"message": "Los datos de ejemplo ya existen"}
        
        profile = Profile(
            name="Softmobile",
            slug="softmobile",
            active=True
        )
        db.add(profile)
        db.flush()

        default_location = db.query(Location).filter(Location.nombre == "Tienda Principal").first()
        if not default_location:
            default_location = Location(
                nombre="Tienda Principal",
                tipo="tienda",
                direccion="",
                telefono=None,
                activo=True
            )
            db.add(default_location)
            db.flush()
        
        products_data = [
            {
                "sku": "SM-S24-256-NEGRO-NUEVO",
                "nombre": "Samsung Galaxy S24 256GB Negro",
                "categoria": "celular",
                "marca": "Samsung",
                "modelo": "Galaxy S24",
                "capacidad": "256GB",
                "condicion": "nuevo",
                "precio": 18500.00,
                "garantia_meses": 12,
                "stock": 5
            },
            {
                "sku": "IP-15PRO-512-TITANIO-NUEVO",
                "nombre": "iPhone 15 Pro 512GB Titanio",
                "categoria": "celular",
                "marca": "Apple",
                "modelo": "iPhone 15 Pro",
                "capacidad": "512GB",
                "condicion": "nuevo",
                "precio": 35000.00,
                "garantia_meses": 12,
                "stock": 3
            },
            {
                "sku": "ACC-FUNDA-SILICONA-UNIVERSAL",
                "nombre": "Funda de Silicona Universal",
                "categoria": "accesorio",
                "marca": "Genérico",
                "modelo": "Universal",
                "capacidad": None,
                "condicion": "nuevo",
                "precio": 150.00,
                "garantia_meses": 0,
                "stock": 50
            },
            {
                "sku": "ACC-CARGADOR-RAPIDO-20W",
                "nombre": "Cargador Rápido 20W USB-C",
                "categoria": "accesorio",
                "marca": "Anker",
                "modelo": "PowerPort 20W",
                "capacidad": "20W",
                "condicion": "nuevo",
                "precio": 350.00,
                "garantia_meses": 6,
                "stock": 25
            }
        ]
        
        for product_data in products_data:
            stock_qty = product_data.pop("stock")
            
            product = Product(
                profile_id=profile.id,
                **product_data,
                moneda="HNL",
                activo=True
            )
            db.add(product)
            db.flush()
            
            stock = Stock(
                product_id=product.id,
                location_id=default_location.id,
                cantidad_disponible=stock_qty
            )
            db.add(stock)
        
        db.commit()
        
        return {
            "message": "Datos de ejemplo inicializados correctamente",
            "profile": {
                "name": profile.name,
                "slug": profile.slug
            },
            "location": {
                "nombre": default_location.nombre,
                "id": default_location.id,
                "tipo": default_location.tipo
            },
            "products_created": len(products_data)
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al inicializar datos: {str(e)}")

@app.get("/api/health", tags=["Health"])
def health_check():
    """
    Verifica el estado de salud de la API y la base de datos.
    
    Returns:
        - status: Estado del servicio (healthy/unhealthy)
        - database: Estado de la conexión a la base de datos
        
    Raises:
        - 503: Si la base de datos no está disponible
    """
    db_healthy = check_db_connection()
    
    if not db_healthy:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "disconnected"
            }
        )
    
    return {
        "status": "healthy",
        "database": "connected"
    }
