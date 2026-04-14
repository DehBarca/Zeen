import { useEffect } from 'react'
import { useAuthStore } from '../store/authStore'

export const useAuth = () => {
  const { user, token, isLoading, loadUser } = useAuthStore()

  useEffect(() => {
    if (token && !user) {
      loadUser()
    }
  }, [token, user, loadUser])

  return {
    user,
    token,
    isLoading,
    isAuthenticated: !!user,
  }
}
