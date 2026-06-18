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


def test_preview_prompt_works_without_qwen_api_key():
    response = client.post(
        "/api/generation/preview-prompt",
        json={
            "task_type": "style-transfer",
            "input_text": "母亲您好，我在新加坡平安，寄八元回家，请弟弟好好读书。",
            "top_k": 3,
            "filters": {},
            "expansion_mode": "balanced",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["task_type"] == "style-transfer"
    assert payload["input_text"]
    assert payload["prompt_context"]
    assert payload["messages"]
    assert payload["evidence_references"]


def test_qwen_status_does_not_expose_api_key(monkeypatch):
    unit_test_key = "unit-test-api-key"
    monkeypatch.setattr("app.settings.QWEN_ENABLED", True)
    monkeypatch.setattr("app.settings.QWEN_API_KEY", unit_test_key)
    monkeypatch.setattr("app.settings.QWEN_BASE_URL", "https://qwen.example.test/compatible-mode/v1")
    monkeypatch.setattr("app.settings.QWEN_MODEL", "qwen-plus")

    response = client.get("/api/generation/qwen-status")

    payload = response.json()
    assert response.status_code == 200
    assert payload["enabled"] is True
    assert payload["api_key_configured"] is True
    assert payload["base_url_configured"] is True
    assert payload["live_generation_ready"] is True
    assert unit_test_key not in str(payload)
    assert "QWEN_API_KEY" not in payload


def test_generation_disabled_returns_controlled_response(monkeypatch):
    monkeypatch.setattr("app.settings.QWEN_ENABLED", False)

    response = client.post(
        "/api/generation/style-transfer",
        json={
            "plain_text": "母亲您好，我在新加坡平安，寄八元回家。",
            "top_k": 2,
            "filters": {},
            "expansion_mode": "balanced",
            "dry_run": False,
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["dry_run"] is True
    assert payload["generated_text"] == ""
    assert payload["error_message"]
    assert "Qwen generation is disabled" in payload["error_message"]
    assert payload["prompt_context"]
    assert payload["evidence_references"]


def test_generation_enabled_with_api_key_does_not_return_disabled(monkeypatch):
    unit_test_key = "unit-test-api-key"
    monkeypatch.setattr("app.settings.QWEN_ENABLED", True)
    monkeypatch.setattr("app.settings.QWEN_API_KEY", unit_test_key)
    monkeypatch.setattr("app.settings.QWEN_BASE_URL", "https://qwen.example.test/compatible-mode/v1")
    monkeypatch.setattr("app.settings.QWEN_MODEL", "qwen-plus")

    def fake_generate_chat_completion(self, messages, temperature=0.3, max_tokens=1200):
        assert self.enabled is True
        assert self.api_key == unit_test_key
        assert self.base_url
        assert messages
        return "【生成侨批体草稿】慈亲大人膝下：儿客居叻埠平安，兹奉上大洋银捌元，祈查收。另望胞弟勤学向上。儿谨禀。"

    monkeypatch.setattr(
        "app.llm.qwen_client.QwenClient.generate_chat_completion",
        fake_generate_chat_completion,
    )

    response = client.post(
        "/api/generation/style-transfer",
        json={
            "plain_text": "母亲您好，我在新加坡平安，寄八元回家。",
            "top_k": 2,
            "filters": {},
            "expansion_mode": "balanced",
            "dry_run": False,
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["dry_run"] is False
    assert payload["generated_text"]
    assert payload["error_message"] is None
    assert "disabled" not in str(payload).lower()
    assert unit_test_key not in str(payload)
    assert payload["validation_report"]
    assert payload["validation_report"]["risk_level"] in {"low", "medium"}


def test_generation_query_logging_inserts_row():
    endpoint = "/api/generation/preview-prompt"
    before_count = _query_log_count(endpoint)

    response = client.post(
        endpoint,
        json={
            "task_type": "interpret",
            "input_text": "母亲寄款查收",
            "record_id": "CSQP-SFHC-TEXT-017",
            "top_k": 4,
            "filters": {},
            "expansion_mode": "balanced",
        },
    )

    assert response.status_code == 200
    assert _query_log_count(endpoint) == before_count + 1
