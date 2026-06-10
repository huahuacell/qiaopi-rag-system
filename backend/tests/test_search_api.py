from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_keyword_search_returns_retrieval_unit_results():
    response = client.post(
        "/api/search/keyword",
        json={
            "query": "母亲 寄款 查收",
            "top_k": 5,
            "unit_types": [],
            "filters": {},
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["query"] == "母亲 寄款 查收"
    assert payload["top_k"] == 5
    assert payload["results"]

    result = payload["results"][0]
    assert result["record_id"].startswith("CSQP-SFHC-TEXT-")
    assert result["unit_id"]
    assert result["unit_type"]
    assert result["unit_text"]
    assert result["snippet"]
    assert "bm25_score" in result
    assert "source_column" in result


def test_keyword_search_can_filter_unit_types():
    response = client.post(
        "/api/search/keyword",
        json={
            "query": "母亲 寄款 查收",
            "top_k": 5,
            "unit_types": ["remittance"],
            "filters": {},
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["results"]
    assert all(result["unit_type"] == "remittance" for result in payload["results"])
