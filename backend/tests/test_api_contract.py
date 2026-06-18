from main import app


EXPECTED_ROUTES = {
    ("GET", "/api/health"),
    ("GET", "/api/dashboard/stats"),
    ("GET", "/api/dashboard/distributions"),
    ("POST", "/api/search/keyword"),
    ("POST", "/api/search/semantic"),
    ("POST", "/api/search/hybrid"),
    ("GET", "/api/records/{record_id}"),
    ("GET", "/api/records/{record_id}/entities"),
    ("GET", "/api/records/{record_id}/evidence"),
    ("GET", "/api/records/{record_id}/similar"),
    ("POST", "/api/generation/plain-interpretation"),
    ("POST", "/api/generation/style-transfer"),
}


EXPECTED_SCHEMAS = {
    "HealthResponse": {
        "properties": {"status", "version", "message"},
        "required": {"status", "version", "message"},
    },
    "DashboardStatsResponse": {
        "properties": {
            "total_records",
            "text_records",
            "origin_places",
            "destination_places",
            "kinship_distribution",
            "money_distribution",
            "timeline",
        },
        "required": {
            "total_records",
            "text_records",
            "origin_places",
            "destination_places",
            "kinship_distribution",
            "money_distribution",
            "timeline",
        },
    },
    "DashboardDistributionsResponse": {
        "properties": {
            "top_places",
            "relationship_distribution",
            "year_distribution",
        },
        "required": {
            "top_places",
            "relationship_distribution",
            "year_distribution",
        },
    },
    "SearchRequest": {
        "properties": {
            "query",
            "filters",
            "page",
            "page_size",
            "top_k",
            "expansion_mode",
        },
        "required": set(),
    },
    "SearchResponse": {
        "properties": {"mode", "query", "total", "results"},
        "required": {"mode", "query", "total", "results"},
    },
    "SearchResult": {
        "properties": {
            "record_id",
            "title",
            "origin_place",
            "destination_place",
            "date",
            "sender",
            "recipient",
            "kinship",
            "money",
            "snippet",
            "score",
            "evidence",
        },
        "required": {
            "record_id",
            "title",
            "origin_place",
            "destination_place",
            "date",
            "sender",
            "recipient",
            "kinship",
            "money",
            "snippet",
            "score",
            "evidence",
        },
    },
    "RecordDetailResponse": {
        "properties": {
            "record_id",
            "title",
            "metadata",
            "original_text",
            "normalized_text",
            "entities",
            "evidence",
        },
        "required": {
            "record_id",
            "title",
            "metadata",
            "original_text",
            "normalized_text",
            "entities",
            "evidence",
        },
    },
    "EntityResponse": {
        "properties": {"record_id", "entities"},
        "required": {"record_id", "entities"},
    },
    "EvidenceResponse": {
        "properties": {"record_id", "evidence"},
        "required": {"record_id", "evidence"},
    },
    "PlainInterpretationRequest": {
        "properties": {"record_id", "original_text"},
        "required": set(),
    },
    "PlainInterpretationResponse": {
        "properties": {
            "record_id",
            "generated_text",
            "summary",
            "slots",
            "evidence",
            "evidence_mapping",
            "consistency_check",
        },
        "required": {
            "record_id",
            "generated_text",
            "summary",
            "slots",
            "evidence",
            "evidence_mapping",
            "consistency_check",
        },
    },
    "StyleTransferRequest": {
        "properties": {"plain_text", "slots"},
        "required": {"plain_text"},
    },
    "StyleTransferResponse": {
        "properties": {
            "generated_text",
            "summary",
            "slots",
            "evidence",
            "evidence_mapping",
            "consistency_check",
        },
        "required": {
            "generated_text",
            "summary",
            "slots",
            "evidence",
            "evidence_mapping",
            "consistency_check",
        },
    },
}


def test_openapi_routes_match_frozen_contract():
    schema = app.openapi()
    actual_routes = {
        (method.upper(), path)
        for path, operations in schema["paths"].items()
        for method in operations
        if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}
    }

    assert actual_routes == EXPECTED_ROUTES


def test_openapi_model_fields_match_frozen_contract():
    schemas = app.openapi()["components"]["schemas"]

    for model_name, expected in EXPECTED_SCHEMAS.items():
        model = schemas[model_name]
        assert set(model.get("properties", {})) == expected["properties"]
        assert set(model.get("required", [])) == expected["required"]
