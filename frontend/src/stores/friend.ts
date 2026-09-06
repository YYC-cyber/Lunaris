import { defineStore } from 'pinia'
import api from '../utils/api'

export interface Friend {
  user_id: string
  lunaris_id?: string
  nickname?: string
  avatar_url?: string
}

export const useFriendStore = defineStore('friend', {
  state: () => ({
    friends: [] as Friend[],
    requests: [] as any[],
  }),
  actions: {
    async loadFriends() {
      const res: any = await api.get('/api/friends')
      this.friends = res?.data ?? res ?? []
    },
    async loadRequests() {
      const res: any = await api.get('/api/friends/requests')
      this.requests = res?.data ?? res ?? []
    },
    async search(lunarisId: string) {
      const res: any = await api.get('/api/friends/search', { params: { lunaris_id: lunarisId } })
      return res
    },
    async sendRequest(lunarisId: string) {
      return await api.post('/api/friends/request', { lunaris_id: lunarisId })
    },
    async handleRequest(userId: string, action: 'accept' | 'reject') {
      await api.post('/api/friends/request/handle', { user_id: userId, action })
      await this.loadRequests()
      await this.loadFriends()
    },
    async removeFriend(userId: string) {
      await api.delete(`/api/friends/${userId}`)
      await this.loadFriends()
    },

    // ============ P2-07: 高级搜索 ============
    async advancedSearch(filters: { keyword?: string; gender?: string; minAge?: number; maxAge?: number; sortBy?: string }) {
      const res: any = await api.get('/api/friends/search', { params: filters })
      return res?.data ?? res ?? []
    },
  },
})
