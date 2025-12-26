from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db, get_db, check_db_connection
from app.routers import (
    profiles, products, orders, faq, customers, reports, 
    auth_router, stock_transfers, suppliers, stock_history,
    locations, sales_profiles, returns, imeis, ai_intelligence,
    financing, public, forecasting
)
from app.models import Profile, Product, Stock, Location
from app.config import settings
from sqlalchemy.orm import Session


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown (if needed in the future)


app = FastAPI(
    title="Sistema de Inventario API",
    description="API REST para gestión de inventario de celulares y accesorios con ubicaciones físicas y perfiles de venta",
    version="2.0.0",
    lifespan=lifespan
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
app.include_router(forecasting.router)

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

@app.post("/api/init-data", tags=["Inicialización"])
def initialize_sample_data(db: Session = Depends(get_db)):
    """
    Inicializa datos de ejemplo en la base de datos.
    
    Crea un perfil "Softmobile" con productos de ejemplo si no existen.
    Es idempotente: si ya existen datos, no los duplica.
    
    Returns:
        - message: Mensaje de confirmación
        - profile: Información del perfil creado
        - products_created: Número de productos inicializados
    """
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

        # V2.0: crear ubicación por defecto para asignar stock inicial
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
