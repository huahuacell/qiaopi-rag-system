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


def _load_person_properties(
    connection: sqlite3.Connection,
    node_id: str,
) -> tuple[sqlite3.Row, dict]:
    row = connection.execute(
        """
        SELECT *
        FROM qiaopi_kg_nodes
        WHERE node_id = ?
        """,
        (node_id,),
    ).fetchone()
    assert row is not None
    return row, json.loads(row["properties_json"])


def _load_optional_person_properties(
    connection: sqlite3.Connection,
    node_id: str,
) -> tuple[sqlite3.Row | None, dict]:
    row = connection.execute(
        """
        SELECT *
        FROM qiaopi_kg_nodes
        WHERE node_id = ?
        """,
        (node_id,),
    ).fetchone()
    if row is None:
        return None, {}
    return row, json.loads(row["properties_json"])


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
    stats = build_knowledge_graph()

    assert not any(
        "qiaopi_text_records missing optional place columns" in warning
        for warning in stats["warnings"]
    )

    with get_connection() as connection:
        node_counts = node_type_distribution(connection)
        edge_counts = edge_type_distribution(connection)

    assert node_counts["record"] >= 1
    assert sum(node_counts.values()) >= 1
    assert sum(edge_counts.values()) >= 1
    assert edge_counts["SENT_FROM"] > 0
    assert edge_counts["SENT_TO"] > 0


def test_knowledge_graph_date_nodes_prefer_standard_date(metadata_layer_ready):
    build_knowledge_graph()

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                e.target_node_id,
                n.label,
                n.normalized_label,
                n.properties_json,
                e.properties_json AS edge_properties_json
            FROM qiaopi_kg_edges AS e
            JOIN qiaopi_kg_nodes AS n
                ON n.node_id = e.target_node_id
            WHERE e.record_id = ?
                AND e.edge_type = 'HAS_DATE'
            """,
            ("CSQP-SFHC-TEXT-017",),
        ).fetchone()

    assert row is not None
    assert row["target_node_id"] == "date:1933.9.11"
    assert row["label"] == "1933.9.11"
    assert row["normalized_label"] == "1933.9.11"

    node_properties = json.loads(row["properties_json"])
    edge_properties = json.loads(row["edge_properties_json"])
    assert node_properties["raw_date_text"] == "癸九月十一日"
    assert node_properties["date_standard"] == "1933.9.11"
    assert node_properties["date_calendar"] == "traditional_lunar_text"
    assert edge_properties["raw_date_text"] == "癸九月十一日"


def test_knowledge_graph_normalizes_kinship_person_nodes(metadata_layer_ready):
    stats = build_knowledge_graph()

    with get_connection() as connection:
        mother, mother_properties = _load_person_properties(connection, "person:母亲")
        son, son_properties = _load_person_properties(connection, "person:儿子")
        parents, parents_properties = _load_person_properties(connection, "person:双亲")
        parents_in_law, parents_in_law_properties = _load_person_properties(
            connection,
            "person:岳父母",
        )
        old_mother_alias_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM qiaopi_kg_nodes
            WHERE node_id = 'person:慈亲'
            """
        ).fetchone()["count"]
        text_record_count = count_rows(connection, "qiaopi_text_records")

    assert mother is not None
    assert mother_properties["person_kind"] == "kinship_term"
    assert mother_properties["kinship_type"] == "mother"
    assert "慈亲" in mother_properties["raw_labels"]
    assert "母亲" in mother_properties["raw_labels"]
    assert not any("岳慈亲" in raw_label for raw_label in mother_properties["raw_labels"])
    assert old_mother_alias_count == 0

    assert son is not None
    assert son_properties["person_kind"] == "kinship_term"
    assert son_properties["kinship_type"] == "son"
    assert "男" in son_properties["raw_labels"]
    assert "儿" in son_properties["raw_labels"]

    assert parents is not None
    assert parents_properties["person_kind"] == "kinship_term"
    assert parents_properties["kinship_type"] == "parents"
    assert parents_properties["is_collective_kinship"] is True
    assert parents_properties["member_labels"] == ["父亲", "母亲"]
    assert parents_properties["member_kinship_types"] == ["father", "mother"]
    assert not any("岳双亲" in raw_label for raw_label in parents_properties["raw_labels"])
    assert parents["node_id"] != "person:母亲"

    assert parents_in_law is not None
    assert parents_in_law["label"] == "岳父母"
    assert parents_in_law_properties["person_kind"] == "kinship_term"
    assert parents_in_law_properties["kinship_type"] == "parents_in_law"
    assert parents_in_law_properties["is_collective_kinship"] is True
    assert parents_in_law_properties["member_labels"] == ["岳父", "岳母"]
    assert parents_in_law_properties["member_kinship_types"] == [
        "father_in_law",
        "mother_in_law",
    ]
    assert any("岳双亲" in raw_label for raw_label in parents_in_law_properties["raw_labels"])

    coverage = stats["kinship_coverage"]
    assert coverage["record_count"] == text_record_count
    assert "CSQP-SFHC-TEXT-017" in coverage["record_has_kinship"]
    assert isinstance(coverage["record_has_kinship"]["CSQP-SFHC-TEXT-017"], bool)
    assert coverage["records_with_kinship_count"] > 0


def test_knowledge_graph_normalizes_embedded_kinship_person_nodes(metadata_layer_ready):
    build_knowledge_graph()

    with get_connection() as connection:
        wife, wife_properties = _load_person_properties(connection, "person:妻子")
        grandmother, grandmother_properties = _load_person_properties(connection, "person:祖母")
        grandfather, grandfather_properties = _load_person_properties(connection, "person:祖父")
        mother_in_law, mother_in_law_properties = _load_person_properties(
            connection,
            "person:岳母",
        )
        grandmother_in_law, grandmother_in_law_properties = _load_person_properties(
            connection,
            "person:岳祖母",
        )
        maternal_grandparents, maternal_grandparents_properties = _load_person_properties(
            connection,
            "person:外祖父母",
        )
        maternal_grandfather, maternal_grandfather_properties = _load_optional_person_properties(
            connection,
            "person:外祖父",
        )
        maternal_grandmother, maternal_grandmother_properties = _load_optional_person_properties(
            connection,
            "person:外祖母",
        )
        elder_brother, elder_brother_properties = _load_person_properties(
            connection,
            "person:兄长",
        )
        younger_brother, younger_brother_properties = _load_person_properties(
            connection,
            "person:弟弟",
        )
        elder_sister, elder_sister_properties = _load_person_properties(
            connection,
            "person:姐姐",
        )
        sister_in_law, sister_in_law_properties = _load_person_properties(
            connection,
            "person:嫂子",
        )
        daughter, daughter_properties = _load_person_properties(connection, "person:女儿")
        _, named_person_properties = _load_person_properties(connection, "person:丁南")
        wife_alias_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM qiaopi_kg_nodes
            WHERE node_id IN ('person:黄氏吾妻', 'person:荆妻李氏')
            """
        ).fetchone()["count"]
        compound_grandparent_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM qiaopi_kg_nodes
            WHERE node_id = 'person:外祖父母'
            """
        ).fetchone()["count"]
        wife_evidence = connection.execute(
            """
            SELECT evidence_text
            FROM qiaopi_kg_edges
            WHERE target_node_id = 'person:妻子'
                AND evidence_text LIKE '%吾妻%'
            LIMIT 1
            """
        ).fetchone()
        maternal_grandparent_edges = connection.execute(
            """
            SELECT target_node_id, evidence_text
            FROM qiaopi_kg_edges
            WHERE edge_type = 'MENTIONS_PERSON'
                AND evidence_text LIKE '%外祖父母%'
            """
        ).fetchall()
        affinal_sibling_edges = connection.execute(
            """
            SELECT target_node_id, evidence_text
            FROM qiaopi_kg_edges
            WHERE edge_type = 'MENTIONS_PERSON'
                AND evidence_text LIKE '%妙姿姻姊%'
            """
        ).fetchall()

    assert wife["label"] == "妻子"
    assert wife_properties["person_kind"] == "kinship_term"
    assert wife_properties["kinship_type"] == "wife"
    assert "黄氏吾妻" in wife_properties["raw_labels"]
    assert "荆妻李氏" in wife_properties["raw_labels"]
    assert "吾妻" in wife_properties["detected_terms"]
    assert wife_alias_count == 0

    assert grandmother["label"] == "祖母"
    assert grandmother_properties["kinship_type"] == "grandmother"
    assert "祖慈" in grandmother_properties["raw_labels"]
    assert grandmother_properties["needs_review"] is False
    assert not any("岳祖母" in raw_label for raw_label in grandmother_properties["raw_labels"])

    assert grandfather["label"] == "祖父"
    assert grandfather_properties["kinship_type"] == "grandfather"
    assert "祖父" in grandfather_properties["raw_labels"]

    assert mother_in_law["label"] == "岳母"
    assert mother_in_law_properties["kinship_type"] == "mother_in_law"
    assert "岳母" in mother_in_law_properties["raw_labels"]
    assert "岳慈亲" in mother_in_law_properties["raw_labels"]

    assert grandmother_in_law["label"] == "岳祖母"
    assert grandmother_in_law_properties["kinship_type"] == "grandmother_in_law"
    assert "岳祖母" in grandmother_in_law_properties["raw_labels"]
    assert "岳祖母、岳慈亲" in grandmother_in_law_properties["raw_labels"]

    assert maternal_grandparents["label"] == "外祖父母"
    assert maternal_grandparents_properties["kinship_type"] == "maternal_grandparents"
    assert maternal_grandparents_properties["is_collective_kinship"] is True
    assert maternal_grandparents_properties["member_labels"] == ["外祖父", "外祖母"]
    assert maternal_grandparents_properties["member_kinship_types"] == [
        "maternal_grandfather",
        "maternal_grandmother",
    ]
    assert "外祖父母" in maternal_grandparents_properties["raw_labels"]
    assert compound_grandparent_count == 1
    if maternal_grandfather is not None:
        assert maternal_grandfather["label"] == "外祖父"
        assert maternal_grandfather_properties["kinship_type"] == "maternal_grandfather"
        assert "外祖父母" not in maternal_grandfather_properties["raw_labels"]
    if maternal_grandmother is not None:
        assert maternal_grandmother["label"] == "外祖母"
        assert maternal_grandmother_properties["kinship_type"] == "maternal_grandmother"
        assert "外祖父母" not in maternal_grandmother_properties["raw_labels"]

    assert elder_brother["label"] == "兄长"
    assert elder_brother_properties["kinship_type"] == "elder_brother"
    assert any("胞兄" in raw_label for raw_label in elder_brother_properties["raw_labels"])

    assert younger_brother["label"] == "弟弟"
    assert younger_brother_properties["kinship_type"] == "younger_brother"
    assert any("胞弟" in raw_label for raw_label in younger_brother_properties["raw_labels"])
    assert any("英弟" in raw_label for raw_label in younger_brother_properties["raw_labels"])
    assert any("妙姿姻姊" in raw_label for raw_label in younger_brother_properties["raw_labels"])

    assert elder_sister["label"] == "姐姐"
    assert elder_sister_properties["kinship_type"] == "elder_sister"
    assert any("吾姊" in raw_label for raw_label in elder_sister_properties["raw_labels"])
    assert any("妙姿姻姊" in raw_label for raw_label in elder_sister_properties["raw_labels"])

    assert sister_in_law["label"] == "嫂子"
    assert sister_in_law_properties["kinship_type"] == "sister_in_law"
    assert "嫂嫂" in sister_in_law_properties["raw_labels"]

    assert daughter["label"] == "女儿"
    assert daughter_properties["kinship_type"] == "daughter"
    assert any("女儿" in raw_label for raw_label in daughter_properties["raw_labels"])

    assert named_person_properties["person_kind"] == "named_person"
    assert named_person_properties["kinship_type"] == "none"
    assert named_person_properties["needs_review"] is False
    assert wife_evidence is not None
    assert "吾妻" in wife_evidence["evidence_text"]
    assert {row["target_node_id"] for row in maternal_grandparent_edges} == {
        "person:外祖父母",
    }
    assert all("外祖父母" in row["evidence_text"] for row in maternal_grandparent_edges)
    assert {row["target_node_id"] for row in affinal_sibling_edges} >= {
        "person:姐姐",
        "person:弟弟",
    }
    assert all("妙姿姻姊" in row["evidence_text"] for row in affinal_sibling_edges)


def test_knowledge_graph_reports_unknown_kinship_terms_for_review(metadata_layer_ready):
    stats = build_knowledge_graph()

    review_by_label = {
        item["raw_label"]: item
        for item in stats["kinship_needs_review"]
    }

    assert review_by_label["姑"]["person_kind"] == "unknown"
    assert review_by_label["姑"]["kinship_type"] == "unknown"
    assert review_by_label["姑"]["count"] > 0


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


def test_knowledge_graph_build_step_has_no_neo4j_modules():
    repo_root = Path(__file__).resolve().parents[2]

    assert not (repo_root / "backend" / "app" / "graph" / "neo4j_exporter.py").exists()
    assert not (repo_root / "backend" / "app" / "graph" / "neo4j_importer.py").exists()
