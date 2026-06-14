from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

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


def _json_dump(value: Mapping[str, Any]) -> str:
    return json.dumps(_clean_json(value), ensure_ascii=False, sort_keys=True)


def _clean_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _clean_json(item) for key, item in value.items() if item not in (None, "")}
    if isinstance(value, (list, tuple, set)):
        cleaned = [_clean_json(item) for item in value if item not in (None, "")]
        try:
            return sorted(cleaned)
        except TypeError:
            return cleaned
    return value
