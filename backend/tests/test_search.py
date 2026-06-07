from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_keyword_search_returns_mock_results():
    response = client.post(
        "/api/search/keyword",
        json={"query": "eight yuan", "filters": {}, "page": 1, "page_size": 10},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["mode"] == "keyword"
    assert payload["total"] >= 1
    assert payload["results"][0]["record_id"].startswith("CSQP-")


def test_semantic_search_returns_stable_shape():
    response = client.post(
        "/api/search/semantic",
        json={"query": "letter to mother", "filters": {}, "page": 1, "page_size": 10},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["mode"] == "semantic"
    assert "evidence" in payload["results"][0]

