import { useNavigate } from 'react-router-dom'
import { useAuth } from './useAuth'
import { useEffect } from 'react'

export const useProtectedRoute = () => {
  const navigate = useNavigate()
  const { isAuthenticated, isLoading } = useAuth()

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate('/login')
    }
  }, [isAuthenticated, isLoading, navigate])

  return { isAuthenticated, isLoading }
}
