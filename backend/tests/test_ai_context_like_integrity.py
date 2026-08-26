from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.ai_context_search import ilike_contains_literal
from app.models import FAQEntry, Product


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
