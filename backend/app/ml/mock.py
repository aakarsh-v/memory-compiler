import hashlib
import math
import struct
from pathlib import Path
from typing import List, Union

from app.ml.base import EmbeddingProvider


class MockEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic mock embedding provider for testing and CPU CI.
    Generates unit-normalized float vectors using seeded pseudo-random streams derived from SHA-256.
    Produces identical vectors for identical inputs, with no GPU and zero external downloads.
    """

    def __init__(self, model_id: str = "mock-clip-vit-b32", dimension: int = 512):
        self._model_id = model_id
        self._dimension = dimension

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def dimension(self) -> int:
        return self._dimension

    def _generate_vector(self, seed_bytes: bytes) -> List[float]:
        # Derive pseudo-random numbers deterministically from seed using incremental hash rounds
        raw_values: List[float] = []
        counter = 0
        while len(raw_values) < self._dimension:
            round_bytes = seed_bytes + counter.to_bytes(4, byteorder="big")
            digest = hashlib.sha256(round_bytes).digest()
            # Unpack into 8 float32s
            for i in range(0, 32, 4):
                if len(raw_values) < self._dimension:
                    # Normalize unpacked int to [-1.0, 1.0]
                    (val,) = struct.unpack(">i", digest[i : i + 4])
                    raw_values.append(val / 2147483648.0)
            counter += 1

        # L2 normalize
        norm = math.sqrt(sum(x * x for x in raw_values))
        if norm == 0:
            norm = 1.0
        return [x / norm for x in raw_values]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        results: List[List[float]] = []
        for text in texts:
            seed = f"text:{text.strip().lower()}".encode("utf-8")
            results.append(self._generate_vector(seed))
        return results

    def embed_frames(self, frame_sources: List[Union[str, Path, bytes]]) -> List[List[float]]:
        results: List[List[float]] = []
        for source in frame_sources:
            if isinstance(source, bytes):
                seed = b"frame_bytes:" + hashlib.sha256(source).digest()
            elif isinstance(source, (str, Path)):
                path = Path(source)
                if path.exists() and path.is_file():
                    with open(path, "rb") as f:
                        file_bytes = f.read(65536)  # Read initial header/content for hashing
                    seed = b"frame_file:" + hashlib.sha256(file_bytes).digest()
                else:
                    seed = f"frame_path:{str(path)}".encode("utf-8")
            else:
                seed = str(source).encode("utf-8")
            results.append(self._generate_vector(seed))
        return results
