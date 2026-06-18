from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dashboard_routes import router as dashboard_router
from app.api.generation_routes import router as generation_router
from app.api.record_routes import router as record_router
from app.api.search_routes import router as search_router
from app.schemas import HealthResponse


def create_app() -> FastAPI:
    app = FastAPI(
        title="Qiaopi RAG System API",
        description="Local Qiaopi NLP/RAG API backed by SQLite where available.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        return HealthResponse(
            status="healthy",
            version="0.1.0",
            message="Qiaopi RAG backend is running",
        )

    app.include_router(dashboard_router)
    app.include_router(search_router)
    app.include_router(record_router)
    app.include_router(generation_router)
    return app


app = create_app()

