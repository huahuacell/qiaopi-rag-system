from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping

from app.database.connection import get_connection
from app.graph.graph_repository import (
    fetch_kg_edges_between_nodes,
    fetch_kg_edges_for_record,
    fetch_kg_edges_touching_nodes,
    fetch_kg_node,
    fetch_kg_nodes_by_ids,
    fetch_kg_overview_nodes,
    fetch_kg_place_flow_pairs,
    fetch_kg_stats,
)


def get_graph_stats() -> dict[str, Any]:
    with get_connection() as connection:
        return fetch_kg_stats(connection)


def get_record_graph(record_id: str, *, limit_edges: int = 500) -> dict[str, Any] | None:
    record_node_id = f"record:{record_id}"
    with get_connection() as connection:
        record_node = fetch_kg_node(connection, record_node_id)
        if record_node is None:
            return None
        edge_rows = fetch_kg_edges_for_record(connection, record_id, limit=limit_edges)
        node_ids = {record_node_id}
        for edge in edge_rows:
            node_ids.add(edge.get("source_node_id", ""))
            node_ids.add(edge.get("target_node_id", ""))
        node_rows = fetch_kg_nodes_by_ids(connection, sorted(node_ids))

    return {
        "record_id": record_id,
        "nodes": [_node_response(row) for row in node_rows],
        "edges": [_edge_response(row) for row in edge_rows],
    }


def get_node_neighbors(
    node_id: str,
    *,
    depth: int = 1,
    limit: int = 50,
) -> dict[str, Any] | None:
    depth = max(1, min(depth, 2))
    limit = max(1, min(limit, 200))

    with get_connection() as connection:
        center_node = fetch_kg_node(connection, node_id)
        if center_node is None:
            return None

        edge_rows_by_id: dict[str, dict[str, Any]] = {}
        first_edges = fetch_kg_edges_touching_nodes(connection, [node_id], limit=limit)
        for edge in first_edges:
            edge_rows_by_id[edge["edge_id"]] = edge

        if depth > 1 and len(edge_rows_by_id) < limit:
            neighbor_ids = _neighbor_ids(edge_rows_by_id.values(), center=node_id)
            second_edges = fetch_kg_edges_touching_nodes(
                connection,
                sorted(neighbor_ids),
                limit=limit - len(edge_rows_by_id),
            )
            for edge in second_edges:
                if len(edge_rows_by_id) >= limit:
                    break
                edge_rows_by_id.setdefault(edge["edge_id"], edge)

        edge_rows = list(edge_rows_by_id.values())[:limit]
        node_ids = {node_id}
        for edge in edge_rows:
            node_ids.add(edge.get("source_node_id", ""))
            node_ids.add(edge.get("target_node_id", ""))
        node_rows = fetch_kg_nodes_by_ids(connection, sorted(node_ids))

    return {
        "node_id": node_id,
        "center_node": _node_response(center_node),
        "nodes": [_node_response(row) for row in node_rows],
        "edges": [_edge_response(row) for row in edge_rows],
        "depth": depth,
        "limit": limit,
    }


def get_graph_overview(
    *,
    limit_nodes: int = 80,
    limit_edges: int = 120,
) -> dict[str, Any]:
    limit_nodes = max(1, min(limit_nodes, 200))
    limit_edges = max(1, min(limit_edges, 300))

    with get_connection() as connection:
        node_rows = fetch_kg_overview_nodes(connection, limit_nodes=limit_nodes)
        edge_rows = fetch_kg_edges_between_nodes(
            connection,
            [row["node_id"] for row in node_rows],
            limit_edges=limit_edges,
        )
        edge_node_ids = _edge_node_ids(edge_rows)
        if edge_node_ids:
            node_rows = fetch_kg_nodes_by_ids(
                connection,
                sorted((edge_node_ids | {row["node_id"] for row in node_rows}) ),
            )[:limit_nodes]

    selected_node_ids = {row["node_id"] for row in node_rows}
    edge_rows = [
        edge
        for edge in edge_rows
        if edge.get("source_node_id") in selected_node_ids
        and edge.get("target_node_id") in selected_node_ids
    ][:limit_edges]
    return {
        "nodes": [_node_response(row) for row in node_rows],
        "edges": [_edge_response(row) for row in edge_rows],
        "summary": {
            "limit_nodes": limit_nodes,
            "limit_edges": limit_edges,
            "returned_nodes": len(node_rows),
            "returned_edges": len(edge_rows),
        },
    }


def get_place_flows(*, limit: int = 50) -> dict[str, Any]:
    limit = max(1, min(limit, 200))
    with get_connection() as connection:
        rows = fetch_kg_place_flow_pairs(connection)

    counts: Counter[tuple[str, str]] = Counter()
    samples: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    for row in rows:
        origin_place = str(row.get("origin_place") or "").strip()
        destination_place = str(row.get("destination_place") or "").strip()
        record_id = str(row.get("record_id") or "").strip()
        if not origin_place or not destination_place or not record_id:
            continue
        key = (origin_place, destination_place)
        counts[key] += 1
        if len(samples[key]) < 5 and record_id not in samples[key]:
            samples[key].append(record_id)

    flows = [
        {
            "origin_place": origin_place,
            "destination_place": destination_place,
            "count": count,
            "record_ids_sample": samples[(origin_place, destination_place)],
        }
        for (origin_place, destination_place), count in counts.items()
    ]
    flows.sort(key=lambda item: (-item["count"], item["origin_place"], item["destination_place"]))
    return {"flows": flows[:limit]}


def _node_response(row: Mapping[str, Any]) -> dict[str, Any]:
    node_type = str(row.get("node_type") or "")
    return {
        "id": row.get("node_id", ""),
        "label": row.get("label", ""),
        "type": node_type,
        "category": node_type,
        "normalized_label": row.get("normalized_label", ""),
        "record_id": row.get("record_id") or "",
        "source_table": row.get("source_table") or "",
        "source_id": row.get("source_id") or "",
        "properties": _safe_properties(row.get("properties_json")),
    }


def _edge_response(row: Mapping[str, Any]) -> dict[str, Any]:
    edge_type = str(row.get("edge_type") or "")
    return {
        "id": row.get("edge_id", ""),
        "source": row.get("source_node_id", ""),
        "target": row.get("target_node_id", ""),
        "type": edge_type,
        "label": edge_type,
        "record_id": row.get("record_id") or "",
        "evidence_text": row.get("evidence_text") or "",
        "source_table": row.get("source_table") or "",
        "source_id": row.get("source_id") or "",
        "weight": float(row.get("weight") or 0.0),
        "confidence": float(row.get("confidence") or 0.0),
        "properties": _safe_properties(row.get("properties_json")),
    }


def _safe_properties(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _neighbor_ids(edges: Iterable[Mapping[str, Any]], *, center: str) -> set[str]:
    node_ids: set[str] = set()
    for edge in edges:
        for column in ("source_node_id", "target_node_id"):
            node_id = str(edge.get(column) or "")
            if node_id and node_id != center:
                node_ids.add(node_id)
    return node_ids


def _edge_node_ids(edges: Iterable[Mapping[str, Any]]) -> set[str]:
    node_ids: set[str] = set()
    for edge in edges:
        source_node_id = str(edge.get("source_node_id") or "")
        target_node_id = str(edge.get("target_node_id") or "")
        if source_node_id:
            node_ids.add(source_node_id)
        if target_node_id:
            node_ids.add(target_node_id)
    return node_ids
