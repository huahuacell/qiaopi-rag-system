from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from app.database.schema import create_tables


SUPPORTED_NODE_TYPES: tuple[str, ...] = (
    "record",
    "metadata_record",
    "person",
    "place",
    "amount",
    "date",
    "theme",
    "evidence",
)

SUPPORTED_EDGE_TYPES: tuple[str, ...] = (
    "SENT_BY",
    "RECEIVED_BY",
    "MENTIONS_PERSON",
    "MENTIONS_PLACE",
    "SENT_FROM",
    "SENT_TO",
    "HAS_AMOUNT",
    "HAS_DATE",
    "HAS_THEME",
    "SUPPORTED_BY",
    "LINKED_TO_METADATA",
)
ORDERED_JSON_LIST_KEYS = {"member_labels", "member_kinship_types"}


@dataclass(frozen=True)
class KgNode:
    node_id: str
    node_type: str
    label: str
    normalized_label: str
    record_id: str = ""
    source_table: str = ""
    source_id: str = ""
    properties: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KgEdge:
    edge_id: str
    source_node_id: str
    target_node_id: str
    edge_type: str
    record_id: str = ""
    evidence_text: str = ""
    source_table: str = ""
    source_id: str = ""
    weight: float = 1.0
    confidence: float = 0.0
    properties: Mapping[str, Any] = field(default_factory=dict)


def ensure_kg_schema(connection: sqlite3.Connection) -> None:
    create_tables(connection)


def reset_kg_tables(connection: sqlite3.Connection) -> None:
    connection.execute("DELETE FROM qiaopi_kg_edges")
    connection.execute("DELETE FROM qiaopi_kg_nodes")


def insert_nodes(connection: sqlite3.Connection, nodes: Iterable[KgNode]) -> int:
    rows = [
        (
            node.node_id,
            node.node_type,
            node.label,
            node.normalized_label,
            node.record_id,
            node.source_table,
            node.source_id,
            _json_dump(node.properties),
        )
        for node in sorted(nodes, key=lambda item: item.node_id)
    ]
    if rows:
        connection.executemany(
            """
            INSERT OR REPLACE INTO qiaopi_kg_nodes (
                node_id,
                node_type,
                label,
                normalized_label,
                record_id,
                source_table,
                source_id,
                properties_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    return len(rows)


def insert_edges(connection: sqlite3.Connection, edges: Iterable[KgEdge]) -> int:
    rows = [
        (
            edge.edge_id,
            edge.source_node_id,
            edge.target_node_id,
            edge.edge_type,
            edge.record_id,
            edge.evidence_text,
            edge.source_table,
            edge.source_id,
            edge.weight,
            edge.confidence,
            _json_dump(edge.properties),
        )
        for edge in sorted(edges, key=lambda item: item.edge_id)
    ]
    if rows:
        connection.executemany(
            """
            INSERT OR REPLACE INTO qiaopi_kg_edges (
                edge_id,
                source_node_id,
                target_node_id,
                edge_type,
                record_id,
                evidence_text,
                source_table,
                source_id,
                weight,
                confidence,
                properties_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    return len(rows)


def node_type_distribution(connection: sqlite3.Connection) -> dict[str, int]:
    rows = connection.execute(
        """
        SELECT node_type, COUNT(*) AS count
        FROM qiaopi_kg_nodes
        GROUP BY node_type
        ORDER BY node_type
        """
    ).fetchall()
    return {str(row["node_type"]): int(row["count"]) for row in rows}


def edge_type_distribution(connection: sqlite3.Connection) -> dict[str, int]:
    rows = connection.execute(
        """
        SELECT edge_type, COUNT(*) AS count
        FROM qiaopi_kg_edges
        GROUP BY edge_type
        ORDER BY edge_type
        """
    ).fetchall()
    return {str(row["edge_type"]): int(row["count"]) for row in rows}


def count_kg_nodes(connection: sqlite3.Connection) -> int:
    row = connection.execute("SELECT COUNT(*) AS count FROM qiaopi_kg_nodes").fetchone()
    return int(row["count"])


def count_kg_edges(connection: sqlite3.Connection) -> int:
    row = connection.execute("SELECT COUNT(*) AS count FROM qiaopi_kg_edges").fetchone()
    return int(row["count"])


def kg_tables_exist(connection: sqlite3.Connection) -> bool:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
            AND name IN ('qiaopi_kg_nodes', 'qiaopi_kg_edges')
        """
    ).fetchall()
    return {row["name"] for row in rows} == {"qiaopi_kg_nodes", "qiaopi_kg_edges"}


def fetch_kg_stats(connection: sqlite3.Connection) -> dict[str, Any]:
    if not kg_tables_exist(connection):
        return {
            "node_count": 0,
            "edge_count": 0,
            "node_type_distribution": {},
            "edge_type_distribution": {},
        }
    return {
        "node_count": count_kg_nodes(connection),
        "edge_count": count_kg_edges(connection),
        "node_type_distribution": node_type_distribution(connection),
        "edge_type_distribution": edge_type_distribution(connection),
    }


def fetch_kg_node(connection: sqlite3.Connection, node_id: str) -> dict[str, Any] | None:
    if not kg_tables_exist(connection):
        return None
    row = connection.execute(
        """
        SELECT *
        FROM qiaopi_kg_nodes
        WHERE node_id = ?
        """,
        (node_id,),
    ).fetchone()
    return dict(row) if row else None


def fetch_kg_nodes_by_ids(
    connection: sqlite3.Connection,
    node_ids: Sequence[str],
) -> list[dict[str, Any]]:
    if not kg_tables_exist(connection):
        return []
    unique_node_ids = sorted({node_id for node_id in node_ids if node_id})
    if not unique_node_ids:
        return []
    placeholders = ", ".join("?" for _ in unique_node_ids)
    rows = connection.execute(
        f"""
        SELECT *
        FROM qiaopi_kg_nodes
        WHERE node_id IN ({placeholders})
        ORDER BY
            CASE node_type
                WHEN 'record' THEN 1
                WHEN 'person' THEN 2
                WHEN 'place' THEN 3
                WHEN 'theme' THEN 4
                WHEN 'amount' THEN 5
                WHEN 'date' THEN 6
                WHEN 'evidence' THEN 7
                WHEN 'metadata_record' THEN 8
                ELSE 99
            END,
            node_id
        """,
        unique_node_ids,
    ).fetchall()
    return _rows_to_dicts(rows)


def fetch_kg_edges_for_record(
    connection: sqlite3.Connection,
    record_id: str,
    *,
    limit: int = 500,
) -> list[dict[str, Any]]:
    if not kg_tables_exist(connection):
        return []
    rows = connection.execute(
        """
        SELECT *
        FROM qiaopi_kg_edges
        WHERE record_id = ?
        ORDER BY
            CASE edge_type
                WHEN 'SENT_BY' THEN 1
                WHEN 'RECEIVED_BY' THEN 2
                WHEN 'SENT_FROM' THEN 3
                WHEN 'SENT_TO' THEN 4
                WHEN 'MENTIONS_PERSON' THEN 5
                WHEN 'MENTIONS_PLACE' THEN 6
                WHEN 'HAS_AMOUNT' THEN 7
                WHEN 'HAS_DATE' THEN 8
                WHEN 'HAS_THEME' THEN 9
                WHEN 'SUPPORTED_BY' THEN 10
                WHEN 'LINKED_TO_METADATA' THEN 11
                ELSE 99
            END,
            edge_id
        LIMIT ?
        """,
        (record_id, limit),
    ).fetchall()
    return _rows_to_dicts(rows)


def fetch_kg_edges_touching_nodes(
    connection: sqlite3.Connection,
    node_ids: Sequence[str],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    if not kg_tables_exist(connection):
        return []
    unique_node_ids = sorted({node_id for node_id in node_ids if node_id})
    if not unique_node_ids:
        return []
    placeholders = ", ".join("?" for _ in unique_node_ids)
    rows = connection.execute(
        f"""
        SELECT *
        FROM qiaopi_kg_edges
        WHERE source_node_id IN ({placeholders})
            OR target_node_id IN ({placeholders})
        ORDER BY confidence DESC, edge_type, edge_id
        LIMIT ?
        """,
        [*unique_node_ids, *unique_node_ids, limit],
    ).fetchall()
    return _rows_to_dicts(rows)


def fetch_kg_overview_nodes(
    connection: sqlite3.Connection,
    *,
    limit_nodes: int,
) -> list[dict[str, Any]]:
    if not kg_tables_exist(connection):
        return []
    rows = connection.execute(
        """
        WITH degree_rows AS (
            SELECT source_node_id AS node_id, COUNT(*) AS degree
            FROM qiaopi_kg_edges
            GROUP BY source_node_id
            UNION ALL
            SELECT target_node_id AS node_id, COUNT(*) AS degree
            FROM qiaopi_kg_edges
            GROUP BY target_node_id
        ),
        degree AS (
            SELECT node_id, SUM(degree) AS degree
            FROM degree_rows
            GROUP BY node_id
        )
        SELECT n.*, COALESCE(d.degree, 0) AS degree
        FROM qiaopi_kg_nodes n
        LEFT JOIN degree d ON d.node_id = n.node_id
        WHERE n.node_type IN ('record', 'person', 'place', 'theme', 'amount')
        ORDER BY
            COALESCE(d.degree, 0) DESC,
            CASE n.node_type
                WHEN 'record' THEN 1
                WHEN 'person' THEN 2
                WHEN 'place' THEN 3
                WHEN 'theme' THEN 4
                WHEN 'amount' THEN 5
                ELSE 99
            END,
            n.node_id
        LIMIT ?
        """,
        (limit_nodes,),
    ).fetchall()
    return _rows_to_dicts(rows)


def fetch_kg_edges_between_nodes(
    connection: sqlite3.Connection,
    node_ids: Sequence[str],
    *,
    limit_edges: int,
) -> list[dict[str, Any]]:
    if not kg_tables_exist(connection):
        return []
    unique_node_ids = sorted({node_id for node_id in node_ids if node_id})
    if not unique_node_ids:
        return []
    placeholders = ", ".join("?" for _ in unique_node_ids)
    rows = connection.execute(
        f"""
        SELECT *
        FROM qiaopi_kg_edges
        WHERE source_node_id IN ({placeholders})
            AND target_node_id IN ({placeholders})
        ORDER BY confidence DESC, edge_type, edge_id
        LIMIT ?
        """,
        [*unique_node_ids, *unique_node_ids, limit_edges],
    ).fetchall()
    return _rows_to_dicts(rows)


def fetch_kg_place_flow_pairs(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    if not kg_tables_exist(connection):
        return []
    rows = connection.execute(
        """
        WITH origins AS (
            SELECT DISTINCT
                e.record_id,
                COALESCE(NULLIF(n.normalized_label, ''), n.label) AS origin_place
            FROM qiaopi_kg_edges e
            JOIN qiaopi_kg_nodes n ON n.node_id = e.target_node_id
            WHERE e.edge_type = 'SENT_FROM'
                AND e.record_id != ''
                AND e.source_node_id LIKE 'record:%'
                AND n.node_type = 'place'
        ),
        destinations AS (
            SELECT DISTINCT
                e.record_id,
                COALESCE(NULLIF(n.normalized_label, ''), n.label) AS destination_place
            FROM qiaopi_kg_edges e
            JOIN qiaopi_kg_nodes n ON n.node_id = e.target_node_id
            WHERE e.edge_type = 'SENT_TO'
                AND e.record_id != ''
                AND e.source_node_id LIKE 'record:%'
                AND n.node_type = 'place'
        )
        SELECT
            origins.record_id,
            origins.origin_place,
            destinations.destination_place
        FROM origins
        JOIN destinations ON destinations.record_id = origins.record_id
        ORDER BY origins.origin_place, destinations.destination_place, origins.record_id
        """
    ).fetchall()
    return _rows_to_dicts(rows)


def _rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def _json_dump(value: Mapping[str, Any]) -> str:
    return json.dumps(_clean_json(value), ensure_ascii=False, sort_keys=True)


def _clean_json(value: Any, *, preserve_list_order: bool = False) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _clean_json(
                item,
                preserve_list_order=str(key) in ORDERED_JSON_LIST_KEYS,
            )
            for key, item in value.items()
            if item not in (None, "")
        }
    if isinstance(value, (list, tuple, set)):
        cleaned = [_clean_json(item) for item in value if item not in (None, "")]
        if preserve_list_order:
            return cleaned
        try:
            return sorted(cleaned)
        except TypeError:
            return cleaned
    return value
