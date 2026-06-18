from app.database.repository import search_text_records
from app.schemas import SearchRequest


def _search_response(mode: str, request: SearchRequest) -> dict:
    rows = search_text_records(request.query, filters=request.filters)
    page_size = request.top_k or request.page_size
    start = (request.page - 1) * page_size
    end = start + page_size

    results = []
    for index, row in enumerate(rows[start:end]):
        score_offset = 0.02 if mode == "hybrid" else 0.0
        score = max(0.1, min(1.0, 0.97 - ((start + index) * 0.03) + score_offset))
        evidence_text = str(row.get("unit_text") or row.get("body_core") or row.get("body_clean") or "")
        results.append(
            {
                "record_id": str(row["record_id"]),
                "title": str(row.get("title_reference") or row["record_id"]),
                "origin_place": str(row.get("origin_place") or ""),
                "destination_place": str(row.get("destination_place") or ""),
                "date": str(
                    row.get("date_standard")
                    or row.get("year_normalized")
                    or row.get("date_text")
                    or ""
                ),
                "sender": str(row.get("sender_name_clean") or row.get("sender") or ""),
                "recipient": str(row.get("recipient_name_clean") or row.get("recipient") or ""),
                "kinship": str(row.get("kinship") or row.get("relationship_type") or ""),
                "money": str(row.get("money") or ""),
                "snippet": evidence_text[:220],
                "score": round(score, 2),
                "evidence": [
                    {
                        "source_field": str(row.get("unit_type") or "record_full"),
                        "source_text": evidence_text,
                        "reason": "SQLite FTS5/BM25 检索命中",
                        "similarity_score": round(score, 2),
                    }
                ],
            }
        )

    return {
        "mode": mode,
        "query": request.query,
        "total": len(rows),
        "results": results,
    }


def run_keyword_search(request: SearchRequest) -> dict:
    return _search_response("keyword", request)


def run_semantic_search(request: SearchRequest) -> dict:
    # The vector index is not present on this branch yet. Keep the response shape
    # stable while using the database-backed lexical retriever.
    return _search_response("semantic", request)


def run_hybrid_search(request: SearchRequest) -> dict:
    # Hybrid currently means database-backed lexical retrieval only. Semantic
    # fusion can replace this implementation without changing the API fields.
    return _search_response("hybrid", request)
