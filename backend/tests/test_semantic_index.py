from pathlib import Path

from app import settings
from app.database.repository import fetch_all_retrieval_units
from app.ingestion.build_semantic_index import build_semantic_index
from app.search.semantic_retriever import semantic_search, semantic_status


def _configure_hash_index(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_ENABLED", True)
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "hash")
    monkeypatch.setattr(settings, "EMBEDDING_DIM", 64)
    monkeypatch.setattr(settings, "SEMANTIC_FAISS_INDEX_PATH", tmp_path / "semantic.faiss")
    monkeypatch.setattr(settings, "SEMANTIC_FAISS_METADATA_PATH", tmp_path / "semantic_meta.jsonl")


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
    assert len(settings.SEMANTIC_FAISS_METADATA_PATH.read_text(encoding="utf-8").splitlines()) == stats[
        "retrieval_unit_count"
    ]


def test_semantic_search_returns_controlled_missing_index_message(monkeypatch, tmp_path):
    _configure_hash_index(monkeypatch, tmp_path)

    result = semantic_search("母亲 寄款 查收", top_k=3)

    assert result["semantic_enabled"] is False
    assert result["results"] == []
    assert "build_semantic_index" in result["error_message"]


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
    assert status["vector_count"] == len(fetch_all_retrieval_units())
