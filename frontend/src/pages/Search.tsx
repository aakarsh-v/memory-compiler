import React, { useState } from 'react';
import { Search as SearchIcon, Sliders, AlertCircle, Sparkles, Film } from 'lucide-react';
import { api } from '../api/client';
import { SearchMode, SearchResult, SearchResponse } from '../types';
import { ResultCard } from '../components/ResultCard';
import { VideoPlayer } from '../components/VideoPlayer';

interface SearchPageProps {
  initialVideoId?: string | null;
  initialVideoTitle?: string | null;
}

export const SearchPage: React.FC<SearchPageProps> = ({
  initialVideoId = null,
  initialVideoTitle = null,
}) => {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<SearchMode>('frame_semantic_v1');
  const [minSimilarity, setMinSimilarity] = useState(0.05);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(null);

  // Active player state
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(initialVideoId);
  const [selectedVideoTitle, setSelectedVideoTitle] = useState<string | null>(initialVideoTitle);
  const [selectedSeekTime, setSelectedSeekTime] = useState<number | undefined>(undefined);
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const res = await api.search(query.trim(), mode, 20, minSimilarity);
      setSearchResponse(res);

      // If results returned and no active player, pick top match
      if (res.results.length > 0) {
        const top = res.results[0];
        setSelectedVideoId(top.video_id);
        setSelectedVideoTitle(top.filename);
        setSelectedSeekTime(top.evidence_timestamp_seconds);
        setSelectedResult(top);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Search failed');
      setSearchResponse(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectResult = (result: SearchResult) => {
    setSelectedResult(result);
    setSelectedVideoId(result.video_id);
    setSelectedVideoTitle(result.filename);
    setSelectedSeekTime(result.evidence_timestamp_seconds);
  };

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.35rem', fontWeight: 700, marginBottom: '0.25rem' }}>
          Natural-Language Semantic Video Search
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          Search indexed frames and temporal windows using natural language queries.
        </p>
      </div>

      <form onSubmit={handleSearch} className="search-bar-wrap">
        <SearchIcon className="search-icon" size={20} />
        <input
          type="text"
          className="search-input"
          placeholder="e.g. 'red car on highway', 'person laughing', 'blue banner before sunset'..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button
          type="submit"
          className="btn btn-primary"
          style={{ position: 'absolute', right: '0.5rem', top: '50%', transform: 'translateY(-50%)' }}
          disabled={isLoading || !query.trim()}
        >
          {isLoading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {/* Query Options */}
      <div className="search-options">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Sliders size={16} color="var(--text-muted)" />
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Search Mode:</span>
          <select
            className="select-input"
            value={mode}
            onChange={(e) => setMode(e.target.value as SearchMode)}
          >
            <option value="frame_semantic_v1">Frame Semantic (v1)</option>
            <option value="video_window_v1">Video Window (v1)</option>
            <option value="hybrid_v1">Hybrid Multi-Resolution (v1)</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Min Similarity:</span>
          <input
            type="range"
            min="0"
            max="0.8"
            step="0.05"
            value={minSimilarity}
            onChange={(e) => setMinSimilarity(parseFloat(e.target.value))}
            style={{ width: '90px', accentColor: 'var(--accent-blue)', cursor: 'pointer' }}
          />
          <span style={{ fontSize: '0.8rem', fontFamily: 'monospace', color: 'var(--text-muted)' }}>
            {minSimilarity.toFixed(2)}
          </span>
        </div>

        {searchResponse && (
          <div style={{ marginLeft: 'auto', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Found {searchResponse.total_results} matches in {searchResponse.execution_time_ms}ms
          </div>
        )}
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

      {/* Main Split Layout: Results list on left, HTML5 Player on right */}
      <div className="search-layout">
        <div>
          {isLoading ? (
            <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-secondary)' }}>
              <p>Searching multimodal index...</p>
            </div>
          ) : !searchResponse ? (
            <div className="card" style={{ textAlign: 'center', padding: '3rem 1.5rem', borderStyle: 'dashed' }}>
              <Sparkles size={36} color="var(--accent-blue)" style={{ margin: '0 auto 0.75rem' }} />
              <h4 style={{ fontSize: '1rem', marginBottom: '0.25rem' }}>Ready to Search</h4>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                Enter a visual description or event query above. Candidate frames and temporal windows will appear here.
              </p>
            </div>
          ) : searchResponse.results.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: '3rem 1.5rem' }}>
              <Film size={36} color="var(--text-muted)" style={{ margin: '0 auto 0.75rem' }} />
              <h4 style={{ fontSize: '1rem', marginBottom: '0.25rem' }}>No matching moments found</h4>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                Try lowering the similarity threshold or phrasing the visual description differently.
              </p>
            </div>
          ) : (
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
                Showing top {searchResponse.results.length} candidate windows (ranked by cosine similarity)
              </div>
              {searchResponse.results.map((result, idx) => (
                <ResultCard
                  key={`${result.video_id}-${result.evidence_timestamp_seconds}-${idx}`}
                  result={result}
                  isSelected={
                    selectedResult?.video_id === result.video_id &&
                    selectedResult?.evidence_timestamp_seconds === result.evidence_timestamp_seconds
                  }
                  onSelect={handleSelectResult}
                />
              ))}
            </div>
          )}
        </div>

        <div>
          <VideoPlayer
            videoId={selectedVideoId}
            videoTitle={selectedVideoTitle || undefined}
            initialSeekSeconds={selectedSeekTime}
            highlightRange={
              selectedResult
                ? { start: selectedResult.start_seconds, end: selectedResult.end_seconds }
                : undefined
            }
          />
        </div>
      </div>
    </div>
  );
};

