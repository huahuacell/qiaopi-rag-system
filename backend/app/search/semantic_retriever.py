from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from app import settings
from app.embedding.embedding_provider import EmbeddingProviderError, get_embedding_provider
from app.search.corpus_domains import (
    FULL_TEXT_EVIDENCE_DOMAIN,
    SEMANTIC_MANIFEST_VERSION,
    embedding_model_name,
    production_semantic_eligible,
    semantic_corpus_fingerprint,
    semantic_quality,
)
from app.search.result_aggregator import deduplicate_results_by_record
from app.search.semantic_relevance import (
    row_matches_semantic_guard,
    semantic_guard_terms,
)


MISSING_INDEX_MESSAGE = (
    "Semantic index, metadata, or manifest not found. "
    "Run python -m app.ingestion.build_semantic_index"
)
DISABLED_MESSAGE = "Semantic search is disabled. Set SEMANTIC_SEARCH_ENABLED=true."
MANIFEST_MISMATCH_PREFIX = "Semantic index manifest mismatch"


@dataclass(frozen=True)
class SemanticIndexBundle:
    metadata: list[dict[str, Any]]
    vectors: np.ndarray | None = None
    faiss_index: Any | None = None
    backend: str = "numpy"
    dimension: int = 0
    manifest: dict[str, Any] | None = None


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


def _manifest_path(
    *,
    index_path: Path | None,
    metadata_path: Path | None,
    manifest_path: Path | None,
) -> Path:
    if manifest_path is not None:
        return manifest_path
    if index_path is not None or metadata_path is not None:
        resolved_metadata = metadata_path or settings.SEMANTIC_FAISS_METADATA_PATH
        return resolved_metadata.parent / "qiaopi_retrieval_units_manifest.json"
    return settings.SEMANTIC_FAISS_MANIFEST_PATH


def _read_manifest(manifest_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"{MANIFEST_MISMATCH_PREFIX}: manifest is not valid JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{MANIFEST_MISMATCH_PREFIX}: manifest root must be an object."
        )
    return payload


def _validate_manifest(
    *,
    manifest: Mapping[str, Any],
    metadata: list[dict[str, Any]],
    vector_count: int,
    dimension: int,
    validate_runtime: bool,
) -> None:
    mismatches: list[str] = []
    if str(manifest.get("manifest_version")) != SEMANTIC_MANIFEST_VERSION:
        mismatches.append("manifest_version")
    if manifest.get("corpus_domain") != FULL_TEXT_EVIDENCE_DOMAIN:
        mismatches.append("corpus_domain")
    if int(manifest.get("retrieval_unit_count") or 0) != vector_count:
        mismatches.append("retrieval_unit_count")
    if int(manifest.get("embedding_dimension") or 0) != dimension:
        mismatches.append("embedding_dimension")
    actual_unit_ids = [_text(row.get("unit_id")) for row in metadata]
    if manifest.get("corpus_unit_ids") != actual_unit_ids:
        mismatches.append("corpus_unit_ids")
    actual_fingerprint = semantic_corpus_fingerprint(metadata)
    if manifest.get("corpus_fingerprint") != actual_fingerprint:
        mismatches.append("corpus_fingerprint")

    if validate_runtime:
        configured_provider = settings.EMBEDDING_PROVIDER.strip().lower()
        configured_model = embedding_model_name(configured_provider, settings)
        if manifest.get("embedding_provider") != configured_provider:
            mismatches.append("embedding_provider")
        if manifest.get("embedding_model") != configured_model:
            mismatches.append("embedding_model")
        configured_dimension = int(settings.EMBEDDING_DIM or 0)
        if configured_dimension and configured_dimension != dimension:
            mismatches.append("configured_embedding_dimension")

    if mismatches:
        raise RuntimeError(
            f"{MANIFEST_MISMATCH_PREFIX}: {', '.join(sorted(set(mismatches)))}."
        )


def _index_files_exist() -> bool:
    return (
        settings.SEMANTIC_FAISS_INDEX_PATH.exists()
        and settings.SEMANTIC_FAISS_METADATA_PATH.exists()
        and settings.SEMANTIC_FAISS_MANIFEST_PATH.exists()
    )


def load_semantic_index(
    index_path: Path | None = None,
    metadata_path: Path | None = None,
    manifest_path: Path | None = None,
    *,
    validate_manifest: bool = True,
    validate_runtime: bool = False,
) -> SemanticIndexBundle:
    resolved_index_path = index_path or settings.SEMANTIC_FAISS_INDEX_PATH
    resolved_metadata_path = metadata_path or settings.SEMANTIC_FAISS_METADATA_PATH
    resolved_manifest_path = _manifest_path(
        index_path=index_path,
        metadata_path=metadata_path,
        manifest_path=manifest_path,
    )
    required_paths = [resolved_index_path, resolved_metadata_path]
    if validate_manifest:
        required_paths.append(resolved_manifest_path)
    if not all(path.exists() for path in required_paths):
        raise FileNotFoundError(MISSING_INDEX_MESSAGE)
    metadata = _read_metadata(resolved_metadata_path)
    faiss_index, vectors, backend = _read_index(resolved_index_path)
    vector_count = int(faiss_index.ntotal) if faiss_index is not None else int(vectors.shape[0])
    dimension = int(faiss_index.d) if faiss_index is not None else int(vectors.shape[1])
    if vector_count != len(metadata):
        raise RuntimeError(
            f"Semantic index metadata mismatch: index has {vector_count} vectors, metadata has {len(metadata)} rows."
        )
    manifest = _read_manifest(resolved_manifest_path) if validate_manifest else None
    if manifest is not None:
        _validate_manifest(
            manifest=manifest,
            metadata=metadata,
            vector_count=vector_count,
            dimension=dimension,
            validate_runtime=validate_runtime,
        )
    return SemanticIndexBundle(
        metadata=metadata,
        vectors=vectors,
        faiss_index=faiss_index,
        backend=backend,
        dimension=dimension,
        manifest=manifest,
    )


def semantic_status() -> dict[str, Any]:
    index_exists = settings.SEMANTIC_FAISS_INDEX_PATH.exists()
    metadata_exists = settings.SEMANTIC_FAISS_METADATA_PATH.exists()
    manifest_exists = settings.SEMANTIC_FAISS_MANIFEST_PATH.exists()
    status = {
        "semantic_enabled": False,
        "configured_enabled": settings.SEMANTIC_SEARCH_ENABLED,
        "index_exists": index_exists,
        "metadata_exists": metadata_exists,
        "manifest_exists": manifest_exists,
        "manifest_valid": False,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL,
        "index_path": str(settings.SEMANTIC_FAISS_INDEX_PATH),
        "metadata_path": str(settings.SEMANTIC_FAISS_METADATA_PATH),
        "manifest_path": str(settings.SEMANTIC_FAISS_MANIFEST_PATH),
        "vector_count": 0,
        "corpus_domain": None,
        "corpus_fingerprint": None,
        "semantic_quality": "disabled",
        "production_semantic_eligible": False,
        "error_message": None,
    }
    if not settings.SEMANTIC_SEARCH_ENABLED:
        status["error_message"] = DISABLED_MESSAGE
        return status
    if not index_exists or not metadata_exists or not manifest_exists:
        status["error_message"] = MISSING_INDEX_MESSAGE
        return status
    try:
        bundle = load_semantic_index(validate_runtime=True)
        manifest = bundle.manifest or {}
        index_provider = str(manifest.get("embedding_provider") or "")
        status["vector_count"] = len(bundle.metadata)
        status["manifest_valid"] = True
        status["semantic_enabled"] = True
        status["embedding_provider"] = index_provider
        status["embedding_model"] = str(manifest.get("embedding_model") or "")
        status["corpus_domain"] = manifest.get("corpus_domain")
        status["corpus_fingerprint"] = manifest.get("corpus_fingerprint")
        status["semantic_quality"] = semantic_quality(index_provider)
        status["production_semantic_eligible"] = production_semantic_eligible(
            index_provider
        )
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
            "semantic_quality": "disabled",
        }
    if not _index_files_exist():
        return {
            "semantic_enabled": False,
            "results": [],
            "error_message": MISSING_INDEX_MESSAGE,
            "index_backend": None,
            "semantic_quality": "disabled",
        }

    try:
        bundle = load_semantic_index(validate_runtime=True)
        provider = get_embedding_provider()
        query_vector = provider.embed_texts([query])
        if query_vector.ndim != 2 or int(query_vector.shape[1]) != bundle.dimension:
            raise RuntimeError(
                f"{MANIFEST_MISMATCH_PREFIX}: query_embedding_dimension."
            )
    except (EmbeddingProviderError, FileNotFoundError, RuntimeError, ValueError, OSError) as exc:
        return {
            "semantic_enabled": False,
            "results": [],
            "error_message": str(exc),
            "index_backend": None,
            "semantic_quality": "disabled",
        }

    requested_unit_types = {unit_type for unit_type in (unit_types or []) if unit_type}
    guard_terms = semantic_guard_terms(query)
    candidate_multiplier = 40 if guard_terms else 10
    candidate_floor = 200 if guard_terms else 50
    candidate_limit = min(
        len(bundle.metadata),
        max(top_k * candidate_multiplier, top_k, candidate_floor),
    )
    ranked = _search_scores(bundle, query_vector, candidate_limit)
    results: list[dict[str, Any]] = []
    for vector_id, score in ranked:
        row = bundle.metadata[vector_id]
        if requested_unit_types and _text(row.get("unit_type")) not in requested_unit_types:
            continue
        if not _matches_filters(row, filters):
            continue
        result = _semantic_result(row, score, query)
        if not row_matches_semantic_guard(result, guard_terms, query=query):
            continue
        results.append(result)
        if len(deduplicate_results_by_record(results, top_k=top_k)) >= top_k:
            break
    results = deduplicate_results_by_record(results, top_k=top_k)

    return {
        "semantic_enabled": True,
        "results": results,
        "error_message": None,
        "index_backend": bundle.backend,
        "semantic_quality": semantic_quality(
            str((bundle.manifest or {}).get("embedding_provider") or "")
        ),
    }
