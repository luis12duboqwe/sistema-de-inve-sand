from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.models import IMEIHistory, Location, Order, OrderItem, Profile, Product, ProductIMEI, SalesProfile, Stock, StockHistory


DEMO_LOCATIONS: list[dict[str, Any]] = [
    {"nombre": "Tienda Centro", "tipo": "tienda", "direccion": "Av. Principal #123, Centro", "telefono": "+504 2234-5678"},
    {"nombre": "Tienda Norte", "tipo": "tienda", "direccion": "Col. Las Minitas, Salida Norte", "telefono": "+504 2245-6789"},
    {"nombre": "Bodega Central", "tipo": "bodega", "direccion": "Zona Industrial, Bodega #5", "telefono": "+504 2256-7890"},
]

DEMO_SALES_PROFILES: list[dict[str, Any]] = [
    {
        "name": "Bot WhatsApp Principal",
        "slug": "bot-whatsapp-1",
        "tipo": "bot_ia",
        "canales": ["whatsapp"],
        "configuracion": {
            "numero": "+504 9999-8888",
            "horario": "24/7",
            "auto_respuesta": True,
            "negotiation_rules": {
                "max_discount_percent": 0.05,
                "steps": [0.02, 0.04, 0.05],
                "round_to": 100,
            },
        },
    },
    {
        "name": "Vendedor Tienda Centro",
        "slug": "vendedor-centro",
        "tipo": "vendedor_humano",
        "canales": ["whatsapp", "facebook", "instagram"],
        "configuracion": {"turno": "8AM-6PM", "comision": 5},
    },
    {
        "name": "Automatizador Marketplace",
        "slug": "sistema-marketplace",
        "tipo": "sistema_automatico",
        "canales": ["facebook", "instagram"],
        "configuracion": {"canal_principal": "facebook", "respuesta_rapida": True},
    },
]

DEMO_PROFILE: dict[str, Any] = {
    "name": "Softmobile",
    "slug": "softmobile",
}

DEMO_PRODUCTS: list[dict[str, Any]] = [
    {
        "sku": "SM-S24-256-NEGRO-NUEVO",
        "nombre": "Samsung Galaxy S24 256GB Negro",
        "categoria": "celular",
        "marca": "Samsung",
        "modelo": "Galaxy S24",
        "capacidad": "256GB",
        "condicion": "nuevo",
        "precio": Decimal("18500.00"),
        "costo": Decimal("15100.00"),
        "garantia_meses": 12,
        "is_serialized": True,
        "stock_by_location": [3, 2, 5],
        "imeis": [
            {"imei": "356789012345670", "location_index": 0},
            {"imei": "356789012345688", "location_index": 0},
            {"imei": "356789012345696", "location_index": 0},
            {"imei": "356789012345704", "location_index": 1},
            {"imei": "356789012345712", "location_index": 1},
            {"imei": "356789012345720", "location_index": 2},
            {"imei": "356789012345738", "location_index": 2},
            {"imei": "356789012345746", "location_index": 2},
            {"imei": "356789012345753", "location_index": 2},
            {"imei": "356789012345761", "location_index": 2},
        ],
    },
    {
        "sku": "IP-15PRO-512-TITANIO-NUEVO",
        "nombre": "iPhone 15 Pro 512GB Titanio",
        "categoria": "celular",
        "marca": "Apple",
        "modelo": "iPhone 15 Pro",
        "capacidad": "512GB",
        "condicion": "nuevo",
        "precio": Decimal("35000.00"),
        "costo": Decimal("28750.00"),
        "garantia_meses": 12,
        "is_serialized": True,
        "stock_by_location": [1, 1, 3],
        "imeis": [
            {"imei": "356789012345779", "location_index": 0},
            {"imei": "356789012345787", "location_index": 1},
            {"imei": "356789012345795", "location_index": 2},
            {"imei": "356789012345803", "location_index": 2},
            {"imei": "356789012345811", "location_index": 2},
        ],
    },
    {
        "sku": "ACC-FUNDA-SILICONA-UNIVERSAL",
        "nombre": "Funda de Silicona Universal",
        "categoria": "accesorio",
        "marca": "Genérico",
        "modelo": "Universal",
        "capacidad": None,
        "condicion": "nuevo",
        "precio": Decimal("150.00"),
        "costo": Decimal("55.00"),
        "garantia_meses": 0,
        "is_serialized": False,
        "stock_by_location": [20, 15, 50],
    },
    {
        "sku": "ACC-CARGADOR-RAPIDO-20W",
        "nombre": "Cargador Rápido 20W USB-C",
        "categoria": "accesorio",
        "marca": "Anker",
        "modelo": "PowerPort 20W",
        "capacidad": "20W",
        "condicion": "nuevo",
        "precio": Decimal("350.00"),
        "costo": Decimal("180.00"),
        "garantia_meses": 6,
        "is_serialized": False,
        "stock_by_location": [10, 8, 25],
    },
    {
        "sku": "ACC-GLASS-UNIVERSAL-10PK",
        "nombre": "Protector de Pantalla Universal x10",
        "categoria": "accesorio",
        "marca": "MobileCare",
        "modelo": "10 Pack",
        "capacidad": None,
        "condicion": "nuevo",
        "precio": Decimal("420.00"),
        "costo": Decimal("210.00"),
        "garantia_meses": 0,
        "is_serialized": False,
        "stock_by_location": [12, 12, 30],
    },
    {
        "sku": "ACC-HF-BLUETOOTH-LITE",
        "nombre": "Audífonos Bluetooth Lite",
        "categoria": "accesorio",
        "marca": "SoundPro",
        "modelo": "Lite",
        "capacidad": None,
        "condicion": "nuevo",
        "precio": Decimal("790.00"),
        "costo": Decimal("390.00"),
        "garantia_meses": 6,
        "is_serialized": False,
        "stock_by_location": [6, 6, 18],
    },
]

DEMO_ORDERS: list[dict[str, Any]] = [
    {
        "notes": "DEMO_SEED: whatsapp accesorios",
        "sales_profile_slug": "bot-whatsapp-1",
        "source_location_name": "Tienda Centro",
        "customer_name": "María López",
        "customer_phone": "+50488887777",
        "canal": "whatsapp",
        "metodo_pago": "efectivo",
        "estado": "completada",
        "items": [
            {"sku": "ACC-FUNDA-SILICONA-UNIVERSAL", "cantidad": 2, "precio_unitario": Decimal("150.00")},
            {"sku": "ACC-CARGADOR-RAPIDO-20W", "cantidad": 1, "precio_unitario": Decimal("350.00")},
        ],
    },
    {
        "notes": "DEMO_SEED: facebook venta mixta",
        "sales_profile_slug": "vendedor-centro",
        "source_location_name": "Tienda Norte",
        "customer_name": "Carlos Hernández",
        "customer_phone": "+50499990000",
        "canal": "facebook",
        "metodo_pago": "transferencia",
        "estado": "completada",
        "items": [
            {"sku": "ACC-GLASS-UNIVERSAL-10PK", "cantidad": 1, "precio_unitario": Decimal("420.00")},
            {"sku": "ACC-HF-BLUETOOTH-LITE", "cantidad": 1, "precio_unitario": Decimal("790.00")},
        ],
    },
]


def _json_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _get_or_create_location(db: Session, payload: dict[str, Any]) -> tuple[Location, bool]:
    location = db.query(Location).filter(Location.nombre == payload["nombre"]).first()
    created = location is None
    if location is None:
        location = Location(**payload, activo=True)
        db.add(location)
        db.flush()
        return location, created

    location.tipo = payload["tipo"]
    location.direccion = payload.get("direccion")
    location.telefono = payload.get("telefono")
    location.activo = True
    db.flush()
    return location, created


def _get_or_create_sales_profile(db: Session, payload: dict[str, Any]) -> tuple[SalesProfile, bool]:
    sales_profile = db.query(SalesProfile).filter(SalesProfile.slug == payload["slug"]).first()
    created = sales_profile is None
    if sales_profile is None:
        sales_profile = SalesProfile(
            name=payload["name"],
            slug=payload["slug"],
            tipo=payload["tipo"],
            canales=_json_text(payload.get("canales")),
            configuracion=_json_text(payload.get("configuracion")),
            active=True,
        )
        db.add(sales_profile)
        db.flush()
        return sales_profile, created

    sales_profile.name = payload["name"]
    sales_profile.tipo = payload["tipo"]
    sales_profile.canales = _json_text(payload.get("canales"))
    sales_profile.configuracion = _json_text(payload.get("configuracion"))
    sales_profile.active = True
    db.flush()
    return sales_profile, created


def _get_or_create_profile(db: Session, payload: dict[str, Any]) -> tuple[Profile, bool]:
    profile = db.query(Profile).filter(Profile.slug == payload["slug"]).first()
    created = profile is None
    if profile is None:
        profile = Profile(name=payload["name"], slug=payload["slug"], active=True)
        db.add(profile)
        db.flush()
        return profile, created

    profile.name = payload["name"]
    profile.active = True
    db.flush()
    return profile, created


def _get_or_create_product(db: Session, payload: dict[str, Any], profile_id: int) -> tuple[Product, bool]:
    product = db.query(Product).filter(Product.sku == payload["sku"]).first()
    created = product is None
    product_fields = {
        "profile_id": profile_id,
        "sku": payload["sku"],
        "nombre": payload["nombre"],
        "categoria": payload["categoria"],
        "marca": payload["marca"],
        "modelo": payload["modelo"],
        "color": payload.get("color"),
        "capacidad": payload.get("capacidad"),
        "condicion": payload["condicion"],
        "precio": payload["precio"],
        "costo": payload.get("costo", Decimal("0.00")),
        "moneda": payload.get("moneda", "HNL"),
        "garantia_meses": payload.get("garantia_meses", 0),
        "garantia_condiciones": payload.get("garantia_condiciones"),
        "activo": True,
        "is_serialized": payload.get("is_serialized", False),
    }

    if product is None:
        product = Product(**product_fields)
        db.add(product)
        db.flush()
        return product, created

    for field, value in product_fields.items():
        setattr(product, field, value)
    db.flush()
    return product, created


def _sync_stock(
    db: Session,
    product: Product,
    locations: list[Location],
    stock_by_location: list[int],
    created_by: str,
) -> tuple[int, int]:
    created_count = 0
    updated_count = 0

    for index, quantity in enumerate(stock_by_location):
        location = locations[index]
        stock = db.query(Stock).filter(Stock.product_id == product.id, Stock.location_id == location.id).first()
        if stock is None:
            stock = Stock(product_id=product.id, location_id=location.id, cantidad_disponible=quantity)
            db.add(stock)
            db.flush()
            created_count += 1
            db.add(
                StockHistory(
                    product_id=product.id,
                    location_id=location.id,
                    tipo_cambio="ajuste",
                    cantidad=quantity,
                    stock_anterior=0,
                    stock_nuevo=quantity,
                    referencia_id=product.id,
                    referencia_tipo="demo_seed",
                    notas=f"Stock inicial demo para {product.nombre} ({location.nombre})",
                    usuario=created_by,
                )
            )
            continue

        if stock.cantidad_disponible != quantity:
            stock.cantidad_disponible = quantity
            updated_count += 1

    return created_count, updated_count


def _sync_imeis(
    db: Session,
    product: Product,
    created_by: str,
    imeis: Iterable[dict[str, Any]],
    locations: list[Location],
) -> int:
    created_count = 0
    for imei_data in imeis:
        imei_value = str(imei_data["imei"]).strip()
        location_index = int(imei_data["location_index"])
        location = locations[location_index]

        imei_record = db.query(ProductIMEI).filter(ProductIMEI.imei == imei_value).first()
        if imei_record is None:
            imei_record = ProductIMEI(
                product_id=product.id,
                location_id=location.id,
                supplier_id=product.supplier_id,
                imei=imei_value,
                vendido=False,
                acquisition_type="initial_stock",
                received_notes=f"Stock inicial demo para {product.nombre} ({location.nombre})",
                received_by=created_by,
            )
            db.add(imei_record)
            created_count += 1
        else:
            imei_record.product_id = product.id
            imei_record.location_id = location.id
            imei_record.vendido = False
            imei_record.acquisition_type = "initial_stock"
            imei_record.received_notes = f"Stock inicial demo para {product.nombre} ({location.nombre})"
            imei_record.received_by = created_by

        history_exists = db.query(IMEIHistory).filter(
            IMEIHistory.imei == imei_value,
            IMEIHistory.product_id == product.id,
            IMEIHistory.reference_type == "demo_seed",
            IMEIHistory.reference_id == product.id,
        ).first()
        if history_exists is None:
            db.add(
                IMEIHistory(
                    imei=imei_value,
                    product_id=product.id,
                    location_id=location.id,
                    supplier_id=product.supplier_id,
                    event_type="purchase",
                    reference_id=product.id,
                    reference_type="demo_seed",
                    notes=f"Stock inicial demo para {product.nombre} ({location.nombre})",
                    created_by=created_by,
                )
            )

    return created_count


def _seed_orders(
    db: Session,
    profile: Profile,
    locations: list[Location],
    products_by_sku: dict[str, Product],
    created_by: str,
) -> int:
    created_count = 0

    for order_data in DEMO_ORDERS:
        existing = db.query(Order).filter(Order.notes == order_data["notes"]).first()
        if existing is not None:
            continue

        sales_profile = db.query(SalesProfile).filter(SalesProfile.slug == order_data["sales_profile_slug"]).first()
        source_location = next((location for location in locations if location.nombre == order_data["source_location_name"]), None)
        if sales_profile is None or source_location is None:
            continue

        total = Decimal("0.00")
        order_items_payload: list[dict[str, Any]] = []
        for item in order_data["items"]:
            product = products_by_sku[item["sku"]]
            precio_unitario = Decimal(item["precio_unitario"])
            cantidad = int(item["cantidad"])
            total += precio_unitario * cantidad
            order_items_payload.append(
                {
                    "product_id": product.id,
                    "cantidad": cantidad,
                    "precio_unitario": precio_unitario,
                    "costo_unitario": product.costo,
                }
            )

        order = Order(
            sales_profile_id=sales_profile.id,
            profile_id=profile.id,
            source_location_id=source_location.id,
            customer_name=order_data["customer_name"],
            customer_phone=order_data["customer_phone"],
            canal=order_data["canal"],
            metodo_pago=order_data["metodo_pago"],
            total=total,
            estado=order_data["estado"],
            notes=order_data["notes"],
            validated_by=created_by,
        )
        db.add(order)
        db.flush()

        for item_payload in order_items_payload:
            db.add(OrderItem(order_id=order.id, **item_payload))

        created_count += 1

    return created_count


def seed_demo_data(db: Session, *, created_by: str = "demo-seed") -> dict[str, int]:
    locations: list[Location] = []
    locations_created = 0
    for location_payload in DEMO_LOCATIONS:
        location, created = _get_or_create_location(db, location_payload)
        locations.append(location)
        locations_created += int(created)

    sales_profiles_created = 0
    for sales_profile_payload in DEMO_SALES_PROFILES:
        _, created = _get_or_create_sales_profile(db, sales_profile_payload)
        sales_profiles_created += int(created)

    profile, profile_created = _get_or_create_profile(db, DEMO_PROFILE)

    products_created = 0
    stock_created = 0
    stock_updated = 0
    imeis_created = 0

    products_by_sku: dict[str, Product] = {}
    for product_payload in DEMO_PRODUCTS:
        product, created = _get_or_create_product(db, product_payload, profile.id)
        products_by_sku[product_payload["sku"]] = product
        products_created += int(created)
        created_count, updated_count = _sync_stock(db, product, locations, product_payload["stock_by_location"], created_by)
        stock_created += created_count
        stock_updated += updated_count
        imeis_created += _sync_imeis(db, product, created_by, product_payload.get("imeis", []), locations)

    orders_created = _seed_orders(db, profile, locations, products_by_sku, created_by)

    db.commit()

    return {
        "locations_created": locations_created,
        "sales_profiles_created": sales_profiles_created,
        "profiles_created": int(profile_created),
        "products_created": products_created,
        "stock_rows_created": stock_created,
        "stock_rows_updated": stock_updated,
        "imeis_created": imeis_created,
        "orders_created": orders_created,
    }
