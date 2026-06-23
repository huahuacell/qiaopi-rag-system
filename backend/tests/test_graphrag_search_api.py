from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import settings
from app.ingestion.build_knowledge_graph import build_knowledge_graph
from main import app


client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def graph_rag_ready(metadata_layer_ready):
    build_knowledge_graph()


def test_graph_rag_uses_graph_and_returns_traceable_paths():
    response = client.post(
        "/api/search/graphrag",
        json={
            "query": "新加坡 祖母 寄款",
            "top_k": 8,
            "unit_types": [],
            "filters": {},
            "expansion_mode": "balanced",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["graph_enabled"] is True
    assert payload["graph_fallback"] is False
    assert payload["fusion_method"] == "graph_rrf"
    assert payload["graph_candidate_count"] > 0
    assert {seed["label"] for seed in payload["graph_seed_nodes"]} >= {
        "祖母",
        "新加坡",
        "remittance",
    }
    assert payload["results"]
    graph_results = [
        result for result in payload["results"] if "graph" in result["retrieval_sources"]
    ]
    assert graph_results
    assert graph_results[0]["graph_score"] > 0
    assert graph_results[0]["graph_seed_count"] >= 1
    assert graph_results[0]["graph_paths"]
    assert graph_results[0]["graph_paths"][0]["record_id"] == graph_results[0]["record_id"]
    assert "查询词" in graph_results[0]["graph_paths"][0]["path_text"]


def test_graph_rag_prioritizes_multi_seed_record():
    response = client.post(
        "/api/search/graphrag",
        json={
            "query": "弟弟 读书 家用",
            "top_k": 5,
            "unit_types": [],
            "filters": {},
            "expansion_mode": "balanced",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["graph_enabled"] is True
    assert payload["results"][0]["record_id"] == "CSQP-SFHC-TEXT-150"
    assert payload["results"][0]["graph_seed_count"] >= 2


def test_graph_rag_falls_back_without_graph_seed():
    response = client.post(
        "/api/search/graphrag",
        json={
            "query": "天气如何",
            "top_k": 5,
            "unit_types": [],
            "filters": {},
            "expansion_mode": "balanced",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["graph_enabled"] is False
    assert payload["graph_fallback"] is True
    assert payload["graph_fallback_reason"]
    assert payload["graph_seed_nodes"] == []


def test_graph_rag_can_be_disabled_without_breaking_search(monkeypatch):
    monkeypatch.setattr(settings, "GRAPH_RAG_ENABLED", False)

    response = client.post(
        "/api/search/graphrag",
        json={
            "query": "母亲 寄款",
            "top_k": 5,
            "unit_types": [],
            "filters": {},
            "expansion_mode": "balanced",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["graph_enabled"] is False
    assert payload["graph_fallback"] is True
    assert payload["results"]
