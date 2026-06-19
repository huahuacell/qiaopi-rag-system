from fastapi.testclient import TestClient

from app.database.connection import get_connection
from main import app


client = TestClient(app)


def _query_log_count(endpoint: str) -> int:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS count FROM qiaopi_query_logs WHERE endpoint = ?",
            (endpoint,),
        ).fetchone()
    return int(row["count"])


def test_rag_context_returns_contexts_and_prompt_context():
    response = client.post(
        "/api/rag/context",
        json={
            "query": "母亲寄款查收的侨批内容",
            "top_k": 8,
            "unit_types": [
                "body_core",
                "remittance",
                "family_care",
                "instruction",
                "rag_summary",
            ],
            "filters": {},
            "expansion_mode": "balanced",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["query"] == "母亲寄款查收的侨批内容"
    assert payload["semantic_enabled"] is False
    assert payload["semantic_quality"] == "disabled"
    assert payload["contexts"]
    assert payload["grouped_contexts"]
    assert payload["prompt_context"]
    assert "【检索问题】" in payload["prompt_context"]
    assert "【相关侨批证据 1】" in payload["prompt_context"]
    assert payload["evidence_count"] == len(payload["contexts"])
    assert payload["source_record_count"] >= 1


def test_rag_context_preserves_traceable_evidence_fields():
    response = client.post(
        "/api/rag/context",
        json={
            "query": "母亲寄款查收的侨批内容",
            "top_k": 5,
            "unit_types": ["remittance", "body_core", "rag_summary"],
            "filters": {},
            "expansion_mode": "balanced",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["contexts"]
    context = payload["contexts"][0]
    assert context["record_id"].startswith("CSQP-SFHC-TEXT-")
    assert context["unit_id"]
    assert context["source_column"]
    assert context["evidence_type"]
    assert context["unit_text"]
    assert context["matched_reason"]
    assert "final_score" in context


def test_rag_context_query_logging_inserts_row():
    endpoint = "/api/rag/context"
    before_count = _query_log_count(endpoint)

    response = client.post(
        endpoint,
        json={
            "query": "平安寄款",
            "top_k": 4,
            "unit_types": ["safety", "remittance", "body_core"],
            "filters": {},
            "expansion_mode": "balanced",
        },
    )

    assert response.status_code == 200
    assert _query_log_count(endpoint) == before_count + 1
