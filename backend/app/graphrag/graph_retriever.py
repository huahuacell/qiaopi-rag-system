from __future__ import annotations

import json
import math
import sqlite3
from collections import defaultdict
from typing import Any, Iterable, Mapping

from app import settings
from app.database.connection import get_readonly_connection
from app.database.repository import (
    fetch_retrieval_units_for_records,
    matches_retrieval_filters,
)
from app.search.hybrid_retriever import retrieve_hybrid
from app.search.query_expansion import QueryExpansion, expand_query
from app.search.reranker import rerank_units
from app.search.result_aggregator import group_results_by_record


RRF_K = 60
GRAPH_RRF_WEIGHT = 1.2
GRAPH_SCORE_BONUS = 0.014
MAX_SEEDS = 8
MAX_PATHS_PER_RESULT = 4
TOTAL_FULL_TEXT_RECORDS = 213

GRAPH_QUERY_ALIASES: dict[str, tuple[str, ...]] = {
    "person:母亲": ("母亲", "妈妈", "阿母", "阿妈", "慈亲", "慈母", "娘亲"),
    "person:父亲": ("父亲", "爸爸", "阿爸", "严亲", "严父"),
    "person:祖母": ("祖母", "阿嬷", "阿嫲", "奶奶", "祖慈"),
    "person:祖父": ("祖父", "阿公", "爷爷"),
    "person:妻子": ("妻子", "吾妻", "贤妻", "爱妻", "内人"),
    "person:弟弟": ("弟弟", "阿弟", "胞弟", "贤弟", "吾弟"),
    "person:兄长": ("兄长", "哥哥", "阿兄", "胞兄", "吾兄"),
    "person:姐姐": ("姐姐", "姊姊", "阿姊"),
    "person:妹妹": ("妹妹", "阿妹", "胞妹"),
    "place:新加坡": ("新加坡", "星洲", "叻埠", "石叻", "叻坡"),
    "place:泰国": ("泰国", "暹罗", "暹"),
    "place:越南": ("越南", "安南", "西贡"),
    "place:广东侨乡": ("广东侨乡", "侨乡", "广东"),
    "theme:remittance": ("寄款", "汇款", "批款", "寄钱", "汇银"),
    "theme:family_affection": ("亲情", "思念", "想念", "家书", "家人关怀"),
    "theme:safety": ("平安", "安好", "无恙", "勿念"),
    "theme:safety_report": ("报平安", "告平安"),
    "theme:instruction": ("嘱托", "嘱咐", "劝诫", "叮嘱"),
    "theme:study": ("读书", "学习", "学业", "书法", "功课"),
    "theme:health": ("生病", "疾病", "病愈", "医病"),
    "theme:health_care": ("保重", "调养", "医药", "身体"),
    "theme:debt": ("债务", "还债", "借款", "欠款"),
    "theme:work": ("工作", "营生", "谋生", "生意"),
    "theme:marriage": ("婚姻", "夫妻", "结婚"),
    "theme:home_building": ("建房", "房屋", "置业", "起屋"),
    "theme:funeral": ("丧事", "去世", "安葬", "葬礼"),
}

EDGE_WEIGHTS: dict[str, float] = {
    "RECEIVED_BY": 1.25,
    "SENT_BY": 1.15,
    "SENT_FROM": 1.18,
    "SENT_TO": 1.18,
    "MENTIONS_PERSON": 1.0,
    "MENTIONS_PLACE": 1.0,
    "HAS_THEME": 0.92,
    "HAS_AMOUNT": 0.9,
    "HAS_DATE": 0.85,
}

EDGE_LABELS: dict[str, str] = {
    "RECEIVED_BY": "收信人为",
    "SENT_BY": "寄信人为",
    "SENT_FROM": "寄自",
    "SENT_TO": "寄往",
    "MENTIONS_PERSON": "提及人物",
    "MENTIONS_PLACE": "提及地点",
    "HAS_THEME": "涉及主题",
    "HAS_AMOUNT": "包含金额",
    "HAS_DATE": "写于",
}


def _safe_properties(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _compact(value: Any) -> str:
    return "".join(str(value or "").lower().split())


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        clean = str(value or "").strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        result.append(clean)
    return result


def _node_aliases(row: Mapping[str, Any]) -> list[str]:
    properties = _safe_properties(row.get("properties_json"))
    raw_labels = properties.get("raw_labels") or properties.get("original_labels") or []
    if not isinstance(raw_labels, list):
        raw_labels = [raw_labels]
    return _dedupe(
        [
            str(row.get("label") or ""),
            str(row.get("normalized_label") or ""),
            *(str(item) for item in raw_labels),
        ]
    )


def _idf(record_count: int) -> float:
    return math.log((TOTAL_FULL_TEXT_RECORDS + 1) / (max(record_count, 0) + 1)) + 0.15


def _seed_match_score(
    row: Mapping[str, Any],
    *,
    query_compact: str,
    expansion_terms: list[str],
) -> tuple[float, str]:
    node_id = str(row.get("node_id") or "")
    forced_aliases = GRAPH_QUERY_ALIASES.get(node_id, ())
    forced_matches = [alias for alias in forced_aliases if _compact(alias) in query_compact]
    if forced_matches:
        best = max(forced_matches, key=len)
        return 1.0, best

    aliases = _node_aliases(row)
    direct_matches = [
        alias
        for alias in aliases
        if len(_compact(alias)) >= 2 and _compact(alias) in query_compact
    ]
    if direct_matches:
        best = max(direct_matches, key=len)
        return 0.96, best

    is_person = str(row.get("node_type") or "") == "person"
    for term in expansion_terms:
        compact_term = _compact(term)
        if len(compact_term) < 2:
            continue
        for alias in aliases:
            compact_alias = _compact(alias)
            if compact_alias == compact_term:
                return 0.9, term
            if not is_person and len(compact_alias) >= 2 and (
                compact_alias in compact_term or compact_term in compact_alias
            ):
                return 0.72, term
    return 0.0, ""


def _find_seed_nodes(
    query: str,
    expansion: QueryExpansion,
) -> list[dict[str, Any]]:
    query_compact = _compact(query)
    expansion_terms = _dedupe(
        [
            *expansion.original_terms,
            *expansion.strong_expansion_terms,
            *expansion.medium_expansion_terms,
        ]
    )
    with get_readonly_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                n.*,
                COUNT(DISTINCT NULLIF(e.record_id, '')) AS record_count
            FROM qiaopi_kg_nodes AS n
            LEFT JOIN qiaopi_kg_edges AS e
              ON e.source_node_id = n.node_id
              OR e.target_node_id = n.node_id
            WHERE n.node_type IN ('person', 'place', 'theme')
            GROUP BY n.node_id
            HAVING record_count > 0
            ORDER BY n.node_type, n.node_id
            """
        ).fetchall()

    seeds: list[dict[str, Any]] = []
    for raw_row in rows:
        row = dict(raw_row)
        node_terms = (
            list(expansion.original_terms)
            if row.get("node_type") == "person"
            else expansion_terms
        )
        match_score, matched_term = _seed_match_score(
            row,
            query_compact=query_compact,
            expansion_terms=node_terms,
        )
        if match_score <= 0:
            continue
        record_count = int(row.get("record_count") or 0)
        specificity = _idf(record_count)
        seeds.append(
            {
                "id": row["node_id"],
                "label": row["label"],
                "type": row["node_type"],
                "matched_term": matched_term,
                "match_score": round(match_score, 6),
                "record_count": record_count,
                "_priority": match_score * specificity,
            }
        )
    seeds.sort(
        key=lambda item: (
            -float(item["_priority"]),
            -float(item["match_score"]),
            item["id"],
        )
    )
    for seed in seeds:
        seed.pop("_priority", None)
    return seeds[:MAX_SEEDS]


def _graph_record_candidates(
    seeds: list[Mapping[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    if not seeds:
        return []
    seed_by_id = {str(seed["id"]): seed for seed in seeds}
    node_ids = sorted(seed_by_id)
    placeholders = ", ".join("?" for _ in node_ids)
    with get_readonly_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT
                e.edge_id,
                e.source_node_id,
                e.target_node_id,
                e.edge_type,
                e.record_id,
                e.evidence_text,
                e.confidence
            FROM qiaopi_kg_edges AS e
            JOIN qiaopi_text_records AS r ON r.record_id = e.record_id
            WHERE e.record_id != ''
              AND (
                e.source_node_id IN ({placeholders})
                OR e.target_node_id IN ({placeholders})
              )
            ORDER BY e.record_id, e.edge_type, e.edge_id
            """,
            [*node_ids, *node_ids],
        ).fetchall()

    contributions: defaultdict[str, dict[str, float]] = defaultdict(dict)
    paths: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw_row in rows:
        row = dict(raw_row)
        matched_node_id = (
            row["source_node_id"]
            if row["source_node_id"] in seed_by_id
            else row["target_node_id"]
        )
        seed = seed_by_id[matched_node_id]
        confidence = max(float(row.get("confidence") or 0.0), 0.6)
        contribution = (
            float(seed["match_score"])
            * _idf(int(seed["record_count"]))
            * EDGE_WEIGHTS.get(str(row.get("edge_type") or ""), 0.8)
            * confidence
        )
        record_id = str(row["record_id"])
        previous = contributions[record_id].get(matched_node_id, 0.0)
        if contribution <= previous:
            continue
        contributions[record_id][matched_node_id] = contribution
        paths[record_id] = [
            path
            for path in paths[record_id]
            if path["seed_node_id"] != matched_node_id
        ]
        edge_type = str(row.get("edge_type") or "")
        paths[record_id].append(
            {
                "seed_node_id": matched_node_id,
                "seed_label": seed["label"],
                "seed_type": seed["type"],
                "matched_term": seed["matched_term"],
                "edge_type": edge_type,
                "edge_label": EDGE_LABELS.get(edge_type, edge_type),
                "record_id": record_id,
                "confidence": round(confidence, 6),
                "evidence_text": str(row.get("evidence_text") or ""),
                "path_text": (
                    f"查询词“{seed['matched_term']}” → {seed['label']}"
                    f" → {EDGE_LABELS.get(edge_type, edge_type)} → {record_id}"
                ),
                "score": round(contribution, 8),
            }
        )

    candidates: list[dict[str, Any]] = []
    for record_id, seed_scores in contributions.items():
        seed_count = len(seed_scores)
        base_score = sum(seed_scores.values())
        coverage_bonus = 1.0 + min(max(seed_count - 1, 0), 4) * 0.35
        candidates.append(
            {
                "record_id": record_id,
                "raw_graph_score": base_score * coverage_bonus,
                "graph_seed_count": seed_count,
                "graph_paths": sorted(
                    paths[record_id],
                    key=lambda item: (-float(item["score"]), item["seed_node_id"]),
                )[:MAX_PATHS_PER_RESULT],
            }
        )
    candidates.sort(
        key=lambda item: (
            -float(item["raw_graph_score"]),
            -int(item["graph_seed_count"]),
            item["record_id"],
        )
    )
    selected = candidates[:limit]
    max_score = max(
        (float(item["raw_graph_score"]) for item in selected),
        default=1.0,
    )
    for item in selected:
        item["graph_score"] = round(float(item["raw_graph_score"]) / max_score, 8)
    return selected


def _graph_unit_results(
    candidates: list[Mapping[str, Any]],
    *,
    expansion: QueryExpansion,
    unit_types: list[str],
    filters: Mapping[str, Any],
    top_k: int,
) -> list[dict[str, Any]]:
    if not candidates:
        return []
    candidate_by_record = {
        str(candidate["record_id"]): candidate for candidate in candidates
    }
    rows = fetch_retrieval_units_for_records(candidate_by_record)
    rows = [
        row
        for row in rows
        if (not unit_types or row.get("unit_type") in unit_types)
        and matches_retrieval_filters(row, filters)
    ]
    if not rows:
        return []
    reranked = rerank_units(
        rows,
        expansion=expansion,
        requested_unit_types=unit_types,
        top_k=len(rows),
    )
    max_text_score = max(
        (float(row.get("final_score") or 0.0) for row in reranked),
        default=1.0,
    )
    prepared: list[dict[str, Any]] = []
    per_record_count: defaultdict[str, int] = defaultdict(int)
    for row in reranked:
        record_id = str(row.get("record_id") or "")
        candidate = candidate_by_record.get(record_id)
        if candidate is None or per_record_count[record_id] >= 2:
            continue
        per_record_count[record_id] += 1
        text_score = float(row.get("final_score") or 0.0)
        text_ratio = text_score / max_text_score if max_text_score > 0 else 0.0
        graph_score = float(candidate["graph_score"])
        prepared_row = dict(row)
        prepared_row["graph_score"] = graph_score
        prepared_row["graph_seed_count"] = int(candidate["graph_seed_count"])
        prepared_row["graph_paths"] = list(candidate["graph_paths"])
        prepared_row["graph_rank_score"] = round(
            graph_score * (0.78 + 0.22 * text_ratio),
            8,
        )
        prepared_row["retrieval_sources"] = ["graph"]
        path_summary = "；".join(
            path["path_text"] for path in candidate["graph_paths"][:2]
        )
        prepared_row["matched_reason"] = f"图谱关联：{path_summary}"
        prepared.append(prepared_row)
    prepared.sort(
        key=lambda item: (
            -float(item.get("graph_rank_score") or 0.0),
            -int(item.get("graph_seed_count") or 0),
            -float(item.get("final_score") or 0.0),
            str(item.get("unit_id") or ""),
        )
    )
    return prepared[: max(top_k * 4, 20)]


def _merge_row(
    combined: dict[str, dict[str, Any]],
    row: Mapping[str, Any],
    source: str,
) -> dict[str, Any] | None:
    unit_id = str(row.get("unit_id") or "")
    if not unit_id:
        return None
    if unit_id not in combined:
        combined[unit_id] = dict(row)
        combined[unit_id]["retrieval_sources"] = []
    target = combined[unit_id]
    sources = target.setdefault("retrieval_sources", [])
    for item in row.get("retrieval_sources") or [source]:
        if item not in sources:
            sources.append(item)
    if source == "graph":
        target["graph_score"] = float(row.get("graph_score") or 0.0)
        target["graph_seed_count"] = int(row.get("graph_seed_count") or 0)
        target["graph_paths"] = list(row.get("graph_paths") or [])
        graph_reason = str(row.get("matched_reason") or "")
        existing_reason = str(target.get("matched_reason") or "")
        if graph_reason and "图谱关联：" not in existing_reason:
            target["matched_reason"] = (
                f"{existing_reason}；{graph_reason}" if existing_reason else graph_reason
            )
    return target


def retrieve_graph_rag(
    query: str,
    top_k: int = 10,
    unit_types: list[str] | None = None,
    filters: Mapping[str, Any] | None = None,
    expansion_mode: str = "balanced",
) -> dict[str, Any]:
    requested_unit_types = unit_types or []
    active_filters = filters or {}
    internal_limit = max(top_k * 6, 40)
    base_result = retrieve_hybrid(
        query=query,
        top_k=internal_limit,
        unit_types=requested_unit_types,
        filters=active_filters,
        expansion_mode=expansion_mode,
    )
    expansion: QueryExpansion = base_result.get("expansion") or expand_query(query)

    if not settings.GRAPH_RAG_ENABLED:
        return {
            **base_result,
            "results": base_result["results"][:top_k],
            "grouped_by_record": group_results_by_record(base_result["results"][:top_k]),
            "graph_enabled": False,
            "graph_fallback": True,
            "graph_fallback_reason": "GraphRAG 已由运行配置关闭。",
            "graph_seed_nodes": [],
            "graph_candidate_count": 0,
            "graph_message": "已回退到现有混合检索。",
        }

    try:
        seeds = _find_seed_nodes(query, expansion)
        candidates = _graph_record_candidates(
            seeds,
            limit=max(top_k * 8, 60),
        )
        graph_rows = _graph_unit_results(
            candidates,
            expansion=expansion,
            unit_types=requested_unit_types,
            filters=active_filters,
            top_k=top_k,
        )
    except (FileNotFoundError, OSError, ValueError, sqlite3.Error) as exc:
        seeds = []
        candidates = []
        graph_rows = []
        fallback_reason = f"图谱检索不可用：{exc}"
    else:
        fallback_reason = ""

    if not seeds or not candidates or not graph_rows:
        reason = fallback_reason or (
            "未识别到可用的图谱实体或没有符合筛选条件的图谱候选。"
        )
        rows = base_result["results"][:top_k]
        return {
            **base_result,
            "results": rows,
            "grouped_by_record": group_results_by_record(rows),
            "graph_enabled": False,
            "graph_fallback": True,
            "graph_fallback_reason": reason,
            "graph_seed_nodes": seeds,
            "graph_candidate_count": len(candidates),
            "graph_message": "已自动回退到现有混合检索。",
        }

    combined: dict[str, dict[str, Any]] = {}
    fused_scores: defaultdict[str, float] = defaultdict(float)
    for rank, row in enumerate(base_result["results"], start=1):
        target = _merge_row(combined, row, "base")
        if target is not None:
            fused_scores[str(target["unit_id"])] += 1.0 / (RRF_K + rank)
    for rank, row in enumerate(graph_rows, start=1):
        target = _merge_row(combined, row, "graph")
        if target is not None:
            unit_id = str(target["unit_id"])
            fused_scores[unit_id] += GRAPH_RRF_WEIGHT / (RRF_K + rank)
            fused_scores[unit_id] += (
                GRAPH_SCORE_BONUS * float(row.get("graph_score") or 0.0)
            )

    fused_rows: list[dict[str, Any]] = []
    for unit_id, row in combined.items():
        prepared = dict(row)
        prepared["fusion_score"] = round(fused_scores[unit_id], 8)
        prepared["final_score"] = round(fused_scores[unit_id], 8)
        prepared.setdefault("bm25_score", 0.0)
        prepared.setdefault("semantic_score", 0.0)
        prepared.setdefault("graph_score", 0.0)
        prepared.setdefault("graph_seed_count", 0)
        prepared.setdefault("graph_paths", [])
        fused_rows.append(prepared)
    fused_rows.sort(
        key=lambda item: (
            -float(item.get("fusion_score") or 0.0),
            -int(item.get("graph_seed_count") or 0),
            -float(item.get("graph_score") or 0.0),
            str(item.get("unit_id") or ""),
        )
    )
    selected = fused_rows[:top_k]
    semantic_participated = bool(base_result.get("semantic_enabled", False))
    graph_message = (
        "图谱候选已与关键词、语义结果进行 RRF 融合。"
        if semantic_participated
        else "语义索引未参与；图谱候选已与关键词结果进行 RRF 融合。"
    )
    return {
        **base_result,
        "results": selected,
        "grouped_by_record": group_results_by_record(selected),
        "fusion_method": "graph_rrf",
        "error_message": None,
        "graph_enabled": True,
        "graph_fallback": False,
        "graph_fallback_reason": None,
        "graph_seed_nodes": seeds,
        "graph_candidate_count": len(candidates),
        "graph_message": graph_message,
    }
