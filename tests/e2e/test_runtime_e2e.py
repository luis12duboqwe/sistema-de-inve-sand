import os
import socket
import subprocess
import tempfile
import time
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


def _start_backend(*, maintenance: bool = False) -> tuple[subprocess.Popen, str, tempfile.TemporaryDirectory]:
    temp_dir = tempfile.TemporaryDirectory(prefix="inventory-e2e-")
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
            "MAINTENANCE_MODE": "true" if maintenance else "false",
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


def test_health_readiness_and_metrics_runtime():
    process, base_url, temp_dir = _start_backend(maintenance=False)
    try:
        health = requests.get(f"{base_url}/api/health", timeout=5)
        assert health.status_code == 200
        payload = health.json()
        assert payload["database"] == "connected"
        assert "readiness" in payload

        ready = requests.get(f"{base_url}/api/ready", timeout=5)
        assert ready.status_code == 200
        assert ready.json()["ready"] is True

        for _ in range(3):
            requests.get(f"{base_url}/api/health", timeout=5)

        metrics = requests.get(f"{base_url}/api/metrics", timeout=5)
        assert metrics.status_code == 200
        metrics_payload = metrics.json()
        assert metrics_payload["requests"]["total"] >= 3
        assert "p95" in metrics_payload["latency_ms"]
    finally:
        _stop_backend(process, temp_dir)


def test_maintenance_mode_blocks_business_routes():
    process, base_url, temp_dir = _start_backend(maintenance=True)
    try:
        health = requests.get(f"{base_url}/api/health", timeout=5)
        assert health.status_code == 200

        blocked = requests.get(f"{base_url}/api/products", timeout=5)
        assert blocked.status_code == 503
        payload = blocked.json()
        assert payload["status"] == "maintenance"
    finally:
        _stop_backend(process, temp_dir)
