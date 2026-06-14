import pytest
from fastapi.testclient import TestClient

from app.database.connection import get_connection
from main import app


client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def build_metadata_layer(metadata_layer_ready):
    return metadata_layer_ready


def test_metadata_stats_endpoint_works(metadata_layer_ready):
    response = client.get("/api/metadata/stats")

    payload = response.json()
    assert response.status_code == 200
    assert payload["total_metadata_records"] > 50000
    assert payload["unlinked_metadata_count"] >= 0
    assert payload["link_candidate_count"] >= 0
    assert payload["year_min"] is None or payload["year_min"] >= 1800


def test_metadata_distributions_endpoint_works():
    response = client.get("/api/metadata/distributions")

    payload = response.json()
    assert response.status_code == 200
    assert payload["year_distribution"]
    assert payload["country_or_region_distribution"]
    assert payload["theme_distribution"]
    assert {"label", "value"}.issubset(payload["country_or_region_distribution"][0])


def test_metadata_search_returns_results():
    response = client.post(
        "/api/metadata/search",
        json={
            "query": "新加坡 母亲 寄款",
            "top_k": 5,
            "filters": {"has_linked_text": False},
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["query"] == "新加坡 母亲 寄款"
    assert payload["results"]
    result = payload["results"][0]
    assert result["metadata_id"].startswith("CSQP-META-")
    assert "score" in result
    assert "snippet" in result


def test_metadata_detail_endpoint_returns_raw_json():
    response = client.get("/api/metadata/CSQP-META-000001")

    payload = response.json()
    assert response.status_code == 200
    assert payload["metadata_id"] == "CSQP-META-000001"
    assert payload["title_raw"]
    assert isinstance(payload["raw_json"], dict)


def test_metadata_linked_text_endpoint_returns_controlled_response():
    with get_connection() as connection:
        linked_row = connection.execute(
            "SELECT metadata_id FROM qiaopi_metadata_records WHERE has_linked_text = 1 LIMIT 1"
        ).fetchone()
        unlinked_row = connection.execute(
            "SELECT metadata_id FROM qiaopi_metadata_records WHERE has_linked_text = 0 LIMIT 1"
        ).fetchone()

    linked_metadata_id = linked_row["metadata_id"] if linked_row else unlinked_row["metadata_id"]
    linked_response = client.get(f"/api/metadata/{linked_metadata_id}/linked-text")
    linked_payload = linked_response.json()
    assert linked_response.status_code == 200
    assert "has_linked_text" in linked_payload
    if linked_payload["has_linked_text"]:
        assert linked_payload["linked_record_id"].startswith("CSQP-SFHC-TEXT-")
        assert linked_payload["record_detail_summary"]["record_id"] == linked_payload["linked_record_id"]

    unlinked_response = client.get(f"/api/metadata/{unlinked_row['metadata_id']}/linked-text")
    unlinked_payload = unlinked_response.json()
    assert unlinked_response.status_code == 200
    assert unlinked_payload["has_linked_text"] is False
    assert "no linked full-text" in unlinked_payload["message"]


def test_metadata_links_stats_endpoint_works():
    response = client.get("/api/metadata/links/stats")

    payload = response.json()
    assert response.status_code == 200
    assert payload["auto_link_count"] >= 0
    assert payload["candidate_link_count"] >= 0
    assert payload["unlinked_full_text_count"] >= 0
    assert "average_link_confidence" in payload
