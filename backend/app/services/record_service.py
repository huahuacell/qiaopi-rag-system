from __future__ import annotations

import json
from typing import Any

from app.database.repository import (
    fetch_amount_mentions,
    fetch_entity_mentions,
    fetch_evidence_spans,
    fetch_place_mentions,
    fetch_retrieval_units,
    fetch_text_record,
)


def _raw_fields(record: dict[str, Any]) -> dict[str, Any]:
    raw_json = record.get("raw_json") or "{}"
    try:
        value = json.loads(raw_json)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _int_flag(value: Any) -> int:
    if value is None or value == "":
        return 0
    return int(value)


def get_record_detail(record_id: str) -> dict[str, Any] | None:
    record = fetch_text_record(record_id)
    if not record:
        return None
    return {
        "record_id": record.get("record_id", ""),
        "title_reference": record.get("title_reference", ""),
        "sender": record.get("sender", ""),
        "recipient": record.get("recipient", ""),
        "sender_name_clean": record.get("sender_name_clean", ""),
        "recipient_name_clean": record.get("recipient_name_clean", ""),
        "date_text": record.get("date_text", ""),
        "year_normalized": record.get("year_normalized", ""),
        "body_clean": record.get("body_clean", ""),
        "body_core": record.get("body_core", ""),
        "main_intent": record.get("main_intent", ""),
        "theme_tags": record.get("theme_tags", ""),
        "text_quality_level": record.get("text_quality_level", ""),
        "has_full_text": _int_flag(record.get("has_full_text")),
        "has_remittance": _int_flag(record.get("has_remittance")),
        "relationship_type": record.get("relationship_type", ""),
        "place_mentions_normalized": record.get("place_mentions_normalized", ""),
        "retrieval_keywords": record.get("retrieval_keywords", ""),
        "rag_summary_text": record.get("rag_summary_text", ""),
        "style_reference_text": record.get("style_reference_text", ""),
        "raw_fields": _raw_fields(record),
    }


def get_record_amounts(record_id: str) -> list[dict[str, Any]] | None:
    if not fetch_text_record(record_id):
        return None
    return fetch_amount_mentions(record_id)


def get_record_entities(record_id: str) -> list[dict[str, Any]] | None:
    if not fetch_text_record(record_id):
        return None
    entities = []
    for entity in fetch_entity_mentions(record_id):
        entity_text = entity.get("entity_text", "")
        normalized_text = entity.get("normalized_text", "")
        entities.append(
            {
                "mention_id": entity.get("mention_id"),
                "record_id": entity.get("record_id"),
                "entity_type": entity.get("entity_type", ""),
                "value": normalized_text or entity_text,
                "source_text": entity_text,
                "normalized_text": normalized_text,
                "source_field": entity.get("source_field", ""),
                "confidence": entity.get("confidence"),
            }
        )
    return entities


def get_record_places(record_id: str) -> list[dict[str, Any]] | None:
    if not fetch_text_record(record_id):
        return None
    return fetch_place_mentions(record_id)


def get_record_evidence(record_id: str) -> list[dict[str, Any]] | None:
    if not fetch_text_record(record_id):
        return None
    return fetch_evidence_spans(record_id)


def get_record_retrieval_units(record_id: str) -> list[dict[str, Any]] | None:
    if not fetch_text_record(record_id):
        return None
    return fetch_retrieval_units(record_id)
