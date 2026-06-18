from fastapi.testclient import TestClient

from app.database.connection import get_connection
from main import app


client = TestClient(app)

EXPECTED_STYLE_SLOTS = {
    "opening",
    "safety",
    "remittance",
    "family_care",
    "instruction",
    "closing",
    "style_reference",
}


def _query_log_count(endpoint: str) -> int:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS count FROM qiaopi_query_logs WHERE endpoint = ?",
            (endpoint,),
        ).fetchone()
    return int(row["count"])


def test_style_context_returns_grouped_slot_examples():
    response = client.post(
        "/api/rag/style-context",
        json={
            "query": "母亲您好，我在新加坡平安，寄八元回家，请弟弟好好读书。",
            "top_k": 3,
            "filters": {},
            "expansion_mode": "balanced",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["semantic_enabled"] is False
    assert set(payload["style_slots"]) == EXPECTED_STYLE_SLOTS
    assert any(payload["style_slots"][slot] for slot in EXPECTED_STYLE_SLOTS)
    assert payload["grouped_contexts"]
    assert payload["prompt_context"]
    assert "【用户白话输入】" in payload["prompt_context"]
    assert "【开头称谓样例】" in payload["prompt_context"]
    assert "【寄款表达样例】" in payload["prompt_context"]

    first_non_empty_slot = next(
        slot for slot in EXPECTED_STYLE_SLOTS if payload["style_slots"][slot]
    )
    example = payload["style_slots"][first_non_empty_slot][0]
    assert example["record_id"].startswith("CSQP-SFHC-TEXT-")
    assert example["unit_id"]
    assert example["unit_type"] == first_non_empty_slot
    assert example["unit_text"]
    assert example["source_column"]
    assert example["evidence_type"]
    assert example["matched_reason"]
    assert "final_score" in example


def test_style_context_empty_slots_do_not_break_response():
    response = client.post(
        "/api/rag/style-context",
        json={
            "query": "不存在的测试词",
            "top_k": 2,
            "filters": {"record_id": "MISSING-RECORD"},
            "expansion_mode": "balanced",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert set(payload["style_slots"]) == EXPECTED_STYLE_SLOTS
    assert all(payload["style_slots"][slot] == [] for slot in EXPECTED_STYLE_SLOTS)
    assert payload["grouped_contexts"] == []
    assert payload["source_record_count"] == 0
    assert payload["semantic_enabled"] is False
    assert "暂无可用样例" in payload["prompt_context"]


def test_style_context_query_logging_inserts_row():
    endpoint = "/api/rag/style-context"
    before_count = _query_log_count(endpoint)

    response = client.post(
        endpoint,
        json={
            "query": "母亲平安寄款读书",
            "top_k": 2,
            "filters": {},
            "expansion_mode": "balanced",
        },
    )

    assert response.status_code == 200
    assert _query_log_count(endpoint) == before_count + 1
