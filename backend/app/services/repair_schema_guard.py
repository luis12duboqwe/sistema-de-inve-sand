"""Required-schema gate for the opt-in repair module.

Do not import the repair ORM models until an independently installed schema
has been inspected. This prevents legacy Base.metadata.create_all() from
creating production repair tables merely because the feature flag was set.
"""
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

REQUIRED = {
    "repair_cases":{
        "id","external_reference","location_id","device_model","issue_category",
        "status","technician_id","quote_amount","approval_reference_digest",
        "quote_approved","approved_by_user_id","parts_available","qa_passed",
        "revision","created_at","updated_at"
    },
    "repair_events":{
        "id","case_id","event_key","event_type","actor_user_id",
        "prior_status","next_status","revision","at"
    }
}

def require_preinstalled_repair_schema(engine: Engine) -> None:
    # The caller must explicitly enable the feature. This function never
    # creates tables or calls metadata.create_all(), alter, migrate or commit.
    inspector=inspect(engine)
    for table,columns in REQUIRED.items():
        if not inspector.has_table(table):
            raise RuntimeError("Repair schema missing: "+table)
        actual={row["name"] for row in inspector.get_columns(table)}
        if not columns.issubset(actual):
            raise RuntimeError("Repair schema missing required fields: "+table)
    # The schema's transactional and status guards are part of reviewed DDL.
    # This is a shape check; separate migration checks remain mandatory.
