# Memory Compiler

Memory Compiler is a private video archive with natural-language retrieval. Users upload long-form videos and search for moments using natural-language queries (e.g., *"person in a red jacket walking into the room"*). The system localizes candidate timestamps, provides preview evidence, and supports instant playback at the matching scene.

## Current Status

- **Phase 0 (Repository Assessment & Scaffolding):** Complete
- **Phase 1 (Upload, Private Storage & Processing State):** Complete
- **Phase 2 (Frames and Metadata Extraction Pipeline):** Complete
- **Phase 3 (Multimodal Frame Embedding Search & Playback):** Complete
- **Phase 4 (Labeled Evaluation Benchmark & Retrieval Metrics):** Complete

## Technology Stack

- **Backend:** FastAPI, Pydantic v2, SQLAlchemy 2, Alembic
- **Database:** PostgreSQL 16 + pgvector (SQLite compatible for in-memory unit tests)
- **Worker / Tasks:** Celery + Redis
- **Media Ingestion:** Local private storage with path-traversal guards and atomic writes; FFmpeg / FFprobe
- **Multimodal AI:** Deterministic `MockEmbeddingProvider` (unit normalized vectors, zero weight downloads in CI)
- **Containerization:** Docker Compose

## Repository Layout

```
memory-compiler/
├── docker-compose.yml          # Container services: Postgres (pgvector), Redis, API, Worker
├── .env.example                # Documented configuration template
├── README.md                   # Setup, architecture, runnable commands
├── docs/                       # Technical specs, API contracts, architecture
│   ├── api.md
│   ├── architecture.md
│   └── evaluation.md
├── backend/
│   ├── pyproject.toml          # Python project metadata & pytest configuration
│   ├── Dockerfile              # Backend and worker container build
│   ├── alembic.ini             # Database migration configuration
│   ├── alembic/                # Versioned database migrations
│   ├── app/
│   │   ├── main.py             # FastAPI entrypoint, middlewares, error handlers
│   │   ├── core/               # Configuration, structured logging, errors, auth
│   │   ├── db/                 # Models (Video, ProcessingJob, Frame), session
│   │   ├── ml/                 # Embedding provider interface and mock adapter
│   │   ├── storage/            # Local private storage service with atomic writes
│   │   ├── services/           # Job service and upload validation
│   │   ├── schemas/            # Pydantic v2 API contracts
│   │   └── api/v1/             # Endpoints: /videos, /health
│   └── tests/
│       ├── unit/               # Storage, validation, config, mock embedding, health
│       └── integration/        # Video upload, status polling, ownership isolation
└── frontend/                   # React + Vite application (Phase 3+)
```

## Quick Start (Local Development)

### 1. Prerequisites
- Python 3.11+
- FFmpeg and FFprobe installed and available on PATH
- Docker & Docker Compose (optional, for running Postgres and Redis)

### 2. Configure Environment
```bash
cp .env.example .env
```

### 3. Install Backend Dependencies
```bash
cd backend
pip install -e .
pip install pytest pytest-asyncio pytest-mock
```

### 4. Run Tests
Execute the full test suite without requiring GPU or external services:
```bash
cd backend
python -m pytest tests/ -v
```

### 5. Start Backend API
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```
- Interactive Swagger UI: `http://localhost:8000/docs`
- Health Liveness: `http://localhost:8000/health/live`
- Health Readiness: `http://localhost:8000/health/ready`

### 6. Start Services with Docker Compose
```bash
docker compose up -d
```

## API Endpoints (Phase 1)

| Method | Route | Description | Response Code |
|---|---|---|---|
| `GET` | `/health/live` | Process liveness probe | `200 OK` |
| `GET` | `/health/ready` | Dependency and storage readiness | `200 OK` / `503` |
| `POST` | `/api/v1/videos` | Multipart upload (returns video ID & status immediately) | `202 Accepted` |
| `GET` | `/api/v1/videos` | List owned videos (paginated via cursor) | `200 OK` |
| `GET` | `/api/v1/videos/{id}` | Video metadata and state | `200 OK` |
| `GET` | `/api/v1/videos/{id}/status` | Stage, progress, and safe error summary | `200 OK` |
| `POST` | `/api/v1/search` | Natural-language top-K semantic search | `200 OK` |
| `GET` | `/api/v1/videos/{id}/stream` | Range-seeking private video streaming | `200 OK` / `206 Partial Content` |
| `GET` | `/api/v1/frames/{id}/thumbnail` | Frame thumbnail preview image | `200 OK` (`image/jpeg`) |
