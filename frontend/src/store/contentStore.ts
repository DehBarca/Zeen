import { create } from 'zustand'
import { Content, contentService, ContentListParams } from '../services/content'

interface ContentStore {
  contents: Content[]
  selectedContent: Content | null
  isLoading: boolean
  error: string | null
  
  // Actions
  listContents: (params?: ContentListParams) => Promise<void>
  getContent: (id: string) => Promise<void>
  setSelectedContent: (content: Content | null) => void
}

export const useContentStore = create<ContentStore>((set) => ({
  contents: [],
  selectedContent: null,
  isLoading: false,
  error: null,

  listContents: async (params?) => {
    set({ isLoading: true, error: null })
    try {
      const contents = await contentService.listContent(params)
      set({ contents, isLoading: false })
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to load contents'
      set({ error: errorMessage, isLoading: false })
      throw error
    }
  },

  getContent: async (id) => {
    set({ isLoading: true, error: null })
    try {
      const content = await contentService.getContent(id)
      set({ selectedContent: content, isLoading: false })
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to load content'
      set({ error: errorMessage, isLoading: false })
      throw error
    }
  },

  setSelectedContent: (content) => set({ selectedContent: content }),
}))
