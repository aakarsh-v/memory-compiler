import React from 'react';
import { Film, Search, UploadCloud, Database, User } from 'lucide-react';

interface NavbarProps {
  currentTab: 'library' | 'upload' | 'search';
  onTabChange: (tab: 'library' | 'upload' | 'search') => void;
  ownerId: string;
  onOwnerIdChange: (ownerId: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentTab,
  onTabChange,
  ownerId,
  onOwnerIdChange,
}) => {
  return (
    <header className="app-header">
      <div className="brand" role="banner">
        <Film className="brand-icon" />
        <span>Memory Compiler</span>
      </div>

      <nav className="nav-links" aria-label="Main Navigation">
        <button
          className={`nav-btn ${currentTab === 'library' ? 'active' : ''}`}
          onClick={() => onTabChange('library')}
        >
          <Database size={18} />
          <span>Library</span>
        </button>

        <button
          className={`nav-btn ${currentTab === 'search' ? 'active' : ''}`}
          onClick={() => onTabChange('search')}
        >
          <Search size={18} />
          <span>Semantic Search</span>
        </button>

        <button
          className={`nav-btn ${currentTab === 'upload' ? 'active' : ''}`}
          onClick={() => onTabChange('upload')}
        >
          <UploadCloud size={18} />
          <span>Upload</span>
        </button>
      </nav>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <User size={15} color="var(--text-muted)" />
        <input
          type="text"
          value={ownerId}
          onChange={(e) => onOwnerIdChange(e.target.value || 'default_user')}
          className="owner-tag"
          title="Current Owner ID (enforces isolated private storage & search)"
          style={{ width: '110px' }}
        />
      </div>
    </header>
  );
};
