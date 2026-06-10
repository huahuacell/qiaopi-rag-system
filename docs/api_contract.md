# API Contract

Base URL: `http://localhost:8000`

All responses are deterministic mock JSON in the scaffold phase. Field names are stable and should not be renamed without explicit contract updates.

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
- `qiaopi_generation_cache`
- `qiaopi_query_logs`

`qiaopi_retrieval_units` stores record-level, body, evidence, style, and RAG summary retrieval units with stable `unit_id`, traceable source columns, evidence type, weight, and normalized `fts_text`.

SQLite FTS5/BM25 search is built over retrieval units by `python -m app.ingestion.build_database`. It returns retrieval-unit-level matches and does not replace future semantic search.

Current limitation: this step does not implement Qwen generation, FAISS semantic search, or new business API routes.

## GET /api/health

Response:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "message": "Qiaopi RAG mock backend is running"
}
```

Fields:

- `status`: backend state.
- `version`: scaffold version.
- `message`: human-readable status.

## GET /api/dashboard/stats

Response:

```json
{
  "total_records": 50064,
  "text_records": 213,
  "origin_places": [{"label": "Singapore", "value": 12680}],
  "destination_places": [{"label": "Guangdong Chaozhou", "value": 18420}],
  "kinship_distribution": [{"label": "mother", "value": 46}],
  "money_distribution": [{"label": "eight yuan", "value": 22}],
  "timeline": [{"label": "1930s", "value": 78}]
}
```

Fields:

- `total_records`: metadata row count placeholder.
- `text_records`: text row count placeholder.
- Distribution arrays use `label` and `value`.

## POST /api/search/keyword

Request:

```json
{
  "query": "eight yuan",
  "filters": {
    "origin_place": "Singapore",
    "destination_place": "Guangdong Chaozhou"
  },
  "page": 1,
  "page_size": 10
}
```

Response:

```json
{
  "mode": "keyword",
  "query": "eight yuan",
  "total": 2,
  "results": [
    {
      "record_id": "CSQP-SFHC-TEXT-001",
      "title": "Letter from Singapore to Chaozhou",
      "origin_place": "Singapore",
      "destination_place": "Guangdong Chaozhou",
      "date": "1936",
      "sender": "Chen Sheng",
      "recipient": "mother",
      "kinship": "mother",
      "money": "eight yuan",
      "snippet": "Sent eight yuan home and asked mother to use it for rice and medicine.",
      "score": 0.93,
      "evidence": [
        {
          "source_field": "original_text",
          "source_text": "attached eight yuan for household use",
          "reason": "Keyword match on remittance amount",
          "similarity_score": 0.93
        }
      ]
    }
  ]
}
```

## POST /api/search/semantic

Same request and response shape as keyword search. `mode` is `semantic`; `score` means semantic similarity.

## POST /api/search/hybrid

Same request and response shape as keyword search. `mode` is `hybrid`; `score` combines keyword and semantic placeholder signals.

## GET /api/records/{record_id}

Response:

```json
{
  "record_id": "CSQP-SFHC-TEXT-001",
  "title": "Letter from Singapore to Chaozhou",
  "metadata": {
    "origin_place": "Singapore",
    "destination_place": "Guangdong Chaozhou",
    "date": "1936",
    "sender": "Chen Sheng",
    "recipient": "mother",
    "kinship": "mother",
    "money": "eight yuan"
  },
  "original_text": "Qiaopi-style source text placeholder",
  "normalized_text": "Normalized plain text placeholder",
  "entities": [],
  "evidence": []
}
```

Fields:

- `metadata`: stable record-level fields used by search, filtering, and display.
- `original_text`: source Qiaopi text or placeholder.
- `normalized_text`: readable normalized text or placeholder.
- `entities`: extracted entity objects.
- `evidence`: evidence objects tied to the record.

## GET /api/records/{record_id}/entities

Response:

```json
{
  "record_id": "CSQP-SFHC-TEXT-001",
  "entities": [
    {
      "entity_type": "money",
      "value": "eight yuan",
      "source_text": "attached eight yuan",
      "confidence": 0.91
    }
  ]
}
```

## GET /api/records/{record_id}/similar

Response shape matches search responses:

```json
{
  "mode": "similar",
  "query": "CSQP-SFHC-TEXT-001",
  "total": 1,
  "results": []
}
```

## POST /api/generation/plain-interpretation

Request:

```json
{
  "record_id": "CSQP-SFHC-TEXT-001",
  "original_text": ""
}
```

Response:

```json
{
  "record_id": "CSQP-SFHC-TEXT-001",
  "generated_text": "Plain Chinese interpretation placeholder",
  "summary": ["Sender reports safety", "Sender remits eight yuan"],
  "slots": {
    "sender": "Chen Sheng",
    "recipient": "mother",
    "money": "eight yuan"
  },
  "evidence": [],
  "evidence_mapping": [],
  "consistency_check": {
    "status": "passed",
    "warnings": [],
    "passed_rules": ["money_supported_by_evidence"],
    "failed_rules": []
  }
}
```

## POST /api/generation/style-transfer

Request:

```json
{
  "plain_text": "Mother, I am safe in Singapore and send eight yuan home.",
  "slots": {
    "recipient": "mother",
    "money": "eight yuan"
  }
}
```

Response shape:

```json
{
  "generated_text": "Qiaopi-style generated text placeholder",
  "summary": ["Converted plain letter into respectful Qiaopi style"],
  "slots": {},
  "evidence": [],
  "evidence_mapping": [],
  "consistency_check": {
    "status": "passed",
    "warnings": [],
    "passed_rules": [],
    "failed_rules": []
  }
}
```
