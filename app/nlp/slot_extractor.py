from __future__ import annotations

import re
from typing import Any

from app.nlp.text_normalizer import NormalizedText, normalize_qiaopi_text_with_mapping


SLOT_RULE_VERSION = "qiaopi-slot-rules-1.0.0"
_PURPOSE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("household_expenses", ("家用", "家中之用", "生活费", "买米", "米粮")),
    ("medical_expenses", ("医药", "药费", "买药", "治病", "疾病")),
    ("education", ("学费", "读书", "升学", "勤学")),
    ("debt_repayment", ("还债", "欠款", "债务", "赎回")),
    ("distribution", ("分抹", "分给", "交与")),
)


def extract_slots(
    text: str,
    entities: list[dict[str, Any]] | None = None,
    relations: list[dict[str, Any]] | None = None,
    normalized: NormalizedText | None = None,
) -> list[dict[str, Any]]:
    bundle = normalized or normalize_qiaopi_text_with_mapping(text)
    entity_rows = entities or []
    relation_rows = relations or []
    slots: list[dict[str, Any]] = []

    sender = _first_entity(entity_rows, "person", role="sender")
    recipient = _first_entity(entity_rows, "person", role="recipient") or _first_entity(
        entity_rows, "kinship"
    )
    money = _first_entity(entity_rows, "money")
    date = _first_entity(entity_rows, "date")
    origin = _place_for_relation(entity_rows, relation_rows, "sent_from")
    destination = _place_for_relation(entity_rows, relation_rows, "sent_to")

    for name, entity, confidence in (
        ("sender", sender, 0.96),
        ("recipient", recipient, 0.9),
        ("money", money, 0.92),
        ("date", date, date["confidence"] if date else 0.0),
        ("origin_place", origin, 0.82),
        ("destination_place", destination, 0.82),
    ):
        if entity:
            slots.append(_slot_from_entity(name, entity, confidence))

    if money:
        currency = money.get("attributes", {}).get("currency")
        if currency:
            slots.append(_slot_from_entity("currency", money, 0.9, value=currency))

    for purpose, keywords in _PURPOSE_RULES:
        match = next(
            (
                re.search(re.escape(keyword), bundle.normalized_text)
                for keyword in keywords
                if keyword in bundle.normalized_text
            ),
            None,
        )
        if match:
            slots.append(
                _slot(
                    bundle,
                    slot_name="purpose",
                    value=purpose,
                    normalized_start=match.start(),
                    normalized_end=match.end(),
                    confidence=0.84,
                    needs_review=False,
                    rule_id=f"purpose:{purpose}",
                )
            )

    relationship = next(
        (
            relation
            for relation in relation_rows
            if relation["relation_type"]
            in {
                "child_to_parent",
                "writes_to",
                "remits_money_to",
            }
        ),
        None,
    )
    if relationship:
        slots.append(
            {
                "slot_id": f"SLOT-{len(slots) + 1:03d}",
                "slot_name": "relationship_type",
                "value": relationship["relation_type"],
                "source_text": relationship["evidence_text"],
                "normalized_source_text": relationship["normalized_evidence_text"],
                "original_start": relationship["original_start"],
                "original_end": relationship["original_end"],
                "normalized_start": relationship["normalized_start"],
                "normalized_end": relationship["normalized_end"],
                "extractor": "rule",
                "extractor_version": SLOT_RULE_VERSION,
                "rule_id": "relation_to_slot",
                "confidence": relationship["confidence"],
                "needs_review": relationship["needs_review"],
            }
        )

    for index, slot in enumerate(slots, start=1):
        slot["slot_id"] = f"SLOT-{index:03d}"
    return slots


def _slot_from_entity(
    slot_name: str,
    entity: dict[str, Any],
    confidence: float,
    *,
    value: str | None = None,
) -> dict[str, Any]:
    return {
        "slot_id": "",
        "slot_name": slot_name,
        "value": value if value is not None else entity["value"],
        "source_text": entity["source_text"],
        "normalized_source_text": entity["normalized_source_text"],
        "original_start": entity["original_start"],
        "original_end": entity["original_end"],
        "normalized_start": entity["normalized_start"],
        "normalized_end": entity["normalized_end"],
        "extractor": "rule",
        "extractor_version": SLOT_RULE_VERSION,
        "rule_id": f"entity:{entity['entity_type']}",
        "confidence": round(min(confidence, entity["confidence"]), 4),
        "needs_review": bool(entity["needs_review"]),
    }


def _slot(
    bundle: NormalizedText,
    *,
    slot_name: str,
    value: str,
    normalized_start: int,
    normalized_end: int,
    confidence: float,
    needs_review: bool,
    rule_id: str,
) -> dict[str, Any]:
    original_start, original_end = bundle.original_span(normalized_start, normalized_end)
    return {
        "slot_id": "",
        "slot_name": slot_name,
        "value": value,
        "source_text": bundle.original_text[original_start:original_end],
        "normalized_source_text": bundle.normalized_text[normalized_start:normalized_end],
        "original_start": original_start,
        "original_end": original_end,
        "normalized_start": normalized_start,
        "normalized_end": normalized_end,
        "extractor": "rule",
        "extractor_version": SLOT_RULE_VERSION,
        "rule_id": rule_id,
        "confidence": confidence,
        "needs_review": needs_review,
    }


def _first_entity(
    entities: list[dict[str, Any]],
    entity_type: str,
    *,
    role: str = "",
) -> dict[str, Any] | None:
    return next(
        (
            entity
            for entity in entities
            if entity["entity_type"] == entity_type
            and (not role or entity.get("attributes", {}).get("role") == role)
        ),
        None,
    )


def _place_for_relation(
    entities: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    relation_type: str,
) -> dict[str, Any] | None:
    relation = next(
        (item for item in relations if item["relation_type"] == relation_type),
        None,
    )
    if relation:
        return next(
            (
                entity
                for entity in entities
                if entity["entity_id"] == relation["target_entity_id"]
            ),
            None,
        )
    return None
