from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dashboard import router as dashboard_router
from app.api.generation import router as generation_router
from app.api.graph import router as graph_router
from app.api.metadata import router as metadata_router
from app.api.nlp import router as nlp_router
from app.api.rag import router as rag_router
from app.api.records import router as record_router
from app.api.search import router as search_router
from app.api.validation import router as validation_router
from app.schemas import HealthResponse


def create_app() -> FastAPI:
    app = FastAPI(
        title="Qiaopi RAG System API",
        description="SQLite-backed API for the Qiaopi NLP/RAG backend foundation.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
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
    app.include_router(metadata_router)
    app.include_router(nlp_router)
    app.include_router(rag_router)
    app.include_router(generation_router)
    app.include_router(validation_router)
    app.include_router(graph_router)
    return app


app = create_app()
