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
