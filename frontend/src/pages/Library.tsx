import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Film, Trash2, Search, RefreshCw, AlertCircle, Volume2, VolumeX, Clock } from 'lucide-react';
import { Video } from '../types';
import { api } from '../api/client';
import { formatDuration, formatBytes, formatDate } from '../utils/formatters';
import { ConfirmModal } from '../components/ConfirmModal';

interface LibraryProps {
  onSelectVideoForSearch: (videoId: string, filename: string) => void;
  onSelectVideoForPlay: (videoId: string, filename: string) => void;
  onNavigateToUpload: () => void;
}

export const Library: React.FC<LibraryProps> = ({
  onSelectVideoForSearch,
  onSelectVideoForPlay,
  onNavigateToUpload,
}) => {
  const [videos, setVideos] = useState<Video[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [videoToDelete, setVideoToDelete] = useState<Video | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const pollTimerRef = useRef<number | null>(null);

  const fetchVideos = useCallback(async () => {
    try {
      setError(null);
      const res = await api.listVideos();
      setVideos(res.videos);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch videos');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchVideos();
  }, [fetchVideos]);

  // Auto-poll if any video is currently processing
  useEffect(() => {
    const hasActiveProcessing = videos.some(
      (v) => v.status !== 'ready' && v.status !== 'failed'
    );

    if (hasActiveProcessing) {
      pollTimerRef.current = window.setTimeout(() => {
        fetchVideos();
      }, 3000);
    }

    return () => {
      if (pollTimerRef.current) {
        window.clearTimeout(pollTimerRef.current);
      }
    };
  }, [videos, fetchVideos]);

  const handleDelete = async () => {
    if (!videoToDelete) return;
    setIsDeleting(true);
    try {
      await api.deleteVideo(videoToDelete.id);
      setVideos((prev) => prev.filter((v) => v.id !== videoToDelete.id));
      setVideoToDelete(null);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to delete video');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 700 }}>Video Archive</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            {videos.length} {videos.length === 1 ? 'video' : 'videos'} cataloged in private storage
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={fetchVideos}
            disabled={isLoading}
            title="Refresh library"
          >
            <RefreshCw size={15} className={isLoading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>

          <button
            type="button"
            className="btn btn-primary"
            onClick={onNavigateToUpload}
          >
            Upload New Video
          </button>
        </div>
      </div>

      {error && (
        <div
          style={{
            background: 'rgba(244, 63, 94, 0.1)',
            border: '1px solid rgba(244, 63, 94, 0.3)',
            borderRadius: '0.5rem',
            padding: '1rem',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            color: '#fb7185',
          }}
        >
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {isLoading && videos.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '4rem 1rem', color: 'var(--text-secondary)' }}>
          <p>Loading video library...</p>
        </div>
      ) : videos.length === 0 ? (
        <div
          className="card"
          style={{ textAlign: 'center', padding: '4rem 2rem', borderStyle: 'dashed' }}
        >
          <Film size={48} color="var(--text-muted)" style={{ margin: '0 auto 1rem' }} />
          <h3 style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>No videos in archive yet</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1.5rem', maxWidth: '450px', margin: '0 auto 1.5rem' }}>
            Upload videos to extract monotonic timestamped frames, compute multimodal embeddings, and search memories with natural language.
          </p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={onNavigateToUpload}
          >
            Upload your first video
          </button>
        </div>
      ) : (
        <div className="video-grid">
          {videos.map((video) => {
            const isReady = video.status === 'ready';
            const isFailed = video.status === 'failed';
            const isProcessing = !isReady && !isFailed;

            return (
              <div key={video.id} className="card" style={{ display: 'flex', flexDirection: 'column' }}>
                <div className="video-card-thumb">
                  <Film size={40} color="var(--text-muted)" />
                  {video.duration_seconds !== null && (
                    <div className="video-duration-pill">
                      {formatDuration(video.duration_seconds)}
                    </div>
                  )}
                </div>

                <div style={{ marginTop: '1rem', flex: 1, display: 'flex', flexDirection: 'column' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                    <h4
                      style={{
                        fontSize: '0.95rem',
                        fontWeight: 600,
                        wordBreak: 'break-all',
                        color: 'var(--text-primary)',
                      }}
                      title={video.filename}
                    >
                      {video.filename}
                    </h4>
                    <span className={`badge badge-${video.status}`}>
                      {video.status}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.4rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <span>{formatBytes(video.size_bytes)}</span>
                    {video.width && video.height && (
                      <span>{video.width}×{video.height}</span>
                    )}
                    {video.fps && <span>{video.fps.toFixed(1)} fps</span>}
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                      {video.has_audio ? <Volume2 size={12} /> : <VolumeX size={12} />}
                      {video.has_audio ? 'Audio' : 'Muted'}
                    </span>
                  </div>

                  {isProcessing && (
                    <div style={{ marginTop: '0.75rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#fbbf24' }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                          <Clock size={12} />
                          {video.current_stage || 'Processing'}
                        </span>
                        <span>{video.progress}%</span>
                      </div>
                      <div className="progress-bar-container">
                        <div
                          className="progress-bar-fill"
                          style={{ width: `${Math.max(5, video.progress)}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {isFailed && (
                    <div
                      style={{
                        marginTop: '0.75rem',
                        padding: '0.5rem',
                        borderRadius: '0.35rem',
                        background: 'rgba(244, 63, 94, 0.1)',
                        fontSize: '0.75rem',
                        color: '#fb7185',
                      }}
                    >
                      <strong>{video.error_code || 'Error'}:</strong> {video.error_message || 'Processing failed'}
                    </div>
                  )}

                  <div style={{ marginTop: 'auto', paddingTop: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      {formatDate(video.created_at)}
                    </span>

                    <div style={{ display: 'flex', gap: '0.4rem' }}>
                      {isReady && (
                        <>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            style={{ padding: '0.35rem 0.6rem' }}
                            onClick={() => onSelectVideoForPlay(video.id, video.filename)}
                            title="Play video"
                          >
                            Play
                          </button>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            style={{ padding: '0.35rem 0.6rem' }}
                            onClick={() => onSelectVideoForSearch(video.id, video.filename)}
                            title="Search within video"
                          >
                            <Search size={14} />
                          </button>
                        </>
                      )}

                      <button
                        type="button"
                        className="btn btn-danger"
                        style={{ padding: '0.35rem 0.6rem' }}
                        onClick={() => setVideoToDelete(video)}
                        title="Delete video & purge all frame indices"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <ConfirmModal
        isOpen={videoToDelete !== null}
        title="Delete Video & Derived Frames"
        message={`Are you sure you want to delete "${videoToDelete?.filename}"? This action permanently cascades: the original media file, all extracted frames, window embeddings, and thumbnail previews will be purged from storage.`}
        confirmLabel="Cascade Delete"
        onConfirm={handleDelete}
        onCancel={() => setVideoToDelete(null)}
        isLoading={isDeleting}
      />
    </div>
  );
};
