import json

import httpx
import pytest

from app.llm.qwen_client import QwenClient, QwenClientError


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.request = httpx.Request("POST", "https://qwen.example.test")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=self.request,
                response=httpx.Response(
                    self.status_code,
                    request=self.request,
                ),
            )

    def json(self):
        return self._payload


def _success_payload():
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "generated_text": "结构化生成结果",
                            "summary": ["摘要"],
                            "style_notes": [],
                            "warnings": [],
                        },
                        ensure_ascii=False,
                    )
                }
            }
        ]
    }


def test_qwen_client_retries_timeout_then_returns_structured_output():
    attempts = {"count": 0}
    sleeps = []

    def fake_post(*args, **kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise httpx.ReadTimeout("timeout", request=httpx.Request("POST", args[0]))
        return FakeResponse(_success_payload())

    client = QwenClient(
        api_key="test",
        base_url="https://qwen.example.test/v1",
        enabled=True,
        scaffold_phase_complete=True,
        max_retries=2,
        retry_backoff_ms=10,
        post=fake_post,
        sleep=sleeps.append,
    )

    result = client.generate_structured([{"role": "user", "content": "test"}])

    assert result.payload["generated_text"] == "结构化生成结果"
    assert result.attempt_count == 2
    assert attempts["count"] == 2
    assert sleeps == [0.01]


def test_qwen_client_retries_invalid_json_and_fails_with_reason_code():
    client = QwenClient(
        api_key="test",
        base_url="https://qwen.example.test/v1",
        enabled=True,
        scaffold_phase_complete=True,
        max_retries=1,
        retry_backoff_ms=0,
        post=lambda *args, **kwargs: FakeResponse(
            {"choices": [{"message": {"content": "not-json"}}]}
        ),
        sleep=lambda seconds: None,
    )

    with pytest.raises(QwenClientError) as exc_info:
        client.generate_structured([{"role": "user", "content": "test"}])

    assert exc_info.value.reason_code == "qwen_invalid_structured_output"
    assert exc_info.value.attempt_count == 2


def test_qwen_client_blocks_live_calls_during_scaffold_phase():
    calls = {"count": 0}

    def fake_post(*args, **kwargs):
        calls["count"] += 1
        return FakeResponse(_success_payload())

    client = QwenClient(
        api_key="test",
        base_url="https://qwen.example.test/v1",
        enabled=True,
        scaffold_phase_complete=False,
        post=fake_post,
    )

    with pytest.raises(QwenClientError) as exc_info:
        client.generate_structured([{"role": "user", "content": "test"}])

    assert exc_info.value.reason_code == "scaffold_phase_active"
    assert calls["count"] == 0
