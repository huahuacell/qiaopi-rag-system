from __future__ import annotations

from typing import Protocol

import numpy as np

from app import settings


class EmbeddingProviderError(RuntimeError):
    """Controlled embedding provider configuration/runtime error."""


class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: list[str]) -> np.ndarray:
        ...


def l2_normalize(embeddings: np.ndarray) -> np.ndarray:
    vectors = np.asarray(embeddings, dtype=np.float32)
    if vectors.ndim != 2:
        raise EmbeddingProviderError("Embedding provider returned a non-2D array.")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (vectors / norms).astype(np.float32)


def get_embedding_provider(provider_name: str | None = None) -> EmbeddingProvider:
    provider = (provider_name or settings.EMBEDDING_PROVIDER).strip().lower()
    if provider == "hash":
        from app.embedding.hash_embedding_provider import HashEmbeddingProvider

        return HashEmbeddingProvider()
    if provider == "qwen":
        from app.embedding.qwen_embedding_provider import QwenEmbeddingProvider

        return QwenEmbeddingProvider()
    if provider == "local":
        from app.embedding.local_embedding_provider import LocalEmbeddingProvider

        return LocalEmbeddingProvider()
    raise EmbeddingProviderError(f"Unsupported embedding provider: {provider}")
