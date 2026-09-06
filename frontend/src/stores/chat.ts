import { defineStore } from 'pinia'
import api from '../utils/api'
import { wsClient } from '../utils/ws'
import { notifyIfInactive } from '../utils/electron'
import { stopVoice } from '../utils/ttsAudioPlayer'
import { useUserStore } from './user'

export interface Soul {
  id: number
  name: string
  display_name: string
  gender: string
  first_greeting?: string
  avatar_url?: string
  voice_id?: string
  tags?: string[]
  is_default?: boolean
}

export interface Friend {
  user_id: string
  lunaris_id?: string
  nickname?: string
  avatar_url?: string
}

export interface Message {
  id?: number
  sender_type: 'user' | 'ai'
  content?: string | null
  msg_type?: 'text' | 'image' | 'voice' | 'sticker'  // 消息类型
  emotion?: string
  created_at?: string
  image_url?: string  // 图片 URL（好友聊天）
  voice_url?: string
  original_text?: string  // 语音消息对应的原始文本（用户右键转文字）
  sticker_id?: number
  sticker_name?: string
  sticker_url?: string
  sticker_emotion?: string
  sticker_emoji?: string
  streaming?: boolean
  is_recalled?: boolean
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    // AI 伴侣聊天
    souls: [] as Soul[],
    currentSoulId: null as number | null,
    messages: {} as Record<number, Message[]>,
    unread: {} as Record<number, number>,
    aiTyping: {} as Record<number, boolean>,  // 记录每个 soul 是否正在输入
    // 真人好友聊天
    friends: [] as Friend[],
    conversations: [] as any[],
    currentFriendId: null as string | null,
    currentConvId: null as number | null,
    friendMessages: {} as Record<number, Message[]>,
    // 通用
    sending: false,
  }),
  getters: {
    currentSoul: (s) => s.souls.find((x) => x.id === s.currentSoulId) || null,
    currentMessages: (s) => (s.currentSoulId != null ? (s.messages[s.currentSoulId] || []) : []),
    currentFriend: (s) => s.friends.find((f) => f.user_id === s.currentFriendId) || null,
    currentFriendMessages: (s) => (s.currentConvId != null ? (s.friendMessages[s.currentConvId] || []) : []),
    isFriendChat: (s) => s.currentFriendId != null,
  },
  actions: {
    // ============ AI 伴侣 ============
    async loadSouls() {
      const res: any = await api.get('/api/souls/paired')
      this.souls = Array.isArray(res) ? res : (res?.data || [])
      if (!this.currentSoulId && !this.currentFriendId && this.souls.length) {
        this.currentSoulId = (this.souls.find((s) => s.is_default) || this.souls[0]).id
      }
    },
    selectSoul(id: number) {
      // 切换 AI 伴侣时停止正在播放的语音
      stopVoice()

      this.currentSoulId = id
      this.currentFriendId = null
      if (this.unread[id]) this.unread[id] = 0
    },
    async loadHistory(soulId: number) {
      const res: any = await api.get('/v1/chat/history', { params: { soul_id: soulId, offset: 0, limit: 50 } })
      const items = res?.data ?? res ?? []
      this.messages[soulId] = items.map((m: any) => ({
        id: m.message_id,
        sender_type: m.sender_type,
        content: m.content,
        emotion: m.emotion,
        created_at: m.created_at,
        sticker_id: m.sticker_id,
        sticker_name: m.sticker_name,
        sticker_url: m.sticker_url,
        sticker_emotion: m.sticker_emotion,
        sticker_emoji: m.sticker_emoji,
        voice_url: m.voice_url,
        original_text: m.original_text,
        is_recalled: m.is_recalled,
      }))
    },
    async clearHistory(soulId: number) {
      await api.delete('/v1/chat/history', { params: { soul_id: soulId } })
      this.messages[soulId] = []
    },
    async send(
      text: string,
      stickerId?: number,
      stream = false,
      stickerUrl?: string,
      stickerEmotion?: string,
      stickerEmoji?: string,
    ) {
      const soulId = this.currentSoulId
      if (!soulId) return
      this.messages[soulId] = this.messages[soulId] || []
      this.messages[soulId].push({
        sender_type: 'user',
        content: text,
        sticker_id: stickerId,
        sticker_emoji: stickerEmoji,
        sticker_url: stickerUrl,
        sticker_emotion: stickerEmotion,
      })
      this.sending = true
      try {
        const res: any = await api.post('/v1/chat/completions', {
          soul_id: soulId, message: text, sticker_id: stickerId, stream,
        })
        if (stream) {
          this.messages[soulId].push({ sender_type: 'ai', content: '', emotion: 'neutral', streaming: true })
        } else {
          this.messages[soulId].push({
            sender_type: 'ai',
            content: res.content,
            original_text: res.original_text,
            emotion: res.emotion,
            created_at: res.created_at,
            sticker_id: res.sticker_id,
            sticker_name: res.sticker_name,
            sticker_url: res.sticker_url,
            sticker_emotion: res.sticker_emotion,
            sticker_emoji: res.sticker_emoji,
            voice_url: res.voice_url,
          })
        }
      } catch {
        this.messages[soulId].push({ sender_type: 'ai', content: '（发送失败，请稍后再试）', emotion: 'neutral' })
      } finally {
        this.sending = false
      }
    },

    async sendWithVoice(
      text: string,
      voiceUrl: string,  // 用户发的语音 URL
      stream = false,
    ) {
      const soulId = this.currentSoulId
      if (!soulId) return
      this.messages[soulId] = this.messages[soulId] || []

      // 添加用户的语音消息
      this.messages[soulId].push({
        sender_type: 'user',
        content: text,
        original_text: text,
        voice_url: voiceUrl,  // 显示语音
      })

      this.sending = true
      try {
        // 发送消息时包含语音 URL
        const res: any = await api.post('/v1/chat/completions', {
          soul_id: soulId,
          message: text,  // 转写后的文字
          voice_url: voiceUrl,  // 用户的语音 URL
          stream,
        })

        if (stream) {
          this.messages[soulId].push({ sender_type: 'ai', content: '', emotion: 'neutral', streaming: true })
        } else {
          this.messages[soulId].push({
            sender_type: 'ai',
            content: res.content,
            original_text: res.original_text,
            emotion: res.emotion,
            created_at: res.created_at,
            voice_url: res.voice_url,  // AI 的回复语音
          })
        }
      } catch {
        this.messages[soulId].push({ sender_type: 'ai', content: '（发送失败，请稍后再试）', emotion: 'neutral' })
      } finally {
        this.sending = false
      }
    },

    // ============ 真人好友 ============
    async loadFriends() {
      const res: any = await api.get('/api/friends')
      this.friends = res?.data ?? res ?? []
    },
    async loadConversations() {
      const res: any = await api.get('/api/conversations')
      this.conversations = res?.data ?? []
    },
    async selectFriend(f: Friend) {
      // 切换好友时停止正在播放的语音
      stopVoice()

      this.currentFriendId = f.user_id
      this.currentSoulId = null
      await this.loadConversations()
      const conv = this.conversations.find((c) => c.other_user?.user_id === f.user_id)
      if (conv) {
        this.currentConvId = conv.conversation_id
        await this.loadFriendHistory(conv.conversation_id)
      } else {
        this.currentConvId = null
        this.friendMessages[0] = []
      }
    },
    async loadFriendHistory(convId: number) {
      const res: any = await api.get(`/api/conversations/${convId}/messages`)
      const items = res?.data ?? []
      const myId = useUserStore().user?.id
      this.friendMessages[convId] = items.map((m: any) => ({
        id: m.message_id,
        sender_type: m.sender_id === myId ? 'user' : 'ai',
        content: m.content,
        msg_type: m.msg_type,
        image_url: m.image_url,
        voice_url: m.voice_url,
      }))
    },
    async sendFriendMessage(content: string, stickerId?: number, imageUrl?: string, voiceUrl?: string) {
      if (!this.currentFriend) return

      let msgType: Message['msg_type'] = 'text'
      let msgContent = content

      if (imageUrl) {
        msgType = 'image'
        msgContent = content || '（分享了一张图片）'
      } else if (voiceUrl) {
        msgType = 'voice'
        msgContent = content || '（语音消息）'
      }

      const res: any = await api.post('/api/conversations', {
        user_id: this.currentFriend.user_id,
        content: msgContent,
        msg_type: msgType,
        image_url: imageUrl,
        voice_url: voiceUrl,
      })
      const msg = res.message
      const convId = msg.conversation_id
      this.currentConvId = convId
      this.friendMessages[convId] = this.friendMessages[convId] || []
      this.friendMessages[convId].push({
        id: msg.message_id,
        sender_type: 'user',
        content: msgContent,
        msg_type: msgType,
        image_url: imageUrl,
        voice_url: voiceUrl,
      })
      await this.loadConversations()
    },

    // ============ 流式 / WS ============
    onStreamChunk(e: any) {
      const target = this._findStreaming()
      if (target) target.content += (e?.data?.delta || '')
    },
    onStreamEnd(e: any) {
      const target = this._findStreaming()
      if (target) {
        target.content = e?.data?.full_content || target.content
        target.original_text = e?.data?.original_text
        target.voice_url = e?.data?.voice_url
        target.streaming = false
        target.emotion = e?.data?.emotion
      }
    },
    _findStreaming(): Message | null {
      for (const id of Object.keys(this.messages)) {
        const list = this.messages[Number(id)]
        for (let i = list.length - 1; i >= 0; i--) if (list[i].streaming) return list[i]
      }
      return null
    },
    onWsMessage(e: any) {
      const d = e?.data || {}
      const soulId = d.soul_id
      if (soulId != null && soulId !== this.currentSoulId) {
        this.unread[soulId] = (this.unread[soulId] || 0) + 1
        notifyIfInactive('新回复', String(d.content || '').slice(0, 30))
      }
    },
    onWsUserMessage(e: any) {
      const d = e?.data || {}
      const convId = d.conversation_id
      if (convId == null) return
      const myId = useUserStore().user?.id
      const isMine = d.sender_id === myId
      this.friendMessages[convId] = this.friendMessages[convId] || []
      this.friendMessages[convId].push({
        id: d.message_id,
        sender_type: isMine ? 'user' : 'ai',
        content: d.content,
        msg_type: d.msg_type,
        image_url: d.image_url,
        voice_url: d.voice_url,
      })
      if (convId !== this.currentConvId && !isMine) notifyIfInactive('新私信', String(d.content || '').slice(0, 30))
    },
    onTypingStart(e: any) {
      const soulId = e?.data?.soul_id
      if (soulId != null) {
        this.aiTyping[soulId] = true
      }
    },
    onTypingEnd(e: any) {
      const soulId = e?.data?.soul_id
      if (soulId != null) {
        this.aiTyping[soulId] = false
      }
    },
    initWs() {
      wsClient.on('message', (e) => this.onWsMessage(e))
      wsClient.on('stream_chunk', (e) => this.onStreamChunk(e))
      wsClient.on('stream_end', (e) => this.onStreamEnd(e))
      wsClient.on('user_message', (e) => this.onWsUserMessage(e))
      wsClient.on('typing_start', (e) => this.onTypingStart(e))
      wsClient.on('typing_end', (e) => this.onTypingEnd(e))
    },

    // ============ P1-01～03: 消息编辑、转发、收藏 ============
    async editMessage(messageId: number, newContent: string) {
      await api.patch(`/v1/chat/message/${messageId}`, { new_content: newContent })
      const soulId = this.currentSoulId
      if (soulId && this.messages[soulId]) {
        const msg = this.messages[soulId].find((m) => m.id === messageId)
        if (msg) msg.content = newContent
      }
    },

    async forwardMessage(messageId: number, targetUserId: string) {
      await api.post(`/v1/chat/message/${messageId}/forward`, {
        target_user_id: targetUserId,
      })
    },

    async addFavorite(messageId: number, category: string = '默认') {
      await api.post(`/v1/chat/message/${messageId}/favorite`, { category })
    },

    // P1-05: 举报消息
    async reportMessage(messageId: number, reason: string) {
      await api.post('/api/reports/create', {
        target_type: 'message',
        target_id: String(messageId),
        reason: reason || 'other',
        description: reason,
      })
    },

    async getRecentStickers(limit: number = 20) {
      const res: any = await api.get(`/api/stickers/recent?limit=${limit}`)
      return res?.data ?? res ?? []
    },

    // ============ TTS 语音合成（批次2：synthesize + voices） ============
    async synthesizeVoice(text: string, emotion: string = 'neutral', soulId?: number): Promise<string> {
      const res: any = await api.post('/api/voice/synthesize', {
        text,
        emotion,
        soul_id: soulId ?? this.currentSoulId ?? undefined,
      })
      return res?.url || ''
    },
    async listVoices() {
      const res: any = await api.get('/api/voice/voices')
      return res?.data ?? []
    },

    // ============ P2-01: 消息搜索 ============
    async searchMessages(query: string, startDate?: string, endDate?: string, senderId?: string, page: number = 1, pageSize: number = 20) {
      const params: any = { query, page, page_size: pageSize }
      if (startDate) params.start_date = startDate
      if (endDate) params.end_date = endDate
      if (senderId) params.sender_id = senderId
      const res: any = await api.get('/api/search/messages', { params })
      return res?.data ?? res ?? { items: [], total: 0, page, page_size: pageSize }
    },
  },
})
