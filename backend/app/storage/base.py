from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Optional


class StorageService(ABC):
    """Abstract interface for private media storage."""

    @abstractmethod
    def save_file(self, stream: BinaryIO, storage_key: str) -> Path:
        """Atomically persist a binary stream to storage under an opaque key."""
        pass

    @abstractmethod
    def get_path(self, storage_key: str) -> Path:
        """Resolve an opaque key to a verified local path."""
        pass

    @abstractmethod
    def delete_file(self, storage_key: str) -> bool:
        """Delete file associated with storage key."""
        pass

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Check if storage key exists."""
        pass
