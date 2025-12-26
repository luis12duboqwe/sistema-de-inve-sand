import json
import os
import threading
import time
import uuid
from decimal import Decimal
from pathlib import Path
from urllib import error, request
import unittest

import sys

import uvicorn


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"

# Forzar base de datos de pruebas a un archivo temporal accesible
TEST_DB_PATH = Path("/tmp/test_api_usage.db")
os.environ["DATABASE_URL"] = f"sqlite:////{TEST_DB_PATH}"

# Garantiza un estado limpio de base de datos y que las rutas relativas de SQLite
# apunten al directorio backend para las pruebas.
for db_path in (PROJECT_ROOT / "inventory.db", BACKEND_DIR / "inventory.db", BACKEND_DIR / "test_api_usage.db", TEST_DB_PATH):
    if db_path.exists():
        db_path.unlink()

# Asegura que el paquete ``app`` sea importable sin depender del cwd
# que usa unittest al descubrir los tests desde la raíz del proyecto.
os.chdir(BACKEND_DIR)
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Reconstruir engine/SessionLocal con el DATABASE_URL de pruebas aunque app.main
# se haya cargado antes en otros tests.
import importlib
import app.database as _db  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

_db.engine = create_engine(
    os.environ["DATABASE_URL"], connect_args={"check_same_thread": False}
)
_db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_db.engine)

from app.main import app  # noqa: E402  importado después de fijar el cwd y reconfigurar DB

# En algunos entornos, el lifespan de Uvicorn puede no ejecutar init_db
# antes de que este test llame a /api/init-data. Creamos tablas explícitamente
# para evitar 500 por "no such table" en SQLite.
from app import models as _models  # noqa: E402,F401
from app.database import init_db  # noqa: E402

# Este archivo levanta Uvicorn real y usa la DB en archivo.
# Aun así, varias rutas (ej: POST /api/products) requieren permisos.
# Para evitar manejar tokens aquí, forzamos un usuario superusuario.
from app.auth import get_current_active_user, get_current_superuser, get_current_user  # noqa: E402


class _FakeUser:
    def __init__(self):
        self.id = 1
        self.username = "test"
        self.is_active = True
        self.is_superuser = True
        self.role = None


def _fake_user():
    return _FakeUser()


app.dependency_overrides[get_current_user] = _fake_user
app.dependency_overrides[get_current_active_user] = _fake_user
app.dependency_overrides[get_current_superuser] = _fake_user

# Crea tablas explícitamente para evitar 500 por "no such table"
init_db()


def _http_json(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    data_bytes = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    req = request.Request(url, data=data_bytes, method=method, headers=headers)
    try:
        with request.urlopen(req) as resp:
            return resp.getcode(), json.loads(resp.read().decode())
    except error.HTTPError as http_err:
        body = http_err.read().decode()
        try:
            return http_err.code, json.loads(body)
        except Exception:
            raise


class ApiUsageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = 8001
        config = uvicorn.Config(app, host="127.0.0.1", port=cls.port, log_level="warning")
        cls.server = uvicorn.Server(config)
        cls.thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.thread.start()

        base_url = f"http://127.0.0.1:{cls.port}"
        for _ in range(50):
            try:
                status, _ = _http_json("GET", f"{base_url}/api/health")
                if status == 200:
                    break
            except Exception:
                time.sleep(0.1)
        else:
            raise RuntimeError("El servidor no inició correctamente para las pruebas")

        status, init_payload = _http_json("POST", f"{base_url}/api/init-data")
        assert status == 200, init_payload

        status, locations_response = _http_json("GET", f"{base_url}/api/locations")
        assert status == 200, locations_response
        locations = locations_response.get("items", locations_response) if isinstance(locations_response, dict) else locations_response
        assert locations, "Se esperaba al menos una ubicación para las pruebas"
        cls.location_id = locations[0]["id"]

        status, profiles_response = _http_json("GET", f"{base_url}/api/profiles")
        assert status == 200 and profiles_response, "Se esperaba al menos un perfil de prueba"
        # Response is now paginated, so access the 'items' field
        profiles = profiles_response.get("items", [])
        assert len(profiles) > 0, "Se esperaba al menos un perfil en items"
        cls.profile = profiles[0]
        cls.base_url = base_url

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(timeout=5)

    def _create_product(self, *, price: Decimal = Decimal("99.99"), stock: int = 5, categoria: str = "accesorio"):
        sku = f"TEST-{uuid.uuid4().hex[:8]}"
        payload = {
            "profile_id": self.profile["id"],
            "sku": sku,
            "nombre": f"Producto {sku}",
            "categoria": categoria,
            "marca": "MarcaTest",
            "modelo": "ModeloX",
            "capacidad": "128GB" if categoria == "celular" else None,
            "condicion": "nuevo",
            "precio": float(price),
            "moneda": "Lps",
            "garantia_meses": 0,
            "stock_inicial": stock,
        }

        # V2.x: celulares son serializados y requieren IMEIs si stock > 0
        if categoria == "celular" and stock > 0:
            payload["imeis"] = [f"{uuid.uuid4().int % 10**15:015d}" for _ in range(stock)]

        status, data = _http_json("POST", f"{self.base_url}/api/products", payload)
        self.assertEqual(status, 201, data)
        return data

    def _create_order(self, product_id: int, *, quantity: int = 1, es_regalo_promocion: bool = False):
        payload = {
            "profile_slug": self.profile["slug"],
            "source_location_id": type(self).location_id,
            "canal": "whatsapp",
            "customer_name": "Cliente Test",
            "customer_phone": "+50411111111",
            "metodo_pago": "efectivo",
            "items": [
                {
                    "product_id": product_id,
                    "cantidad": quantity,
                    "es_regalo_promocion": es_regalo_promocion,
                }
            ],
        }

        status, data = _http_json("POST", f"{self.base_url}/api/orders", payload)
        self.assertEqual(status, 201, data)
        return data

    def test_health_and_init_are_available(self):
        status, data = _http_json("GET", f"{self.base_url}/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(data.get("status"), "healthy")

        status, data = _http_json("POST", f"{self.base_url}/api/init-data")
        self.assertEqual(status, 200)
        self.assertIn("message", data)

    def test_list_products_returns_only_active_with_stock(self):
        status, response = _http_json("GET", f"{self.base_url}/api/products")
        self.assertEqual(status, 200)
        # Response is now paginated
        products = response.get("items", [])
        self.assertGreaterEqual(len(products), 1)
        for product in products:
            self.assertGreater(product["stock_disponible"], 0)

    def test_create_product_sets_default_warranty_and_stock(self):
        payload = {
            "profile_id": self.profile["id"],
            "sku": f"AUTO-WARRANTY-{uuid.uuid4().hex[:6]}",
            "nombre": "Teléfono con garantía automática",
            "categoria": "celular",
            "marca": "MarcaAuto",
            "modelo": "ModeloAuto",
            "capacidad": "256GB",
            "condicion": "nuevo",
            "precio": 15000,
            "moneda": "Lps",
            "garantia_meses": 0,
            "stock_inicial": 7,
            "imeis": [f"{uuid.uuid4().int % 10**15:015d}" for _ in range(7)],
        }

        status, data = _http_json("POST", f"{self.base_url}/api/products", payload)
        self.assertEqual(status, 201, data)
        self.assertEqual(data["garantia_meses"], 2)
        self.assertEqual(data["stock_disponible"], 7)

    def test_bulk_create_products_respects_stock_and_returns_items(self):
        bulk_payload = {
            "products": [
                {
                    "profile_id": self.profile["id"],
                    "sku": f"BULK-{uuid.uuid4().hex[:6]}",
                    "nombre": "Accesorio Bulk 1",
                    "categoria": "accesorio",
                    "marca": "MarcaBulk",
                    "modelo": "ModeloA",
                    "capacidad": None,
                    "condicion": "nuevo",
                    "precio": 250,
                    "moneda": "Lps",
                    "garantia_meses": 0,
                    "stock_inicial": 4,
                },
                {
                    "profile_id": self.profile["id"],
                    "sku": f"BULK-{uuid.uuid4().hex[:6]}",
                    "nombre": "Accesorio Bulk 2",
                    "categoria": "accesorio",
                    "marca": "MarcaBulk",
                    "modelo": "ModeloB",
                    "capacidad": None,
                    "condicion": "nuevo",
                    "precio": 275,
                    "moneda": "Lps",
                    "garantia_meses": 0,
                    "stock_inicial": 6,
                },
            ]
        }

        status, data = _http_json("POST", f"{self.base_url}/api/products/bulk", bulk_payload)
        self.assertEqual(status, 201, data)
        self.assertEqual(len(data), 2)
        self.assertCountEqual([item["stock_disponible"] for item in data], [4, 6])

    def test_create_order_deducts_stock_and_calculates_total(self):
        product = self._create_product(price=Decimal("123.45"), stock=2)

        order = self._create_order(product["id"], quantity=1)
        self.assertEqual(Decimal(str(order["total"])), Decimal("123.45"))

        status, refreshed = _http_json("GET", f"{self.base_url}/api/products/{product['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(refreshed["stock_disponible"], 1)

    def test_update_order_replenishes_previous_items_before_applying_new(self):
        product = self._create_product(price=Decimal("100.00"), stock=3)
        order = self._create_order(product["id"], quantity=1)

        update_payload = {
            "items": [
                {
                    "product_id": product["id"],
                    "cantidad": 2,
                    "es_regalo_promocion": False,
                }
            ]
        }

        status, updated = _http_json("PUT", f"{self.base_url}/api/orders/{order['id']}", update_payload)
        self.assertEqual(status, 200, updated)
        self.assertEqual(Decimal(str(updated["total"])), Decimal("200.00"))

        status, refreshed = _http_json("GET", f"{self.base_url}/api/products/{product['id']}")
        self.assertEqual(status, 200)
        # Stock inicial 3, -1 por la orden original, +1 al reponer, -2 en la nueva orden => 1
        self.assertEqual(refreshed["stock_disponible"], 1)

    def test_update_order_status(self):
        product = self._create_product(price=Decimal("50.00"), stock=1)
        order = self._create_order(product["id"], quantity=1)

        status, updated = _http_json(
            "PUT",
            f"{self.base_url}/api/orders/{order['id']}/status",
            {"estado": "completada"},
        )

        self.assertEqual(status, 200, updated)
        self.assertEqual(updated["estado"], "completada")


if __name__ == "__main__":
    unittest.main()
