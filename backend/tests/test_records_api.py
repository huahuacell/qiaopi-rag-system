from fastapi.testclient import TestClient

from main import app


client = TestClient(app)
RECORD_ID = "CSQP-SFHC-TEXT-017"


def test_record_detail_returns_real_record():
    response = client.get(f"/api/records/{RECORD_ID}")

    payload = response.json()
    assert response.status_code == 200
    assert payload["record_id"] == RECORD_ID
    assert payload["title_reference"]
    assert payload["body_clean"]
    assert payload["raw_fields"]["record_id"] == RECORD_ID


def test_record_auxiliary_endpoints_return_rows():
    endpoints = {
        "amounts": "amounts",
        "entities": "entities",
        "places": "places",
        "evidence": "evidence",
        "retrieval-units": "retrieval_units",
    }

    for path, response_key in endpoints.items():
        response = client.get(f"/api/records/{RECORD_ID}/{path}")
        payload = response.json()
        assert response.status_code == 200, path
        assert payload["record_id"] == RECORD_ID
        assert payload[response_key], path


def test_record_not_found_returns_404():
    response = client.get("/api/records/CSQP-SFHC-TEXT-999999")

    assert response.status_code == 404
