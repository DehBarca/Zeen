import React from 'react'
import './MovieModal.css'
import { Content } from '../services/content'

interface Props {
  content: Content
  onClose: () => void
}

export default function MovieModal({ content, onClose }: Props) {
  const poster = content.poster_url || ''
  const banner = content.banner_url || poster
  const genres = content.genres || []
  const cast = content.cast || []
  const directors = content.directors || []
  const releaseYear = content.release_date ? new Date(content.release_date).getFullYear() : ''
  const duration = typeof content.duration_minutes === 'number' ? content.duration_minutes : undefined

  return (
    <div className="mm-overlay" onClick={onClose}>
      <div className="mm-modal" onClick={(e) => e.stopPropagation()}>
        <button className="mm-close" onClick={onClose} aria-label="Close">×</button>
        <div className="mm-banner" style={{ backgroundImage: `url(${banner})` }}>
          <div className="mm-banner-overlay">
            <h2 className="mm-title">{content.title || 'Untitled'}</h2>
            <div className="mm-actions">
              <button className="mm-play">▶ Play</button>
            </div>
          </div>
        </div>

        <div className="mm-body">
          <div className="mm-poster">
            {poster ? <img src={poster} alt={content.title || 'poster'} /> : <div className="mm-poster-placeholder" />}
          </div>
          <div className="mm-details">
            <p className="mm-meta">
              <strong>{content.content_type || 'content'}</strong>
              {duration !== undefined && <> • {duration} min</>}
              {releaseYear && <> • {releaseYear}</>}
            </p>
            {typeof content.rating === 'number' && <p className="mm-rating">⭐ {content.rating.toFixed(1)}</p>}
            <p className="mm-description">{content.description || 'No description available.'}</p>

            <p className="mm-list"><strong>Genres:</strong> {genres.length ? genres.join(', ') : '—'}</p>
            <p className="mm-list"><strong>Cast:</strong> {cast.length ? cast.join(', ') : '—'}</p>
            <p className="mm-list"><strong>Directors:</strong> {directors.length ? directors.join(', ') : '—'}</p>
          </div>
        </div>
      </div>
    </div>
  )
}
