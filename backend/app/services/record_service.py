from app.database.repository import (
    get_primary_amount,
    get_record_by_id,
    get_record_entities as fetch_record_entities,
    get_record_evidence as fetch_record_evidence,
    search_text_records,
)


def _entities(record_id: str) -> list[dict]:
    entities = []
    seen: set[tuple[str, str]] = set()
    for row in fetch_record_entities(record_id):
        entity_type = str(row.get("entity_type") or "other")
        value = str(row.get("normalized_text") or row.get("entity_text") or "")
        key = (entity_type, value)
        if not value or key in seen:
            continue
        seen.add(key)
        entities.append(
            {
                "entity_type": entity_type,
                "value": value,
                "source_text": str(row.get("entity_text") or value),
                "confidence": float(row.get("confidence") or 0.0),
            }
        )
    return entities


def _evidence(record_id: str) -> list[dict]:
    return [
        {
            "source_field": str(row.get("source_column") or "body_clean"),
            "source_text": str(row.get("evidence_text") or ""),
            "reason": str(row.get("evidence_type") or "database_evidence"),
            "similarity_score": 1.0,
        }
        for row in fetch_record_evidence(record_id)
        if row.get("evidence_text")
    ]


def get_record_detail(record_id: str) -> dict | None:
    row = get_record_by_id(record_id)
    if row is None:
        return None

    amount = get_primary_amount(record_id) or {}
    metadata_keys = [
        "origin_place",
        "destination_place",
        "date_text",
        "date_standard",
        "year_normalized",
        "sender",
        "recipient",
        "sender_name_clean",
        "recipient_name_clean",
        "relationship_type",
        "main_intent",
        "theme_tags",
        "text_quality_level",
        "place_mentions_normalized",
        "retrieval_keywords",
    ]
    metadata = {
        key: str(row.get(key) or "")
        for key in metadata_keys
        if row.get(key) not in (None, "")
    }
    if amount:
        metadata["money"] = str(amount.get("raw_text") or amount.get("amount_text") or "")

    return {
        "record_id": record_id,
        "title": str(row.get("title_reference") or record_id),
        "metadata": metadata,
        "original_text": str(row.get("body_clean") or row.get("body_core") or ""),
        "normalized_text": str(row.get("rag_summary_text") or row.get("body_core") or ""),
        "entities": _entities(record_id),
        "evidence": _evidence(record_id),
    }


def get_record_entities(record_id: str) -> dict | None:
    if get_record_by_id(record_id) is None:
        return None
    return {"record_id": record_id, "entities": _entities(record_id)}


def get_record_evidence(record_id: str) -> dict | None:
    if get_record_by_id(record_id) is None:
        return None
    return {"record_id": record_id, "evidence": _evidence(record_id)}


def get_similar_records(record_id: str) -> dict:
    detail = get_record_by_id(record_id)
    query = ""
    if detail:
        query = " ".join(
            str(detail.get(key) or "")
            for key in ("origin_place", "relationship_type", "main_intent")
        )
    rows = search_text_records(query, filters={})
    rows = [row for row in rows if row["record_id"] != record_id][:10]
    return {
        "mode": "similar",
        "query": record_id,
        "total": len(rows),
        "results": [
            {
                "record_id": str(row["record_id"]),
                "title": str(row.get("title_reference") or row["record_id"]),
                "origin_place": str(row.get("origin_place") or ""),
                "destination_place": str(row.get("destination_place") or ""),
                "date": str(row.get("date_standard") or row.get("year_normalized") or ""),
                "sender": str(row.get("sender_name_clean") or row.get("sender") or ""),
                "recipient": str(row.get("recipient_name_clean") or row.get("recipient") or ""),
                "kinship": str(row.get("kinship") or row.get("relationship_type") or ""),
                "money": str(row.get("money") or ""),
                "snippet": str(row.get("unit_text") or "")[:220],
                "score": round(max(0.1, 0.9 - index * 0.04), 2),
                "evidence": [
                    {
                        "source_field": str(row.get("unit_type") or "record_full"),
                        "source_text": str(row.get("unit_text") or ""),
                        "reason": "相同来源地或主题的 SQLite 检索结果",
                        "similarity_score": round(max(0.1, 0.9 - index * 0.04), 2),
                    }
                ],
            }
            for index, row in enumerate(rows)
        ],
    }
