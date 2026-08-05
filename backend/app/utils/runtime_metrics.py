"""Métricas runtime de API para observabilidad operativa."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Lock
from time import time


@dataclass
class Snapshot:
    total_requests: int
    total_errors: int
    in_flight: int
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    uptime_seconds: float


class RuntimeMetrics:
    """Acumula métricas de tráfico y latencia en memoria."""

    def __init__(self, latency_sample_size: int = 5000) -> None:
        self._started_at = time()
        self._lock = Lock()
        self._total_requests = 0
        self._total_errors = 0
        self._in_flight = 0
        self._latencies_ms: deque[float] = deque(maxlen=latency_sample_size)

    def on_request_start(self) -> None:
        with self._lock:
            self._in_flight += 1

    def on_request_end(self, latency_ms: float, status_code: int) -> None:
        with self._lock:
            self._in_flight = max(0, self._in_flight - 1)
            self._total_requests += 1
            if status_code >= 500:
                self._total_errors += 1
            self._latencies_ms.append(latency_ms)

    @staticmethod
    def _percentile(sorted_values: list[float], percentile: float) -> float:
        if not sorted_values:
            return 0.0
        idx = int((len(sorted_values) - 1) * percentile)
        return float(sorted_values[idx])

    def snapshot(self) -> Snapshot:
        with self._lock:
            latencies = list(self._latencies_ms)
            total_requests = self._total_requests
            total_errors = self._total_errors
            in_flight = self._in_flight

        latencies.sort()
        avg_latency = (sum(latencies) / len(latencies)) if latencies else 0.0
        p95 = self._percentile(latencies, 0.95)
        p99 = self._percentile(latencies, 0.99)

        return Snapshot(
            total_requests=total_requests,
            total_errors=total_errors,
            in_flight=in_flight,
            avg_latency_ms=round(avg_latency, 2),
            p95_latency_ms=round(p95, 2),
            p99_latency_ms=round(p99, 2),
            uptime_seconds=round(time() - self._started_at, 2),
        )
