// 群聊 store
import { defineStore } from 'pinia'
import { wsClient } from '../utils/ws'
import api from '../utils/api'

export interface GroupMember {
  id: number
  type: 'ai' | 'human'
  name: string
  soul_id?: number
  user_id?: string
  role?: 'owner' | 'admin' | 'member'
}

export interface GroupMessage {
  id: number
  group_id: number
  sender_type: 'ai' | 'user'
  sender_name: string
  sender_id: string
  content: string
  voice_url?: string
  created_at: string
  is_merged?: boolean
}

export interface GroupChat {
  id: number
  name: string
  type: 'ai_only' | 'human_only' | 'mixed'
  creator_id: string
  created_at: string
  auto_delete_hours?: number
  announcement?: string
  members: GroupMember[]
}

export interface GroupInvitation {
  id: number
  group_id: number
  group_name: string
  inviter_id: string
  created_at: string
  expires_at: string
}

export const useGroupStore = defineStore('group', {
  state: () => ({
    // 群聊列表
    groups: [] as GroupChat[],
    currentGroupId: null as number | null,

    // 群消息
    messages: {} as Record<number, GroupMessage[]>,

    // 待处理邀请
    pendingInvitations: [] as GroupInvitation[],

    // 加载状态
    loading: false,
    error: null as string | null,
  }),

  getters: {
    currentGroup: (state) => {
      if (!state.currentGroupId) return null
      return state.groups.find(g => g.id === state.currentGroupId)
    },

    currentMessages: (state) => {
      if (!state.currentGroupId) return []
      return state.messages[state.currentGroupId] || []
    },
  },

  actions: {
    // ================== 群聊管理 ==================

    async createGroup(
      groupName: string,
      groupType: 'ai_only' | 'human_only' | 'mixed',
      aiSoulIds?: number[],
      humanUserIds?: string[],
      autoDeleteHours?: number
    ) {
      try {
        this.loading = true
        const res: any = await api.post('/api/groups', {
          group_name: groupName,
          group_type: groupType,
          ai_soul_ids: aiSoulIds,
          human_user_ids: humanUserIds,
          auto_delete_hours: autoDeleteHours,
        })

        this.groups.push(res)
        this.currentGroupId = res.id
        this.messages[res.id] = []
        return res
      } catch (e: any) {
        this.error = e?.response?.data?.detail || 'Failed to create group'
        throw e
      } finally {
        this.loading = false
      }
    },

    async loadGroups() {
      try {
        this.loading = true
        const res: any = await api.get('/api/groups')
        this.groups = res
      } catch (e: any) {
        this.error = e?.response?.data?.detail || 'Failed to load groups'
      } finally {
        this.loading = false
      }
    },

    async selectGroup(groupId: number) {
      this.currentGroupId = groupId
      await this.refreshGroup(groupId)
      await this.loadMessages(groupId)
    },

    // ================== 消息 ==================

    async sendMessage(groupId: number, content: string, voiceUrl?: string) {
      try {
        const res: any = await api.post(`/api/groups/${groupId}/messages`, {
          group_id: groupId,
          content,
          voice_url: voiceUrl,
        })

        // 不要在这里 push，等待 WebSocket 推送（避免重复）
        // 后端会通过 manager.push() 推送给所有群成员，前端 onGroupMessage 会处理
        return res
      } catch (e: any) {
        this.error = e?.response?.data?.detail || 'Failed to send message'
        throw e
      }
    },

    async loadMessages(groupId: number, limit = 50) {
      try {
        this.loading = true
        const res: any = await api.get(`/api/groups/${groupId}/messages?limit=${limit}`)
        this.messages[groupId] = res.messages
      } catch (e: any) {
        this.error = e?.response?.data?.detail || 'Failed to load messages'
      } finally {
        this.loading = false
      }
    },

    // ================== 邀请 ==================

    async inviteMember(groupId: number, inviteeId: string) {
      try {
        const res: any = await api.post(`/api/groups/${groupId}/invite`, {
          group_id: groupId,
          invitee_id: inviteeId,
        })
        return res
      } catch (e: any) {
        this.error = e?.response?.data?.detail || 'Failed to invite member'
        throw e
      }
    },

    async addMember(groupId: number, memberType: 'ai' | 'human', options: { soulId?: number; userId?: string }) {
      const res: any = await api.post(`/api/groups/${groupId}/members`, {
        member_type: memberType,
        soul_id: options.soulId,
        user_id: options.userId,
      })
      await this.refreshGroup(groupId)
      return res
    },

    async updateMember(groupId: number, memberId: number, role: 'admin' | 'member') {
      const res: any = await api.patch(`/api/groups/${groupId}/members/${memberId}`, {
        role,
      })
      await this.refreshGroup(groupId)
      return res
    },

    async removeMember(groupId: number, memberId: number) {
      const res: any = await api.delete(`/api/groups/${groupId}/members/${memberId}`)
      await this.refreshGroup(groupId)
      return res
    },

    async updateGroupSettings(groupId: number, settings: { groupName?: string; announcement?: string }) {
      const res: any = await api.patch(`/api/groups/${groupId}/settings`, {
        group_name: settings.groupName,
        announcement: settings.announcement,
      })
      const index = this.groups.findIndex(group => group.id === groupId)
      if (index >= 0) this.groups[index] = res
      return res
    },

    async refreshGroup(groupId: number) {
      const res: any = await api.get(`/api/groups/${groupId}`)
      const index = this.groups.findIndex(group => group.id === groupId)
      if (index >= 0) this.groups[index] = res
      else this.groups.push(res)
    },

    // ================== 批次3：群聊高级能力 ==================

    // 退群（成员主动退出）
    async leaveGroup(groupId: number) {
      const res: any = await api.delete(`/api/groups/${groupId}/leave`)
      this.groups = this.groups.filter(g => g.id !== groupId)
      if (this.currentGroupId === groupId) this.currentGroupId = null
      return res
    },

    // 转让群主（仅群主可操作，new_owner_member_id 为新群主的 members 记录 id）
    async transferOwner(groupId: number, newOwnerMemberId: number) {
      const res: any = await api.post(`/api/groups/${groupId}/transfer-owner`, {
        new_owner_member_id: newOwnerMemberId,
      })
      await this.refreshGroup(groupId)
      return res
    },

    // ---- 群记忆（仅群创建者可增删，成员可看） ----
    async listMemories(groupId: number, soulId: number) {
      const res: any = await api.get(`/api/groups/${groupId}/souls/${soulId}/memories`)
      return res?.memories ?? []
    },
    async addMemory(groupId: number, soulId: number, memoryType: string, content: string) {
      const res: any = await api.post(`/api/groups/${groupId}/souls/${soulId}/memories`, {
        memory_type: memoryType,
        content,
      })
      return res
    },
    async deleteMemory(groupId: number, soulId: number, memoryId: number) {
      await api.delete(`/api/groups/${groupId}/souls/${soulId}/memories/${memoryId}`)
    },

    // ---- 公告 ----
    async listAnnouncements(groupId: number) {
      const res: any = await api.get(`/api/groups/${groupId}/announcements`)
      return res?.announcements ?? []
    },
    async createAnnouncement(groupId: number, content: string) {
      const res: any = await api.post(`/api/groups/${groupId}/announcements`, { content })
      return res
    },
    async deleteAnnouncement(groupId: number, announcementId: number) {
      await api.delete(`/api/groups/${groupId}/announcements/${announcementId}`)
    },
    async toggleAnnouncementPin(groupId: number, announcementId: number, isPinned: boolean) {
      const res: any = await api.patch(
        `/api/groups/${groupId}/announcements/${announcementId}/pin`,
        null,
        { params: { is_pinned: isPinned } },
      )
      return res
    },

    // ---- 禁言 ----
    async muteMember(groupId: number, userId: string, durationMinutes: number) {
      const res: any = await api.post(
        `/api/groups/${groupId}/mute/${userId}`,
        null,
        { params: { duration_minutes: durationMinutes } },
      )
      return res
    },
    async unmuteMember(groupId: number, userId: string) {
      await api.delete(`/api/groups/${groupId}/mute/${userId}`)
    },
    async listMutedUsers(groupId: number) {
      const res: any = await api.get(`/api/groups/${groupId}/muted-users`)
      return res?.users ?? []
    },

    // ---- 群权限（仅群主可编辑，成员可查看） ----
    async listPermissions(groupId: number) {
      const res: any = await api.get(`/api/groups/${groupId}/permissions`)
      return res?.permissions ?? []
    },
    async updateRolePermissions(groupId: number, role: string, patch: any) {
      const res: any = await api.patch(`/api/groups/${groupId}/permissions/${role}`, patch)
      return res
    },

    async loadPendingInvitations() {
      try {
        const res: any = await api.get('/api/invitations/pending')
        this.pendingInvitations = res.invitations
      } catch (e: any) {
        this.error = e?.response?.data?.detail || 'Failed to load invitations'
      }
    },

    async respondToInvitation(invitationId: number, accept: boolean) {
      try {
        const res: any = await api.post(`/api/invitations/${invitationId}/respond`, {
          invitation_id: invitationId,
          accept,
        })

        // 移除该邀请
        this.pendingInvitations = this.pendingInvitations.filter(
          inv => inv.id !== invitationId
        )

        // 如果接受，重新加载群聊列表
        if (accept) {
          await this.loadGroups()
        }

        return res
      } catch (e: any) {
        this.error = e?.response?.data?.detail || 'Failed to respond to invitation'
        throw e
      }
    },

    // ================== WebSocket 事件 ==================

    onGroupMessage(data: any) {
      const { group_id, message } = data
      if (!this.messages[group_id]) {
        this.messages[group_id] = []
      }
      console.log(`📥 群 ${group_id} 收到消息 ${message.id}: ${message.content.slice(0, 20)}... (总共 ${this.messages[group_id].length + 1} 条)`)
      this.messages[group_id].push(message)
    },

    onGroupInvitation(data: any) {
      this.pendingInvitations.push(data)
    },

    initWs() {
      wsClient.on('group_message', (e) => this.onGroupMessage(e?.data))
      wsClient.on('group_invitation', (e) => this.onGroupInvitation(e?.data))
    },

    // ================== P1-16: @Mentions ==================

    async sendMessageWithMentions(
      groupId: number,
      content: string,
      mentionedUserIds?: string[],
      voiceUrl?: string
    ) {
      try {
        const res: any = await api.post(`/api/groups/${groupId}/messages`, {
          group_id: groupId,
          content,
          voice_url: voiceUrl,
          mentioned_user_ids: mentionedUserIds || [],
        })
        return res
      } catch (e: any) {
        this.error = e?.response?.data?.detail || 'Failed to send message'
        throw e
      }
    },
  },
})
