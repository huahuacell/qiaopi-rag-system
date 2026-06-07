from app.settings import FAISS_INDEX_PATH, FAISS_METADATA_PATH


def build_vector_index_placeholder() -> dict:
    return {
        "status": "placeholder",
        "index_path": str(FAISS_INDEX_PATH),
        "metadata_path": str(FAISS_METADATA_PATH),
        "message": "FAISS index build is reserved for the backend phase.",
    }

