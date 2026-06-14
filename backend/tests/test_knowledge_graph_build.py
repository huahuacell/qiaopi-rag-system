from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.database.connection import get_connection
from app.database.repository import count_rows, list_tables
from app.graph.graph_repository import edge_type_distribution, node_type_distribution
from app.ingestion.build_knowledge_graph import build_knowledge_graph


def _safe_count(connection: sqlite3.Connection, table_name: str) -> int:
    try:
        return count_rows(connection, table_name)
    except sqlite3.OperationalError:
        return 0


def test_knowledge_graph_tables_are_created_and_populated(metadata_layer_ready):
    stats = build_knowledge_graph()

    assert stats["node_count"] > 0
    assert stats["edge_count"] > 0

    with get_connection() as connection:
        table_names = set(list_tables(connection))
        assert "qiaopi_kg_nodes" in table_names
        assert "qiaopi_kg_edges" in table_names
        assert count_rows(connection, "qiaopi_kg_nodes") == stats["node_count"]
        assert count_rows(connection, "qiaopi_kg_edges") == stats["edge_count"]


def test_knowledge_graph_build_is_deterministic(metadata_layer_ready):
    first = build_knowledge_graph()
    second = build_knowledge_graph()

    assert second["node_count"] == first["node_count"]
    assert second["edge_count"] == first["edge_count"]
    assert second["node_type_distribution"] == first["node_type_distribution"]
    assert second["edge_type_distribution"] == first["edge_type_distribution"]


def test_knowledge_graph_has_no_duplicate_logical_edges(metadata_layer_ready):
    build_knowledge_graph()

    with get_connection() as connection:
        duplicate_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM (
                SELECT
                    record_id,
                    source_node_id,
                    target_node_id,
                    edge_type,
                    COUNT(*) AS logical_count
                FROM qiaopi_kg_edges
                GROUP BY record_id, source_node_id, target_node_id, edge_type
                HAVING logical_count > 1
            )
            """
        ).fetchone()["count"]

    assert duplicate_count == 0


def test_knowledge_graph_aggregates_duplicate_place_edge_evidence(metadata_layer_ready):
    build_knowledge_graph()

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM qiaopi_kg_edges
            WHERE record_id = ?
                AND source_node_id = ?
                AND target_node_id = ?
                AND edge_type = ?
            """,
            (
                "CSQP-SFHC-TEXT-017",
                "record:CSQP-SFHC-TEXT-017",
                "place:越南",
                "MENTIONS_PLACE",
            ),
        ).fetchone()

    assert row is not None
    properties = json.loads(row["properties_json"])
    assert properties["deduplicated_count"] > 1
    assert "qiaopi_place_mentions" in properties["source_tables"]
    assert "qiaopi_text_records" in properties["source_tables"]
    assert "安南" in properties["raw_labels"]
    assert "越南" in properties["raw_labels"]
    assert row["confidence"] == max(properties["confidences"])


def test_knowledge_graph_merges_duplicate_amount_mentions(metadata_layer_ready):
    build_knowledge_graph()

    with get_connection() as connection:
        amount_rows = connection.execute(
            """
            SELECT *
            FROM qiaopi_kg_nodes
            WHERE record_id = ?
                AND node_type = 'amount'
                AND label = ?
            """,
            ("CSQP-SFHC-TEXT-017", "洋银肆元"),
        ).fetchall()
        edge_rows = connection.execute(
            """
            SELECT *
            FROM qiaopi_kg_edges
            WHERE record_id = ?
                AND edge_type = 'HAS_AMOUNT'
                AND target_node_id = ?
            """,
            ("CSQP-SFHC-TEXT-017", amount_rows[0]["node_id"] if amount_rows else ""),
        ).fetchall()

    assert len(amount_rows) == 1
    assert len(edge_rows) == 1

    node_properties = json.loads(amount_rows[0]["properties_json"])
    edge_properties = json.loads(edge_rows[0]["properties_json"])
    assert node_properties["deduplicated_count"] == 2
    assert edge_properties["deduplicated_count"] == 2
    assert len(node_properties["source_ids"]) == 2
    assert len(edge_properties["source_ids"]) == 2
    assert len(node_properties["evidence_texts"]) == 2
    assert len(edge_properties["evidence_texts"]) == 2
    assert "批款:洋银肆元" in node_properties["evidence_texts"]


def test_knowledge_graph_distributions_are_queryable(metadata_layer_ready):
    build_knowledge_graph()

    with get_connection() as connection:
        node_counts = node_type_distribution(connection)
        edge_counts = edge_type_distribution(connection)

    assert node_counts["record"] >= 1
    assert sum(node_counts.values()) >= 1
    assert sum(edge_counts.values()) >= 1


def test_knowledge_graph_contains_source_backed_node_types(metadata_layer_ready):
    stats = build_knowledge_graph()
    node_counts = stats["node_type_distribution"]

    with get_connection() as connection:
        if _safe_count(connection, "qiaopi_entity_mentions") > 0:
            assert node_counts["person"] > 0
        if _safe_count(connection, "qiaopi_place_mentions") > 0:
            assert node_counts["place"] > 0
        if _safe_count(connection, "qiaopi_evidence_spans") > 0:
            assert node_counts["evidence"] > 0
        if _safe_count(connection, "qiaopi_text_records") > 0:
            assert node_counts["theme"] > 0


def test_knowledge_graph_does_not_promote_metadata_to_retrieval_units(metadata_layer_ready):
    with get_connection() as connection:
        before_count = count_rows(connection, "qiaopi_retrieval_units")

    build_knowledge_graph()

    with get_connection() as connection:
        after_count = count_rows(connection, "qiaopi_retrieval_units")
        metadata_unit_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM qiaopi_retrieval_units
            WHERE record_id LIKE 'CSQP-META-%'
            """
        ).fetchone()["count"]

    assert after_count == before_count
    assert metadata_unit_count == 0


def test_knowledge_graph_step_has_no_graph_api_neo4j_or_viewer():
    repo_root = Path(__file__).resolve().parents[2]

    assert not (repo_root / "backend" / "app" / "api" / "graph.py").exists()
    assert not (repo_root / "backend" / "app" / "services" / "graph_service.py").exists()
    assert not (repo_root / "backend" / "app" / "graph" / "neo4j_exporter.py").exists()
    assert not (repo_root / "backend" / "app" / "graph" / "neo4j_importer.py").exists()
    assert not (repo_root / "kg-viewer").exists()
