from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from app import settings
from app.database.repository import fetch_all_metadata_records
from app.ingestion.build_semantic_index import (
    _embed_texts,
    _text,
    _write_faiss_or_numpy_index,
)
from app.search.corpus_domains import (
    METADATA_CATALOG_DOMAIN,
    SEMANTIC_MANIFEST_VERSION,
    metadata_semantic_corpus_fingerprint,
    metadata_semantic_index_text,
    production_semantic_eligible,
    semantic_quality,
)


METADATA_FIELDS: tuple[str, ...] = (
    "metadata_id",
    "source_index",
    "title_clean",
    "sender_raw",
    "recipient_raw",
    "sender_name_clean",
    "recipient_name_clean",
    "date_text",
    "date_standard",
    "year_normalized",
    "origin_place",
    "destination_place",
    "place_mentions",
    "country_or_region",
    "remittance_raw",
    "amount_number",
    "currency",
    "has_remittance",
    "kinship_terms",
    "relationship_type",
    "theme_tags",
    "main_intent",
    "has_linked_text",
    "linked_record_id",
    "parse_confidence",
    "needs_review",
)


def _write_metadata(
    rows: list[Mapping[str, Any]],
    metadata_path: Path,
) -> None:
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with metadata_path.open("w", encoding="utf-8") as file:
        for vector_id, row in enumerate(rows):
            item: dict[str, Any] = {"vector_id": vector_id}
            for field_name in METADATA_FIELDS:
                value = row.get(field_name)
                if field_name in {
                    "source_index",
                    "has_remittance",
                    "has_linked_text",
                    "needs_review",
                }:
                    item[field_name] = int(value or 0)
                elif field_name in {"amount_number", "parse_confidence"}:
                    item[field_name] = float(value or 0.0)
                else:
                    item[field_name] = _text(value)
            file.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def build_metadata_semantic_index(
    provider_name: str | None = None,
    *,
    db_path: Path | str | None = None,
    index_path: Path | None = None,
    metadata_path: Path | None = None,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    resolved_index_path = index_path or settings.METADATA_SEMANTIC_FAISS_INDEX_PATH
    resolved_metadata_path = (
        metadata_path or settings.METADATA_SEMANTIC_FAISS_METADATA_PATH
    )
    resolved_manifest_path = (
        manifest_path or settings.METADATA_SEMANTIC_FAISS_MANIFEST_PATH
    )
    rows = fetch_all_metadata_records(db_path)
    texts = [metadata_semantic_index_text(row) for row in rows]
    vectors, _provider, effective_provider_name, embedding_model = _embed_texts(
        texts,
        provider_name,
    )
    if len(rows) != int(vectors.shape[0]):
        raise RuntimeError(
            f"Metadata embedding count mismatch: expected {len(rows)}, "
            f"got {vectors.shape[0]}."
        )

    index_backend = _write_faiss_or_numpy_index(vectors, resolved_index_path)
    _write_metadata(rows, resolved_metadata_path)
    fingerprint = metadata_semantic_corpus_fingerprint(rows)
    corpus_ids = [str(row.get("metadata_id") or "") for row in rows]
    manifest = {
        "manifest_version": SEMANTIC_MANIFEST_VERSION,
        "corpus_domain": METADATA_CATALOG_DOMAIN,
        "metadata_record_count": len(rows),
        "corpus_ids": corpus_ids,
        "embedding_provider": effective_provider_name,
        "embedding_model": embedding_model,
        "embedding_dimension": int(vectors.shape[1]),
        "corpus_fingerprint": fingerprint,
        "index_backend": index_backend,
        "semantic_quality": semantic_quality(effective_provider_name),
        "production_semantic_eligible": production_semantic_eligible(
            effective_provider_name
        ),
    }
    resolved_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "status": "ok",
        "metadata_record_count": len(rows),
        "embedding_provider": effective_provider_name,
        "embedding_model": embedding_model,
        "embedding_dimension": int(vectors.shape[1]),
        "corpus_domain": METADATA_CATALOG_DOMAIN,
        "corpus_fingerprint": fingerprint,
        "index_backend": index_backend,
        "index_path": str(resolved_index_path),
        "metadata_path": str(resolved_metadata_path),
        "manifest_path": str(resolved_manifest_path),
        "semantic_quality": manifest["semantic_quality"],
        "production_semantic_eligible": manifest["production_semantic_eligible"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build semantic index for the qiaopi metadata catalog."
    )
    parser.add_argument(
        "--provider",
        choices=["local", "qwen", "hash"],
        default=None,
    )
    args = parser.parse_args()
    print(
        json.dumps(
            build_metadata_semantic_index(provider_name=args.provider),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
