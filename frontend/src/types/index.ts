export type VideoStatus =
  | 'queued'
  | 'probing'
  | 'extracting_frames'
  | 'embedding_frames'
  | 'persisting_index'
  | 'ready'
  | 'failed';

export interface Video {
  id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  duration_seconds: number | null;
  width: number | null;
  height: number | null;
  fps: number | null;
  has_audio: boolean;
  status: VideoStatus;
  current_stage: string | null;
  progress: number;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface VideoListResponse {
  videos: Video[];
  total: number;
  cursor: string | null;
  has_more: boolean;
}

export interface UploadResponse {
  video_id: string;
  status: VideoStatus;
  status_url: string;
}

export type SearchMode = 'frame_semantic_v1' | 'video_window_v1' | 'hybrid_v1';

export interface SearchResult {
  video_id: string;
  filename: string;
  start_seconds: number;
  end_seconds: number;
  evidence_timestamp_seconds: number;
  frame_id: string | null;
  thumbnail_url: string;
  score: number;
  score_type: string;
  search_mode: string;
  applied_constraints: string[];
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total_results: number;
  execution_time_ms: number;
  search_mode: string;
}

export interface ApiErrorDetail {
  code: string;
  message: string;
  request_id?: string;
}

export interface ApiErrorResponse {
  error: ApiErrorDetail;
}
