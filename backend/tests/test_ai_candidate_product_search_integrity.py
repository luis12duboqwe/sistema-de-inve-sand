from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models import Customer, Product
from app.routers import ai_candidate_product_integrity, ai_intelligence


def _product(db_session: Session, *, nombre: str, sku_prefix: str) -> Product:
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
    db_session.commit()
    db_session.refresh(product)
    return product


@pytest.mark.parametrize(
    ("query_text", "wildcard_decoy"),
    [
        ("100%", "Accesorio 100X Original"),
        ("Cable_USB", "CableXUSB"),
        (r"Ruta\Pro", "RutaPro"),
    ],
)
def test_candidate_search_does_not_expand_like_metacharacters(
    db_session: Session,
    query_text: str,
    wildcard_decoy: str,
) -> None:
    _product(db_session, nombre=wildcard_decoy, sku_prefix="AI-CAND-DECOY")

    candidates = ai_candidate_product_integrity.find_candidate_products_integrity(
        db_session,
        query_text,
    )

    assert candidates == []


def test_candidate_search_keeps_literal_partial_match(db_session: Session) -> None:
    literal = _product(
        db_session,
        nombre="Accesorio 100% Original",
        sku_prefix="AI-CAND-LITERAL",
    )
    _product(
        db_session,
        nombre="Accesorio 100X Original",
        sku_prefix="AI-CAND-DECOY",
    )

    candidates = ai_candidate_product_integrity.find_candidate_products_integrity(
        db_session,
        "100%",
    )

    assert [product.id for product in candidates] == [literal.id]


def test_candidate_search_preserves_all_keyword_first_pass(db_session: Session) -> None:
    both = _product(db_session, nombre="Alpha Beta Combo", sku_prefix="AI-CAND-BOTH")
    _product(db_session, nombre="Alpha Solo", sku_prefix="AI-CAND-ALPHA")
    _product(db_session, nombre="Beta Solo", sku_prefix="AI-CAND-BETA")

    candidates = ai_candidate_product_integrity.find_candidate_products_integrity(
        db_session,
        "Alpha Beta",
    )

    assert [product.id for product in candidates] == [both.id]


def test_candidate_search_preserves_or_fallback(db_session: Session) -> None:
    alpha = _product(db_session, nombre="Alpha Solo", sku_prefix="AI-CAND-ALPHA")

    candidates = ai_candidate_product_integrity.find_candidate_products_integrity(
        db_session,
        "Alpha Missing",
    )

    assert alpha.id in {product.id for product in candidates}


def test_candidate_search_preserves_last_referenced_product_context(
    db_session: Session,
) -> None:
    referenced = _product(
        db_session,
        nombre="Alpha Phone",
        sku_prefix="AI-CAND-MEMORY",
    )
    customer = Customer(
        phone_number=f"504{uuid4().int % 100_000_000:08d}",
        name="Cliente memoria",
        last_referenced_product_name="Alpha Phone",
    )
    db_session.add(customer)
    db_session.commit()

    candidates = ai_candidate_product_integrity.find_candidate_products_integrity(
        db_session,
        "gris",
        customer,
    )

    assert referenced.id in {product.id for product in candidates}


def test_candidate_search_runtime_boundary_rejects_wildcard_decoy(
    db_session: Session,
) -> None:
    decoy = _product(
        db_session,
        nombre="Accesorio 100X Runtime",
        sku_prefix="AI-CAND-RUNTIME",
    )

    assert (
        ai_intelligence._find_candidate_products
        is ai_candidate_product_integrity.find_candidate_products_integrity
    )
    assert ai_intelligence._find_product_name_hint(db_session, "100%") == "Producto solicitado"
    assert decoy.nombre != "Producto solicitado"
