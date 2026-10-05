"""Versioned data migration for the canonical sales discount policy.

The migration records its id in the shared ``schema_migrations`` ledger, but the
business invariant is intentionally re-checked on every startup. That makes the
startup path self-healing if an old/manual integration later writes a discount
above the automated ceiling or removes the canonical AI context rule.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path
import logging
import sqlite3

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

import app.database as database
from app.utils.ai_sales_policy import (
    MAX_AUTOMATED_DISCOUNT_RATE,
    ensure_canonical_discount_context_rules,
)


logger = logging.getLogger(__name__)

MIGRATION_ID = "20260925_02_ai_discount_policy_cap_and_context"
ORDER_CURRENCY_MIGRATION_ID = "20261002_01_legacy_usd_orders_to_hnl"
CENT = Decimal("0.01")


def _q(value: object) -> Decimal:
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def _rate_from_config(raw: object) -> Decimal:
    try:
        config = raw if isinstance(raw, dict) else json.loads(str(raw or "{}"))
        value = config.get("exchange_rate", config.get("exchangeRate", 25))
        rate = Decimal(str(value))
        if rate.is_finite() and rate > 0:
            return rate.quantize(CENT, rounding=ROUND_HALF_UP)
    except (TypeError, ValueError, json.JSONDecodeError, ArithmeticError, AttributeError):
        pass
    return Decimal("25.00")


def _scale_json_money(raw: object, rate: Decimal, keys: set[str]) -> object:
    if not raw:
        return raw
    try:
        data = json.loads(str(raw))
    except (TypeError, ValueError, json.JSONDecodeError):
        return raw
    def walk(value):
        if isinstance(value, list):
            return [walk(item) for item in value]
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if key in keys and isinstance(item, (int, float, str)):
                    try:
                        scaled = (_q(item) * rate).quantize(CENT, rounding=ROUND_HALF_UP)
                    except (ArithmeticError, ValueError):
                        result[key] = walk(item)
                    else:
                        result[key] = str(scaled) if isinstance(item, str) else float(scaled)
                else:
                    result[key] = walk(item)
            return result
        return value
    return json.dumps(walk(data), ensure_ascii=False)


def _backup_sqlite_if_needed() -> Path | None:
    if database.engine.dialect.name != "sqlite":
        return None

    database_name = database.engine.url.database
    if not database_name or database_name == ":memory:":
        return None

    source = Path(database_name).expanduser().resolve()
    if not source.exists():
        return None

    backup_dir = source.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = backup_dir / f"{source.stem}.pre-pricing-policy-{timestamp}{source.suffix or '.db'}"

    with sqlite3.connect(str(source)) as source_conn, sqlite3.connect(str(destination)) as destination_conn:
        source_conn.backup(destination_conn)

    logger.info("Backup SQLite previo a normalización de descuentos creado en %s", destination)
    return destination


def run_pricing_policy_migration(*, bind: Engine | None = None) -> bool:
    """Normalize AI discount settings and continuously enforce the canonical rule."""

    engine = bind or database.engine
    dialect = engine.dialect.name
    if dialect not in {"postgresql", "sqlite"}:
        logger.info(
            "Normalización de descuentos omitida para dialecto no soportado %s",
            dialect,
        )
        return True

    table_names = set(inspect(engine).get_table_names())
    if "ai_profile_configs" not in table_names:
        return True

    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "id VARCHAR(100) PRIMARY KEY, "
                + (
                    "applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
                    if dialect == "sqlite"
                    else "applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()"
                )
                + ")"
            )
        )
        already_applied = conn.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :migration_id"),
            {"migration_id": MIGRATION_ID},
        ).first()

    # Only the first application needs a workstation backup. The normalization
    # itself remains idempotent and is deliberately re-run to enforce the invariant.
    if not already_applied:
        _backup_sqlite_if_needed()

    # One-time normalization of legacy USD-backed sales. Before this policy,
    # order item price/cost and order totals could persist the raw USD catalog
    # number. Convert only rows whose USD item price still has the legacy shape
    # (at or below the raw USD catalog ceiling); HNL-normalized rows are larger
    # and therefore remain untouched. The ledger makes the operation one-shot.
    if {"orders", "order_items", "products"}.issubset(table_names):
        with engine.begin() as conn:
            currency_applied = conn.execute(
                text("SELECT 1 FROM schema_migrations WHERE id = :migration_id"),
                {"migration_id": ORDER_CURRENCY_MIGRATION_ID},
            ).first()
            if not currency_applied:
                rows = conn.execute(text("""
                    SELECT oi.id AS item_id, oi.order_id, oi.precio_unitario, oi.costo_unitario,
                           p.precio AS catalog_price, p.costo AS catalog_cost, p.moneda,
                           o.sales_profile_id, o.profile_id
                    FROM order_items oi
                    JOIN products p ON p.id = oi.product_id
                    JOIN orders o ON o.id = oi.order_id
                    WHERE UPPER(TRIM(COALESCE(p.moneda, ''))) IN ('USD', 'US$', '$')
                """)).mappings().all()
                candidates: dict[int, list[dict[str, object]]] = {}
                for row in rows:
                    price = _q(row["precio_unitario"])
                    catalog = _q(row["catalog_price"])
                    if price > catalog and price != Decimal("0.00"):
                        continue
                    candidates.setdefault(int(row["order_id"]), []).append(dict(row))

                for order_id, order_rows in candidates.items():
                    item_count = int(conn.execute(
                        text("SELECT COUNT(*) FROM order_items WHERE order_id=:id"),
                        {"id": order_id},
                    ).scalar_one())
                    # Mixed historical orders are ambiguous: their aggregate
                    # payment/financing payload does not record which portion was
                    # raw USD versus already-HNL. Never guess and corrupt ledger
                    # allocations. Only normalize an order when every item has
                    # the unambiguous legacy-USD shape.
                    if len(order_rows) != item_count:
                        continue

                    first = order_rows[0]
                    raw_config = None
                    if first["sales_profile_id"] is not None and "sales_profiles" in table_names:
                        raw_config = conn.execute(
                            text("SELECT configuracion FROM sales_profiles WHERE id=:id"),
                            {"id": first["sales_profile_id"]},
                        ).scalar()
                    elif first["profile_id"] is not None and "profiles" in table_names:
                        raw_config = conn.execute(
                            text("SELECT settings FROM profiles WHERE id=:id"),
                            {"id": first["profile_id"]},
                        ).scalar()
                    rate = _rate_from_config(raw_config)

                    for row in order_rows:
                        price = _q(row["precio_unitario"])
                        new_price = (price * rate).quantize(CENT, rounding=ROUND_HALF_UP)
                        cost = row["costo_unitario"]
                        if cost is None:
                            new_cost = None
                        else:
                            cost_value = _q(cost)
                            catalog_cost = _q(row["catalog_cost"])
                            # The transaction guard may already have normalized
                            # historical cost to HNL while the legacy sale price
                            # still has its raw USD shape. Only scale costs that
                            # are still at/below the raw USD catalog cost.
                            new_cost = (
                                (cost_value * rate).quantize(CENT, rounding=ROUND_HALF_UP)
                                if cost_value <= catalog_cost
                                else cost_value
                            )
                        conn.execute(
                            text("UPDATE order_items SET precio_unitario=:price, costo_unitario=:cost WHERE id=:id"),
                            {"price": new_price, "cost": new_cost, "id": row["item_id"]},
                        )

                    order_row = conn.execute(
                        text("SELECT total, payment_breakdown, financing_details FROM orders WHERE id=:id"),
                        {"id": order_id},
                    ).mappings().one()
                    money_keys = {"amount", "down_payment", "prima", "financed_amount", "surcharge", "monthly_payment", "total_with_surcharge"}
                    conn.execute(
                        text("UPDATE orders SET total=:total, payment_breakdown=:payments, financing_details=:financing WHERE id=:id"),
                        {
                            "total": (_q(order_row["total"]) * rate).quantize(CENT, rounding=ROUND_HALF_UP),
                            "payments": _scale_json_money(order_row["payment_breakdown"], rate, money_keys),
                            "financing": _scale_json_money(order_row["financing_details"], rate, money_keys),
                            "id": order_id,
                        },
                    )
                ledger_sql = (
                    "INSERT OR IGNORE INTO schema_migrations (id) VALUES (:migration_id)"
                    if dialect == "sqlite"
                    else "INSERT INTO schema_migrations (id) VALUES (:migration_id) ON CONFLICT (id) DO NOTHING"
                )
                conn.execute(text(ledger_sql), {"migration_id": ORDER_CURRENCY_MIGRATION_ID})

    with engine.begin() as conn:
        capped = conn.execute(
            text(
                "UPDATE ai_profile_configs "
                "SET max_discount_rate = :max_discount "
                "WHERE max_discount_rate IS NOT NULL "
                "AND max_discount_rate > :max_discount"
            ),
            {"max_discount": MAX_AUTOMATED_DISCOUNT_RATE},
        )
        conn.execute(
            text(
                "UPDATE ai_profile_configs SET max_discount_rate = 0 "
                "WHERE max_discount_rate IS NOT NULL AND max_discount_rate < 0"
            )
        )

        rows = conn.execute(
            text("SELECT id, context_rules FROM ai_profile_configs ORDER BY id")
        ).mappings().all()
        for row in rows:
            normalized_rules = ensure_canonical_discount_context_rules(row["context_rules"])
            if normalized_rules != str(row["context_rules"] or ""):
                conn.execute(
                    text(
                        "UPDATE ai_profile_configs SET context_rules = :context_rules "
                        "WHERE id = :config_id"
                    ),
                    {
                        "context_rules": normalized_rules,
                        "config_id": int(row["id"]),
                    },
                )

        if dialect == "sqlite":
            ledger_sql = (
                "INSERT OR IGNORE INTO schema_migrations (id) VALUES (:migration_id)"
            )
        else:
            ledger_sql = (
                "INSERT INTO schema_migrations (id) VALUES (:migration_id) "
                "ON CONFLICT (id) DO NOTHING"
            )
        conn.execute(text(ledger_sql), {"migration_id": MIGRATION_ID})

    logger.info(
        "Política de descuentos IA verificada; %s configuraciones fueron limitadas a %.2f%% en esta ejecución",
        max(int(capped.rowcount or 0), 0),
        MAX_AUTOMATED_DISCOUNT_RATE * 100,
    )
    return True


__all__ = ["MIGRATION_ID", "ORDER_CURRENCY_MIGRATION_ID", "run_pricing_policy_migration"]
