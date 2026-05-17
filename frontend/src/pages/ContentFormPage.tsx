import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useAuthStore } from '../store/authStore'
import { ContentCreate, contentService } from '../services/content'
import './HomePage.css'

type ContentFormState = Omit<ContentCreate, 'genres' | 'cast' | 'directors'> & {
  genresText: string
  castText: string
  directorsText: string
}

const defaultForm = (): ContentFormState => ({
  title: '',
  description: '',
  content_type: 'movie',
  duration_minutes: 90,
  release_date: new Date().toISOString().slice(0, 10),
  poster_url: '',
  banner_url: '',
  rating: undefined,
  genresText: '',
  castText: '',
  directorsText: '',
})

export function ContentFormPage() {
  const navigate = useNavigate()
  const { id } = useParams()
  const { user } = useAuth()
  const { logout } = useAuthStore()
  const isEditMode = Boolean(id)
  const [loading, setLoading] = useState(isEditMode)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState<ContentFormState>(defaultForm)

  useEffect(() => {
    if (!user || user.role !== 'admin') return
    if (!id) return

    const loadContent = async () => {
      setLoading(true)
      try {
        const content = await contentService.getContent(id)
        setForm({
          title: content.title,
          description: content.description,
          content_type: content.content_type,
          duration_minutes: content.duration_minutes,
          release_date: content.release_date.slice(0, 10),
          poster_url: content.poster_url || '',
          banner_url: content.banner_url || '',
          rating: content.rating,
          genresText: content.genres.join(', '),
          castText: content.cast.join(', '),
          directorsText: content.directors.join(', '),
        })
      } finally {
        setLoading(false)
      }
    }

    void loadContent()
  }, [id, user])

  const title = useMemo(() => (isEditMode ? 'Edit content' : 'Create movie'), [isEditMode])

  const parseList = (value: string) =>
    value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const payload: ContentCreate = {
        title: form.title.trim(),
        description: form.description.trim(),
        content_type: form.content_type,
        duration_minutes: Number(form.duration_minutes),
        release_date: new Date(form.release_date).toISOString(),
        poster_url: form.poster_url.trim() || undefined,
        banner_url: form.banner_url.trim() || undefined,
        rating: form.rating ? Number(form.rating) : undefined,
        genres: parseList(form.genresText),
        cast: parseList(form.castText),
        directors: parseList(form.directorsText),
      }

      if (isEditMode && id) {
        await contentService.updateContent(id, payload)
      } else {
        await contentService.createContent(payload)
      }

      navigate('/admin')
    } catch (error: any) {
      alert(error?.response?.data?.detail || 'Unable to save content')
    } finally {
      setSaving(false)
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  if (!user || user.role !== 'admin') {
    return <div style={{ padding: 20 }}>Access denied. Admins only.</div>
  }

  if (loading) {
    return <div className="home-page" style={{ padding: 24 }}>Loading...</div>
  }

  return (
    <div className="home-page">
      <header className="header">
        <div className="header-topbar">
          <div>
            <h1>{title}</h1>
            <p>Fill out the required fields to save the movie or series.</p>
          </div>

          <div className="header-actions">
            <button type="button" className="header-button ghost" onClick={() => navigate('/')}>
              Exit admin
            </button>
            <button type="button" className="header-button ghost" onClick={() => navigate('/admin')}>
              Back to panel
            </button>
            <button type="button" className="header-button danger" onClick={handleLogout}>
              Log out
            </button>
          </div>
        </div>
      </header>

      <section className="content-section">
        <form className="editor-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Title</label>
            <input value={form.title} onChange={(e) => setForm((current) => ({ ...current, title: e.target.value }))} required />
          </div>

          <div className="form-group">
            <label>Description</label>
            <textarea value={form.description} onChange={(e) => setForm((current) => ({ ...current, description: e.target.value }))} required />
          </div>

          <div className="form-group">
            <label>Type</label>
            <select value={form.content_type} onChange={(e) => setForm((current) => ({ ...current, content_type: e.target.value as ContentCreate['content_type'] }))}>
              <option value="movie">Movie</option>
              <option value="series">Series</option>
              <option value="episode">Episode</option>
            </select>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Duration (minutes)</label>
              <input type="number" value={form.duration_minutes} onChange={(e) => setForm((current) => ({ ...current, duration_minutes: Number(e.target.value) }))} required />
            </div>
            <div className="form-group">
              <label>Release date</label>
              <input type="date" value={form.release_date} onChange={(e) => setForm((current) => ({ ...current, release_date: e.target.value }))} required />
            </div>
          </div>

          <div className="form-group">
            <label>Poster URL</label>
            <input value={form.poster_url || ''} onChange={(e) => setForm((current) => ({ ...current, poster_url: e.target.value }))} />
          </div>

          <div className="form-group">
            <label>Banner URL</label>
            <input value={form.banner_url || ''} onChange={(e) => setForm((current) => ({ ...current, banner_url: e.target.value }))} />
          </div>

          <div className="form-group">
            <label>Genres (comma separated)</label>
            <input value={form.genresText} onChange={(e) => setForm((current) => ({ ...current, genresText: e.target.value }))} />
          </div>

          <div className="form-group">
            <label>Cast (comma separated)</label>
            <input value={form.castText} onChange={(e) => setForm((current) => ({ ...current, castText: e.target.value }))} />
          </div>

          <div className="form-group">
            <label>Directors (comma separated)</label>
            <input value={form.directorsText} onChange={(e) => setForm((current) => ({ ...current, directorsText: e.target.value }))} />
          </div>

          <div className="selection-actions">
            <button type="submit" className="header-button" disabled={saving}>
              {saving ? 'Saving...' : isEditMode ? 'Save changes' : 'Create movie'}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}

export default ContentFormPage