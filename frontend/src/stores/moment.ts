import { defineStore } from 'pinia'
import api from '../utils/api'
import { wsClient } from '../utils/ws'
import { notifyIfInactive } from '../utils/electron'

export interface Moment {
  id: number
  soul_id?: number | null
  user_id?: string | null
  soul_name?: string
  author_name?: string
  content: string
  images?: string[]
  topic_tags?: string[]
  visibility?: 'public' | 'friends' | 'private'
  like_count?: number
  is_liked?: boolean
  is_mine?: boolean
  created_at?: string
  comments?: any[]
}

export const useMomentStore = defineStore('moment', {
  state: () => ({
    timeline: [] as Moment[],
  }),
  actions: {
    async loadTimeline() {
      const res: any = await api.get('/api/moments', { params: { limit: 50, offset: 0 } })
      this.timeline = res?.data ?? res ?? []
    },

    async publish(content: string, images: string[], visibility: string, visibleGroups?: string[]) {
      const res: any = await api.post('/api/moments', {
        content,
        images,
        visibility,
        visible_groups: visibleGroups,
      })
      await this.loadTimeline()
      return res
    },

    async deleteMoment(m: Moment) {
      await api.delete(`/api/moments/${m.id}`)
      this.timeline = this.timeline.filter(item => item.id !== m.id)
    },

    async updateVisibility(m: Moment, visibility: 'public' | 'friends' | 'private') {
      const res: any = await api.patch(`/api/moments/${m.id}/visibility`, {
        visibility
      })
      m.visibility = visibility
      return res
    },

    async toggleLike(m: Moment) {
      const res: any = await api.post(`/api/moments/${m.id}/like`)
      m.is_liked = res.is_liked
      m.like_count = (m.like_count || 0) + (res.is_liked ? 1 : -1)
    },

    async comment(m: Moment, content: string) {
      await api.post(`/api/moments/${m.id}/comment`, { content })
      await this.loadTimeline()
    },

    initWs() {
      wsClient.on('moment', (e) => {
        this.loadTimeline()
        notifyIfInactive('新动态', String(e?.data?.content || '').slice(0, 30))
      })
    },
  },
})
