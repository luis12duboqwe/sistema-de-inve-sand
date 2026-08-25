import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import SalesProfile


def _profile(
    *,
    name: str,
    slug: str,
    canales: str | None,
    active: bool = True,
) -> SalesProfile:
    return SalesProfile(
        name=name,
        slug=slug,
        tipo="bot_ia",
        canales=canales,
        active=active,
        configuracion=json.dumps({}),
    )


def test_channel_monitoring_status_parses_json_and_legacy_csv_channels(
    client: TestClient,
    db_session: Session,
) -> None:
    db_session.add_all(
        [
            _profile(
                name="JSON Profile",
                slug="json-profile",
                canales=json.dumps(["whatsapp", "instagram"]),
            ),
            _profile(
                name="Legacy CSV Profile",
                slug="legacy-csv-profile",
                canales="messenger, whatsapp",
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/channels/monitoring/status")

    assert response.status_code == 200, response.text
    payload = response.json()
    profiles = {item["slug"]: item for item in payload["profiles"]}

    assert payload["profiles_with_channels"] == 2
    assert profiles["json-profile"]["canales"] == ["whatsapp", "instagram"]
    assert profiles["legacy-csv-profile"]["canales"] == ["messenger", "whatsapp"]

    serialized = response.text
    assert '\\"whatsapp\\"' not in serialized
    assert '[\\"whatsapp\\"' not in serialized


def test_channel_monitoring_status_omits_empty_and_inactive_profiles(
    client: TestClient,
    db_session: Session,
) -> None:
    db_session.add_all(
        [
            _profile(
                name="Empty JSON Profile",
                slug="empty-json-profile",
                canales="[]",
            ),
            _profile(
                name="Whitespace Profile",
                slug="whitespace-profile",
                canales="   ",
            ),
            _profile(
                name="Inactive Profile",
                slug="inactive-profile",
                canales=json.dumps(["whatsapp"]),
                active=False,
            ),
            _profile(
                name="Active Profile",
                slug="active-profile",
                canales=json.dumps(["messenger"]),
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/channels/monitoring/status")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["profiles_with_channels"] == 1
    assert payload["profiles"] == [
        {
            "slug": "active-profile",
            "name": "Active Profile",
            "canales": ["messenger"],
            "tipo": "bot_ia",
        }
    ]
