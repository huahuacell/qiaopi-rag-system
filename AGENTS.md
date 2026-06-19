# Agent Role Boundaries

This project is designed for two developers to continue independently after the scaffold phase.

## Backend Developer

Can modify:

- `backend/`
- `docs/api_contract.md`
- `docs/technology_acceptance_matrix.md`

Responsibilities:

- Keep FastAPI endpoints aligned with the API contract.
- Add SQLite ingestion and real search implementations later.
- Add NLP, RAG, and Qwen integration only after mock behavior is verified.
- Never hard-code API keys.
- Do not call the real Qwen API during the scaffold phase.
- Own the cross-layer technology acceptance matrix and update it only from
  verified backend, API, frontend, and test evidence.

## Frontend Developer

Can modify:

- `frontend/`
- `kg-viewer/`
- `docs/test_cases.md`
- `docs/demo_script.md`

Responsibilities:

- Build and refine the six user-facing workflows.
- Use mock JSON first and switch to backend API responses when available.
- Preserve loading, empty, and error states.
- Do not hard-code backend response logic inside views.
- Treat `frontend/` as the only formal product frontend.
- Maintain `kg-viewer/` as a diagnostic graph sandbox. Product-only graph
  workflows must be implemented in `frontend/`, not only in `kg-viewer/`.

## Shared Rules

- Do not cross boundaries unless explicitly requested.
- Keep API fields stable after definition.
- Use English file names only.
- Use relative project paths only.
- Never commit real API keys.
- Keep mock responses deterministic.
