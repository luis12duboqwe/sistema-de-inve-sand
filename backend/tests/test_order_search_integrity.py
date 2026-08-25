from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Order, OrderItem, Product


def _order(customer_name: str, customer_phone: str) -> Order:
    return Order(
        customer_name=customer_name,
        customer_phone=customer_phone,
        canal="tienda",
        metodo_pago="efectivo",
        total=Decimal("100.00"),
        estado="pendiente",
    )


def test_customer_search_treats_like_wildcards_as_literal_text(
    client: TestClient,
    db_session: Session,
) -> None:
    percent_order = _order("Cliente % Especial", "50411110000")
    underscore_order = _order("Cliente_Interno", "50422220000")
    ordinary_order = _order("Cliente Normal", "50433330000")
    db_session.add_all([percent_order, underscore_order, ordinary_order])
    db_session.commit()

    percent_response = client.post(
        "/api/orders/search",
        json={"customer_query": "%"},
    )
    assert percent_response.status_code == 200, percent_response.text
    percent_payload = percent_response.json()
    assert percent_payload["total"] == 1
    assert [item["id"] for item in percent_payload["items"]] == [percent_order.id]

    underscore_response = client.post(
        "/api/orders/search",
        json={"customer_query": "_"},
    )
    assert underscore_response.status_code == 200, underscore_response.text
    underscore_payload = underscore_response.json()
    assert underscore_payload["total"] == 1
    assert [item["id"] for item in underscore_payload["items"]] == [underscore_order.id]


def test_product_filter_counts_each_order_once_with_repeated_product_lines(
    client: TestClient,
    db_session: Session,
) -> None:
    product = Product(
        sku="SEARCH-DUP-LINES",
        nombre="Producto búsqueda",
        categoria="telefono",
        marca="Demo",
        modelo="Search",
        color="Negro",
        capacidad="128GB",
        condicion="usado",
        precio=Decimal("5000.00"),
        costo=Decimal("4000.00"),
        moneda="Lps",
        garantia_meses=0,
        activo=True,
        is_serialized=False,
    )
    order = _order("Cliente Producto", "50444440000")
    db_session.add_all([product, order])
    db_session.flush()

    db_session.add_all(
        [
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                cantidad=1,
                precio_unitario=Decimal("2500.00"),
                costo_unitario=Decimal("2000.00"),
                es_regalo_promocion=False,
            ),
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                cantidad=1,
                precio_unitario=Decimal("2500.00"),
                costo_unitario=Decimal("2000.00"),
                es_regalo_promocion=False,
            ),
        ]
    )
    db_session.commit()

    response = client.post(
        "/api/orders/search",
        params={"per_page": 1},
        json={"product_id": product.id},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == 1
    assert payload["pages"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["id"] == order.id
