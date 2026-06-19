from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_interpret_dry_run_returns_prompt_and_evidence_references():
    response = client.post(
        "/api/generation/interpret",
        json={
            "query": "这封侨批主要说了什么？",
            "record_id": "CSQP-SFHC-TEXT-017",
            "top_k": 8,
            "filters": {},
            "expansion_mode": "balanced",
            "dry_run": True,
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["task_type"] == "interpret"
    assert payload["record_id"] == "CSQP-SFHC-TEXT-017"
    assert payload["semantic_enabled"] is False
    assert payload["semantic_quality"] == "disabled"
    assert payload["dry_run"] is True
    assert payload["generation_backend"] == "prompt_preview"
    assert payload["degraded_reason"] == "dry_run_requested"
    assert payload["cache_hit"] is False
    assert payload["prompt_version"] == "interpret-json-v2"
    assert payload["index_version"]
    assert payload["prompt_context"]
    assert payload["messages"]
    assert payload["evidence_references"]
    reference = payload["evidence_references"][0]
    assert reference["record_id"] == "CSQP-SFHC-TEXT-017"
    assert reference["unit_id"]
    assert reference["source_column"]
    assert reference["evidence_type"]


def test_style_transfer_dry_run_returns_style_slots_and_references():
    response = client.post(
        "/api/generation/style-transfer",
        json={
            "plain_text": "母亲您好，我在新加坡平安，寄八元回家，请弟弟好好读书。",
            "top_k": 3,
            "filters": {},
            "expansion_mode": "balanced",
            "dry_run": True,
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["task_type"] == "style-transfer"
    assert payload["semantic_enabled"] is False
    assert payload["semantic_quality"] == "disabled"
    assert payload["dry_run"] is True
    assert payload["generation_backend"] == "prompt_preview"
    assert payload["degraded_reason"] == "dry_run_requested"
    assert payload["prompt_version"] == "style-transfer-json-v2"
    assert payload["style_slots"]
    assert "opening" in payload["style_slots"]
    assert "style_reference" in payload["style_slots"]
    assert payload["prompt_context"]
    assert payload["messages"]
    assert payload["evidence_references"]
