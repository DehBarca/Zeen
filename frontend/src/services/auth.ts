import api from './api'

export interface User {
  id: string
  email: string
  username: string
  first_name?: string
  last_name?: string
  is_active: boolean
  role?: 'user' | 'admin'
  watchlist?: string[]
  profiles?: Array<Record<string, unknown>>
  created_at: string
  updated_at: string
}

export interface UserCreate {
  email: string
  username: string
  password: string
  first_name?: string
  last_name?: string
}

export interface UserLogin {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export const authService = {
  async register(data: UserCreate): Promise<User> {
    const response = await api.post<User>('/auth/register', data)
    return response.data
  },

  async login(data: UserLogin): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/auth/login', data)
    return response.data
  },

  async getMe(): Promise<User> {
    const response = await api.get<User>('/auth/me')
    return response.data
  },

  logout(): void {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
  },
}
