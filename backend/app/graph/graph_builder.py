from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from app.database.connection import get_connection
from app.graph.graph_repository import (
    SUPPORTED_EDGE_TYPES,
    SUPPORTED_NODE_TYPES,
    KgEdge,
    KgNode,
    count_kg_edges,
    count_kg_nodes,
    edge_type_distribution,
    ensure_kg_schema,
    insert_edges,
    insert_nodes,
    node_type_distribution,
    reset_kg_tables,
)
from app.graph.normalizers import (
    KINSHIP_TERM,
    NAMED_PERSON,
    NO_KINSHIP_TYPE,
    UNKNOWN_KINSHIP_TYPE,
    UNKNOWN_PERSON_KIND,
    KinshipNormalization,
    clean_text,
    is_uncertain_date,
    normalize_amount_number,
    normalize_amount_raw,
    normalize_date_label,
    normalize_kinship_people,
    normalize_person_label,
    normalize_place_label,
    normalize_theme_label,
    split_multi_value,
)
from app.settings import QIAOPI_DB_PATH


DIRECT_FIELD_CONFIDENCE = 0.95
STRUCTURED_MENTION_CONFIDENCE = 0.90
INFERRED_CONFIDENCE = 0.75
UNCERTAIN_CONFIDENCE = 0.60

SOURCE_TABLES: tuple[str, ...] = (
    "qiaopi_text_records",
    "qiaopi_entity_mentions",
    "qiaopi_place_mentions",
    "qiaopi_amount_mentions",
    "qiaopi_evidence_spans",
    "qiaopi_retrieval_units",
    "qiaopi_metadata_records",
    "qiaopi_text_metadata_links",
)

OPTIONAL_SOURCE_TABLES: tuple[str, ...] = tuple(
    table for table in SOURCE_TABLES if table != "qiaopi_text_records"
)

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def build_knowledge_graph(db_path: Path = QIAOPI_DB_PATH) -> dict[str, Any]:
    with get_connection(db_path) as connection:
        builder = SQLiteKnowledgeGraphBuilder(connection)
        return builder.build()


class SQLiteKnowledgeGraphBuilder:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.nodes: dict[str, KgNode] = {}
        self.edges: dict[str, KgEdge] = {}
        self.warnings: list[str] = []
        self._initial_tables = self._list_tables()
        self._columns_cache: dict[str, set[str]] = {}
        self.kinship_record_ids: dict[str, set[str]] = defaultdict(set)
        self._kinship_review_items: dict[str, dict[str, Any]] = {}

    def build(self) -> dict[str, Any]:
        self._warn_missing_source_tables()
        ensure_kg_schema(self.connection)
        reset_kg_tables(self.connection)

        retrieval_unit_counts = self._retrieval_unit_counts()
        text_records = self._fetch_rows(
            "qiaopi_text_records",
            order_by=("record_id",),
            optional=False,
        )
        self._add_record_nodes(text_records, retrieval_unit_counts)
        self._add_record_person_edges(text_records)
        self._add_record_date_theme_place_edges(text_records)
        self._add_entity_mentions()
        self._add_place_mentions()
        self._add_amount_mentions()
        self._add_evidence_spans()
        self._add_linked_metadata_records()

        inserted_nodes = insert_nodes(self.connection, self.nodes.values())
        inserted_edges = insert_edges(self.connection, self.edges.values())

        node_counts = node_type_distribution(self.connection)
        edge_counts = edge_type_distribution(self.connection)
        return {
            "node_count": count_kg_nodes(self.connection),
            "edge_count": count_kg_edges(self.connection),
            "inserted_node_count": inserted_nodes,
            "inserted_edge_count": inserted_edges,
            "node_type_distribution": {
                node_type: node_counts.get(node_type, 0)
                for node_type in SUPPORTED_NODE_TYPES
            },
            "edge_type_distribution": {
                edge_type: edge_counts.get(edge_type, 0)
                for edge_type in SUPPORTED_EDGE_TYPES
            },
            "kinship_coverage": self._kinship_coverage(text_records),
            "kinship_needs_review": self._kinship_needs_review(),
            "warnings": list(self.warnings),
        }

    def _add_record_nodes(
        self,
        records: Iterable[Mapping[str, Any]],
        retrieval_unit_counts: Mapping[str, int],
    ) -> None:
        self._warn_missing_columns(
            "qiaopi_text_records",
            (
                "record_id",
                "title_reference",
                "sender",
                "recipient",
                "date_text",
                "main_intent",
                "theme_tags",
                "text_quality_level",
            ),
        )
        for row in records:
            record_id = self._value(row, "record_id")
            if not record_id:
                continue
            title = self._value(row, "title_reference") or record_id
            has_full_text = self._value(row, "has_full_text")
            properties = self._properties(
                {
                    "record_id": record_id,
                    "title_reference": self._value(row, "title_reference"),
                    "sender": self._value(row, "sender"),
                    "recipient": self._value(row, "recipient"),
                    "sender_name_clean": self._value(row, "sender_name_clean"),
                    "recipient_name_clean": self._value(row, "recipient_name_clean"),
                    "date_text": self._value(row, "date_text"),
                    "year_normalized": self._value(row, "year_normalized"),
                    "date_standard": self._value(row, "date_standard"),
                    "date_year": self._number_or_text(row, "date_year"),
                    "date_month": self._number_or_text(row, "date_month"),
                    "date_day": self._number_or_text(row, "date_day"),
                    "date_precision": self._value(row, "date_precision"),
                    "date_calendar": self._value(row, "date_calendar"),
                    "date_parse_confidence": self._number_or_text(row, "date_parse_confidence"),
                    "date_parse_note": self._value(row, "date_parse_note"),
                    "main_intent": self._value(row, "main_intent"),
                    "theme_tags": self._value(row, "theme_tags"),
                    "text_quality": self._value(row, "text_quality_level", "text_quality"),
                    "has_full_text": has_full_text,
                    "retrieval_unit_count": retrieval_unit_counts.get(record_id, 0),
                    "rag_evidence_allowed": has_full_text == "1",
                }
            )
            self._upsert_node(
                node_id=f"record:{record_id}",
                node_type="record",
                label=title,
                normalized_label=record_id,
                record_id=record_id,
                source_table="qiaopi_text_records",
                source_id=record_id,
                properties=properties,
            )

    def _add_record_person_edges(self, records: Iterable[Mapping[str, Any]]) -> None:
        for row in records:
            record_id = self._value(row, "record_id")
            if not record_id:
                continue
            record_node_id = f"record:{record_id}"
            sender_label = self._value(row, "sender_name_clean", "sender")
            if sender_label:
                sender_node_ids = self._upsert_person_nodes(
                    sender_label,
                    source_table="qiaopi_text_records",
                    source_id=f"{record_id}:sender",
                    record_id=record_id,
                    source_field="sender",
                    properties={
                        "original_labels": [self._value(row, "sender") or sender_label],
                        "clean_label": sender_label,
                        "source_columns": ["sender", "sender_name_clean"],
                    },
                )
                for sender_node_id in sender_node_ids:
                    self._add_edge(
                        source_node_id=record_node_id,
                        target_node_id=sender_node_id,
                        edge_type="SENT_BY",
                        record_id=record_id,
                        source_table="qiaopi_text_records",
                        source_id=f"{record_id}:sender",
                        confidence=DIRECT_FIELD_CONFIDENCE,
                        properties={
                            "source_column": "sender",
                            "original_label": self._value(row, "sender") or sender_label,
                            "clean_label": sender_label,
                        },
                    )

            recipient_label = self._value(row, "recipient_name_clean", "recipient")
            if recipient_label:
                recipient_node_ids = self._upsert_person_nodes(
                    recipient_label,
                    source_table="qiaopi_text_records",
                    source_id=f"{record_id}:recipient",
                    record_id=record_id,
                    source_field="recipient",
                    properties={
                        "original_labels": [self._value(row, "recipient") or recipient_label],
                        "clean_label": recipient_label,
                        "source_columns": ["recipient", "recipient_name_clean"],
                    },
                )
                for recipient_node_id in recipient_node_ids:
                    self._add_edge(
                        source_node_id=record_node_id,
                        target_node_id=recipient_node_id,
                        edge_type="RECEIVED_BY",
                        record_id=record_id,
                        source_table="qiaopi_text_records",
                        source_id=f"{record_id}:recipient",
                        confidence=DIRECT_FIELD_CONFIDENCE,
                        properties={
                            "source_column": "recipient",
                            "original_label": self._value(row, "recipient") or recipient_label,
                            "clean_label": recipient_label,
                        },
                    )

    def _add_record_date_theme_place_edges(self, records: Iterable[Mapping[str, Any]]) -> None:
        missing_place_columns = [
            column
            for column in ("origin_place", "destination_place", "country_or_region")
            if column not in self._table_columns("qiaopi_text_records")
        ]
        if missing_place_columns:
            self._warn_once(
                "qiaopi_text_records missing optional place columns "
                f"{', '.join(missing_place_columns)}; falling back to raw_json and "
                "place_mentions_normalized where available."
            )

        for row in records:
            record_id = self._value(row, "record_id")
            if not record_id:
                continue
            record_node_id = f"record:{record_id}"
            raw_json = self._raw_json(row)

            self._add_date_edge(row, raw_json, record_id, record_node_id)
            self._add_theme_edges(row, record_id, record_node_id)
            self._add_record_place_edges(row, raw_json, record_id, record_node_id)

    def _add_date_edge(
        self,
        row: Mapping[str, Any],
        raw_json: Mapping[str, Any],
        record_id: str,
        record_node_id: str,
    ) -> None:
        raw_date = self._value(row, "date_text") or clean_text(raw_json.get("date_text"))
        normalized_year = self._value(row, "year_normalized") or clean_text(
            raw_json.get("year_normalized")
        )
        date_standard = self._value(row, "date_standard") or clean_text(
            raw_json.get("date_standard")
        )
        label = date_standard or normalized_year
        normalized_label = normalize_date_label(label)
        if not normalized_label:
            return
        date_node_id = f"date:{normalized_label}"
        uncertainty = is_uncertain_date(raw_date) if raw_date else False
        confidence = (
            self._float_value(row, "date_parse_confidence", INFERRED_CONFIDENCE)
            if date_standard
            else UNCERTAIN_CONFIDENCE if uncertainty else INFERRED_CONFIDENCE
        )
        source_column = "date_standard" if date_standard else "year_normalized"
        self._upsert_node(
            node_id=date_node_id,
            node_type="date",
            label=label,
            normalized_label=normalized_label,
            source_table="qiaopi_text_records",
            source_id=f"{record_id}:date",
            properties={
                "raw_date_text": raw_date,
                "year_normalized": normalized_year,
                "date_standard": date_standard,
                "date_year": self._number_or_text(row, "date_year"),
                "date_month": self._number_or_text(row, "date_month"),
                "date_day": self._number_or_text(row, "date_day"),
                "date_precision": self._value(row, "date_precision"),
                "date_calendar": self._value(row, "date_calendar"),
                "date_parse_confidence": self._number_or_text(row, "date_parse_confidence"),
                "date_parse_note": self._value(row, "date_parse_note"),
                "source_column": source_column,
                "uncertain": uncertainty,
            },
        )
        self._add_edge(
            source_node_id=record_node_id,
            target_node_id=date_node_id,
            edge_type="HAS_DATE",
            record_id=record_id,
            source_table="qiaopi_text_records",
            source_id=f"{record_id}:date",
            confidence=confidence,
            properties={
                "raw_date_text": raw_date,
                "year_normalized": normalized_year,
                "date_standard": date_standard,
                "date_year": self._number_or_text(row, "date_year"),
                "date_month": self._number_or_text(row, "date_month"),
                "date_day": self._number_or_text(row, "date_day"),
                "date_precision": self._value(row, "date_precision"),
                "date_calendar": self._value(row, "date_calendar"),
                "date_parse_confidence": self._number_or_text(row, "date_parse_confidence"),
                "date_parse_note": self._value(row, "date_parse_note"),
                "source_column": source_column,
                "uncertain": uncertainty,
            },
        )

    def _add_theme_edges(
        self,
        row: Mapping[str, Any],
        record_id: str,
        record_node_id: str,
    ) -> None:
        theme_values: list[tuple[str, str]] = []
        main_intent = self._value(row, "main_intent")
        if main_intent:
            theme_values.append(("main_intent", main_intent))
        for theme in split_multi_value(self._value(row, "theme_tags")):
            theme_values.append(("theme_tags", theme))

        seen: set[str] = set()
        for source_column, raw_theme in theme_values:
            normalized_label = normalize_theme_label(raw_theme)
            if not normalized_label or normalized_label in seen:
                continue
            seen.add(normalized_label)
            theme_node_id = f"theme:{normalized_label}"
            self._upsert_node(
                node_id=theme_node_id,
                node_type="theme",
                label=raw_theme,
                normalized_label=normalized_label,
                source_table="qiaopi_text_records",
                source_id=f"{record_id}:{source_column}:{normalized_label}",
                properties={
                    "original_labels": [raw_theme],
                    "source_columns": [source_column],
                },
            )
            self._add_edge(
                source_node_id=record_node_id,
                target_node_id=theme_node_id,
                edge_type="HAS_THEME",
                record_id=record_id,
                source_table="qiaopi_text_records",
                source_id=f"{record_id}:{source_column}:{normalized_label}",
                confidence=INFERRED_CONFIDENCE,
                properties={"source_column": source_column, "original_label": raw_theme},
            )

    def _add_record_place_edges(
        self,
        row: Mapping[str, Any],
        raw_json: Mapping[str, Any],
        record_id: str,
        record_node_id: str,
    ) -> None:
        origin = self._value(row, "origin_place", "overseas_place") or clean_text(
            raw_json.get("origin_place") or raw_json.get("overseas_place")
        )
        destination = self._value(row, "destination_place", "hometown_place") or clean_text(
            raw_json.get("destination_place") or raw_json.get("hometown_place")
        )
        if origin:
            self._add_place_edge(
                source_node_id=record_node_id,
                edge_type="SENT_FROM",
                raw_label=origin,
                record_id=record_id,
                source_table="qiaopi_text_records",
                source_id=f"{record_id}:origin_place",
                confidence=INFERRED_CONFIDENCE,
                properties={"source_column": "origin_place", "inferred_from": "record_fields"},
            )
        if destination:
            self._add_place_edge(
                source_node_id=record_node_id,
                edge_type="SENT_TO",
                raw_label=destination,
                record_id=record_id,
                source_table="qiaopi_text_records",
                source_id=f"{record_id}:destination_place",
                confidence=INFERRED_CONFIDENCE,
                properties={"source_column": "destination_place", "inferred_from": "record_fields"},
            )

        for index, place_label in enumerate(
            split_multi_value(self._value(row, "place_mentions_normalized")),
            start=1,
        ):
            self._add_place_edge(
                source_node_id=record_node_id,
                edge_type="MENTIONS_PLACE",
                raw_label=place_label,
                record_id=record_id,
                source_table="qiaopi_text_records",
                source_id=f"{record_id}:place_mentions_normalized:{index:03d}",
                confidence=UNCERTAIN_CONFIDENCE,
                properties={
                    "source_column": "place_mentions_normalized",
                    "uncertain_relation": True,
                },
            )

    def _add_entity_mentions(self) -> None:
        self._warn_missing_columns(
            "qiaopi_entity_mentions",
            ("mention_id", "record_id", "entity_type", "entity_text", "normalized_text"),
        )
        rows = self._fetch_rows(
            "qiaopi_entity_mentions",
            order_by=("record_id", "mention_id"),
        )
        for row in rows:
            entity_type = self._value(row, "entity_type")
            if entity_type not in {"person", "kinship"}:
                continue
            record_id = self._value(row, "record_id")
            if not record_id:
                continue
            original_label = self._value(row, "entity_text", "source_text", "value")
            label = self._value(row, "normalized_text") or original_label
            if not label:
                continue
            mention_id = self._value(row, "mention_id") or self._stable_suffix(
                record_id, entity_type, label
            )
            person_node_ids = self._upsert_person_nodes(
                label,
                source_table="qiaopi_entity_mentions",
                source_id=mention_id,
                record_id=record_id,
                entity_type=entity_type,
                source_field=self._value(row, "source_field"),
                properties={
                    "original_labels": [original_label or label],
                    "entity_types": [entity_type],
                    "source_columns": [self._value(row, "source_field")],
                },
            )
            for person_node_id in person_node_ids:
                self._add_edge(
                    source_node_id=f"record:{record_id}",
                    target_node_id=person_node_id,
                    edge_type="MENTIONS_PERSON",
                    record_id=record_id,
                    evidence_text=original_label,
                    source_table="qiaopi_entity_mentions",
                    source_id=mention_id,
                    confidence=self._float_value(row, "confidence", STRUCTURED_MENTION_CONFIDENCE),
                    properties={
                        "entity_type": entity_type,
                        "source_field": self._value(row, "source_field"),
                        "original_label": original_label,
                        "normalized_text": self._value(row, "normalized_text"),
                    },
                )

    def _add_place_mentions(self) -> None:
        self._warn_missing_columns(
            "qiaopi_place_mentions",
            ("mention_id", "record_id", "alias_text", "normalized_place", "source_field"),
        )
        rows = self._fetch_rows(
            "qiaopi_place_mentions",
            order_by=("record_id", "mention_id"),
        )
        for row in rows:
            record_id = self._value(row, "record_id")
            if not record_id:
                continue
            label = self._value(row, "normalized_place", "alias_text", "country_or_region")
            if not label:
                continue
            mention_id = self._value(row, "mention_id") or self._stable_suffix(record_id, label)
            self._add_place_edge(
                source_node_id=f"record:{record_id}",
                edge_type="MENTIONS_PLACE",
                raw_label=label,
                record_id=record_id,
                evidence_text=self._value(row, "alias_text"),
                source_table="qiaopi_place_mentions",
                source_id=mention_id,
                confidence=STRUCTURED_MENTION_CONFIDENCE,
                properties={
                    "alias_text": self._value(row, "alias_text"),
                    "normalized_place": self._value(row, "normalized_place"),
                    "country_or_region": self._value(row, "country_or_region"),
                    "source_field": self._value(row, "source_field"),
                },
            )

    def _add_amount_mentions(self) -> None:
        self._warn_missing_columns(
            "qiaopi_amount_mentions",
            ("mention_id", "record_id", "raw_text", "amount_number", "currency", "sentence"),
        )
        rows = self._fetch_rows(
            "qiaopi_amount_mentions",
            order_by=("record_id", "mention_id"),
        )
        for row in rows:
            record_id = self._value(row, "record_id")
            if not record_id:
                continue
            raw_amount = self._value(row, "raw_text", "amount_text")
            if not raw_amount:
                raw_amount = "amount"
            amount_key = self._amount_key(row, record_id, raw_amount)
            amount_node_id = f"amount:{record_id}:{self._stable_suffix(amount_key)}"
            mention_id = self._value(row, "mention_id") or f"{record_id}:amount:{self._stable_suffix(amount_key)}"
            evidence_text = self._value(row, "sentence") or self._value(row, "raw_text")
            self._upsert_node(
                node_id=amount_node_id,
                node_type="amount",
                label=raw_amount,
                normalized_label=amount_key,
                record_id=record_id,
                source_table="qiaopi_amount_mentions",
                source_id=mention_id,
                properties={
                    "amount_raw": self._value(row, "raw_text"),
                    "amount_text": self._value(row, "amount_text"),
                    "amount_number": self._number_or_text(row, "amount_number"),
                    "currency": self._value(row, "currency"),
                    "evidence_text": evidence_text,
                    "raw_amounts": [raw_amount],
                    "amount_numbers": [self._number_or_text(row, "amount_number")],
                    "currencies": [self._value(row, "currency")],
                    "evidence_texts": [evidence_text],
                    "source_ids": [mention_id],
                    "source_fields": [self._value(row, "source_field")],
                    "deduplicated_count": 1,
                    "source_field": self._value(row, "source_field"),
                    "is_primary_candidate": self._value(row, "is_primary_candidate"),
                },
            )
            self._add_edge(
                source_node_id=f"record:{record_id}",
                target_node_id=amount_node_id,
                edge_type="HAS_AMOUNT",
                record_id=record_id,
                evidence_text=evidence_text,
                source_table="qiaopi_amount_mentions",
                source_id=mention_id,
                confidence=STRUCTURED_MENTION_CONFIDENCE,
                properties={
                    "amount_raw": self._value(row, "raw_text"),
                    "amount_number": self._number_or_text(row, "amount_number"),
                    "currency": self._value(row, "currency"),
                    "source_field": self._value(row, "source_field"),
                },
            )

    def _add_evidence_spans(self) -> None:
        self._warn_missing_columns(
            "qiaopi_evidence_spans",
            (
                "evidence_id",
                "record_id",
                "evidence_type",
                "evidence_text",
                "source_column",
                "start_char",
                "end_char",
            ),
        )
        rows = self._fetch_rows(
            "qiaopi_evidence_spans",
            order_by=("record_id", "evidence_id"),
        )
        counters: defaultdict[str, int] = defaultdict(int)
        for row in rows:
            record_id = self._value(row, "record_id")
            if not record_id:
                continue
            counters[record_id] += 1
            fallback_id = f"{record_id}:evidence:{counters[record_id]:03d}"
            evidence_id = self._value(row, "evidence_id") or fallback_id
            evidence_node_id = f"evidence:{record_id}:{evidence_id}"
            evidence_text = self._value(row, "evidence_text")
            label = evidence_text[:80] if evidence_text else self._value(row, "evidence_type") or evidence_id
            self._upsert_node(
                node_id=evidence_node_id,
                node_type="evidence",
                label=label,
                normalized_label=evidence_id,
                record_id=record_id,
                source_table="qiaopi_evidence_spans",
                source_id=evidence_id,
                properties={
                    "evidence_text": evidence_text,
                    "source_column": self._value(row, "source_column"),
                    "evidence_type": self._value(row, "evidence_type"),
                    "start_char": self._number_or_text(row, "start_char"),
                    "end_char": self._number_or_text(row, "end_char"),
                    "rag_evidence_allowed": True,
                },
            )
            self._add_edge(
                source_node_id=f"record:{record_id}",
                target_node_id=evidence_node_id,
                edge_type="SUPPORTED_BY",
                record_id=record_id,
                evidence_text=evidence_text,
                source_table="qiaopi_evidence_spans",
                source_id=evidence_id,
                confidence=STRUCTURED_MENTION_CONFIDENCE,
                properties={
                    "source_column": self._value(row, "source_column"),
                    "evidence_type": self._value(row, "evidence_type"),
                    "start_char": self._number_or_text(row, "start_char"),
                    "end_char": self._number_or_text(row, "end_char"),
                },
            )

    def _add_linked_metadata_records(self) -> None:
        self._warn_missing_columns(
            "qiaopi_text_metadata_links",
            ("link_id", "record_id", "metadata_id", "link_method", "link_confidence"),
        )
        links = self._fetch_rows(
            "qiaopi_text_metadata_links",
            order_by=("record_id", "metadata_id"),
        )
        if not links:
            return

        metadata_by_id = self._linked_metadata_by_id(
            sorted({self._value(link, "metadata_id") for link in links if self._value(link, "metadata_id")})
        )
        for link in links:
            record_id = self._value(link, "record_id")
            metadata_id = self._value(link, "metadata_id")
            if not record_id or not metadata_id:
                continue
            metadata = metadata_by_id.get(metadata_id, {})
            metadata_node_id = f"metadata:{metadata_id}"
            label = (
                self._value(metadata, "title_clean")
                or self._value(metadata, "title_raw")
                or metadata_id
            )
            self._upsert_node(
                node_id=metadata_node_id,
                node_type="metadata_record",
                label=label,
                normalized_label=metadata_id,
                record_id=record_id,
                source_table="qiaopi_metadata_records",
                source_id=metadata_id,
                properties={
                    "metadata_id": metadata_id,
                    "linked_record_id": record_id,
                    "title_clean": self._value(metadata, "title_clean"),
                    "sender_raw": self._value(metadata, "sender_raw"),
                    "recipient_raw": self._value(metadata, "recipient_raw"),
                    "date_text": self._value(metadata, "date_text"),
                    "year_normalized": self._value(metadata, "year_normalized"),
                    "date_standard": self._value(metadata, "date_standard"),
                    "date_year": self._number_or_text(metadata, "date_year"),
                    "date_month": self._number_or_text(metadata, "date_month"),
                    "date_day": self._number_or_text(metadata, "date_day"),
                    "date_precision": self._value(metadata, "date_precision"),
                    "date_calendar": self._value(metadata, "date_calendar"),
                    "date_parse_confidence": self._number_or_text(metadata, "date_parse_confidence"),
                    "date_parse_note": self._value(metadata, "date_parse_note"),
                    "origin_place": self._value(metadata, "origin_place"),
                    "destination_place": self._value(metadata, "destination_place"),
                    "catalog_only": True,
                    "rag_evidence_allowed": False,
                },
            )
            self._add_edge(
                source_node_id=f"record:{record_id}",
                target_node_id=metadata_node_id,
                edge_type="LINKED_TO_METADATA",
                record_id=record_id,
                source_table="qiaopi_text_metadata_links",
                source_id=self._value(link, "link_id") or f"{record_id}:{metadata_id}",
                confidence=self._float_value(link, "link_confidence", STRUCTURED_MENTION_CONFIDENCE),
                properties={
                    "metadata_id": metadata_id,
                    "link_method": self._value(link, "link_method"),
                    "title_similarity": self._number_or_text(link, "title_similarity"),
                    "matched_fields_json": self._value(link, "matched_fields_json"),
                    "catalog_only": True,
                    "rag_evidence_allowed": False,
                },
            )
            self._add_metadata_place_edges(metadata, metadata_node_id, record_id, metadata_id)

    def _add_metadata_place_edges(
        self,
        metadata: Mapping[str, Any],
        metadata_node_id: str,
        record_id: str,
        metadata_id: str,
    ) -> None:
        origin = self._value(metadata, "origin_place")
        destination = self._value(metadata, "destination_place")
        if origin:
            self._add_place_edge(
                source_node_id=metadata_node_id,
                edge_type="SENT_FROM",
                raw_label=origin,
                record_id=record_id,
                source_table="qiaopi_metadata_records",
                source_id=f"{metadata_id}:origin_place",
                confidence=UNCERTAIN_CONFIDENCE,
                properties={
                    "metadata_id": metadata_id,
                    "source_column": "origin_place",
                    "catalog_only": True,
                    "rag_evidence_allowed": False,
                },
            )
        if destination:
            self._add_place_edge(
                source_node_id=metadata_node_id,
                edge_type="SENT_TO",
                raw_label=destination,
                record_id=record_id,
                source_table="qiaopi_metadata_records",
                source_id=f"{metadata_id}:destination_place",
                confidence=UNCERTAIN_CONFIDENCE,
                properties={
                    "metadata_id": metadata_id,
                    "source_column": "destination_place",
                    "catalog_only": True,
                    "rag_evidence_allowed": False,
                },
            )
        for index, place_label in enumerate(split_multi_value(self._value(metadata, "place_mentions")), start=1):
            self._add_place_edge(
                source_node_id=metadata_node_id,
                edge_type="MENTIONS_PLACE",
                raw_label=place_label,
                record_id=record_id,
                source_table="qiaopi_metadata_records",
                source_id=f"{metadata_id}:place_mentions:{index:03d}",
                confidence=UNCERTAIN_CONFIDENCE,
                properties={
                    "metadata_id": metadata_id,
                    "source_column": "place_mentions",
                    "catalog_only": True,
                    "rag_evidence_allowed": False,
                    "uncertain_relation": True,
                },
            )

    def _upsert_person_node(
        self,
        label: str,
        *,
        source_table: str,
        source_id: str,
        properties: Mapping[str, Any],
        record_id: str = "",
        entity_type: str = "",
        source_field: str = "",
        person_kind_hint: str = "",
    ) -> str:
        node_ids = self._upsert_person_nodes(
            label,
            source_table=source_table,
            source_id=source_id,
            properties=properties,
            record_id=record_id,
            entity_type=entity_type,
            source_field=source_field,
            person_kind_hint=person_kind_hint,
        )
        return node_ids[0] if node_ids else ""

    def _upsert_person_nodes(
        self,
        label: str,
        *,
        source_table: str,
        source_id: str,
        properties: Mapping[str, Any],
        record_id: str = "",
        entity_type: str = "",
        source_field: str = "",
        person_kind_hint: str = "",
    ) -> list[str]:
        raw_labels = self._person_source_labels(label, properties)
        kinships = normalize_kinship_people(
            label,
            raw_labels=raw_labels,
            entity_type=entity_type,
            source_field=source_field,
            person_kind_hint=person_kind_hint,
        )
        node_ids: list[str] = []
        for kinship in kinships:
            normalized_label = normalize_person_label(kinship.standard_label)
            if not normalized_label:
                continue
            self._track_kinship_normalization(
                kinship,
                record_id=record_id,
                source_table=source_table,
                source_id=source_id,
            )
            node_id = f"person:{normalized_label}"
            self._upsert_node(
                node_id=node_id,
                node_type="person",
                label=kinship.standard_label,
                normalized_label=normalized_label,
                source_table=source_table,
                source_id=source_id,
                properties={
                    **dict(properties),
                    "person_kind": kinship.person_kind,
                    "kinship_type": kinship.kinship_type,
                    "raw_labels": self._person_raw_labels(label, properties, kinship),
                    "normalization_note": kinship.normalization_note,
                    "confidence": kinship.confidence,
                    "needs_review": kinship.needs_review,
                    "detected_terms": list(kinship.detected_terms),
                    "is_collective_kinship": kinship.is_collective_kinship,
                    "member_labels": list(kinship.member_labels),
                    "member_kinship_types": list(kinship.member_kinship_types),
                },
            )
            node_ids.append(node_id)
        return node_ids

    def _person_source_labels(
        self,
        label: str,
        properties: Mapping[str, Any],
    ) -> list[str]:
        values: list[Any] = [label]
        values.extend(self._as_list(properties.get("raw_labels", [])))
        values.extend(self._as_list(properties.get("original_labels", [])))
        values.extend(self._as_list(properties.get("clean_label", [])))
        return [
            clean_value
            for clean_value in self._dedupe_values(clean_text(value) for value in values)
            if clean_value
        ]

    def _person_raw_labels(
        self,
        label: str,
        properties: Mapping[str, Any],
        kinship: KinshipNormalization,
    ) -> list[str]:
        values: list[Any] = [*kinship.raw_labels, kinship.raw_label, label]
        values.extend(self._as_list(properties.get("raw_labels", [])))
        values.extend(self._as_list(properties.get("original_labels", [])))
        if kinship.person_kind == KINSHIP_TERM and kinship.detected_terms:
            values = [
                value
                for value in values
                if self._contains_detected_term(value, kinship.detected_terms)
            ]
        return [
            clean_value
            for clean_value in self._dedupe_values(clean_text(value) for value in values)
            if clean_value
        ]

    def _contains_detected_term(self, value: Any, detected_terms: Iterable[str]) -> bool:
        text = clean_text(value)
        return any(term and term in text for term in detected_terms)

    def _track_kinship_normalization(
        self,
        kinship: KinshipNormalization,
        *,
        record_id: str,
        source_table: str,
        source_id: str,
    ) -> None:
        if kinship.person_kind == KINSHIP_TERM and record_id:
            self.kinship_record_ids[record_id].add(kinship.kinship_type)
        if not kinship.needs_review:
            return
        item = self._kinship_review_items.setdefault(
            kinship.raw_label,
            {
                "raw_label": kinship.raw_label,
                "raw_labels": set(),
                "person_kind": kinship.person_kind,
                "kinship_type": kinship.kinship_type or UNKNOWN_KINSHIP_TYPE,
                "detected_terms": set(),
                "confidence": kinship.confidence,
                "count": 0,
                "record_ids": set(),
                "source_tables": set(),
                "source_ids": set(),
                "normalization_note": kinship.normalization_note,
            },
        )
        item["count"] += 1
        item["raw_labels"].update(kinship.raw_labels)
        item["detected_terms"].update(kinship.detected_terms)
        item["confidence"] = max(item["confidence"], kinship.confidence)
        if item["person_kind"] == UNKNOWN_PERSON_KIND and kinship.person_kind != UNKNOWN_PERSON_KIND:
            item["person_kind"] = kinship.person_kind
        if item["kinship_type"] in ("", UNKNOWN_KINSHIP_TYPE) and kinship.kinship_type:
            item["kinship_type"] = kinship.kinship_type
        if record_id:
            item["record_ids"].add(record_id)
        if source_table:
            item["source_tables"].add(source_table)
        if source_id:
            item["source_ids"].add(source_id)

    def _add_place_edge(
        self,
        *,
        source_node_id: str,
        edge_type: str,
        raw_label: str,
        record_id: str,
        source_table: str,
        source_id: str,
        confidence: float,
        properties: Mapping[str, Any],
        evidence_text: str = "",
    ) -> None:
        normalized_label = normalize_place_label(raw_label)
        if not normalized_label:
            return
        place_node_id = f"place:{normalized_label}"
        self._upsert_node(
            node_id=place_node_id,
            node_type="place",
            label=normalized_label,
            normalized_label=normalized_label,
            source_table=source_table,
            source_id=source_id,
            properties={
                "original_labels": [raw_label],
                **dict(properties),
            },
        )
        self._add_edge(
            source_node_id=source_node_id,
            target_node_id=place_node_id,
            edge_type=edge_type,
            record_id=record_id,
            evidence_text=evidence_text,
            source_table=source_table,
            source_id=source_id,
            confidence=confidence,
            properties={
                "original_label": raw_label,
                "normalized_label": normalized_label,
                **dict(properties),
            },
        )

    def _upsert_node(
        self,
        *,
        node_id: str,
        node_type: str,
        label: str,
        normalized_label: str,
        record_id: str = "",
        source_table: str = "",
        source_id: str = "",
        properties: Mapping[str, Any] | None = None,
    ) -> None:
        if not node_id or not label or node_type not in SUPPORTED_NODE_TYPES:
            return
        properties = self._properties(properties or {})
        existing = self.nodes.get(node_id)
        if existing is None:
            self.nodes[node_id] = KgNode(
                node_id=node_id,
                node_type=node_type,
                label=label,
                normalized_label=normalized_label,
                record_id=record_id,
                source_table=source_table,
                source_id=source_id,
                properties=properties,
            )
            return
        self.nodes[node_id] = KgNode(
            node_id=existing.node_id,
            node_type=existing.node_type,
            label=existing.label,
            normalized_label=existing.normalized_label,
            record_id=existing.record_id or record_id,
            source_table=existing.source_table or source_table,
            source_id=existing.source_id or source_id,
            properties=self._merge_properties(existing.properties, properties),
        )

    def _add_edge(
        self,
        *,
        source_node_id: str,
        target_node_id: str,
        edge_type: str,
        record_id: str = "",
        evidence_text: str = "",
        source_table: str = "",
        source_id: str = "",
        weight: float = 1.0,
        confidence: float = 0.0,
        properties: Mapping[str, Any] | None = None,
    ) -> None:
        if (
            not source_node_id
            or not target_node_id
            or source_node_id not in self.nodes
            or target_node_id not in self.nodes
            or edge_type not in SUPPORTED_EDGE_TYPES
        ):
            return
        edge_id = self._edge_id(
            edge_type=edge_type,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            record_id=record_id,
        )
        clean_evidence_text = clean_text(evidence_text)
        clean_properties = self._edge_support_properties(
            properties or {},
            evidence_text=clean_evidence_text,
            source_table=source_table,
            source_id=source_id,
            confidence=confidence,
        )
        existing = self.edges.get(edge_id)
        if existing is None:
            self.edges[edge_id] = KgEdge(
                edge_id=edge_id,
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                edge_type=edge_type,
                record_id=record_id,
                evidence_text=clean_evidence_text,
                source_table=source_table,
                source_id=source_id,
                weight=weight,
                confidence=confidence,
                properties=clean_properties,
            )
            return

        keep_new_source = confidence > existing.confidence or not existing.source_table
        self.edges[edge_id] = KgEdge(
            edge_id=edge_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            edge_type=edge_type,
            record_id=record_id,
            evidence_text=existing.evidence_text or clean_evidence_text,
            source_table=source_table if keep_new_source else existing.source_table,
            source_id=source_id if keep_new_source else existing.source_id,
            weight=max(existing.weight, weight),
            confidence=max(existing.confidence, confidence),
            properties=self._merge_properties(existing.properties, clean_properties),
        )

    def _retrieval_unit_counts(self) -> dict[str, int]:
        rows = self._fetch_rows("qiaopi_retrieval_units", order_by=("record_id", "unit_id"))
        counts: Counter[str] = Counter()
        for row in rows:
            record_id = self._value(row, "record_id")
            if record_id:
                counts[record_id] += 1
        return dict(counts)

    def _kinship_coverage(self, text_records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
        record_ids = sorted(self._value(row, "record_id") for row in text_records if self._value(row, "record_id"))
        record_has_kinship = {
            record_id: record_id in self.kinship_record_ids
            for record_id in record_ids
        }
        records_without_kinship = [
            record_id
            for record_id, has_kinship in record_has_kinship.items()
            if not has_kinship
        ]
        records_with_kinship_count = sum(1 for has_kinship in record_has_kinship.values() if has_kinship)
        record_count = len(record_ids)
        return {
            "record_count": record_count,
            "records_with_kinship_count": records_with_kinship_count,
            "records_without_kinship_count": len(records_without_kinship),
            "coverage_ratio": round(records_with_kinship_count / record_count, 6)
            if record_count
            else 0.0,
            "record_has_kinship": record_has_kinship,
            "records_without_kinship": records_without_kinship,
        }

    def _kinship_needs_review(self) -> list[dict[str, Any]]:
        review_rows: list[dict[str, Any]] = []
        for item in self._kinship_review_items.values():
            review_rows.append(
                {
                    "raw_label": item["raw_label"],
                    "raw_labels": sorted(item["raw_labels"]),
                    "person_kind": item["person_kind"],
                    "kinship_type": item["kinship_type"],
                    "detected_terms": sorted(item["detected_terms"]),
                    "confidence": item["confidence"],
                    "count": item["count"],
                    "record_ids_sample": sorted(item["record_ids"])[:10],
                    "source_tables": sorted(item["source_tables"]),
                    "source_ids_sample": sorted(item["source_ids"])[:10],
                    "normalization_note": item["normalization_note"],
                }
            )
        return sorted(review_rows, key=lambda item: (-item["count"], item["raw_label"]))

    def _linked_metadata_by_id(self, metadata_ids: list[str]) -> dict[str, Mapping[str, Any]]:
        if not metadata_ids:
            return {}
        if "qiaopi_metadata_records" not in self._initial_tables:
            return {}
        if not self._table_exists("qiaopi_metadata_records"):
            return {}
        placeholders = ", ".join("?" for _ in metadata_ids)
        rows = self.connection.execute(
            f"""
            SELECT *
            FROM qiaopi_metadata_records
            WHERE metadata_id IN ({placeholders})
            ORDER BY metadata_id
            """,
            metadata_ids,
        ).fetchall()
        return {self._value(dict(row), "metadata_id"): dict(row) for row in rows}

    def _fetch_rows(
        self,
        table_name: str,
        *,
        order_by: tuple[str, ...] = (),
        optional: bool = True,
    ) -> list[dict[str, Any]]:
        if optional and table_name not in self._initial_tables:
            return []
        if not self._table_exists(table_name):
            if optional:
                self._warn_once(f"Skipped optional table {table_name}: table does not exist.")
                return []
            self._warn_once(f"Required source table {table_name} does not exist.")
            return []
        columns = self._table_columns(table_name)
        order_columns = [column for column in order_by if column in columns]
        order_sql = ""
        if order_columns:
            quoted = ", ".join(self._quote_identifier(column) for column in order_columns)
            order_sql = f" ORDER BY {quoted}"
        rows = self.connection.execute(
            f"SELECT * FROM {self._quote_identifier(table_name)}{order_sql}"
        ).fetchall()
        return [dict(row) for row in rows]

    def _warn_missing_source_tables(self) -> None:
        if "qiaopi_text_records" not in self._initial_tables:
            self._warn_once(
                "Required source table qiaopi_text_records was not found before KG schema initialization."
            )
        for table_name in OPTIONAL_SOURCE_TABLES:
            if table_name not in self._initial_tables:
                self._warn_once(f"Skipped optional table {table_name}: table does not exist.")

    def _warn_missing_columns(self, table_name: str, columns: tuple[str, ...]) -> None:
        if table_name not in self._initial_tables:
            return
        existing_columns = self._table_columns(table_name)
        missing_columns = [column for column in columns if column not in existing_columns]
        if missing_columns:
            self._warn_once(
                f"{table_name} missing optional columns: {', '.join(missing_columns)}."
            )

    def _warn_once(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    def _list_tables(self) -> set[str]:
        rows = self.connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type IN ('table', 'view')
            """
        ).fetchall()
        return {str(row["name"]) for row in rows}

    def _table_exists(self, table_name: str) -> bool:
        row = self.connection.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type IN ('table', 'view')
                AND name = ?
            """,
            (table_name,),
        ).fetchone()
        return row is not None

    def _table_columns(self, table_name: str) -> set[str]:
        if table_name not in self._columns_cache:
            rows = self.connection.execute(
                f"PRAGMA table_info({self._quote_identifier(table_name)})"
            ).fetchall()
            self._columns_cache[table_name] = {str(row["name"]) for row in rows}
        return self._columns_cache[table_name]

    def _raw_json(self, row: Mapping[str, Any]) -> Mapping[str, Any]:
        text = self._value(row, "raw_json")
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, Mapping):
            return parsed
        return {}

    def _value(self, row: Mapping[str, Any], *columns: str) -> str:
        for column in columns:
            if column not in row:
                continue
            value = clean_text(row.get(column))
            if value:
                return value
        return ""

    def _float_value(self, row: Mapping[str, Any], column: str, default: float) -> float:
        value = self._value(row, column)
        if not value:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    def _number_or_text(self, row: Mapping[str, Any], column: str) -> float | int | str:
        value = self._value(row, column)
        if not value:
            return ""
        try:
            number = float(value)
        except ValueError:
            return value
        if number.is_integer():
            return int(number)
        return number

    def _amount_key(
        self,
        row: Mapping[str, Any],
        record_id: str,
        raw_amount: str,
    ) -> str:
        amount_number = normalize_amount_number(self._value(row, "amount_number"))
        currency = normalize_amount_raw(self._value(row, "currency"))
        raw_amount_normalized = normalize_amount_raw(raw_amount)
        if amount_number:
            parts = (record_id, amount_number, currency, raw_amount_normalized)
        else:
            parts = (record_id, raw_amount_normalized, currency)
        return "|".join(part for part in parts if part)

    def _properties(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return {
            str(key): item
            for key, item in value.items()
            if item not in (None, "", [], {})
        }

    def _edge_support_properties(
        self,
        properties: Mapping[str, Any],
        *,
        evidence_text: str,
        source_table: str,
        source_id: str,
        confidence: float,
    ) -> dict[str, Any]:
        support = self._properties(properties)
        if evidence_text:
            support["evidence_texts"] = [evidence_text]
        if source_table:
            support["source_tables"] = [source_table]
        if source_id:
            support["source_ids"] = [source_id]
        support["confidences"] = [round(float(confidence), 6)]
        raw_labels = [
            clean_text(support.get(key))
            for key in (
                "original_label",
                "amount_raw",
                "alias_text",
                "normalized_text",
                "clean_label",
            )
            if clean_text(support.get(key))
        ]
        if raw_labels:
            support["raw_labels"] = raw_labels
        support["deduplicated_count"] = 1
        return support

    def _merge_properties(
        self,
        existing: Mapping[str, Any],
        new: Mapping[str, Any],
    ) -> dict[str, Any]:
        merged = dict(existing)
        for key, value in new.items():
            if value in (None, "", [], {}):
                continue
            if key == "deduplicated_count":
                merged[key] = self._int_value(merged.get(key)) + self._int_value(value)
                continue
            if key == "person_kind":
                values = {clean_text(merged.get(key)), clean_text(value)}
                if KINSHIP_TERM in values:
                    merged[key] = KINSHIP_TERM
                elif NAMED_PERSON in values:
                    merged[key] = NAMED_PERSON
                else:
                    merged[key] = UNKNOWN_PERSON_KIND
                continue
            if key == "kinship_type":
                existing_value = clean_text(merged.get(key))
                new_value = clean_text(value)
                if existing_value not in ("", UNKNOWN_KINSHIP_TYPE, NO_KINSHIP_TYPE):
                    merged[key] = existing_value
                elif new_value not in ("", UNKNOWN_KINSHIP_TYPE, NO_KINSHIP_TYPE):
                    merged[key] = new_value
                elif NO_KINSHIP_TYPE in {existing_value, new_value}:
                    merged[key] = NO_KINSHIP_TYPE
                else:
                    merged[key] = UNKNOWN_KINSHIP_TYPE
                continue
            if key == "normalization_note":
                existing_value = clean_text(merged.get(key))
                new_value = clean_text(value)
                if not existing_value:
                    merged[key] = new_value
                elif existing_value.startswith("Named person") and not new_value.startswith("Named person"):
                    merged[key] = new_value
                elif "review recommended" in new_value and "review recommended" not in existing_value:
                    merged[key] = new_value
                continue
            if key == "confidence":
                merged[key] = max(self._float_property(merged.get(key)), self._float_property(value))
                continue
            if key == "needs_review":
                merged[key] = bool(merged.get(key)) or bool(value)
                continue
            if key == "is_collective_kinship":
                merged[key] = bool(merged.get(key)) or bool(value)
                continue
            if key in {"member_labels", "member_kinship_types"}:
                merged_values = self._as_list(merged.get(key, [])) + self._as_list(value)
                merged[key] = self._dedupe_values_preserve_order(merged_values)
                continue
            if key not in merged or merged[key] in (None, "", [], {}):
                merged[key] = value
                continue
            if isinstance(merged[key], list) or isinstance(value, list):
                merged_values = self._as_list(merged[key]) + self._as_list(value)
                merged[key] = self._dedupe_values(merged_values)
        return merged

    def _dedupe_values(self, values: Iterable[Any]) -> list[Any]:
        seen: set[str] = set()
        deduped: list[Any] = []
        for value in values:
            if value in (None, "", [], {}):
                continue
            key = json.dumps(value, ensure_ascii=False, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(value)
        return sorted(deduped, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True))

    def _dedupe_values_preserve_order(self, values: Iterable[Any]) -> list[Any]:
        seen: set[str] = set()
        deduped: list[Any] = []
        for value in values:
            if value in (None, "", [], {}):
                continue
            key = json.dumps(value, ensure_ascii=False, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(value)
        return deduped

    def _int_value(self, value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _float_property(self, value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _as_list(self, value: Any) -> list[Any]:
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        if isinstance(value, set):
            return sorted(value)
        return [value]

    def _edge_id(
        self,
        *,
        edge_type: str,
        source_node_id: str,
        target_node_id: str,
        record_id: str,
    ) -> str:
        payload = "|".join(
            (
                edge_type,
                source_node_id,
                target_node_id,
                record_id,
            )
        )
        digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:20]
        return f"edge:{edge_type}:{digest}"

    def _stable_suffix(self, *parts: str) -> str:
        payload = "|".join(clean_text(part) for part in parts)
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]

    def _quote_identifier(self, value: str) -> str:
        if not _IDENTIFIER_RE.match(value):
            raise ValueError(f"Unsafe SQLite identifier: {value}")
        return f'"{value}"'
