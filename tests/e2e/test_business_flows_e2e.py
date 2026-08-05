import os
import socket
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

import requests


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def _wait_until_ready(base_url: str, timeout_seconds: int = 30) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            response = requests.get(f"{base_url}/api/health", timeout=2)
            if response.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(0.2)
    raise AssertionError("El backend no respondió /api/health dentro del timeout")


def _start_backend() -> tuple[subprocess.Popen, str, tempfile.TemporaryDirectory]:
    temp_dir = tempfile.TemporaryDirectory(prefix="inventory-business-e2e-")
    db_path = Path(temp_dir.name) / "e2e.db"
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    env = os.environ.copy()
    env.update(
        {
            "ENVIRONMENT": "development",
            "DEBUG": "true",
            "DATABASE_URL": f"sqlite:///{db_path}",
            "SENTRY_DISABLED": "true",
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
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    _wait_until_ready(base_url)
    return process, base_url, temp_dir


def _stop_backend(process: subprocess.Popen, temp_dir: tempfile.TemporaryDirectory) -> None:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    finally:
        temp_dir.cleanup()


def _payload_items(data):
    if isinstance(data, dict) and "items" in data:
        return data["items"]
    if isinstance(data, list):
        return data
    return []


def _request_json(method: str, url: str, *, headers=None, json=None, data=None, expected_status=200):
    response = requests.request(method, url, headers=headers, json=json, data=data, timeout=20)
    if response.status_code != expected_status:
        raise AssertionError(f"{method} {url} => {response.status_code}, body={response.text}")
    if not response.text:
        return {}
    return response.json()


def _setup_admin_and_login(base_url: str) -> dict:
    admin_user = {
        "username": "superadmin",
        "password": "S3curePass!2026",
        "email": "superadmin@example.com",
        "full_name": "Super Admin",
    }

    _request_json("POST", f"{base_url}/api/auth/setup", json=admin_user, expected_status=200)

    token_payload = _request_json(
        "POST",
        f"{base_url}/api/auth/token",
        data={"username": admin_user["username"], "password": admin_user["password"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        expected_status=200,
    )
    token = token_payload["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_business_flow_end_to_end_with_real_auth():
    process, base_url, temp_dir = _start_backend()
    try:
        auth_headers = _setup_admin_and_login(base_url)

        locations = _payload_items(_request_json("GET", f"{base_url}/api/locations", headers=auth_headers))
        if len(locations) == 0:
            from_location = _request_json(
                "POST",
                f"{base_url}/api/locations",
                headers=auth_headers,
                json={"nombre": "Tienda E2E", "tipo": "tienda", "direccion": "Zona E2E", "activo": True},
                expected_status=201,
            )
            to_location = _request_json(
                "POST",
                f"{base_url}/api/locations",
                headers=auth_headers,
                json={"nombre": "Bodega E2E", "tipo": "bodega", "direccion": "Zona E2E", "activo": True},
                expected_status=201,
            )
        elif len(locations) == 1:
            from_location = locations[0]
            to_location = _request_json(
                "POST",
                f"{base_url}/api/locations",
                headers=auth_headers,
                json={"nombre": "Bodega E2E", "tipo": "bodega", "direccion": "Zona E2E", "activo": True},
                expected_status=201,
            )
        else:
            from_location = locations[0]
            to_location = locations[1]

        sales_profiles = _payload_items(_request_json("GET", f"{base_url}/api/sales-profiles?active=true", headers=auth_headers))
        sales_profile = sales_profiles[0] if sales_profiles else _request_json(
            "POST",
            f"{base_url}/api/sales-profiles",
            headers=auth_headers,
            json={"name": "E2E Bot", "slug": "e2e-bot", "tipo": "bot_ia", "canales": ["whatsapp"], "active": True},
            expected_status=201,
        )

        imei_1 = f"{uuid.uuid4().int % 10**15:015d}"
        imei_2 = f"{uuid.uuid4().int % 10**15:015d}"

        product = _request_json(
            "POST",
            f"{base_url}/api/products",
            headers=auth_headers,
            json={
                "sku": f"E2E-{uuid.uuid4().hex[:8]}",
                "nombre": "Telefono E2E",
                "categoria": "celular",
                "marca": "MarcaE2E",
                "modelo": "ModeloE2E",
                "condicion": "nuevo",
                "precio": 12500,
                "costo": 9000,
                "moneda": "Lps",
                "garantia_meses": 12,
                "stock_inicial": 2,
                "initial_location_id": from_location["id"],
                "imeis": [imei_1, imei_2],
            },
            expected_status=201,
        )

        order = _request_json(
            "POST",
            f"{base_url}/api/orders",
            headers=auth_headers,
            json={
                "sales_profile_slug": sales_profile["slug"],
                "source_location_id": from_location["id"],
                "canal": "whatsapp",
                "customer_name": "Cliente E2E",
                "customer_phone": "+50499887766",
                "metodo_pago": "efectivo",
                "items": [
                    {
                        "product_id": product["id"],
                        "cantidad": 1,
                        "imeis": [imei_1],
                    }
                ],
            },
            expected_status=201,
        )

        _request_json(
            "PUT",
            f"{base_url}/api/orders/{order['id']}/status",
            headers=auth_headers,
            json={"estado": "completada"},
            expected_status=200,
        )

        _request_json(
            "POST",
            f"{base_url}/api/daily-close/config",
            headers=auth_headers,
            json={"new_code": "654321", "confirm_code": "654321"},
            expected_status=200,
        )

        transfer = _request_json(
            "POST",
            f"{base_url}/api/stock-transfers",
            headers=auth_headers,
            json={
                "product_id": product["id"],
                "from_location_id": from_location["id"],
                "to_location_id": to_location["id"],
                "cantidad": 1,
                "imeis": [imei_2],
                "notas": "Transferencia E2E",
            },
            expected_status=201,
        )

        _request_json(
            "POST",
            f"{base_url}/api/stock-transfers/{transfer['id']}/confirm",
            headers=auth_headers,
            json={
                "validation_code": "654321",
                "received_quantity": 1,
                "scanned_imeis": [imei_2],
            },
            expected_status=200,
        )

        pending = _request_json("GET", f"{base_url}/api/daily-close/pending", headers=auth_headers)
        assert any(item["id"] == order["id"] for item in pending)

        _request_json(
            "POST",
            f"{base_url}/api/daily-close/validate",
            headers=auth_headers,
            json={"validation_code": "654321", "order_ids": [order["id"]], "location_id": from_location["id"]},
            expected_status=200,
        )

        returned = _request_json(
            "POST",
            f"{base_url}/api/returns",
            headers=auth_headers,
            json={
                "order_id": order["id"],
                "reason": "Prueba de devolución E2E",
                "items": [
                    {
                        "product_id": product["id"],
                        "quantity": 1,
                        "condition": "nuevo",
                        "action": "store_credit",
                        "imei": imei_1,
                    }
                ],
            },
            expected_status=201,
        )
        assert returned["order_id"] == order["id"]

        imei_history = _request_json(
            "GET",
            f"{base_url}/api/imeis/history?imei={imei_1}",
            headers=auth_headers,
            expected_status=200,
        )
        history_items = _payload_items(imei_history)
        assert len(history_items) >= 1
    finally:
        _stop_backend(process, temp_dir)


def test_rbac_restrictions_with_real_auth():
    process, base_url, temp_dir = _start_backend()
    try:
        admin_headers = _setup_admin_and_login(base_url)

        roles_resp = _request_json("GET", f"{base_url}/api/auth/roles", headers=admin_headers)
        roles = _payload_items(roles_resp)
        vendedor_role = next((role for role in roles if role["name"].lower() == "vendedor"), None)
        assert vendedor_role is not None

        username = f"vendedor{uuid.uuid4().hex[:6]}"
        _request_json(
            "POST",
            f"{base_url}/api/auth/register",
            headers=admin_headers,
            json={
                "username": username,
                "password": "Vend3dor!2026",
                "email": f"{username}@example.com",
                "full_name": "Usuario Vendedor",
                "role_id": vendedor_role["id"],
            },
            expected_status=201,
        )

        token_payload = _request_json(
            "POST",
            f"{base_url}/api/auth/token",
            data={"username": username, "password": "Vend3dor!2026"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            expected_status=200,
        )
        user_headers = {"Authorization": f"Bearer {token_payload['access_token']}"}

        products_response = requests.get(f"{base_url}/api/products", headers=user_headers, timeout=20)
        assert products_response.status_code == 200

        locations_post = requests.post(
            f"{base_url}/api/locations",
            headers=user_headers,
            json={"nombre": "No permitido", "tipo": "tienda", "activo": True},
            timeout=20,
        )
        assert locations_post.status_code == 403

        transfer_post = requests.post(
            f"{base_url}/api/stock-transfers",
            headers=user_headers,
            json={
                "product_id": 1,
                "from_location_id": 1,
                "to_location_id": 1,
                "cantidad": 1,
            },
            timeout=20,
        )
        assert transfer_post.status_code == 403
    finally:
        _stop_backend(process, temp_dir)
