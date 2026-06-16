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


def test_text_database_populates_normalized_place_fields():
    with get_connection() as connection:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(qiaopi_text_records)").fetchall()
        }
        row = connection.execute(
            """
            SELECT
                origin_place,
                destination_place,
                country_or_region,
                place_mentions_normalized,
                raw_json
            FROM qiaopi_text_records
            WHERE record_id = 'CSQP-SFHC-TEXT-017'
            """
        ).fetchone()

    assert {"origin_place", "destination_place", "country_or_region"}.issubset(columns)
    assert row["origin_place"] == "越南"
    assert row["destination_place"] == "广东潮安"
    assert row["country_or_region"] == "越南；广东侨乡"
    assert row["place_mentions_normalized"] == "越南；广东潮安"
    assert '"origin_place": "越南"' in row["raw_json"]


def test_text_database_populates_standard_dates_without_overwriting_raw_dates():
    with get_connection() as connection:
        traditional_row = connection.execute(
            """
            SELECT
                date_text,
                year_normalized,
                date_standard,
                date_year,
                date_month,
                date_day,
                date_precision,
                date_calendar,
                date_parse_confidence,
                date_parse_note
            FROM qiaopi_text_records
            WHERE record_id = 'CSQP-SFHC-TEXT-017'
            """
        ).fetchone()
        no_year_row = connection.execute(
            """
            SELECT
                date_text,
                date_standard,
                date_year,
                date_month,
                date_day,
                date_precision
            FROM qiaopi_text_records
            WHERE record_id = 'CSQP-SFHC-TEXT-144'
            """
        ).fetchone()

    assert traditional_row["date_text"] == "癸九月十一日"
    assert traditional_row["year_normalized"] == "1933"
    assert traditional_row["date_standard"] == "1933.9.11"
    assert traditional_row["date_year"] == 1933
    assert traditional_row["date_month"] == 9
    assert traditional_row["date_day"] == 11
    assert traditional_row["date_precision"] == "day"
    assert traditional_row["date_calendar"] == "traditional_lunar_text"
    assert traditional_row["date_parse_confidence"] == 0.85
    assert "not converted to exact Gregorian calendar date" in traditional_row["date_parse_note"]

    assert no_year_row["date_text"] == "九月十日（民国）"
    assert no_year_row["date_standard"] == ""
    assert no_year_row["date_year"] is None
    assert no_year_row["date_month"] == 9
    assert no_year_row["date_day"] == 10
    assert no_year_row["date_precision"] == "month_day_no_year"
