import { create } from 'zustand'
import { User, authService } from '../services/auth'

interface AuthStore {
  user: User | null
  token: string | null
  isLoading: boolean
  error: string | null
  
  // Actions
  setUser: (user: User | null) => void
  setToken: (token: string | null) => void
  login: (email: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string) => Promise<void>
  logout: () => void
  loadUser: () => Promise<void>
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  token: localStorage.getItem('access_token'),
  isLoading: false,
  error: null,

  setUser: (user) => set({ user }),
  setToken: (token) => {
    if (token) {
      localStorage.setItem('access_token', token)
    } else {
      localStorage.removeItem('access_token')
    }
    set({ token })
  },

  login: async (email, password) => {
    set({ isLoading: true, error: null })
    try {
      const response = await authService.login({ email, password })
      set({ token: response.access_token })
      localStorage.setItem('access_token', response.access_token)
      
      // Load user data
      const user = await authService.getMe()
      set({ user, isLoading: false })
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Login failed'
      set({ error: errorMessage, isLoading: false })
      throw error
    }
  },

  register: async (email, username, password) => {
    set({ isLoading: true, error: null })
    try {
      await authService.register({ email, username, password })
      // Auto-login after registration
      await authService.login({ email, password })
      const response = await authService.login({ email, password })
      set({ token: response.access_token })
      localStorage.setItem('access_token', response.access_token)
      
      const user = await authService.getMe()
      set({ user, isLoading: false })
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Registration failed'
      set({ error: errorMessage, isLoading: false })
      throw error
    }
  },

  logout: () => {
    authService.logout()
    set({ user: null, token: null, error: null })
  },

  loadUser: async () => {
    const token = localStorage.getItem('access_token')
    if (!token) return

    set({ isLoading: true })
    try {
      const user = await authService.getMe()
      set({ user, isLoading: false })
    } catch (error) {
      set({ user: null, token: null, isLoading: false })
    }
  },
}))
