"""SQLAlchemy declarative models may not map an attribute named metadata."""
from sqlalchemy import inspect


def test_analytics_models_import_and_retain_database_metadata_column():
    from app.models.analytics import AnalyticsEvent, CustomerMemoryAudit

    mapper = inspect(AnalyticsEvent)
    assert "event_metadata" in mapper.attrs
    assert AnalyticsEvent.__table__.c.metadata.name == "metadata"
    assert mapper.attrs["event_metadata"].columns[0].name == "metadata"
    assert CustomerMemoryAudit.__table__.name == "customer_memory_audit"
