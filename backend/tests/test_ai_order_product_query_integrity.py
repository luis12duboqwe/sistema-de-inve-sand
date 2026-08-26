from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Order, Product, Stock
from app.routers import ai_intelligence, ai_order_product_integrity
from .helpers import seed_location_and_sales_profile


def _seed_stocked_product(
    db_session: Session,
    *,
    location_id: int,
    nombre: str,
    sku_prefix: str,
) -> Product:
    suffix = uuid4().hex
    product = Product(
        sku=f"{sku_prefix}-{suffix}",
        nombre=nombre,
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
    db_session.flush()
    db_session.add(
        Stock(
            product_id=product.id,
            location_id=location_id,
            cantidad_disponible=2,
            cantidad_reservada=0,
            cantidad_defectuosa=0,
        )
    )
    db_session.commit()
    db_session.refresh(product)
    return product


@pytest.mark.parametrize(
    ("query_text", "wildcard_decoy"),
    [
        ("Accesorio 100% Original", "Accesorio 100X Original"),
        ("Cable_USB", "CableXUSB"),
        (r"Ruta\Pro", "RutaPro"),
    ],
)
def test_ai_order_product_query_does_not_match_wildcard_decoy(
    db_session: Session,
    query_text: str,
    wildcard_decoy: str,
) -> None:
    location, _ = seed_location_and_sales_profile(db_session)
    _seed_stocked_product(
        db_session,
        location_id=int(location.id),
        nombre=wildcard_decoy,
        sku_prefix="AI-DECOY",
    )

    with pytest.raises(HTTPException) as exc_info:
        ai_order_product_integrity.resolve_product_for_ai_item_integrity(
            db_session,
            source_location_id=int(location.id),
            product_id=None,
            product_query=query_text,
        )

    assert exc_info.value.status_code == 404


def test_ai_order_product_query_still_supports_literal_partial_match(
    db_session: Session,
) -> None:
    location, _ = seed_location_and_sales_profile(db_session)
    literal = _seed_stocked_product(
        db_session,
        location_id=int(location.id),
        nombre="Accesorio 100% Original",
        sku_prefix="AI-LITERAL",
    )
    _seed_stocked_product(
        db_session,
        location_id=int(location.id),
        nombre="Accesorio 100X Original",
        sku_prefix="AI-DECOY",
    )

    resolved = ai_order_product_integrity.resolve_product_for_ai_item_integrity(
        db_session,
        source_location_id=int(location.id),
        product_id=None,
        product_query="100%",
    )

    assert resolved.id == literal.id


def test_ai_order_product_id_priority_is_preserved(db_session: Session) -> None:
    location, _ = seed_location_and_sales_profile(db_session)
    selected = _seed_stocked_product(
        db_session,
        location_id=int(location.id),
        nombre="Producto seleccionado por ID",
        sku_prefix="AI-ID",
    )

    resolved = ai_order_product_integrity.resolve_product_for_ai_item_integrity(
        db_session,
        source_location_id=int(location.id),
        product_id=int(selected.id),
        product_query="texto que no coincide",
    )

    assert resolved.id == selected.id


def test_ai_order_runtime_uses_literal_safe_resolver(
    client: TestClient,
    db_session: Session,
) -> None:
    location, sales_profile = seed_location_and_sales_profile(db_session)
    _seed_stocked_product(
        db_session,
        location_id=int(location.id),
        nombre="Accesorio 100X Runtime",
        sku_prefix="AI-RUNTIME-DECOY",
    )

    assert (
        ai_intelligence._resolve_product_for_ai_item
        is ai_order_product_integrity.resolve_product_for_ai_item_integrity
    )

    response = client.post(
        "/api/ai/create-order",
        json={
            "sales_profile_slug": str(sales_profile.slug),
            "source_location_id": int(location.id),
            "customer_phone": "50470009999",
            "customer_name": "Cliente wildcard",
            "items": [
                {
                    "product_query": "Accesorio 100% Runtime",
                    "cantidad": 1,
                }
            ],
        },
    )

    assert response.status_code == 404, response.text
    assert db_session.query(Order).count() == 0
