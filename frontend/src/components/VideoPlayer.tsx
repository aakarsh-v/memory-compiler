import React, { useRef, useEffect, useState } from 'react';
import { Play, Pause, RotateCcw, FastForward, Film } from 'lucide-react';
import { api } from '../api/client';
import { formatDuration } from '../utils/formatters';

interface VideoPlayerProps {
  videoId: string | null;
  videoTitle?: string;
  initialSeekSeconds?: number;
  highlightRange?: { start: number; end: number };
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  videoId,
  videoTitle,
  initialSeekSeconds,
  highlightRange,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    setCurrentTime(0);
    setIsPlaying(false);

    if (videoRef.current) {
      videoRef.current.load();
    }
  }, [videoId]);

  useEffect(() => {
    if (
      videoRef.current &&
      initialSeekSeconds !== undefined &&
      initialSeekSeconds !== null &&
      !isNaN(initialSeekSeconds)
    ) {
      videoRef.current.currentTime = initialSeekSeconds;
      videoRef.current.play().catch(() => {
        // Autoplay may be blocked by browser policy; user can click play
      });
    }
  }, [initialSeekSeconds, videoId]);

  if (!videoId) {
    return (
      <div className="player-container" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
        <Film size={48} color="var(--text-muted)" style={{ margin: '0 auto 1rem' }} />
        <h4 style={{ color: 'var(--text-secondary)' }}>No video selected</h4>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.5rem' }}>
          Click a search result or select a video from the library to start playback.
        </p>
      </div>
    );
  }

  const streamUrl = api.getStreamUrl(videoId);

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
    } else {
      videoRef.current.play().catch(() => {});
    }
  };

  const seekRelative = (delta: number) => {
    if (!videoRef.current) return;
    videoRef.current.currentTime = Math.max(0, Math.min(duration, videoRef.current.currentTime + delta));
  };

  const cyclePlaybackRate = () => {
    if (!videoRef.current) return;
    const rates = [1, 1.25, 1.5, 2.0];
    const nextIdx = (rates.indexOf(playbackRate) + 1) % rates.length;
    const newRate = rates[nextIdx];
    videoRef.current.playbackRate = newRate;
    setPlaybackRate(newRate);
  };

  return (
    <div className="player-container">
      <div style={{ position: 'relative' }}>
        <video
          ref={videoRef}
          src={streamUrl}
          className="player-video"
          controls={false}
          onTimeUpdate={() => {
            if (videoRef.current) {
              setCurrentTime(videoRef.current.currentTime);
            }
          }}
          onLoadedMetadata={() => {
            if (videoRef.current) {
              setDuration(videoRef.current.duration);
              if (initialSeekSeconds !== undefined) {
                videoRef.current.currentTime = initialSeekSeconds;
              }
            }
          }}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          onError={() => setError('Unable to stream video. Verify backend is running and ownership token is valid.')}
        />

        {error && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: 'rgba(0,0,0,0.85)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '1.5rem',
              color: 'var(--accent-rose)',
              textAlign: 'center',
              fontSize: '0.875rem',
            }}
          >
            {error}
          </div>
        )}
      </div>

      <div className="player-details">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <h4 style={{ fontSize: '0.95rem', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {videoTitle || `Video ${videoId.slice(0, 8)}`}
          </h4>
          <span style={{ fontSize: '0.8rem', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>
            {formatDuration(currentTime)} / {formatDuration(duration)}
          </span>
        </div>

        {/* Custom Timeline Scrub */}
        <div style={{ position: 'relative', width: '100%', marginBottom: '0.75rem' }}>
          <input
            type="range"
            min={0}
            max={duration || 100}
            step={0.1}
            value={currentTime}
            onChange={(e) => {
              const val = parseFloat(e.target.value);
              setCurrentTime(val);
              if (videoRef.current) {
                videoRef.current.currentTime = val;
              }
            }}
            style={{ width: '100%', accentColor: 'var(--accent-blue)', cursor: 'pointer' }}
          />

          {/* Highlight match region marker if available */}
          {highlightRange && duration > 0 && (
            <div
              style={{
                position: 'absolute',
                top: '0px',
                left: `${(highlightRange.start / duration) * 100}%`,
                width: `${Math.max(2, ((highlightRange.end - highlightRange.start) / duration) * 100)}%`,
                height: '5px',
                background: 'rgba(59, 130, 246, 0.65)',
                borderRadius: '2px',
                pointerEvents: 'none',
              }}
              title={`Match range: ${formatDuration(highlightRange.start)} - ${formatDuration(highlightRange.end)}`}
            />
          )}
        </div>

        {/* Controls Bar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ padding: '0.35rem 0.6rem' }}
              onClick={() => seekRelative(-5)}
              title="Seek back 5 seconds"
            >
              <RotateCcw size={15} />
              <span style={{ fontSize: '0.75rem' }}>-5s</span>
            </button>

            <button
              type="button"
              className="btn btn-primary"
              style={{ padding: '0.35rem 0.9rem' }}
              onClick={togglePlay}
            >
              {isPlaying ? <Pause size={16} /> : <Play size={16} />}
              <span style={{ fontSize: '0.8rem' }}>{isPlaying ? 'Pause' : 'Play'}</span>
            </button>

            <button
              type="button"
              className="btn btn-secondary"
              style={{ padding: '0.35rem 0.6rem' }}
              onClick={() => seekRelative(5)}
              title="Seek forward 5 seconds"
            >
              <FastForward size={15} />
              <span style={{ fontSize: '0.75rem' }}>+5s</span>
            </button>
          </div>

          <button
            type="button"
            className="btn btn-secondary"
            style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem', fontFamily: 'monospace' }}
            onClick={cyclePlaybackRate}
            title="Cycle Playback Speed"
          >
            {playbackRate}x
          </button>
        </div>
      </div>
    </div>
  );
};
