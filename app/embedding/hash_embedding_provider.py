from __future__ import annotations

import hashlib

import numpy as np

from app import settings
from app.embedding.embedding_provider import l2_normalize


class HashEmbeddingProvider:
    def __init__(self, dimension: int | None = None) -> None:
        self.dimension = dimension or settings.EMBEDDING_DIM or 384

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.dimension), dtype=np.float32)
        for row_index, text in enumerate(texts):
            clean_text = text or ""
            tokens = [char for char in clean_text if not char.isspace()]
            if not tokens:
                tokens = ["<empty>"]
            for token in tokens:
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                bucket = int.from_bytes(digest[:4], "little") % self.dimension
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vectors[row_index, bucket] += sign
            full_digest = hashlib.sha256(clean_text.encode("utf-8")).digest()
            for offset, byte_value in enumerate(full_digest[:32]):
                bucket = (byte_value + offset * 131) % self.dimension
                vectors[row_index, bucket] += 0.05
        return l2_normalize(vectors)
