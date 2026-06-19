from __future__ import annotations

import re
from typing import Any

from app.nlp.text_normalizer import NormalizedText, normalize_qiaopi_text_with_mapping


RELATION_RULE_VERSION = "qiaopi-relation-rules-1.0.0"
_REMITTANCE_RE = re.compile(r"寄上|汇上|奉上|付去|寄去|批款|查收|收讫|寄回")
_ORIGIN_RE = re.compile(r"在|由|从|旅居|侨居|僑居")
_DESTINATION_RE = re.compile(r"寄往|寄回|付往|汇往|回|往|至")
_SELF_CHILD_RE = re.compile(r"(?:^|[，,。；;\n])(?:小儿|儿|男|孩儿)[\u4e00-\u9fff]{0,6}")


def extract_relations(
    text: str,
    entities: list[dict[str, Any]],
    normalized: NormalizedText | None = None,
) -> list[dict[str, Any]]:
    if not text or not entities:
        return []
    bundle = normalized or normalize_qiaopi_text_with_mapping(text)
    relations: list[dict[str, Any]] = []

    sender = _first_entity(entities, "person", role="sender")
    recipient = _first_entity(entities, "person", role="recipient")
    kinship = _first_entity(entities, "kinship")
    target_person = recipient or kinship

    if sender and target_person:
        relations.append(
            _relation(
                bundle,
                relation_type="writes_to",
                source=sender,
                target=target_person,
                evidence_start=min(sender["normalized_start"], target_person["normalized_start"]),
                evidence_end=max(sender["normalized_end"], target_person["normalized_end"]),
                confidence=0.96,
                needs_review=False,
                rule_id="metadata_sender_recipient",
            )
        )

    if kinship and _SELF_CHILD_RE.search(bundle.normalized_text):
        child_match = _SELF_CHILD_RE.search(bundle.normalized_text)
        relations.append(
            _relation(
                bundle,
                relation_type="child_to_parent",
                source=sender or _virtual_entity("writer"),
                target=kinship,
                evidence_start=min(child_match.start(), kinship["normalized_start"]),
                evidence_end=max(child_match.end(), kinship["normalized_end"]),
                confidence=0.84,
                needs_review=False,
                rule_id="self_child_and_parent_kinship",
            )
        )

    for money in _entities_of_type(entities, "money"):
        sentence_start, sentence_end = _sentence_span(
            bundle.normalized_text,
            money["normalized_start"],
            money["normalized_end"],
        )
        sentence = bundle.normalized_text[sentence_start:sentence_end]
        if not _REMITTANCE_RE.search(sentence):
            continue
        relations.append(
            _relation(
                bundle,
                relation_type="remits_money_to",
                source=sender or _virtual_entity("writer"),
                target=target_person or _virtual_entity("recipient:unspecified"),
                evidence_start=sentence_start,
                evidence_end=sentence_end,
                confidence=0.9 if target_person else 0.68,
                needs_review=target_person is None,
                rule_id="remittance_verb_money",
                attributes={"money_entity_id": money["entity_id"]},
            )
        )

    for place in _entities_of_type(entities, "place"):
        context_start = max(0, place["normalized_start"] - 5)
        prefix = bundle.normalized_text[context_start : place["normalized_start"]]
        sentence_start, sentence_end = _sentence_span(
            bundle.normalized_text,
            place["normalized_start"],
            place["normalized_end"],
        )
        if _ORIGIN_RE.search(prefix):
            relations.append(
                _relation(
                    bundle,
                    relation_type="sent_from",
                    source=sender or _virtual_entity("writer"),
                    target=place,
                    evidence_start=sentence_start,
                    evidence_end=sentence_end,
                    confidence=0.82,
                    needs_review=False,
                    rule_id="origin_preposition_place",
                )
            )
        if _DESTINATION_RE.search(prefix):
            relations.append(
                _relation(
                    bundle,
                    relation_type="sent_to",
                    source=sender or _virtual_entity("writer"),
                    target=place,
                    evidence_start=sentence_start,
                    evidence_end=sentence_end,
                    confidence=0.82,
                    needs_review=False,
                    rule_id="destination_preposition_place",
                )
            )

    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, int, int]] = set()
    for relation in relations:
        key = (
            relation["relation_type"],
            relation["source_entity_id"],
            relation["target_entity_id"],
            relation["normalized_start"],
            relation["normalized_end"],
        )
        if key in seen:
            continue
        seen.add(key)
        relation["relation_id"] = f"REL-{len(unique) + 1:03d}"
        unique.append(relation)
    return unique


def _relation(
    bundle: NormalizedText,
    *,
    relation_type: str,
    source: dict[str, Any],
    target: dict[str, Any],
    evidence_start: int,
    evidence_end: int,
    confidence: float,
    needs_review: bool,
    rule_id: str,
    attributes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence_start, evidence_end = _sentence_span(
        bundle.normalized_text, evidence_start, evidence_end
    )
    original_start, original_end = bundle.original_span(evidence_start, evidence_end)
    return {
        "relation_id": "",
        "relation_type": relation_type,
        "source_entity_id": source["entity_id"],
        "source_value": source["value"],
        "target_entity_id": target["entity_id"],
        "target_value": target["value"],
        "source_text": bundle.original_text[original_start:original_end],
        "normalized_source_text": bundle.normalized_text[evidence_start:evidence_end],
        "evidence_text": bundle.original_text[original_start:original_end],
        "normalized_evidence_text": bundle.normalized_text[evidence_start:evidence_end],
        "original_start": original_start,
        "original_end": original_end,
        "normalized_start": evidence_start,
        "normalized_end": evidence_end,
        "extractor": "rule",
        "extractor_version": RELATION_RULE_VERSION,
        "rule_id": rule_id,
        "confidence": round(max(0.0, min(1.0, confidence)), 4),
        "needs_review": bool(needs_review),
        "attributes": attributes or {},
    }


def _first_entity(
    entities: list[dict[str, Any]],
    entity_type: str,
    *,
    role: str = "",
) -> dict[str, Any] | None:
    for entity in entities:
        if entity["entity_type"] != entity_type:
            continue
        if role and entity.get("attributes", {}).get("role") != role:
            continue
        return entity
    return None


def _entities_of_type(
    entities: list[dict[str, Any]], entity_type: str
) -> list[dict[str, Any]]:
    return [entity for entity in entities if entity["entity_type"] == entity_type]


def _virtual_entity(value: str) -> dict[str, Any]:
    return {"entity_id": value, "value": value}


def _sentence_span(text: str, start: int, end: int) -> tuple[int, int]:
    if not text:
        return 0, 0
    start = max(0, min(start, len(text)))
    end = max(start, min(end, len(text)))
    left = start
    while left > 0 and text[left - 1] not in "\n。！？!?；;":
        left -= 1
    right = end
    while right < len(text) and text[right] not in "\n。！？!?；;":
        right += 1
    if right < len(text):
        right += 1
    return left, right
