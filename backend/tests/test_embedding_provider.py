from app import settings
from app.embedding.embedding_provider import (
    clear_embedding_provider_cache,
    get_embedding_provider,
)


def test_local_embedding_provider_is_cached_by_model(monkeypatch):
    created_models: list[str] = []

    class FakeLocalEmbeddingProvider:
        def __init__(self, model_name: str) -> None:
            created_models.append(model_name)
            self.model_name = model_name

    monkeypatch.setattr(
        "app.embedding.local_embedding_provider.LocalEmbeddingProvider",
        FakeLocalEmbeddingProvider,
    )
    clear_embedding_provider_cache()
    monkeypatch.setattr(settings, "EMBEDDING_MODEL", "model-a")

    first = get_embedding_provider("local")
    second = get_embedding_provider("local")
    monkeypatch.setattr(settings, "EMBEDDING_MODEL", "model-b")
    third = get_embedding_provider("local")

    assert first is second
    assert third is not first
    assert created_models == ["model-a", "model-b"]
    clear_embedding_provider_cache()
