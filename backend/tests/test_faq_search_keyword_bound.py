from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import FAQEntry
from app.routers.faq import MAX_FAQ_SEARCH_KEYWORDS, search_faq_entries


def _faq(db_session: Session, question: str) -> FAQEntry:
    faq = FAQEntry(
        pregunta_clave=question,
        ejemplo_pregunta_cliente=None,
        respuesta=f"Respuesta {uuid4().hex}",
        categoria="general",
        activa=True,
        veces_usada=0,
    )
    db_session.add(faq)
    db_session.commit()
    db_session.refresh(faq)
    return faq


def test_faq_search_limits_sql_keyword_expansion_to_six(db_session: Session) -> None:
    first_keyword_match = _faq(db_session, "alphaone respuesta prioritaria")
    seventh_keyword_only = _faq(db_session, "needle-seven-only respuesta tardia")

    rows = search_faq_entries(
        query=(
            "alphaone betatwo gammathree deltafour epsilonfive zetasix "
            "needle-seven-only"
        ),
        limit=20,
        db=db_session,
    )
    ids = [faq.id for faq in rows]

    assert MAX_FAQ_SEARCH_KEYWORDS == 6
    assert first_keyword_match.id in ids
    assert seventh_keyword_only.id not in ids


def test_faq_search_keeps_literal_percent_semantics(db_session: Session) -> None:
    literal = _faq(db_session, "Aceptamos 100% de prima")
    decoy = _faq(db_session, "Aceptamos 100X de prima")

    rows = search_faq_entries(query="100%", limit=20, db=db_session)
    ids = [faq.id for faq in rows]

    assert literal.id in ids
    assert decoy.id not in ids
