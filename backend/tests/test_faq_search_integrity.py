from app.models import FAQEntry


def _seed_faq(
    db_session,
    *,
    pregunta_clave: str,
    ejemplo: str | None = None,
    veces_usada: int = 0,
) -> FAQEntry:
    faq = FAQEntry(
        pregunta_clave=pregunta_clave,
        ejemplo_pregunta_cliente=ejemplo,
        respuesta=f"Respuesta para {pregunta_clave}",
        categoria="ventas",
        nivel_seriedad="normal",
        activa=True,
        veces_usada=veces_usada,
    )
    db_session.add(faq)
    db_session.commit()
    db_session.refresh(faq)
    return faq


def test_faq_search_treats_percent_wildcard_as_literal(client, db_session):
    percent_faq = _seed_faq(
        db_session,
        pregunta_clave="Descuento 10% en accesorios",
    )
    unrelated_faq = _seed_faq(
        db_session,
        pregunta_clave="Garantía para celulares",
    )

    response = client.get("/api/faq/search", params={"query": "%", "limit": 20})

    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()] == [percent_faq.id]

    db_session.expire_all()
    assert db_session.get(FAQEntry, percent_faq.id).veces_usada == 1
    assert db_session.get(FAQEntry, unrelated_faq.id).veces_usada == 0


def test_faq_search_treats_underscore_wildcard_as_literal(client, db_session):
    underscore_faq = _seed_faq(
        db_session,
        pregunta_clave="Código_plan especial",
    )
    unrelated_faq = _seed_faq(
        db_session,
        pregunta_clave="Código plan normal",
    )

    response = client.get("/api/faq/search", params={"query": "_", "limit": 20})

    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()] == [underscore_faq.id]

    db_session.expire_all()
    assert db_session.get(FAQEntry, underscore_faq.id).veces_usada == 1
    assert db_session.get(FAQEntry, unrelated_faq.id).veces_usada == 0


def test_faq_search_keeps_normal_keyword_behavior(client, db_session):
    warranty_faq = _seed_faq(
        db_session,
        pregunta_clave="Garantía para celulares",
        ejemplo="¿Cuánto dura la garantía?",
    )
    _seed_faq(db_session, pregunta_clave="Métodos de pago")

    response = client.get("/api/faq/search", params={"query": "garantía"})

    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()] == [warranty_faq.id]


def test_faq_search_rejects_out_of_range_limits(client):
    too_small = client.get("/api/faq/search", params={"query": "garantía", "limit": 0})
    too_large = client.get("/api/faq/search", params={"query": "garantía", "limit": 21})

    assert too_small.status_code == 422
    assert too_large.status_code == 422
