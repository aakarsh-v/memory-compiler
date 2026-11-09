import uuid
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.core.errors import AppException, app_exception_handler, generic_exception_handler
from app.api.v1.health import router as health_router
from app.api.v1.videos import router as videos_router
from app.api.v1.search import router as search_router
from app.api.v1.frames import router as frames_router

setup_logging(settings.LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from app.db.session import init_db
        init_db()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.warning(f"Database initialization warning: {e}")
    yield


app = FastAPI(
    title="Memory Compiler API",
    description="Multimodal deep-learning system for natural-language search across video archives",
    version="0.1.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        start_time = time.time()

        response = await call_next(request)

        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code} ({elapsed_ms}ms)",
            extra={"request_id": request_id, "elapsed_ms": elapsed_ms}
        )
        return response


app.add_middleware(RequestContextMiddleware)

# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Routers
app.include_router(health_router)
app.include_router(videos_router)
app.include_router(search_router)
app.include_router(frames_router)
