from fastapi.testclient import TestClient

from app.main import app
from app.utils.prometheus_metrics import REQUESTS_TOTAL, metric_route_template


def test_metrics_unmatched_uploads_do_not_multiply_path_labels():
    client = TestClient(app)
    before = {
        key for key in REQUESTS_TOTAL._metrics
        if key[1] == "/uploads/{path}"
    }
    for suffix in range(22):
        response = client.get(f"/uploads/untrusted-{suffix}.jpg")
        assert response.status_code == 404
    after = {
        key for key in REQUESTS_TOTAL._metrics
        if key[1] == "/uploads/{path}"
    }
    assert len(after - before) <= 1
    assert not any(
        "untrusted-" in key[1]
        for key in REQUESTS_TOTAL._metrics
    )


def test_metrics_templates_never_derive_from_unknown_url_segments():
    assert metric_route_template("/api/no-route/123/unique", None) == "/__unmatched__"
    assert metric_route_template("/uploads/secret-session/foo", None) == "/uploads/{path}"

    class Route:
        path = "/api/orders/{order_id}"

    assert metric_route_template("/api/orders/42", Route()) == "/api/orders/{order_id}"
