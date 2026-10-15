"""Métricas Prometheus para observabilidad enterprise."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, generate_latest


REQUESTS_TOTAL = Counter(
    "inventory_api_requests_total",
    "Total de requests HTTP procesados",
    ["method", "path", "status"],
)

REQUEST_LATENCY_SECONDS = Histogram(
    "inventory_api_request_latency_seconds",
    "Latencia de requests HTTP en segundos",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)

REQUESTS_IN_FLIGHT = Gauge(
    "inventory_api_requests_in_flight",
    "Requests concurrentes en proceso",
)

RATE_LIMIT_BLOCK_TOTAL = Counter(
    "inventory_api_rate_limit_block_total",
    "Bloqueos por rate limiting",
    ["scope"],
)

AUTH_LOGIN_EVENTS_TOTAL = Counter(
    "inventory_api_auth_login_events_total",
    "Eventos de autenticación",
    ["result"],
)


def metric_route_template(raw_path: str, route: object | None) -> str:
    """Fixed-cardinality labels from registered routes only; never user URL segments.

    StaticFiles mounts do not necessarily populate scope.route, therefore uploads
    are collapsed explicitly before inspecting the route object.
    """
    if raw_path == "/uploads" or raw_path.startswith("/uploads/"):
        return "/uploads/{path}"
    template = getattr(route, "path", None)
    if isinstance(template, str) and template.startswith("/") and len(template) <= 180:
        return template
    return "/__unmatched__"


def render_prometheus_metrics() -> bytes:
    """Devuelve el payload de métricas en formato Prometheus."""
    return generate_latest()
