from pathlib import Path

migration_path = Path("backend/app/utils/auto_migrations.py")
text = migration_path.read_text()
old = '''def _supplier_unique_index_exists() -> bool:\n    if "suppliers" not in inspect(database.engine).get_table_names():\n        return True\n\n    with database.engine.connect() as conn:\n        if _dialect_name() == "sqlite":\n            rows = conn.execute(text("PRAGMA index_list('suppliers')")).fetchall()\n            return any(\n                str(row[1]) == "ix_suppliers_nombre_key_hash" and bool(row[2])\n                for row in rows\n            )\n\n        indexdef = conn.execute(\n            text(\n                "SELECT indexdef FROM pg_indexes "\n                "WHERE schemaname = current_schema() "\n                "AND tablename = 'suppliers' "\n                "AND indexname = 'ix_suppliers_nombre_key_hash'"\n            )\n        ).scalar_one_or_none()\n        return bool(indexdef and "CREATE UNIQUE INDEX" in str(indexdef).upper())\n'''
new = '''def _supplier_unique_index_exists() -> bool:\n    inspector = inspect(database.engine)\n    if "suppliers" not in inspector.get_table_names():\n        return True\n\n    return any(\n        str(index.get("name") or "") == "ix_suppliers_nombre_key_hash"\n        and bool(index.get("unique"))\n        and list(index.get("column_names") or []) == ["nombre_key_hash"]\n        for index in inspector.get_indexes("suppliers")\n    )\n'''
if text.count(old) != 1:
    raise SystemExit(f"expected exactly one supplier index helper, found {text.count(old)}")
migration_path.write_text(text.replace(old, new, 1))

test_path = Path("backend/tests/test_supplier_name_concurrency_integrity.py")
tests = test_path.read_text()
marker = '''    finally:\n        engine.dispose()\n'''
if not tests.endswith(marker):
    raise SystemExit("supplier test file no longer ends at the expected migration test")
addition = r'''


def test_supplier_name_rejects_invisible_unicode_controls() -> None:
    with pytest.raises(ValueError, match="Unicode no permitidos"):
        supplier_name_key("Proveedor\u200bCentral")


def test_supplier_name_migration_fails_closed_on_invisible_unicode(
    tmp_path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "supplier-invisible.db"
    engine = create_engine(f"sqlite:///{db_path}")
    _create_legacy_sqlite_schema(engine, [(1, "Proveedor\u200bCentral")])
    monkeypatch.setattr(database, "engine", engine)

    try:
        with pytest.raises(RuntimeError, match="nombre inválido"):
            run_auto_migrations()

        with engine.connect() as conn:
            applied = {
                str(row[0])
                for row in conn.execute(text("SELECT id FROM schema_migrations"))
            }
        assert "20260825_01_supplier_name_uniqueness" not in applied
    finally:
        engine.dispose()


def test_supplier_schema_rejects_misbound_unique_index(
    tmp_path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "supplier-wrong-index.db"
    engine = create_engine(f"sqlite:///{db_path}")
    _create_legacy_sqlite_schema(engine, [(1, "Proveedor Central")])
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE UNIQUE INDEX ix_suppliers_nombre_key_hash "
                "ON suppliers (nombre)"
            )
        )
    monkeypatch.setattr(database, "engine", engine)

    try:
        with pytest.raises(
            RuntimeError,
            match="falta índice único ix_suppliers_nombre_key_hash",
        ):
            run_auto_migrations()

        with engine.connect() as conn:
            columns = [
                str(row[2])
                for row in conn.execute(
                    text("PRAGMA index_info('ix_suppliers_nombre_key_hash')")
                ).fetchall()
            ]
        assert columns == ["nombre"]
    finally:
        engine.dispose()
'''
test_path.write_text(tests + addition)
