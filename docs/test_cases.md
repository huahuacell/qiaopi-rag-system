# Frontend Workflow Test Cases

## 1. Dashboard

- Open `/dashboard`.
- Verify metadata count, text count, place distribution, relationship
  distribution, and timeline render from the dashboard APIs.
- Stop the backend and verify the page clearly labels deterministic fallback
  data.

## 2. Keyword Search

- Open `/search` and select keyword mode.
- Search for `母亲 寄款 查收`.
- Verify each result shows a retrieval unit, matched reason, source field,
  BM25/final score data, and a record-detail link.

## 3. Semantic and Hybrid Status

- With semantic retrieval disabled, run semantic search.
- Verify the page shows the controlled backend message and does not label
  keyword fallback as semantic results.
- Run hybrid search and verify `fusion_method=keyword_fallback` is represented
  as degradation.
- With a test semantic index enabled, verify semantic results and RRF hybrid
  results can differ from keyword ordering.

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
