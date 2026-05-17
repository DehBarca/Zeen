import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useAuthStore } from '../store/authStore'
import './HomePage.css'

export function ProfilePage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { logout } = useAuthStore()

  if (!user) {
    return <div style={{ padding: 24 }}>Loading...</div>
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
            <h1>My Profile</h1>
            <p>{fullName}</p>
          </div>

          <div className="header-actions">
            <button type="button" className="header-button ghost" onClick={() => navigate('/') }>
              Back to home
            </button>
            <button type="button" className="header-button danger" onClick={handleLogout}>
              Log out
            </button>
          </div>
        </div>
      </header>

      <section className="content-section">
        <div className="profile-card">
          <h2>Account details</h2>
          <p><strong>Username:</strong> {user.username}</p>
          <p><strong>Email:</strong> {user.email}</p>
          <p><strong>Role:</strong> {user.role || 'user'}</p>
          <p><strong>Status:</strong> {user.is_active ? 'Active' : 'Inactive'}</p>
          <div className="profile-actions">
            <button type="button" className="header-button" onClick={() => navigate(user.role === 'admin' ? '/admin' : '/') }>
              Go to {user.role === 'admin' ? 'admin panel' : 'home'}
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}

export default ProfilePage