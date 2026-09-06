<template>
  <div class="msg-group">
    <!-- 时间分隔线 -->
    <div v-if="showTime" class="time-divider">
      {{ formatTime(message.created_at) }}
    </div>

    <!-- 消息项 -->
    <div class="msg-item" :class="{ 'is-mine': isMine }">
      <!-- 头像 + 发言人信息 -->
      <div class="msg-header">
        <div class="avatar" :class="{ ai: message.sender_type === 'ai' }">
          {{ message.sender_type === 'ai' ? message.sender_name[0] : '👤' }}
        </div>
        <div class="sender-info">
          <div class="sender-name">{{ message.sender_name }}</div>
          <div class="sender-time">{{ formatTime(message.created_at, 'HH:mm') }}</div>
        </div>
      </div>

      <!-- 气泡内容 -->
      <div
        v-if="message.voice_url"
        class="bubble voice-bubble"
        :class="[message.sender_type, { expired: isExpired }]"
      >
        <VoiceMessage :url="message.voice_url" :message-id="message.id" />
      </div>
      <div
        v-else
        class="bubble"
        :class="[message.sender_type, { expired: isExpired }]"
        @contextmenu.prevent="showContextMenu = true"
        @touchstart="onTouchStart"
        @touchend="onTouchEnd"
      >
        <span v-html="highlightMentions(message.content)"></span>
      </div>

      <!-- Context Menu -->
      <div
        v-if="showContextMenu"
        class="message-context-menu"
        :style="{ left: `${contextMenuX}px`, top: `${contextMenuY}px` }"
        @click.stop
      >
        <div class="context-menu-item" @click="handleReport">
          🚩 举报
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useUserStore } from '../../stores/user'
import VoiceMessage from './VoiceMessage.vue'

interface Message {
  id: number
  group_id: number
  sender_type: 'ai' | 'user'
  sender_name: string
  sender_id: string
  content: string
  voice_url?: string
  created_at: string
  is_merged?: boolean
  is_deleted?: boolean
  expires_at?: string
}

interface Props {
  message: Message
  showTime?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showTime: false,
})

const user = useUserStore()
const showContextMenu = ref(false)
const contextMenuX = ref(0)
const contextMenuY = ref(0)
let touchStartTime = 0
let touchStartX = 0
let touchStartY = 0

const isMine = computed(() => {
  if (props.message.sender_type !== 'user') return false
  const currentUser = user.user
  if (!currentUser) return false

  const senderId = String(props.message.sender_id || '')
  if (senderId && String(currentUser.id || '') === senderId) return true

  const senderName = String(props.message.sender_name || '')
  return Boolean(senderName) && [
    currentUser.nickname,
    currentUser.username,
    currentUser.lunaris_id,
  ].filter(Boolean).some((name) => String(name) === senderName)
})

const isExpired = computed(() => {
  return props.message.content === '[消息已过期]' || props.message.is_deleted
})

function formatTime(time: string, format: string = 'MM-dd'): string {
  const date = new Date(time)
  if (format === 'HH:mm') {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
  }
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

function highlightMentions(content: string): string {
  if (!content) return ''
  return content.replace(/@([^\s@]+)/g, '<span class="mention">@$1</span>')
}

function onTouchStart(e: TouchEvent) {
  touchStartTime = Date.now()
  touchStartX = e.touches[0].clientX
  touchStartY = e.touches[0].clientY
}

function onTouchEnd(e: TouchEvent) {
  const duration = Date.now() - touchStartTime
  const moveX = Math.abs(e.changedTouches[0].clientX - touchStartX)
  const moveY = Math.abs(e.changedTouches[0].clientY - touchStartY)

  if (duration > 500 && moveX < 10 && moveY < 10) {
    const touch = e.changedTouches[0]
    contextMenuX.value = touch.clientX
    contextMenuY.value = touch.clientY
    showContextMenu.value = true
  }
}

function hideContextMenu() {
  showContextMenu.value = false
}

function handleReport() {
  hideContextMenu()
  // TODO: Implement report dialog
}

document.addEventListener('click', () => {
  hideContextMenu()
})
</script>

<style scoped>
.msg-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.time-divider {
  text-align: center;
  font-size: 12px;
  color: var(--color-text-light);
  margin: 8px 0 12px 0;
}

.msg-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 4px;
  position: relative;
  width: 100%;
  justify-content: flex-start;
}

.msg-item.is-mine {
  flex-direction: row-reverse;
  justify-content: flex-start;
}

.msg-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  min-width: 40px;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-card);
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
  font-size: 14px;
  flex-shrink: 0;
}

.avatar.ai {
  background: linear-gradient(135deg, #E8D4F1 0%, #F5D5E3 100%);
}

.sender-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  font-size: 10px;
  color: var(--color-text-light);
  gap: 1px;
}

.sender-name {
  font-weight: 500;
  color: var(--color-text-secondary);
  max-width: 50px;
  text-align: center;
  word-break: break-all;
}

.sender-time {
  font-size: 9px;
}

.bubble {
  max-width: 280px;
  padding: 8px 12px;
  border-radius: var(--radius-bubble);
  word-break: break-word;
  line-height: 1.5;
  font-size: 14px;
}

.msg-item.is-mine .bubble {
  text-align: left;
}

.bubble.ai {
  background: var(--color-ai-gradient);
  color: var(--color-text-primary);
}

.bubble.user {
  background: var(--color-user);
  color: var(--color-text-primary);
}

.bubble.expired {
  background: var(--color-border);
  color: var(--color-text-light);
  opacity: 0.6;
  font-style: italic;
}

.mention {
  color: #d17ba8;
  font-weight: 600;
  background: rgba(209, 123, 168, 0.1);
  border-radius: 2px;
  padding: 0 2px;
}

.message-context-menu {
  position: fixed;
  z-index: 1000;
  min-width: 100px;
  padding: 4px;
  background: var(--color-bg, #fff);
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 6px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.16);
}

.context-menu-item {
  padding: 8px 12px;
  border: 0;
  background: transparent;
  color: var(--color-text, #333);
  text-align: left;
  cursor: pointer;
  border-radius: 4px;
  font-size: 13px;
  transition: all 0.2s;
}

.context-menu-item:hover {
  background: rgba(212, 165, 212, 0.16);
}
</style>
