import os
import shutil
import tempfile
from pathlib import Path
from typing import BinaryIO

from app.core.errors import ValidationException
from app.storage.base import StorageService


class LocalStorageService(StorageService):
    """
    Local filesystem storage provider with path traversal defenses,
    atomic writes via tempfile + replace, and strict key isolation.
    """

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_and_resolve_key(self, storage_key: str) -> Path:
        """
        Validate storage key to ensure it does not escape base directory.
        Rejects directory traversal sequences and absolute paths.
        """
        if not storage_key or ".." in storage_key or storage_key.startswith(("/", "\\")):
            raise ValidationException("STORAGE_INVALID_KEY", "Invalid storage key format")

        target_path = (self.base_dir / storage_key).resolve()

        # Path traversal guard: must be subpath of base_dir
        try:
            target_path.relative_to(self.base_dir)
        except ValueError:
            raise ValidationException("STORAGE_PATH_ESCAPE", "Storage path escape detected")

        return target_path

    def save_file(self, stream: BinaryIO, storage_key: str) -> Path:
        dest_path = self._sanitize_and_resolve_key(storage_key)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write: write to temp file on the same filesystem, then replace
        temp_fd, temp_path_str = tempfile.mkstemp(dir=dest_path.parent, prefix="upload_tmp_")
        temp_path = Path(temp_path_str)

        try:
            with os.fdopen(temp_fd, "wb") as temp_file:
                shutil.copyfileobj(stream, temp_file)
            temp_path.replace(dest_path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

        return dest_path

    def get_path(self, storage_key: str) -> Path:
        dest_path = self._sanitize_and_resolve_key(storage_key)
        if not dest_path.exists():
            raise ValidationException("STORAGE_FILE_NOT_FOUND", "Media file not found in storage")
        return dest_path

    def delete_file(self, storage_key: str) -> bool:
        dest_path = self._sanitize_and_resolve_key(storage_key)
        if dest_path.exists():
            dest_path.unlink()
            return True
        return False

    def exists(self, storage_key: str) -> bool:
        try:
            dest_path = self._sanitize_and_resolve_key(storage_key)
            return dest_path.exists()
        except ValidationException:
            return False
