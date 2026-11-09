from abc import ABC, abstractmethod
from typing import List, Union
from pathlib import Path


class EmbeddingProvider(ABC):
    """Abstract interface for image-text multimodal embedding models."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Identifier/revision of the model."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimensionality of output vectors."""
        pass

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of text strings into normalized vectors."""
        pass

    @abstractmethod
    def embed_frames(self, frame_sources: List[Union[str, Path, bytes]]) -> List[List[float]]:
        """Embed a batch of frame image paths or raw bytes into normalized vectors."""
        pass

