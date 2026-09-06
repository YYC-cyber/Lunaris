<template>
  <div class="chat-window" :class="theme.className" :style="themeStyle">
    <div class="header">
      <div class="avatar">
        <img v-if="avatarUrl" :src="avatarUrl" alt="" />
        <span v-else>{{ title[0] || '?' }}</span>
      </div>
      <div class="identity">
        <div class="name">{{ title }}</div>
        <div v-if="!isFriend && currentSoul" class="role-line">
          <span>{{ theme.label }}</span>
          <span v-for="tag in currentSoul.tags?.slice(0, 2)" :key="tag" class="role-tag">{{ tag }}</span>
        </div>
      </div>
      <div class="spacer" />
      <el-button text @click="navigateToSearch" size="small" title="搜索消息">🔍</el-button>
      <el-button v-if="!isFriend" text type="danger" size="small" @click="clearHistory">清空记录</el-button>
    </div>

    <div v-if="!isFriend && currentSoul" class="companion-banner">
      <div class="banner-glow"></div>
      <div class="banner-copy">
        <span class="banner-kicker">{{ theme.kicker }}</span>
        <strong>{{ theme.greeting }}</strong>
      </div>
      <span class="banner-mark">{{ theme.mark }}</span>
    </div>

    <div ref="scrollRef" class="messages">
      <div v-for="(m, i) in msgs" :key="messageKey(m, i)">
        <MessageBubble :m="m" :show-time="shouldShowTime(i)" />
      </div>
      <!-- Typing 气泡 - AI 正在输入时显示 -->
      <div v-if="isAiTyping" class="typing-container">
        <TypingBubble />
      </div>
      <div v-if="!msgs.length && !isAiTyping" class="empty-hint">{{ emptyHint }}</div>
    </div>
    <InputArea />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useChatStore } from '../../stores/chat'
import MessageBubble from './MessageBubble.vue'
import InputArea from './InputArea.vue'
import TypingBubble from '../common/TypingBubble.vue'

const router = useRouter()
const chat = useChatStore()
const scrollRef = ref<HTMLElement>()

const isFriend = computed(() => chat.isFriendChat)
const currentSoul = computed(() => chat.currentSoul)
const title = computed(() =>
  isFriend.value
    ? (chat.currentFriend?.nickname || chat.currentFriend?.lunaris_id || '好友')
    : (chat.currentSoul?.display_name || '请选择聊天对象')
)
const avatarUrl = computed(() =>
  isFriend.value
    ? (chat.currentFriend?.avatar_url || '')
    : (currentSoul.value?.avatar_url || '')
)
const theme = computed(() => {
  const name = currentSoul.value?.name?.toLowerCase() || ''
  const themes: Record<string, {
    className: string
    label: string
    kicker: string
    greeting: string
    mark: string
    primary: string
    secondary: string
    surface: string
    bubble: string
    banner: string
  }> = {
    diana: {
      className: 'theme-diana',
      label: '音乐与灵感',
      kicker: '今晚的旋律',
      greeting: '把心事交给一段音乐。',
      mark: '♫',
      primary: '#9274b4',
      secondary: '#caa5c8',
      surface: '#f0e7f2',
      bubble: '#ead9ed',
      banner: 'linear-gradient(135deg, #5e4a76, #a783ad)',
    },
    raven: {
      className: 'theme-raven',
      label: '夜色与观察',
      kicker: '安静的夜',
      greeting: '慢一点，也能看见更多。',
      mark: '✦',
      primary: '#637891',
      secondary: '#9baec3',
      surface: '#e5ebf0',
      bubble: '#d9e3ec',
      banner: 'linear-gradient(135deg, #35485f, #71879c)',
    },
    luna: {
      className: 'theme-luna',
      label: '月光与陪伴',
      kicker: '月亮在线',
      greeting: '今天也留一点温柔给自己。',
      mark: '☾',
      primary: '#7f86b8',
      secondary: '#c0bce0',
      surface: '#e8e8f5',
      bubble: '#e0def2',
      banner: 'linear-gradient(135deg, #535d91, #9a9bca)',
    },
    elara: {
      className: 'theme-elara',
      label: '温度与日常',
      kicker: '今日小记',
      greeting: '平凡的日子，也值得被记住。',
      mark: '✿',
      primary: '#b07f78',
      secondary: '#d9ada0',
      surface: '#f3e8e2',
      bubble: '#f0ddd8',
      banner: 'linear-gradient(135deg, #78534f, #b98578)',
    },
  }
  return themes[name] || {
    className: 'theme-default',
    label: 'AI 伴侣',
    kicker: '正在陪伴',
    greeting: currentSoul.value?.first_greeting || '和我聊聊今天吧。',
    mark: '·',
    primary: '#9b7ba9',
    secondary: '#d4a5d4',
    surface: '#f0e8f2',
    bubble: '#eadcf0',
    banner: 'linear-gradient(135deg, #665174, #af88b3)',
  }
})
const themeStyle = computed(() => ({
  '--companion-primary': theme.value.primary,
  '--companion-secondary': theme.value.secondary,
  '--companion-surface': theme.value.surface,
  '--companion-bubble': theme.value.bubble,
  '--companion-banner': theme.value.banner,
}))
const msgs = computed(() => (isFriend.value ? chat.currentFriendMessages : chat.currentMessages))
const isAiTyping = computed(() => {
  if (isFriend.value || !chat.currentSoulId) return false
  return chat.aiTyping[chat.currentSoulId] || false
})
const emptyHint = computed(() =>
  isFriend.value ? '和好友打个招呼吧' : (chat.currentSoul?.first_greeting || '开始聊天吧')
)

function shouldShowTime(index: number): boolean {
  if (index === 0) return true

  const current = msgs.value[index]
  const prev = msgs.value[index - 1]

  if (!current?.created_at || !prev?.created_at) return false

  const currentTime = new Date(current.created_at).getTime()
  const prevTime = new Date(prev.created_at).getTime()

  return (currentTime - prevTime) > 5 * 60 * 1000
}

function messageKey(message: { id?: number; sender_type: string; created_at?: string; content?: string | null; sticker_id?: number }, index: number): string | number {
  return message.id ?? `${message.sender_type}:${message.created_at || 'pending'}:${message.sticker_id || ''}:${message.content}:${index}`
}

watch(
  () => chat.currentSoulId,
  async (id) => {
    if (id != null) await chat.loadHistory(id)
    scrollToBottom()
  },
  { immediate: true }
)

watch(
  () => [chat.currentMessages.length, chat.currentFriendMessages.length, isAiTyping.value],
  () => scrollToBottom()
)

function scrollToBottom() {
  nextTick(() => {
    if (scrollRef.value) scrollRef.value.scrollTop = scrollRef.value.scrollHeight
  })
}

function navigateToSearch() {
  router.push('/search')
}

function clearHistory() {
  const soulId = chat.currentSoulId
  if (soulId == null) return
  ElMessageBox.confirm('确定清空与该角色的聊天记录吗？', '提示', { type: 'warning' })
    .then(async () => {
      await chat.clearHistory(soulId)
      ElMessage.success('已清空')
    })
    .catch(() => {})
}
</script>

<style scoped>
.chat-window {
  flex: 1;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(circle at 80% 0%, color-mix(in srgb, var(--companion-secondary) 22%, transparent), transparent 32%),
    var(--color-bg-gradient);
}

.header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: color-mix(in srgb, var(--companion-surface) 52%, transparent);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(212, 165, 212, 0.1);
  box-shadow: var(--shadow-soft);
}

.avatar {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-card);
  background: linear-gradient(135deg, var(--companion-primary), var(--companion-secondary));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  box-shadow: var(--shadow-soft);
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.identity {
  min-width: 0;
}

.name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.role-line {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 3px;
  color: var(--companion-primary);
  font-size: 11px;
}

.role-tag {
  padding: 2px 6px;
  border-radius: 5px;
  background: color-mix(in srgb, var(--companion-secondary) 30%, transparent);
  color: var(--color-text-secondary);
}

.spacer { flex: 1; }

.companion-banner {
  position: relative;
  min-height: 72px;
  margin: 10px 14px 0;
  padding: 14px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  overflow: hidden;
  border-radius: 8px;
  color: #fff;
  background: var(--companion-banner);
  box-shadow: 0 10px 24px color-mix(in srgb, var(--companion-primary) 28%, transparent);
}

.banner-glow {
  position: absolute;
  width: 130px;
  height: 130px;
  right: 30px;
  top: -70px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
}

.banner-copy,
.banner-mark {
  position: relative;
  z-index: 1;
}

.banner-copy {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.banner-kicker {
  font-size: 11px;
  opacity: 0.72;
}

.banner-copy strong {
  font-size: 14px;
  font-weight: 600;
}

.banner-mark {
  font-size: 30px;
  opacity: 0.82;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  background: color-mix(in srgb, var(--companion-surface) 18%, transparent);
}

.empty-hint {
  text-align: center;
  color: var(--color-text-light);
  margin-top: 40px;
  font-size: 14px;
}

.typing-container {
  margin: 6px 12px;
  display: flex;
  flex-direction: column;
}

:global(:root.dark) .chat-window {
  background:
    radial-gradient(circle at 80% 0%, color-mix(in srgb, var(--companion-primary) 18%, transparent), transparent 34%),
    var(--color-bg-gradient);
}

@media (max-width: 640px) {
  .companion-banner {
    margin: 8px 10px 0;
  }
}
</style>
