"""Prevent legacy documentation from recommending destructive Meta credentials resets."""
from pathlib import Path

DOC = Path(__file__).resolve().parents[2] / "CHANNELS_CONFIGURATION.md"

def test_channel_instructions_distinguish_challenge_from_hmac():
    text = DOC.read_text(encoding="utf-8")
    assert "X-Hub-Signature-256" in text
    assert "HMAC-SHA256" in text
    assert "hub.verify_token" in text
    assert "no autentica" in text
    assert "App Secret" in text

def test_channel_instructions_refuse_destructive_seed_on_live_config():
    text = DOC.read_text(encoding="utf-8")
    assert "No ejecutar" in text
    assert "seed_channel_credentials.py --clear" in text
    assert "base descartable" in text
