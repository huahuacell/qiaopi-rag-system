from fastapi.testclient import TestClient

from app import settings
from app.database.connection import get_connection
from app.ingestion.build_semantic_index import build_semantic_index
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


def _configure_hash_index(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_ENABLED", True)
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "hash")
    monkeypatch.setattr(settings, "EMBEDDING_DIM", 64)
    monkeypatch.setattr(settings, "SEMANTIC_FAISS_INDEX_PATH", tmp_path / "semantic.faiss")
    monkeypatch.setattr(settings, "SEMANTIC_FAISS_METADATA_PATH", tmp_path / "semantic_meta.jsonl")
    monkeypatch.setattr(settings, "SEMANTIC_FAISS_MANIFEST_PATH", tmp_path / "semantic_manifest.json")


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
    assert payload["retrieval_mode"] == "hybrid"
    assert set(payload["style_slots"]) == EXPECTED_STYLE_SLOTS
    assert payload["active_style_slots"] == [
        "opening",
        "safety",
        "remittance",
        "instruction",
        "closing",
        "style_reference",
    ]
    assert any(payload["style_slots"][slot] for slot in EXPECTED_STYLE_SLOTS)
    assert payload["grouped_contexts"]
    assert payload["prompt_context"]
    assert "【事实来源（唯一）】" in payload["prompt_context"]
    assert "【文体参考使用规则】" in payload["prompt_context"]
    assert "【开头称谓样例】" in payload["prompt_context"]
    assert "【寄款表达样例】" in payload["prompt_context"]
    assert payload["prompt_included_count"] > 0
    assert payload["prompt_character_count"] <= 900

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
    assert "slot_score" in example
    assert "quality_score" in example
    assert "slot_purity_score" in example
    assert "retrieval_sources" in example
    assert "。；" not in example["unit_text"]
    assert sum(
        1
        for examples in payload["style_slots"].values()
        for item in examples
        if item["prompt_included"]
    ) == payload["prompt_included_count"]


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
    assert payload["retrieval_mode"] == "hybrid"
    assert payload["active_style_slots"] == [
        "opening",
        "closing",
        "style_reference",
    ]
    assert "暂无达到质量要求的知识库样例" in payload["prompt_context"]


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


def test_style_context_uses_hybrid_rrf_when_semantic_index_exists(
    monkeypatch,
    tmp_path,
):
    _configure_hash_index(monkeypatch, tmp_path)
    build_semantic_index(provider_name="hash")

    response = client.post(
        "/api/rag/style-context",
        json={
            "query": "母亲平安，寄八元回家，请查收。",
            "top_k": 2,
            "filters": {},
            "expansion_mode": "balanced",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["retrieval_mode"] == "hybrid"
    assert payload["semantic_enabled"] is True
    assert payload["semantic_quality"] == "test_hash"
    examples = [
        example
        for slot_examples in payload["style_slots"].values()
        for example in slot_examples
    ]
    assert examples
    assert any("semantic" in example["retrieval_sources"] for example in examples)


def test_style_context_infers_named_spouse_and_avoids_parent_opening():
    response = client.post(
        "/api/rag/style-context",
        json={
            "query": (
                "淑兰：我到曼谷已近半年，托可靠船客捎回三十元，"
                "二十元作家用，十元给孩子添衣。近日夜雨想起你，"
                "待生意安稳便设法回去。木泉"
            ),
            "top_k": 3,
            "filters": {},
            "expansion_mode": "balanced",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    opening = payload["style_slots"]["opening"][0]
    assert opening["relationship_profile"] == "wife"
    assert opening["relationship_match"] == "matched"
    assert opening["relationship_type"] == "spouse_to_spouse"
    assert not any(
        term in opening["unit_text"]
        for term in ("慈亲", "母亲", "膝下")
    )
    assert opening["prompt_included"] is True
    closing = payload["style_slots"]["closing"][0]
    assert "【署名】" in closing["prompt_text"]
    assert closing["prompt_text"].startswith("夫")
    assert "【本次收信关系】" in payload["prompt_context"]
    assert "夫妻（写给妻子）" in payload["prompt_context"]
