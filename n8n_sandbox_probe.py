"""Safe, read-only n8n discovery probe against an EXPLICIT local test API.

A success result verifies only protected API discovery. It does not claim Meta
delivery, training submission, order creation or a live n8n workflow succeeded.
"""
from __future__ import annotations

import argparse
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def validate_target(api_url: str, environment: str, confirm: bool, jwt: str) -> str:
    if environment.lower() != "testing":
        raise ValueError("Sandbox checks require ENVIRONMENT=testing")
    if not confirm:
        raise ValueError("--confirm-isolated-test must be supplied")
    if not jwt:
        raise ValueError("SOFTMOBILE_TEST_JWT is required for protected discovery")
    parsed = urlsplit(api_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Only an explicit loopback HTTP test API is permitted")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Credentials, query and fragments are not allowed in the API URL")
    if not parsed.path.rstrip("/").endswith("/api"):
        raise ValueError("The test API must end with /api")
    return api_url.rstrip("/")


def probe_discovery(api_url: str, jwt: str) -> int:
    request = Request(
        api_url + "/sales-profiles",
        headers={"Authorization": "Bearer " + jwt, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=8) as response:
            if response.status != 200:
                raise RuntimeError(f"Discovery returned HTTP {response.status}")
            payload = json.loads(response.read())
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise RuntimeError(f"Protected discovery failed: {exc}") from exc
    profiles = payload.get("items", payload) if isinstance(payload, dict) else payload
    if not isinstance(profiles, list) or not profiles:
        raise RuntimeError("The test API returned no sales profiles")
    if not any(isinstance(p, dict) and p.get("tipo") == "bot_ia" for p in profiles):
        raise RuntimeError("The sandbox has no AI sales profile")
    print(f"Authorized sandbox discovery OK: {len(profiles)} profile(s)")
    print("NOT VERIFIED: n8n execution, OpenAI reply, Meta/WhatsApp delivery, training or order creation")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True, help="Sandbox URL, e.g. http://127.0.0.1:8001/api")
    parser.add_argument("--confirm-isolated-test", action="store_true")
    args = parser.parse_args(argv)
    token = os.environ.get("SOFTMOBILE_TEST_JWT", "")
    try:
        base = validate_target(
            args.api_url, os.environ.get("ENVIRONMENT", ""),
            args.confirm_isolated_test, token,
        )
        return probe_discovery(base, token)
    except (ValueError, RuntimeError) as exc:
        parser.exit(status=2, message=f"Probe FAILED: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
