from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config_production import prod_settings
from app.models import Customer
from app.routers import ai_customer_search_integrity, ai_intelligence


def _customer(
    db_session: Session,
    *,
    name: str,
    is_troll: bool = False,
    last_interaction_at: datetime | None = None,
    **overrides,
) -> Customer:
    suffix = uuid4().hex
    customer = Customer(
        phone_number=f"504{int(suffix[:8], 16) % 100_000_000:08d}",
        name=name,
        email=overrides.get("email"),
        notes=overrides.get("notes"),
        is_troll=is_troll,
        is_blocked=overrides.get("is_blocked", False),
        reputation_score=overrides.get("reputation_score", 100),
        daily_message_count=overrides.get("daily_message_count", 0),
        last_interaction_at=last_interaction_at,
        conversation_summary=overrides.get("conversation_summary"),
        ai_memory_json=overrides.get("ai_memory_json"),
        last_referenced_product_name=overrides.get("last_referenced_product_name"),
        last_referenced_color=overrides.get("last_referenced_color"),
        last_referenced_variant=overrides.get("last_referenced_variant"),
        memory_updated_at=overrides.get("memory_updated_at"),
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


@pytest.mark.parametrize(
    ("search_text", "literal_name", "wildcard_decoy"),
    [
        ("100%", "Cliente 100% VIP", "Cliente 100X VIP"),
        ("A_B", "Cliente A_B", "Cliente AXB"),
        (r"Ruta\Pro", r"Cliente Ruta\Pro", "Cliente RutaPro"),
    ],
)
def test_ai_customer_search_treats_like_metacharacters_literally(
    db_session: Session,
    search_text: str,
    literal_name: str,
    wildcard_decoy: str,
) -> None:
    literal = _customer(db_session, name=literal_name)
    _customer(db_session, name=wildcard_decoy)

    response = ai_customer_search_integrity.list_customers_ai_integrity(
        search=search_text,
        is_troll=None,
        page=1,
        per_page=50,
        db=db_session,
        current_user=None,
    )

    assert response.total == 1
    assert [item.id for item in response.items] == [literal.id]


def test_ai_customer_search_preserves_filters_pagination_order_and_memory(
    db_session: Session,
) -> None:
    now = datetime.now(UTC)
    target = _customer(
        db_session,
        name="Segmento objetivo",
        is_troll=True,
        last_interaction_at=now,
        email="cliente@example.com",
        notes="nota QA",
        is_blocked=True,
        reputation_score=77,
        daily_message_count=9,
        conversation_summary="Resumen persistente",
        ai_memory_json='{"last_intent":"pricing"}',
        last_referenced_product_name="iPhone QA",
        last_referenced_color="negro",
        last_referenced_variant="256GB",
        memory_updated_at=now,
    )

    for index in range(10):
        _customer(
            db_session,
            name=f"Segmento troll {index}",
            is_troll=True,
            last_interaction_at=now - timedelta(minutes=index + 1),
        )

    _customer(
        db_session,
        name="Segmento no troll",
        is_troll=False,
        last_interaction_at=now + timedelta(minutes=1),
    )

    first_page = ai_customer_search_integrity.list_customers_ai_integrity(
        search="Segmento",
        is_troll=True,
        page=1,
        per_page=10,
        db=db_session,
        current_user=None,
    )
    second_page = ai_customer_search_integrity.list_customers_ai_integrity(
        search="Segmento",
        is_troll=True,
        page=2,
        per_page=10,
        db=db_session,
        current_user=None,
    )

    assert first_page.total == 11
    assert first_page.pages == 2
    assert len(first_page.items) == 10
    assert len(second_page.items) == 1
    assert first_page.items[0].id == target.id
    assert first_page.items[0].email == "cliente@example.com"
    assert first_page.items[0].notes == "nota QA"
    assert first_page.items[0].is_troll is True
    assert first_page.items[0].is_blocked is True
    assert first_page.items[0].reputation_score == 77
    assert first_page.items[0].daily_message_count == 9
    assert first_page.items[0].conversation_summary == "Resumen persistente"
    assert first_page.items[0].ai_memory_json == '{"last_intent":"pricing"}'
    assert first_page.items[0].last_referenced_product_name == "iPhone QA"
    assert first_page.items[0].last_referenced_color == "negro"
    assert first_page.items[0].last_referenced_variant == "256GB"
    assert first_page.items[0].memory_updated_at == now


def _matching_get_routes(router) -> list:
    return [
        route
        for route in router.routes
        if getattr(route, "path", None) == "/api/ai/customers"
        and "GET" in (getattr(route, "methods", set()) or set())
    ]


def test_ai_customer_search_legacy_is_stripped_and_canonical_route_exists() -> None:
    assert _matching_get_routes(ai_intelligence.router) == []

    canonical_matches = _matching_get_routes(ai_customer_search_integrity.router)
    assert len(canonical_matches) == 1
    assert canonical_matches[0].endpoint is ai_customer_search_integrity.list_customers_ai_integrity


def test_ai_customer_search_runtime_respects_ai_feature_flag(
    client: TestClient,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(prod_settings, "ENABLE_AI_FEATURES", False)

    response = client.get("/api/ai/customers")

    assert response.status_code == 503
    assert "deshabilitadas" in response.json()["detail"]
