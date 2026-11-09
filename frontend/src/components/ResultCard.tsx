import React, { useState } from 'react';
import { Clock, PlayCircle, Eye, Tag } from 'lucide-react';
import { SearchResult } from '../types';
import { formatDuration, formatScore } from '../utils/formatters';

interface ResultCardProps {
  result: SearchResult;
  isSelected: boolean;
  onSelect: (result: SearchResult) => void;
}

export const ResultCard: React.FC<ResultCardProps> = ({
  result,
  isSelected,
  onSelect,
}) => {
  const [thumbError, setThumbError] = useState(false);

  return (
    <div
      className={`result-card ${isSelected ? 'selected' : ''}`}
      onClick={() => onSelect(result)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          onSelect(result);
        }
      }}
    >
      <div className="result-thumb">
        {!thumbError ? (
          <img
            src={result.thumbnail_url}
            alt={`Frame evidence at ${formatDuration(result.evidence_timestamp_seconds)}`}
            onError={() => setThumbError(true)}
            loading="lazy"
          />
        ) : (
          <div
            style={{
              width: '100%',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: '#1e293b',
              color: 'var(--text-muted)',
            }}
          >
            <Eye size={20} />
          </div>
        )}
        <div className="video-duration-pill">
          {formatDuration(result.evidence_timestamp_seconds)}
        </div>
      </div>

      <div className="result-info">
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
            <h5
              style={{
                fontSize: '0.9rem',
                fontWeight: 600,
                color: 'var(--text-primary)',
                wordBreak: 'break-all',
              }}
            >
              {result.filename}
            </h5>
            <span
              className="similarity-badge"
              title={`Similarity: ${formatScore(result.score)} (${result.score_type})`}
            >
              {formatScore(result.score)}
            </span>
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              color: 'var(--text-secondary)',
              fontSize: '0.78rem',
              marginTop: '0.35rem',
            }}
          >
            <Clock size={13} />
            <span>
              Window: {formatDuration(result.start_seconds)} – {formatDuration(result.end_seconds)}
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '0.5rem' }}>
          <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
            <span
              style={{
                fontSize: '0.7rem',
                background: 'rgba(255,255,255,0.06)',
                color: 'var(--text-muted)',
                padding: '0.1rem 0.4rem',
                borderRadius: '0.2rem',
              }}
            >
              {result.search_mode}
            </span>

            {result.applied_constraints && result.applied_constraints.length > 0 && (
              <span
                style={{
                  fontSize: '0.7rem',
                  background: 'rgba(16, 185, 129, 0.1)',
                  color: '#34d399',
                  padding: '0.1rem 0.4rem',
                  borderRadius: '0.2rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.2rem',
                }}
              >
                <Tag size={10} />
                {result.applied_constraints.join(', ')}
              </span>
            )}
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem',
              color: isSelected ? 'var(--accent-blue)' : 'var(--text-muted)',
              fontSize: '0.75rem',
              fontWeight: 500,
            }}
          >
            <PlayCircle size={14} />
            <span>Seek</span>
          </div>
        </div>
      </div>
    </div>
  );
};
