from typing import Any, Dict, Tuple, TypedDict, cast

from fastapi.applications import FastAPI
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.orm import Session
from _pytest.monkeypatch import MonkeyPatch

from .helpers import seed_location_and_sales_profile, seed_product
from app.models import AIProfileConfig, InteractionLog, Location, Order, OrderItem, SalesProfile
from app.config_production import prod_settings
from app.routers import ai_intelligence


def _require_pk(value: object, label: str) -> int:
    if not isinstance(value, int):
        raise AssertionError(f"{label} must be an int primary key")
    return value


def _require_str(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise AssertionError(f"{label} must be a string")
    return value


class ChatRequestPayload(TypedDict):
    sales_profile_slug: str
    customer_phone: str
    customer_name: str
    message_content: str


def _chat_payload(
    *,
    sales_profile_slug: str,
    customer_phone: str,
    customer_name: str,
    message_content: str,
) -> ChatRequestPayload:
    return {
        "sales_profile_slug": sales_profile_slug,
        "customer_phone": customer_phone,
        "customer_name": customer_name,
        "message_content": message_content,
    }


class _DummyOpenAIService:
    def __init__(self) -> None:
        self.calls: list[Dict[str, Any]] = []

    def create_chat_completion(self, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(kwargs)
        return {
            "reply": "Respuesta simulada",
            "model": "gpt-4o-mini",
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 24,
                "total_tokens": 36,
            },
        }


def _configure_ai_profile(db_session: Session, sales_profile_id: int) -> None:
    config = AIProfileConfig(
        sales_profile_id=sales_profile_id,
        system_prompt="Eres un bot de pruebas.",
        model_name="gpt-4o-mini",
        temperature=0.1,
        is_active=True,
    )
    db_session.add(config)
    db_session.commit()


def _seed_business_insight_data(client: TestClient, db_session: Session) -> Tuple[Location, SalesProfile, Dict[str, Any]]:
    location, sales_profile = seed_location_and_sales_profile(db_session)
    location_id = _require_pk(location.id, "location.id")
    product = seed_product(client, location_id)

    order = Order(
        sales_profile_id=_require_pk(sales_profile.id, "sales_profile.id"),
        source_location_id=location_id,
        customer_name="Cliente Insight",
        customer_phone="50455555555",
        canal="whatsapp",
        metodo_pago="efectivo",
        total=1000,
        estado="completada",
    )
    db_session.add(order)
    db_session.commit()

    product_id = int(product["id"])
    order_item = OrderItem(
        order_id=_require_pk(order.id, "order.id"),
        product_id=product_id,
        cantidad=1,
        precio_unitario=1000,
        es_regalo_promocion=False,
    )
    db_session.add(order_item)
    db_session.commit()

    return location, sales_profile, product


def test_ai_context_returns_inventory_snippet(client: TestClient, db_session: Session) -> None:
    location, sales_profile = seed_location_and_sales_profile(db_session)
    location_id = _require_pk(location.id, "location.id")
    seed_product(client, location_id)
    _configure_ai_profile(db_session, _require_pk(sales_profile.id, "sales_profile.id"))

    payload = _chat_payload(
        sales_profile_slug=_require_str(sales_profile.slug, "sales_profile.slug"),
        customer_phone="50411112222",
        customer_name="Cliente QA",
        message_content="Busco telefono",
    )

    res: Response = client.post("/api/ai/context", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["bot_config"]["model"] == "gpt-4o-mini"
    assert "Telefono Test" in data["relevant_inventory"]
    assert data["customer_info"]["name"] == "Cliente QA"


def test_ai_reply_logs_interactions(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    location, sales_profile = seed_location_and_sales_profile(db_session)
    location_id = _require_pk(location.id, "location.id")
    seed_product(client, location_id)
    _configure_ai_profile(db_session, _require_pk(sales_profile.id, "sales_profile.id"))

    monkeypatch.setattr(prod_settings, "ENABLE_AI_FEATURES", True)
    monkeypatch.setattr(prod_settings, "OPENAI_API_KEY", "test-key")

    dummy_service = _DummyOpenAIService()
    monkeypatch.setattr(ai_intelligence, "openai_service", dummy_service)

    payload = _chat_payload(
        sales_profile_slug=_require_str(sales_profile.slug, "sales_profile.slug"),
        customer_phone="50433334444",
        customer_name="Cliente QA",
        message_content="Hola, que recomiendas?",
    )

    res: Response = client.post("/api/ai/reply", json=payload)
    assert res.status_code == 200, res.text

    data = res.json()
    assert data["reply"] == "Respuesta simulada"
    assert data["tokens_used"] == 36
    assert dummy_service.calls, "Se esperaba que el servicio de OpenAI se invocara"

    logs = db_session.query(InteractionLog).order_by(InteractionLog.id).all()
    assert len(logs) == 2
    first_log = logs[0]
    second_log = logs[1]
    first_role = cast(str, first_log.role)
    second_role = cast(str, second_log.role)
    reply_content = cast(str, second_log.content)
    assert first_role == "user"
    assert second_role == "assistant"
    assert reply_content == "Respuesta simulada"


def test_business_insights_returns_fallback(client: TestClient, db_session: Session) -> None:
    _, sales_profile, _ = _seed_business_insight_data(client, db_session)
    sales_profile_slug = _require_str(sales_profile.slug, "sales_profile.slug")

    response: Response = client.post(
        "/api/ai/business-insights",
        json={"sales_profile_slug": sales_profile_slug, "days": 30},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["metrics"]["kpis"]["orders_count"] >= 1
    assert len(data["recommendations"]) >= 1


def test_business_insights_cache_headers(client: TestClient, db_session: Session) -> None:
    _, sales_profile, _ = _seed_business_insight_data(client, db_session)
    sales_profile_slug = _require_str(sales_profile.slug, "sales_profile.slug")
    app_instance = cast(FastAPI, client.app)
    cache: Dict[str, Any] | None = getattr(app_instance.state, "business_insights_cache", None)
    if cache is not None:
        cache.clear()
    else:
        app_instance.state.business_insights_cache = {}

    first = client.post(
        "/api/ai/business-insights",
        json={
            "sales_profile_slug": sales_profile_slug,
            "days": 30,
            "use_cache": True,
        },
    )
    assert first.status_code == 200
    assert first.headers.get("x-ai-business-cache") == "MISS"

    cached = client.post(
        "/api/ai/business-insights",
        json={
            "sales_profile_slug": sales_profile_slug,
            "days": 30,
            "use_cache": True,
        },
    )
    assert cached.status_code == 200
    assert cached.headers.get("x-ai-business-cache") == "HIT"
    assert cached.json() == first.json()

    refreshed = client.post(
        "/api/ai/business-insights",
        json={
            "sales_profile_slug": sales_profile_slug,
            "days": 30,
            "use_cache": True,
            "force_refresh": True,
        },
    )
    assert refreshed.status_code == 200
    assert refreshed.headers.get("x-ai-business-cache") == "MISS"


def test_ai_endpoints_return_503_when_disabled(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    location, sales_profile = seed_location_and_sales_profile(db_session)
    location_id = _require_pk(location.id, "location.id")
    seed_product(client, location_id)
    _configure_ai_profile(db_session, _require_pk(sales_profile.id, "sales_profile.id"))

    monkeypatch.setattr(prod_settings, "ENABLE_AI_FEATURES", False)

    payload = _chat_payload(
        sales_profile_slug=_require_str(sales_profile.slug, "sales_profile.slug"),
        customer_phone="50488889999",
        customer_name="Cliente Flag",
        message_content="Hola",
    )

    response: Response = client.post("/api/ai/context", json=payload)
    assert response.status_code == 503
    assert "deshabilitadas" in response.json()["detail"]

    # Restaurar bandera para otras pruebas
    monkeypatch.setattr(prod_settings, "ENABLE_AI_FEATURES", True)