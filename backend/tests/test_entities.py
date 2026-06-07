from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_record_detail_returns_entities_and_evidence():
    response = client.get("/api/records/CSQP-SFHC-TEXT-001")

    payload = response.json()
    assert response.status_code == 200
    assert payload["record_id"] == "CSQP-SFHC-TEXT-001"
    assert payload["entities"]
    assert payload["evidence"]


def test_record_entities_endpoint_returns_money_entity():
    response = client.get("/api/records/CSQP-SFHC-TEXT-001/entities")

    payload = response.json()
    assert response.status_code == 200
    assert any(entity["entity_type"] == "money" for entity in payload["entities"])

