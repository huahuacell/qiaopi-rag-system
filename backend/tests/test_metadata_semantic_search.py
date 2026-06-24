from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import settings
from app.embedding.embedding_provider import clear_embedding_provider_cache
from app.ingestion.build_metadata_semantic_index import (
    build_metadata_semantic_index,
)
from main import app


client = TestClient(app)


def _configure_hash_metadata_index(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_ENABLED", True)
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "hash")
    monkeypatch.setattr(settings, "EMBEDDING_DIM", 64)
    monkeypatch.setattr(
        settings,
        "METADATA_SEMANTIC_FAISS_INDEX_PATH",
        tmp_path / "metadata.faiss",
    )
    monkeypatch.setattr(
        settings,
        "METADATA_SEMANTIC_FAISS_METADATA_PATH",
        tmp_path / "metadata_meta.jsonl",
    )
    monkeypatch.setattr(
        settings,
        "METADATA_SEMANTIC_FAISS_MANIFEST_PATH",
        tmp_path / "metadata_manifest.json",
    )
    clear_embedding_provider_cache()


def test_metadata_semantic_and_hybrid_search_are_available(
    monkeypatch,
    tmp_path,
    metadata_layer_ready,
):
    _configure_hash_metadata_index(monkeypatch, tmp_path)
    stats = build_metadata_semantic_index(provider_name="hash")
    assert stats["metadata_record_count"] == 50064

    semantic = client.post(
        "/api/metadata/search",
        json={
            "query": "新加坡 母亲 寄款",
            "top_k": 5,
            "filters": {},
            "retrieval_mode": "semantic",
        },
    )
    hybrid = client.post(
        "/api/metadata/search",
        json={
            "query": "新加坡 母亲 寄款",
            "top_k": 5,
            "filters": {},
            "retrieval_mode": "hybrid",
        },
    )

    semantic_payload = semantic.json()
    hybrid_payload = hybrid.json()
    assert semantic.status_code == 200
    assert semantic_payload["semantic_enabled"] is True
    assert semantic_payload["semantic_quality"] == "test_hash"
    assert semantic_payload["results"]
    assert semantic_payload["results"][0]["retrieval_sources"] == ["semantic"]
    assert hybrid.status_code == 200
    assert hybrid_payload["semantic_enabled"] is True
    assert hybrid_payload["fusion_method"] == "rrf"
    assert hybrid_payload["results"]
    assert any(
        "semantic" in result["retrieval_sources"]
        for result in hybrid_payload["results"]
    )


def test_metadata_semantic_status_reports_catalog_domain(
    monkeypatch,
    tmp_path,
    metadata_layer_ready,
):
    _configure_hash_metadata_index(monkeypatch, tmp_path)
    build_metadata_semantic_index(provider_name="hash")

    response = client.get("/api/metadata/semantic/status")
    payload = response.json()

    assert response.status_code == 200
    assert payload["semantic_enabled"] is True
    assert payload["corpus_domain"] == "metadata_catalog"
    assert payload["vector_count"] == 50064
