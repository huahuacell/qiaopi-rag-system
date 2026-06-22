from fastapi.testclient import TestClient

from main import app
from app.llm.prompts import build_style_transfer_prompt
from app.llm.style_transfer_prompts import (
    ACTIVE_STYLE_TRANSFER_PROMPT_VERSION,
    available_style_transfer_prompt_versions,
)


client = TestClient(app)


def test_style_transfer_prompt_versions_are_preserved_and_selectable():
    versions = available_style_transfer_prompt_versions()
    assert versions == (
        "style-transfer-json-v1",
        "style-transfer-concise-json-v2",
        "style-transfer-concise-json-v3",
        "style-transfer-concise-json-v4",
        "style-transfer-vernacular-json-v5",
    )
    assert ACTIVE_STYLE_TRANSFER_PROMPT_VERSION == "style-transfer-vernacular-json-v5"

    prompts = {
        version: build_style_transfer_prompt(
            plain_text="测试输入",
            prompt_context="测试上下文",
            evidence_references=[],
            version=version,
        )
        for version in versions
    }
    assert all(messages[0]["role"] == "system" for messages in prompts.values())
    assert "请严格输出以下 JSON 结构" in prompts["style-transfer-json-v1"][1]["content"]
    assert prompts["style-transfer-json-v1"] != prompts["style-transfer-vernacular-json-v5"]


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
    assert payload["prompt_version"] == "style-transfer-vernacular-json-v5"
    assert payload["style_slots"]
    assert "opening" in payload["style_slots"]
    assert "style_reference" in payload["style_slots"]
    assert payload["prompt_context"]
    assert payload["messages"]
    assert payload["evidence_references"]
    combined_prompt = "\n".join(message["content"] for message in payload["messages"])
    assert "以自然白话为主体" in combined_prompt
    assert "不得把每个句子都改造成文言句" in combined_prompt
    assert "55%—70%" in combined_prompt
    assert "同一事实、情感或安慰只表达一次" in combined_prompt
    assert "不得堆叠套语" in combined_prompt
    assert "署名只能出现一次" in combined_prompt
    assert "一至两个正文段落" in combined_prompt
    assert "随后删除重复问候" in combined_prompt
    assert "禁止过拟合" in combined_prompt
    assert "用户输入才是生成事实的唯一来源" in combined_prompt
    assert "白话可读性检查" in combined_prompt
    assert "不得自行增加寄递方式、币种称谓" in combined_prompt
    assert "【生成草稿】" in combined_prompt
