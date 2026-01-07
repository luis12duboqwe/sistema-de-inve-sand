"""Esquemas para dashboards, pronósticos y métricas de IA."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Literal

from pydantic import BaseModel, Field


class DashboardStats(BaseModel):
    """KPI principales del tablero de inventario y ventas."""

    active_products: int
    total_products: int
    low_stock_count: int
    out_of_stock_count: int
    total_inventory_value: float
    pending_orders: int
    total_orders_today: int
    total_revenue_today: float
    total_revenue_month: float
    total_revenue_last_month: float
    gross_margin_month: Optional[float] = Field(None, description="Margen bruto del mes actual (%)")
    average_ticket_month: Optional[float] = Field(None, description="Ticket promedio del mes actual")


class TopProduct(BaseModel):
    """Productos destacados por unidades vendidas."""

    product_id: int
    product_name: str
    units_sold: int
    total_revenue: Decimal


class SalesReport(BaseModel):
    """Resumen de ventas en un periodo determinado."""

    period_start: date
    period_end: date
    total_orders: int
    total_revenue: Decimal
    average_order_value: Decimal
    top_products: List[TopProduct]


class InventoryAlert(BaseModel):
    """Alertas de inventario por nivel crítico."""

    product_id: int
    product_name: str
    sku: str
    current_stock: int
    category: str
    alert_level: str  # critical, low, out_of_stock


class SalesForecast(BaseModel):
    """Pronóstico de ventas por producto."""

    product_id: int
    product_name: str
    current_stock: int
    average_daily_sales: float
    predicted_sales_next_7_days: int
    predicted_sales_next_30_days: int
    days_until_stockout: int
    restock_recommendation: int
    confidence: float
    trend: str  # increasing, stable, decreasing


class ForecastingSummary(BaseModel):
    """Resumen de múltiples pronósticos."""

    total_products: int
    products_needing_restock: int
    critical_stock_alerts: int
    estimated_revenue_7_days: float
    estimated_revenue_30_days: float
    top_performing_products: List[str]
    slow_moving_products: List[str]
    forecasts: List[SalesForecast]


class ForecastAnalyticsRequest(BaseModel):
    """Payload para solicitar pronósticos avanzados."""

    days_history: int = Field(60, ge=30, le=365)
    location_id: Optional[int] = Field(None, description="Filtrar por ubicación de origen de órdenes")
    product_ids: Optional[List[int]] = Field(None, description="IDs específicos a pronosticar")
    min_confidence: float = Field(0.0, ge=0.0, le=1.0)
    trend: Literal["increasing", "stable", "decreasing", "any"] = "any"
    limit: int = Field(50, ge=1, le=200)
    use_cache: bool = Field(True, description="Permite usar el snapshot precalculado si aplica")
    force_refresh: bool = Field(False, description="Ignora cache y fuerza recálculo")


class ForecastingAlertItem(BaseModel):
    """Alertas simplificadas derivadas de los pronósticos."""

    product_id: int
    product_name: str
    days_until_stockout: int
    restock_recommendation: int
    trend: str


class AIProfileMetric(BaseModel):
    """Estado operativo de un perfil habilitado con IA."""

    sales_profile_id: int
    sales_profile_name: str
    slug: Optional[str]
    is_ai_active: bool
    last_interaction_at: Optional[datetime]
    interactions_last_7_days: int
    tokens_last_7_days: int
    pending_training_items: int


class AIStatusResponse(BaseModel):
    """Instantánea global del sistema de IA y forecasting."""

    snapshot_generated_at: datetime
    total_sales_profiles: int
    ai_profiles_active: int
    ai_profiles_inactive: int
    interactions_last_24h: int
    tokens_last_24h: int
    avg_tokens_per_response: float
    customers_flagged: int
    training_backlog: int
    ai_profiles: List[AIProfileMetric]
    forecasting_alerts: List[ForecastingAlertItem]


class BusinessInsightsRequest(BaseModel):
    """Parámetros para calcular insights con IA."""

    days: int = Field(30, ge=7, le=120)
    location_id: Optional[int] = Field(None, description="Filtrar métricas por ubicación específica")
    sales_profile_id: Optional[int] = Field(None, description="Filtrar por perfil de venta (ID)")
    sales_profile_slug: Optional[str] = Field(None, description="Filtrar por perfil de venta (slug)")
    use_cache: bool = Field(True, description="Utiliza caché en memoria para consultas frecuentes")
    force_refresh: bool = Field(False, description="Ignora la caché y recalcula métricas")


class BusinessInsightsFilters(BaseModel):
    """Filtros aplicados a un conjunto de insights."""

    location_id: Optional[int] = None
    sales_profile_id: Optional[int] = None
    sales_profile_slug: Optional[str] = None


class BusinessInsightsKPIs(BaseModel):
    """KPIs agregados para el panel de insights."""

    total_revenue: float
    orders_count: int
    avg_order_value: float
    gross_margin_estimate: float


class BusinessInsightTopSeller(BaseModel):
    """Productos más vendidos según el motor de insights."""

    product_id: int
    product_name: str
    units_sold: int
    revenue: float
    gross_profit: float


class BusinessInsightSlowMover(BaseModel):
    """Productos con rotación lenta."""

    product_id: int
    product_name: str
    stock_available: int
    days_without_sales: int
    last_sale_at: Optional[str]


class BusinessInsightStockAlert(BaseModel):
    """Alertas de inventario generadas por insights."""

    product_id: int
    product_name: str
    stock_available: int
    avg_daily_demand: float
    days_until_stockout: Optional[float]


class BusinessInsightTrendPoint(BaseModel):
    """Puntos de tendencia de ingresos."""

    date: str
    revenue: float


class BusinessInsightsMetrics(BaseModel):
    """Colección de métricas y listados generados por insights."""

    kpis: BusinessInsightsKPIs
    top_sellers: List[BusinessInsightTopSeller]
    slow_movers: List[BusinessInsightSlowMover]
    stock_alerts: List[BusinessInsightStockAlert]
    revenue_trends: List[BusinessInsightTrendPoint]


class BusinessInsightRecommendation(BaseModel):
    """Acciones recomendadas por el motor de insights."""

    title: str
    action: str
    impact: Optional[str] = None
    category: Optional[str] = None
    priority: Literal["alta", "media", "baja", "critica"] = "media"


class BusinessInsightsResponse(BaseModel):
    """Respuesta completa de insights de negocio."""

    generated_at: datetime
    period_days: int
    filters: BusinessInsightsFilters
    metrics: BusinessInsightsMetrics
    recommendations: List[BusinessInsightRecommendation]
    ai_summary: Optional[str] = None
    tokens_used: int = 0
    raw_response: Optional[str] = None
