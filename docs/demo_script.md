# 10-Minute Demo Script

## 0:00–1:00 Project and Contract

Open the README and explain the `2026-06-19-converged` API baseline. State that
OpenAPI, the contract document, clients, and tests now describe one interface.

## 1:00–2:00 Backend API

Open `http://localhost:8000/docs`. Show search, metadata, record, RAG,
generation, validation, and graph endpoint groups.

Mention that `/api/generation/plain-interpretation` and
`/api/records/{record_id}/similar` are not current endpoints.

## 2:00–3:00 Dashboard

Open `/dashboard`. Show SQLite-backed metadata/text counts and distributions.

## 3:00–4:30 Search

Open `/search` and run keyword and hybrid searches. If semantic retrieval is
disabled, point out the controlled `keyword_fallback` state instead of
presenting it as true semantic fusion.

## 4:30–5:30 Record Detail

Open `/records/CSQP-SFHC-TEXT-002`. Show `body_clean`, metadata, entities, and
evidence from SQLite.

## 5:30–7:00 Plain Interpretation

Open `/plain-interpretation` with `CSQP-SFHC-TEXT-017`. Explain that the page now
calls `/api/generation/interpret`. The current demo uses `dry_run=true`, showing
evidence-grounded prompt preparation without making a live Qwen call.

## 7:00–8:30 Style Transfer

Open `/style-transfer`. Submit a short family letter and show retrieved style
slots and evidence references. The current frontend also uses `dry_run=true`.

## 8:30–9:30 Knowledge Graph

Use the standalone `kg-viewer/` if it is running, or show `/api/graph/stats` and
one record graph in Swagger. Clarify that the official `frontend/` analysis page
has not yet integrated these graph APIs.

## 9:30–10:00 Next Work

Summarize the remaining work: one-command reproducible build, production-grade
semantic configuration, official metadata/graph frontend integration, vector
similarity recommendations, online NLP, Qwen retry/cache/structured output, and
quality evaluation.
