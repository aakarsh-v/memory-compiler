# Memory Compiler Architecture

## Overview

Memory Compiler implements an asynchronous, staged ingestion and retrieval pipeline designed for natural-language search over long-form video archives.

```mermaid
flowchart TD
    Client["Client / React UI"] -->|POST /api/v1/videos| API["FastAPI Application"]
    API -->|Atomic Write| Storage["Private Local Media Storage"]
    API -->|Create Row + Job| DB[("PostgreSQL + pgvector")]
    API -.->|202 Accepted| Client
    API -->|Enqueue| Queue["Redis Queue"]
    Queue --> Worker["Celery Worker"]
    Worker -->|FFprobe / FFmpeg| Storage
    Worker -->|Inference (Batch)| ML["Embedding Adapter (Mock/CLIP)"]
    Worker -->|Vectors & Frames| DB
```

## Key Architectural Principles

1. **Decoupled Heavy Inference:** No long-running model inference or frame extraction occurs inside request handlers or within open database transactions.
2. **Deterministic & Isolated Storage:** Opaque generated storage keys (e.g., `{owner_id}/{video_id}.mp4`) prevent path traversal, filename collisions, and unauthorized access.
3. **Pluggable Embedding Adapters:** All embedding models live behind `EmbeddingProvider`. A deterministic, unit-normalized `MockEmbeddingProvider` ensures complete testability without GPU or downloading large model weights.
4. **Ownership-Aware Invariants:** Media assets and database records enforce explicit `owner_id` constraints in database query filters.
