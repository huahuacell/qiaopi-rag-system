from copy import deepcopy

from app.schemas import SearchRequest


MOCK_RESULTS = [
    {
        "record_id": "CSQP-SFHC-TEXT-001",
        "title": "新加坡寄往潮州的家书",
        "origin_place": "新加坡",
        "destination_place": "广东潮州",
        "date": "1936",
        "sender": "陈生",
        "recipient": "母亲",
        "kinship": "母亲",
        "money": "八元",
        "snippet": "寄信人托水客带回八元，请母亲用于购买米粮和药品。",
        "score": 0.93,
        "evidence": [
            {
                "source_field": "original_text",
                "source_text": "附上银八元以备家用",
                "reason": "命中汇款金额关键词",
                "similarity_score": 0.93,
            },
            {
                "source_field": "destination_place",
                "source_text": "广东潮州",
                "reason": "目的地筛选匹配",
                "similarity_score": 0.88,
            },
        ],
    },
    {
        "record_id": "CSQP-SFHC-TEXT-002",
        "title": "寄给祖母的汇款短札",
        "origin_place": "新加坡",
        "destination_place": "广东潮州",
        "date": "1938",
        "sender": "林文",
        "recipient": "祖母",
        "kinship": "祖母",
        "money": "十元",
        "snippet": "寄信人在新加坡报平安，并请祖母查收十元汇款。",
        "score": 0.87,
        "evidence": [
            {
                "source_field": "normalized_text",
                "source_text": "请祖母收十元",
                "reason": "亲属关系和汇款金额证据",
                "similarity_score": 0.87,
            }
        ],
    },
    {
        "record_id": "CSQP-SFHC-TEXT-003",
        "title": "寄给父母的家用书信",
        "origin_place": "泰国",
        "destination_place": "广东汕头",
        "date": "1941",
        "sender": "郑侨",
        "recipient": "父母",
        "kinship": "父母",
        "money": "十五元",
        "snippet": "寄给父母的书信，说明寄回十五元以供家用和学费。",
        "score": 0.79,
        "evidence": [
            {
                "source_field": "original_text",
                "source_text": "十五元作家用",
                "reason": "语义匹配家庭支持主题",
                "similarity_score": 0.79,
            }
        ],
    },
]


def _apply_filters(results: list, filters: dict) -> list:
    filtered = results
    for key, value in filters.items():
        if value:
            filtered = [
                item
                for item in filtered
                if str(item.get(key, "")).lower() == str(value).lower()
            ]
    return filtered


def _search_response(mode: str, request: SearchRequest, score_offset: float = 0.0) -> dict:
    results = deepcopy(MOCK_RESULTS)
    query = request.query.strip().lower()
    if query:
        for item in results:
            haystack = " ".join(
                [
                    item["title"],
                    item["origin_place"],
                    item["destination_place"],
                    item["kinship"],
                    item["money"],
                    item["snippet"],
                ]
            ).lower()
            if query in haystack:
                item["score"] = min(1.0, item["score"] + 0.04 + score_offset)
            else:
                item["score"] = max(0.1, item["score"] - 0.08 + score_offset)
            item["score"] = round(item["score"], 2)

    results = _apply_filters(results, request.filters)
    results = sorted(results, key=lambda item: item["score"], reverse=True)
    start = (request.page - 1) * request.page_size
    end = start + request.page_size
    page_results = results[start:end]
    return {
        "mode": mode,
        "query": request.query,
        "total": len(results),
        "results": page_results,
    }


def run_keyword_search(request: SearchRequest) -> dict:
    return _search_response("keyword", request)


def run_semantic_search(request: SearchRequest) -> dict:
    return _search_response("semantic", request, score_offset=0.02)


def run_hybrid_search(request: SearchRequest) -> dict:
    return _search_response("hybrid", request, score_offset=0.03)
