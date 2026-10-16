from types import SimpleNamespace

from app.routers.daily_close import _daily_close_components


def test_daily_close_components_require_reconciliation_to_order_total():
    order = SimpleNamespace(
        total=100,
        metodo_pago="efectivo",
        payment_breakdown='[{"method":"efectivo","amount":"40"},'
                          '{"method":"transferencia","amount":"60"}]',
    )
    assert _daily_close_components(order) == [
        {"method": "efectivo", "amount": 40.0},
        {"method": "transferencia", "amount": 60.0},
    ]
    order.payment_breakdown = '[{"method":"efectivo","amount":"80"}]'
    assert _daily_close_components(order) == []
    order.payment_breakdown = None
    assert _daily_close_components(order) is None
