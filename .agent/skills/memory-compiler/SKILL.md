---
name: memory-compiler
description: Build and extend the Memory Compiler project, a private video archive with natural-language search (upload, frame indexing, pgvector semantic search, timestamp playback). Use for any task in this repo involving the FastAPI backend, Celery worker, FFmpeg pipeline, embedding adapters, search, React UI, tests, or evaluation.
---

# Memory Compiler: Build Skill

Goal of the first release: **upload video -> timestamped frames -> image-text embeddings -> natural-language search -> candidate timestamp -> play original video at that time.** Nothing else ships before this works end to end and has tests.

## 0. Operating rules (always)

1. Inspect the repo first (stack, scripts, tests, what already works). Summarize before editing. Preserve working code; adapt, don't replace.
2. Work one phase at a time, in order. Prefer a complete earlier phase over a half-built later one.
3. Write or update tests with every feature. Run them after each edit, not just at the end.
4. Never fake outputs: no hard-coded scores, fabricated model results, or success responses that skip real processing. If a model is unavailable, add an adapter boundary and a clear "feature disabled" message.
5. Never silently swallow exceptions. Raise typed, safe errors; log detail server-side.
6. Pick a reasonable documented default instead of asking about non-essential details.
7. Update `.env.example`, README, and migrations whenever config or schema changes.
8. Do not claim a feature works unless it runs end to end.

## 1. Scope

**MVP (must):** single-user dev mode with `owner_id` everywhere; upload + validation + async status; FFmpeg frame extraction with timestamps; pretrained image-text embeddings; PostgreSQL + pgvector; text-query top-K search; React UI (library, status, results, playback); unit + integration tests with a deterministic mock model.

**Later (do not block MVP):** video-window embeddings, audio transcription, object detection/tracking, captions/event graph, temporal query parsing, fine-tuning, multi-user prod, cloud storage.

**Non-goals:** training a foundation model, face/identity recognition, cross-video identity, emotion/intent inference, legal/disciplinary decisions, video editing, general chatbot, user sharing, graph DB.

## 2. Stack defaults

- Backend: Python, FastAPI, Pydantic, SQLAlchemy/Alembic migrations
- Worker: Celery + Redis (never run heavy inference in request handlers or FastAPI BackgroundTasks)
- Media: FFmpeg/FFprobe via safe argument lists (no shell strings); PySceneDetect optional
- ML: PyTorch + OpenCLIP or HF Transformers behind an adapter interface
- DB: PostgreSQL + pgvector (exact search first; add ANN only after measuring recall/latency)
- Frontend: React + Vite + TypeScript
- Dev infra: Docker Compose (Postgres, Redis, worker, API)
- Tests: pytest; frontend test runner already in repo or Vitest

## 3. Architecture rules

- Model, storage, detector, and transcriber code lives behind interfaces in `ml/` and `storage/`. Route handlers never import model libraries.
- Store on every vector row: model ID/revision, embedding dimension, preprocessing version, indexing config. Never compare or mix vectors from different models; filter by model.
- Timestamps are float seconds on the original media timeline. Never derive them from frame number alone.
- Never silently fall back to random vectors or a different model. If the configured model fails to load, fail with an actionable message.
- Batch embeddings. Don't call an LLM per frame.
- No long inference inside an open DB transaction.
- Opaque generated storage keys; never build paths from filenames; block path traversal and symlink escapes.

## 4. Repository layout

```
memory-compiler/
  .env.example  docker-compose.yml  README.md
  docs/ (architecture.md, api.md, evaluation.md)
  backend/
    pyproject.toml
    app/ main.py core/ api/v1/ schemas/ db/ services/ workers/ pipeline/ ml/ storage/
    tests/ unit/ integration/ fixtures/
  frontend/ src/ api/ components/ pages/ hooks/ types/
  scripts/ seed_demo_data.py evaluate_retrieval.py
```

## 5. Data model (use migrations, UUID public IDs, created_at/updated_at)

- `videos`: id, owner_id, filename, storage_key, mime_type, size_bytes, duration_seconds, width, height, fps, has_audio, status, current_stage, progress, error_code, error_message
- `processing_jobs`: id, video_id, status, attempt, stage, progress, config_json, started_at, finished_at, error_summary
- `frames`: id, video_id, scene_id?, timestamp_seconds, image_key, width, height, embedding vector(N), embedding_model, preprocessing_version
- Unique constraint on `(video_id, timestamp_seconds, preprocessing_version)` for retry-safe upserts
- Indexes on video_id, owner_id, status, timestamps
- Phase 5+: `video_windows`. Phase 6+: `scenes`, `events`, `tracks`, `event_participants`, `search_feedback`
- FKs cascade or explicit cleanup so deleting a video leaves no orphan rows or files
- Enforce ownership in query filters, not just in the UI

## 6. Processing pipeline

State machine: `UPLOADED -> QUEUED -> PROBING -> EXTRACTING_FRAMES -> EMBEDDING_FRAMES -> PERSISTING_INDEX -> READY`. Any state may go to `FAILED` with a safe error code. Retry goes `FAILED -> QUEUED` and rebuilds idempotently.

1. Validate extension, size limit, FFprobe-verified streams (not client MIME alone)
2. Atomically write original to private storage; create video + job rows; return 202 promptly
3. FFprobe: duration, dimensions, fps, codec, audio presence; reject malformed media safely
4. Optional scene detection (metadata only)
5. Extract frames at `FRAME_SAMPLE_SECONDS` (default 2.0, single source of truth, never hard-coded elsewhere)
6. Resize/normalize per encoder; thumbnails generated separately
7. Batched embeddings; validate dimension, finiteness, normalization
8. Persist in batches; update progress at honest checkpoints only
9. Mark READY only when everything is persisted and searchable
10. On failure keep diagnostic metadata; never leave a READY video with a partial index

Also: bounded batches (RAM/GPU), timeouts and return-code checks on every FFmpeg call, structured logs with job_id/video_id/stage/elapsed_ms/error_code, never log media content.

## 7. Search (MVP = `frame_semantic_v1`)

1. Validate query length and scope to owned, READY videos
2. Encode query with the matching text encoder
3. pgvector cosine top-K filtered by model/preprocessing version
4. Merge near-duplicate frames per video into time windows, keep best frame as evidence
5. Optionally diversify so one scene doesn't fill top-K
6. Return video_id, filename, start/end seconds, evidence timestamp, thumbnail URL, score, `score_type: "cosine_similarity"`, `search_mode`, applied_constraints (empty in MVP)

Rules: similarity is not a probability or confidence percentage. Support empty results via a configurable threshold, and distinguish "no match" from "indexing failed" from "constraint unsupported". Use cautious wording ("possible match"). Frame search finds objects and scenes; it cannot prove actions, so label it honestly.

Post-MVP temporal: constrained parser returning a validated schema (events, entities, temporal_constraints before/after/during/first/last/near/same-person). On parse failure fall back to plain semantic search and flag that constraints were not applied. Never execute LLM-generated SQL. Keep score components separately observable.

## 8. API (`/api/v1`, Pydantic models, consistent errors)

| Method | Route | Success |
|---|---|---|
| POST | /videos | 202 `{video_id, status, status_url}` |
| GET | /videos | 200, owner-only, cursor/limit |
| GET | /videos/{id} | 200 |
| GET | /videos/{id}/status | 200 stage/progress/safe error |
| POST | /search | 200 ranked results |
| GET | /videos/{id}/stream | 200/206 with HTTP Range, owner-only |
| DELETE | /videos/{id} | 204, removes rows, thumbnails, file |
| GET | /health/live, /health/ready | liveness vs dependency readiness (503) |

Error shape: `{"error": {"code", "message", "request_id"}}`. Never expose stack traces, paths, credentials, or other users' metadata. Add OpenAPI examples and response-validation tests.

## 9. Frontend

Screens: library (empty/loading/failed/pagination), upload (oversize/unsupported/network/duplicate), processing detail (stage-based progress), search (empty query/no matches/API error), results + player, delete confirmation.
Rules: show results only for indexed, accessible videos; API uses seconds, UI formats HH:MM:SS; seek the original video to `start_seconds` (no clip generation); show uncertainty; keyboard accessible with labels and clear loading/empty/error states.

## 10. Configuration (all via env, none hard-coded)

APP_ENV, DATABASE_URL, REDIS_URL, MEDIA_ROOT, MAX_UPLOAD_MB, ALLOWED_VIDEO_EXTENSIONS, FRAME_SAMPLE_SECONDS, EMBEDDING_PROVIDER (`mock` in tests), EMBEDDING_MODEL_ID, EMBEDDING_DEVICE, EMBEDDING_BATCH_SIZE, VECTOR_DIMENSION, LOG_LEVEL, CORS_ORIGINS (explicit allowlist). Document model download size and license before pulling weights. CI must run with no GPU and no weight downloads.

## 11. Phases and exit gates

| Phase | Work | Exit gate |
|---|---|---|
| 0 | Repo assessment, scaffolding, plan, lint/test commands, .env.example, compose | Skeleton starts; smoke test passes; no secrets |
| 1 | Upload, private storage, job abstraction, status endpoint | Upload returns ID fast; status transitions; validation + ownership tests pass |
| 2 | FFprobe, frame extraction, optional scenes, deterministic names | Fixture video: monotonic timestamps; reruns create no duplicates |
| 3 | Model adapter, pgvector, query embedding, top-K, merge, playback | Known query hits expected frame in top-K; UI seeks correctly; CI uses mock |
| 4 | Labeled benchmark + eval script | Reports Recall@K, tIoU, latency, indexing time with config metadata |
| 5 | Video-window encoder, overlapping windows | Frame vs window compared on same benchmark; no blanket claims |
| 6 | Captions/events with provenance, constrained query schema | Tests for order reversal, false matches, missing events, unsupported constraints |
| 7 | Deletion, Range streaming, security, logging, deploy docs | Fresh-checkout README works; no cross-user access; deletion cleans derived assets |

**Start with Phases 0-1 only, then continue in order.** Do not start tracking, event reasoning, or fine-tuning until Phase 3 is tested end to end. Fine-tuning requires: working baseline, labeled benchmark, documented hard negatives, fixed train/val/test splits, reproducible evaluation.

## 12. Testing checklist

- Unit: timestamp conversion, filename sanitization, schema validation, constraint evaluator, score normalization
- Adapter: mock encoder dimension; storage refuses traversal; model-load errors are actionable
- Integration: upload -> queue -> ready; failed -> retry (no duplicate rows); delete cleans rows and files
- E2E smoke: upload fixture -> ready -> search -> click result -> correct playback time
- Security: user A cannot list/search/stream/delete user B's media; unsupported media rejected; oversized query bounded
- Regression: fixed benchmark compared with the last saved run
- Benchmark: ~5 short dev videos, ~20 queries to start; query types: object/scene, attribute, single action, interaction, ordered actions, first/last, audio-visual (only if audio indexed), hard negatives and no-match. Keep dev and test clips separate.

## 13. Security and privacy

Treat videos, frames, thumbnails, embeddings, captions as private. Authorize at every read/search/stream/delete. Don't expose media directories or storage URLs. Don't send videos to third-party APIs without explicit config and consent. Add rate limits and quotas for shared deployments. Support full deletion and document any backup exceptions.

## 14. Status report after every phase

```
Phase: <ID and name>
Implemented: <observable changes>
Files changed: <key files>
Commands run: <tests / lint / build / smoke>
Results: <pass/fail + relevant output>
Acceptance criteria: [x] met / [ ] not met (reason)
Known limitations / next risks: <notes>
Next phase proposal: <one focused increment>
```

Map work to requirement IDs (FR-01..08, NFR-01..05, ML-01..03) in plans, commits, and reports.

## 15. Kickoff prompt

> Inspect the repo and report its structure, stack, runnable commands, tests, and working functionality. Don't overwrite working code. Propose a short plan mapped to requirement IDs and phases. Implement Phase 0 and Phase 1 only unless already complete. Provide a deterministic mock embedding provider; no large weight downloads in CI. Add migrations, config, tests, README updates. Run tests and report exact commands and results. After each phase, give the status report and wait for the next instruction.