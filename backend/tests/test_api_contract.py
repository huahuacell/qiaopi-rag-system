from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


EXPECTED_OPERATIONS = {
    ("GET", "/api/health"),
    ("GET", "/api/dashboard/stats"),
    ("GET", "/api/dashboard/distributions"),
    ("POST", "/api/search/keyword"),
    ("POST", "/api/search/advanced"),
    ("GET", "/api/search/semantic/status"),
    ("POST", "/api/search/semantic"),
    ("POST", "/api/search/hybrid"),
    ("POST", "/api/rag/context"),
    ("POST", "/api/rag/style-context"),
    ("GET", "/api/generation/qwen-status"),
    ("POST", "/api/generation/preview-prompt"),
    ("POST", "/api/generation/interpret"),
    ("POST", "/api/generation/style-transfer"),
    ("POST", "/api/validation/consistency-check"),
    ("GET", "/api/metadata/stats"),
    ("GET", "/api/metadata/distributions"),
    ("POST", "/api/metadata/search"),
    ("GET", "/api/metadata/links/stats"),
    ("GET", "/api/metadata/{metadata_id}"),
    ("GET", "/api/metadata/{metadata_id}/linked-text"),
    ("GET", "/api/records/{record_id}"),
    ("GET", "/api/records/{record_id}/amounts"),
    ("GET", "/api/records/{record_id}/entities"),
    ("GET", "/api/records/{record_id}/places"),
    ("GET", "/api/records/{record_id}/evidence"),
    ("GET", "/api/records/{record_id}/retrieval-units"),
    ("GET", "/api/graph/stats"),
    ("GET", "/api/graph/record/{record_id}"),
    ("GET", "/api/graph/node/{node_id}/neighbors"),
    ("GET", "/api/graph/overview"),
    ("GET", "/api/graph/flows/places"),
}

# The digest covers request parameters/bodies, response schemas, validation
# constraints, defaults, enums, and every component schema exposed by OpenAPI.
# Update it only together with docs/api_contract.md and affected clients/tests.
EXPECTED_CONTRACT_SHA256 = "5a064a0b4375fb752ac7048d782f8368f9131d88a48ee95cf48e105b02b90efd"


def _public_operations(openapi_schema: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (method.upper(), path)
        for path, operations in openapi_schema["paths"].items()
        for method in operations
        if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}
    }


def _contract_snapshot(openapi_schema: dict[str, Any]) -> dict[str, Any]:
    public_methods = {"get", "post", "put", "patch", "delete"}
    paths: dict[str, Any] = {}
    for path, operations in sorted(openapi_schema["paths"].items()):
        paths[path] = {}
        for method, operation in sorted(operations.items()):
            if method not in public_methods:
                continue
            paths[path][method] = {
                "parameters": operation.get("parameters", []),
                "requestBody": operation.get("requestBody"),
                "responses": operation.get("responses", {}),
            }
    return {
        "paths": paths,
        "schemas": openapi_schema.get("components", {}).get("schemas", {}),
    }


def _contract_digest(openapi_schema: dict[str, Any]) -> str:
    encoded = json.dumps(
        _contract_snapshot(openapi_schema),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def test_openapi_routes_match_converged_contract():
    assert _public_operations(app.openapi()) == EXPECTED_OPERATIONS


def test_openapi_schema_matches_converged_contract():
    actual_digest = _contract_digest(app.openapi())
    assert actual_digest == EXPECTED_CONTRACT_SHA256, (
        "The public OpenAPI contract changed. If this is intentional, update "
        "docs/api_contract.md, affected frontend clients/mocks, integration "
        "tests, and EXPECTED_CONTRACT_SHA256 in the same change. "
        f"Actual digest: {actual_digest}"
    )


def test_retired_scaffold_routes_are_not_advertised():
    operations = _public_operations(app.openapi())
    assert ("POST", "/api/generation/plain-interpretation") not in operations
    assert ("GET", "/api/records/{record_id}/similar") not in operations


def test_retired_scaffold_routes_return_not_found():
    interpretation_response = client.post(
        "/api/generation/plain-interpretation",
        json={"record_id": "CSQP-SFHC-TEXT-017", "original_text": ""},
    )
    similar_response = client.get("/api/records/CSQP-SFHC-TEXT-017/similar")

    assert interpretation_response.status_code == 404
    assert similar_response.status_code == 404
