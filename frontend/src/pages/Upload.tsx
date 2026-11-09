import React, { useState, useRef, useEffect } from 'react';
import { UploadCloud, CheckCircle, AlertCircle, FileVideo, Clock, ArrowRight } from 'lucide-react';
import { api } from '../api/client';
import { Video, VideoStatus } from '../types';
import { formatBytes } from '../utils/formatters';

interface UploadProps {
  onUploadSuccess: (videoId: string) => void;
  onNavigateToSearch: (videoId?: string) => void;
}

const ALLOWED_EXTS = ['mp4', 'mkv', 'mov', 'avi', 'webm'];
const MAX_SIZE_MB = 100;
const MAX_BYTES = MAX_SIZE_MB * 1024 * 1024;

const STAGES = [
  { key: 'queued', label: 'Queued for Ingestion' },
  { key: 'probing', label: 'FFprobe Stream Verification' },
  { key: 'extracting_frames', label: 'FFmpeg Frame Extraction (2.0s monotonic)' },
  { key: 'embedding_frames', label: 'Multimodal Vector Embedding' },
  { key: 'persisting_index', label: 'pgvector Index Persistence' },
  { key: 'ready', label: 'Ready for Semantic Search' },
];

export const Upload: React.FC<UploadProps> = ({
  onUploadSuccess,
  onNavigateToSearch,
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [activeJobVideo, setActiveJobVideo] = useState<Video | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollTimerRef = useRef<number | null>(null);

  const validateFile = (file: File): string | null => {
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!ext || !ALLOWED_EXTS.includes(ext)) {
      return `Unsupported file format ".${ext || 'unknown'}". Allowed: ${ALLOWED_EXTS.join(', ')}`;
    }
    if (file.size > MAX_BYTES) {
      return `File size (${formatBytes(file.size)}) exceeds the maximum upload limit of ${MAX_SIZE_MB}MB.`;
    }
    return null;
  };

  const handleFile = (file: File) => {
    const error = validateFile(file);
    if (error) {
      setUploadError(error);
      setSelectedFile(null);
    } else {
      setUploadError(null);
      setSelectedFile(file);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleUploadSubmit = async () => {
    if (!selectedFile) return;
    setIsUploading(true);
    setUploadError(null);

    try {
      const res = await api.uploadVideo(selectedFile);
      // Fetch initial status
      const statusRes = await api.getVideoStatus(res.video_id);
      setActiveJobVideo(statusRes);
      onUploadSuccess(res.video_id);
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  // Poll active video status until READY or FAILED
  useEffect(() => {
    if (!activeJobVideo) return;
    if (activeJobVideo.status === 'ready' || activeJobVideo.status === 'failed') return;

    pollTimerRef.current = window.setTimeout(async () => {
      try {
        const updated = await api.getVideoStatus(activeJobVideo.id);
        setActiveJobVideo(updated);
      } catch {
        // Retry next cycle
      }
    }, 2000);

    return () => {
      if (pollTimerRef.current) {
        window.clearTimeout(pollTimerRef.current);
      }
    };
  }, [activeJobVideo]);

  const getStageIndex = (status: VideoStatus): number => {
    return STAGES.findIndex((s) => s.key === status);
  };

  return (
    <div style={{ maxWidth: '750px', margin: '0 auto' }}>
      <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>Upload Video Memory</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '0.25rem' }}>
          Upload MP4, MKV, MOV, or WEBM clips up to {MAX_SIZE_MB}MB to index frame embeddings into pgvector.
        </p>
      </div>

      {!activeJobVideo ? (
        <div className="card">
          <div
            className={`dropzone ${dragActive ? 'active' : ''}`}
            onDragEnter={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragLeave={(e) => { e.preventDefault(); setDragActive(false); }}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".mp4,.mkv,.mov,.avi,.webm"
              style={{ display: 'none' }}
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleFile(e.target.files[0]);
                }
              }}
            />
            <UploadCloud size={44} color="var(--accent-blue)" style={{ margin: '0 auto 1rem' }} />
            <h4 style={{ fontSize: '1.05rem', marginBottom: '0.35rem' }}>
              Drag and drop your video here
            </h4>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              or click to browse files on your device
            </p>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '0.75rem' }}>
              Supported: {ALLOWED_EXTS.join(', ')} • Max: {MAX_SIZE_MB}MB
            </p>
          </div>

          {selectedFile && (
            <div
              style={{
                marginTop: '1.25rem',
                padding: '0.85rem 1rem',
                background: 'var(--bg-secondary)',
                borderRadius: '0.5rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                border: '1px solid var(--border-color)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <FileVideo size={24} color="var(--accent-blue)" />
                <div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>{selectedFile.name}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    {formatBytes(selectedFile.size)}
                  </div>
                </div>
              </div>

              <button
                type="button"
                className="btn btn-primary"
                onClick={handleUploadSubmit}
                disabled={isUploading}
              >
                {isUploading ? 'Uploading...' : 'Start Ingestion'}
              </button>
            </div>
          )}

          {uploadError && (
            <div
              style={{
                marginTop: '1.25rem',
                padding: '0.85rem 1rem',
                borderRadius: '0.5rem',
                background: 'rgba(244, 63, 94, 0.1)',
                border: '1px solid rgba(244, 63, 94, 0.3)',
                color: '#fb7185',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                fontSize: '0.85rem',
              }}
            >
              <AlertCircle size={18} />
              <span>{uploadError}</span>
            </div>
          )}
        </div>
      ) : (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <FileVideo size={24} color="var(--accent-blue)" />
              <div>
                <h4 style={{ fontSize: '1rem', fontWeight: 600 }}>{activeJobVideo.filename}</h4>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  ID: {activeJobVideo.id}
                </span>
              </div>
            </div>

            <span className={`badge badge-${activeJobVideo.status}`}>
              {activeJobVideo.status}
            </span>
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>
                {activeJobVideo.current_stage || 'Processing pipeline'}
              </span>
              <span style={{ fontWeight: 600 }}>{activeJobVideo.progress}%</span>
            </div>

            <div className="progress-bar-container" style={{ height: '8px' }}>
              <div
                className="progress-bar-fill"
                style={{ width: `${Math.max(5, activeJobVideo.progress)}%` }}
              />
            </div>
          </div>

          {/* Stepper details */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.5rem' }}>
            {STAGES.map((stage, idx) => {
              const currentIdx = getStageIndex(activeJobVideo.status);
              const isPast = currentIdx > idx || activeJobVideo.status === 'ready';
              const isCurrent = currentIdx === idx && activeJobVideo.status !== 'ready';

              return (
                <div
                  key={stage.key}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                    color: isPast ? '#34d399' : isCurrent ? '#fbbf24' : 'var(--text-muted)',
                    fontSize: '0.85rem',
                  }}
                >
                  {isPast ? (
                    <CheckCircle size={16} />
                  ) : isCurrent ? (
                    <Clock size={16} className="spin" />
                  ) : (
                    <div
                      style={{
                        width: '16px',
                        height: '16px',
                        borderRadius: '50%',
                        border: '2px solid var(--text-muted)',
                      }}
                    />
                  )}
                  <span>{stage.label}</span>
                </div>
              );
            })}
          </div>

          {activeJobVideo.status === 'ready' && (
            <div
              style={{
                background: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                padding: '1rem',
                borderRadius: '0.5rem',
                marginBottom: '1rem',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <div style={{ fontWeight: 600, color: '#34d399', fontSize: '0.9rem' }}>
                  Ingestion & Embedding Complete
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  This video is indexed and immediately queryable via semantic search.
                </div>
              </div>

              <button
                type="button"
                className="btn btn-primary"
                onClick={() => onNavigateToSearch(activeJobVideo.id)}
              >
                <span>Search Video</span>
                <ArrowRight size={15} />
              </button>
            </div>
          )}

          {activeJobVideo.status === 'failed' && (
            <div
              style={{
                background: 'rgba(244, 63, 94, 0.1)',
                border: '1px solid rgba(244, 63, 94, 0.3)',
                padding: '1rem',
                borderRadius: '0.5rem',
                marginBottom: '1rem',
                color: '#fb7185',
              }}
            >
              <strong>Processing Failed ({activeJobVideo.error_code}):</strong> {activeJobVideo.error_message}
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                setActiveJobVideo(null);
                setSelectedFile(null);
              }}
            >
              Upload Another Video
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
