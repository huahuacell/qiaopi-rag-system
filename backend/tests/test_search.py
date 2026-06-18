from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_keyword_search_uses_sqlite_fts_results():
    response = client.post(
        "/api/search/keyword",
        json={"query": "新加坡 平安", "top_k": 3, "unit_types": [], "filters": {}},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["results"]
    assert payload["results"][0]["unit_id"].startswith("CSQP-SFHC-TEXT-")
    assert payload["results"][0]["record_id"].startswith("CSQP-SFHC-TEXT-")
