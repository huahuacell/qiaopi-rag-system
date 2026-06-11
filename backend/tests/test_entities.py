from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_record_detail_returns_real_text_fields():
    response = client.get("/api/records/CSQP-SFHC-TEXT-017")

    payload = response.json()
    assert response.status_code == 200
    assert payload["record_id"] == "CSQP-SFHC-TEXT-017"
    assert payload["title_reference"]
    assert payload["body_core"]


def test_record_entities_endpoint_returns_extracted_entities():
    response = client.get("/api/records/CSQP-SFHC-TEXT-017/entities")

    payload = response.json()
    assert response.status_code == 200
    assert payload["entities"]
    assert any(entity["entity_type"] for entity in payload["entities"])
