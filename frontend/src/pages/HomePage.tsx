import { useEffect } from 'react'
import { useContentStore } from '../store/contentStore'
import { useAuth } from '../hooks/useAuth'
import './HomePage.css'

export function HomePage() {
  const { user } = useAuth()
  const { contents, isLoading, listContents } = useContentStore()

  useEffect(() => {
    listContents({ limit: 20 })
  }, [])

  if (!user) {
    return <div>Loading...</div>
  }

  return (
    <div className="home-page">
      <header className="header">
        <h1>Zeen</h1>
        <p>Welcome, {user.username}!</p>
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
              <div key={content.id} className="content-card">
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
    </div>
  )
}
