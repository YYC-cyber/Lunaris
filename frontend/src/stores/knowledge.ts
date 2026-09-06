import { defineStore } from 'pinia'
import api from '../utils/api'

export interface KnowledgeDoc {
  id: number
  file_name: string
  file_type: string
  file_size?: number
  file_url?: string
  status: string // processing / ready / failed
  chunk_count?: number
  created_at?: string
}

export const useKnowledgeStore = defineStore('knowledge', {
  state: () => ({
    documents: [] as KnowledgeDoc[],
    loading: false,
    results: [] as any[],
    answer: '',
    asking: false,
  }),
  actions: {
    async loadDocuments() {
      this.loading = true
      try {
        const res: any = await api.get('/api/knowledge/documents')
        this.documents = Array.isArray(res) ? res : (res?.documents ?? [])
      } finally {
        this.loading = false
      }
    },
    async upload(file: File) {
      const fd = new FormData()
      fd.append('file', file)
      const res: any = await api.post('/api/knowledge/documents', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      await this.loadDocuments()
      return res
    },
    async remove(docId: number) {
      await api.delete(`/api/knowledge/documents/${docId}`)
      await this.loadDocuments()
    },
    async search(query: string) {
      const res: any = await api.get('/api/knowledge/search', { params: { query, limit: 5 } })
      this.results = Array.isArray(res) ? res : (res?.results ?? [])
    },
    async ask(query: string) {
      this.asking = true
      this.results = []
      try {
        const res: any = await api.post('/api/knowledge/ask', { query })
        this.answer = res?.answer ?? ''
        this.results = res?.sources ?? []
      } finally {
        this.asking = false
      }
    },
  },
})