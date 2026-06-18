from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_dashboard_reads_real_sqlite_counts_and_distributions():
    stats_response = client.get("/api/dashboard/stats")
    distributions_response = client.get("/api/dashboard/distributions")

    assert stats_response.status_code == 200
    assert distributions_response.status_code == 200
    assert stats_response.json()["total_records"] == 50064
    assert stats_response.json()["text_records"] == 213
    assert distributions_response.json()["top_places"]
    assert distributions_response.json()["relationship_distribution"]


def test_record_detail_entities_and_evidence_come_from_sqlite():
    record_id = "CSQP-SFHC-TEXT-002"
    detail = client.get(f"/api/records/{record_id}")
    entities = client.get(f"/api/records/{record_id}/entities")
    evidence = client.get(f"/api/records/{record_id}/evidence")

    assert detail.status_code == 200
    assert entities.status_code == 200
    assert evidence.status_code == 200
    assert "奉大良" in detail.json()["original_text"]
    assert any(item["value"] == "林序周" for item in entities.json()["entities"])
    assert any(item["reason"] == "remittance" for item in evidence.json()["evidence"])


def test_default_frontend_hybrid_search_returns_database_record():
    response = client.post(
        "/api/search/hybrid",
        json={
            "query": "八元 母亲 新加坡",
            "filters": {"origin_place": "新加坡", "kinship": "母亲"},
            "top_k": 10,
            "expansion_mode": "balanced",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["total"] > 0
    assert payload["results"][0]["record_id"] == "CSQP-SFHC-TEXT-002"
    assert "SQLite FTS5" in payload["results"][0]["evidence"][0]["reason"]


def test_plain_interpretation_is_grounded_in_database_record():
    response = client.post(
        "/api/generation/plain-interpretation",
        json={"record_id": "CSQP-SFHC-TEXT-002", "original_text": ""},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["evidence"]
    assert "record_loaded_from_sqlite" in payload["consistency_check"]["passed_rules"]
