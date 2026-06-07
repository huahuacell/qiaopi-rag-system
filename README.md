# Qiaopi RAG System

Local-only full-stack scaffold for a Qiaopi document NLP/RAG system. This phase focuses on a stable project skeleton, API contract, deterministic mock services, and demo-ready Vue pages. Heavy NLP models, real Qwen API calls, and real Excel ingestion are intentionally left as later work.

## Tech Stack

- Frontend: Vue 3, Vite, Element Plus, Axios, Vue Router, ECharts
- Backend: Python, FastAPI, SQLite, Pydantic, pandas placeholders, FAISS placeholder structure, Qwen placeholder client
- Local frontend: http://localhost:5173
- Local backend: http://localhost:8000
- Backend API docs: http://localhost:8000/docs

## Run Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Verify:

```bash
curl http://localhost:8000/api/health
```

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

## Environment

Copy `.env.example` to `.env` when you need local overrides. Do not commit real secrets.

```bash
DASHSCOPE_API_KEY=
VITE_API_BASE_URL=http://localhost:8000
```

The scaffold does not call the real Qwen API. `DASHSCOPE_API_KEY` is read only so the later integration has a stable place to start.

## Raw Excel Files

Place the final Excel files here when the backend phase begins:

- `backend/data/raw/qiaopi_50064_metadata.xlsx`
- `backend/data/raw/qiaopi_213_text.xlsx`

The app runs without these files during the scaffold phase.

## Six Core Features

1. Data dashboard and filtering
2. Keyword search and conditional search
3. Semantic search and similar record recommendation
4. Entity extraction and evidence cards
5. Qiaopi original text to plain Chinese interpretation
6. Plain Chinese letter to Qiaopi-style text transfer with evidence mapping

## Two-Person Workflow

- Backend developer owns `backend/` and `docs/api_contract.md`.
- Frontend developer owns `frontend/`, `docs/test_cases.md`, and `docs/demo_script.md`.
- API fields should stay stable after definition.
- Both sides work mock-first, then integrate against the fixed contract.

See `AGENTS.md` and `docs/workflow.md` for the detailed boundary and handoff rules.

## Verification Commands

```bash
cd backend
pytest
```

```bash
cd frontend
npm run build
```

