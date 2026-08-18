#!/usr/bin/env python3
"""Privacy-preserving, read-only data fingerprinting for safe upgrades.

Examples:
    python upgrade_audit.py snapshot --sqlite inventory.db --output upgrade-before.json
    python upgrade_audit.py snapshot --database-url "$DATABASE_URL" --output upgrade-after.json
    python upgrade_audit.py compare upgrade-before.json upgrade-after.json --output comparison.json

The database is never modified. Snapshots contain counts, schema metadata,
aggregates and keyed HMAC fingerprints; no row-level customer, IMEI, username,
email, password hash or other field values are exported.
"""

from __future__ import annotations

import argparse
import base64
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
from typing import Any

from sqlalchemy import MetaData, create_engine, func, inspect, select, text
from sqlalchemy.engine import Engine, make_url

FORMAT_VERSION = 2
FINGERPRINT_ALGORITHM = "hmac-sha256-pk-v1"
DEFAULT_KEY_FILE = Path(".upgrade-audit.key")
IGNORED_COMPARE_TABLES = {"schema_migrations", "alembic_version"}

CRITICAL_METRICS: dict[str, dict[str, tuple[str, str]]] = {
    "products": {"active_rows": ("count_true", "activo")},
    "stock": {
        "available_total": ("sum", "cantidad_disponible"),
        "reserved_total": ("sum", "cantidad_reservada"),
        "defective_total": ("sum", "cantidad_defectuosa"),
    },
    "orders": {"amount_total": ("sum", "total")},
    "order_items": {"quantity_total": ("sum", "cantidad")},
    "product_imeis": {
        "sold_rows": ("count_true", "vendido"),
        "unsold_rows": ("count_false", "vendido"),
    },
    "users": {
        "active_rows": ("count_true", "is_active"),
        "superuser_rows": ("count_true", "is_superuser"),
    },
    "stock_transfers": {
        "quantity_total": ("sum", "cantidad"),
        "received_total": ("sum", "received_quantity"),
        "missing_total": ("sum", "missing_quantity"),
    },
}


def _normalized_decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal("1")))
    return format(normalized, "f")


def _json_scalar(value: Any) -> int | str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        return _normalized_decimal_text(value)
    if isinstance(value, float):
        return _normalized_decimal_text(Decimal(str(value)))
    return str(value)


def _canonical_value(value: Any) -> str:
    """Canonicalize common SQLite/PostgreSQL scalar representations."""
    if value is None:
        return "null:"
    if isinstance(value, bool):
        return f"bool:{1 if value else 0}"
    if isinstance(value, int):
        return f"num:{value}"
    if isinstance(value, (Decimal, float)):
        return f"num:{_normalized_decimal_text(Decimal(str(value)))}"
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return "datetime:" + value.isoformat(timespec="microseconds")
    if isinstance(value, date):
        return "date:" + value.isoformat()
    if isinstance(value, time):
        if value.tzinfo is not None:
            value = value.replace(tzinfo=None)
        return "time:" + value.isoformat(timespec="microseconds")
    if isinstance(value, (bytes, bytearray, memoryview)):
        return "bytes:" + base64.b64encode(bytes(value)).decode("ascii")
    if isinstance(value, (dict, list, tuple)):
        return "json:" + json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return "str:" + str(value)


def _metric_values_equal(before_value: Any, after_value: Any) -> bool:
    if before_value == after_value:
        return True
    try:
        return Decimal(str(before_value)) == Decimal(str(after_value))
    except (InvalidOperation, ValueError, TypeError):
        return str(before_value) == str(after_value)


def _source_descriptor(engine: Engine) -> dict[str, str]:
    url = make_url(str(engine.url))
    descriptor = {"dialect": engine.dialect.name}
    if engine.dialect.name == "sqlite":
        database = url.database or ""
        descriptor["database"] = Path(database).name if database else ":memory:"
    else:
        descriptor["database"] = url.database or ""
    return descriptor


def _sqlite_engine(path: Path) -> Engine:
    resolved = path.expanduser().resolve()
    if not resolved.exists() or not resolved.is_file():
        raise FileNotFoundError(f"No existe la base SQLite: {resolved}")
    return create_engine(f"sqlite:///{resolved}")


def _database_engine(database_url: str) -> Engine:
    url = make_url(database_url)
    if url.get_backend_name() not in {"postgresql", "sqlite"}:
        raise ValueError("Solo se admiten SQLite y PostgreSQL para auditoría de actualización.")
    return create_engine(database_url, pool_pre_ping=True)


def _database_health(engine: Engine) -> dict[str, Any]:
    if engine.dialect.name == "sqlite":
        with engine.connect() as conn:
            result = str(conn.execute(text("PRAGMA quick_check")).scalar_one())
        return {"check": "sqlite_quick_check", "ok": result.lower() == "ok", "result": result}

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"check": "connectivity", "ok": True, "result": "ok"}


def _metric_value(conn, table, operation: str, column_name: str) -> int | str | None:
    if column_name not in table.c:
        return None
    column = table.c[column_name]
    if operation == "sum":
        value = conn.execute(select(func.coalesce(func.sum(column), 0))).scalar_one()
    elif operation == "count_true":
        value = conn.execute(select(func.count()).select_from(table).where(column.is_(True))).scalar_one()
    elif operation == "count_false":
        value = conn.execute(select(func.count()).select_from(table).where(column.is_(False))).scalar_one()
    else:
        raise ValueError(f"Operación de métrica desconocida: {operation}")
    return _json_scalar(value)


def _fingerprint_key_id(fingerprint_key: bytes) -> str:
    return hashlib.sha256(fingerprint_key).hexdigest()[:16]


def _table_fingerprints(conn, table, fingerprint_key: bytes) -> dict[str, str]:
    """Fingerprint every column while binding each value to its primary-key row."""
    columns = list(table.columns)
    pk_columns = list(table.primary_key.columns)
    order_columns = pk_columns or columns
    statement = select(*columns)
    if order_columns:
        statement = statement.order_by(*order_columns)

    digests = {
        column.name: hmac.new(
            fingerprint_key,
            f"{table.name}\x1f{column.name}\x1e".encode("utf-8"),
            hashlib.sha256,
        )
        for column in columns
    }

    for row in conn.execute(statement):
        mapping = row._mapping
        if pk_columns:
            locator = "\x1f".join(
                f"{column.name}={_canonical_value(mapping[column.name])}"
                for column in pk_columns
            )
        else:
            # No-PK tables are rare here. Bind each value to a canonicalized full
            # row so column-value permutations cannot preserve the digest.
            locator = "\x1f".join(
                f"{column.name}={_canonical_value(mapping[column.name])}"
                for column in columns
            )

        for column in columns:
            payload = (
                locator
                + "\x1fvalue="
                + _canonical_value(mapping[column.name])
                + "\x1e"
            ).encode("utf-8")
            digests[column.name].update(payload)

    return {name: digest.hexdigest() for name, digest in sorted(digests.items())}


def build_snapshot(engine: Engine, fingerprint_key: bytes) -> dict[str, Any]:
    """Build a read-only aggregate and content snapshot of one database."""
    if len(fingerprint_key) < 32:
        raise ValueError("La clave de fingerprint debe tener al menos 32 bytes.")

    inspector = inspect(engine)
    table_names = sorted(inspector.get_table_names())
    metadata = MetaData()
    metadata.reflect(bind=engine, only=table_names)

    tables: dict[str, dict[str, Any]] = {}
    critical: dict[str, dict[str, Any]] = {}

    with engine.connect() as conn:
        for table_name in table_names:
            table = metadata.tables[table_name]
            row_count = int(conn.execute(select(func.count()).select_from(table)).scalar_one())
            tables[table_name] = {
                "rows": row_count,
                "columns": sorted(column.name for column in table.columns),
                "primary_key": [column.name for column in table.primary_key.columns],
                "fingerprints": _table_fingerprints(conn, table, fingerprint_key),
            }

            definitions = CRITICAL_METRICS.get(table_name)
            if definitions:
                metrics: dict[str, Any] = {"rows": row_count}
                for metric_name, (operation, column_name) in definitions.items():
                    value = _metric_value(conn, table, operation, column_name)
                    if value is not None:
                        metrics[metric_name] = value
                critical[table_name] = metrics

    health = _database_health(engine)
    if not health["ok"]:
        raise RuntimeError(f"La base no superó la verificación de integridad: {health['result']}")

    return {
        "format_version": FORMAT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": _source_descriptor(engine),
        "health": health,
        "fingerprint": {
            "algorithm": FINGERPRINT_ALGORITHM,
            "key_id": _fingerprint_key_id(fingerprint_key),
        },
        "tables": tables,
        "critical": critical,
    }


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Compare source and target while allowing only additive target schema changes."""
    if before.get("format_version") != FORMAT_VERSION or after.get("format_version") != FORMAT_VERSION:
        raise ValueError("Versión de snapshot no soportada.")

    before_fp = before.get("fingerprint", {})
    after_fp = after.get("fingerprint", {})
    if before_fp.get("algorithm") != FINGERPRINT_ALGORITHM or after_fp.get("algorithm") != FINGERPRINT_ALGORITHM:
        raise ValueError("Algoritmo de fingerprint no soportado.")
    if not before_fp.get("key_id") or before_fp.get("key_id") != after_fp.get("key_id"):
        raise ValueError("Los snapshots deben generarse con la misma clave de fingerprint.")

    mismatches: list[str] = []
    warnings: list[str] = []
    before_tables = before.get("tables", {})
    after_tables = after.get("tables", {})

    for table_name, before_info in sorted(before_tables.items()):
        if table_name in IGNORED_COMPARE_TABLES:
            continue
        after_info = after_tables.get(table_name)
        if after_info is None:
            mismatches.append(f"Falta tabla destino: {table_name}")
            continue

        if int(before_info.get("rows", -1)) != int(after_info.get("rows", -2)):
            mismatches.append(
                f"Conteo distinto en {table_name}: antes={before_info.get('rows')} después={after_info.get('rows')}"
            )

        before_columns = set(before_info.get("columns", []))
        after_columns = set(after_info.get("columns", []))
        missing_columns = sorted(before_columns - after_columns)
        for column_name in missing_columns:
            mismatches.append(f"Falta columna destino con datos históricos: {table_name}.{column_name}")

        before_fingerprints = before_info.get("fingerprints", {})
        after_fingerprints = after_info.get("fingerprints", {})
        for column_name in sorted(before_columns & after_columns):
            before_digest = before_fingerprints.get(column_name)
            after_digest = after_fingerprints.get(column_name)
            if not before_digest or not after_digest:
                mismatches.append(f"Falta fingerprint: {table_name}.{column_name}")
            elif not hmac.compare_digest(str(before_digest), str(after_digest)):
                mismatches.append(f"Contenido distinto: {table_name}.{column_name}")

    new_tables = sorted(set(after_tables) - set(before_tables) - IGNORED_COMPARE_TABLES)
    if new_tables:
        warnings.append("Tablas nuevas en destino (permitidas): " + ", ".join(new_tables))

    before_critical = before.get("critical", {})
    after_critical = after.get("critical", {})
    for table_name, before_metrics in sorted(before_critical.items()):
        after_metrics = after_critical.get(table_name)
        if after_metrics is None:
            mismatches.append(f"Faltan métricas críticas destino: {table_name}")
            continue
        for metric_name, before_value in before_metrics.items():
            if metric_name == "rows":
                continue
            if metric_name not in after_metrics:
                mismatches.append(f"Falta métrica destino: {table_name}.{metric_name}")
                continue
            if not _metric_values_equal(before_value, after_metrics[metric_name]):
                mismatches.append(
                    f"Métrica distinta {table_name}.{metric_name}: antes={before_value} después={after_metrics[metric_name]}"
                )

    return {
        "format_version": FORMAT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "compatible": not mismatches,
        "mismatches": mismatches,
        "warnings": warnings,
        "before_source": before.get("source", {}),
        "after_source": after.get("source", {}),
    }


def _write_json(payload: dict[str, Any], output: Path | None) -> None:
    serialized = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    if output is None:
        print(serialized)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(serialized + "\n", encoding="utf-8")
    print(f"Archivo generado: {output}")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_or_create_fingerprint_key(path: Path) -> bytes:
    path = path.expanduser().resolve()
    if path.exists():
        raw = path.read_text(encoding="ascii").strip()
        try:
            key = bytes.fromhex(raw)
        except ValueError as exc:
            raise ValueError(f"Clave de fingerprint inválida: {path}") from exc
        if len(key) < 32:
            raise ValueError(f"Clave de fingerprint demasiado corta: {path}")
        return key

    key = secrets.token_bytes(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(key.hex() + "\n", encoding="ascii")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    print(f"Clave privada de fingerprint creada: {path}")
    print("Conserva este archivo para generar todos los snapshots del mismo corte; no lo subas a Git.")
    return key


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auditoría read-only para actualización segura.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot = subparsers.add_parser("snapshot", help="Crear huella privada/agregada de una base.")
    source = snapshot.add_mutually_exclusive_group(required=True)
    source.add_argument("--sqlite", type=Path, help="Ruta al inventory.db existente.")
    source.add_argument("--database-url", help="URL SQLite/PostgreSQL a auditar.")
    snapshot.add_argument("--output", type=Path, help="JSON de salida; stdout si se omite.")
    snapshot.add_argument(
        "--fingerprint-key-file",
        type=Path,
        default=DEFAULT_KEY_FILE,
        help="Clave HMAC local reutilizable; se crea con permisos privados si no existe.",
    )

    compare = subparsers.add_parser("compare", help="Comparar dos snapshots JSON.")
    compare.add_argument("before", type=Path)
    compare.add_argument("after", type=Path)
    compare.add_argument("--output", type=Path, help="Reporte JSON de comparación.")

    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.command == "snapshot":
        fingerprint_key = _load_or_create_fingerprint_key(args.fingerprint_key_file)
        engine = _sqlite_engine(args.sqlite) if args.sqlite else _database_engine(args.database_url)
        try:
            snapshot = build_snapshot(engine, fingerprint_key)
        finally:
            engine.dispose()
        _write_json(snapshot, args.output)
        return 0

    before = _load_json(args.before)
    after = _load_json(args.after)
    report = compare_snapshots(before, after)
    _write_json(report, args.output)
    return 0 if report["compatible"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
