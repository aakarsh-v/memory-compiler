from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    APP_ENV: str = "development"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/memory_compiler"
    REDIS_URL: str = "redis://localhost:6379/0"
    ENABLE_ASYNC_WORKER: bool = False
    MEDIA_ROOT: Path = Path("data/media")
    MAX_UPLOAD_MB: int = 500
    ALLOWED_VIDEO_EXTENSIONS: List[str] = [".mp4", ".mov", ".mkv", ".webm", ".avi"]
    FRAME_SAMPLE_SECONDS: float = 2.0
    EMBEDDING_PROVIDER: str = "mock"
    EMBEDDING_MODEL_ID: str = "mock-clip-vit-b32"
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_BATCH_SIZE: int = 16
    VECTOR_DIMENSION: int = 512
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    model_config = SettingsConfigDict(
        env_file=(str(PROJECT_ROOT / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("MEDIA_ROOT", mode="after")
    @classmethod
    def resolve_media_root(cls, v: Path) -> Path:
        if not v.is_absolute():
            return (PROJECT_ROOT / v).resolve()
        return v

    @field_validator("ALLOWED_VIDEO_EXTENSIONS", mode="before")
    @classmethod
    def parse_allowed_extensions(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            # Parse comma-separated or json string
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                import json
                return [ext.strip().lower() for ext in json.loads(v)]
            return [ext.strip().lower() for ext in v.split(",") if ext.strip()]
        return [ext.lower() for ext in v]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                import json
                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024


settings = Settings()

