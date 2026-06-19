from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping


METADATA_CATALOG_DOMAIN = "metadata_catalog"
FULL_TEXT_EVIDENCE_DOMAIN = "full_text_evidence"
SEMANTIC_MANIFEST_VERSION = "2"
HASH_EMBEDDING_MODEL = "hash-sha256-char-v1"

SEMANTIC_INDEX_TEXT_FIELDS: tuple[str, ...] = (
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


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def semantic_index_text(row: Mapping[str, Any]) -> str:
    parts = [text(row.get(field_name)) for field_name in SEMANTIC_INDEX_TEXT_FIELDS]
    return "\n".join(part for part in parts if part)


def semantic_corpus_fingerprint(rows: Iterable[Mapping[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: text(item.get("unit_id"))):
        payload = {
            "unit_id": text(row.get("unit_id")),
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


def embedding_model_name(provider_name: str, settings_module: Any) -> str:
    provider = provider_name.strip().lower()
    if provider == "hash":
        return HASH_EMBEDDING_MODEL
    if provider == "qwen":
        return settings_module.QWEN_EMBEDDING_MODEL or ""
    return settings_module.EMBEDDING_MODEL


def semantic_quality(provider_name: str) -> str:
    return "test_hash" if provider_name.strip().lower() == "hash" else "production"


def production_semantic_eligible(provider_name: str) -> bool:
    return semantic_quality(provider_name) == "production"
