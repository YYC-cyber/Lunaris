import { defineStore } from 'pinia'
import api from '../utils/api'

export interface UserInfo {
  id: string
  username: string
  lunaris_id?: string
  gender: string
  nickname?: string
  avatar_url?: string
  api_granted_until?: string
  remaining_days?: number | null
  is_admin?: boolean
}

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: null as UserInfo | null,
    onlineUsers: new Set<string>(),
    blocks: [] as any[],
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
  },
  actions: {
    async login(username: string, password: string) {
      const res: any = await api.post('/api/auth/login', { username, password })
      this.token = res.token
      localStorage.setItem('token', res.token)
      await this.fetchMe()
    },
    async register(payload: { username: string; password: string; gender: string; nickname?: string }) {
      const res: any = await api.post('/api/auth/register', payload)
      this.token = res.token
      localStorage.setItem('token', res.token)
      await this.fetchMe()
    },
    async fetchMe() {
      const res: any = await api.get('/api/auth/me')
      this.user = res?.data ?? res ?? null
    },
    logout() {
      this.token = ''
      this.user = null
      this.onlineUsers.clear()
      localStorage.removeItem('token')
    },
    async fetchOnlineUsers() {
      try {
        const res: any = await api.get('/api/users/online')
        const userIds = Array.isArray(res) ? res : (res?.data ?? [])
        this.onlineUsers = new Set(userIds)
      } catch (e) {
        console.error('Failed to fetch online users:', e)
      }
    },
    updateUserStatus(userId: string, online: boolean) {
      if (online) {
        this.onlineUsers.add(userId)
      } else {
        this.onlineUsers.delete(userId)
      }
    },

    // ==================== 认证扩展（C 类接线） ====================
    async logoutServer() {
      try {
        await api.post('/api/auth/logout')
      } catch { /* 后端退出失败不阻断本地清理 */ }
      this.logout()
    },
    async refresh() {
      const res: any = await api.post('/api/auth/refresh')
      if (res?.token) {
        this.token = res.token
        localStorage.setItem('token', res.token)
      }
      return res
    },
    async changePassword(oldPassword: string, newPassword: string) {
      await api.post('/api/auth/change-password', { old_password: oldPassword, new_password: newPassword })
    },

    // ==================== 账户与资料 ====================
    async updateProfile(patch: { nickname?: string }) {
      const res: any = await api.post('/api/user/profile/update', patch)
      this.user = res?.data ?? res ?? this.user
      return res
    },
    async exportData() {
      return await api.get('/api/user/export-data')
    },
    async deleteAccount() {
      await api.post('/api/account/delete-permanently')
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
    },

    // ==================== 屏蔽管理 ====================
    async fetchBlocks() {
      const res: any = await api.get('/api/blocks')
      this.blocks = Array.isArray(res) ? res : (res?.data ?? res?.items ?? [])
    },
    async blockUser(userId: string) {
      await api.post(`/api/blocks/${userId}`)
      await this.fetchBlocks()
    },
    async unblockUser(userId: string) {
      await api.delete(`/api/blocks/${userId}`)
      await this.fetchBlocks()
    },
  },
})
