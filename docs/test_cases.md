# Test Cases

## 1. Dashboard And Filtering

- Open `/`.
- Expected: total records, text count, place distribution, kinship chart, and timeline chart render.
- Fallback check: stop backend and refresh; dashboard still renders from `frontend/src/mock/dashboard.json`.

## 2. Keyword Search

- Open `/search`.
- Select keyword mode.
- Search for `eight yuan`.
- Expected: result cards show matching snippets, metadata, scores, and evidence.

## 3. Semantic Search And Similar Records

- Open `/search`.
- Select semantic mode.
- Search for `a remittance letter to mother`.
- Expected: semantic results render with similarity scores.
- Open one record detail and verify similar records are listed.

## 4. Entity Extraction And Evidence Cards

- Open `/records/CSQP-SFHC-TEXT-001`.
- Expected: entity cards show people, places, kinship, money, and time entities with source evidence.

## 5. Plain Interpretation

- Open `/plain-interpretation`.
- Enter `CSQP-SFHC-TEXT-001`.
- Expected: generated plain interpretation, summary, slots, evidence table, and consistency result render.

## 6. Style Transfer

- Open `/style-transfer`.
- Enter a plain Chinese family letter.
- Expected: Qiaopi-style text, extracted slots, evidence mapping, and consistency result render.

