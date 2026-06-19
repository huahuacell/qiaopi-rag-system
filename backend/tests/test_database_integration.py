from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_dashboard_reads_real_sqlite_counts_and_distributions():
    stats_response = client.get("/api/dashboard/stats")
    distributions_response = client.get("/api/dashboard/distributions")

    assert stats_response.status_code == 200
    assert distributions_response.status_code == 200
    assert stats_response.json()["total_text_records"] == 213
    assert stats_response.json()["metadata_record_count"] >= 0
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
    assert "奉大良" in detail.json()["body_clean"]
    assert any(item["value"] == "林序周" for item in entities.json()["entities"])
    assert any(item["evidence_type"] == "remittance" for item in evidence.json()["evidence"])


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
    assert payload["results"]
    assert payload["fusion_method"] == "keyword_fallback"
    assert payload["semantic_enabled"] is False
    assert all(item["retrieval_sources"] == ["keyword"] for item in payload["results"])
    assert all(item["matched_reason"] for item in payload["results"])


def test_interpretation_preview_is_grounded_in_database_record():
    response = client.post(
        "/api/generation/interpret",
        json={
            "query": "这封侨批主要说了什么？",
            "record_id": "CSQP-SFHC-TEXT-002",
            "top_k": 8,
            "filters": {},
            "expansion_mode": "balanced",
            "dry_run": True,
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["record_id"] == "CSQP-SFHC-TEXT-002"
    assert payload["dry_run"] is True
    assert payload["prompt_context"]
    assert payload["evidence_references"]
    assert all(
        item["record_id"] == "CSQP-SFHC-TEXT-002"
        for item in payload["evidence_references"]
    )
