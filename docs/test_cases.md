# Frontend Workflow Test Cases

## 1. Dashboard

- Open `/dashboard`.
- Verify metadata count, text count, place distribution, relationship
  distribution, and timeline render from the dashboard APIs.
- With `VITE_DEMO_MODE=false`, stop the backend and verify the page shows an
  interface error and does not load deterministic Mock data.
- With `VITE_DEMO_MODE=true`, repeat and verify fallback data is explicitly
  labelled as demonstration data.

## 2. Keyword Search

- Open `/search` and select keyword mode.
- Search for `母亲 寄款 查收`.
- Verify each result shows a retrieval unit, matched reason, source field,
  BM25/keyword-rerank contribution, and a record-detail link.
- Verify scores are raw ranking contributions, never percentages.

## 3. Semantic and Hybrid Status

- With semantic retrieval disabled, run semantic search.
- Verify the page shows the controlled backend message and does not label
  keyword fallback as semantic results.
- Run hybrid search and verify `fusion_method=keyword_fallback` is represented
  as `关键词检索（混合降级）`.
- With a test semantic index enabled, verify semantic results and RRF hybrid
  results can differ from keyword ordering and are labelled `测试向量`.
- With a validated production index, verify BM25, cosine similarity, and RRF
  are displayed as separate, non-comparable ranking contributions.

## 4. Record Detail

- Open `/records/CSQP-SFHC-TEXT-002`.
- Verify `body_clean`, normalized metadata, entities, and evidence are loaded
  from the current record APIs.
- Similar-record recommendations are not expected in this contract version.

## 5. Plain Interpretation

- Open `/plain-interpretation`.
- Use record `CSQP-SFHC-TEXT-017`.
- Verify the page calls `POST /api/generation/interpret`.
- With scaffold mode active, verify
  `generation_backend=deterministic_local`,
  `degraded_reason=scaffold_phase_active`, model/prompt/index versions, and
  sentence-level evidence mappings.
- Repeat the same request and verify `cache_hit=true`.
- Verify the page never labels deterministic fallback as Qwen.

## 6. Style Transfer

- Open `/style-transfer`.
- Enter a short modern family letter.
- Verify the page calls `POST /api/generation/style-transfer` with
  `dry_run=false`; the backend safety gate decides whether Qwen is permitted.
- Verify style slots, structured output, evidence mappings, actual generation
  backend, model, prompt/index versions, cache state, and degradation reason.
- In CI, enable the scaffold flag only with a simulated Qwen client and assert
  no real network request is made.

## 7. Online NLP

- Open `/nlp`.
- Submit text containing a kinship term, place alias, money amount, date, and
  qiaopi formula.
- Verify the page calls `POST /api/nlp/analyze` and explicitly labels the
  current engine as deterministic rules, not a statistical model.
- Verify every entity, relation, and slot displays original and normalized
  half-open offsets, extractor version, confidence, and review state.
- Verify slicing the returned original and normalized texts by those offsets
  reproduces `source_text` and `normalized_source_text`.
- Enter text containing `□`, `�`, `疑为`, or `不清` and verify the review
  warning is visible.
- Stop the backend and verify the page reports an API error without loading
  mock NLP output.

## 8. Knowledge Graph

- Open `/knowledge-graph`.
- Verify graph counts and quality indicators come from `/api/graph/stats`.
- Load `CSQP-SFHC-TEXT-063` and verify the record subgraph contains record,
  evidence, and linked metadata nodes.
- Click an evidence node and verify the trace panel resolves its
  `source_table`, `source_id`, original evidence text, and record-detail link.
- Click a metadata node and verify the metadata detail and linked full-text
  record are displayed.
- Click a shared person or place node and verify neighbor edges produce
  traceable record links and edge evidence.
- Verify duplicate logical edges, orphan edges, and missing provenance counts
  are zero.

## 9. Contract Failure Checks

- Requests to `/api/generation/plain-interpretation` return 404.
- Requests to `/api/records/{record_id}/similar` return 404.
- The backend contract test must fail if an endpoint or schema changes without
  an intentional baseline update.

## 10. Production Mock Boundary

- Build or run with `VITE_DEMO_MODE=false`.
- Stop the backend and visit all formal workflows, including the graph page.
- Verify no page silently inserts data from `frontend/src/mock/`.
- Repeat with `VITE_DEMO_MODE=true` and verify every fallback message contains
  an explicit demonstration-mode label.
