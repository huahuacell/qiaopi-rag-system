# Qiaopi RAG System

Local Vue 3 + FastAPI application for Qiaopi archive browsing, retrieval,
evidence tracing, graph exploration, and evidence-grounded generation work.

Current contract baseline: `2026-06-23-graphrag`

## Current Capabilities

- SQLite dashboard over 213 full-text records and 50,064 metadata records.
- FTS5/BM25 retrieval over 1,959 retrieval units.
- Production local vector semantic retrieval and RRF hybrid fusion.
- Evidence-grounded local GraphRAG over the SQLite knowledge graph.
- Metadata keyword, semantic, and hybrid catalog search with separate vectors.
- Record detail, amount, entity, place, evidence, and retrieval-unit APIs.
- SQLite knowledge-graph build and query APIs.
- RAG/style context, prompt preview, optional Qwen generation, and rule-based
  consistency reports.

Semantic retrieval requires its runtime flag and validated index artifacts.
Full-text and metadata vectors remain separate. Hybrid and GraphRAG retrieval
report explicit fallback states when a configured retrieval source did not
participate. The official frontend currently sends generation requests with
`dry_run=true`, so it does not trigger live Qwen calls.

Similarity recommendation and online NLP extraction are not part of the current
public API.

## Tech Stack

- Frontend: Vue 3, Vite, Element Plus, Axios, Vue Router, ECharts
- Backend: Python, FastAPI, SQLite, Pydantic, pandas, FTS5, NumPy/FAISS
- Optional integrations: sentence-transformers and OpenAI-compatible Qwen APIs

## Run Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend URLs:

- API: `http://localhost:8000`
- OpenAPI UI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/health`

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Environment

Copy `.env.example` to `.env` for local overrides. Never commit real secrets.
Qwen and semantic retrieval remain opt-in. See `docs/api_contract.md` for the
current configuration fields and behavior.

## Data and Index Commands

Run commands from `backend/`:

```bash
python -m app.ingestion.preprocess_qiaopi_wide_table
python -m app.ingestion.build_database
python -m app.ingestion.build_metadata_database
python -m app.ingestion.link_metadata_text_records
python -m app.ingestion.build_semantic_index --provider local
python -m app.ingestion.build_metadata_semantic_index --provider local
python -m app.ingestion.build_knowledge_graph
```

These commands are currently separate stages; a single safe `build-all`
orchestrator is still pending.

## Contract Rules

The running OpenAPI document and `docs/api_contract.md` define the converged
public API. `backend/tests/test_api_contract.py` freezes public operations and
the canonical OpenAPI digest.

The old `/api/generation/plain-interpretation` and
`/api/records/{record_id}/similar` routes are not part of the current contract.

## Verification

```bash
cd backend
python -m pytest -q
```

```bash
cd frontend
npm run build
```

See `AGENTS.md` for backend/frontend ownership boundaries.
