from fastapi.testclient import TestClient

from app.database.connection import get_connection
from app.llm.qwen_client import QwenStructuredResult
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
    monkeypatch.setattr("app.settings.SCAFFOLD_PHASE_COMPLETE", True)
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
    assert payload["scaffold_phase_complete"] is True
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
    assert payload["dry_run"] is False
    assert payload["generated_text"]
    assert payload["generation_backend"] == "deterministic_local"
    assert payload["degraded_reason"] in {"scaffold_phase_active", "qwen_disabled"}
    assert payload["model"] == "deterministic-local-v1"
    assert payload["cache_hit"] is False
    assert payload["prompt_context"]
    assert payload["evidence_references"]
    assert payload["evidence_mapping"]


def test_generation_enabled_with_api_key_does_not_return_disabled(monkeypatch):
    unit_test_key = "unit-test-api-key"
    monkeypatch.setattr("app.settings.QWEN_ENABLED", True)
    monkeypatch.setattr("app.settings.SCAFFOLD_PHASE_COMPLETE", True)
    monkeypatch.setattr("app.settings.QWEN_API_KEY", unit_test_key)
    monkeypatch.setattr("app.settings.QWEN_BASE_URL", "https://qwen.example.test/compatible-mode/v1")
    monkeypatch.setattr("app.settings.QWEN_MODEL", "qwen-plus")

    def fake_generate_structured(self, messages, temperature=0.2, max_tokens=1600):
        assert self.enabled is True
        assert self.scaffold_phase_complete is True
        assert self.api_key == unit_test_key
        assert self.base_url
        assert messages
        return QwenStructuredResult(
            payload={
                "generated_text": "【生成侨批体草稿】慈亲大人膝下：儿客居叻埠平安，兹奉上大洋银捌元，祈查收。",
                "summary": ["寄款八元"],
                "style_notes": ["慈亲大人膝下"],
                "warnings": [],
            },
            model="qwen-plus",
            attempt_count=1,
        )

    monkeypatch.setattr(
        "app.llm.qwen_client.QwenClient.generate_structured",
        fake_generate_structured,
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
    assert payload["generation_backend"] == "qwen"
    assert payload["prompt_version"] == "style-transfer-vernacular-json-v5"
    assert payload["index_version"]
    assert payload["cache_hit"] is False
    assert payload["degraded_reason"] is None
    assert payload["attempt_count"] == 1
    assert payload["structured_output"]["summary"] == ["寄款八元"]
    assert payload["evidence_mapping"]
    assert payload["error_message"] is None
    assert payload["semantic_enabled"] is False
    assert payload["semantic_quality"] == "disabled"
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


def test_generation_cache_prevents_duplicate_mock_qwen_call(monkeypatch):
    monkeypatch.setattr("app.settings.SCAFFOLD_PHASE_COMPLETE", True)
    monkeypatch.setattr("app.settings.QWEN_ENABLED", True)
    monkeypatch.setattr("app.settings.QWEN_API_KEY", "unit-test-key")
    monkeypatch.setattr(
        "app.settings.QWEN_BASE_URL",
        "https://qwen.example.test/compatible-mode/v1",
    )
    calls = {"count": 0}

    def fake_generate_structured(self, messages, temperature=0.2, max_tokens=1600):
        calls["count"] += 1
        return QwenStructuredResult(
            payload={
                "generated_text": "【生成解读】此信向母亲报平安并说明寄款。",
                "summary": ["报平安", "寄款"],
                "style_notes": [],
                "warnings": [],
            },
            model="qwen-plus",
            attempt_count=1,
        )

    monkeypatch.setattr(
        "app.llm.qwen_client.QwenClient.generate_structured",
        fake_generate_structured,
    )
    request = {
        "query": "缓存闭环测试：这封信说了什么？",
        "record_id": "CSQP-SFHC-TEXT-017",
        "top_k": 4,
        "filters": {},
        "expansion_mode": "balanced",
        "dry_run": False,
    }

    first = client.post("/api/generation/interpret", json=request).json()
    second = client.post("/api/generation/interpret", json=request).json()

    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert first["cache_key"] == second["cache_key"]
    assert calls["count"] == 1


def test_generation_call_log_records_backend_and_cache_state():
    response = client.post(
        "/api/generation/style-transfer",
        json={
            "plain_text": "调用日志测试：母亲，我在新加坡平安。",
            "top_k": 2,
            "filters": {},
            "expansion_mode": "balanced",
            "dry_run": False,
        },
    )
    payload = response.json()

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM qiaopi_generation_logs
            WHERE request_id = ?
            """,
            (payload["request_id"],),
        ).fetchone()

    assert row is not None
    assert row["generation_backend"] == payload["generation_backend"]
    assert bool(row["cache_hit"]) is payload["cache_hit"]
    assert row["prompt_version"] == payload["prompt_version"]
    assert row["index_version"] == payload["index_version"]
