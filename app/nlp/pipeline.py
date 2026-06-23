from __future__ import annotations

from typing import Any

from app.nlp.entity_extractor import ENTITY_RULE_VERSION, extract_entities
from app.nlp.relation_extractor import RELATION_RULE_VERSION, extract_relations
from app.nlp.slot_extractor import SLOT_RULE_VERSION, extract_slots
from app.nlp.text_normalizer import (
    NORMALIZATION_VERSION,
    normalize_qiaopi_text_with_mapping,
)


NLP_PIPELINE_VERSION = "qiaopi-online-nlp-1.0.0"
_UNCERTAINTY_MARKERS = ("□", "�", "缺字", "待校", "无法辨识", "疑为", "未辨", "不清")


def analyze_qiaopi_text(text: str, task: str = "general") -> dict[str, Any]:
    normalized = normalize_qiaopi_text_with_mapping(text)
    entities = extract_entities(text, normalized)
    relations = extract_relations(text, entities, normalized)
    slots = extract_slots(text, entities, relations, normalized)

    uncertain_markers = [
        marker for marker in _UNCERTAINTY_MARKERS if marker in normalized.normalized_text
    ]
    review_items = [
        item
        for item in [*entities, *relations, *slots]
        if item.get("needs_review")
    ]
    review_reasons: list[str] = []
    if uncertain_markers:
        review_reasons.append(
            f"原文含不确定字符或复核标记：{'、'.join(uncertain_markers)}"
        )
    if review_items:
        review_reasons.append(f"{len(review_items)} 个抽取项低置信或需要规则复核")
    if not entities:
        review_reasons.append("未抽取到实体")

    return {
        "task": task,
        "original_text": normalized.original_text,
        "normalized_text": normalized.normalized_text,
        "normalization_changed": normalized.original_text != normalized.normalized_text,
        "normalization_version": NORMALIZATION_VERSION,
        "pipeline_version": NLP_PIPELINE_VERSION,
        "engine": "deterministic_rule",
        "entity_extractor_version": ENTITY_RULE_VERSION,
        "relation_extractor_version": RELATION_RULE_VERSION,
        "slot_extractor_version": SLOT_RULE_VERSION,
        "entities": entities,
        "relations": relations,
        "slots": slots,
        "review_required": bool(review_reasons),
        "review_reasons": review_reasons,
        "summary": {
            "entity_count": len(entities),
            "relation_count": len(relations),
            "slot_count": len(slots),
            "review_item_count": len(review_items),
        },
    }
