from fastapi.testclient import TestClient
from _pytest.monkeypatch import MonkeyPatch

from app.config_production import prod_settings
from app.routers import ai_business_integrity, ai_intelligence


def _matching_post_routes(router) -> list:
    return [
        route
        for route in router.routes
        if getattr(route, "path", None) == "/api/ai/business-insights"
        and "POST" in (getattr(route, "methods", set()) or set())
    ]


def test_business_insights_legacy_is_stripped_and_canonical_route_exists() -> None:
    legacy_matches = _matching_post_routes(ai_intelligence.router)
    canonical_matches = _matching_post_routes(ai_business_integrity.router)

    assert legacy_matches == []
    assert len(canonical_matches) == 1
    assert canonical_matches[0].endpoint is ai_business_integrity.generate_business_insights_integrity


def test_business_insights_runtime_respects_ai_feature_flag(
    client: TestClient,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(prod_settings, "ENABLE_AI_FEATURES", False)

    response = client.post("/api/ai/business-insights", json={"days": 30})

    assert response.status_code == 503
    assert "deshabilitadas" in response.json()["detail"]
