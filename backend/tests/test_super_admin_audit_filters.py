from datetime import UTC, datetime

from app.models import AuditLog


def _audit(
    db_session,
    *,
    username: str,
    action: str,
    created_at: datetime | None = None,
) -> AuditLog:
    row = AuditLog(
        username=username,
        action=action,
        entity_type="test",
        created_at=created_at or datetime.now(UTC),
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def test_default_filter_matches_literal_super_admin_prefix_only(client, db_session):
    canonical = _audit(
        db_session,
        username="root",
        action="super_admin.stock.adjust",
    )
    _audit(
        db_session,
        username="root",
        action="superXadmin.stock.adjust",
    )

    response = client.get("/api/super-admin/audit-logs")

    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()["items"]] == [canonical.id]


def test_username_percent_and_underscore_are_literal_search_text(client, db_session):
    percent = _audit(
        db_session,
        username="cashier%one",
        action="super_admin.user.test",
    )
    underscore = _audit(
        db_session,
        username="cashier_one",
        action="super_admin.user.test",
    )
    _audit(
        db_session,
        username="cashierXone",
        action="super_admin.user.test",
    )

    percent_response = client.get(
        "/api/super-admin/audit-logs",
        params={"username": "%"},
    )
    underscore_response = client.get(
        "/api/super-admin/audit-logs",
        params={"username": "_"},
    )

    assert percent_response.status_code == 200, percent_response.text
    assert [item["id"] for item in percent_response.json()["items"]] == [percent.id]
    assert underscore_response.status_code == 200, underscore_response.text
    assert [item["id"] for item in underscore_response.json()["items"]] == [underscore.id]


def test_action_like_metacharacters_are_literal_search_text(client, db_session):
    percent = _audit(
        db_session,
        username="root",
        action="super_admin.audit%export",
    )
    underscore = _audit(
        db_session,
        username="root",
        action="super_admin.audit_event",
    )
    _audit(
        db_session,
        username="root",
        action="super_admin.auditXevent",
    )

    percent_response = client.get(
        "/api/super-admin/audit-logs",
        params={"action": "audit%"},
    )
    underscore_response = client.get(
        "/api/super-admin/audit-logs",
        params={"action": "audit_"},
    )

    assert percent_response.status_code == 200, percent_response.text
    assert [item["id"] for item in percent_response.json()["items"]] == [percent.id]
    assert underscore_response.status_code == 200, underscore_response.text
    assert [item["id"] for item in underscore_response.json()["items"]] == [underscore.id]


def test_invalid_iso_date_filters_return_400(client):
    bad_start = client.get(
        "/api/super-admin/audit-logs",
        params={"start_date": "not-a-date"},
    )
    bad_end = client.get(
        "/api/super-admin/audit-logs",
        params={"end_date": "2026-99-99"},
    )

    assert bad_start.status_code == 400
    assert "start_date" in bad_start.json()["detail"]
    assert bad_end.status_code == 400
    assert "end_date" in bad_end.json()["detail"]


def test_date_only_end_filter_includes_entire_day(client, db_session):
    included = _audit(
        db_session,
        username="root",
        action="super_admin.audit.day",
        created_at=datetime(2026, 8, 24, 23, 59, 59, tzinfo=UTC),
    )
    _audit(
        db_session,
        username="root",
        action="super_admin.audit.next-day",
        created_at=datetime(2026, 8, 25, 0, 0, 0, tzinfo=UTC),
    )

    response = client.get(
        "/api/super-admin/audit-logs",
        params={"end_date": "2026-08-24"},
    )

    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()["items"]] == [included.id]


def test_blank_text_filters_do_not_expand_or_restrict_results(client, db_session):
    first = _audit(
        db_session,
        username="root",
        action="super_admin.audit.first",
        created_at=datetime(2026, 8, 24, 10, 0, tzinfo=UTC),
    )
    second = _audit(
        db_session,
        username="manager",
        action="super_admin.audit.second",
        created_at=datetime(2026, 8, 24, 11, 0, tzinfo=UTC),
    )

    response = client.get(
        "/api/super-admin/audit-logs",
        params={"username": "   ", "action": "   "},
    )

    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()["items"]] == [second.id, first.id]
