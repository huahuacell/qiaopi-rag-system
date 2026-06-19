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


def test_semantic_search_api_reports_missing_index(monkeypatch, tmp_path):
    _configure_hash_index(monkeypatch, tmp_path)

    response = client.post(
        "/api/search/semantic",
        json={"query": "母亲 寄款 查收", "top_k": 3, "unit_types": [], "filters": {}},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["semantic_enabled"] is False
    assert payload["results"] == []
    assert "build_semantic_index" in payload["error_message"]


def test_semantic_search_api_returns_results_when_index_exists(monkeypatch, tmp_path):
    _configure_hash_index(monkeypatch, tmp_path)
    build_semantic_index(provider_name="hash")

    response = client.post(
        "/api/search/semantic",
        json={"query": "母亲 寄款 查收", "top_k": 5, "unit_types": [], "filters": {}},
    )
    status_response = client.get("/api/search/semantic/status")

    payload = response.json()
    status_payload = status_response.json()
    assert response.status_code == 200
    assert payload["semantic_enabled"] is True
    assert payload["semantic_quality"] == "test_hash"
    assert payload["results"]
    assert payload["results"][0]["retrieval_sources"] == ["semantic"]
    assert "semantic_score" in payload["results"][0]
    assert status_response.status_code == 200
    assert status_payload["semantic_enabled"] is True
    assert status_payload["production_semantic_eligible"] is False
    assert status_payload["vector_count"] > 0


def test_rag_context_accepts_semantic_retrieval_mode(monkeypatch, tmp_path):
    _configure_hash_index(monkeypatch, tmp_path)
    build_semantic_index(provider_name="hash")

    response = client.post(
        "/api/rag/context",
        json={
            "query": "母亲寄款查收的侨批内容",
            "top_k": 5,
            "unit_types": ["body_core", "remittance", "family_care", "instruction", "rag_summary"],
            "filters": {},
            "expansion_mode": "balanced",
            "retrieval_mode": "semantic",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["semantic_enabled"] is True
    assert payload["contexts"]
