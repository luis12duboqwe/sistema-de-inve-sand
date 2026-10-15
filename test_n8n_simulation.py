"""Optional isolated n8n test discovery; never asserts a fake end-to-end success."""
import os
import pytest
from n8n_sandbox_probe import main


def test_n8n_flow():
    api = os.environ.get("SOFTMOBILE_SANDBOX_API_URL")
    if not api:
        pytest.skip("No isolated test API configured; do not assert a fake n8n success")
    assert main(["--api-url", api, "--confirm-isolated-test"]) == 0


if __name__ == "__main__":
    raise SystemExit(main())
