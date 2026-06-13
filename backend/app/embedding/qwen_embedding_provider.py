from __future__ import annotations

from typing import Any

import httpx
import numpy as np

from app import settings
from app.embedding.embedding_provider import EmbeddingProviderError, l2_normalize


def _embedding_url(base_url: str) -> str:
    clean_url = base_url.rstrip("/")
    if clean_url.endswith("/embeddings"):
        return clean_url
    return f"{clean_url}/embeddings"


class QwenEmbeddingProvider:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = settings.QWEN_EMBEDDING_API_KEY if api_key is None else api_key
        self.base_url = settings.QWEN_EMBEDDING_BASE_URL if base_url is None else base_url
        self.model = settings.QWEN_EMBEDDING_MODEL if model is None else model

    def _validate_configuration(self) -> None:
        if not self.api_key:
            raise EmbeddingProviderError("Qwen embedding API key is missing. Set QWEN_EMBEDDING_API_KEY.")
        if not self.base_url:
            raise EmbeddingProviderError("Qwen embedding base URL is missing. Set QWEN_EMBEDDING_BASE_URL.")
        if not self.model:
            raise EmbeddingProviderError("Qwen embedding model is missing. Set QWEN_EMBEDDING_MODEL.")

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        self._validate_configuration()
        vectors: list[list[float]] = []
        for start in range(0, len(texts), settings.EMBEDDING_BATCH_SIZE):
            batch = texts[start : start + settings.EMBEDDING_BATCH_SIZE]
            vectors.extend(self._embed_batch(batch))
        return l2_normalize(np.asarray(vectors, dtype=np.float32))

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        payload: dict[str, Any] = {
            "model": self.model,
            "input": texts,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = httpx.post(
                _embedding_url(self.base_url),
                json=payload,
                headers=headers,
                timeout=settings.QWEN_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise EmbeddingProviderError("Qwen embedding request timed out.") from exc
        except httpx.HTTPStatusError as exc:
            raise EmbeddingProviderError(
                f"Qwen embedding request failed with HTTP {exc.response.status_code}."
            ) from exc
        except httpx.RequestError as exc:
            raise EmbeddingProviderError("Qwen embedding request failed before a response was received.") from exc

        try:
            data = response.json()
            sorted_items = sorted(data["data"], key=lambda item: int(item.get("index", 0)))
            return [item["embedding"] for item in sorted_items]
        except (KeyError, TypeError, ValueError) as exc:
            raise EmbeddingProviderError("Qwen embedding response did not contain embeddings.") from exc
