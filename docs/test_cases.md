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
- In the current frontend baseline, verify `dry_run=true`, evidence references
  and prompt context are returned, and no live Qwen request is required.

## 6. Style Transfer

- Open `/style-transfer`.
- Enter a short modern family letter.
- Verify the page calls `POST /api/generation/style-transfer` with
  `dry_run=true`.
- Verify style slots and evidence references render even when generated text is
  empty.

## 7. Contract Failure Checks

- Requests to `/api/generation/plain-interpretation` return 404.
- Requests to `/api/records/{record_id}/similar` return 404.
- The backend contract test must fail if an endpoint or schema changes without
  an intentional baseline update.

## 8. Production Mock Boundary

- Build or run with `VITE_DEMO_MODE=false`.
- Stop the backend and visit all six workflows.
- Verify no page silently inserts data from `frontend/src/mock/`.
- Repeat with `VITE_DEMO_MODE=true` and verify every fallback message contains
  an explicit demonstration-mode label.
