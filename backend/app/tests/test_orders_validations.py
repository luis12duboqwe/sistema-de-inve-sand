from decimal import Decimal
from typing import Any, Dict, Iterable, List, Tuple, cast

from fastapi.testclient import TestClient
from httpx import Response as HTTPResponse
from sqlalchemy.orm import Session

from app.models import Location, Product, SalesProfile, Stock

OrderDependencies = Tuple[Location, SalesProfile, Product]
OrderPayload = Dict[str, Any]
ErrorList = List[Dict[str, Any]]


def _as_str_dict(candidate: object) -> Dict[str, Any] | None:
    if isinstance(candidate, dict):
        str_only: Dict[str, Any] = {}
        candidate_dict = cast(Dict[Any, Any], candidate)
        items: Iterable[Tuple[Any, Any]] = candidate_dict.items()
        for key_candidate, value in items:
            if not isinstance(key_candidate, str):
                return None
            str_only[key_candidate] = value
        return str_only
    return None


def _extract_detail(response: HTTPResponse) -> ErrorList:
    payload = _as_str_dict(response.json())
    if payload is not None:
        detail_candidate = payload.get("detail", [])
        if isinstance(detail_candidate, list):
            detail_field = cast(List[object], detail_candidate)
            parsed: ErrorList = []
            for entry in detail_field:
                entry_dict = _as_str_dict(entry)
                if entry_dict is not None:
                    parsed.append(entry_dict)
            return parsed
    return []


def _extract_detail_text(response: HTTPResponse) -> str:
    payload = _as_str_dict(response.json())
    if payload is not None:
        return str(payload.get("detail", ""))
    return ""


def _detail_has_field(detail: ErrorList, field_name: str) -> bool:
    for entry in detail:
        loc_value = entry.get("loc")
        if isinstance(loc_value, list) and loc_value and loc_value[-1] == field_name:
            return True
    return False


def _create_order_dependencies(db_session: Session) -> OrderDependencies:
    location = Location(
        nombre="Tienda Centro",
        tipo="tienda",
        direccion="",
        telefono="",
        activo=True,
    )
    sales_profile = SalesProfile(
        name="Bot QA",
        slug="bot-qa",
        tipo="bot_ia",
        canales='["whatsapp"]',
        active=True,
    )
    product = Product(
        sku="SKU-VALID-1",
        nombre="Telefono QA",
        categoria="celular",
        marca="Marca QA",
        modelo="Modelo QA",
        condicion="nuevo",
        precio=Decimal("1000.00"),
        costo=Decimal("800.00"),
        moneda="HNL",
        garantia_meses=12,
        activo=True,
        is_serialized=False,
    )

    db_session.add_all([location, sales_profile, product])
    db_session.flush()

    stock = Stock(
        product_id=product.id,
        location_id=location.id,
        cantidad_disponible=5,
        cantidad_reservada=0,
        cantidad_defectuosa=0,
    )
    db_session.add(stock)
    db_session.commit()
    return location, sales_profile, product


def _base_payload(
    location: Location,
    sales_profile: SalesProfile,
    product: Product,
) -> OrderPayload:
    precio_value = product.precio
    if not isinstance(precio_value, Decimal):
        raise AssertionError("Product price should be a Decimal during tests")
    return {
        "sales_profile_slug": sales_profile.slug,
        "source_location_id": location.id,
        "canal": "whatsapp",
        "customer_name": "Cliente QA",
        "customer_phone": "+504 9999-1111",
        "metodo_pago": "efectivo",
        "items": [
            {
                "product_id": product.id,
                "cantidad": 1,
                "precio_unitario": float(precio_value),
            }
        ],
    }


def test_create_order_invalid_phone_format_returns_422(
    client: TestClient,
    db_session: Session,
) -> None:
    location, sales_profile, product = _create_order_dependencies(db_session)
    payload: OrderPayload = _base_payload(location, sales_profile, product)
    payload["customer_phone"] = "abc"

    response: HTTPResponse = client.post("/api/orders", json=payload)
    detail = _extract_detail(response)

    assert response.status_code == 422
    assert any("Formato de teléfono" in error.get("msg", "") for error in detail)


def test_create_order_short_phone_digits_returns_400(
    client: TestClient,
    db_session: Session,
) -> None:
    location, sales_profile, product = _create_order_dependencies(db_session)
    payload: OrderPayload = _base_payload(location, sales_profile, product)
    payload["customer_phone"] = "1234567"  # Solo 7 dígitos

    response: HTTPResponse = client.post("/api/orders", json=payload)
    detail_text = _extract_detail_text(response)

    assert response.status_code == 400
    assert "al menos 8 dígitos" in detail_text


def test_create_order_rejects_notes_over_limit(
    client: TestClient,
    db_session: Session,
) -> None:
    location, sales_profile, product = _create_order_dependencies(db_session)
    payload: OrderPayload = _base_payload(location, sales_profile, product)
    payload["notes"] = "a" * 1200

    response: HTTPResponse = client.post("/api/orders", json=payload)
    detail = _extract_detail(response)

    assert response.status_code == 422
    assert any("notas" in error.get("msg", "") for error in detail)


def test_create_order_rejects_customer_name_over_limit(
    client: TestClient,
    db_session: Session,
) -> None:
    location, sales_profile, product = _create_order_dependencies(db_session)
    payload: OrderPayload = _base_payload(location, sales_profile, product)
    payload["customer_name"] = "X" * 205

    response: HTTPResponse = client.post("/api/orders", json=payload)
    detail = _extract_detail(response)

    assert response.status_code == 422
    assert any("customer_name" in error.get("msg", "") for error in detail)


def test_create_order_rejects_blank_customer_name(
    client: TestClient,
    db_session: Session,
) -> None:
    location, sales_profile, product = _create_order_dependencies(db_session)
    payload: OrderPayload = _base_payload(location, sales_profile, product)
    payload["customer_name"] = "   "

    response: HTTPResponse = client.post("/api/orders", json=payload)
    detail = _extract_detail(response)

    assert response.status_code == 422
    assert any("obligatorio" in error.get("msg", "") for error in detail)


def test_create_order_trade_in_requires_brand(
    client: TestClient,
    db_session: Session,
) -> None:
    location, sales_profile, product = _create_order_dependencies(db_session)
    payload: OrderPayload = _base_payload(location, sales_profile, product)
    payload["trade_ins"] = [
        {
            "marca": "",
            "modelo": "Modelo QA",
            "condicion": "usado",
            "valor_estimado": 500,
        }
    ]

    response: HTTPResponse = client.post("/api/orders", json=payload)
    detail = _extract_detail(response)

    assert response.status_code == 422
    assert _detail_has_field(detail, "marca")


def test_create_order_trade_in_requires_positive_value(
    client: TestClient,
    db_session: Session,
) -> None:
    location, sales_profile, product = _create_order_dependencies(db_session)
    payload: OrderPayload = _base_payload(location, sales_profile, product)
    payload["trade_ins"] = [
        {
            "marca": "Marca QA",
            "modelo": "Modelo QA",
            "condicion": "usado",
            "valor_estimado": 0,
        }
    ]

    response: HTTPResponse = client.post("/api/orders", json=payload)
    detail = _extract_detail(response)

    assert response.status_code == 422
    assert _detail_has_field(detail, "valor_estimado")


def test_create_order_trade_in_notes_limit(
    client: TestClient,
    db_session: Session,
) -> None:
    location, sales_profile, product = _create_order_dependencies(db_session)
    payload: OrderPayload = _base_payload(location, sales_profile, product)
    payload["trade_ins"] = [
        {
            "marca": "Marca QA",
            "modelo": "Modelo QA",
            "condicion": "usado",
            "valor_estimado": 500,
            "notas": "a" * 600,
        }
    ]

    response: HTTPResponse = client.post("/api/orders", json=payload)
    detail = _extract_detail(response)

    assert response.status_code == 422
    assert any("retoma" in error.get("msg", "") for error in detail)


def test_create_order_trade_in_invalid_imei(
    client: TestClient,
    db_session: Session,
) -> None:
    location, sales_profile, product = _create_order_dependencies(db_session)
    payload: OrderPayload = _base_payload(location, sales_profile, product)
    payload["trade_ins"] = [
        {
            "marca": "Marca QA",
            "modelo": "Modelo QA",
            "condicion": "usado",
            "valor_estimado": 500,
            "imei": "12345",
        }
    ]

    response: HTTPResponse = client.post("/api/orders", json=payload)
    detail = _extract_detail(response)

    assert response.status_code == 422
    assert any("IMEI" in error.get("msg", "") for error in detail)
