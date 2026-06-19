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

Show the “actual execution mode” panel. Explain that BM25, cosine similarity,
and RRF are displayed as separate ranking contributions rather than converted
to percentages.

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

## 8:30–9:10 Online NLP

Open `/nlp`. Submit the sample letter and show normalized text, entity and
relation extraction, task slots, original/normalized offsets, rule versions,
confidence, and review markers. Explain that online and offline preprocessing
share `qiaopi-text-normalizer-1.0.0`.

## 9:10–9:45 Knowledge Graph

Open `/knowledge-graph`. Load `CSQP-SFHC-TEXT-063`, click an evidence node and
then the linked metadata node. Show source table/source ID, original evidence,
metadata details, and the record-detail links. Point out that all structural
quality counters are zero.

Clarify that `kg-viewer/` is now a Frontend Developer-owned diagnostic sandbox;
the formal product workflow is the main `frontend/` route.

## 9:45–10:00 Runtime Boundary

Show the top-right runtime badge. `VITE_DEMO_MODE=false` is the production
default and never silently loads Mock JSON. `VITE_DEMO_MODE=true` is reserved
for an explicitly labelled offline demonstration.
