"""Regression tests for non-destructive legacy diagnostics and historical migration docs."""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = [
    "check_db_direct.py", "check_ai_tables.py", "check_user_role.py",
    "check_users_schema.py", "inspect_last_order.py",
]


def invoke(script: str, *args: str, env_overrides=None):
    env = os.environ.copy()
    env["ENVIRONMENT"] = "testing"
    env.update(env_overrides or {})
    return subprocess.run(
        [sys.executable, str(ROOT / script), *args],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=10,
        check=False,
    )


@pytest.fixture
def snapshot(tmp_path):
    path = tmp_path / "legacy-fixture.db"
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE products(id INTEGER PRIMARY KEY);
            CREATE TABLE orders(id INTEGER PRIMARY KEY, estado TEXT, total NUMERIC);
            CREATE TABLE order_items(id INTEGER PRIMARY KEY, order_id INTEGER);
            CREATE TABLE users(id INTEGER PRIMARY KEY, role_id INTEGER);
            CREATE TABLE roles(id INTEGER PRIMARY KEY);
            CREATE TABLE customers(id INTEGER PRIMARY KEY);
            CREATE TABLE ai_profile_configs(id INTEGER PRIMARY KEY);
            CREATE TABLE interaction_logs(id INTEGER PRIMARY KEY);
            CREATE TABLE training_queue(id INTEGER PRIMARY KEY);
            INSERT INTO products VALUES(1);
            INSERT INTO orders VALUES(1,'completada',1500);
            INSERT INTO order_items VALUES(1,1);
            INSERT INTO roles VALUES(2);
            INSERT INTO users VALUES(1,2);
        """)
    return path


@pytest.mark.parametrize("script", SCRIPTS)
def test_requires_explicit_legacy_snapshot(script):
    result = invoke(script)
    assert result.returncode != 0
    assert "legacy-sqlite" in result.stderr


@pytest.mark.parametrize("script", SCRIPTS)
def test_refuses_nonexistent_snapshot_without_creating_file(script, tmp_path):
    path = tmp_path / "missing.db"
    result = invoke(script, "--legacy-sqlite", str(path), "--acknowledge-legacy")
    assert result.returncode != 0
    assert not path.exists()


@pytest.mark.parametrize("script", SCRIPTS)
def test_refuses_legacy_scripts_in_production(script, snapshot):
    result = invoke(
        script, "--legacy-sqlite", str(snapshot), "--acknowledge-legacy",
        env_overrides={"ENVIRONMENT": "production"},
    )
    assert result.returncode != 0
    assert "disabled in production" in result.stderr


@pytest.mark.parametrize("script", SCRIPTS)
def test_reads_legacy_snapshot_readonly_without_writing(script, snapshot):
    prior = snapshot.read_bytes()
    result = invoke(script, "--legacy-sqlite", str(snapshot), "--acknowledge-legacy")
    assert result.returncode == 0, result.stderr + result.stdout
    assert snapshot.read_bytes() == prior


def test_documented_upgrade_commands_reject_absent_migrations():
    changelog = (ROOT / "CHANGELOG_AI_IMPROVEMENTS_V2.md").read_text(encoding="utf-8")
    transfer = (ROOT / "docs" / "GUIA_TRANSFERENCIAS.md").read_text(encoding="utf-8")
    assert "DOCUMENTO HISTÓRICO" in changelog
    assert "ARCHIVO LEGACY" in transfer
    assert "NO USAR" in changelog
    assert "no existe" in transfer
    assert (ROOT / "docs" / "ACTUALIZAR_INSTALACION_EXISTENTE.md").exists()
