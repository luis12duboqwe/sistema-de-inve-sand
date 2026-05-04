from typing import Any, Dict, Tuple, TypedDict, cast

from fastapi.applications import FastAPI
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.orm import Session
from _pytest.monkeypatch import MonkeyPatch

from .helpers import seed_location_and_sales_profile, seed_product
from app.models import AIProfileConfig, Customer, FAQEntry, InteractionLog, Location, Order, OrderItem, SalesProfile, TrainingQueue, ProcessedMessage
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


def test_training_queue_patch_updates_generic_fields(client: TestClient, db_session: Session) -> None:
    _, sales_profile = seed_location_and_sales_profile(db_session)
    queue_item = TrainingQueue(
        sales_profile_id=_require_pk(sales_profile.id, "sales_profile.id"),
        customer_question="¿Tienen iPhone 13?",
        ai_proposed_answer="No estoy seguro.",
        status="pending",
    )
    db_session.add(queue_item)
    db_session.commit()

    response: Response = client.patch(
        f"/api/ai/training-queue/{_require_pk(queue_item.id, 'queue_item.id')}",
        json={
            "customer_question": "¿Tienen iPhone 13 Pro?",
            "ai_proposed_answer": "Sí, disponible en tienda centro",
            "status": "approved",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["customer_question"] == "¿Tienen iPhone 13 Pro?"
    assert payload["ai_proposed_answer"] == "Sí, disponible en tienda centro"
    assert payload["status"] == "approved"


def test_training_queue_patch_convert_to_faq_creates_faq(client: TestClient, db_session: Session) -> None:
    _, sales_profile = seed_location_and_sales_profile(db_session)
    queue_item = TrainingQueue(
        sales_profile_id=_require_pk(sales_profile.id, "sales_profile.id"),
        customer_question="¿Hacen envíos a domicilio?",
        ai_proposed_answer="Tal vez.",
        status="pending",
    )
    db_session.add(queue_item)
    db_session.commit()

    response: Response = client.patch(
        f"/api/ai/training-queue/{_require_pk(queue_item.id, 'queue_item.id')}",
        json={
            "status": "converted_to_faq",
            "admin_correction": "Sí, hacemos envíos en Tegucigalpa con costo adicional.",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "converted_to_faq"
    assert payload["admin_correction"] == "Sí, hacemos envíos en Tegucigalpa con costo adicional."

    faq = (
        db_session.query(FAQEntry)
        .filter(FAQEntry.pregunta_clave == "¿Hacen envíos a domicilio?")
        .first()
    )
    assert faq is not None
    faq_respuesta = cast(str, faq.respuesta)
    assert faq_respuesta == "Sí, hacemos envíos en Tegucigalpa con costo adicional."


def test_ai_create_order_from_intent_by_product_query(client: TestClient, db_session: Session) -> None:
    location, sales_profile = seed_location_and_sales_profile(db_session)
    location_id = _require_pk(location.id, "location.id")
    product = seed_product(client, location_id)

    response: Response = client.post(
        "/api/ai/create-order",
        json={
            "sales_profile_slug": _require_str(sales_profile.slug, "sales_profile.slug"),
            "source_location_id": location_id,
            "customer_phone": "50470001111",
            "customer_name": "Cliente IA",
            "items": [
                {
                    "product_query": str(product["nombre"]),
                    "cantidad": 1,
                    "imeis": ["111111111111111"],
                }
            ],
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "created"
    assert isinstance(payload["order_id"], int)
    assert payload["linked_interaction"] is False

    created_order = db_session.query(Order).filter(Order.id == payload["order_id"]).first()
    assert created_order is not None
    created_phone = cast(str, created_order.customer_phone)
    assert created_phone == "50470001111"


def test_ai_create_order_from_intent_links_existing_interaction(client: TestClient, db_session: Session) -> None:
    location, sales_profile = seed_location_and_sales_profile(db_session)
    location_id = _require_pk(location.id, "location.id")
    product = seed_product(client, location_id)
    profile_id = _require_pk(sales_profile.id, "sales_profile.id")

    customer = Customer(
        phone_number="50472223333",
        name="Cliente Conversación",
        reputation_score=100,
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)

    interaction = InteractionLog(
        sales_profile_id=profile_id,
        customer_id=_require_pk(customer.id, "customer.id"),
        role="user",
        content="Quiero comprar ese teléfono",
        tokens_used=0,
    )
    db_session.add(interaction)
    db_session.commit()

    response: Response = client.post(
        "/api/ai/create-order",
        json={
            "sales_profile_slug": _require_str(sales_profile.slug, "sales_profile.slug"),
            "source_location_id": location_id,
            "customer_phone": "50472223333",
            "items": [
                {
                    "product_id": int(product["id"]),
                    "cantidad": 1,
                    "imeis": ["111111111111111"],
                }
            ],
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "created"
    assert payload["linked_interaction"] is True


def test_ai_handle_message_returns_reply_without_order(
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
    monkeypatch.setattr(ai_intelligence, "openai_service", _DummyOpenAIService())

    response: Response = client.post(
        "/api/ai/handle-message",
        json={
            "sales_profile_slug": _require_str(sales_profile.slug, "sales_profile.slug"),
            "customer_phone": "50476667777",
            "customer_name": "Cliente Orquestado",
            "message_content": "Hola, tienen equipos?",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["reply"] == "Respuesta simulada"
    assert payload.get("order") is None


def test_ai_handle_message_creates_order_when_intent_present(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    location, sales_profile = seed_location_and_sales_profile(db_session)
    location_id = _require_pk(location.id, "location.id")
    product = seed_product(client, location_id)
    _configure_ai_profile(db_session, _require_pk(sales_profile.id, "sales_profile.id"))

    monkeypatch.setattr(prod_settings, "ENABLE_AI_FEATURES", True)
    monkeypatch.setattr(prod_settings, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ai_intelligence, "openai_service", _DummyOpenAIService())

    response: Response = client.post(
        "/api/ai/handle-message",
        json={
            "sales_profile_slug": _require_str(sales_profile.slug, "sales_profile.slug"),
            "customer_phone": "50478889999",
            "customer_name": "Cliente Orquestado",
            "message_content": "Quiero ese teléfono",
            "order_intent": {
                "source_location_id": location_id,
                "items": [
                    {
                        "product_id": int(product["id"]),
                        "cantidad": 1,
                        "imeis": ["111111111111111"],
                    }
                ],
                "metodo_pago": "efectivo",
                "canal": "whatsapp",
                "auto_create": True,
                "auto_link_interaction": True,
            },
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["reply"] == "Respuesta simulada"
    order_payload = payload.get("order")
    assert order_payload is not None
    assert order_payload["status"] == "created"
    assert isinstance(order_payload["order_id"], int)


def test_ai_handle_message_is_idempotent_with_message_id(
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
    monkeypatch.setattr(ai_intelligence, "openai_service", _DummyOpenAIService())

    payload = {
        "sales_profile_slug": _require_str(sales_profile.slug, "sales_profile.slug"),
        "customer_phone": "50470000001",
        "customer_name": "Cliente Idempotente",
        "message_content": "Hola, tienen disponibilidad?",
        "message_id": "msg-dup-001",
        "channel_hint": "whatsapp",
    }

    first = client.post("/api/ai/handle-message", json=payload)
    assert first.status_code == 200, first.text

    second = client.post("/api/ai/handle-message", json=payload)
    assert second.status_code == 200, second.text
    assert second.json()["model"] == "duplicate-guard"

    rows = db_session.query(ProcessedMessage).filter(ProcessedMessage.message_id == "msg-dup-001").count()
    assert rows == 1


def test_ai_reply_uses_local_fallback_when_openai_fails(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    class _FailingOpenAIService:
        def create_chat_completion(self, **kwargs: Any) -> Dict[str, Any]:
            raise RuntimeError("OpenAI unavailable")

    location, sales_profile = seed_location_and_sales_profile(db_session)
    location_id = _require_pk(location.id, "location.id")
    seed_product(client, location_id)
    _configure_ai_profile(db_session, _require_pk(sales_profile.id, "sales_profile.id"))

    monkeypatch.setattr(prod_settings, "ENABLE_AI_FEATURES", True)
    monkeypatch.setattr(prod_settings, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ai_intelligence, "openai_service", _FailingOpenAIService())

    response = client.post(
        "/api/ai/reply",
        json={
            "sales_profile_slug": _require_str(sales_profile.slug, "sales_profile.slug"),
            "customer_phone": "50470000002",
            "customer_name": "Cliente Fallback",
            "message_content": "¿Cuánto cuesta?",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["model"] == "fallback-local"
    assert isinstance(payload["reply"], str)
    assert payload["reply"] != ""