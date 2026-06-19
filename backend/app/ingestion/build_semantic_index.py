from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from app import settings
from app.database.repository import fetch_all_retrieval_units
from app.embedding.embedding_provider import (
    EmbeddingProvider,
    EmbeddingProviderError,
    get_embedding_provider,
)
from app.search.semantic_retriever import _search_scores, load_semantic_index


INDEX_TEXT_FIELDS: tuple[str, ...] = (
    "unit_text",
    "title_reference",
    "sender",
    "recipient",
    "main_intent",
    "theme_tags",
    "style_keywords",
    "relationship_type",
    "place_mentions_normalized",
    "retrieval_keywords",
)

METADATA_FIELDS: tuple[str, ...] = (
    "unit_id",
    "record_id",
    "unit_type",
    "title_reference",
    "sender",
    "recipient",
    "date_text",
    "main_intent",
    "unit_text",
    "source_column",
    "evidence_type",
    "theme_tags",
    "style_keywords",
    "relationship_type",
    "place_mentions_normalized",
    "retrieval_keywords",
    "weight",
    "text_quality_level",
    "has_remittance",
    "year_normalized",
    "normalized_places",
    "countries_or_regions",
)

HASH_EMBEDDING_MODEL = "hash-sha256-char-v1"
DEFAULT_REGRESSION_QUERIES: tuple[str, ...] = (
    "母亲 寄款 查收",
    "新加坡 平安",
    "读书 勤学",
)


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def semantic_index_text(row: Mapping[str, Any]) -> str:
    parts = [_text(row.get(field_name)) for field_name in INDEX_TEXT_FIELDS]
    return "\n".join(part for part in parts if part)


def _batched(values: list[str], batch_size: int) -> Iterable[list[str]]:
    safe_batch_size = max(1, batch_size)
    for start in range(0, len(values), safe_batch_size):
        yield values[start : start + safe_batch_size]


def _embedding_model_name(provider_name: str) -> str:
    if provider_name == "hash":
        return HASH_EMBEDDING_MODEL
    if provider_name == "qwen":
        return settings.QWEN_EMBEDDING_MODEL or ""
    return settings.EMBEDDING_MODEL


def _resolve_provider(
    provider_name: str | None,
) -> tuple[EmbeddingProvider, str, str]:
    effective_provider_name = provider_name or settings.EMBEDDING_PROVIDER
    try:
        provider = get_embedding_provider(effective_provider_name)
    except EmbeddingProviderError:
        if (effective_provider_name or "").strip().lower() != "local":
            raise
        provider = get_embedding_provider("hash")
        effective_provider_name = "hash"
    effective_provider_name = effective_provider_name.strip().lower()
    return (
        provider,
        effective_provider_name,
        _embedding_model_name(effective_provider_name),
    )


def _embed_texts(
    texts: list[str],
    provider_name: str | None,
) -> tuple[np.ndarray, EmbeddingProvider, str, str]:
    provider, effective_provider_name, embedding_model = _resolve_provider(provider_name)
    batches: list[np.ndarray] = []
    for batch in _batched(texts, settings.EMBEDDING_BATCH_SIZE):
        batches.append(provider.embed_texts(batch))
    if not batches:
        vectors = np.zeros((0, settings.EMBEDDING_DIM or 384), dtype=np.float32)
    else:
        vectors = np.vstack(batches).astype(np.float32)
    return vectors, provider, effective_provider_name, embedding_model


def _write_faiss_or_numpy_index(vectors: np.ndarray, index_path: Path) -> str:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import faiss  # type: ignore
    except ImportError:
        with index_path.open("wb") as file:
            np.savez(file, vectors=vectors)
        return "numpy"

    index = faiss.IndexFlatIP(int(vectors.shape[1]))
    index.add(np.ascontiguousarray(vectors, dtype=np.float32))
    faiss.write_index(index, str(index_path))
    return "faiss"


def _write_metadata(rows: list[Mapping[str, Any]], metadata_path: Path) -> None:
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with metadata_path.open("w", encoding="utf-8") as file:
        for vector_id, row in enumerate(rows):
            item = {"vector_id": vector_id}
            item.update({field_name: _text(row.get(field_name)) for field_name in METADATA_FIELDS})
            file.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def corpus_fingerprint(rows: Iterable[Mapping[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: _text(item.get("unit_id"))):
        payload = {
            "unit_id": _text(row.get("unit_id")),
            "text": semantic_index_text(row),
        }
        digest.update(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        digest.update(b"\n")
    return digest.hexdigest()


def _retrieval_regression(
    *,
    provider: EmbeddingProvider,
    index_path: Path,
    metadata_path: Path,
    queries: Iterable[str],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    bundle = load_semantic_index(index_path, metadata_path)
    results: list[dict[str, Any]] = []
    for query in queries:
        query_vector = provider.embed_texts([query])
        ranked = _search_scores(bundle, query_vector, top_k)
        hits = [
            {
                "rank": rank,
                "unit_id": _text(bundle.metadata[vector_id].get("unit_id")),
                "record_id": _text(bundle.metadata[vector_id].get("record_id")),
                "score": round(float(score), 8),
            }
            for rank, (vector_id, score) in enumerate(ranked, start=1)
        ]
        results.append({"query": query, "hits": hits})
    return results


def build_semantic_index(
    provider_name: str | None = None,
    *,
    db_path: Path | str | None = None,
    index_path: Path | None = None,
    metadata_path: Path | None = None,
    regression_queries: Iterable[str] = DEFAULT_REGRESSION_QUERIES,
) -> dict[str, Any]:
    resolved_index_path = index_path or settings.SEMANTIC_FAISS_INDEX_PATH
    resolved_metadata_path = metadata_path or settings.SEMANTIC_FAISS_METADATA_PATH
    rows = fetch_all_retrieval_units(db_path)
    texts = [semantic_index_text(row) for row in rows]
    vectors, provider, effective_provider_name, embedding_model = _embed_texts(
        texts,
        provider_name,
    )

    if len(rows) != int(vectors.shape[0]):
        raise EmbeddingProviderError(
            f"Embedding count mismatch: expected {len(rows)}, got {vectors.shape[0]}."
        )

    index_backend = _write_faiss_or_numpy_index(vectors, resolved_index_path)
    _write_metadata(rows, resolved_metadata_path)
    regression_results = _retrieval_regression(
        provider=provider,
        index_path=resolved_index_path,
        metadata_path=resolved_metadata_path,
        queries=regression_queries,
    )

    stats = {
        "status": "ok",
        "retrieval_unit_count": len(rows),
        "embedding_provider": effective_provider_name,
        "embedding_model": embedding_model,
        "embedding_dimension": int(vectors.shape[1]) if vectors.ndim == 2 else 0,
        "corpus_fingerprint": corpus_fingerprint(rows),
        "index_backend": index_backend,
        "index_path": str(resolved_index_path),
        "metadata_path": str(resolved_metadata_path),
        "retrieval_regression": regression_results,
    }
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Build semantic retrieval index for qiaopi retrieval units.")
    parser.add_argument(
        "--provider",
        choices=["local", "qwen", "hash"],
        default=None,
        help="Override EMBEDDING_PROVIDER for this build. Use hash for deterministic local tests.",
    )
    args = parser.parse_args()
    stats = build_semantic_index(provider_name=args.provider)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
