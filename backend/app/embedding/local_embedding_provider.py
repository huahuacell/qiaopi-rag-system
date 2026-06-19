from __future__ import annotations

import numpy as np

from app import settings
from app.embedding.embedding_provider import EmbeddingProviderError, l2_normalize


class LocalEmbeddingProvider:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.EMBEDDING_MODEL
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbeddingProviderError(
                "sentence-transformers is not installed. Install the production "
                "semantic dependency. EMBEDDING_PROVIDER=hash is available only "
                "for deterministic tests and cannot pass semantic acceptance."
            ) from exc
        self.model = SentenceTransformer(self.model_name)

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        embeddings = self.model.encode(
            texts,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return l2_normalize(np.asarray(embeddings, dtype=np.float32))
