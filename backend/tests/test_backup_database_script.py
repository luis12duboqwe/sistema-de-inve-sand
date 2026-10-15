"""The operational PostgreSQL backup script must fail closed.

These tests use a fake pg_dump and a temporary directory; no real DB access.
"""
import os
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "backup_database.sh"


def _run_backup(tmp_path, dump_script):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_pg_dump = bin_dir / "pg_dump"
    fake_pg_dump.write_text("#!/bin/sh\n" + dump_script + "\n", encoding="utf-8")
    fake_pg_dump.chmod(0o755)
    backup_dir = tmp_path / "backups"
    env = os.environ.copy()
    env.update({
        "PATH": str(bin_dir) + os.pathsep + env["PATH"],
        "BACKUP_DIR": str(backup_dir),
        "DB_NAME": "audit_fake",
        "DB_USER": "audit_fake",
        "DB_HOST": "127.0.0.1",
        "DB_PORT": "5432",
        "DB_PASSWORD": "synthetic",
        "BACKUP_RETENTION_DAYS": "1",
    })
    result = subprocess.run(
        ["bash", str(SCRIPT)], env=env, capture_output=True, text=True,
        check=False, timeout=20,
    )
    return result, backup_dir


def test_failed_pg_dump_never_publishes_backup_or_reports_success(tmp_path):
    result, backup_dir = _run_backup(tmp_path, "exit 42")
    assert result.returncode != 0
    assert "BACKUP COMPLETADO EXITOSAMENTE" not in result.stdout
    assert not list(backup_dir.glob("*.sql.gz"))
    assert not list(backup_dir.glob("*.sha256"))
    assert not list(backup_dir.glob("*.partial.*"))


def test_successful_pg_dump_publishes_verifiable_gzip_and_checksum(tmp_path):
    result, backup_dir = _run_backup(
        tmp_path, "printf '%s\\n' 'CREATE TABLE audit_fixture (id integer);'",
    )
    assert result.returncode == 0, result.stderr + result.stdout
    backups = list(backup_dir.glob("*.sql.gz"))
    assert len(backups) == 1
    assert (backup_dir / (backups[0].name + ".sha256")).exists()
    subprocess.run(["gzip", "-t", str(backups[0])], check=True, timeout=10)
    subprocess.run(
        ["sha256sum", "-c", str(backups[0]) + ".sha256"],
        check=True, timeout=10, capture_output=True,
    )
    assert "BACKUP COMPLETADO EXITOSAMENTE" in result.stdout
