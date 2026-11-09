import os
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.core.logging import logger
from app.db.models import Base


def get_engine():
    db_url = settings.DATABASE_URL
    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    # Test connecting if postgresql in development
    if "postgresql" in db_url and settings.APP_ENV == "development":
        try:
            temp_eng = create_engine(
                db_url,
                connect_args=connect_args,
                pool_pre_ping=True,
                pool_timeout=2
            )
            with temp_eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            return temp_eng
        except Exception as e:
            project_root = Path(__file__).resolve().parents[3]
            sqlite_dir = project_root / "data"
            sqlite_dir.mkdir(parents=True, exist_ok=True)
            sqlite_path = (sqlite_dir / "memory_compiler_dev.db").resolve()
            sqlite_url = f"sqlite:///{sqlite_path}"
            logger.warning(
                f"PostgreSQL connection to {db_url} failed ({e}). "
                f"Falling back to SQLite for local development: {sqlite_url}"
            )
            return create_engine(
                sqlite_url,
                connect_args={"check_same_thread": False},
                pool_pre_ping=True
            )

    return create_engine(
        db_url,
        connect_args=connect_args,
        pool_pre_ping=True
    )


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
