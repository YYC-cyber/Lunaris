<template>
  <div class="msg-wrapper">
    <div v-if="showTime" class="time-divider">{{ formatTime(m.created_at) }}</div>
    <div class="msg" :class="m.sender_type">
      <div class="message-avatar" :class="m.sender_type">
        <img v-if="avatarUrl" :src="avatarUrl" alt="" />
        <span v-else>{{ avatarText }}</span>
      </div>
      <div v-if="m.is_recalled" class="recalled">消息已撤回</div>
      <div
        v-else-if="m.voice_url"
        class="voice-message"
        :class="m.sender_type"
        @contextmenu.prevent="showContextMenu = true"
        @touchstart="onTouchStart"
        @touchend="onTouchEnd"
      >
        <VoiceMessage
          :url="m.voice_url"
          :original-text="m.original_text"
          :text-visible="showVoiceText"
          @show-text="onShowVoiceText"
          @hide-text="showVoiceText = false"
        />
        <div v-if="showVoiceText" class="bubble voice-text" :class="m.sender_type">
          <span>{{ voiceText || m.content }}</span>
        </div>
      </div>
      <div
        v-else-if="m.msg_type === 'image' && m.image_url"
        class="image-message"
        :class="m.sender_type"
        @contextmenu.prevent="showContextMenu = true"
        @touchstart="onTouchStart"
        @touchend="onTouchEnd"
      >
        <img
          class="message-image"
          :src="m.image_url"
          alt="图片"
          @error="onImageError"
        />
        <p v-if="m.content" class="image-caption">{{ m.content }}</p>
      </div>
      <div
        v-else-if="m.sticker_id != null || m.sticker_url || m.sticker_emoji"
        class="sticker-message"
        :class="m.sender_type"
        @contextmenu.prevent="showContextMenu = true"
        @touchstart="onTouchStart"
        @touchend="onTouchEnd"
      >
        <img
          v-if="isStickerImage(m.sticker_url) && !m.sticker_emoji && !stickerImageFailed"
          class="sticker"
          :src="m.sticker_url"
          alt="表情"
          @error="stickerImageFailed = true"
        />
        <span v-else class="sticker-emoji">{{ stickerEmoji }}</span>
      </div>
      <div
        v-else
        class="bubble"
        :class="m.sender_type"
        @contextmenu.prevent="showContextMenu = true"
        @touchstart="onTouchStart"
        @touchend="onTouchEnd"
      >
        <span v-if="isEditing" class="edit-mode">
          <el-input
            v-model="editingContent"
            @keyup.escape="cancelEdit"
            @keyup.enter="submitEdit"
            clearable
            autofocus
          />
        </span>
        <span v-else>{{ m.content }}<i v-if="m.streaming" class="cursor">▌</i></span>
        <button
          v-if="canSpeak"
          class="speak-btn"
          :class="{ speaking }"
          :disabled="speaking"
          :title="speaking ? '停止朗读' : '语音朗读'"
          :aria-label="speaking ? '停止朗读' : '语音朗读'"
          @click.stop="toggleSpeak"
        >
          {{ speaking ? '⏹' : '🔊' }}
        </button>
      </div>

      <!-- Context Menu -->
      <div
        v-if="showContextMenu"
        class="message-context-menu"
        :style="{ left: `${contextMenuX}px`, top: `${contextMenuY}px` }"
        role="menu"
        aria-label="消息操作菜单"
        @click.stop
      >
        <div
          v-if="m.voice_url"
          class="context-menu-item"
          role="menuitem"
          tabindex="0"
          @click="handleTranscribe"
          @keydown.enter="handleTranscribe"
        >
          Aa 转文字
        </div>
        <div
          v-if="canForward"
          class="context-menu-item"
          role="menuitem"
          tabindex="0"
          @click="handleForward"
          @keydown.enter="handleForward"
        >
          ➜ 转发
        </div>
        <div
          class="context-menu-item"
          role="menuitem"
          tabindex="0"
          @click="handleFavorite"
          @keydown.enter="handleFavorite"
        >
          ⭐ 收藏
        </div>
        <div
          class="context-menu-item"
          role="menuitem"
          tabindex="0"
          @click="handleReport"
          @keydown.enter="handleReport"
        >
          🚩 举报
        </div>
        <div
          v-if="canEdit"
          class="context-menu-item"
          role="menuitem"
          tabindex="0"
          @click="handleEdit"
          @keydown.enter="handleEdit"
        >
          ✏️ 编辑
        </div>
      </div>
    </div>

    <el-dialog v-model="showForwardDialog" title="转发给站内好友" width="380px">
      <div v-if="chat.friends.length" class="forward-friends">
        <button
          v-for="friend in chat.friends"
          :key="friend.user_id"
          class="forward-friend"
          :class="{ selected: forwardTargetId === friend.user_id }"
          @click="forwardTargetId = friend.user_id"
        >
          <span class="forward-avatar">{{ friend.nickname?.[0] || friend.lunaris_id?.[0] || '友' }}</span>
          <span>{{ friend.nickname || friend.lunaris_id }}</span>
        </button>
      </div>
      <el-empty v-else description="暂无站内好友，不能转发" />
      <template #footer>
        <el-button @click="showForwardDialog = false">取消</el-button>
        <el-button type="primary" :loading="forwarding" :disabled="!forwardTargetId" @click="submitForward">
          转发
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showReportDialog" title="举报消息" width="420px">
      <el-form label-position="top">
        <el-form-item label="举报原因">
          <el-select v-model="reportReason" style="width: 100%">
            <el-option label="骚扰、辱骂或人身攻击" value="harassment" />
            <el-option label="垃圾信息或广告" value="spam" />
            <el-option label="暴力、恐怖或危险内容" value="violence" />
            <el-option label="违法内容" value="illegal" />
            <el-option label="成人内容" value="adult" />
            <el-option label="诈骗或诱导转账" value="scam" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="补充说明">
          <el-input v-model="reportDescription" type="textarea" :rows="3" maxlength="500" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showReportDialog = false">取消</el-button>
        <el-button type="danger" :loading="reporting" @click="submitReport">提交举报</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import type { Message } from '../../stores/chat'
import VoiceMessage from './VoiceMessage.vue'
import { formatRelativeTime } from '../../utils/time'
import { isStickerImage, stickerFallbackEmoji } from '../../utils/sticker'
import { cleanVoiceText } from '../../utils/voice'
import { computed, ref, watch, onUnmounted } from 'vue'
import { useChatStore } from '../../stores/chat'
import { useUserStore } from '../../stores/user'
import { ElMessage } from 'element-plus'
import api from '../../utils/api'
import { getAudioExtension } from '../../utils/voice'
import { resolveApiUrl } from '../../config'
import { playVoice, stopVoice } from '../../utils/ttsAudioPlayer'

interface Props {
  m: Message
  showTime?: boolean
}

const props = defineProps<Props>()
const chat = useChatStore()
const user = useUserStore()

const stickerImageFailed = ref(false)
const showVoiceText = ref(false)
const voiceText = ref(cleanVoiceText(props.m.original_text))
const showContextMenu = ref(false)
const contextMenuX = ref(0)
const contextMenuY = ref(0)
const isEditing = ref(false)
const editingContent = ref(props.m.content || '')
const showForwardDialog = ref(false)
const forwardTargetId = ref('')
const forwarding = ref(false)
const showReportDialog = ref(false)
const reportReason = ref('other')
const reportDescription = ref('')
const reporting = ref(false)
let touchStartTime = 0
let touchStartX = 0
let touchStartY = 0

const stickerEmoji = computed(() => {
  if (props.m.sticker_emoji) return props.m.sticker_emoji
  if (!isStickerImage(props.m.sticker_url)) {
    return props.m.sticker_url || stickerFallbackEmoji(props.m.sticker_emotion || props.m.emotion, props.m.sticker_name)
  }
  return stickerFallbackEmoji(props.m.sticker_emotion || props.m.emotion, props.m.sticker_name)
})

const isUserMessage = computed(() => props.m.sender_type === 'user')
const isWithin15Min = computed(() => {
  if (!props.m.created_at) return false
  const createdTime = new Date(props.m.created_at).getTime()
  const now = Date.now()
  return (now - createdTime) < 15 * 60 * 1000
})

const canEdit = computed(() => isUserMessage.value && isWithin15Min.value && !props.m.is_recalled)
const canForward = computed(() => !props.m.is_recalled && props.m.content)
const isMine = computed(() => props.m.sender_type === 'user')

// 批次2：AI 文本消息可语音朗读（仅当无自带语音、非撤回、非编辑、非流式中）
const speaking = ref(false)
const canSpeak = computed(() => {
  if (props.m.sender_type !== 'ai') return false
  if (props.m.is_recalled || props.m.streaming || props.m.voice_url || isEditing.value) return false
  return !!(props.m.content || '').trim()
})
async function toggleSpeak() {
  const text = (props.m.content || '').trim()
  if (!text) return
  if (speaking.value) {
    stopVoice()
    speaking.value = false
    return
  }
  speaking.value = true
  try {
    const url = await chat.synthesizeVoice(text, props.m.emotion || 'neutral')
    if (!url) throw new Error('语音合成失败')
    await playVoice(url)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '语音朗读失败')
  } finally {
    speaking.value = false
  }
}
onUnmounted(() => {
  if (speaking.value) stopVoice()
})
const avatarUrl = computed(() => {
  if (isMine.value) return user.user?.avatar_url || ''
  return chat.isFriendChat ? (chat.currentFriend?.avatar_url || '') : (chat.currentSoul?.avatar_url || '')
})
const avatarText = computed(() => {
  if (isMine.value) return user.user?.nickname?.[0] || user.user?.username?.[0] || user.user?.lunaris_id?.[0] || '我'
  if (chat.isFriendChat) return chat.currentFriend?.nickname?.[0] || chat.currentFriend?.lunaris_id?.[0] || '友'
  return chat.currentSoul?.display_name?.[0] || 'AI'
})

watch(
  () => props.m.sticker_url,
  () => { stickerImageFailed.value = false },
)

function onShowVoiceText(text: string) {
  if (text) {
    voiceText.value = text
    showVoiceText.value = true
  }
}

watch(
  () => props.m.voice_url,
  () => {
    showVoiceText.value = false
    voiceText.value = cleanVoiceText(props.m.original_text)
  },
)

watch(
  () => props.m.original_text,
  (text) => {
    if (text && !voiceText.value) voiceText.value = cleanVoiceText(text)
  },
)

function formatTime(isoString?: string): string {
  if (!isoString) return ''
  return formatRelativeTime(isoString)
}

function onImageError() {
  // 图片加载失败时的处理
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

async function handleForward() {
  hideContextMenu()
  if (!props.m.id) return
  forwardTargetId.value = ''
  showForwardDialog.value = true
}

async function submitForward() {
  if (!props.m.id || !forwardTargetId.value) return
  forwarding.value = true
  try {
    await chat.forwardMessage(props.m.id, forwardTargetId.value)
    ElMessage.success('已转发给好友')
    showForwardDialog.value = false
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '转发失败')
  } finally {
    forwarding.value = false
  }
}

async function handleFavorite() {
  hideContextMenu()
  try {
    if (!props.m.id) return
    await chat.addFavorite(props.m.id, '默认')
    ElMessage.success('已收藏')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '收藏失败')
  }
}

async function handleReport() {
  hideContextMenu()
  if (!props.m.id) return
  reportReason.value = 'other'
  reportDescription.value = ''
  showReportDialog.value = true
}

async function submitReport() {
  if (!props.m.id) return
  reporting.value = true
  try {
    await api.post('/api/reports/create', {
      target_type: 'message',
      target_id: props.m.id,
      reason: reportReason.value,
      description: reportDescription.value.trim() || null,
    })
    ElMessage.success('举报已提交，等待审核')
    showReportDialog.value = false
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '举报提交失败')
  } finally {
    reporting.value = false
  }
}

async function handleTranscribe() {
  hideContextMenu()
  if (!props.m.voice_url) return
  try {
    const response = await fetch(resolveApiUrl(props.m.voice_url))
    if (!response.ok) throw new Error('音频加载失败')
    const blob = await response.blob()
    const form = new FormData()
    form.append('file', blob, `voice.${getAudioExtension(blob)}`)
    const result: any = await api.post('/api/voice/transcribe', form)
    const text = String(result?.text || '').trim()
    if (!text) {
      ElMessage.warning('未识别到语音内容')
      return
    }
    props.m.original_text = text
    showVoiceText.value = true
    voiceText.value = text
    ElMessage.success('语音转写成功')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '语音转写失败')
  }
}

function handleEdit() {
  hideContextMenu()
  if (canEdit.value) {
    isEditing.value = true
    editingContent.value = props.m.content || ''
  }
}

async function submitEdit() {
  try {
    if (!props.m.id || !editingContent.value.trim()) {
      ElMessage.warning('内容不能为空')
      return
    }
    await chat.editMessage(props.m.id, editingContent.value.trim())
    isEditing.value = false
    ElMessage.success('编辑成功')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '编辑失败')
  }
}

function cancelEdit() {
  isEditing.value = false
  editingContent.value = ''
}

// Close menu when clicking outside
document.addEventListener('click', () => {
  hideContextMenu()
})
</script>

<style scoped>
.msg-wrapper {
  margin: 6px 12px;
  display: flex;
  flex-direction: column;
}

.time-divider {
  font-size: 12px;
  color: var(--color-text-light);
  text-align: center;
  margin: 14px 0 10px 0;
  padding: 0 8px;
}

.msg {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  position: relative;
}

.msg.user {
  flex-direction: row-reverse;
  justify-content: flex-start;
}

.msg.ai {
  justify-content: flex-start;
}

.message-avatar {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-card);
  background: rgba(212, 165, 212, 0.22);
  color: var(--color-text-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
  box-shadow: var(--shadow-soft);
}

.message-avatar.user {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%);
  color: #fff;
}

.message-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.recalled {
  padding: 10px 14px;
  background: rgba(212, 165, 212, 0.08);
  border-radius: var(--radius-bubble);
  color: var(--color-text-light);
  font-size: 12px;
  font-style: italic;
  border-left: 2px solid rgba(212, 165, 212, 0.3);
}

.voice-message {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}

.voice-message.user,
.image-message.user {
  align-items: flex-end;
}

.bubble.voice-text {
  background: rgba(212, 165, 212, 0.12);
  border: 1px solid rgba(212, 165, 212, 0.3);
  font-size: 13px;
  max-width: 300px;
}

.sticker-message {
  display: flex;
}

.image-message {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-width: 280px;
}

.message-image {
  max-width: 100%;
  max-height: 300px;
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-soft);
  display: block;
  object-fit: contain;
  cursor: pointer;
  transition: all 0.2s ease;
}

.message-image:hover {
  box-shadow: var(--shadow-medium);
}

.image-caption {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin: 0;
  padding: 4px 8px;
  background: rgba(212, 165, 212, 0.05);
  border-radius: 4px;
}

.image-message.user .image-caption {
  text-align: right;
}

.sticker {
  max-width: 120px;
  max-height: 120px;
  display: block;
  object-fit: contain;
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-soft);
}

.sticker-emoji {
  display: block;
  font-family: "Apple Color Emoji", "Segoe UI Emoji", sans-serif;
  font-size: 56px;
  line-height: 1;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.08));
}

.bubble {
  max-width: 320px;
  padding: 10px 14px;
  border-radius: var(--radius-bubble);
  word-break: break-word;
  line-height: 1.5;
  background: color-mix(in srgb, var(--companion-bubble, #eadcf0) 74%, transparent);
  color: var(--color-text-primary);
}

.bubble.user {
  background: linear-gradient(135deg, var(--companion-primary, var(--color-primary)) 0%, var(--companion-secondary, var(--color-secondary)) 100%);
  color: #fff;
}

.bubble.ai {
  background: color-mix(in srgb, var(--companion-bubble, #eadcf0) 78%, transparent);
}

.cursor {
  font-style: normal;
  animation: blink 1s step-start infinite;
}

.speak-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  margin-left: 8px;
  flex: 0 0 auto;
  border: none;
  border-radius: 50%;
  background: color-mix(in srgb, var(--color-primary, #C8A2D6) 18%, transparent);
  color: var(--color-primary, #C8A2D6);
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  vertical-align: middle;
  transition: all 0.2s ease;
}

.speak-btn:hover:not(:disabled) {
  background: var(--color-primary, #C8A2D6);
  color: #fff;
  transform: translateY(-1px);
}

.speak-btn:disabled {
  opacity: 0.6;
  cursor: wait;
}

.speak-btn.speaking {
  background: var(--color-primary, #C8A2D6);
  color: #fff;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.55;
  }
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

.message-context-menu {
  position: fixed;
  z-index: 1000;
  min-width: 140px;
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

.edit-mode {
  display: block;
  width: 100%;
}

.edit-mode :deep(.el-input) {
  width: 100%;
}

.forward-friends {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.forward-friend {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-bg);
  color: var(--color-text-primary);
  cursor: pointer;
  text-align: left;
}

.forward-friend.selected {
  border-color: var(--color-primary);
  background: color-mix(in srgb, var(--color-primary) 10%, transparent);
}

.forward-avatar {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  flex: 0 0 auto;
}
</style>
