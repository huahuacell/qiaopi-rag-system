from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from app import settings
from app.embedding.embedding_provider import EmbeddingProviderError, get_embedding_provider


MISSING_INDEX_MESSAGE = (
    "Semantic index not found. Run python -m app.ingestion.build_semantic_index"
)
DISABLED_MESSAGE = "Semantic search is disabled. Set SEMANTIC_SEARCH_ENABLED=true."


@dataclass(frozen=True)
class SemanticIndexBundle:
    metadata: list[dict[str, Any]]
    vectors: np.ndarray | None = None
    faiss_index: Any | None = None
    backend: str = "numpy"


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _snippet(unit_text: str, query: str, length: int = 120) -> str:
    text = unit_text.strip()
    if len(text) <= length:
        return text
    for term in [part for part in query.split() if part]:
        index = text.find(term)
        if index >= 0:
            start = max(0, index - 30)
            end = min(len(text), start + length)
            return ("..." if start else "") + text[start:end] + ("..." if end < len(text) else "")
    return text[:length] + "..."


def _read_metadata(metadata_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with metadata_path.open("r", encoding="utf-8") as file:
        for line in file:
            clean_line = line.strip()
            if clean_line:
                rows.append(json.loads(clean_line))
    return rows


def _read_index(index_path: Path) -> tuple[Any | None, np.ndarray | None, str]:
    try:
        import faiss  # type: ignore

        return faiss.read_index(str(index_path)), None, "faiss"
    except Exception:
        with index_path.open("rb") as file:
            data = np.load(file)
            return None, np.asarray(data["vectors"], dtype=np.float32), "numpy"


def _index_files_exist() -> bool:
    return settings.SEMANTIC_FAISS_INDEX_PATH.exists() and settings.SEMANTIC_FAISS_METADATA_PATH.exists()


def load_semantic_index() -> SemanticIndexBundle:
    if not _index_files_exist():
        raise FileNotFoundError(MISSING_INDEX_MESSAGE)
    metadata = _read_metadata(settings.SEMANTIC_FAISS_METADATA_PATH)
    faiss_index, vectors, backend = _read_index(settings.SEMANTIC_FAISS_INDEX_PATH)
    vector_count = int(faiss_index.ntotal) if faiss_index is not None else int(vectors.shape[0])
    if vector_count != len(metadata):
        raise RuntimeError(
            f"Semantic index metadata mismatch: index has {vector_count} vectors, metadata has {len(metadata)} rows."
        )
    return SemanticIndexBundle(metadata=metadata, vectors=vectors, faiss_index=faiss_index, backend=backend)


def semantic_status() -> dict[str, Any]:
    index_exists = settings.SEMANTIC_FAISS_INDEX_PATH.exists()
    metadata_exists = settings.SEMANTIC_FAISS_METADATA_PATH.exists()
    status = {
        "semantic_enabled": bool(settings.SEMANTIC_SEARCH_ENABLED and index_exists and metadata_exists),
        "configured_enabled": settings.SEMANTIC_SEARCH_ENABLED,
        "index_exists": index_exists,
        "metadata_exists": metadata_exists,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL,
        "index_path": str(settings.SEMANTIC_FAISS_INDEX_PATH),
        "metadata_path": str(settings.SEMANTIC_FAISS_METADATA_PATH),
        "vector_count": 0,
        "error_message": None,
    }
    if not settings.SEMANTIC_SEARCH_ENABLED:
        status["error_message"] = DISABLED_MESSAGE
        return status
    if not index_exists or not metadata_exists:
        status["error_message"] = MISSING_INDEX_MESSAGE
        return status
    try:
        bundle = load_semantic_index()
        status["vector_count"] = len(bundle.metadata)
    except Exception as exc:
        status["semantic_enabled"] = False
        status["error_message"] = str(exc)
    return status


def _matches_filters(row: Mapping[str, Any], filters: Mapping[str, Any] | None) -> bool:
    if not filters:
        return True
    for key, value in filters.items():
        if value in (None, "", []):
            continue
        if key == "unit_types":
            if _text(row.get("unit_type")) not in {str(item) for item in value}:
                return False
        elif key == "theme":
            if str(value) not in _text(row.get("theme_tags")):
                return False
        elif key == "place":
            haystack = f"{_text(row.get('place_mentions_normalized'))}；{_text(row.get('normalized_places'))}"
            if str(value) not in haystack:
                return False
        elif key == "country_or_region":
            if str(value) not in _text(row.get("countries_or_regions")):
                return False
        elif key == "has_remittance":
            expected = "1" if str(value).lower() in {"1", "true", "yes"} else "0"
            if _text(row.get("has_remittance")) != expected:
                return False
        else:
            row_value = _text(row.get(key))
            if row_value != str(value):
                return False
    return True


def _semantic_result(row: Mapping[str, Any], score: float, query: str) -> dict[str, Any]:
    unit_text = _text(row.get("unit_text"))
    return {
        "record_id": _text(row.get("record_id")),
        "unit_id": _text(row.get("unit_id")),
        "unit_type": _text(row.get("unit_type")),
        "title_reference": _text(row.get("title_reference")),
        "sender": _text(row.get("sender")),
        "recipient": _text(row.get("recipient")),
        "date_text": _text(row.get("date_text")),
        "main_intent": _text(row.get("main_intent")),
        "unit_text": unit_text,
        "snippet": _snippet(unit_text, query),
        "matched_text": unit_text,
        "matched_reason": "语义向量相似度命中",
        "bm25_score": 0.0,
        "semantic_score": round(float(score), 8),
        "final_score": round(float(score), 8),
        "original_hit_count": 0,
        "strong_hit_count": 0,
        "medium_hit_count": 0,
        "weak_hit_count": 0,
        "evidence_type": _text(row.get("evidence_type")),
        "source_column": _text(row.get("source_column")),
        "retrieval_sources": ["semantic"],
    }


def _search_scores(bundle: SemanticIndexBundle, query_vector: np.ndarray, limit: int) -> list[tuple[int, float]]:
    safe_limit = max(1, min(limit, len(bundle.metadata)))
    vector = np.ascontiguousarray(query_vector.astype(np.float32))
    if bundle.faiss_index is not None:
        scores, indexes = bundle.faiss_index.search(vector, safe_limit)
        return [
            (int(index), float(score))
            for index, score in zip(indexes[0], scores[0])
            if int(index) >= 0
        ]
    assert bundle.vectors is not None
    scores = np.matmul(bundle.vectors, vector[0])
    ranked_indexes = np.argsort(-scores)[:safe_limit]
    return [(int(index), float(scores[index])) for index in ranked_indexes]


def semantic_search(
    query: str,
    top_k: int = 10,
    unit_types: list[str] | None = None,
    filters: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not settings.SEMANTIC_SEARCH_ENABLED:
        return {
            "semantic_enabled": False,
            "results": [],
            "error_message": DISABLED_MESSAGE,
            "index_backend": None,
        }
    if not _index_files_exist():
        return {
            "semantic_enabled": False,
            "results": [],
            "error_message": MISSING_INDEX_MESSAGE,
            "index_backend": None,
        }

    try:
        bundle = load_semantic_index()
        try:
            provider = get_embedding_provider()
        except EmbeddingProviderError:
            if settings.EMBEDDING_PROVIDER.strip().lower() != "local":
                raise
            provider = get_embedding_provider("hash")
        query_vector = provider.embed_texts([query])
    except (EmbeddingProviderError, FileNotFoundError, RuntimeError, ValueError, OSError) as exc:
        return {
            "semantic_enabled": False,
            "results": [],
            "error_message": str(exc),
            "index_backend": None,
        }

    requested_unit_types = {unit_type for unit_type in (unit_types or []) if unit_type}
    candidate_limit = min(len(bundle.metadata), max(top_k * 10, top_k, 50))
    ranked = _search_scores(bundle, query_vector, candidate_limit)
    results: list[dict[str, Any]] = []
    for vector_id, score in ranked:
        row = bundle.metadata[vector_id]
        if requested_unit_types and _text(row.get("unit_type")) not in requested_unit_types:
            continue
        if not _matches_filters(row, filters):
            continue
        results.append(_semantic_result(row, score, query))
        if len(results) >= top_k:
            break

    return {
        "semantic_enabled": True,
        "results": results,
        "error_message": None,
        "index_backend": bundle.backend,
    }
