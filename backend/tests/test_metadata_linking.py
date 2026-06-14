from app.database.repository import fetch_metadata_link_stats
from app.ingestion.link_metadata_text_records import link_metadata_text_records


def test_metadata_linking_is_deterministic_and_reports_counts(metadata_layer_ready):
    first_run = metadata_layer_ready["link_stats"]
    second_run = link_metadata_text_records()
    stats = fetch_metadata_link_stats()

    assert first_run["full_text_record_count"] == 213
    assert second_run["auto_link_count"] == first_run["auto_link_count"]
    assert second_run["candidate_link_count"] == first_run["candidate_link_count"]
    assert stats["auto_link_count"] == second_run["auto_link_count"]
    assert stats["candidate_link_count"] == second_run["candidate_link_count"]
    assert stats["unlinked_full_text_count"] == 213 - stats["auto_link_count"]
