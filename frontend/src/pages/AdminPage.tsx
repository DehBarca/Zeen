import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useAuthStore } from '../store/authStore'
import { contentService, Content } from '../services/content'
import './HomePage.css'

export function AdminPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { logout } = useAuthStore()
  const [contents, setContents] = useState<Content[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [contentType, setContentType] = useState<'all' | 'movie' | 'series'>('all')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => {
    if (!user || user.role !== 'admin') return
    void fetchContents()
  }, [user, search, contentType])

  const selectedContent = useMemo(
    () => contents.find((content) => content.id === selectedId) || null,
    [contents, selectedId]
  )

  async function fetchContents() {
    setLoading(true)
    try {
      const list = await contentService.listContent({
        limit: 100,
        query: search.trim() || undefined,
        content_type: contentType === 'all' ? undefined : contentType,
        sort_by: 'created_at',
        sort_order: 'desc',
      })
      setContents(list)
      setSelectedId((current) => (current && list.some((item) => item.id === current) ? current : list[0]?.id ?? null))
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this content?')) return
    try {
      await contentService.deleteContent(id)
      await fetchContents()
    } catch {
      alert('Delete failed')
    }
  }

  if (!user || user.role !== 'admin') {
    return <div style={{ padding: 20 }}>Access denied. Admins only.</div>
  }

  return (
    <div className="home-page">
      <header className="header">
        <div className="header-topbar">
          <div>
            <h1>Admin Panel</h1>
            <p>Select a movie or series to edit it, or create a new one from the main button.</p>
          </div>

          <div className="header-actions">
            <button type="button" className="header-button ghost" onClick={() => navigate('/')}>
              Exit panel
            </button>
            <button type="button" className="header-button" onClick={() => navigate('/admin/content/new')}>
              Create movie
            </button>
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
        <div className="catalog-layout">
          <div>
            <div className="section-title-row">
              <h2>Catalog</h2>
              <p>Click a card to select it, then press edit.</p>
            </div>

            {loading ? (
              <p>Loading...</p>
            ) : contents.length === 0 ? (
              <p>No content yet.</p>
            ) : (
              <div className="content-grid">
                {contents.map((content) => {
                  const isSelected = content.id === selectedId
                  return (
                    <button
                      key={content.id}
                      type="button"
                      className={isSelected ? 'content-card selected' : 'content-card'}
                      onClick={() => setSelectedId(content.id)}
                    >
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
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          <aside className="selection-panel">
            <h3>Actions</h3>
            {selectedContent ? (
              <>
                <p className="selection-title">{selectedContent.title}</p>
                <p className="selection-meta">
                  {selectedContent.content_type} · {selectedContent.release_date?.slice?.(0, 10)}
                </p>
                <p className="selection-description">{selectedContent.description}</p>
                <div className="selection-actions">
                  <button type="button" className="header-button" onClick={() => navigate(`/admin/content/${selectedContent.id}/edit`)}>
                    Edit
                  </button>
                  <button type="button" className="header-button danger" onClick={() => handleDelete(selectedContent.id)}>
                    Delete
                  </button>
                </div>
              </>
            ) : (
              <p>Select a movie or series to see actions.</p>
            )}
          </aside>
        </div>
      </section>
    </div>
  )
}

export default AdminPage