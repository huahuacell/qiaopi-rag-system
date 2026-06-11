from __future__ import annotations

from collections import OrderedDict
from typing import Any, Iterable, Mapping


def _unit_summary(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "unit_id": row.get("unit_id", ""),
        "unit_type": row.get("unit_type", ""),
        "unit_text": row.get("unit_text", ""),
        "source_column": row.get("source_column", ""),
        "evidence_type": row.get("evidence_type", ""),
        "bm25_score": float(row.get("bm25_score") or 0.0),
        "final_score": float(row.get("final_score") or 0.0),
        "matched_reason": row.get("matched_reason", ""),
        "original_hit_count": int(row.get("original_hit_count") or 0),
        "strong_hit_count": int(row.get("strong_hit_count") or 0),
        "medium_hit_count": int(row.get("medium_hit_count") or 0),
        "weak_hit_count": int(row.get("weak_hit_count") or 0),
    }


def group_results_by_record(
    rows: Iterable[Mapping[str, Any]],
    max_units_per_record: int = 3,
) -> list[dict[str, Any]]:
    groups: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for row in rows:
        record_id = str(row.get("record_id", ""))
        if not record_id:
            continue
        if record_id not in groups:
            groups[record_id] = {
                "record_id": record_id,
                "title_reference": row.get("title_reference", ""),
                "sender": row.get("sender", ""),
                "recipient": row.get("recipient", ""),
                "date_text": row.get("date_text", ""),
                "main_intent": row.get("main_intent", ""),
                "best_score": float(row.get("final_score") or 0.0),
                "matched_units": [],
            }
        group = groups[record_id]
        group["best_score"] = max(
            float(group["best_score"]),
            float(row.get("final_score") or 0.0),
        )
        if len(group["matched_units"]) < max_units_per_record:
            group["matched_units"].append(_unit_summary(row))

    return sorted(
        groups.values(),
        key=lambda item: (-float(item["best_score"]), item["record_id"]),
    )
