from __future__ import annotations

from typing import Any, Iterable, Mapping

from app.search.query_expansion import QueryExpansion


UNIT_TYPE_BOOSTS: dict[str, float] = {
    "remittance": 1.6,
    "instruction": 1.5,
    "opening": 1.4,
    "style_reference": 1.4,
    "safety": 1.3,
    "family_care": 1.3,
    "body_core": 1.2,
    "rag_summary": 1.1,
    "record_full": 1.0,
    "closing": 0.8,
}

SIGNATURE_LIKE_SHORT_PHRASES = {
    "草",
    "谨禀",
    "叩上",
    "谨上",
    "敬上",
    "禀上",
    "手泐",
    "拜启",
    "顿",
    "字",
    "泐",
}

COVERAGE_FIELDS: tuple[tuple[str, str], ...] = (
    ("unit_text", "原文片段"),
    ("retrieval_keywords", "检索关键词"),
    ("theme_tags", "主题标签"),
    ("style_keywords", "风格词"),
    ("title_reference", "题名"),
)

UNIT_TYPE_REASON = {
    "remittance": "命中寄款片段",
    "instruction": "命中嘱咐片段",
    "opening": "命中开头称谓",
    "style_reference": "命中侨批风格样例",
    "safety": "命中平安问候",
    "family_care": "命中家人关怀",
    "body_core": "命中正文核心",
    "rag_summary": "命中RAG摘要",
    "record_full": "命中整条记录",
    "closing": "命中结尾署名",
}

CONCEPT_TERM_SETS: dict[str, tuple[str, ...]] = {
    "读书": ("读书", "勤读", "勤学", "学业", "书馆", "课程", "成绩", "温习"),
}


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _base_score(bm25_score: Any) -> float:
    try:
        score = float(bm25_score)
    except (TypeError, ValueError):
        score = 0.0
    return 1.0 / (1.0 + abs(score))


def _closing_penalty(unit_type: str, unit_text: str) -> float:
    clean_text = "".join(unit_text.split())
    if unit_type != "closing":
        return 1.0
    if len(clean_text) < 5:
        return 0.1
    if clean_text in SIGNATURE_LIKE_SHORT_PHRASES:
        return 0.15
    if len(clean_text) <= 8 and any(phrase in clean_text for phrase in SIGNATURE_LIKE_SHORT_PHRASES):
        return 0.25
    return 1.0


def _requested_type_boost(unit_type: str, requested_unit_types: set[str]) -> float:
    if not requested_unit_types:
        return 1.0
    return 1.08 if unit_type in requested_unit_types else 0.9


def _hit_terms(row: Mapping[str, Any], terms: Iterable[str]) -> list[str]:
    clean_terms = [term for term in terms if term]
    haystack = "\n".join(_text(row.get(field_name)) for field_name, _label in COVERAGE_FIELDS)
    return [term for term in clean_terms if term in haystack]


def _unit_text_hit_terms(row: Mapping[str, Any], terms: Iterable[str]) -> list[str]:
    clean_terms = [term for term in terms if term]
    unit_text = _text(row.get("unit_text"))
    return [term for term in clean_terms if term in unit_text]


def _matched_text(row: Mapping[str, Any], terms: Iterable[str]) -> str:
    clean_terms = [term for term in terms if term]
    for field_name, _label in COVERAGE_FIELDS:
        value = _text(row.get(field_name)).strip()
        if value and any(term in value for term in clean_terms):
            return value
    return _text(row.get("unit_text")).strip()


def _coverage(row: Mapping[str, Any], expansion: QueryExpansion) -> dict[str, Any]:
    original_term_set = set(expansion.original_terms)
    strong_terms = [term for term in expansion.strong_expansion_terms if term not in original_term_set]
    medium_terms = [term for term in expansion.medium_expansion_terms if term not in original_term_set]
    weak_terms = [term for term in expansion.weak_expansion_terms if term not in original_term_set]
    original_hits = _hit_terms(row, expansion.original_terms)
    strong_hits = _hit_terms(row, strong_terms)
    medium_hits = _hit_terms(row, medium_terms)
    weak_hits = _hit_terms(row, weak_terms)
    original_unit_hits = _unit_text_hit_terms(row, expansion.original_terms)
    strong_unit_hits = _unit_text_hit_terms(row, strong_terms)
    medium_unit_hits = _unit_text_hit_terms(row, medium_terms)
    weak_unit_hits = _unit_text_hit_terms(row, weak_terms)
    return {
        "original_hits": original_hits,
        "strong_hits": strong_hits,
        "medium_hits": medium_hits,
        "weak_hits": weak_hits,
        "original_unit_hits": original_unit_hits,
        "strong_unit_hits": strong_unit_hits,
        "medium_unit_hits": medium_unit_hits,
        "weak_unit_hits": weak_unit_hits,
        "original_hit_count": len(original_hits),
        "strong_hit_count": len(strong_hits),
        "medium_hit_count": len(medium_hits),
        "weak_hit_count": len(weak_hits),
    }


def _concept_focus_penalty(row: Mapping[str, Any], expansion: QueryExpansion) -> float:
    haystack = "\n".join(_text(row.get(field_name)) for field_name, _label in COVERAGE_FIELDS)
    penalty = 1.0
    for trigger, concept_terms in CONCEPT_TERM_SETS.items():
        if trigger in expansion.original_terms and not any(term in haystack for term in concept_terms):
            penalty *= 0.42
    return penalty


def _coverage_multiplier(row: Mapping[str, Any], coverage: Mapping[str, Any]) -> float:
    original_count = int(coverage["original_hit_count"])
    strong_count = int(coverage["strong_hit_count"])
    medium_count = int(coverage["medium_hit_count"])
    weak_count = int(coverage["weak_hit_count"])
    core_count = original_count + strong_count + medium_count
    unit_core_count = (
        len(coverage["original_unit_hits"])
        + len(coverage["strong_unit_hits"])
        + len(coverage["medium_unit_hits"])
    )
    unit_any_count = unit_core_count + len(coverage["weak_unit_hits"])

    if original_count + strong_count + medium_count + weak_count == 0:
        return 0.12

    multiplier = (
        1.0
        + original_count * 0.8
        + strong_count * 0.45
        + medium_count * 0.18
        + min(weak_count, 3) * 0.04
    )
    if core_count == 0 and weak_count > 0:
        multiplier *= 0.22
    elif original_count + strong_count == 0:
        multiplier *= 0.58

    if unit_core_count > 0:
        multiplier *= 1.35
    elif unit_any_count > 0:
        multiplier *= 0.8
    else:
        multiplier *= 0.62

    if _text(row.get("unit_type")) in {"remittance", "opening", "closing"} and unit_core_count == 0:
        multiplier *= 0.72

    return multiplier


def _format_terms(label: str, terms: list[str]) -> str | None:
    if not terms:
        return None
    return f"{label}命中“{'/'.join(terms[:5])}”"


def _matched_reason(
    row: Mapping[str, Any],
    coverage: Mapping[str, Any],
) -> str:
    unit_type = _text(row.get("unit_type"))
    unit_reason = UNIT_TYPE_REASON.get(unit_type, "命中检索单元")
    original_hits = coverage["original_hits"]
    strong_hits = coverage["strong_hits"]
    medium_hits = coverage["medium_hits"]
    weak_hits = coverage["weak_hits"]
    core_count = len(original_hits) + len(strong_hits) + len(medium_hits)

    if core_count == 0 and not weak_hits:
        return f"仅命中{unit_reason.replace('命中', '')}类型，未命中核心查询词"

    reason_parts = [unit_reason]
    for part in (
        _format_terms("原始查询", original_hits),
        _format_terms("强扩展", strong_hits),
        _format_terms("中扩展", medium_hits),
        _format_terms("弱扩展", weak_hits),
    ):
        if part:
            reason_parts.append(part)
    if core_count == 0 and weak_hits:
        reason_parts.append("未命中原始/强/中扩展核心词")
    return "；".join(reason_parts)


def rerank_units(
    rows: Iterable[Mapping[str, Any]],
    expansion: QueryExpansion,
    requested_unit_types: Iterable[str] | None = None,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    requested_types = {unit_type for unit_type in (requested_unit_types or []) if unit_type}
    all_terms = [
        *expansion.original_terms,
        *expansion.strong_expansion_terms,
        *expansion.medium_expansion_terms,
        *expansion.weak_expansion_terms,
    ]

    reranked_rows: list[dict[str, Any]] = []
    for row in rows:
        unit_type = _text(row.get("unit_type"))
        unit_text = _text(row.get("unit_text"))
        bm25_score = float(row.get("bm25_score", row.get("score", 0.0)) or 0.0)
        coverage = _coverage(row, expansion)
        final_score = (
            _base_score(bm25_score)
            * UNIT_TYPE_BOOSTS.get(unit_type, 1.0)
            * _requested_type_boost(unit_type, requested_types)
            * _closing_penalty(unit_type, unit_text)
            * _coverage_multiplier(row, coverage)
            * _concept_focus_penalty(row, expansion)
        )
        reranked_row = dict(row)
        reranked_row["bm25_score"] = bm25_score
        reranked_row["final_score"] = round(final_score, 8)
        reranked_row["matched_text"] = _matched_text(row, all_terms)
        reranked_row["matched_reason"] = _matched_reason(row, coverage)
        reranked_row["original_hit_count"] = coverage["original_hit_count"]
        reranked_row["strong_hit_count"] = coverage["strong_hit_count"]
        reranked_row["medium_hit_count"] = coverage["medium_hit_count"]
        reranked_row["weak_hit_count"] = coverage["weak_hit_count"]
        reranked_rows.append(reranked_row)

    return sorted(
        reranked_rows,
        key=lambda item: (
            -float(item.get("final_score") or 0.0),
            -(
                int(item.get("original_hit_count") or 0)
                + int(item.get("strong_hit_count") or 0)
                + int(item.get("medium_hit_count") or 0)
            ),
            -len(_text(item.get("unit_text"))),
            _text(item.get("unit_id")),
        ),
    )[:top_k]
