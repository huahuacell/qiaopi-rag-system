from pathlib import Path

from fastapi.testclient import TestClient

from app import settings
from app.ingestion.build_semantic_index import build_semantic_index
from main import app


client = TestClient(app)


def _configure_hash_index(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_ENABLED", True)
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "hash")
    monkeypatch.setattr(settings, "EMBEDDING_DIM", 64)
    monkeypatch.setattr(settings, "SEMANTIC_FAISS_INDEX_PATH", tmp_path / "semantic.faiss")
    monkeypatch.setattr(settings, "SEMANTIC_FAISS_METADATA_PATH", tmp_path / "semantic_meta.jsonl")
    monkeypatch.setattr(settings, "SEMANTIC_FAISS_MANIFEST_PATH", tmp_path / "semantic_manifest.json")


def test_hybrid_search_falls_back_to_keyword_when_semantic_index_is_missing(monkeypatch, tmp_path):
    _configure_hash_index(monkeypatch, tmp_path)

    response = client.post(
        "/api/search/hybrid",
        json={
            "query": "新加坡 平安",
            "top_k": 5,
            "unit_types": [],
            "filters": {},
            "expansion_mode": "balanced",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["semantic_enabled"] is False
    assert payload["fusion_method"] == "keyword_fallback"
    assert "build_semantic_index" in payload["error_message"]
    assert payload["results"]
    assert payload["results"][0]["retrieval_sources"] == ["keyword"]


def test_hybrid_search_uses_rrf_when_semantic_index_exists(monkeypatch, tmp_path):
    _configure_hash_index(monkeypatch, tmp_path)
    build_semantic_index(provider_name="hash")

    response = client.post(
        "/api/search/hybrid",
        json={
            "query": "母亲 寄款 查收",
            "top_k": 10,
            "unit_types": [],
            "filters": {},
            "expansion_mode": "balanced",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["semantic_enabled"] is True
    assert payload["semantic_quality"] == "test_hash"
    assert payload["fusion_method"] == "rrf"
    assert payload["results"]
    assert any("semantic" in result["retrieval_sources"] for result in payload["results"])
    assert "semantic_score" in payload["results"][0]
