import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Library } from './pages/Library';
import { Upload } from './pages/Upload';
import { SearchPage } from './pages/Search';
import { api } from './api/client';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<'library' | 'upload' | 'search'>('library');
  const [ownerId, setOwnerId] = useState<string>('default_user');

  // Preselection for search
  const [searchTargetVideoId, setSearchTargetVideoId] = useState<string | null>(null);
  const [searchTargetTitle, setSearchTargetTitle] = useState<string | null>(null);

  useEffect(() => {
    api.setOwnerId(ownerId);
  }, [ownerId]);

  const handleSelectVideoForSearch = (videoId: string, filename: string) => {
    setSearchTargetVideoId(videoId);
    setSearchTargetTitle(filename);
    setCurrentTab('search');
  };

  const handleSelectVideoForPlay = (videoId: string, filename: string) => {
    setSearchTargetVideoId(videoId);
    setSearchTargetTitle(filename);
    setCurrentTab('search');
  };

  return (
    <div className="app-container">
      <Navbar
        currentTab={currentTab}
        onTabChange={setCurrentTab}
        ownerId={ownerId}
        onOwnerIdChange={setOwnerId}
      />

      <main style={{ flex: 1 }}>
        {currentTab === 'library' && (
          <Library
            onSelectVideoForSearch={handleSelectVideoForSearch}
            onSelectVideoForPlay={handleSelectVideoForPlay}
            onNavigateToUpload={() => setCurrentTab('upload')}
          />
        )}

        {currentTab === 'upload' && (
          <Upload
            onUploadSuccess={() => {}}
            onNavigateToSearch={(videoId) => {
              if (videoId) setSearchTargetVideoId(videoId);
              setCurrentTab('search');
            }}
          />
        )}

        {currentTab === 'search' && (
          <SearchPage
            initialVideoId={searchTargetVideoId}
            initialVideoTitle={searchTargetTitle}
          />
        )}
      </main>

      <footer
        style={{
          marginTop: '4rem',
          paddingTop: '1.5rem',
          borderTop: '1px solid var(--border-color)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '0.8rem',
          color: 'var(--text-muted)',
        }}
      >
        <span>Memory Compiler — Semantic Video Retrieval & Timestamp Playback</span>
        <span>Isolated Owner: <strong style={{ color: 'var(--text-secondary)' }}>{ownerId}</strong></span>
      </footer>
    </div>
  );
};
