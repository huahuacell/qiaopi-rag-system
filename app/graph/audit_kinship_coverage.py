from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from app.database.connection import get_connection
from app.graph.graph_repository import kg_tables_exist
from app.graph.normalizers import KINSHIP_TERM, NAMED_PERSON, UNKNOWN_PERSON_KIND
from app.settings import QIAOPI_DB_PATH


def audit_kinship_coverage(
    db_path: Path = QIAOPI_DB_PATH,
    *,
    top_limit: int = 10,
    sample_limit: int = 20,
) -> dict[str, Any]:
    with get_connection(db_path) as connection:
        if not kg_tables_exist(connection):
            return {
                "error": "KG tables do not exist. Run python -m app.ingestion.build_knowledge_graph first.",
                "total_person_nodes": 0,
            }

        person_rows = connection.execute(
            """
            SELECT node_id, label, properties_json
            FROM qiaopi_kg_nodes
            WHERE node_type = 'person'
            ORDER BY node_id
            """
        ).fetchall()
        edge_rows = connection.execute(
            """
            SELECT edge_type, record_id, target_node_id
            FROM qiaopi_kg_edges
            WHERE target_node_id LIKE 'person:%'
            """
        ).fetchall()
        record_rows = connection.execute(
            """
            SELECT record_id
            FROM qiaopi_text_records
            ORDER BY record_id
            """
        ).fetchall()

    person_props = {
        row["node_id"]: _loads_properties(row["properties_json"])
        for row in person_rows
    }
    person_kind_counts: Counter[str] = Counter()
    kinship_type_counts: Counter[str] = Counter()
    kinship_node_ids: set[str] = set()
    top_raw_labels: dict[str, Counter[str]] = defaultdict(Counter)
    unknown_samples: list[dict[str, Any]] = []

    for row in person_rows:
        node_id = row["node_id"]
        props = person_props[node_id]
        person_kind = str(props.get("person_kind") or UNKNOWN_PERSON_KIND)
        kinship_type = str(props.get("kinship_type") or "unknown")
        person_kind_counts[person_kind] += 1
        kinship_type_counts[kinship_type] += 1
        if person_kind == KINSHIP_TERM:
            kinship_node_ids.add(node_id)
            for raw_label in _as_strings(props.get("raw_labels")):
                top_raw_labels[kinship_type][raw_label] += 1
        if person_kind == UNKNOWN_PERSON_KIND or kinship_type == "unknown":
            unknown_samples.append(
                {
                    "node_id": node_id,
                    "label": row["label"],
                    "raw_labels": _as_strings(props.get("raw_labels"))[:5],
                    "detected_terms": _as_strings(props.get("detected_terms")),
                    "normalization_note": props.get("normalization_note", ""),
                    "needs_review": bool(props.get("needs_review")),
                }
            )

    kinship_edge_distribution: Counter[str] = Counter()
    kinship_record_ids: set[str] = set()
    for row in edge_rows:
        if row["target_node_id"] not in kinship_node_ids:
            continue
        kinship_edge_distribution[str(row["edge_type"])] += 1
        record_id = str(row["record_id"] or "")
        if record_id:
            kinship_record_ids.add(record_id)

    record_ids = [str(row["record_id"]) for row in record_rows if row["record_id"]]
    missing_record_ids = sorted(set(record_ids) - kinship_record_ids)
    return {
        "total_person_nodes": len(person_rows),
        "named_person_count": person_kind_counts.get(NAMED_PERSON, 0),
        "kinship_term_count": person_kind_counts.get(KINSHIP_TERM, 0),
        "unknown_count": person_kind_counts.get(UNKNOWN_PERSON_KIND, 0),
        "person_kind_distribution": dict(sorted(person_kind_counts.items())),
        "kinship_type_distribution": dict(sorted(kinship_type_counts.items())),
        "kinship_edge_distribution": dict(sorted(kinship_edge_distribution.items())),
        "record_kinship_coverage": {
            "record_count": len(record_ids),
            "records_with_kinship_count": len(kinship_record_ids),
            "records_without_kinship_count": len(missing_record_ids),
            "coverage_ratio": round(len(kinship_record_ids) / len(record_ids), 6)
            if record_ids
            else 0.0,
            "records_without_kinship_sample": missing_record_ids[:sample_limit],
        },
        "top_raw_labels_by_kinship_type": {
            kinship_type: counter.most_common(top_limit)
            for kinship_type, counter in sorted(top_raw_labels.items())
        },
        "possible_remaining_unknown_samples": unknown_samples[:sample_limit],
    }


def print_audit(audit: Mapping[str, Any]) -> None:
    if audit.get("error"):
        print(audit["error"])
        return

    print("Kinship coverage audit")
    print(f"total person nodes: {audit['total_person_nodes']}")
    print(f"named_person count: {audit['named_person_count']}")
    print(f"kinship_term count: {audit['kinship_term_count']}")
    print(f"unknown count: {audit['unknown_count']}")
    print()
    _print_distribution("kinship edge distribution", audit["kinship_edge_distribution"])
    print()
    print("record kinship coverage:")
    for key, value in audit["record_kinship_coverage"].items():
        print(f"  {key}: {value}")
    print()
    print("top raw_labels for each kinship_type:")
    for kinship_type, rows in audit["top_raw_labels_by_kinship_type"].items():
        labels = ", ".join(f"{label} ({count})" for label, count in rows)
        print(f"  {kinship_type}: {labels}")
    print()
    print("possible remaining unknown samples:")
    for sample in audit["possible_remaining_unknown_samples"]:
        print(f"  {sample['node_id']}: {sample['raw_labels']}")


def _print_distribution(title: str, distribution: Mapping[str, int]) -> None:
    print(f"{title}:")
    if not distribution:
        print("  none")
        return
    for key, count in distribution.items():
        print(f"  {key}: {count}")


def _loads_properties(value: Any) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _as_strings(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)]


def main() -> None:
    print_audit(audit_kinship_coverage())


if __name__ == "__main__":
    main()
