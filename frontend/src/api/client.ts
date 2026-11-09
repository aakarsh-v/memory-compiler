import {
  Video,
  VideoListResponse,
  UploadResponse,
  SearchResponse,
  SearchMode,
  ApiErrorResponse,
} from '../types';

const API_BASE = '/api/v1';

export class ApiClient {
  private ownerId: string;

  constructor(ownerId: string = 'default_user') {
    this.ownerId = ownerId;
  }

  setOwnerId(ownerId: string) {
    this.ownerId = ownerId;
  }

  getOwnerId(): string {
    return this.ownerId;
  }

  private getHeaders(extraHeaders: Record<string, string> = {}): HeadersInit {
    return {
      'X-User-ID': this.ownerId,
      'X-Owner-ID': this.ownerId,
      ...extraHeaders,
    };
  }

  private async handleResponse<T>(res: Response): Promise<T> {
    if (!res.ok) {
      let errorMsg = `HTTP ${res.status} ${res.statusText}`;
      try {
        const errorJson: ApiErrorResponse = await res.json();
        if (errorJson?.error?.message) {
          errorMsg = errorJson.error.message;
        }
      } catch {
        // Fall back to HTTP status
      }
      throw new Error(errorMsg);
    }
    return res.json() as Promise<T>;
  }

  async listVideos(cursor?: string, limit: number = 50): Promise<VideoListResponse> {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (cursor) params.set('cursor', cursor);

    const res = await fetch(`${API_BASE}/videos?${params.toString()}`, {
      headers: this.getHeaders(),
    });
    const data = await this.handleResponse<{ items: Video[]; cursor: string | null }>(res);
    return {
      items: data.items,
      videos: data.items,
      cursor: data.cursor,
      total: data.items?.length || 0,
    };
  }

  async getVideo(videoId: string): Promise<Video> {
    const res = await fetch(`${API_BASE}/videos/${encodeURIComponent(videoId)}`, {
      headers: this.getHeaders(),
    });
    return this.handleResponse<Video>(res);
  }

  async getVideoStatus(videoId: string): Promise<Video> {
    const res = await fetch(`${API_BASE}/videos/${encodeURIComponent(videoId)}/status`, {
      headers: this.getHeaders(),
    });
    const data = await this.handleResponse<any>(res);
    return {
      ...data,
      id: data.id || data.video_id || videoId,
      status: (data.status || 'queued').toLowerCase(),
    };
  }

  async uploadVideo(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${API_BASE}/videos`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: formData,
    });
    return this.handleResponse<UploadResponse>(res);
  }

  async deleteVideo(videoId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/videos/${encodeURIComponent(videoId)}`, {
      method: 'DELETE',
      headers: this.getHeaders(),
    });
    if (!res.ok && res.status !== 204) {
      let errorMsg = `Failed to delete video (${res.status})`;
      try {
        const errorJson: ApiErrorResponse = await res.json();
        if (errorJson?.error?.message) errorMsg = errorJson.error.message;
      } catch {
        // Fall back
      }
      throw new Error(errorMsg);
    }
  }

  async search(
    query: string,
    mode: SearchMode = 'frame_semantic_v1',
    limit: number = 20,
    minSimilarity: number = 0.05
  ): Promise<SearchResponse> {
    const res = await fetch(`${API_BASE}/search`, {
      method: 'POST',
      headers: this.getHeaders({
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify({
        query,
        search_mode: mode,
        limit,
        threshold: minSimilarity,
        min_similarity: minSimilarity,
      }),
    });
    return this.handleResponse<SearchResponse>(res);
  }

  getStreamUrl(videoId: string): string {
    return `${API_BASE}/videos/${encodeURIComponent(videoId)}/stream`;
  }

  getThumbnailUrl(frameId: string): string {
    return `${API_BASE}/frames/${encodeURIComponent(frameId)}/thumbnail`;
  }
}

export const api = new ApiClient();

