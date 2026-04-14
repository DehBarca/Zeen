import api from './api'

export type ContentType = 'movie' | 'series' | 'episode'

export interface Content {
  id: string
  title: string
  description: string
  content_type: ContentType
  duration_minutes: number
  release_date: string
  poster_url?: string
  banner_url?: string
  rating?: number
  genres: string[]
  cast: string[]
  directors: string[]
  created_at: string
  updated_at: string
}

export interface ContentCreate {
  title: string
  description: string
  content_type: ContentType
  duration_minutes: number
  release_date: string
  poster_url?: string
  banner_url?: string
  rating?: number
  genres?: string[]
  cast?: string[]
  directors?: string[]
}

export interface ContentListParams {
  content_type?: ContentType
  genre?: string
  skip?: number
  limit?: number
}

export const contentService = {
  async createContent(data: ContentCreate): Promise<Content> {
    const response = await api.post<Content>('/content/', data)
    return response.data
  },

  async getContent(id: string): Promise<Content> {
    const response = await api.get<Content>(`/content/${id}`)
    return response.data
  },

  async listContent(params?: ContentListParams): Promise<Content[]> {
    const response = await api.get<Content[]>('/content/', { params })
    return response.data
  },

  async updateContent(id: string, data: Partial<ContentCreate>): Promise<Content> {
    const response = await api.put<Content>(`/content/${id}`, data)
    return response.data
  },

  async deleteContent(id: string): Promise<void> {
    await api.delete(`/content/${id}`)
  },
}
