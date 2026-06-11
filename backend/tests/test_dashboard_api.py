from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_health_endpoint_still_works():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_dashboard_stats_return_real_counts():
    response = client.get("/api/dashboard/stats")

    payload = response.json()
    assert response.status_code == 200
    assert payload["total_text_records"] == 213
    assert payload["full_text_count"] > 0
    assert payload["metadata_only_count"] > 0
    assert payload["retrieval_unit_count"] > payload["total_text_records"]
    assert payload["fts_row_count"] == payload["retrieval_unit_count"]
    assert payload["amount_mention_count"] > 0
    assert payload["entity_mention_count"] > 0
    assert payload["place_mention_count"] > 0
    assert payload["evidence_count"] > 0
    assert payload["remittance_record_count"] > 0


def test_dashboard_distributions_return_expected_dimensions():
    response = client.get("/api/dashboard/distributions")

    payload = response.json()
    assert response.status_code == 200
    for key in (
        "text_quality_distribution",
        "main_intent_distribution",
        "relationship_distribution",
        "unit_type_distribution",
        "top_places",
        "top_countries_or_regions",
        "year_distribution",
    ):
        assert payload[key], key
        assert {"label", "value"}.issubset(payload[key][0])
