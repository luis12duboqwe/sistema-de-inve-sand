import concurrent.futures
import os
import socket
import subprocess
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import requests


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_until_ready(base_url: str, timeout_seconds: int = 45) -> None:
    deadline = time.time() + timeout_seconds
    last_body = ""
    while time.time() < deadline:
        try:
            response = requests.get(f"{base_url}/api/ready", timeout=2)
            last_body = response.text
            if response.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(0.4)
    raise AssertionError(
        f"El backend PostgreSQL no quedó listo dentro del timeout. Última respuesta: {last_body}"
    )


def _assert_isolated_postgres_dsn(database_url: str) -> None:
    """Never run write-heavy auth/inventory E2E against production databases."""
    parsed = urlsplit(database_url)
    database = parsed.path.lstrip("/")
    if (not parsed.scheme.startswith("postgresql")
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or database not in {"inventory_e2e", "inventory_browser_e2e"}):
        raise AssertionError(
            "E2E destructivo sólo admite PostgreSQL local y base descartable inventory_e2e."
        )


def _start_backend() -> tuple[subprocess.Popen, str]:
    database_url = os.environ.get("DATABASE_URL", "")
    _assert_isolated_postgres_dsn(database_url)

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.update(
        {
            "ENVIRONMENT": "testing",
            "DEBUG": "true",
            "DATABASE_URL": database_url,
            "SENTRY_DISABLED": "true",
            "ENABLE_AI_FEATURES": "false",
            "PYTHONPATH": str(BACKEND_DIR),
        }
    )

    process = subprocess.Popen(
        [
            "python",
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(BACKEND_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        _wait_until_ready(base_url)
    except Exception:
        process.terminate()
        output, _ = process.communicate(timeout=10)
        raise AssertionError(f"No se pudo iniciar el backend PostgreSQL:\n{output}")
    return process, base_url


def _stop_backend(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _request_json(method: str, url: str, *, headers=None, json=None, data=None, expected_status=200):
    response = requests.request(method, url, headers=headers, json=json, data=data, timeout=20)
    if response.status_code != expected_status:
        raise AssertionError(f"{method} {url} => {response.status_code}, body={response.text}")
    return response.json() if response.text else {}


def _setup_admin(base_url: str) -> dict[str, str]:
    username = f"admin{uuid.uuid4().hex[:8]}"
    password = "StrongAdminPass!2026"
    _request_json(
        "POST",
        f"{base_url}/api/auth/setup",
        json={
            "username": username,
            "password": password,
            "email": f"{username}@example.com",
            "full_name": "PostgreSQL E2E Admin",
        },
    )
    token_payload = _request_json(
        "POST",
        f"{base_url}/api/auth/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return {"Authorization": f"Bearer {token_payload['access_token']}"}


def _items(payload):
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload["items"]
    if isinstance(payload, list):
        return payload
    return []


def test_postgres_real_auth_readiness_and_stock_concurrency():
    process, base_url = _start_backend()
    try:
        ready = requests.get(f"{base_url}/api/ready", timeout=5)
        assert ready.status_code == 200
        assert ready.json()["database"] == "connected"

        headers = _setup_admin(base_url)

        location = _request_json(
            "POST",
            f"{base_url}/api/locations",
            headers=headers,
            json={
                "nombre": f"Tienda PG {uuid.uuid4().hex[:6]}",
                "tipo": "tienda",
                "direccion": "Prueba PostgreSQL",
                "activo": True,
            },
            expected_status=201,
        )
        sales_profile = _request_json(
            "POST",
            f"{base_url}/api/sales-profiles",
            headers=headers,
            json={
                "name": f"Ventas PG {uuid.uuid4().hex[:6]}",
                "slug": f"ventas-pg-{uuid.uuid4().hex[:8]}",
                "tipo": "vendedor_humano",
                "canales": ["tienda"],
                "active": True,
            },
            expected_status=201,
        )

        imei = f"{uuid.uuid4().int % 10**15:015d}"
        product = _request_json(
            "POST",
            f"{base_url}/api/products",
            headers=headers,
            json={
                "sku": f"PG-{uuid.uuid4().hex[:10]}",
                "nombre": "Equipo concurrencia PostgreSQL",
                "categoria": "celular",
                "marca": "Test",
                "modelo": "PG-Lock",
                "color": "Negro",
                "capacidad": "128GB",
                "condicion": "nuevo",
                "precio": 10000,
                "costo": 7000,
                "moneda": "Lps",
                "garantia_meses": 12,
                "stock_inicial": 1,
                "initial_location_id": location["id"],
                "imeis": [imei],
            },
            expected_status=201,
        )

        def create_order(customer_suffix: str):
            return requests.post(
                f"{base_url}/api/orders",
                headers=headers,
                json={
                    "sales_profile_slug": sales_profile["slug"],
                    "source_location_id": location["id"],
                    "canal": "tienda",
                    "customer_name": f"Cliente {customer_suffix}",
                    "customer_phone": f"+5049{uuid.uuid4().int % 10**7:07d}",
                    "metodo_pago": "efectivo",
                    "items": [
                        {
                            "product_id": product["id"],
                            "cantidad": 1,
                            "imeis": [imei],
                        }
                    ],
                },
                timeout=30,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(create_order, ["A", "B"]))

        statuses = sorted(response.status_code for response in responses)
        assert statuses == [201, 409] or statuses == [400, 201], (
            "Los fallos 500/503 no demuestran concurrencia correcta: "
            + str([(response.status_code, response.text) for response in responses])
        )
        # Debe haberse persistido exactamente una orden válida sin efectos
        # parciales del segundo intento.
        orders = _items(_request_json("GET", f"{base_url}/api/orders?per_page=100", headers=headers))
        matching = [item for item in orders if item["source_location_id"] == location["id"]]
        assert len(matching) == 1, matching
        created = matching[0]
        assert len(created.get("items") or []) == 1, created
        assert created["items"][0]["product_id"] == product["id"]

        products = _items(
            _request_json(
                "GET",
                f"{base_url}/api/products?search={product['sku']}&include_inactive=true",
                headers=headers,
            )
        )
        matched = next(item for item in products if item["id"] == product["id"])
        assert matched["stock_disponible"] == 0
    finally:
        _stop_backend(process)


def test_pg_runtime_e2e_rejects_any_prod_or_remote_database():
    import pytest

    with pytest.raises(AssertionError):
        _assert_isolated_postgres_dsn(
            "postgresql+psycopg2://user:pass@production.example:5432/inventory_live"
        )
    with pytest.raises(AssertionError):
        _assert_isolated_postgres_dsn(
            "postgresql+psycopg2://user:pass@127.0.0.1:5432/inventory_live"
        )
    _assert_isolated_postgres_dsn(
        "postgresql+psycopg2://inventory_e2e:password@127.0.0.1:5432/inventory_e2e"
    )
