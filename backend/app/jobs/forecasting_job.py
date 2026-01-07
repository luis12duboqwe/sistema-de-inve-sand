"""Tareas programadas relacionadas con pronósticos de ventas."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI

from app.database import SessionLocal
from app.services.forecasting_service import generate_sales_forecasts, summarize_forecasts

logger = logging.getLogger(__name__)


def _build_snapshot(days_history: int = 90):
    session = SessionLocal()
    try:
        forecasts = generate_sales_forecasts(session, days_history=days_history)
        return summarize_forecasts(session, forecasts)
    except Exception:  # pragma: no cover - errores se registran
        logger.exception("Error al crear snapshot de pronósticos")
        return None
    finally:
        session.close()


def start_forecasting_job(app: FastAPI, days_history: int = 90) -> AsyncIOScheduler:
    """Configura un job diario que precalcula pronósticos."""
    scheduler = AsyncIOScheduler()

    def task() -> None:
        summary = _build_snapshot(days_history)
        if summary:
            app.state.forecast_cache = {
                "generated_at": datetime.now(timezone.utc),
                "summary": summary,
            }
            logger.info(
                "Pronósticos actualizados automáticamente (%s productos)",
                len(summary.forecasts),
            )

    # Ejecutar una vez al iniciar para precargar cache
    task()

    scheduler.add_job(task, CronTrigger(hour=3, minute=0))
    scheduler.start()
    return scheduler