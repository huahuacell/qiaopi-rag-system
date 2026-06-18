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
            "expansion_mode": "balanced",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["query"] == "母亲 寄款 查收"
    assert payload["normalized_query"] == "母亲 寄款 查收"
    assert "慈亲" in payload["expanded_query"] or "膝下" in payload["expanded_query"]
    assert payload["expansion_mode"] == "balanced"
    assert payload["original_terms"] == ["母亲", "寄款", "查收"]
    assert payload["strong_expansion_terms"]
    assert payload["medium_expansion_terms"]
    assert "weak_expansion_terms" in payload
    assert payload["semantic_enabled"] is False
    assert payload["top_k"] == 5
    assert payload["results"]
    assert payload["grouped_by_record"]

    result = payload["results"][0]
    assert result["record_id"].startswith("CSQP-SFHC-TEXT-")
    assert result["unit_id"]
    assert result["unit_type"]
    assert result["unit_text"]
    assert result["snippet"]
    assert "bm25_score" in result
    assert "final_score" in result
    assert "original_hit_count" in result
    assert "strong_hit_count" in result
    assert "medium_hit_count" in result
    assert "weak_hit_count" in result
    assert result["matched_reason"]
    assert result["matched_text"]
    assert "source_column" in result


def test_keyword_search_can_filter_unit_types():
    response = client.post(
        "/api/search/keyword",
        json={
            "query": "母亲 寄款 查收",
            "top_k": 5,
            "unit_types": ["remittance"],
            "filters": {},
            "expansion_mode": "balanced",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["results"]
    assert all(result["unit_type"] == "remittance" for result in payload["results"])


def test_keyword_search_reranks_short_closing_units_lower():
    response = client.post(
        "/api/search/keyword",
        json={
            "query": "母亲 寄款 查收",
            "top_k": 10,
            "unit_types": ["remittance", "opening", "body_core", "closing"],
            "filters": {},
            "expansion_mode": "balanced",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["results"]
    assert all(
        not (
            result["unit_type"] == "closing"
            and len("".join(result["unit_text"].split())) < 5
        )
        for result in payload["results"][:5]
    )


def test_grouped_by_record_is_not_larger_than_unit_results():
    response = client.post(
        "/api/search/keyword",
        json={
            "query": "母亲 寄款 查收",
            "top_k": 10,
            "unit_types": [],
            "filters": {},
            "expansion_mode": "balanced",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert len(payload["grouped_by_record"]) <= len(payload["results"])
    assert payload["grouped_by_record"][0]["matched_units"]


def test_study_search_prioritizes_actual_study_hits_over_generic_instruction():
    response = client.post(
        "/api/search/keyword",
        json={
            "query": "读书 勤俭",
            "top_k": 10,
            "unit_types": ["instruction", "body_core", "record_full", "remittance"],
            "filters": {},
            "expansion_mode": "balanced",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["grouped_by_record"]
    study_terms = ("勤学", "学业", "读书", "课程", "书馆", "温习")
    top_three = payload["results"][:3]
    assert any(
        any(term in result["unit_text"] or term in result["matched_text"] for term in study_terms)
        for result in top_three
    )
    assert all(
        result["original_hit_count"] + result["strong_hit_count"] + result["medium_hit_count"] > 0
        for result in payload["results"][:5]
    )
    assert all("命中“" in result["matched_reason"] for result in payload["results"][:5])


def test_advanced_search_supports_main_intent_filter():
    response = client.post(
        "/api/search/advanced",
        json={
            "query": "读书 勤俭",
            "top_k": 10,
            "unit_types": ["instruction", "body_core"],
            "filters": {"main_intent": "instruction"},
            "expansion_mode": "balanced",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["semantic_enabled"] is False
    assert payload["results"]
    assert all(result["main_intent"] == "instruction" for result in payload["results"])
    assert all(result["matched_reason"] for result in payload["results"])


def test_hybrid_search_reports_semantic_disabled():
    response = client.post(
        "/api/search/hybrid",
        json={
            "query": "新加坡 平安",
            "top_k": 10,
            "unit_types": ["safety", "body_core", "record_full"],
            "filters": {},
            "expansion_mode": "balanced",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["semantic_enabled"] is False
    assert payload["results"]


def test_strict_expansion_mode_omits_medium_and_weak_terms_from_expanded_query():
    response = client.post(
        "/api/search/keyword",
        json={
            "query": "读书 勤俭",
            "top_k": 5,
            "unit_types": ["instruction", "body_core"],
            "filters": {},
            "expansion_mode": "strict",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["expansion_mode"] == "strict"
    assert "课程" not in payload["expanded_query"]
    assert "务望" not in payload["expanded_query"]
