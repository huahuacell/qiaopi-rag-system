from fastapi.testclient import TestClient

from app.ingestion.preprocess_qiaopi_wide_table import normalize_text
from app.nlp.pipeline import analyze_qiaopi_text
from app.nlp.text_normalizer import normalize_qiaopi_text_with_mapping
from main import app


client = TestClient(app)
SAMPLE_TEXT = (
    "  寄批人：儿海泉\r\n"
    "收批人：母亲大人\r\n\r\n"
    "母亲大人尊前：我在星洲平安，今寄回中央法币陆元，"
    "给家中买米和药。戊七月初十日。  "
)


def test_online_and_offline_use_the_same_normalization_rules():
    online = normalize_qiaopi_text_with_mapping(SAMPLE_TEXT)

    assert online.normalized_text == normalize_text(SAMPLE_TEXT)
    assert online.version == "qiaopi-text-normalizer-1.0.0"
    assert "\r" not in online.normalized_text
    assert online.normalized_text.startswith("寄批人")
    assert online.normalized_text.endswith("戊七月初十日。")


def test_online_nlp_returns_traceable_entities_relations_and_slots():
    payload = analyze_qiaopi_text(SAMPLE_TEXT)

    assert payload["engine"] == "deterministic_rule"
    assert payload["entities"]
    assert payload["relations"]
    assert payload["slots"]
    assert any(
        item["entity_type"] == "place" and item["value"] == "新加坡"
        for item in payload["entities"]
    )
    assert any(
        item["entity_type"] == "money" and item["value"] == "6元"
        for item in payload["entities"]
    )
    assert any(
        item["relation_type"] == "remits_money_to"
        for item in payload["relations"]
    )
    assert any(
        item["slot_name"] == "purpose" and item["value"] == "household_expenses"
        for item in payload["slots"]
    )

    for item in [*payload["entities"], *payload["relations"], *payload["slots"]]:
        assert item["extractor"] == "rule"
        assert item["extractor_version"]
        assert 0.0 <= item["confidence"] <= 1.0
        assert isinstance(item["needs_review"], bool)
        assert (
            payload["original_text"][item["original_start"] : item["original_end"]]
            == item["source_text"]
        )
        assert (
            payload["normalized_text"][
                item["normalized_start"] : item["normalized_end"]
            ]
            == item["normalized_source_text"]
        )


def test_online_nlp_api_exposes_versions_offsets_and_review_flags():
    response = client.post(
        "/api/nlp/analyze",
        json={"text": SAMPLE_TEXT, "task": "style_transfer"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["task"] == "style_transfer"
    assert payload["normalization_changed"] is True
    assert payload["normalization_version"]
    assert payload["pipeline_version"]
    assert payload["entity_extractor_version"]
    assert payload["relation_extractor_version"]
    assert payload["slot_extractor_version"]
    assert payload["summary"]["entity_count"] == len(payload["entities"])
    assert payload["summary"]["relation_count"] == len(payload["relations"])
    assert payload["summary"]["slot_count"] == len(payload["slots"])


def test_online_nlp_marks_uncertain_text_for_review():
    response = client.post(
        "/api/nlp/analyze",
        json={"text": "母亲大人尊前：今寄银□元，疑为字迹不清。"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["review_required"] is True
    assert any("不确定字符" in reason for reason in payload["review_reasons"])


def test_online_nlp_does_not_return_placeholder_entities_for_unmatched_text():
    response = client.post("/api/nlp/analyze", json={"text": "天气晴朗。"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["entities"] == []
    assert payload["relations"] == []
    assert payload["slots"] == []
