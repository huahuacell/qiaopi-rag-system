import json
from pathlib import Path

import pytest

from app import settings
from app.database.repository import fetch_all_retrieval_units
from app.embedding.embedding_provider import EmbeddingProviderError
from app.ingestion.build_semantic_index import build_semantic_index
from app.search.semantic_retriever import semantic_search, semantic_status


def _configure_hash_index(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_ENABLED", True)
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "hash")
    monkeypatch.setattr(settings, "EMBEDDING_DIM", 64)
    monkeypatch.setattr(settings, "SEMANTIC_FAISS_INDEX_PATH", tmp_path / "semantic.faiss")
    monkeypatch.setattr(settings, "SEMANTIC_FAISS_METADATA_PATH", tmp_path / "semantic_meta.jsonl")
    monkeypatch.setattr(settings, "SEMANTIC_FAISS_MANIFEST_PATH", tmp_path / "semantic_manifest.json")


def test_build_semantic_index_writes_index_and_metadata(monkeypatch, tmp_path):
    _configure_hash_index(monkeypatch, tmp_path)

    stats = build_semantic_index(provider_name="hash")

    assert stats["status"] == "ok"
    assert stats["embedding_provider"] == "hash"
    assert stats["embedding_model"] == "hash-sha256-char-v1"
    assert stats["embedding_dimension"] == 64
    assert len(stats["corpus_fingerprint"]) == 64
    assert stats["retrieval_regression"]
    assert all(item["hits"] for item in stats["retrieval_regression"])
    assert stats["retrieval_unit_count"] == len(fetch_all_retrieval_units())
    assert settings.SEMANTIC_FAISS_INDEX_PATH.exists()
    assert settings.SEMANTIC_FAISS_METADATA_PATH.exists()
    assert settings.SEMANTIC_FAISS_MANIFEST_PATH.exists()
    manifest = json.loads(
        settings.SEMANTIC_FAISS_MANIFEST_PATH.read_text(encoding="utf-8")
    )
    assert manifest["corpus_domain"] == "full_text_evidence"
    assert len(manifest["corpus_unit_ids"]) == stats["retrieval_unit_count"]
    assert manifest["semantic_quality"] == "test_hash"
    assert manifest["production_semantic_eligible"] is False
    assert len(settings.SEMANTIC_FAISS_METADATA_PATH.read_text(encoding="utf-8").splitlines()) == stats[
        "retrieval_unit_count"
    ]


def test_semantic_search_returns_controlled_missing_index_message(monkeypatch, tmp_path):
    _configure_hash_index(monkeypatch, tmp_path)

    result = semantic_search("母亲 寄款 查收", top_k=3)

    assert result["semantic_enabled"] is False
    assert result["results"] == []
    assert "build_semantic_index" in result["error_message"]


def test_local_index_build_does_not_fall_back_to_hash(monkeypatch, tmp_path):
    _configure_hash_index(monkeypatch, tmp_path)

    def unavailable_provider(provider_name):
        raise EmbeddingProviderError(f"provider unavailable: {provider_name}")

    monkeypatch.setattr(
        "app.ingestion.build_semantic_index.get_embedding_provider",
        unavailable_provider,
    )

    with pytest.raises(EmbeddingProviderError, match="provider unavailable: local"):
        build_semantic_index(provider_name="local")

    assert not settings.SEMANTIC_FAISS_INDEX_PATH.exists()
    assert not settings.SEMANTIC_FAISS_MANIFEST_PATH.exists()


def test_semantic_search_reads_hash_index(monkeypatch, tmp_path):
    _configure_hash_index(monkeypatch, tmp_path)
    build_semantic_index(provider_name="hash")

    result = semantic_search("母亲 寄款 查收", top_k=5)
    status = semantic_status()

    assert result["semantic_enabled"] is True
    assert result["results"]
    assert result["results"][0]["semantic_score"] != 0
    assert result["results"][0]["retrieval_sources"] == ["semantic"]
    assert status["semantic_enabled"] is True
    assert status["semantic_quality"] == "test_hash"
    assert status["production_semantic_eligible"] is False
    assert status["manifest_valid"] is True
    assert status["vector_count"] == len(fetch_all_retrieval_units())


def test_semantic_search_rejects_runtime_model_mismatch(monkeypatch, tmp_path):
    _configure_hash_index(monkeypatch, tmp_path)
    build_semantic_index(provider_name="hash")
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "local")
    monkeypatch.setattr(settings, "EMBEDDING_MODEL", "different-model")

    result = semantic_search("母亲 寄款 查收", top_k=5)
    status = semantic_status()

    assert result["semantic_enabled"] is False
    assert result["results"] == []
    assert "manifest mismatch" in result["error_message"].lower()
    assert "embedding_model" in result["error_message"]
    assert status["semantic_enabled"] is False
    assert status["manifest_valid"] is False


def test_semantic_search_rejects_corpus_manifest_mismatch(monkeypatch, tmp_path):
    _configure_hash_index(monkeypatch, tmp_path)
    build_semantic_index(provider_name="hash")
    manifest = json.loads(
        settings.SEMANTIC_FAISS_MANIFEST_PATH.read_text(encoding="utf-8")
    )
    manifest["corpus_unit_ids"][0] = "tampered-unit-id"
    settings.SEMANTIC_FAISS_MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False),
        encoding="utf-8",
    )

    result = semantic_search("母亲 寄款 查收", top_k=5)

    assert result["semantic_enabled"] is False
    assert result["results"] == []
    assert "corpus_unit_ids" in result["error_message"]
