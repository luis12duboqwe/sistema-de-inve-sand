import concurrent.futures
import os
import socket
import subprocess
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit
from typing import Callable
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

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


def _create_isolated_schema_url(database_url: str) -> tuple[str, Callable[[], None]]:
    """Each destructive E2E execution uses a unique disposable PostgreSQL schema."""
    schema_name = f"softmobile_e2e_{uuid.uuid4().hex[:16]}"
    admin_engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with admin_engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema_name}"'))
    except Exception:
        admin_engine.dispose()
        raise

    parsed = make_url(database_url)
    if "options" in parsed.query:
        with admin_engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema_name}" CASCADE'))
        admin_engine.dispose()
        raise AssertionError("E2E must not inherit a custom PostgreSQL search_path")
    isolated = parsed.update_query_dict({
        "options": f"-csearch_path={schema_name}",
    }).render_as_string(hide_password=False)

    def cleanup() -> None:
        try:
            with admin_engine.begin() as conn:
                conn.execute(text(f'DROP SCHEMA "{schema_name}" CASCADE'))
        finally:
            admin_engine.dispose()

    return isolated, cleanup


def _start_backend() -> tuple[subprocess.Popen, str, Callable[[], None], str]:
    database_url = os.environ.get("DATABASE_URL", "")
    _assert_isolated_postgres_dsn(database_url)

    isolated_url, cleanup = _create_isolated_schema_url(database_url)
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.update(
        {
            "ENVIRONMENT": "testing",
            "DEBUG": "true",
            "DATABASE_URL": isolated_url,
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
        cleanup()
        raise AssertionError(f"No se pudo iniciar el backend PostgreSQL:\n{output}")
    return process, base_url, cleanup, isolated_url


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
    process, base_url, cleanup, isolated_url = _start_backend()
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
        assert statuses in ([201, 400], [201, 409]), (
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

        # Check the REAL disposable PostgreSQL schema, not only API response
        # models; a losing concurrent order must not leave orphan items,
        # duplicate sales ledger entries or stale serial reservations.
        engine = create_engine(isolated_url)
        try:
            with engine.connect() as conn:
                order_rows = conn.execute(
                    text("SELECT id FROM orders WHERE source_location_id = :location"),
                    {"location": location["id"]},
                ).scalars().all()
                assert order_rows == [created["id"]]
                assert conn.execute(
                    text("SELECT COUNT(*) FROM order_items WHERE order_id = :order_id"),
                    {"order_id": created["id"]},
                ).scalar_one() == 1
                assert conn.execute(
                    text("SELECT COUNT(*) FROM order_items WHERE product_id = :product_id"),
                    {"product_id": product["id"]},
                ).scalar_one() == 1

                balance = conn.execute(
                    text("SELECT cantidad_disponible, cantidad_reservada FROM stock "
                         "WHERE product_id = :product_id AND location_id = :location_id"),
                    {"product_id": product["id"], "location_id": location["id"]},
                ).one()
                assert tuple(balance) == (0, 0)

                serial = conn.execute(
                    text("SELECT vendido, order_id, transfer_id FROM product_imeis "
                         "WHERE imei = :imei"),
                    {"imei": imei},
                ).one()
                assert tuple(serial) == (True, created["id"], None)

                movements = conn.execute(
                    text("SELECT cantidad FROM stock_history "
                         "WHERE product_id = :product_id AND referencia_tipo = 'order' "
                         "AND referencia_id = :order_id AND tipo_cambio = 'venta'"),
                    {"product_id": product["id"], "order_id": created["id"]},
                ).scalars().all()
                assert movements == [-1], movements
        finally:
            engine.dispose()
    finally:
        _stop_backend(process)
        cleanup()


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


def test_pg_e2e_schema_is_unique_and_cannot_mutate_public_schema():
    db_url = os.environ["DATABASE_URL"]
    _assert_isolated_postgres_dsn(db_url)
    isolated_url, cleanup = _create_isolated_schema_url(db_url)
    try:
        isolated_engine = create_engine(isolated_url)
        with isolated_engine.begin() as conn:
            namespace = conn.execute(text("SELECT current_schema()")).scalar_one()
            assert namespace.startswith("softmobile_e2e_")
            conn.execute(text("CREATE TABLE e2e_isolation_probe(id INTEGER)"))
        isolated_engine.dispose()
        live_engine = create_engine(db_url)
        with live_engine.connect() as conn:
            count = conn.execute(text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name='e2e_isolation_probe'"
            )).scalar_one()
            assert count == 0
        live_engine.dispose()
    finally:
        cleanup()
