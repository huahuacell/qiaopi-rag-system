from app.database.connection import get_connection
from app.database.repository import count_rows


def test_metadata_database_can_be_built_from_real_catalog_file(metadata_layer_ready):
    stats = metadata_layer_ready["metadata_stats"]

    assert stats["metadata_record_count"] > 50000
    assert stats["fts_row_count"] == stats["metadata_record_count"]

    with get_connection() as connection:
        assert count_rows(connection, "qiaopi_metadata_records") == stats["metadata_record_count"]
        assert count_rows(connection, "qiaopi_metadata_fts") == stats["metadata_record_count"]
        assert count_rows(connection, "qiaopi_retrieval_units") < stats["metadata_record_count"]
        assert count_rows(connection, "qiaopi_retrieval_units") == 1959


def test_metadata_database_populates_standard_dates_without_overwriting_raw_dates(metadata_layer_ready):
    with get_connection() as connection:
        roc_row = connection.execute(
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
                date_parse_confidence
            FROM qiaopi_metadata_records
            WHERE metadata_id = 'CSQP-META-000001'
            """
        ).fetchone()
        month_day_row = connection.execute(
            """
            SELECT
                date_text,
                date_standard,
                date_year,
                date_month,
                date_day,
                date_precision
            FROM qiaopi_metadata_records
            WHERE metadata_id = 'CSQP-META-000004'
            """
        ).fetchone()
        unknown_row = connection.execute(
            """
            SELECT date_text, date_standard, date_precision, date_calendar, date_parse_confidence
            FROM qiaopi_metadata_records
            WHERE metadata_id = 'CSQP-META-000003'
            """
        ).fetchone()

    assert roc_row["date_text"] == "[民国卅六年壹月二日]"
    assert roc_row["year_normalized"] == "1947"
    assert roc_row["date_standard"] == "1947.1.2"
    assert roc_row["date_year"] == 1947
    assert roc_row["date_month"] == 1
    assert roc_row["date_day"] == 2
    assert roc_row["date_precision"] == "day"
    assert roc_row["date_calendar"] == "roc"
    assert roc_row["date_parse_confidence"] >= 0.9

    assert month_day_row["date_text"] == "七月十五日"
    assert month_day_row["date_standard"] == ""
    assert month_day_row["date_year"] is None
    assert month_day_row["date_month"] == 7
    assert month_day_row["date_day"] == 15
    assert month_day_row["date_precision"] == "month_day_no_year"

    assert unknown_row["date_text"] == "[不详]"
    assert unknown_row["date_standard"] == ""
    assert unknown_row["date_precision"] == "unknown"
    assert unknown_row["date_calendar"] == "unknown"
    assert unknown_row["date_parse_confidence"] == 0.0
