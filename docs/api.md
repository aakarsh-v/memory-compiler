# Memory Compiler API Contracts

Version: `/api/v1`

## Error Response Format

All error responses adhere to the standard JSON shape:

```json
{
  "error": {
    "code": "VIDEO_UNSUPPORTED_FORMAT",
    "message": "Video format '.exe' is not supported.",
    "request_id": "893c5fa1-ff07-4ba3-bf30-4e20790e9603"
  }
}
```

No stack traces, internal paths, or secrets are exposed in API responses.

## Endpoints

### 1. Liveness Probe
`GET /health/live`
- Response: `200 OK`
```json
{
  "status": "ok"
}
```

### 2. Readiness Probe
`GET /health/ready`
- Response: `200 OK` or `503 Service Unavailable`
```json
{
  "status": "ready",
  "checks": {
    "storage": true,
    "environment": "development",
    "embedding_provider": "mock"
  }
}
```

### 3. Upload Video
`POST /api/v1/videos`
- Content-Type: `multipart/form-data`
- Header: `X-User-ID: <owner_id>` (optional, defaults to `dev-user`)
- Response: `202 Accepted`
```json
{
  "video_id": "670fbc02-09c3-4d6f-871d-f8ec008c2b74",
  "status": "queued",
  "status_url": "/api/v1/videos/670fbc02-09c3-4d6f-871d-f8ec008c2b74/status"
}
```

### 4. Query Video Status
`GET /api/v1/videos/{video_id}/status`
- Header: `X-User-ID: <owner_id>`
- Response: `200 OK`
```json
{
  "video_id": "670fbc02-09c3-4d6f-871d-f8ec008c2b74",
  "status": "QUEUED",
  "current_stage": "QUEUED",
  "progress": 0.0,
  "error_code": null,
  "error_message": null,
  "created_at": "2026-11-09T10:15:00Z",
  "updated_at": "2026-11-09T10:15:00Z"
}
```

### 5. List Videos
`GET /api/v1/videos?cursor=<uuid>&limit=20`
- Header: `X-User-ID: <owner_id>`
- Response: `200 OK`
```json
{
  "items": [
    {
      "id": "670fbc02-09c3-4d6f-871d-f8ec008c2b74",
      "owner_id": "dev-user",
      "filename": "sample_clip.mp4",
      "mime_type": "video/mp4",
      "size_bytes": 10485760,
      "duration_seconds": null,
      "width": null,
      "height": null,
      "fps": null,
      "has_audio": null,
      "status": "QUEUED",
      "current_stage": "QUEUED",
      "progress": 0.0,
      "error_code": null,
      "error_message": null,
      "created_at": "2026-11-09T10:15:00Z",
      "updated_at": "2026-11-09T10:15:00Z"
    }
  ],
  "cursor": null
}
```

### 6. Video Metadata Detail
`GET /api/v1/videos/{video_id}`
- Header: `X-User-ID: <owner_id>`
- Response: `200 OK` (returns full metadata)

### 7. Delete Video & Derived Assets
`DELETE /api/v1/videos/{video_id}`
- Header: `X-User-ID: <owner_id>`
- Response: `204 No Content`
- Cascades deletion to processing jobs, extracted frames, temporal windows, and events.
- Safely purges original video and all frame JPEG thumbnails from private storage without leaving orphan records or files.

### 7. Natural-Language Semantic Search
`POST /api/v1/search`
- Header: `X-User-ID: <owner_id>`
- Content-Type: `application/json`
- Request:
```json
{
  "query": "person walking in hallway",
  "video_ids": null,
  "limit": 10,
  "threshold": 0.0,
  "include_evidence": true
}
```
- Response: `200 OK`
```json
{
  "query": "person walking in hallway",
  "search_mode": "frame_semantic_v1",
  "results": [
    {
      "video_id": "670fbc02-09c3-4d6f-871d-f8ec008c2b74",
      "filename": "sample_clip.mp4",
      "start_seconds": 1.0,
      "end_seconds": 3.0,
      "evidence_timestamp_seconds": 2.0,
      "thumbnail_url": "/api/v1/frames/8d05e263-d022-44df-9118-2e061ff635c0/thumbnail",
      "description": "Visually similar frame candidate",
      "score": 0.8245,
      "score_type": "cosine_similarity",
      "applied_constraints": [],
      "evidence": [
        {
          "frame_id": "8d05e263-d022-44df-9118-2e061ff635c0",
          "timestamp_seconds": 2.0
        }
      ]
    }
  ]
}
```

### 8. Video Stream & Range Seeking
`GET /api/v1/videos/{video_id}/stream`
- Header: `X-User-ID: <owner_id>`
- Header: `Range: bytes=0-1048576` (optional)
- Response: `206 Partial Content` (with `Content-Range`) or `200 OK`
- Supports video timeline seeking to `evidence_timestamp_seconds`.

### 9. Frame Thumbnail Preview
`GET /api/v1/frames/{frame_id}/thumbnail`
- Header: `X-User-ID: <owner_id>`
- Response: `200 OK` (`image/jpeg`)
