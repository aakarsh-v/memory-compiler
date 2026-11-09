from app.core.config import settings
from app.ml.base import EmbeddingProvider
from app.ml.mock import MockEmbeddingProvider


def get_embedding_provider() -> EmbeddingProvider:
    """Factory to retrieve configured embedding provider."""
    provider = settings.EMBEDDING_PROVIDER.lower()
    if provider == "mock":
        return MockEmbeddingProvider(
            model_id=settings.EMBEDDING_MODEL_ID,
            dimension=settings.VECTOR_DIMENSION
        )
    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: '{provider}'. Only 'mock' is currently supported without GPU/heavy weights.")

