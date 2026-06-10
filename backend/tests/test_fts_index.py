from app.database.connection import get_connection
from app.database.repository import count_rows
from app.ingestion.build_database import build_database
from app.search.fts_index import search_fts


def test_fts_index_is_populated_and_search_returns_units():
    stats = build_database()

    with get_connection() as connection:
        assert count_rows(connection, "qiaopi_retrieval_units_fts") == stats["retrieval_unit_count"]

        results = search_fts(connection, "母亲 寄款 查收", top_k=5)
        assert results
        assert {
            "unit_id",
            "record_id",
            "unit_type",
            "title_reference",
            "sender",
            "recipient",
            "unit_text",
            "score",
            "evidence_type",
        }.issubset(results[0])
        assert results[0]["unit_id"]
        assert results[0]["unit_text"]


def test_core_chinese_queries_return_results_when_supported():
    build_database()

    with get_connection() as connection:
        for query in ("母亲 寄款 查收", "读书 勤俭", "新加坡 平安"):
            assert search_fts(connection, query, top_k=5), query


def test_rebuilding_database_twice_does_not_duplicate_rows():
    first_stats = build_database()
    second_stats = build_database()

    assert second_stats["text_record_count"] == first_stats["text_record_count"] == 213
    assert second_stats["retrieval_unit_count"] == first_stats["retrieval_unit_count"]
    assert second_stats["fts_row_count"] == first_stats["fts_row_count"]

    with get_connection() as connection:
        assert count_rows(connection, "qiaopi_text_records") == 213
        assert count_rows(connection, "qiaopi_retrieval_units") == second_stats["retrieval_unit_count"]
        assert count_rows(connection, "qiaopi_retrieval_units_fts") == second_stats["fts_row_count"]
