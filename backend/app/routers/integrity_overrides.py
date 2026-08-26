"""Register canonical integrity routes and remove shadowed legacy definitions.

The project keeps the legacy implementation files for reviewability and gradual
refactoring, but OpenAPI and runtime must expose exactly one handler per operation.
This module removes only the paths replaced by the hardening routers below.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.routers import (
    ai_business_integrity,
    ai_candidate_product_integrity,
    ai_intelligence,
    ai_order_product_integrity,
    ai_slug_integrity,
    auth_admin_integrity,
    auth_register_integrity,
    auth_router,
    auth_setup_integrity,
    channel_integrations,
    channel_integrity,
    channel_webhook_integrity,
    multistore_control,
    multistore_integrity,
    order_search_integrity,
    order_state_integrity,
    orders,
    product_search_integrity,
    products,
    reports,
    reports_final_integrity,
    reports_integrity,
    stock_transfer_integrity,
    stock_transfers,
    super_admin,
    super_admin_audit_integrity,
    super_admin_integrity,
)


def _strip_route(router: APIRouter, path: str, method: str) -> None:
    wanted_method = method.upper()
    router.routes[:] = [
        route
        for route in router.routes
        if not (
            getattr(route, "path", None) == path
            and wanted_method in (getattr(route, "methods", set()) or set())
        )
    ]


_SHADOWED_ROUTES: tuple[tuple[APIRouter, str, str], ...] = (
    (auth_router.router, "/api/auth/setup", "POST"),
    (auth_router.router, "/api/auth/register", "POST"),
    (auth_router.router, "/api/auth/users", "GET"),
    (auth_router.router, "/api/auth/users/{user_id}/role", "PUT"),
    (auth_router.router, "/api/auth/users/{user_id}", "PUT"),
    (auth_router.router, "/api/auth/users/{user_id}", "DELETE"),
    (orders.router, "/api/orders/search", "POST"),
    (orders.router, "/api/orders/{order_id}/status", "PUT"),
    (orders.router, "/api/orders/{order_id}", "PUT"),
    (orders.router, "/api/orders/{order_id}/cancel", "POST"),
    (products.router, "/api/products", "GET"),
    (reports.router, "/api/reports/dashboard", "GET"),
    (reports.router, "/api/reports/sales", "GET"),
    (reports.router, "/api/reports/sales-summary-by-location", "GET"),
    (reports.router, "/api/reports/top-products-by-location/{location_id}", "GET"),
    (reports.router, "/api/reports/bank-transfer-reconciliation", "GET"),
    (reports_integrity.router, "/api/reports/dashboard", "GET"),
    (reports_integrity.router, "/api/reports/sales", "GET"),
    (reports_integrity.router, "/api/reports/top-products-by-location/{location_id}", "GET"),
    (multistore_control.router, "/api/multistore-control/location-daily-closes", "POST"),
    (stock_transfers.router, "/api/stock-transfers/{transfer_id}/confirm", "POST"),
    (stock_transfers.router, "/api/stock-transfers/{transfer_id}/reject", "POST"),
    (stock_transfers.router, "/api/stock-transfers/{transfer_id}", "DELETE"),
    (channel_integrations.router, "/api/channels/health", "GET"),
    (
        channel_integrations.router,
        "/api/channels/test-connection/{sales_profile_slug}/{channel}",
        "POST",
    ),
    (channel_integrations.router, "/api/channels/whatsapp/webhook", "POST"),
    (channel_integrations.router, "/api/channels/messenger/webhook", "POST"),
    (channel_integrations.router, "/api/channels/instagram/webhook", "POST"),
    (super_admin.router, "/api/super-admin/users/{user_id}/active", "POST"),
    (super_admin.router, "/api/super-admin/users/{user_id}/reset-role", "POST"),
    (super_admin.router, "/api/super-admin/stock/adjust", "POST"),
    (super_admin.router, "/api/super-admin/orders/{order_id}/cancel", "POST"),
    (super_admin.router, "/api/super-admin/audit-logs", "GET"),
    (super_admin.router, "/api/super-admin/audit-logs/{audit_id}/revert", "POST"),
    (ai_intelligence.router, "/api/ai/business-insights", "POST"),
    (ai_intelligence.router, "/api/ai/context", "POST"),
    (ai_intelligence.router, "/api/ai/reply", "POST"),
    (ai_intelligence.router, "/api/ai/log", "POST"),
    (ai_intelligence.router, "/api/ai/training/submit", "POST"),
    (ai_intelligence.router, "/api/ai/handle-message", "POST"),
)

for _router, _path, _method in _SHADOWED_ROUTES:
    _strip_route(_router, _path, _method)

# Channel handlers import the legacy AI function directly. Point that runtime
# reference at the same canonical boundary used by the HTTP API so configured
# default slugs receive identical Unicode/case-insensitive semantics.
channel_integrations.handle_message_without_n8n = (
    ai_slug_integrity.handle_message_without_n8n_integrity
)

# AI order creation resolves product_query values through a module-global helper.
# Rebind that boundary once so both /create-order and /handle-message order intents
# treat user-entered LIKE metacharacters as literal text without duplicating auth,
# feature gates, stock validation, or OrderService behavior.
ai_intelligence._resolve_product_for_ai_item = (
    ai_order_product_integrity.resolve_product_for_ai_item_integrity
)

# Candidate products influence inventory context, remembered products, and photo
# requests. Rebind the shared runtime helper once so every AI path keeps existing
# ranking/fallback semantics while treating message keywords as literal text.
ai_intelligence._find_candidate_products = (
    ai_candidate_product_integrity.find_candidate_products_integrity
)


router = APIRouter()
router.include_router(auth_setup_integrity.router)
router.include_router(auth_register_integrity.router)
router.include_router(auth_admin_integrity.router)
router.include_router(order_search_integrity.router)
router.include_router(order_state_integrity.router)
router.include_router(product_search_integrity.router)
router.include_router(reports_integrity.router)
router.include_router(reports_final_integrity.router)
router.include_router(multistore_integrity.router)
router.include_router(stock_transfer_integrity.router)
router.include_router(channel_integrity.router)
router.include_router(channel_webhook_integrity.router)
router.include_router(super_admin_integrity.router)
router.include_router(super_admin_audit_integrity.router)
router.include_router(
    ai_business_integrity.router,
    dependencies=[Depends(ai_intelligence._ensure_ai_features_enabled)],
)
router.include_router(ai_slug_integrity.router)
