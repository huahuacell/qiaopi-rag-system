# Qiaopi KG Viewer

Standalone knowledge graph viewer for the Qiaopi RAG system.

## Purpose

`kg-viewer/` previews the SQLite knowledge graph exposed by the backend Graph
API. It is owned by the Frontend Developer as a diagnostic and development
sandbox.

The formal product graph workflow lives in `frontend/` at
`/knowledge-graph`. Features implemented only in this standalone viewer are not
considered product acceptance.

## Tech Stack

- Vue 3
- Vite
- Element Plus
- ECharts
- Axios

## Backend Prerequisite

Run the backend and build the SQLite KG tables first:

```bash
cd backend
python -m app.ingestion.build_database
python -m app.ingestion.build_metadata_database
python -m app.ingestion.link_metadata_text_records
python -m app.ingestion.build_knowledge_graph
uvicorn main:app --reload
```

Default API base URL:

```text
http://localhost:8000
```

## Run

```bash
cd kg-viewer
npm install
npm run dev
```

The dev server uses:

```text
http://localhost:5173
```

## Examples

Default record ID:

```text
CSQP-SFHC-TEXT-017
```

Default node ID:

```text
person:母亲
```

## Scope

Implemented:

- Graph stats display
- Record graph display
- Overview graph display
- Place flow table
- Node neighbor display
- Chinese display labels for theme, node type, and edge type values
- Short graph labels for record and evidence nodes, with full details kept in tooltips
- Evidence-node visibility toggle for overview and record graphs

Not implemented:

- Neo4j integration
- Graph analytics algorithms
- Authentication or deployment integration beyond the formal `frontend/`
