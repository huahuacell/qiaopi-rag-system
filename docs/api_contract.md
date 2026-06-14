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
- `qiaopi_metadata_records`
- `qiaopi_metadata_fts`
- `qiaopi_text_metadata_links`
- `qiaopi_text_metadata_link_candidates`
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

Step B2 adds precision-aware qiaopi-domain query expansion, staged retrieval, Python reranking, matched reasons, and record-level aggregation for search display.

Step C adds RAG evidence context and qiaopi style context construction. These APIs prepare traceable context blocks for later generation but do not call Qwen.

Step D1 adds a Qwen generation foundation for prompt preview, evidence-grounded modern interpretation, and qiaopi-style drafting. Qwen calls are disabled unless environment variables explicitly enable them.

Step F adds optional semantic retrieval over `qiaopi_retrieval_units`. Build the local semantic index with `python -m app.ingestion.build_semantic_index` after rebuilding the SQLite database. Runtime semantic retrieval remains disabled until `SEMANTIC_SEARCH_ENABLED=true` and index files exist. Generated content is not historical source material and must be displayed with evidence references.

Step G adds a large-scale 50064-record metadata catalog layer for archive browsing, metadata search, statistics, timeline views, place distribution, and links to the 213 full-text records. Metadata-only records are catalog records, not full-text evidence. They must not be inserted into `qiaopi_retrieval_units`, `qiaopi_retrieval_units_fts`, the semantic index, RAG context, or Qwen generation prompts. Only linked 213 full-text records may be used for RAG or generation tasks.

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
  "metadata_record_count": 50064,
  "metadata_linked_text_count": 1,
  "metadata_link_candidate_count": 4,
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

Search pipeline:

- Normalize unsafe punctuation and whitespace before sending text into FTS5.
- Expand modern Chinese terms to weighted qiaopi-domain groups: original terms, strong expansion terms, medium expansion terms, and weak expansion terms.
- Retrieve first-stage candidates from `qiaopi_retrieval_units_fts` with SQLite FTS5/BM25.
- Use `expansion_mode` to control precision: `strict` uses original + strong terms, `balanced` stages original/strong first and adds medium or weak terms only if needed, and `broad` uses all terms while still applying coverage penalties.
- Rerank candidates in Python using BM25, unit-type boosts, query coverage, weak-only penalties, and penalties for very short `closing` or signature-like units.
- Return unit-level results and `grouped_by_record` for record-level display.

Request:

```json
{
  "query": "母亲 寄款 查收",
  "top_k": 10,
  "unit_types": [],
  "filters": {},
  "expansion_mode": "balanced"
}
```

Response:

```json
{
  "query": "母亲 寄款 查收",
  "normalized_query": "母亲 寄款 查收",
  "expanded_query": "母亲 寄款 查收 慈亲 萱堂 家母 大人 膝下 批款 寄上 汇上 付去 兹托 带去 奉上 收讫 照收 如数查收 收用 检收 祈收 严慈 批局 查明",
  "expansion_mode": "balanced",
  "original_terms": ["母亲", "寄款", "查收"],
  "strong_expansion_terms": ["慈亲", "萱堂", "家母", "批款", "寄上", "汇上", "收讫", "照收", "如数查收"],
  "medium_expansion_terms": ["大人", "膝下", "阿母", "阿妈", "付去", "兹托", "带去", "奉上", "收用", "检收", "祈收"],
  "weak_expansion_terms": ["严慈", "批局", "查明"],
  "expansion_terms": ["慈亲", "萱堂", "家母", "批款", "寄上", "汇上"],
  "top_k": 10,
  "semantic_enabled": false,
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
      "matched_text": "兹寄批局，带去洋银肆元，至照查收，以安家计。",
      "matched_reason": "命中寄款片段；原始查询命中“查收”；中扩展命中“带去”；弱扩展命中“批局”",
      "bm25_score": -0.000007,
      "semantic_score": 0,
      "final_score": 1.8399826,
      "retrieval_sources": [],
      "original_hit_count": 1,
      "strong_hit_count": 0,
      "medium_hit_count": 1,
      "weak_hit_count": 1,
      "evidence_type": "remittance",
      "source_column": "evidence_remittance"
    }
  ],
  "grouped_by_record": [
    {
      "record_id": "CSQP-SFHC-TEXT-017",
      "title_reference": "题名文本",
      "sender": "寄批人",
      "recipient": "收批人",
      "date_text": "癸九月十一日",
      "main_intent": "remittance",
      "best_score": 1.8399826,
      "matched_units": [
        {
          "unit_id": "CSQP-SFHC-TEXT-017-RU-REMITTANCE-001",
          "unit_type": "remittance",
          "unit_text": "兹寄批局，带去洋银肆元，至照查收，以安家计。",
          "source_column": "evidence_remittance",
          "evidence_type": "remittance",
          "bm25_score": -0.000007,
          "final_score": 1.8399826,
          "matched_reason": "命中寄款片段；原始查询命中“查收”；中扩展命中“带去”；弱扩展命中“批局”",
          "original_hit_count": 1,
          "semantic_score": 0,
          "retrieval_sources": [],
          "strong_hit_count": 0,
          "medium_hit_count": 1,
          "weak_hit_count": 1
        }
      ]
    }
  ]
}
```

`results` are reranked retrieval-unit matches. `grouped_by_record` contains one item per record and up to three top matched units per record. `matched_reason` must cite actual hit terms; if a unit only matches a broad type without core terms, it is marked as such and penalized.

## POST /api/search/advanced

Request shape matches keyword search. Supported filters:

- `main_intent`
- `theme`
- `relationship_type`
- `place`
- `country_or_region`
- `has_remittance`
- `text_quality_level`
- `year_normalized`
- `unit_type`

Example request:

```json
{
  "query": "读书 勤俭",
  "top_k": 10,
  "unit_types": ["instruction", "body_core"],
  "filters": {
    "main_intent": "instruction"
  },
  "expansion_mode": "balanced"
}
```

Response shape is the same as `/api/search/keyword`, with `semantic_enabled` set to `false`.

## GET /api/search/semantic/status

Purpose: safely diagnose whether semantic retrieval is available in the running backend process.

Response:

```json
{
  "semantic_enabled": true,
  "configured_enabled": true,
  "index_exists": true,
  "metadata_exists": true,
  "embedding_provider": "local",
  "embedding_model": "BAAI/bge-small-zh-v1.5",
  "index_path": "backend/data/index/qiaopi_retrieval_units.faiss",
  "metadata_path": "backend/data/index/qiaopi_retrieval_units_meta.jsonl",
  "vector_count": 1959,
  "error_message": null
}
```

If semantic search is disabled or the index is missing, the endpoint returns HTTP 200 with `semantic_enabled=false` and an `error_message`. It never returns embedding or generation API keys.

## POST /api/search/semantic

Purpose: retrieve `qiaopi_retrieval_units` by embedding similarity. This endpoint does not do query expansion or BM25 reranking.

Request:

```json
{
  "query": "母亲寄款查收",
  "top_k": 10,
  "unit_types": ["remittance", "body_core"],
  "filters": {}
}
```

Response:

```json
{
  "query": "母亲寄款查收",
  "top_k": 10,
  "semantic_enabled": true,
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
      "matched_text": "兹寄批局，带去洋银肆元，至照查收，以安家计。",
      "matched_reason": "语义向量相似度命中",
      "bm25_score": 0,
      "semantic_score": 0.8123,
      "final_score": 0.8123,
      "retrieval_sources": ["semantic"],
      "original_hit_count": 0,
      "strong_hit_count": 0,
      "medium_hit_count": 0,
      "weak_hit_count": 0,
      "evidence_type": "remittance",
      "source_column": "evidence_remittance"
    }
  ],
  "error_message": null,
  "index_backend": "faiss"
}
```

If `SEMANTIC_SEARCH_ENABLED=false` or index files are missing, the endpoint returns HTTP 200 with `semantic_enabled=false`, empty `results`, and a controlled `error_message`.

## POST /api/search/hybrid

Hybrid search combines advanced keyword retrieval with semantic retrieval using reciprocal rank fusion (`fusion_method: "rrf"`). If semantic search is disabled, misconfigured, or missing index files, it returns the keyword results with `fusion_method: "keyword_fallback"` and does not fake semantic scores.

Example request:

```json
{
  "query": "新加坡 平安",
  "top_k": 10,
  "unit_types": ["safety", "body_core", "record_full"],
  "filters": {},
  "expansion_mode": "balanced"
}
```

Response shape is the same as `/api/search/keyword`, with:

```json
{
  "semantic_enabled": true,
  "fusion_method": "rrf",
  "error_message": null
}
```

Each result includes:

- `bm25_score`: score from keyword/FTS retrieval when present.
- `semantic_score`: embedding similarity when present.
- `final_score`: fused RRF score for hybrid responses.
- `retrieval_sources`: `["keyword"]`, `["semantic"]`, or `["keyword", "semantic"]`.

## POST /api/rag/context

Purpose: prepare traceable evidence context for future qiaopi interpretation, question answering, or plain Chinese explanation. This endpoint can use keyword, semantic, or hybrid retrieval via `retrieval_mode`. It does not call Qwen.

Request:

```json
{
  "query": "母亲寄款查收的侨批内容",
  "top_k": 8,
  "unit_types": ["body_core", "remittance", "family_care", "instruction", "rag_summary"],
  "filters": {},
  "expansion_mode": "balanced",
  "retrieval_mode": "hybrid"
}
```

Response:

```json
{
  "query": "母亲寄款查收的侨批内容",
  "normalized_query": "母亲寄款查收的侨批内容 母亲 寄款 查收",
  "expanded_query": "母亲寄款查收的侨批内容 母亲 寄款 查收 慈亲 萱堂 家母 批款 寄上 汇上 收讫 照收 如数查收 大人 膝下 阿母 阿妈 付去 兹托 带去 奉上 收用 检收 祈收 严慈 批局 查明",
  "expansion_mode": "balanced",
  "semantic_enabled": false,
  "contexts": [
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
      "source_column": "evidence_remittance",
      "evidence_type": "remittance",
      "matched_reason": "命中寄款片段；原始查询命中“查收”",
      "final_score": 1.8399826
    }
  ],
  "grouped_contexts": [
    {
      "record_id": "CSQP-SFHC-TEXT-017",
      "title_reference": "题名文本",
      "sender": "寄批人",
      "recipient": "收批人",
      "date_text": "癸九月十一日",
      "main_intent": "remittance",
      "best_score": 1.8399826,
      "matched_units": [
        {
          "unit_id": "CSQP-SFHC-TEXT-017-RU-REMITTANCE-001",
          "unit_type": "remittance",
          "unit_text": "兹寄批局，带去洋银肆元，至照查收，以安家计。",
          "source_column": "evidence_remittance",
          "evidence_type": "remittance",
          "bm25_score": -0.000007,
          "final_score": 1.8399826,
          "matched_reason": "命中寄款片段；原始查询命中“查收”",
          "original_hit_count": 1,
          "strong_hit_count": 0,
          "medium_hit_count": 1,
          "weak_hit_count": 1
        }
      ]
    }
  ],
  "prompt_context": "【检索问题】\n母亲寄款查收的侨批内容\n\n【相关侨批证据 1】\n来源记录：CSQP-SFHC-TEXT-017\n题名：题名文本\n寄批人：寄批人\n收批人：收批人\n日期：癸九月十一日\n证据类型：remittance\n来源字段：evidence_remittance\n原文片段：兹寄批局，带去洋银肆元，至照查收，以安家计。",
  "evidence_count": 1,
  "source_record_count": 1
}
```

`contexts` are deduplicated by `unit_text` and selected to avoid overloading the prompt with too many units from the same record when enough records are available. Traceability fields are preserved: `record_id`, `unit_id`, `source_column`, and `evidence_type`.

`prompt_context` format:

```text
【检索问题】
母亲寄款查收的侨批内容

【相关侨批证据 1】
来源记录：CSQP-SFHC-TEXT-017
题名：...
寄批人：...
收批人：...
日期：...
证据类型：remittance
来源字段：evidence_remittance
原文片段：...
```

Current limitations:

- This RAG context endpoint does not call Qwen; it only prepares evidence for generation endpoints.
- Semantic retrieval is optional and falls back to keyword retrieval when disabled or missing an index.
- `semantic_enabled` reports whether semantic retrieval participated in this response.

## POST /api/rag/style-context

Purpose: prepare qiaopi style examples for future plain Chinese to qiaopi-style generation. This endpoint returns grouped slot examples only; it does not generate a final qiaopi-style letter.

Request:

```json
{
  "query": "母亲您好，我在新加坡平安，寄八元回家，请弟弟好好读书。",
  "top_k": 3,
  "filters": {},
  "expansion_mode": "balanced"
}
```

Response:

```json
{
  "query": "母亲您好，我在新加坡平安，寄八元回家，请弟弟好好读书。",
  "normalized_query": "母亲您好 我在新加坡平安 寄八元回家 请弟弟好好读书 母亲 平安 寄款 读书 新加坡 慈亲 大人 膝下 安好 无恙 勿念 汇款 批款 查收 勤学 学业 务望",
  "expanded_query": "母亲您好 我在新加坡平安 寄八元回家 请弟弟好好读书 母亲 平安 寄款 读书 新加坡 慈亲 大人 膝下 安好 无恙 勿念 汇款 批款 查收 勤学 学业 务望 萱堂 家母 批款 寄上 汇上 勤读 学业 星洲 叻坡 石叻 阿母 阿妈 付去 兹托 带去 奉上 书馆 课程 成绩 温习 南洋 严慈 安康 批局 教训",
  "expansion_mode": "balanced",
  "semantic_enabled": false,
  "style_slots": {
    "opening": [
      {
        "record_id": "CSQP-SFHC-TEXT-017",
        "unit_id": "CSQP-SFHC-TEXT-017-RU-OPENING-001",
        "unit_type": "opening",
        "title_reference": "题名文本",
        "unit_text": "慈亲大人膝下：",
        "source_column": "evidence_opening",
        "evidence_type": "opening",
        "matched_reason": "命中开头称谓；原始查询命中“慈亲/膝下”",
        "final_score": 2.14
      }
    ],
    "safety": [],
    "remittance": [],
    "family_care": [],
    "instruction": [],
    "closing": [],
    "style_reference": []
  },
  "grouped_contexts": [
    {
      "record_id": "CSQP-SFHC-TEXT-017",
      "title_reference": "题名文本",
      "sender": "寄批人",
      "recipient": "收批人",
      "date_text": "癸九月十一日",
      "main_intent": "remittance",
      "best_score": 2.14,
      "matched_units": [
        {
          "unit_id": "CSQP-SFHC-TEXT-017-RU-OPENING-001",
          "unit_type": "opening",
          "unit_text": "慈亲大人膝下：",
          "source_column": "evidence_opening",
          "evidence_type": "opening",
          "bm25_score": -0.000007,
          "final_score": 2.14,
          "matched_reason": "命中开头称谓；原始查询命中“慈亲/膝下”",
          "original_hit_count": 2,
          "strong_hit_count": 0,
          "medium_hit_count": 0,
          "weak_hit_count": 0
        }
      ]
    }
  ],
  "prompt_context": "【用户白话输入】\n母亲您好，我在新加坡平安，寄八元回家，请弟弟好好读书。\n\n【开头称谓样例】\n1. 慈亲大人膝下：\n来源：CSQP-SFHC-TEXT-017\n\n【报平安样例】\n暂无可用样例。",
  "source_record_count": 1
}
```

`style_slots` always contains these keys:

- `opening`
- `safety`
- `remittance`
- `family_care`
- `instruction`
- `closing`
- `style_reference`

Each slot returns up to `top_k` examples. A slot with no matching result returns an empty list.

Rule-based style hints are deterministic:

- If the query contains `母亲`, `妈妈`, or `阿嬷`, opening retrieval is helped by terms such as `慈亲`, `母亲`, `大人`, and `膝下`.
- If the query contains `平安` or `安好`, safety retrieval is prioritized.
- If the query contains `寄`, `钱`, `元`, or `汇款`, remittance retrieval is prioritized.
- If the query contains `读书`, `学习`, or `勤奋`, instruction retrieval is prioritized.
- If the query contains `保重` or `身体`, family-care retrieval is prioritized.

`prompt_context` format:

```text
【用户白话输入】
母亲您好，我在新加坡平安，寄八元回家，请弟弟好好读书。

【开头称谓样例】
1. 慈亲大人膝下：
来源：CSQP-SFHC-TEXT-017

【报平安样例】
...

【寄款表达样例】
...

【问候保重样例】
...

【嘱托表达样例】
...

【结尾署名样例】
...

【综合风格参考】
...
```

Current limitations:

- This style context endpoint does not call Qwen; it only prepares style examples for generation endpoints.
- Style context currently uses deterministic keyword/slot retrieval.
- `semantic_enabled` is currently `false` for style context.
- The endpoint returns context and examples only, not generated qiaopi text.

## POST /api/generation/preview-prompt

Purpose: preview how retrieved RAG/style context is converted into chat messages without calling Qwen. This endpoint works when Qwen is disabled.

Request:

```json
{
  "task_type": "style-transfer",
  "input_text": "母亲您好，我在新加坡平安，寄八元回家，请弟弟好好读书。",
  "top_k": 3,
  "filters": {},
  "expansion_mode": "balanced"
}
```

Response:

```json
{
  "task_type": "style-transfer",
  "input_text": "母亲您好，我在新加坡平安，寄八元回家，请弟弟好好读书。",
  "prompt_context": "【用户白话输入】\n母亲您好，我在新加坡平安，寄八元回家，请弟弟好好读书。\n\n【开头称谓样例】\n1. 慈亲大人膝下：\n来源：CSQP-SFHC-TEXT-017",
  "messages": [
    {
      "role": "system",
      "content": "你是侨批文体改写助手。..."
    },
    {
      "role": "user",
      "content": "请把用户白话内容改写为侨批体草稿。..."
    }
  ],
  "evidence_references": [
    {
      "record_id": "CSQP-SFHC-TEXT-017",
      "unit_id": "CSQP-SFHC-TEXT-017-RU-OPENING-001",
      "unit_type": "opening",
      "title_reference": "题名文本",
      "source_column": "evidence_opening",
      "evidence_type": "opening",
      "unit_text": "慈亲大人膝下："
    }
  ]
}
```

For `task_type: "interpret"`, `input_text` is treated as the interpretation query. An optional `record_id` can be provided to build context from a specific record.

## POST /api/generation/interpret

Purpose: generate a concise modern Chinese explanation of qiaopi content based on retrieved evidence.

Request:

```json
{
  "query": "这封侨批主要说了什么？",
  "record_id": "CSQP-SFHC-TEXT-017",
  "top_k": 8,
  "filters": {},
  "expansion_mode": "balanced",
  "dry_run": false
}
```

Behavior:

- If `record_id` is provided, the endpoint uses that record's retrieval units as primary context.
- If `record_id` is absent, the endpoint uses `/api/rag/context` retrieval logic.
- If `dry_run` is `true`, Qwen is not called and `messages` are returned for review.
- If Qwen is disabled or misconfigured, the endpoint returns a controlled `error_message` and prompt preview data instead of crashing.

Response:

```json
{
  "task_type": "interpret",
  "query": "这封侨批主要说了什么？",
  "record_id": "CSQP-SFHC-TEXT-017",
  "semantic_enabled": false,
  "prompt_context": "【检索问题】\n这封侨批主要说了什么？\n\n【相关侨批证据 1】\n来源记录：CSQP-SFHC-TEXT-017\n...",
  "generated_text": "【生成解读】...",
  "evidence_references": [
    {
      "record_id": "CSQP-SFHC-TEXT-017",
      "unit_id": "CSQP-SFHC-TEXT-017-RU-BODY-CORE-001",
      "unit_type": "body_core",
      "title_reference": "题名文本",
      "source_column": "body_core",
      "evidence_type": "body_core",
      "unit_text": "兹寄批局，带去洋银肆元，至照查收，以安家计。"
    }
  ],
  "model": "qwen-plus",
  "dry_run": false,
  "messages": [
    {
      "role": "system",
      "content": "你是侨批历史文献解读助手。..."
    }
  ],
  "error_message": null,
  "validation_report": {
    "is_consistent": true,
    "risk_level": "low",
    "summary": "解释文本通过规则式证据一致性检查。",
    "preserved_facts": ["源证据中的汇款信息已覆盖"],
    "possible_hallucinations": [],
    "missing_required_facts": [],
    "unsupported_new_facts": [],
    "evidence_coverage": {
      "has_evidence_references": true,
      "evidence_count": 8,
      "covered_unit_types": ["body_core", "remittance"]
    },
    "checks": [
      {
        "name": "amount_support_check",
        "status": "pass",
        "message": "解释文本未新增证据外金额。"
      }
    ]
  }
}
```

Interpretation prompt requirements:

- Use modern Chinese to explain the qiaopi content.
- Explain who wrote to whom.
- State whether there is remittance, amount, and purpose.
- Explain main emotion and instructions.
- Do not invent information missing from evidence.
- Say `不确定` when evidence is insufficient.
- Clearly mark the output as generated interpretation, not historical source text.

## POST /api/generation/style-transfer

Purpose: convert plain Chinese into a qiaopi-style generated draft using real retrieved qiaopi style examples.

Request:

```json
{
  "plain_text": "母亲您好，我在新加坡平安，寄八元回家，请弟弟好好读书。",
  "top_k": 3,
  "filters": {},
  "expansion_mode": "balanced",
  "dry_run": false
}
```

Behavior:

- Uses `/api/rag/style-context` logic to retrieve examples for `opening`, `safety`, `remittance`, `family_care`, `instruction`, `closing`, and `style_reference`.
- If `dry_run` is `true`, Qwen is not called and prompt messages are returned.
- If Qwen is disabled or misconfigured, the endpoint returns a controlled `error_message` and prompt preview data instead of crashing.

Response:

```json
{
  "task_type": "style-transfer",
  "plain_text": "母亲您好，我在新加坡平安，寄八元回家，请弟弟好好读书。",
  "semantic_enabled": false,
  "style_slots": {
    "opening": [
      {
        "record_id": "CSQP-SFHC-TEXT-017",
        "unit_id": "CSQP-SFHC-TEXT-017-RU-OPENING-001",
        "unit_type": "opening",
        "title_reference": "题名文本",
        "unit_text": "慈亲大人膝下：",
        "source_column": "evidence_opening",
        "evidence_type": "opening",
        "matched_reason": "命中开头称谓；原始查询命中“慈亲/膝下”",
        "final_score": 2.14
      }
    ],
    "safety": [],
    "remittance": [],
    "family_care": [],
    "instruction": [],
    "closing": [],
    "style_reference": []
  },
  "prompt_context": "【用户白话输入】\n母亲您好，我在新加坡平安，寄八元回家，请弟弟好好读书。\n...",
  "generated_text": "【生成侨批体草稿】...",
  "evidence_references": [
    {
      "record_id": "CSQP-SFHC-TEXT-017",
      "unit_id": "CSQP-SFHC-TEXT-017-RU-OPENING-001",
      "unit_type": "opening",
      "title_reference": "题名文本",
      "source_column": "evidence_opening",
      "evidence_type": "opening",
      "unit_text": "慈亲大人膝下："
    }
  ],
  "model": "qwen-plus",
  "dry_run": false,
  "messages": [
    {
      "role": "system",
      "content": "你是侨批文体改写助手。..."
    }
  ],
  "error_message": null,
  "validation_report": {
    "is_consistent": true,
    "risk_level": "low",
    "summary": "规则校验完成：生成文本与输入事实基本一致。",
    "preserved_facts": ["输入金额已保留"],
    "possible_hallucinations": [],
    "missing_required_facts": [],
    "unsupported_new_facts": [],
    "evidence_coverage": {
      "has_evidence_references": true,
      "evidence_count": 21,
      "covered_unit_types": ["opening", "safety", "remittance", "instruction", "closing", "style_reference"]
    },
    "checks": [
      {
        "name": "amount_consistency",
        "status": "pass",
        "message": "输入金额在生成文本中以等值中文金额形式保留。"
      }
    ]
  }
}
```

Style transfer prompt requirements:

- Write qiaopi-style text from the user's plain Chinese.
- Reference real qiaopi examples without copying long passages verbatim.
- Preserve user-provided people, places, amounts, and instructions.
- Do not add amounts, dates, or names absent from user input.
- Output generated draft, style-basis explanation, and reference evidence list.
- Clearly mark the output as generated content, not historical source text.

## POST /api/validation/consistency-check

Purpose: run deterministic evidence and fact consistency checks on generated outputs. This endpoint does not call Qwen.

Style-transfer request:

```json
{
  "task_type": "style-transfer",
  "input_text": "母亲您好，我在新加坡平安，寄八元回家，请弟弟好好读书。",
  "generated_text": "慈亲大人膝下：儿客居叻埠平安，兹奉上大洋银捌元，祈查收。另望胞弟勤学向上。儿谨禀。",
  "evidence_references": [],
  "record_id": null
}
```

Interpretation request:

```json
{
  "task_type": "interpret",
  "input_text": "这封侨批主要说了什么？",
  "generated_text": "生成解读：这封侨批提到寄款查收，并嘱家中照用。",
  "evidence_references": [],
  "record_id": "CSQP-SFHC-TEXT-017"
}
```

Response:

```json
{
  "validation_report": {
    "is_consistent": true,
    "risk_level": "medium",
    "summary": "规则校验完成：生成文本与输入事实基本一致。",
    "preserved_facts": [
      "母亲称谓已保留为亲属/尊称表达",
      "新加坡地点已以允许别名保留",
      "输入金额已保留",
      "弟弟读书嘱托已保留"
    ],
    "possible_hallucinations": [
      "生成文本未明确标注为生成草稿"
    ],
    "missing_required_facts": [],
    "unsupported_new_facts": [],
    "evidence_coverage": {
      "has_evidence_references": false,
      "evidence_count": 0,
      "covered_unit_types": []
    },
    "checks": [
      {
        "name": "amount_consistency",
        "status": "pass",
        "message": "输入金额在生成文本中以等值中文金额形式保留。"
      },
      {
        "name": "place_consistency",
        "status": "pass",
        "message": "输入地点新加坡在生成文本中以新加坡/星洲/叻/叻埠/石叻等允许别名保留。"
      }
    ]
  }
}
```

Risk levels:

- `low`: no suspicious fact drift and evidence references are present.
- `medium`: missing evidence references or non-critical warnings require review.
- `high`: unsupported new amounts, dates, names, or places were detected.

The generation endpoints attach `validation_report` after successful live generation. For `dry_run=true`, disabled Qwen, timeout, or any empty `generated_text`, `validation_report` is `null`.

Current validation limitations:

- Validation is rule-based and deterministic.
- It reduces hallucination risk but cannot guarantee perfect historical accuracy.
- It only checks supported fact categories: people, places, amounts, dates, kinship, remittance, study, and safety expressions.
- It does not use FAISS, embeddings, or Qwen.

## Qwen Configuration

Generation uses these environment variables:

```text
QWEN_API_KEY=
QWEN_BASE_URL=
QWEN_MODEL=qwen-plus
QWEN_TIMEOUT_SECONDS=60
QWEN_ENABLED=false
```

`QWEN_ENABLED=false` or a missing API key means live generation is disabled. Dry runs and prompt preview still work without a real key. API keys are never returned in responses or logs.

## GET /api/generation/qwen-status

Purpose: safely diagnose whether the running backend process has Qwen generation enabled. This endpoint never returns `QWEN_API_KEY` or any secret value.

Response:

```json
{
  "enabled": true,
  "api_key_configured": true,
  "base_url_configured": true,
  "model": "qwen-plus",
  "timeout_seconds": 60,
  "project_env_exists": true,
  "backend_env_exists": false,
  "live_generation_ready": true
}
```

If `/api/generation/style-transfer` still returns a disabled message while `qwen-status.live_generation_ready` is `true`, then the request is likely hitting a stale process or a different port.

## Semantic Retrieval Configuration

Semantic retrieval uses these environment variables:

```text
SEMANTIC_SEARCH_ENABLED=false
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
EMBEDDING_DIM=
EMBEDDING_BATCH_SIZE=32
FAISS_INDEX_DIR=backend/data/index
FAISS_INDEX_PATH=backend/data/index/qiaopi_retrieval_units.faiss
FAISS_METADATA_PATH=backend/data/index/qiaopi_retrieval_units_meta.jsonl

QWEN_EMBEDDING_API_KEY=
QWEN_EMBEDDING_BASE_URL=
QWEN_EMBEDDING_MODEL=
```

Build command:

```powershell
cd backend
python -m app.ingestion.build_database
python -m app.ingestion.build_semantic_index
```

For deterministic local tests without external models:

```powershell
python -m app.ingestion.build_semantic_index --provider hash
```

`backend/data/index/*` is generated artifact data and should not contain committed secrets. `.env.example` is documentation only; real runtime configuration is read from `.env` files, not from `.env.example`.

Current limitations:

- Semantic search is disabled by default and requires an index build plus `SEMANTIC_SEARCH_ENABLED=true`.
- Qwen requires environment variables before live generation.
- Generated content is not historical source material.
- Generated content must be displayed with evidence references.

## Metadata Catalog Layer

Purpose: Step G adds a 50064-record archive catalog layer. It supports metadata search, archive browsing, statistics, timeline views, place distribution, and links back to the 213 full-text qiaopi records.

Build commands:

```powershell
cd backend
python -m app.ingestion.build_metadata_database
python -m app.ingestion.link_metadata_text_records
```

Tables:

- `qiaopi_metadata_records`
- `qiaopi_metadata_fts`
- `qiaopi_text_metadata_links`
- `qiaopi_text_metadata_link_candidates`

Evidence boundary:

- Metadata-only records are not full-text evidence.
- Metadata-only records must not be used in `qiaopi_retrieval_units`, `qiaopi_retrieval_units_fts`, FAISS semantic retrieval, RAG context, or Qwen prompts.
- If a metadata record is linked, generation must use the linked 213 full-text `record_id` as evidence, not the metadata-only fields.

Linking rules:

- `link_confidence >= 0.92`: auto-link one best metadata record to a full-text `record_id`.
- `0.75 <= confidence < 0.92`: store as a manual-review candidate.
- `confidence < 0.75`: ignore.

## GET /api/metadata/stats

Response:

```json
{
  "total_metadata_records": 50064,
  "linked_text_count": 1,
  "unlinked_metadata_count": 50063,
  "link_candidate_count": 4,
  "has_remittance_count": 10,
  "needs_review_count": 24934,
  "year_min": 1915,
  "year_max": 2003
}
```

## GET /api/metadata/distributions

Response:

```json
{
  "year_distribution": [{"label": "1969", "value": 1221}],
  "country_or_region_distribution": [{"label": "泰国", "value": 24307}],
  "origin_place_distribution": [{"label": "新加坡", "value": 18520}],
  "destination_place_distribution": [{"label": "广东潮安", "value": 10550}],
  "relationship_distribution": [{"label": "child_to_parent", "value": 16015}],
  "theme_distribution": [{"label": "theme_archive_catalog", "value": 50064}],
  "has_remittance_distribution": [
    {"label": "true", "value": 10},
    {"label": "false", "value": 50054}
  ]
}
```

## POST /api/metadata/search

Uses `qiaopi_metadata_fts` for metadata search. It does not search full-text evidence, RAG retrieval units, or generated text.

Request:

```json
{
  "query": "新加坡 母亲 寄款",
  "top_k": 20,
  "filters": {
    "year_from": 1930,
    "year_to": 1955,
    "country_or_region": "新加坡",
    "has_remittance": true,
    "has_linked_text": true
  }
}
```

Response:

```json
{
  "query": "新加坡 母亲 寄款",
  "top_k": 20,
  "results": [
    {
      "metadata_id": "CSQP-META-001389",
      "title_clean": "新加坡夏碧粧寄广东母亲侨批",
      "sender_raw": "夏碧粧",
      "recipient_raw": "母亲",
      "date_text": "[不详]",
      "year_normalized": "",
      "origin_place": "新加坡",
      "destination_place": "广东",
      "country_or_region": "新加坡",
      "remittance_raw": "",
      "has_remittance": 0,
      "has_linked_text": 0,
      "linked_record_id": "",
      "score": -2.5,
      "snippet": "新加坡夏碧粧寄广东母亲侨批"
    }
  ]
}
```

Supported filters: `year_from`, `year_to`, `country_or_region`, `origin_place`, `destination_place`, `place`, `has_remittance`, `has_linked_text`, `needs_review`, `relationship_type`, and `main_intent`.

## GET /api/metadata/{metadata_id}

Returns the parsed metadata catalog record plus the original Excel row in `raw_json`.

## GET /api/metadata/{metadata_id}/linked-text

If linked, returns `linked_record_id` and a full-text record summary. If not linked, returns:

```json
{
  "metadata_id": "CSQP-META-000001",
  "has_linked_text": false,
  "linked_record_id": null,
  "record_detail_summary": null,
  "message": "This metadata record has no linked full-text qiaopi record."
}
```

This endpoint never generates or infers missing full text.

## GET /api/metadata/links/stats

Response:

```json
{
  "auto_link_count": 1,
  "candidate_link_count": 4,
  "unlinked_full_text_count": 212,
  "link_method_distribution": [{"label": "field_composite", "value": 1}],
  "average_link_confidence": 0.92
}
```

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
