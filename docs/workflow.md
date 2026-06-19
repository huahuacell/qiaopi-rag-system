# Development Workflow

## Current Baseline

The active API baseline is `2026-06-19-converged`. FastAPI OpenAPI is the
executable source of truth and `docs/api_contract.md` is its human-readable
companion.

## Backend Workflow

1. Implement or change backend behavior.
2. Update Pydantic request/response models.
3. Update `docs/api_contract.md`.
4. Update integration tests.
5. If the public contract changed intentionally, update the frozen OpenAPI
   digest in `backend/tests/test_api_contract.py`.
6. Run the complete backend suite.

Do not update the digest merely to silence a failure.

## Frontend Workflow

1. Consume endpoints only through `frontend/src/api/`.
2. Keep loading, empty, disabled-feature, degradation, and error states visible.
3. Treat `semantic_enabled` and `fusion_method` as runtime truth.
4. Keep mock fallback deterministic and use it only after request failure.
5. Update affected mocks and workflow tests when a contract changes.
6. Run `npm run build`.

## Compatible Changes

New endpoints and optional response fields are normally additive. They still
require documentation and affected client/test review.

## Breaking Changes

The following are breaking:

- removing or renaming an endpoint or field;
- changing field type or meaning;
- making an optional request/response field required;
- changing fallback or error semantics relied on by clients.

Use a coordinated migration, and prefer `/api/v2` if old and new clients must
coexist. Deprecated behavior must remain documented and tested until removal.

## Retired Scaffold Contract

- `/api/generation/plain-interpretation` is replaced by
  `/api/generation/interpret`.
- `/api/records/{record_id}/similar` has no replacement in the current baseline.

Do not add silent aliases for these routes.

## Verification Gate

A contract-related change is complete only when:

1. backend tests pass;
2. frontend build passes;
3. API documentation matches OpenAPI;
4. frontend API wrappers use the current routes;
5. acceptance and demo documents no longer claim retired behavior.

## Ownership

Backend and frontend developers follow `AGENTS.md`. Cross-boundary contract
changes require explicit coordination because they affect both owners.
