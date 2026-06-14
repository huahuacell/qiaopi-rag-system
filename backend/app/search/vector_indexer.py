from app.settings import SEMANTIC_FAISS_INDEX_PATH, SEMANTIC_FAISS_METADATA_PATH


def build_vector_index_placeholder() -> dict:
    return {
        "status": "available",
        "index_path": str(SEMANTIC_FAISS_INDEX_PATH),
        "metadata_path": str(SEMANTIC_FAISS_METADATA_PATH),
        "message": "Run python -m app.ingestion.build_semantic_index to build the semantic index.",
    }
