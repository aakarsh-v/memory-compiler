import math
from app.ml.mock import MockEmbeddingProvider


def test_mock_embedding_determinism():
    provider = MockEmbeddingProvider(dimension=512)
    vec1 = provider.embed_texts(["person walking down the hallway"])[0]
    vec2 = provider.embed_texts(["person walking down the hallway"])[0]
    vec3 = provider.embed_texts(["completely different query"])[0]

    assert len(vec1) == 512
    # Identical input produces identical vector
    assert vec1 == vec2
    # Different input produces different vector
    assert vec1 != vec3


def test_mock_embedding_normalization():
    provider = MockEmbeddingProvider(dimension=256)
    vec = provider.embed_texts(["blue car on highway"])[0]
    assert len(vec) == 256

    # Unit norm: ||v|| ~ 1.0
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-5


def test_mock_frame_embedding():
    provider = MockEmbeddingProvider(dimension=128)
    frame_vec = provider.embed_frames([b"dummy frame jpeg bytes 12345"])[0]
    assert len(frame_vec) == 128
    norm = math.sqrt(sum(x * x for x in frame_vec))
    assert abs(norm - 1.0) < 1e-5

