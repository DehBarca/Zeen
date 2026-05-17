import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useContentStore } from '../store/contentStore'
import MovieModal from '../components/MovieModal'
import { useAuth } from '../hooks/useAuth'
import { useAuthStore } from '../store/authStore'
import './HomePage.css'

export function HomePage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { contents, isLoading, listContents, selectedContent, setSelectedContent } = useContentStore()
  const { logout } = useAuthStore()
  const [search, setSearch] = useState('')
  const [contentType, setContentType] = useState<'all' | 'movie' | 'series'>('all')

  useEffect(() => {
    const trimmed = search.trim()
    listContents({
      limit: trimmed ? 3 : 24,
      query: trimmed || undefined,
      content_type: contentType === 'all' ? undefined : contentType,
      sort_by: 'created_at',
      sort_order: 'desc',
    })
  }, [search, contentType, listContents])

  if (!user) {
    return <div>Loading...</div>
  }

  const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="home-page">
      <header className="header">
        <div className="header-topbar">
          <div>
            <h1>Zeen</h1>
            <p>Welcome, {fullName}!</p>
          </div>

          <div className="header-actions">
            <button type="button" className="header-button ghost" onClick={() => navigate('/profile')}>
              View profile
            </button>
            <button type="button" className="header-button danger" onClick={handleLogout}>
              Log out
            </button>
          </div>
        </div>

        <div className="search-toolbar">
          <input
            className="search-input"
            type="search"
            placeholder="Search by title, description, genre, cast, or director..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />

          <div className="filter-pills">
            <button type="button" className={contentType === 'all' ? 'pill active' : 'pill'} onClick={() => setContentType('all')}>
              All
            </button>
            <button type="button" className={contentType === 'movie' ? 'pill active' : 'pill'} onClick={() => setContentType('movie')}>
              Movies
            </button>
            <button type="button" className={contentType === 'series' ? 'pill active' : 'pill'} onClick={() => setContentType('series')}>
              Series
            </button>
          </div>
        </div>
      </header>

      <section className="content-section">
        <h2>Featured Content</h2>
        {isLoading ? (
          <p>Loading content...</p>
        ) : contents.length === 0 ? (
          <p>No content available yet</p>
        ) : (
          <div className="content-grid">
            {contents.map((content) => (
              <div key={content.id} className="content-card" onClick={() => setSelectedContent(content)} role="button" tabIndex={0}>
                <div className="content-poster">
                  {content.poster_url ? (
                    <img src={content.poster_url} alt={content.title} />
                  ) : (
                    <div className="placeholder">
                      <p>{content.content_type}</p>
                    </div>
                  )}
                </div>
                <div className="content-info">
                  <h3>{content.title}</h3>
                  <p className="content-type">{content.content_type}</p>
                  {content.rating && <p className="rating">⭐ {content.rating.toFixed(1)}</p>}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {selectedContent && (
        <MovieModal content={selectedContent} onClose={() => setSelectedContent(null)} />
      )}

      {user.role === 'admin' && (
        <section className="content-section admin-quick-link">
          <div className="admin-banner">
            <div>
              <h2>Admin panel</h2>
              <p>Manage content, review stats and keep the catalog updated.</p>
            </div>
            <button type="button" className="header-button" onClick={() => navigate('/admin')}>
              Open admin panel
            </button>
          </div>
        </section>
      )}
    </div>
  )
}
