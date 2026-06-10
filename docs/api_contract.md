# API Contract

Base URL: `http://localhost:8000`

Field names are stable and should not be renamed without explicit contract updates.

## Step A Data Foundation

Processed source data:

- `backend/data/processed/qiaopi_213_wide_table.csv`
- `backend/data/processed/qiaopi_213_wide_table.xlsx` as fallback if the CSV is missing
- `backend/data/processed/qiaopi_amount_mentions.csv`
- `backend/data/processed/qiaopi_entity_mentions.csv`
- `backend/data/processed/qiaopi_place_mentions.csv`
- `backend/data/processed/qiaopi_evidence_spans.csv`

Local SQLite database path:

- `backend/data/processed/qiaopi.db`

Core tables:

- `qiaopi_text_records`
- `qiaopi_amount_mentions`
- `qiaopi_entity_mentions`
- `qiaopi_place_mentions`
- `qiaopi_evidence_spans`
- `qiaopi_retrieval_units`
- `qiaopi_retrieval_units_fts`
- `qiaopi_generation_cache`
- `qiaopi_query_logs`

`qiaopi_retrieval_units` stores record-level, body, evidence, style, and RAG summary retrieval units with stable `unit_id`, traceable source columns, evidence type, weight, and normalized `fts_text`.

SQLite FTS5/BM25 search is built over retrieval units by `python -m app.ingestion.build_database`. It returns retrieval-unit-level matches and does not replace future semantic search.

Current limitation: Step B1 does not implement Qwen generation, FAISS semantic search, RAG generation, reranking, aggregation, or complex hybrid search.

## GET /api/health

Response:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "message": "Qiaopi RAG backend is running"
}
```

## GET /api/dashboard/stats

Response:

```json
{
  "total_text_records": 213,
  "full_text_count": 202,
  "metadata_only_count": 11,
  "retrieval_unit_count": 1959,
  "fts_row_count": 1959,
  "amount_mention_count": 482,
  "entity_mention_count": 4312,
  "place_mention_count": 1134,
  "evidence_count": 1097,
  "remittance_record_count": 206
}
```

## GET /api/dashboard/distributions

Response:

```json
{
  "text_quality_distribution": [{"label": "medium", "value": 92}],
  "main_intent_distribution": [{"label": "instruction", "value": 83}],
  "relationship_distribution": [{"label": "son_to_parent", "value": 80}],
  "unit_type_distribution": [{"label": "record_full", "value": 213}],
  "top_places": [{"label": "新加坡", "value": 230}],
  "top_countries_or_regions": [{"label": "广东侨乡", "value": 420}],
  "year_distribution": [{"label": "1931", "value": 8}]
}
```

Each distribution item uses:

- `label`: bucket name.
- `value`: row count.

## POST /api/search/keyword

Request:

```json
{
  "query": "母亲 寄款 查收",
  "top_k": 10,
  "unit_types": [],
  "filters": {}
}
```

Response:

```json
{
  "query": "母亲 寄款 查收",
  "top_k": 10,
  "results": [
    {
      "record_id": "CSQP-SFHC-TEXT-017",
      "unit_id": "CSQP-SFHC-TEXT-017-RU-REMITTANCE-001",
      "unit_type": "remittance",
      "title_reference": "题名文本",
      "sender": "寄批人",
      "recipient": "收批人",
      "date_text": "癸九月十一日",
      "main_intent": "remittance",
      "unit_text": "兹寄批局，带去洋银肆元，至照查收，以安家计。",
      "snippet": "兹寄批局，带去洋银肆元，至照查收，以安家计。",
      "bm25_score": 0.000007,
      "evidence_type": "remittance",
      "source_column": "evidence_remittance"
    }
  ]
}
```

Search uses SQLite FTS5/BM25 over `qiaopi_retrieval_units_fts`. Results are retrieval-unit-level. Step B2 may add reranking, record aggregation, and richer filters.

## GET /api/records/{record_id}

Response:

```json
{
  "record_id": "CSQP-SFHC-TEXT-017",
  "title_reference": "题名文本",
  "sender": "寄批人",
  "recipient": "收批人",
  "sender_name_clean": "寄批人名",
  "recipient_name_clean": "收批人名",
  "date_text": "癸九月十一日",
  "year_normalized": "",
  "body_clean": "清洗后正文",
  "body_core": "正文核心内容",
  "main_intent": "remittance",
  "theme_tags": "theme_remittance；theme_family_affection",
  "text_quality_level": "high",
  "has_full_text": 1,
  "has_remittance": 1,
  "relationship_type": "son_to_parent",
  "place_mentions_normalized": "新加坡；广东侨乡",
  "retrieval_keywords": "母亲；寄款；查收",
  "rag_summary_text": "RAG 摘要文本",
  "style_reference_text": "风格样本文本",
  "raw_fields": {
    "record_id": "CSQP-SFHC-TEXT-017"
  }
}
```

If the record does not exist, returns HTTP 404.

## GET /api/records/{record_id}/amounts

Response:

```json
{
  "record_id": "CSQP-SFHC-TEXT-017",
  "amounts": [
    {
      "mention_id": "CSQP-SFHC-TEXT-017-AMT-001",
      "record_id": "CSQP-SFHC-TEXT-017",
      "raw_text": "洋银肆元",
      "amount_text": "肆元",
      "amount_number": 4,
      "currency": "洋银",
      "sentence": "兹寄批局，带去洋银肆元，至照查收，以安家计。",
      "is_primary_candidate": 1,
      "source_field": "body_clean"
    }
  ]
}
```

## GET /api/records/{record_id}/entities

Response:

```json
{
  "record_id": "CSQP-SFHC-TEXT-017",
  "entities": [
    {
      "mention_id": "CSQP-SFHC-TEXT-017-ENT-0001",
      "record_id": "CSQP-SFHC-TEXT-017",
      "entity_type": "kinship",
      "value": "母亲",
      "source_text": "慈亲",
      "normalized_text": "母亲",
      "source_field": "body_clean",
      "confidence": 0.9
    }
  ]
}
```

## GET /api/records/{record_id}/places

Response:

```json
{
  "record_id": "CSQP-SFHC-TEXT-017",
  "places": [
    {
      "mention_id": "CSQP-SFHC-TEXT-017-PLC-001",
      "record_id": "CSQP-SFHC-TEXT-017",
      "alias_text": "星洲",
      "normalized_place": "新加坡",
      "country_or_region": "新加坡",
      "source_field": "body_clean"
    }
  ]
}
```

## GET /api/records/{record_id}/evidence

Response:

```json
{
  "record_id": "CSQP-SFHC-TEXT-017",
  "evidence": [
    {
      "evidence_id": "CSQP-SFHC-TEXT-017-EVID-0001",
      "record_id": "CSQP-SFHC-TEXT-017",
      "evidence_type": "remittance",
      "evidence_text": "兹寄批局，带去洋银肆元，至照查收，以安家计。",
      "source_column": "body_clean",
      "start_char": 12,
      "end_char": 35
    }
  ]
}
```

## GET /api/records/{record_id}/retrieval-units

Response:

```json
{
  "record_id": "CSQP-SFHC-TEXT-017",
  "retrieval_units": [
    {
      "unit_id": "CSQP-SFHC-TEXT-017-RU-REMITTANCE-001",
      "record_id": "CSQP-SFHC-TEXT-017",
      "unit_type": "remittance",
      "source_column": "evidence_remittance",
      "unit_text": "兹寄批局，带去洋银肆元，至照查收，以安家计。",
      "title_reference": "题名文本",
      "sender": "寄批人",
      "recipient": "收批人",
      "date_text": "癸九月十一日",
      "main_intent": "remittance",
      "theme_tags": "theme_remittance",
      "style_keywords": "慈亲；膝下；查收",
      "relationship_type": "son_to_parent",
      "place_mentions_normalized": "新加坡",
      "retrieval_keywords": "母亲；寄款；查收",
      "weight": 1.5,
      "evidence_type": "remittance",
      "fts_text": "母亲 寄款 查收 新加坡"
    }
  ]
}
```
