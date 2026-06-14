from __future__ import annotations

import sqlite3
from typing import Iterable

from app.database.connection import get_connection


TABLES: tuple[str, ...] = (
    "qiaopi_text_records",
    "qiaopi_metadata_records",
    "qiaopi_text_metadata_links",
    "qiaopi_text_metadata_link_candidates",
    "qiaopi_amount_mentions",
    "qiaopi_entity_mentions",
    "qiaopi_place_mentions",
    "qiaopi_evidence_spans",
    "qiaopi_retrieval_units",
    "qiaopi_kg_nodes",
    "qiaopi_kg_edges",
    "qiaopi_generation_cache",
    "qiaopi_query_logs",
)

DROP_TABLES: tuple[str, ...] = (
    "qiaopi_metadata_fts",
    "qiaopi_retrieval_units_fts",
    *reversed(TABLES),
)

CREATE_TABLE_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS qiaopi_text_records (
        record_id TEXT PRIMARY KEY,
        title_reference TEXT,
        sender TEXT,
        recipient TEXT,
        sender_name_clean TEXT,
        recipient_name_clean TEXT,
        date_text TEXT,
        year_normalized TEXT,
        body_clean TEXT,
        body_core TEXT,
        main_intent TEXT,
        theme_tags TEXT,
        text_quality_level TEXT,
        has_full_text INTEGER,
        has_remittance INTEGER,
        relationship_type TEXT,
        place_mentions_normalized TEXT,
        retrieval_keywords TEXT,
        rag_summary_text TEXT,
        style_reference_text TEXT,
        raw_json TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS qiaopi_metadata_records (
        metadata_id TEXT PRIMARY KEY,
        source_index INTEGER NOT NULL,
        title_raw TEXT,
        title_clean TEXT,
        sender_raw TEXT,
        recipient_raw TEXT,
        sender_name_clean TEXT,
        recipient_name_clean TEXT,
        date_text TEXT,
        year_normalized TEXT,
        era_text TEXT,
        origin_place TEXT,
        destination_place TEXT,
        place_mentions TEXT,
        country_or_region TEXT,
        remittance_raw TEXT,
        amount_number REAL,
        currency TEXT,
        has_remittance INTEGER NOT NULL DEFAULT 0,
        kinship_terms TEXT,
        relationship_type TEXT,
        theme_tags TEXT,
        main_intent TEXT,
        has_linked_text INTEGER NOT NULL DEFAULT 0,
        linked_record_id TEXT,
        parse_confidence REAL NOT NULL DEFAULT 0.0,
        needs_review INTEGER NOT NULL DEFAULT 0,
        warnings TEXT,
        raw_json TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS qiaopi_text_metadata_links (
        link_id TEXT PRIMARY KEY,
        record_id TEXT NOT NULL,
        metadata_id TEXT NOT NULL,
        link_method TEXT NOT NULL,
        link_confidence REAL NOT NULL,
        title_similarity REAL NOT NULL,
        matched_fields_json TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(record_id),
        UNIQUE(metadata_id),
        FOREIGN KEY(record_id) REFERENCES qiaopi_text_records(record_id)
            ON DELETE CASCADE,
        FOREIGN KEY(metadata_id) REFERENCES qiaopi_metadata_records(metadata_id)
            ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS qiaopi_text_metadata_link_candidates (
        candidate_id TEXT PRIMARY KEY,
        record_id TEXT NOT NULL,
        metadata_id TEXT NOT NULL,
        candidate_method TEXT NOT NULL,
        candidate_confidence REAL NOT NULL,
        title_similarity REAL NOT NULL,
        matched_fields_json TEXT NOT NULL,
        reason TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(record_id, metadata_id),
        FOREIGN KEY(record_id) REFERENCES qiaopi_text_records(record_id)
            ON DELETE CASCADE,
        FOREIGN KEY(metadata_id) REFERENCES qiaopi_metadata_records(metadata_id)
            ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS qiaopi_amount_mentions (
        mention_id TEXT PRIMARY KEY,
        record_id TEXT NOT NULL,
        raw_text TEXT,
        amount_text TEXT,
        amount_number REAL,
        currency TEXT,
        sentence TEXT,
        is_primary_candidate INTEGER,
        source_field TEXT,
        FOREIGN KEY(record_id) REFERENCES qiaopi_text_records(record_id)
            ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS qiaopi_entity_mentions (
        mention_id TEXT PRIMARY KEY,
        record_id TEXT NOT NULL,
        entity_type TEXT,
        entity_text TEXT,
        normalized_text TEXT,
        source_field TEXT,
        confidence REAL,
        FOREIGN KEY(record_id) REFERENCES qiaopi_text_records(record_id)
            ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS qiaopi_place_mentions (
        mention_id TEXT PRIMARY KEY,
        record_id TEXT NOT NULL,
        alias_text TEXT,
        normalized_place TEXT,
        country_or_region TEXT,
        source_field TEXT,
        FOREIGN KEY(record_id) REFERENCES qiaopi_text_records(record_id)
            ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS qiaopi_evidence_spans (
        evidence_id TEXT PRIMARY KEY,
        record_id TEXT NOT NULL,
        evidence_type TEXT,
        evidence_text TEXT,
        source_column TEXT,
        start_char INTEGER,
        end_char INTEGER,
        FOREIGN KEY(record_id) REFERENCES qiaopi_text_records(record_id)
            ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS qiaopi_retrieval_units (
        unit_id TEXT PRIMARY KEY,
        record_id TEXT NOT NULL,
        unit_type TEXT NOT NULL,
        source_column TEXT,
        unit_text TEXT NOT NULL,
        title_reference TEXT,
        sender TEXT,
        recipient TEXT,
        date_text TEXT,
        main_intent TEXT,
        theme_tags TEXT,
        style_keywords TEXT,
        relationship_type TEXT,
        place_mentions_normalized TEXT,
        retrieval_keywords TEXT,
        weight REAL NOT NULL DEFAULT 1.0,
        evidence_type TEXT,
        fts_text TEXT NOT NULL,
        raw_json TEXT NOT NULL,
        FOREIGN KEY(record_id) REFERENCES qiaopi_text_records(record_id)
            ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS qiaopi_kg_nodes (
        node_id TEXT PRIMARY KEY,
        node_type TEXT NOT NULL,
        label TEXT NOT NULL,
        normalized_label TEXT NOT NULL,
        record_id TEXT,
        source_table TEXT,
        source_id TEXT,
        properties_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS qiaopi_kg_edges (
        edge_id TEXT PRIMARY KEY,
        source_node_id TEXT NOT NULL,
        target_node_id TEXT NOT NULL,
        edge_type TEXT NOT NULL,
        record_id TEXT,
        evidence_text TEXT,
        source_table TEXT,
        source_id TEXT,
        weight REAL NOT NULL DEFAULT 1.0,
        confidence REAL NOT NULL DEFAULT 0.0,
        properties_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(source_node_id) REFERENCES qiaopi_kg_nodes(node_id)
            ON DELETE CASCADE,
        FOREIGN KEY(target_node_id) REFERENCES qiaopi_kg_nodes(node_id)
            ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS qiaopi_generation_cache (
        cache_id TEXT PRIMARY KEY,
        task_type TEXT NOT NULL,
        input_hash TEXT NOT NULL,
        record_id TEXT,
        result_json TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(task_type, input_hash, record_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS qiaopi_query_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        endpoint TEXT NOT NULL,
        query TEXT NOT NULL,
        filters_json TEXT,
        top_k INTEGER,
        returned_count INTEGER,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
)

CREATE_INDEX_STATEMENTS: tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_text_records_intent ON qiaopi_text_records(main_intent);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_text_records_quality ON qiaopi_text_records(text_quality_level);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_text_records_year ON qiaopi_text_records(year_normalized);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_metadata_records_year ON qiaopi_metadata_records(year_normalized);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_metadata_records_country ON qiaopi_metadata_records(country_or_region);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_metadata_records_origin ON qiaopi_metadata_records(origin_place);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_metadata_records_destination ON qiaopi_metadata_records(destination_place);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_metadata_records_linked ON qiaopi_metadata_records(has_linked_text);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_metadata_records_remittance ON qiaopi_metadata_records(has_remittance);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_metadata_links_record ON qiaopi_text_metadata_links(record_id);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_metadata_links_metadata ON qiaopi_text_metadata_links(metadata_id);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_metadata_candidates_record ON qiaopi_text_metadata_link_candidates(record_id);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_metadata_candidates_metadata ON qiaopi_text_metadata_link_candidates(metadata_id);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_amount_mentions_record ON qiaopi_amount_mentions(record_id);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_entity_mentions_record ON qiaopi_entity_mentions(record_id);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_entity_mentions_type ON qiaopi_entity_mentions(entity_type);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_place_mentions_record ON qiaopi_place_mentions(record_id);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_evidence_spans_record ON qiaopi_evidence_spans(record_id);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_evidence_spans_type ON qiaopi_evidence_spans(evidence_type);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_retrieval_units_record ON qiaopi_retrieval_units(record_id);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_retrieval_units_type ON qiaopi_retrieval_units(unit_type);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_kg_nodes_node_id ON qiaopi_kg_nodes(node_id);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_kg_nodes_type ON qiaopi_kg_nodes(node_type);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_kg_nodes_record ON qiaopi_kg_nodes(record_id);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_kg_edges_edge_id ON qiaopi_kg_edges(edge_id);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_kg_edges_type ON qiaopi_kg_edges(edge_type);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_kg_edges_record ON qiaopi_kg_edges(record_id);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_kg_edges_source ON qiaopi_kg_edges(source_node_id);",
    "CREATE INDEX IF NOT EXISTS idx_qiaopi_kg_edges_target ON qiaopi_kg_edges(target_node_id);",
)


def execute_statements(
    connection: sqlite3.Connection,
    statements: Iterable[str],
) -> None:
    for statement in statements:
        connection.execute(statement)


def create_tables(connection: sqlite3.Connection) -> None:
    execute_statements(connection, CREATE_TABLE_STATEMENTS)
    execute_statements(connection, CREATE_INDEX_STATEMENTS)


def reset_database(connection: sqlite3.Connection) -> None:
    for table_name in DROP_TABLES:
        connection.execute(f"DROP TABLE IF EXISTS {table_name}")
    create_tables(connection)


def initialize_database(reset: bool = False) -> None:
    with get_connection() as connection:
        if reset:
            reset_database(connection)
        else:
            create_tables(connection)
