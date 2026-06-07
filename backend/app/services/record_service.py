from copy import deepcopy

from app.services.search_service import MOCK_RESULTS


MOCK_RECORD_DETAIL = {
    "record_id": "CSQP-SFHC-TEXT-001",
    "title": "新加坡寄往潮州的家书",
    "metadata": {
        "origin_place": "新加坡",
        "destination_place": "广东潮州",
        "date": "1936",
        "sender": "陈生",
        "recipient": "母亲",
        "kinship": "母亲",
        "money": "八元",
    },
    "original_text": "慈母大人膝下，男在星洲平安，今托水客附上银八元，望收讫后置办米粮并药费。",
    "normalized_text": "儿子在新加坡平安，寄回八元，请母亲用于购买米粮和药品。",
    "entities": [
        {
            "entity_type": "person",
            "value": "陈生",
            "source_text": "男",
            "confidence": 0.82,
        },
        {
            "entity_type": "place",
            "value": "新加坡",
            "source_text": "星洲",
            "confidence": 0.94,
        },
        {
            "entity_type": "place",
            "value": "广东潮州",
            "source_text": "家乡",
            "confidence": 0.76,
        },
        {
            "entity_type": "kinship",
            "value": "母亲",
            "source_text": "慈母大人",
            "confidence": 0.96,
        },
        {
            "entity_type": "money",
            "value": "八元",
            "source_text": "银八元",
            "confidence": 0.91,
        },
    ],
    "evidence": [
        {
            "source_field": "original_text",
            "source_text": "今托水客附上银八元",
            "reason": "支持汇款金额和递送方式",
            "similarity_score": 0.95,
        },
        {
            "source_field": "original_text",
            "source_text": "望收讫后置办米粮并药费",
            "reason": "支持汇款用途",
            "similarity_score": 0.9,
        },
    ],
}


def get_record_detail(record_id: str) -> dict:
    detail = deepcopy(MOCK_RECORD_DETAIL)
    detail["record_id"] = record_id or detail["record_id"]
    return detail


def get_record_entities(record_id: str) -> dict:
    detail = get_record_detail(record_id)
    return {"record_id": detail["record_id"], "entities": detail["entities"]}


def get_similar_records(record_id: str) -> dict:
    results = deepcopy(MOCK_RESULTS[1:])
    return {
        "mode": "similar",
        "query": record_id,
        "total": len(results),
        "results": results,
    }
