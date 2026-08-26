from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ai_context_search import (
    MAX_AI_CONTEXT_SQL_KEYWORDS,
    bound_ai_context_sql_keywords,
)
from app.config_production import prod_settings
from app.routers import ai_intelligence
from .helpers import seed_location_and_sales_profile


def test_ai_context_sql_keyword_helper_preserves_first_six_only() -> None:
    values = [
        "alphaone",
        "betatwo",
        "gammathree",
        "deltafour",
        "epsilonfive",
        "zetasix",
        "seventhterm",
    ]

    assert MAX_AI_CONTEXT_SQL_KEYWORDS == 6
    assert bound_ai_context_sql_keywords(values) == values[:6]
    assert values[-1] == "seventhterm"


def test_ai_context_runtime_bounds_inventory_and_faq_sql_terms(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    _, sales_profile = seed_location_and_sales_profile(db_session)
    monkeypatch.setattr(prod_settings, "ENABLE_AI_FEATURES", True)

    original_bound = ai_intelligence.bound_ai_context_sql_keywords
    original_ilike = ai_intelligence.ilike_contains_literal
    bound_inputs: list[list[str]] = []
    predicate_terms: list[str] = []

    def recording_bound(values):
        snapshot = list(values)
        bound_inputs.append(snapshot)
        return original_bound(snapshot)

    def recording_ilike(column, value: str):
        predicate_terms.append(value)
        return original_ilike(column, value)

    monkeypatch.setattr(
        ai_intelligence,
        "bound_ai_context_sql_keywords",
        recording_bound,
    )
    monkeypatch.setattr(ai_intelligence, "ilike_contains_literal", recording_ilike)

    message = (
        "alphaone betatwo gammathree deltafour epsilonfive zetasix seventhterm"
    )
    response = client.post(
        "/api/ai/context",
        json={
            "sales_profile_slug": str(sales_profile.slug),
            "customer_phone": "50494440001",
            "customer_name": "Cliente Keyword Bound",
            "message_content": message,
        },
    )

    assert response.status_code == 200, response.text
    assert len(bound_inputs) == 2
    assert bound_inputs[0][-1] == "seventhterm"
    assert bound_inputs[1][-1] == "seventhterm"
    assert all(len(values) == 7 for values in bound_inputs)

    for term in (
        "alphaone",
        "betatwo",
        "gammathree",
        "deltafour",
        "epsilonfive",
        "zetasix",
    ):
        assert term in predicate_terms
    assert "seventhterm" not in predicate_terms
