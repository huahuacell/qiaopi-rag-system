# Development Workflow

## Scaffold Phase

1. Create the project structure.
2. Start the backend at `http://localhost:8000`.
3. Start the frontend at `http://localhost:5173`.
4. Verify `/api/health`, `/docs`, and all frontend pages.
5. Confirm pages render with backend API responses or fallback mock JSON.

## Backend Phase

1. Place Excel files under `backend/data/raw/`.
2. Build the SQLite database from raw spreadsheets.
3. Implement real dashboard statistics.
4. Implement keyword search.
5. Implement semantic search and FAISS index build steps.
6. Implement entity extraction.
7. Implement RAG generation and Qwen integration.

## Frontend Phase

1. Use mock data first.
2. Build all six views against the API contract.
3. Switch to real API responses after backend readiness.
4. Keep loading, error, and empty states visible and tested.
5. Avoid embedding backend business logic in views.

## Integration Phase

1. Freeze API response fields before connecting real data.
2. Test all six core features.
3. Prepare demo cases and stable record IDs.
4. Capture screenshots for the classroom demo.
5. File contract changes as explicit API updates.

## Demo Phase

1. Start backend with `uvicorn main:app --reload`.
2. Start frontend with `npm run dev`.
3. Follow `docs/demo_script.md`.
4. Show fallback behavior if the backend is stopped.
5. End with next-step ownership for backend and frontend developers.

## API Freeze Rule

After a response field is documented in `docs/api_contract.md`, do not rename or remove it without updating tests, frontend mocks, and both developers.

## Mock-First Rule

Every feature must work with deterministic mock data before real Excel, FAISS, or Qwen integration begins.

## No-Cross-Boundary Rule

Backend and frontend developers should stay inside their assigned directories. Cross-boundary changes require explicit agreement.

