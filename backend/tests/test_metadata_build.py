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
