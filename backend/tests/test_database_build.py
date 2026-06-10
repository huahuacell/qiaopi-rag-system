from app.database.connection import get_connection
from app.database.repository import count_rows, list_tables
from app.database.schema import TABLES
from app.ingestion.build_database import build_database


def test_database_can_be_built_with_expected_tables():
    stats = build_database()

    assert stats["text_record_count"] == 213
    assert stats["amount_mention_count"] > 0
    assert stats["entity_mention_count"] > 0
    assert stats["place_mention_count"] > 0
    assert stats["evidence_span_count"] > 0
    assert stats["retrieval_unit_count"] > stats["text_record_count"]
    assert stats["fts_row_count"] == stats["retrieval_unit_count"]

    with get_connection() as connection:
        table_names = set(list_tables(connection))
        assert set(TABLES).issubset(table_names)
        assert "qiaopi_retrieval_units_fts" in table_names
        assert count_rows(connection, "qiaopi_text_records") == 213
        assert count_rows(connection, "qiaopi_retrieval_units") > 213
        assert count_rows(connection, "qiaopi_retrieval_units_fts") > 213
