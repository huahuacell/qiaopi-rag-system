from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from app import settings
from app.database.repository import fetch_all_retrieval_units
from app.embedding.embedding_provider import (
    EmbeddingProviderError,
    get_embedding_provider,
)


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


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def semantic_index_text(row: Mapping[str, Any]) -> str:
    parts = [_text(row.get(field_name)) for field_name in INDEX_TEXT_FIELDS]
    return "\n".join(part for part in parts if part)


def _batched(values: list[str], batch_size: int) -> Iterable[list[str]]:
    safe_batch_size = max(1, batch_size)
    for start in range(0, len(values), safe_batch_size):
        yield values[start : start + safe_batch_size]


def _embed_texts(texts: list[str], provider_name: str | None) -> tuple[np.ndarray, str]:
    effective_provider_name = provider_name or settings.EMBEDDING_PROVIDER
    try:
        provider = get_embedding_provider(effective_provider_name)
    except EmbeddingProviderError:
        if (effective_provider_name or "").strip().lower() != "local":
            raise
        provider = get_embedding_provider("hash")
        effective_provider_name = "hash"

    batches: list[np.ndarray] = []
    for batch in _batched(texts, settings.EMBEDDING_BATCH_SIZE):
        batches.append(provider.embed_texts(batch))
    if not batches:
        return np.zeros((0, settings.EMBEDDING_DIM or 384), dtype=np.float32), effective_provider_name
    return np.vstack(batches).astype(np.float32), effective_provider_name


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


def build_semantic_index(provider_name: str | None = None) -> dict[str, Any]:
    rows = fetch_all_retrieval_units()
    texts = [semantic_index_text(row) for row in rows]
    vectors, effective_provider_name = _embed_texts(texts, provider_name)

    if len(rows) != int(vectors.shape[0]):
        raise EmbeddingProviderError(
            f"Embedding count mismatch: expected {len(rows)}, got {vectors.shape[0]}."
        )

    index_backend = _write_faiss_or_numpy_index(vectors, settings.SEMANTIC_FAISS_INDEX_PATH)
    _write_metadata(rows, settings.SEMANTIC_FAISS_METADATA_PATH)

    stats = {
        "status": "ok",
        "retrieval_unit_count": len(rows),
        "embedding_provider": effective_provider_name,
        "embedding_dimension": int(vectors.shape[1]) if vectors.ndim == 2 else 0,
        "index_backend": index_backend,
        "index_path": str(settings.SEMANTIC_FAISS_INDEX_PATH),
        "metadata_path": str(settings.SEMANTIC_FAISS_METADATA_PATH),
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
