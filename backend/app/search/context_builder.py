from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Iterable, Mapping

from app.database.repository import fetch_retrieval_units
from app.search.hybrid_retriever import retrieve_hybrid
from app.search.keyword_retriever import retrieve_keyword
from app.search.query_expansion import expand_query, terms_for_expansion_mode
from app.search.result_aggregator import group_results_by_record
from app.search.semantic_retriever import semantic_search


RAG_UNIT_TYPES: tuple[str, ...] = (
    "body_core",
    "remittance",
    "family_care",
    "instruction",
    "rag_summary",
)

RECORD_CONTEXT_UNIT_TYPES: tuple[str, ...] = (
    "body_core",
    "remittance",
    "family_care",
    "instruction",
    "safety",
    "opening",
    "closing",
    "rag_summary",
    "style_reference",
    "record_full",
)

STYLE_SLOT_TYPES: tuple[str, ...] = (
    "opening",
    "safety",
    "remittance",
    "family_care",
    "instruction",
    "closing",
    "style_reference",
)

STYLE_SLOT_LABELS: dict[str, str] = {
    "opening": "开头称谓样例",
    "safety": "报平安样例",
    "remittance": "寄款表达样例",
    "family_care": "问候保重样例",
    "instruction": "嘱托表达样例",
    "closing": "结尾署名样例",
    "style_reference": "综合风格参考",
}

CONTEXT_HINT_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("母亲", "妈妈", "阿母", "阿妈", "阿嬷", "祖母"), ("母亲",)),
    (("父亲", "爸爸", "阿爸", "双亲", "父母"), ("父亲",)),
    (("平安", "安好", "无恙", "勿念", "毋念"), ("平安",)),
    (("寄款", "汇款", "寄", "钱", "元", "银", "款"), ("寄款",)),
    (("查收", "收讫", "收用", "检收"), ("查收",)),
    (("读书", "学习", "勤奋", "勤学", "学业"), ("读书",)),
    (("保重", "身体", "安康", "调养"), ("保重",)),
    (("新加坡", "星洲", "叻坡", "石叻"), ("新加坡",)),
)

STYLE_HINT_RULES: tuple[tuple[tuple[str, ...], str, tuple[str, ...]], ...] = (
    (("母亲", "妈妈", "阿母", "阿妈", "阿嬷"), "opening", ("慈亲", "母亲", "大人", "膝下")),
    (("平安", "安好", "无恙", "勿念", "毋念"), "safety", ("平安", "安好", "无恙", "勿念")),
    (("寄", "钱", "元", "汇款", "寄款", "银"), "remittance", ("寄款", "汇款", "批款", "查收")),
    (("读书", "学习", "勤奋", "勤学"), "instruction", ("读书", "勤学", "学业", "务望")),
    (("保重", "身体", "安康", "调养"), "family_care", ("保重", "身体", "安康", "调养")),
)

STYLE_SLOT_FALLBACK_TERMS: dict[str, tuple[str, ...]] = {
    "opening": ("慈亲", "大人", "膝下"),
    "safety": ("平安", "安好", "无恙"),
    "remittance": ("寄款", "批款", "查收"),
    "family_care": ("保重", "身体", "安康"),
    "instruction": ("读书", "勤学", "务望"),
    "closing": ("谨上", "叩上", "敬上"),
    "style_reference": ("侨批", "风格", "慈亲", "平安", "寄款"),
}

RECORD_CONTEXT_PRIORITY: dict[str, float] = {
    "body_core": 2.0,
    "remittance": 1.9,
    "family_care": 1.7,
    "instruction": 1.7,
    "safety": 1.5,
    "rag_summary": 1.4,
    "opening": 1.2,
    "closing": 1.1,
    "style_reference": 0.9,
    "record_full": 0.8,
}

WHITESPACE_PATTERN = re.compile(r"\s+")


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _normalize_unit_text(text: str) -> str:
    return WHITESPACE_PATTERN.sub("", text)


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped_values: list[str] = []
    for value in values:
        clean_value = value.strip()
        if not clean_value or clean_value in seen:
            continue
        seen.add(clean_value)
        deduped_values.append(clean_value)
    return deduped_values


def _detected_context_terms(query: str) -> list[str]:
    terms: list[str] = []
    for triggers, hints in CONTEXT_HINT_RULES:
        if any(trigger in query for trigger in triggers):
            terms.extend(hints)
    return _dedupe(terms)


def _query_with_context_hints(query: str) -> str:
    terms = _detected_context_terms(query)
    return " ".join(_dedupe([query, *terms]))


def _style_hints_for_slot(query: str, slot_type: str) -> list[str]:
    terms: list[str] = []
    for triggers, target_slot, hints in STYLE_HINT_RULES:
        if target_slot == slot_type and any(trigger in query for trigger in triggers):
            terms.extend(hints)
    return _dedupe(terms)


def _style_base_query(query: str) -> str:
    terms = _detected_context_terms(query)
    for triggers, _slot_type, hints in STYLE_HINT_RULES:
        if any(trigger in query for trigger in triggers):
            terms.extend(hints)
    return " ".join(_dedupe([query, *terms]))


def _style_query_for_slot(query: str, slot_type: str) -> str:
    terms = [
        query,
        *_detected_context_terms(query),
        *_style_hints_for_slot(query, slot_type),
        *STYLE_SLOT_FALLBACK_TERMS.get(slot_type, ()),
    ]
    return " ".join(_dedupe(terms))


def _matches_context_filters(row: Mapping[str, Any], filters: Mapping[str, Any]) -> bool:
    if not filters:
        return True
    for key, value in filters.items():
        if value in (None, "", []):
            continue
        row_value = _text(row.get(key))
        if key in {"unit_type", "evidence_type", "source_column", "main_intent"} and row_value != str(value):
            return False
        if key == "unit_types":
            values = {str(item) for item in value}
            if _text(row.get("unit_type")) not in values:
                return False
    return True


def _select_units(
    rows: list[dict[str, Any]],
    top_k: int,
    *,
    preferred_unit_types: Iterable[str] | None = None,
    max_per_record: int = 2,
) -> list[dict[str, Any]]:
    preferred_set = {unit_type for unit_type in (preferred_unit_types or []) if unit_type}
    preferred_rows = [row for row in rows if _text(row.get("unit_type")) in preferred_set]
    first_pass_rows = preferred_rows if preferred_rows else rows

    selected_rows: list[dict[str, Any]] = []
    seen_texts: set[str] = set()
    record_counts: dict[str, int] = defaultdict(int)

    def try_add(row: dict[str, Any], *, enforce_record_cap: bool) -> None:
        if len(selected_rows) >= top_k:
            return
        unit_text = _text(row.get("unit_text"))
        normalized_text = _normalize_unit_text(unit_text)
        if not normalized_text or normalized_text in seen_texts:
            return
        record_id = _text(row.get("record_id"))
        if enforce_record_cap and record_id and record_counts[record_id] >= max_per_record:
            return
        seen_texts.add(normalized_text)
        if record_id:
            record_counts[record_id] += 1
        selected_rows.append(row)

    for row in first_pass_rows:
        try_add(row, enforce_record_cap=True)
    for row in rows:
        try_add(row, enforce_record_cap=True)
    for row in first_pass_rows:
        try_add(row, enforce_record_cap=False)
    for row in rows:
        try_add(row, enforce_record_cap=False)

    return selected_rows


def _rag_context_item(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "record_id": _text(row.get("record_id")),
        "unit_id": _text(row.get("unit_id")),
        "unit_type": _text(row.get("unit_type")),
        "title_reference": _text(row.get("title_reference")),
        "sender": _text(row.get("sender")),
        "recipient": _text(row.get("recipient")),
        "date_text": _text(row.get("date_text")),
        "main_intent": _text(row.get("main_intent")),
        "unit_text": _text(row.get("unit_text")),
        "source_column": _text(row.get("source_column")),
        "evidence_type": _text(row.get("evidence_type")),
        "matched_reason": _text(row.get("matched_reason")),
        "final_score": _float(row.get("final_score")),
    }


def _style_slot_example(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "record_id": _text(row.get("record_id")),
        "unit_id": _text(row.get("unit_id")),
        "unit_type": _text(row.get("unit_type")),
        "title_reference": _text(row.get("title_reference")),
        "unit_text": _text(row.get("unit_text")),
        "source_column": _text(row.get("source_column")),
        "evidence_type": _text(row.get("evidence_type")),
        "matched_reason": _text(row.get("matched_reason")),
        "final_score": _float(row.get("final_score")),
    }


def _expanded_query(query: str, expansion_mode: str) -> tuple[str, str]:
    expansion = expand_query(query)
    mode = expansion_mode if expansion_mode in {"strict", "balanced", "broad"} else "balanced"
    return (
        expansion.normalized_query,
        " ".join(terms_for_expansion_mode(expansion, mode)),
    )


def _build_rag_prompt_context(query: str, contexts: list[dict[str, Any]]) -> str:
    parts = ["【检索问题】", query.strip()]
    if not contexts:
        parts.extend(["", "【相关侨批证据】", "暂无可用证据。"])
        return "\n".join(parts)

    for index, context in enumerate(contexts, start=1):
        parts.extend(
            [
                "",
                f"【相关侨批证据 {index}】",
                f"来源记录：{context['record_id']}",
                f"题名：{context['title_reference']}",
                f"寄批人：{context['sender']}",
                f"收批人：{context['recipient']}",
                f"日期：{context['date_text']}",
                f"证据类型：{context['evidence_type'] or context['unit_type']}",
                f"来源字段：{context['source_column']}",
                f"原文片段：{context['unit_text']}",
            ]
        )
    return "\n".join(parts)


def _record_context_rows(record_id: str, filters: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in fetch_retrieval_units(record_id):
        unit_type = _text(row.get("unit_type"))
        if unit_type not in RECORD_CONTEXT_UNIT_TYPES:
            continue
        if not _matches_context_filters(row, filters):
            continue
        prepared_row = dict(row)
        prepared_row["bm25_score"] = 0.0
        prepared_row["final_score"] = round(
            RECORD_CONTEXT_PRIORITY.get(unit_type, 1.0) * float(row.get("weight") or 1.0),
            8,
        )
        prepared_row["matched_reason"] = f"来自指定记录的{unit_type}检索单元"
        prepared_row["original_hit_count"] = 0
        prepared_row["strong_hit_count"] = 0
        prepared_row["medium_hit_count"] = 0
        prepared_row["weak_hit_count"] = 0
        rows.append(prepared_row)
    return sorted(
        rows,
        key=lambda item: (
            -float(item.get("final_score") or 0.0),
            _text(item.get("unit_id")),
        ),
    )


def _build_style_prompt_context(
    query: str,
    style_slots: Mapping[str, list[dict[str, Any]]],
) -> str:
    parts = ["【用户白话输入】", query.strip()]
    for slot_type in STYLE_SLOT_TYPES:
        parts.extend(["", f"【{STYLE_SLOT_LABELS[slot_type]}】"])
        examples = style_slots.get(slot_type, [])
        if not examples:
            parts.append("暂无可用样例。")
            continue
        for index, example in enumerate(examples, start=1):
            parts.extend(
                [
                    f"{index}. {example['unit_text']}",
                    f"来源：{example['record_id']}",
                ]
            )
    return "\n".join(parts)


def build_rag_context(
    *,
    query: str,
    top_k: int,
    unit_types: list[str],
    filters: Mapping[str, Any],
    expansion_mode: str,
    retrieval_mode: str = "hybrid",
) -> dict[str, Any]:
    retrieval_query = _query_with_context_hints(query)
    requested_unit_types = [unit_type for unit_type in unit_types if unit_type] or list(RAG_UNIT_TYPES)
    mode = retrieval_mode if retrieval_mode in {"keyword", "semantic", "hybrid"} else "hybrid"
    retrieval_limit = max(20, top_k * 4)
    semantic_enabled = False
    if mode == "semantic":
        semantic_result = semantic_search(
            query=retrieval_query,
            top_k=retrieval_limit,
            unit_types=requested_unit_types,
            filters=filters,
        )
        if semantic_result.get("semantic_enabled") and semantic_result.get("results"):
            retrieval_result = {
                "results": semantic_result["results"],
                "expansion_mode": expansion_mode if expansion_mode in {"strict", "balanced", "broad"} else "balanced",
            }
            semantic_enabled = True
        else:
            retrieval_result = retrieve_keyword(
                query=retrieval_query,
                top_k=retrieval_limit,
                unit_types=requested_unit_types,
                filters=filters,
                expansion_mode=expansion_mode,
            )
    elif mode == "hybrid":
        retrieval_result = retrieve_hybrid(
            query=retrieval_query,
            top_k=retrieval_limit,
            unit_types=requested_unit_types,
            filters=filters,
            expansion_mode=expansion_mode,
        )
        semantic_enabled = bool(retrieval_result.get("semantic_enabled", False))
    else:
        retrieval_result = retrieve_keyword(
            query=retrieval_query,
            top_k=retrieval_limit,
            unit_types=requested_unit_types,
            filters=filters,
            expansion_mode=expansion_mode,
        )
    selected_rows = _select_units(
        retrieval_result["results"],
        top_k,
        preferred_unit_types=RAG_UNIT_TYPES,
        max_per_record=2,
    )
    contexts = [_rag_context_item(row) for row in selected_rows]
    normalized_query, expanded_query = _expanded_query(retrieval_query, retrieval_result["expansion_mode"])
    source_record_ids = {context["record_id"] for context in contexts if context["record_id"]}
    return {
        "query": query,
        "normalized_query": normalized_query,
        "expanded_query": expanded_query,
        "expansion_mode": retrieval_result["expansion_mode"],
        "semantic_enabled": semantic_enabled,
        "contexts": contexts,
        "grouped_contexts": group_results_by_record(selected_rows),
        "prompt_context": _build_rag_prompt_context(query, contexts),
        "evidence_count": len(contexts),
        "source_record_count": len(source_record_ids),
    }


def build_record_rag_context(
    *,
    query: str,
    record_id: str,
    top_k: int,
    filters: Mapping[str, Any],
    expansion_mode: str,
) -> dict[str, Any]:
    retrieval_query = _query_with_context_hints(query)
    rows = _record_context_rows(record_id, filters)
    selected_rows = _select_units(
        rows,
        top_k,
        preferred_unit_types=RAG_UNIT_TYPES,
        max_per_record=top_k,
    )
    contexts = [_rag_context_item(row) for row in selected_rows]
    normalized_query, expanded_query = _expanded_query(retrieval_query, expansion_mode)
    source_record_ids = {context["record_id"] for context in contexts if context["record_id"]}
    return {
        "query": query,
        "normalized_query": normalized_query,
        "expanded_query": expanded_query,
        "expansion_mode": expansion_mode if expansion_mode in {"strict", "balanced", "broad"} else "balanced",
        "semantic_enabled": False,
        "contexts": contexts,
        "grouped_contexts": group_results_by_record(selected_rows),
        "prompt_context": _build_rag_prompt_context(query, contexts),
        "evidence_count": len(contexts),
        "source_record_count": len(source_record_ids),
    }


def build_style_context(
    *,
    query: str,
    top_k: int,
    filters: Mapping[str, Any],
    expansion_mode: str,
) -> dict[str, Any]:
    style_slots: dict[str, list[dict[str, Any]]] = {}
    selected_rows_by_slot: dict[str, list[dict[str, Any]]] = {}
    all_selected_rows: list[dict[str, Any]] = []

    for slot_type in STYLE_SLOT_TYPES:
        retrieval_result = retrieve_keyword(
            query=_style_query_for_slot(query, slot_type),
            top_k=max(10, top_k * 4),
            unit_types=[slot_type],
            filters=filters,
            expansion_mode=expansion_mode,
        )
        selected_rows = _select_units(
            retrieval_result["results"],
            top_k,
            preferred_unit_types=[slot_type],
            max_per_record=1,
        )
        selected_rows_by_slot[slot_type] = selected_rows
        all_selected_rows.extend(selected_rows)
        style_slots[slot_type] = [_style_slot_example(row) for row in selected_rows]

    normalized_query, expanded_query = _expanded_query(_style_base_query(query), expansion_mode)
    source_record_ids = {
        _text(row.get("record_id"))
        for rows in selected_rows_by_slot.values()
        for row in rows
        if _text(row.get("record_id"))
    }
    return {
        "query": query,
        "normalized_query": normalized_query,
        "expanded_query": expanded_query,
        "expansion_mode": expansion_mode if expansion_mode in {"strict", "balanced", "broad"} else "balanced",
        "semantic_enabled": False,
        "style_slots": style_slots,
        "grouped_contexts": group_results_by_record(all_selected_rows),
        "prompt_context": _build_style_prompt_context(query, style_slots),
        "source_record_count": len(source_record_ids),
    }
