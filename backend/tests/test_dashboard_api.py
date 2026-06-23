from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_health_endpoint_still_works():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_dashboard_stats_return_real_counts():
    response = client.get("/api/dashboard/stats")

    payload = response.json()
    assert response.status_code == 200
    assert payload["total_text_records"] == 213
    assert payload["full_text_count"] > 0
    assert payload["metadata_only_count"] > 0
    assert payload["retrieval_unit_count"] > payload["total_text_records"]
    assert payload["fts_row_count"] == payload["retrieval_unit_count"]
    assert payload["amount_mention_count"] > 0
    assert payload["entity_mention_count"] > 0
    assert payload["place_mention_count"] > 0
    assert payload["evidence_count"] > 0
    assert payload["remittance_record_count"] > 0


def test_dashboard_distributions_return_expected_dimensions():
    response = client.get("/api/dashboard/distributions")

    payload = response.json()
    assert response.status_code == 200
    for key in (
        "text_quality_distribution",
        "main_intent_distribution",
        "relationship_distribution",
        "unit_type_distribution",
        "top_places",
        "top_countries_or_regions",
        "year_distribution",
    ):
        assert payload[key], key
        assert {"label", "value"}.issubset(payload[key][0])


def test_emotion_analysis_returns_pytorch_multilabel_evidence():
    response = client.get("/api/analysis/emotions")

    payload = response.json()
    assert response.status_code == 200
    assert payload["total_records"] == 213
    assert payload["analyzed_records"] > 0
    assert payload["analyzed_segments"] > payload["analyzed_records"]
    assert payload["multi_label_records"] > 0
    assert payload["dominant_emotion_label"]
    assert payload["model"]["model_version"] == "qiaopi-emotion-pytorch-v1.0.0"
    assert payload["model"]["engine"] in {
        "pytorch",
        "python_compatible_fallback",
    }
    assert len(payload["label_distribution"]) == 7
    assert {item["key"] for item in payload["valence_distribution"]} == {
        "positive",
        "neutral",
        "negative",
        "mixed",
    }
    assert payload["evidence_examples"]
    assert all(item["record_id"] for item in payload["evidence_examples"])
    assert all(item["text"] for item in payload["evidence_examples"])
    assert all("—" in item["period"] for item in payload["time_trend"])
    evidence_count_by_emotion = {
        emotion_key: sum(
            item["emotion_key"] == emotion_key
            for item in payload["evidence_examples"]
        )
        for emotion_key in {
            item["emotion_key"] for item in payload["evidence_examples"]
        }
    }
    assert all(count <= 9 for count in evidence_count_by_emotion.values())
