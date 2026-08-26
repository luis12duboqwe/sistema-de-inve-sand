from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ai_context_search import ilike_contains_literal
from app.models import FAQEntry, Product, Stock
from .helpers import seed_location_and_sales_profile


def _product(db_session: Session, name: str) -> Product:
    suffix = uuid4().hex
    product = Product(
        sku=f"AI-CONTEXT-{suffix}",
        nombre=name,
        categoria="accesorio",
        marca="Marca QA",
        modelo=f"Modelo-{suffix[:8]}",
        condicion="nuevo",
        precio=100,
        costo=50,
        moneda="Lps",
        garantia_meses=0,
        activo=True,
        is_serialized=False,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


def _stocked_product(
    db_session: Session,
    *,
    location_id: int,
    name: str,
    stock: int,
) -> Product:
    suffix = uuid4().hex
    product = Product(
        sku=f"AI-CONTEXT-RUNTIME-{suffix}",
        nombre=name,
        categoria="accesorio",
        marca="Marca Runtime",
        modelo=f"Runtime-{suffix[:8]}",
        condicion="nuevo",
        precio=100,
        costo=50,
        moneda="Lps",
        garantia_meses=0,
        activo=True,
        is_serialized=False,
    )
    db_session.add(product)
    db_session.flush()
    db_session.add(
        Stock(
            product_id=product.id,
            location_id=location_id,
            cantidad_disponible=stock,
            cantidad_reservada=0,
            cantidad_defectuosa=0,
        )
    )
    return product


@pytest.mark.parametrize(
    ("search_text", "literal_name", "wildcard_decoy"),
    [
        ("100%", "Accesorio 100% Context", "Accesorio 100X Context"),
        ("Cable_USB", "Cable_USB Context", "CableXUSB Context"),
        (r"Ruta\Pro", r"Ruta\Pro Context", "RutaPro Context"),
    ],
)
def test_ai_context_literal_contains_does_not_expand_metacharacters(
    db_session: Session,
    search_text: str,
    literal_name: str,
    wildcard_decoy: str,
) -> None:
    literal = _product(db_session, literal_name)
    _product(db_session, wildcard_decoy)

    rows = (
        db_session.query(Product)
        .filter(ilike_contains_literal(Product.nombre, search_text))
        .all()
    )

    assert [product.id for product in rows] == [literal.id]


def test_ai_context_literal_contains_is_reusable_for_faq_lookup(
    db_session: Session,
) -> None:
    literal = FAQEntry(
        pregunta_clave="¿Aceptan 100% de prima?",
        respuesta="Respuesta literal",
        categoria="general",
        activa=True,
    )
    decoy = FAQEntry(
        pregunta_clave="¿Aceptan 100X de prima?",
        respuesta="Respuesta decoy",
        categoria="general",
        activa=True,
    )
    db_session.add_all([literal, decoy])
    db_session.commit()

    rows = (
        db_session.query(FAQEntry)
        .filter(ilike_contains_literal(FAQEntry.pregunta_clave, "100%"))
        .all()
    )

    assert [faq.id for faq in rows] == [literal.id]


@pytest.mark.parametrize(
    ("search_text", "literal_token", "decoy_token"),
    [
        ("100%", "100%", "100X"),
        ("Cable_USB", "Cable_USB", "CableXUSB"),
        (r"Ruta\Pro", r"Ruta\Pro", "RutaPro"),
    ],
)
def test_canonical_ai_context_promotes_only_literal_keyword_matches(
    client: TestClient,
    db_session: Session,
    search_text: str,
    literal_token: str,
    decoy_token: str,
) -> None:
    location, sales_profile = seed_location_and_sales_profile(db_session)
    assert isinstance(location.id, int)
    assert isinstance(sales_profile.slug, str)

    literal_product = _stocked_product(
        db_session,
        location_id=location.id,
        name=f"Literal {literal_token} Producto",
        stock=50,
    )
    decoy_product = _stocked_product(
        db_session,
        location_id=location.id,
        name=f"Decoy {decoy_token} Producto",
        stock=1,
    )

    # Fifteen higher-stock fillers consume the complete top-stock fallback cutoff.
    # Without keyword promotion, neither the literal product nor decoy can re-enter.
    for index in range(15):
        _stocked_product(
            db_session,
            location_id=location.id,
            name=f"Context Filler {index:02d}",
            stock=100 - index,
        )

    now = datetime.now(UTC)
    literal_faq = FAQEntry(
        pregunta_clave=f"FAQ literal {literal_token}",
        respuesta="Respuesta literal runtime",
        categoria="general",
        activa=True,
        created_at=now - timedelta(days=2),
    )
    decoy_faq = FAQEntry(
        pregunta_clave=f"FAQ decoy {decoy_token}",
        respuesta="Respuesta decoy runtime",
        categoria="general",
        activa=True,
        created_at=now - timedelta(days=3),
    )
    db_session.add_all([literal_faq, decoy_faq])
    for index in range(5):
        db_session.add(
            FAQEntry(
                pregunta_clave=f"FAQ reciente {index}",
                respuesta=f"Respuesta reciente {index}",
                categoria="general",
                activa=True,
                created_at=now + timedelta(minutes=index + 1),
            )
        )
    db_session.commit()

    response = client.post(
        "/api/ai/context",
        json={
            "sales_profile_slug": sales_profile.slug,
            "customer_phone": f"504{uuid4().int % 100_000_000:08d}",
            "customer_name": "Cliente Context Runtime",
            "message_content": search_text,
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    inventory = payload["relevant_inventory"]
    faqs = payload["relevant_faqs"]

    assert literal_product.nombre in inventory
    assert decoy_product.nombre not in inventory
    assert "Context Filler 00" in inventory

    assert literal_faq.pregunta_clave in faqs
    assert decoy_faq.pregunta_clave not in faqs
    assert "FAQ reciente" in faqs
