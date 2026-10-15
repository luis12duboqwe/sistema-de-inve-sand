"""The reference n8n flow must match the API without claiming Meta delivery."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / "docs/n8n/whatsapp_ai_flow.json"

def test_n8n_template_training_contract_and_delivery_disclaimer():
    flow = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    nodes = {node["name"]: node for node in flow["nodes"]}
    train = nodes["Enviar a Cola"]
    assert train["parameters"]["url"].endswith("/api/ai/training/submit")
    template = json.loads(train["parameters"]["bodyParametersJson"])
    assert set(template) == {"sales_profile_slug", "customer_question", "ai_proposed_answer"}
    assert "NO ENVÍA Meta" in flow["name"] or any("NO ENVÍA Meta" in name for name in nodes)

def test_n8n_template_has_connected_reply_on_both_branches():
    flow = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    all_ids = {node["name"] for node in flow["nodes"]}
    for source, ports in flow["connections"].items():
        assert source in all_ids, source
        for branch in ports["main"]:
            for connection in branch:
                assert connection["node"] in all_ids, connection["node"]
    train = flow["connections"]["Enviar a Cola"]["main"][0]
    assert any("NO ENVÍA Meta" in link["node"] for link in train)
