from contextlib import asynccontextmanager
import logging
from pathlib import Path
import re
from time import perf_counter

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.auth import check_permission
from app.config import settings
from app.config_production import check_production_readiness, prod_settings
from app.database import check_db_connection, get_db, init_db
from app.jobs.forecasting_job import start_forecasting_job
from app.middleware.production_guards import ProductionGuardMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.routers import (
    ai_intelligence,
    analytics,
    auth_router,
    channel_integrations,
    channel_monitoring,
    customers,
    daily_close,
    faq,
    financing,
    forecasting,
    imeis,
    locations,
    multistore_control,
    orders,
    photo_requests,
    products,
    profiles,
    public,
    reports,
    returns,
    sales_profiles,
    stock_history,
    stock_transfers,
    super_admin,
    suppliers,
    websocket,
)
from app.utils.auth_security import extract_jwt_subject
from app.utils.auto_migrations import run_auto_migrations
from app.utils.demo_seed import seed_demo_data
from app.utils.logging_config import setup_logging
from app.utils.observability import initialize_observability
from app.utils.prometheus_metrics import (
    RATE_LIMIT_BLOCK_TOTAL,
    REQUEST_LATENCY_SECONDS,
    REQUESTS_IN_FLIGHT,
    REQUESTS_TOTAL,
    render_prometheus_metrics,
)
from app.utils.rate_limiter import get_api_general_limiter
from app.utils.runtime_metrics import RuntimeMetrics
from app.utils.sentry_config import init_sentry


setup_logging()
initialize_observability()
init_sentry()
logger = logging.getLogger(__name__)
runtime_metrics = RuntimeMetrics()

HEALTH_PATHS = {
    "/health",
    "/api/health",
    "/ready",
    "/api/ready",
    "/metrics",
    "/api/metrics",
    "/metrics/prometheus",
    "/api/metrics/prometheus",
}

PATH_ID_PATTERN = re.compile(r"/\d+|/[0-9a-fA-F-]{16,}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application...")
    init_db()
    app.state.forecast_cache = None

    # Las migraciones son parte del arranque. Un fallo debe detener el proceso
    # para evitar operar con un esquema incompleto.
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
    description=(
        "API REST para gestión de inventario de celulares y accesorios "
        "con ubicaciones físicas y perfiles de venta"
    ),
    version="2.0.0",
    lifespan=lifespan,
)

uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

app.add_middleware(RequestContextMiddleware)
app.add_middleware(ProductionGuardMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception in %s %s: %s",
        request.method,
        request.url,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error. Please check logs for details."},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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


@app.middleware("http")
async def protect_maintenance_mode(request: Request, call_next):
    if prod_settings.MAINTENANCE_MODE and request.url.path not in HEALTH_PATHS:
        return JSONResponse(
            status_code=503,
            content={
                "detail": prod_settings.MAINTENANCE_MESSAGE,
                "status": "maintenance",
            },
        )

    return await call_next(request)


@app.middleware("http")
async def limit_payload_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            length = int(content_length)
            if length > prod_settings.MAX_REQUEST_BODY_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": "Payload demasiado grande",
                        "max_bytes": prod_settings.MAX_REQUEST_BODY_BYTES,
                    },
                )
        except ValueError:
            logger.warning("Header Content-Length inválido")

    return await call_next(request)


@app.middleware("http")
async def collect_runtime_metrics(request: Request, call_next):
    runtime_metrics.on_request_start()
    REQUESTS_IN_FLIGHT.inc()
    started = perf_counter()
    response = None
    raw_path = request.url.path
    metrics_path = PATH_ID_PATTERN.sub("/{id}", raw_path)
    try:
        response = await call_next(request)
        return response
    finally:
        elapsed_ms = (perf_counter() - started) * 1000
        status = response.status_code if response is not None else 500
        runtime_metrics.on_request_end(elapsed_ms, status)
        REQUESTS_TOTAL.labels(request.method, metrics_path, str(status)).inc()
        REQUEST_LATENCY_SECONDS.labels(request.method, metrics_path).observe(
            elapsed_ms / 1000
        )
        REQUESTS_IN_FLIGHT.dec()


@app.middleware("http")
async def enforce_general_rate_limit(request: Request, call_next):
    path = request.url.path
    if path in HEALTH_PATHS or path.startswith("/uploads"):
        return await call_next(request)

    limiter = get_api_general_limiter()
    client_ip = request.client.host if request.client else "unknown"
    subject = extract_jwt_subject(request.headers.get("Authorization"))
    key = f"user:{subject}" if subject else f"ip:{client_ip}"
    scope = "user" if subject else "ip"

    allowed, info = limiter.is_allowed(key)
    if not allowed:
        RATE_LIMIT_BLOCK_TOTAL.labels(scope).inc()
        return JSONResponse(
            status_code=429,
            headers={
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": str(info["remaining"]),
                "Retry-After": str(info["reset_in_seconds"]),
            },
            content={
                "detail": (
                    "API rate limit excedido. Reintente en "
                    f"{info['reset_in_seconds']} segundos."
                ),
                "scope": scope,
            },
        )

    response = await call_next(request)
    response.headers.setdefault("X-RateLimit-Limit", str(info["limit"]))
    response.headers.setdefault("X-RateLimit-Remaining", str(info["remaining"]))
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
app.include_router(super_admin.router)


@app.get("/")
def read_root():
    return {
        "message": "Sistema de Inventario API",
        "version": "2.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
def health_check():
    """Liveness: confirma que el proceso responde; no controla despliegues."""
    db_healthy = check_db_connection()
    return {
        "status": "alive",
        "database": "connected" if db_healthy else "disconnected",
        "service": "inventory-api",
        "version": "2.0.0",
        "environment": settings.environment,
    }


@app.get("/ready", tags=["Health"])
@app.get("/api/ready", tags=["Health"])
def readiness_check():
    """Readiness real: requiere configuración válida y base disponible."""
    db_healthy = check_db_connection()
    config_readiness = check_production_readiness()
    ready = bool(db_healthy and config_readiness["ready"])
    warnings = list(config_readiness["warnings"])
    if not db_healthy:
        warnings.append("BASE DE DATOS: PostgreSQL no responde")

    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "status": "ready" if ready else "not_ready",
            "ready": ready,
            "database": "connected" if db_healthy else "disconnected",
            "is_production": config_readiness["is_production"],
            "warnings": warnings,
            "config": config_readiness["config"],
        },
    )


@app.get("/metrics", tags=["Health"])
@app.get("/api/metrics", tags=["Health"])
def metrics_check():
    snapshot = runtime_metrics.snapshot()
    return {
        "requests": {
            "total": snapshot.total_requests,
            "errors": snapshot.total_errors,
            "in_flight": snapshot.in_flight,
            "error_rate": (
                round((snapshot.total_errors / snapshot.total_requests) * 100, 2)
                if snapshot.total_requests
                else 0.0
            ),
        },
        "latency_ms": {
            "avg": snapshot.avg_latency_ms,
            "p95": snapshot.p95_latency_ms,
            "p99": snapshot.p99_latency_ms,
        },
        "uptime_seconds": snapshot.uptime_seconds,
    }


@app.get("/metrics/prometheus", tags=["Health"])
@app.get("/api/metrics/prometheus", tags=["Health"])
def prometheus_metrics():
    payload = render_prometheus_metrics()
    return PlainTextResponse(
        content=payload.decode("utf-8"),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.post(
    "/api/init-data",
    tags=["Inicialización"],
    dependencies=[Depends(check_permission("settings:edit"))],
)
def initialize_sample_data(db: Session = Depends(get_db)):
    if prod_settings.is_production():
        raise HTTPException(
            status_code=403,
            detail="Endpoint deshabilitado en producción",
        )

    try:
        summary = seed_demo_data(db, created_by="api-init-data")
        return {
            "message": "Datos de prueba inicializados correctamente",
            "summary": summary,
        }
    except Exception as exc:
        db.rollback()
        logger.exception("Error al inicializar datos de prueba")
        raise HTTPException(
            status_code=500,
            detail="No se pudieron inicializar los datos de prueba",
        ) from exc
