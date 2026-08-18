from pathlib import Path

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, inspect, text

from migrate_sqlite_to_postgres import (
    _backup_sqlite_source,
    _copy_table_rows,
    _required_target_columns_missing_from_source,
    _target_tables_with_rows,
)


def test_copy_uses_real_legacy_columns_and_allows_new_nullable_fields(tmp_path: Path):
    source = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    target = create_engine(f"sqlite:///{tmp_path / 'target.db'}")

    source_meta = MetaData()
    Table(
        'products',
        source_meta,
        Column('id', Integer, primary_key=True),
        Column('nombre', String(100), nullable=False),
    )
    source_meta.create_all(source)
    with source.begin() as conn:
        conn.execute(
            text("INSERT INTO products (id, nombre) VALUES (5, 'Equipo legado')")
        )

    target_meta = MetaData()
    target_table = Table(
        'products',
        target_meta,
        Column('id', Integer, primary_key=True),
        Column('nombre', String(100), nullable=False),
        Column('descripcion_nueva', String(255), nullable=True),
    )
    target_meta.create_all(target)

    with target.begin() as conn:
        copied = _copy_table_rows(source, conn, target_table)

    assert copied == 1
    with target.connect() as conn:
        row = conn.execute(
            text("SELECT id, nombre, descripcion_nueva FROM products WHERE id = 5")
        ).one()
    assert tuple(row) == (5, 'Equipo legado', None)

    source.dispose()
    target.dispose()


def test_copy_rejects_legacy_schema_missing_required_target_data(tmp_path: Path):
    source = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    target = create_engine(f"sqlite:///{tmp_path / 'target.db'}")

    source_meta = MetaData()
    Table(
        'orders',
        source_meta,
        Column('id', Integer, primary_key=True),
    )
    source_meta.create_all(source)

    target_meta = MetaData()
    target_table = Table(
        'orders',
        target_meta,
        Column('id', Integer, primary_key=True),
        Column('required_new_field', String(50), nullable=False),
    )
    target_meta.create_all(target)

    reflected = Table('orders', MetaData(), autoload_with=source)
    assert _required_target_columns_missing_from_source(reflected, target_table) == [
        'required_new_field'
    ]

    with target.begin() as conn, pytest.raises(RuntimeError, match='demasiado antigua'):
        _copy_table_rows(source, conn, target_table)

    source.dispose()
    target.dispose()


def test_non_empty_target_is_detected_before_mixing_data(tmp_path: Path):
    target = create_engine(f"sqlite:///{tmp_path / 'target.db'}")
    metadata = MetaData()
    Table('products', metadata, Column('id', Integer, primary_key=True))
    Table('orders', metadata, Column('id', Integer, primary_key=True))
    metadata.create_all(target)

    with target.begin() as conn:
        conn.execute(text('INSERT INTO orders (id) VALUES (99)'))

    assert _target_tables_with_rows(target, ['products', 'orders']) == ['orders']
    target.dispose()


def test_sqlite_source_backup_is_consistent_and_does_not_modify_source(tmp_path: Path):
    source_path = tmp_path / 'inventory.db'
    engine = create_engine(f"sqlite:///{source_path}")
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE orders (id INTEGER PRIMARY KEY, total INTEGER)'))
        conn.execute(text('INSERT INTO orders (id, total) VALUES (1, 777)'))
    engine.dispose()

    backup_path = _backup_sqlite_source(source_path)

    assert backup_path.exists()
    assert backup_path.parent == tmp_path / 'backups'

    source_engine = create_engine(f"sqlite:///{source_path}")
    backup_engine = create_engine(f"sqlite:///{backup_path}")
    try:
        with source_engine.connect() as conn:
            source_row = conn.execute(text('SELECT id, total FROM orders')).one()
        with backup_engine.connect() as conn:
            backup_row = conn.execute(text('SELECT id, total FROM orders')).one()

        assert tuple(source_row) == (1, 777)
        assert tuple(backup_row) == (1, 777)
        assert inspect(source_engine).get_table_names() == ['orders']
    finally:
        source_engine.dispose()
        backup_engine.dispose()
