from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_plain_interpretation_returns_grounded_mock_response():
    response = client.post(
        "/api/generation/plain-interpretation",
        json={"record_id": "CSQP-SFHC-TEXT-001", "original_text": ""},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["generated_text"]
    assert payload["consistency_check"]["status"] == "passed"
    assert payload["evidence_mapping"]


def test_style_transfer_returns_qiaopi_style_response():
    response = client.post(
        "/api/generation/style-transfer",
        json={
            "plain_text": "Mother, I am safe in Singapore and send eight yuan home.",
            "slots": {"recipient": "mother", "money": "eight yuan"},
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["generated_text"]
    assert payload["slots"]["money"] == "eight yuan"

