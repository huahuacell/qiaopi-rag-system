from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from app import settings
from app.database.repository import search_metadata_records
from app.embedding.embedding_provider import (
    EmbeddingProviderError,
    get_embedding_provider,
)
from app.search.corpus_domains import (
    METADATA_CATALOG_DOMAIN,
    SEMANTIC_MANIFEST_VERSION,
    embedding_model_name,
    metadata_semantic_corpus_fingerprint,
    production_semantic_eligible,
    semantic_quality,
)
from app.search.semantic_retriever import _read_index, _read_metadata, _search_scores


RRF_K = 60
MISSING_METADATA_INDEX_MESSAGE = (
    "Metadata semantic index, metadata, or manifest not found. "
    "Run python -m app.ingestion.build_metadata_semantic_index"
)


@dataclass(frozen=True)
class MetadataSemanticBundle:
    metadata: list[dict[str, Any]]
    vectors: np.ndarray | None
    faiss_index: Any | None
    backend: str
    dimension: int
    manifest: dict[str, Any]


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _files_exist() -> bool:
    return all(
        path.exists()
        for path in (
            settings.METADATA_SEMANTIC_FAISS_INDEX_PATH,
            settings.METADATA_SEMANTIC_FAISS_METADATA_PATH,
            settings.METADATA_SEMANTIC_FAISS_MANIFEST_PATH,
        )
    )


def load_metadata_semantic_index(
    index_path: Path | None = None,
    metadata_path: Path | None = None,
    manifest_path: Path | None = None,
    *,
    validate_runtime: bool = False,
) -> MetadataSemanticBundle:
    resolved_index_path = index_path or settings.METADATA_SEMANTIC_FAISS_INDEX_PATH
    resolved_metadata_path = (
        metadata_path or settings.METADATA_SEMANTIC_FAISS_METADATA_PATH
    )
    resolved_manifest_path = (
        manifest_path or settings.METADATA_SEMANTIC_FAISS_MANIFEST_PATH
    )
    if not all(
        path.exists()
        for path in (
            resolved_index_path,
            resolved_metadata_path,
            resolved_manifest_path,
        )
    ):
        raise FileNotFoundError(MISSING_METADATA_INDEX_MESSAGE)
    metadata = _read_metadata(resolved_metadata_path)
    faiss_index, vectors, backend = _read_index(resolved_index_path)
    vector_count = (
        int(faiss_index.ntotal)
        if faiss_index is not None
        else int(vectors.shape[0])
    )
    dimension = (
        int(faiss_index.d)
        if faiss_index is not None
        else int(vectors.shape[1])
    )
    manifest = json.loads(resolved_manifest_path.read_text(encoding="utf-8"))
    mismatches: list[str] = []
    if str(manifest.get("manifest_version")) != SEMANTIC_MANIFEST_VERSION:
        mismatches.append("manifest_version")
    if manifest.get("corpus_domain") != METADATA_CATALOG_DOMAIN:
        mismatches.append("corpus_domain")
    if int(manifest.get("metadata_record_count") or 0) != vector_count:
        mismatches.append("metadata_record_count")
    if vector_count != len(metadata):
        mismatches.append("metadata_length")
    if int(manifest.get("embedding_dimension") or 0) != dimension:
        mismatches.append("embedding_dimension")
    actual_ids = [_text(row.get("metadata_id")) for row in metadata]
    if manifest.get("corpus_ids") != actual_ids:
        mismatches.append("corpus_ids")
    if manifest.get("corpus_fingerprint") != metadata_semantic_corpus_fingerprint(
        metadata
    ):
        mismatches.append("corpus_fingerprint")
    if validate_runtime:
        configured_provider = settings.EMBEDDING_PROVIDER.strip().lower()
        if manifest.get("embedding_provider") != configured_provider:
            mismatches.append("embedding_provider")
        if manifest.get("embedding_model") != embedding_model_name(
            configured_provider,
            settings,
        ):
            mismatches.append("embedding_model")
        configured_dimension = int(settings.EMBEDDING_DIM or 0)
        if configured_dimension and configured_dimension != dimension:
            mismatches.append("configured_embedding_dimension")
    if mismatches:
        raise RuntimeError(
            "Metadata semantic index manifest mismatch: "
            + ", ".join(sorted(set(mismatches)))
            + "."
        )
    return MetadataSemanticBundle(
        metadata=metadata,
        vectors=vectors,
        faiss_index=faiss_index,
        backend=backend,
        dimension=dimension,
        manifest=manifest,
    )


def metadata_semantic_status() -> dict[str, Any]:
    status = {
        "semantic_enabled": False,
        "configured_enabled": settings.SEMANTIC_SEARCH_ENABLED,
        "index_exists": settings.METADATA_SEMANTIC_FAISS_INDEX_PATH.exists(),
        "metadata_exists": settings.METADATA_SEMANTIC_FAISS_METADATA_PATH.exists(),
        "manifest_exists": settings.METADATA_SEMANTIC_FAISS_MANIFEST_PATH.exists(),
        "manifest_valid": False,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL,
        "index_path": str(settings.METADATA_SEMANTIC_FAISS_INDEX_PATH),
        "metadata_path": str(settings.METADATA_SEMANTIC_FAISS_METADATA_PATH),
        "manifest_path": str(settings.METADATA_SEMANTIC_FAISS_MANIFEST_PATH),
        "vector_count": 0,
        "corpus_domain": METADATA_CATALOG_DOMAIN,
        "corpus_fingerprint": None,
        "semantic_quality": "disabled",
        "production_semantic_eligible": False,
        "error_message": None,
    }
    if not settings.SEMANTIC_SEARCH_ENABLED:
        status["error_message"] = (
            "Semantic search is disabled. Set SEMANTIC_SEARCH_ENABLED=true."
        )
        return status
    if not _files_exist():
        status["error_message"] = MISSING_METADATA_INDEX_MESSAGE
        return status
    try:
        bundle = load_metadata_semantic_index(validate_runtime=True)
        provider = str(bundle.manifest.get("embedding_provider") or "")
        status.update(
            {
                "semantic_enabled": True,
                "manifest_valid": True,
                "embedding_provider": provider,
                "embedding_model": str(
                    bundle.manifest.get("embedding_model") or ""
                ),
                "vector_count": len(bundle.metadata),
                "corpus_fingerprint": bundle.manifest.get(
                    "corpus_fingerprint"
                ),
                "semantic_quality": semantic_quality(provider),
                "production_semantic_eligible": production_semantic_eligible(
                    provider
                ),
            }
        )
    except Exception as exc:
        status["error_message"] = str(exc)
    return status


def _matches_filters(
    row: Mapping[str, Any],
    filters: Mapping[str, Any] | None,
) -> bool:
    if not filters:
        return True
    year = int(row.get("year_normalized") or 0)
    if filters.get("year_from") not in (None, "") and year < int(
        filters["year_from"]
    ):
        return False
    if filters.get("year_to") not in (None, "") and year > int(
        filters["year_to"]
    ):
        return False
    for key in ("country_or_region", "relationship_type", "main_intent"):
        if filters.get(key) not in (None, "") and _text(row.get(key)) != str(
            filters[key]
        ):
            return False
    for key in ("origin_place", "destination_place", "place"):
        if filters.get(key) in (None, ""):
            continue
        column = "place_mentions" if key == "place" else key
        if str(filters[key]) not in _text(row.get(column)):
            return False
    for key in ("has_remittance", "has_linked_text", "needs_review"):
        if filters.get(key) in (None, ""):
            continue
        expected = 1 if str(filters[key]).lower() in {"1", "true", "yes"} else 0
        if int(row.get(key) or 0) != expected:
            return False
    return True


def _result(
    row: Mapping[str, Any],
    *,
    score: float,
    source: str,
) -> dict[str, Any]:
    return {
        "metadata_id": _text(row.get("metadata_id")),
        "title_clean": _text(row.get("title_clean")),
        "sender_raw": _text(row.get("sender_raw")),
        "recipient_raw": _text(row.get("recipient_raw")),
        "date_text": _text(row.get("date_text")),
        "year_normalized": _text(row.get("year_normalized")),
        "origin_place": _text(row.get("origin_place")),
        "destination_place": _text(row.get("destination_place")),
        "country_or_region": _text(row.get("country_or_region")),
        "remittance_raw": _text(row.get("remittance_raw")),
        "has_remittance": int(row.get("has_remittance") or 0),
        "has_linked_text": int(row.get("has_linked_text") or 0),
        "linked_record_id": _text(row.get("linked_record_id")),
        "score": round(float(score), 8),
        "snippet": _text(row.get("title_clean")),
        "bm25_score": 0.0,
        "semantic_score": round(float(score), 8),
        "final_score": round(float(score), 8),
        "retrieval_sources": [source],
        "matched_reason": "目录元数据语义向量相似度命中",
    }


def search_metadata_semantic(
    *,
    query: str,
    top_k: int,
    filters: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not settings.SEMANTIC_SEARCH_ENABLED:
        return {
            "semantic_enabled": False,
            "semantic_quality": "disabled",
            "results": [],
            "error_message": (
                "Semantic search is disabled. Set SEMANTIC_SEARCH_ENABLED=true."
            ),
        }
    if not _files_exist():
        return {
            "semantic_enabled": False,
            "semantic_quality": "disabled",
            "results": [],
            "error_message": MISSING_METADATA_INDEX_MESSAGE,
        }
    try:
        bundle = load_metadata_semantic_index(validate_runtime=True)
        provider = get_embedding_provider()
        query_vector = provider.embed_texts([query])
        if int(query_vector.shape[1]) != bundle.dimension:
            raise RuntimeError("Metadata query embedding dimension mismatch.")
    except (
        EmbeddingProviderError,
        FileNotFoundError,
        RuntimeError,
        ValueError,
        OSError,
    ) as exc:
        return {
            "semantic_enabled": False,
            "semantic_quality": "disabled",
            "results": [],
            "error_message": str(exc),
        }

    candidate_limit = min(
        len(bundle.metadata),
        max(top_k * 20, top_k, 200),
    )
    ranked = _search_scores(bundle, query_vector, candidate_limit)
    results: list[dict[str, Any]] = []
    for vector_id, score in ranked:
        row = bundle.metadata[vector_id]
        if not _matches_filters(row, filters):
            continue
        results.append(_result(row, score=score, source="semantic"))
        if len(results) >= top_k:
            break
    provider_name = str(bundle.manifest.get("embedding_provider") or "")
    return {
        "semantic_enabled": True,
        "semantic_quality": semantic_quality(provider_name),
        "results": results,
        "error_message": None,
    }


def search_metadata_hybrid(
    *,
    query: str,
    top_k: int,
    filters: Mapping[str, Any] | None,
) -> dict[str, Any]:
    keyword_rows = search_metadata_records(
        query=query,
        top_k=max(top_k * 4, top_k, 40),
        filters=filters,
    )
    semantic = search_metadata_semantic(
        query=query,
        top_k=max(top_k * 4, top_k, 40),
        filters=filters,
    )
    if not semantic["semantic_enabled"]:
        results = []
        for row in keyword_rows[:top_k]:
            prepared = dict(row)
            prepared["bm25_score"] = float(row.get("score") or 0.0)
            prepared["semantic_score"] = 0.0
            prepared["final_score"] = float(row.get("score") or 0.0)
            prepared["retrieval_sources"] = ["keyword"]
            prepared["matched_reason"] = "目录元数据 FTS5 / BM25 命中"
            results.append(prepared)
        return {
            "semantic_enabled": False,
            "semantic_quality": "disabled",
            "fusion_method": "keyword_fallback",
            "results": results,
            "error_message": semantic["error_message"],
        }

    combined: dict[str, dict[str, Any]] = {}
    scores: dict[str, float] = {}
    for rank, row in enumerate(keyword_rows, start=1):
        metadata_id = str(row.get("metadata_id") or "")
        prepared = dict(row)
        prepared["bm25_score"] = float(row.get("score") or 0.0)
        prepared["semantic_score"] = 0.0
        prepared["retrieval_sources"] = ["keyword"]
        prepared["matched_reason"] = "目录元数据 FTS5 / BM25 命中"
        combined[metadata_id] = prepared
        scores[metadata_id] = scores.get(metadata_id, 0.0) + 1 / (RRF_K + rank)
    for rank, row in enumerate(semantic["results"], start=1):
        metadata_id = str(row["metadata_id"])
        if metadata_id not in combined:
            combined[metadata_id] = dict(row)
        target = combined[metadata_id]
        target["semantic_score"] = float(row.get("semantic_score") or 0.0)
        sources = target.setdefault("retrieval_sources", [])
        if "semantic" not in sources:
            sources.append("semantic")
        target["matched_reason"] = (
            "目录元数据关键词与语义排名融合"
            if "keyword" in sources
            else "目录元数据语义向量相似度命中"
        )
        scores[metadata_id] = scores.get(metadata_id, 0.0) + 1 / (RRF_K + rank)
    results: list[dict[str, Any]] = []
    for metadata_id, row in combined.items():
        prepared = dict(row)
        prepared["final_score"] = round(scores[metadata_id], 8)
        prepared["score"] = prepared["final_score"]
        results.append(prepared)
    results.sort(
        key=lambda item: (
            -float(item.get("final_score") or 0.0),
            -float(item.get("semantic_score") or 0.0),
            str(item.get("metadata_id") or ""),
        )
    )
    return {
        "semantic_enabled": True,
        "semantic_quality": semantic["semantic_quality"],
        "fusion_method": "rrf",
        "results": results[:top_k],
        "error_message": None,
    }
