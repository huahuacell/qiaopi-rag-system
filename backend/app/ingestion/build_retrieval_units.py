from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any, Iterable, Mapping


UNIT_WEIGHTS: dict[str, float] = {
    "record_full": 1.0,
    "body_core": 1.2,
    "opening": 1.5,
    "safety": 1.4,
    "remittance": 1.5,
    "family_care": 1.4,
    "instruction": 1.5,
    "closing": 1.5,
    "style_reference": 1.5,
    "rag_summary": 1.3,
}

UNIT_SOURCE_COLUMNS: dict[str, tuple[str, ...]] = {
    "record_full": ("retrieval_text",),
    "body_core": ("body_core",),
    "opening": ("evidence_opening", "opening_salutation", "opening_formula"),
    "safety": ("evidence_safety", "safety_report"),
    "remittance": ("evidence_remittance", "remittance_statement"),
    "family_care": ("evidence_family_care", "family_care_statement"),
    "instruction": ("evidence_instruction", "instruction_statement"),
    "closing": ("evidence_closing", "closing_formula", "signature"),
    "style_reference": ("style_reference_text",),
    "rag_summary": ("rag_summary_text",),
}

EVIDENCE_TYPE_TO_UNIT_TYPE: dict[str, str] = {
    "opening": "opening",
    "safety": "safety",
    "remittance": "remittance",
    "family_care": "family_care",
    "instruction": "instruction",
    "closing": "closing",
}

RETRIEVAL_CONTEXT_FIELDS: tuple[str, ...] = (
    "retrieval_keywords",
    "theme_tags",
    "style_keywords",
    "title_reference",
    "sender",
    "recipient",
    "sender_name_clean",
    "recipient_name_clean",
    "place_mentions_normalized",
    "main_intent",
    "relationship_type",
)

SEPARATOR_PATTERN = re.compile(r"[\s\r\n\t；;，,、。！？!?：:（）()【】\[\]《》<>“”\"'‘’/|\\]+")

DOMAIN_EXPANSIONS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (
        ("母亲", "慈亲", "严亲", "双亲", "父母", "家母", "阿母", "阿妈", "阿嬷", "祖母"),
        ("母亲", "慈亲", "双亲"),
    ),
    (
        ("父亲", "严亲", "父母", "双亲", "家父"),
        ("父亲", "严亲", "双亲"),
    ),
    (
        ("寄上", "汇上", "寄下", "汇下", "批款", "大洋", "银元", "荷银", "港币", "查收", "收讫", "remittance"),
        ("寄款", "汇款", "批款", "查收"),
    ),
    (
        ("平安", "勿念", "毋念", "安好", "无恙", "safety", "safety_report"),
        ("平安", "勿念", "安好", "无恙"),
    ),
    (
        ("读书", "勤学", "念书", "入学", "study"),
        ("读书", "勤学"),
    ),
    (
        ("勤俭", "勤谨", "节俭", "持家", "务望", "嘱", "instruction"),
        ("勤俭", "持家", "嘱咐"),
    ),
    (
        ("身体", "保重", "病", "安康", "health"),
        ("身体", "保重", "安康"),
    ),
    (
        ("新加坡", "星洲", "叻", "叻坡", "石叻"),
        ("新加坡", "星洲", "叻坡"),
    ),
    (
        ("泰国", "暹罗", "暹"),
        ("泰国", "暹罗"),
    ),
    (
        ("越南", "安南", "西贡"),
        ("越南", "安南"),
    ),
    (
        ("慈亲", "膝下", "尊前", "大人", "敬禀"),
        ("慈亲", "膝下", "尊前", "大人"),
    ),
)


def _clean_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value != value:
        return ""
    return str(value).strip()


def _records(table: Any) -> list[dict[str, Any]]:
    if table is None:
        return []
    if hasattr(table, "to_dict"):
        return table.to_dict("records")
    return [dict(row) for row in table]


def _normalize_unit_text(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _dedupe_terms(terms: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped_terms: list[str] = []
    for term in terms:
        clean_term = term.strip()
        if not clean_term or clean_term in seen:
            continue
        seen.add(clean_term)
        deduped_terms.append(clean_term)
    return deduped_terms


def _domain_terms(text: str) -> list[str]:
    terms: list[str] = []
    for triggers, expansions in DOMAIN_EXPANSIONS:
        if any(trigger and trigger in text for trigger in triggers):
            terms.extend(expansions)
    return terms


def normalize_fts_text(*values: Any) -> str:
    combined = " ".join(_clean_value(value) for value in values if _clean_value(value))
    separated = SEPARATOR_PATTERN.sub(" ", combined)
    terms = separated.split()
    terms.extend(_domain_terms(combined))
    return " ".join(_dedupe_terms(terms))


def _metadata(record: Mapping[str, Any]) -> dict[str, str]:
    return {
        "title_reference": _clean_value(record.get("title_reference")),
        "sender": _clean_value(record.get("sender")),
        "recipient": _clean_value(record.get("recipient")),
        "date_text": _clean_value(record.get("date_text")),
        "main_intent": _clean_value(record.get("main_intent")),
        "theme_tags": _clean_value(record.get("theme_tags")),
        "style_keywords": _clean_value(record.get("style_keywords")),
        "relationship_type": _clean_value(record.get("relationship_type")),
        "place_mentions_normalized": _clean_value(record.get("place_mentions_normalized")),
        "retrieval_keywords": _clean_value(record.get("retrieval_keywords")),
    }


def _raw_json(data: Mapping[str, Any]) -> str:
    clean_data = {key: _clean_value(value) for key, value in data.items()}
    return json.dumps(clean_data, ensure_ascii=False, sort_keys=True)


def _unit_id(record_id: str, unit_type: str, sequence: int) -> str:
    return f"{record_id}-RU-{unit_type.upper().replace('_', '-')}-{sequence:03d}"


def _make_unit(
    *,
    record: Mapping[str, Any],
    record_id: str,
    unit_type: str,
    source_column: str,
    unit_text: str,
    evidence_type: str,
    sequence: int,
    raw_source: Mapping[str, Any],
) -> dict[str, Any]:
    metadata = _metadata(record)
    fts_context = [
        unit_text,
        *(_clean_value(record.get(field)) for field in RETRIEVAL_CONTEXT_FIELDS),
    ]
    return {
        "unit_id": _unit_id(record_id, unit_type, sequence),
        "record_id": record_id,
        "unit_type": unit_type,
        "source_column": source_column,
        "unit_text": unit_text,
        **metadata,
        "weight": UNIT_WEIGHTS[unit_type],
        "evidence_type": evidence_type,
        "fts_text": normalize_fts_text(*fts_context),
        "raw_json": _raw_json(raw_source),
    }


def _group_evidence_spans(
    evidence_spans: Any,
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for evidence in _records(evidence_spans):
        record_id = _clean_value(evidence.get("record_id"))
        if record_id:
            grouped[record_id].append(evidence)
    return grouped


def build_retrieval_units(
    wide_records: Any,
    evidence_spans: Any | None = None,
) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    evidence_by_record = _group_evidence_spans(evidence_spans)

    for record in _records(wide_records):
        record_id = _clean_value(record.get("record_id"))
        if not record_id:
            continue

        seen_by_type: dict[str, set[str]] = defaultdict(set)
        sequence_by_type: dict[str, int] = defaultdict(int)

        for unit_type, source_columns in UNIT_SOURCE_COLUMNS.items():
            for source_column in source_columns:
                unit_text = _clean_value(record.get(source_column))
                if not unit_text:
                    continue
                normalized_text = _normalize_unit_text(unit_text)
                if normalized_text in seen_by_type[unit_type]:
                    continue
                seen_by_type[unit_type].add(normalized_text)
                sequence_by_type[unit_type] += 1
                units.append(
                    _make_unit(
                        record=record,
                        record_id=record_id,
                        unit_type=unit_type,
                        source_column=source_column,
                        unit_text=unit_text,
                        evidence_type=unit_type,
                        sequence=sequence_by_type[unit_type],
                        raw_source={
                            "record_id": record_id,
                            "unit_type": unit_type,
                            "source_column": source_column,
                            "source_text": unit_text,
                        },
                    )
                )

        for evidence in evidence_by_record.get(record_id, []):
            evidence_type = _clean_value(evidence.get("evidence_type"))
            unit_type = EVIDENCE_TYPE_TO_UNIT_TYPE.get(evidence_type)
            if not unit_type:
                continue
            unit_text = _clean_value(evidence.get("evidence_text"))
            if not unit_text:
                continue
            normalized_text = _normalize_unit_text(unit_text)
            if normalized_text in seen_by_type[unit_type]:
                continue
            seen_by_type[unit_type].add(normalized_text)
            sequence_by_type[unit_type] += 1
            units.append(
                _make_unit(
                    record=record,
                    record_id=record_id,
                    unit_type=unit_type,
                    source_column=_clean_value(evidence.get("source_column")) or "qiaopi_evidence_spans",
                    unit_text=unit_text,
                    evidence_type=evidence_type,
                    sequence=sequence_by_type[unit_type],
                    raw_source={
                        "record_id": record_id,
                        "unit_type": unit_type,
                        "evidence_id": _clean_value(evidence.get("evidence_id")),
                        "evidence_type": evidence_type,
                        "source_column": _clean_value(evidence.get("source_column")),
                        "source_text": unit_text,
                        "start_char": _clean_value(evidence.get("start_char")),
                        "end_char": _clean_value(evidence.get("end_char")),
                    },
                )
            )

    return units
