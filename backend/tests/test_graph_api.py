from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app.ingestion.build_knowledge_graph import build_knowledge_graph
from main import app


client = TestClient(app)
RECORD_ID = "CSQP-SFHC-TEXT-017"


@pytest.fixture(scope="module", autouse=True)
def graph_api_ready(metadata_layer_ready):
    build_knowledge_graph()


def test_graph_stats_returns_counts():
    response = client.get("/api/graph/stats")

    payload = response.json()
    assert response.status_code == 200
    assert payload["node_count"] > 0
    assert payload["edge_count"] > 0
    assert payload["node_type_distribution"]["record"] >= 1
    assert payload["edge_type_distribution"]
    assert payload["quality"]["duplicate_logical_edge_count"] == 0
    assert payload["quality"]["orphan_edge_count"] == 0
    assert payload["quality"]["missing_node_provenance_count"] == 0
    assert payload["quality"]["missing_edge_provenance_count"] == 0


def test_graph_record_returns_connected_nodes_and_edges():
    response = client.get(f"/api/graph/record/{RECORD_ID}")

    payload = response.json()
    assert response.status_code == 200
    assert payload["record_id"] == RECORD_ID
    assert payload["nodes"]
    assert payload["edges"]
    assert {node["id"] for node in payload["nodes"]} >= {f"record:{RECORD_ID}"}
    assert {
        "id",
        "label",
        "type",
        "category",
        "source_table",
        "source_id",
        "properties",
    }.issubset(payload["nodes"][0])
    assert {
        "id",
        "source",
        "target",
        "type",
        "label",
        "source_table",
        "source_id",
        "properties",
    }.issubset(payload["edges"][0])


def test_graph_record_exposes_traceable_evidence_and_metadata_nodes():
    response = client.get("/api/graph/record/CSQP-SFHC-TEXT-063")

    payload = response.json()
    assert response.status_code == 200
    evidence_nodes = [node for node in payload["nodes"] if node["type"] == "evidence"]
    metadata_nodes = [
        node for node in payload["nodes"] if node["type"] == "metadata_record"
    ]
    assert evidence_nodes
    assert metadata_nodes
    assert all(
        node["source_table"] == "qiaopi_evidence_spans" and node["source_id"]
        for node in evidence_nodes
    )
    assert all(
        node["source_table"] == "qiaopi_metadata_records"
        and node["source_id"].startswith("CSQP-META-")
        for node in metadata_nodes
    )


def test_graph_record_includes_global_connected_nodes():
    response = client.get(f"/api/graph/record/{RECORD_ID}")

    payload = response.json()
    assert response.status_code == 200
    assert any(
        node["type"] in {"person", "place", "theme"}
        and node["record_id"] in {"", None}
        for node in payload["nodes"]
    )


def test_graph_record_missing_returns_404():
    response = client.get("/api/graph/record/CSQP-SFHC-TEXT-999999")

    assert response.status_code == 404


def test_graph_node_neighbors_returns_local_graph():
    node_id = "person:母亲"
    response = client.get(f"/api/graph/node/{quote(node_id, safe='')}/neighbors?limit=20")

    payload = response.json()
    assert response.status_code == 200
    assert payload["node_id"] == node_id
    assert payload["center_node"]["id"] == node_id
    assert payload["nodes"]
    assert payload["edges"]
    assert len(payload["edges"]) <= 20


def test_graph_node_neighbors_missing_returns_404():
    response = client.get("/api/graph/node/person%3Amissing-never-used/neighbors")

    assert response.status_code == 404


def test_graph_overview_is_limited():
    response = client.get("/api/graph/overview?limit_nodes=20&limit_edges=30")

    payload = response.json()
    assert response.status_code == 200
    assert 0 < len(payload["nodes"]) <= 20
    assert len(payload["edges"]) <= 30
    assert payload["summary"]["limit_nodes"] == 20
    assert payload["summary"]["limit_edges"] == 30
    assert all("category" in node for node in payload["nodes"])


def test_graph_place_flows_returns_valid_list():
    response = client.get("/api/graph/flows/places?limit=10")

    payload = response.json()
    assert response.status_code == 200
    assert isinstance(payload["flows"], list)
    assert payload["flows"]
    assert len(payload["flows"]) <= 10
    assert {
        "origin_place",
        "destination_place",
        "count",
        "record_ids_sample",
    }.issubset(payload["flows"][0])
    assert len(payload["flows"][0]["record_ids_sample"]) <= 5


def test_graph_api_step_has_no_neo4j_modules():
    repo_root = Path(__file__).resolve().parents[2]

    assert not (repo_root / "backend" / "app" / "graph" / "neo4j_exporter.py").exists()
    assert not (repo_root / "backend" / "app" / "graph" / "neo4j_importer.py").exists()
    assert (repo_root / "frontend").exists()
