<template>
  <div class="input-area">
    <div class="toolbar">
      <el-popover v-if="!chat.isFriendChat" placement="top" width="380" trigger="click">
        <template #reference>
          <el-button text aria-label="选择表情">😀 表情</el-button>
        </template>
        <div class="sticker-popup" role="dialog" aria-label="表情选择器">
          <!-- 分类标签 -->
          <div class="sticker-tabs" role="tablist" aria-label="表情分类">
            <div
              v-for="tab in stickerTabs"
              :key="tab.key"
              :class="['tab-item', { active: activeStickerTab === tab.key }]"
              role="tab"
              :aria-selected="activeStickerTab === tab.key"
              tabindex="0"
              @click="activeStickerTab = tab.key"
              @keydown.enter="activeStickerTab = tab.key"
            >
              {{ tab.label }}
            </div>
          </div>

          <!-- 搜索框 -->
          <el-input
            v-if="activeStickerTab !== 'recent'"
            v-model="stickerSearch"
            placeholder="搜索表情..."
            clearable
            aria-label="搜索表情"
            style="margin-bottom: 8px"
          />

          <!-- 表情网格 -->
          <div class="sticker-grid" role="listbox" aria-label="表情列表">
            <div
              v-for="s in filteredStickers"
              :key="s.id"
              class="sticker-item"
              :title="s.name"
              role="option"
              tabindex="0"
              @click="sendSticker(s)"
              @keydown.enter="sendSticker(s)"
            >
              <span class="emoji">{{ s.displayEmoji }}</span>
            </div>
          </div>
          <div v-if="!filteredStickers.length" class="empty">暂无表情包</div>
        </div>
      </el-popover>
      <!-- 图片上传按钮 (仅真人好友聊天) -->
      <el-button v-if="chat.isFriendChat" text aria-label="发送图片" @click="imageInput?.click()">📷 图片</el-button>
      <input
        ref="imageInput"
        type="file"
        accept="image/*"
        style="display: none"
        @change="handleImageSelect"
      />
      <el-button text :type="recording ? 'danger' : 'default'" aria-label="录音或停止录音" @click="toggleRecord">
        {{ recording ? '🔴 录音中（点此停止）' : '🎤 语音' }}
      </el-button>
      <el-button v-if="recordedVoiceBlob" text type="success" aria-label="发送语音" @click="sendRecordedVoice">
        ✓ 发送语音
      </el-button>
      <el-button v-if="recordedVoiceBlob" text type="info" aria-label="取消语音" @click="cancelRecordedVoice">
        × 取消
      </el-button>
    </div>
    <div class="row">
      <el-input
        v-model="text"
        type="textarea"
        :rows="3"
        resize="none"
        placeholder="发消息…（Enter 发送，Shift+Enter 换行）"
        @keydown.enter.exact.prevent="send"
        @input="onInputChange"
      />
      <el-button type="primary" class="send-btn" :loading="chat.sending" @click="send">发送</el-button>
    </div>

    <!-- @mention 下拉框 -->
    <div
      v-if="showMentionDropdown && mentionableMembers.length"
      class="mention-dropdown"
      :style="{ left: `${mentionDropdownX}px`, top: `${mentionDropdownY}px` }"
    >
      <div
        v-for="member in filteredMentionMembers"
        :key="member.id"
        class="mention-item"
        @click="selectMention(member)"
      >
        <span class="member-name">{{ member.name }}</span>
        <span class="member-type">{{ member.type === 'ai' ? '🤖' : '👤' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../utils/api'
import { useChatStore } from '../../stores/chat'
import { useGroupStore } from '../../stores/group'
import { useUserStore } from '../../stores/user'
import { wsClient } from '../../utils/ws'
import { isStickerImage, stickerFallbackEmoji, stickerReplacementEmoji } from '../../utils/sticker'
import { cleanVoiceText, getAudioExtension } from '../../utils/voice'

const chat = useChatStore()
const groupStore = useGroupStore()
const user = useUserStore()
const text = ref('')
const stickers = ref<any[]>([])
const recentStickers = ref<any[]>([])
const recording = ref(false)
const recordedVoiceBlob = ref<Blob | null>(null)
const transcribingVoice = ref(false)
const imageInput = ref<HTMLInputElement>()
const uploading = ref(false)
const selectedImage = ref<{ url: string; file?: File }>()
const activeStickerTab = ref('all')
const stickerSearch = ref('')

// Typing status
let typingTimer: number | null = null
let typingStarted = false

// @mention 相关
const showMentionDropdown = ref(false)
const mentionDropdownX = ref(0)
const mentionDropdownY = ref(0)
const mentionSearch = ref('')
const mentionCursorPos = ref(0)

const stickerTabs = [
  { key: 'recent', label: '最近使用' },
  { key: 'happy', label: '开心' },
  { key: 'sad', label: '伤心' },
  { key: 'angry', label: '生气' },
  { key: 'love', label: '喜欢' },
  { key: 'neutral', label: '平静' },
  { key: 'all', label: '全部' },
]

const mentionableMembers = computed(() => {
  const group = groupStore.currentGroup
  if (!group) return []
  return group.members || []
})

const filteredMentionMembers = computed(() => {
  return mentionableMembers.value.filter((m) =>
    m.name.toLowerCase().includes(mentionSearch.value.toLowerCase())
  )
})

const displayStickers = computed(() => {
  const used = new Set<string>()
  const filtered = getFilteredStickers()

  return filtered.map((s, index) => {
    const image = s.image_url || ''
    const isImage = isStickerImage(image)
    let displayEmoji = s.sticker_emoji || (isImage ? stickerFallbackEmoji(s.emotion, s.name) : image)

    if (used.has(displayEmoji)) {
      displayEmoji = stickerReplacementEmoji(s.emotion, used, index)
    }

    used.add(displayEmoji)
    return { ...s, displayEmoji }
  })
})

const filteredStickers = computed(() => {
  if (activeStickerTab.value === 'recent') {
    return displayStickers.value.filter((s) =>
      recentStickers.value.some((r) => r.id === s.id)
    )
  }

  let result = displayStickers.value
  if (activeStickerTab.value !== 'all') {
    result = result.filter((s) => s.emotion === activeStickerTab.value)
  }

  if (stickerSearch.value) {
    result = result.filter((s) =>
      s.name.toLowerCase().includes(stickerSearch.value.toLowerCase()) ||
      s.emotion.toLowerCase().includes(stickerSearch.value.toLowerCase())
    )
  }

  return result
})

let mediaStream: MediaStream | null = null
let audioContext: AudioContext | null = null
let audioSource: MediaStreamAudioSourceNode | null = null
let audioProcessor: ScriptProcessorNode | null = null
let pcmChunks: Float32Array[] = []
let recordingSampleRate = 44100

onMounted(async () => {
  try {
    const res: any = await api.get('/api/stickers')
    stickers.value = res?.data ?? res ?? []
  } catch { /* 忽略 */ }

  // 加载最近使用的表情
  try {
    const recentRes = await chat.getRecentStickers(20)
    recentStickers.value = recentRes
  } catch { /* 忽略 */ }
})

function getFilteredStickers() {
  return stickers.value
}

function send() {
  const t = text.value.trim()
  if (!t) return

  // Stop typing indicator
  if (typingStarted) {
    typingStarted = false
    wsClient.send({
      type: 'typing_stop',
      data: { user_id: user.user?.id },
    })
  }
  if (typingTimer) clearTimeout(typingTimer)

  const mentionedUserIds = extractMentions(t)

  if (chat.isFriendChat) {
    chat.sendFriendMessage(t)
  } else {
    const groupId = groupStore.currentGroupId
    if (groupId) {
      groupStore.sendMessageWithMentions(groupId, t, mentionedUserIds)
    } else {
      chat.send(t)
    }
  }
  text.value = ''
}

function extractMentions(content: string): string[] {
  const matches = content.match(/@([^\s@]+)/g) || []
  return matches.map((m) => {
    const mentioned = mentionableMembers.value.find((member) => member.name === m.slice(1))
    const mentionedId = mentioned?.type === 'ai'
      ? mentioned.soul_id
      : mentioned?.user_id
    return (mentionedId || m.slice(1)).toString()
  })
}

function onInputChange() {
  // Handle @mention dropdown
  const inputValue = text.value
  const cursorPos = (text.value as any).selectionStart || 0

  const beforeCursor = inputValue.substring(0, cursorPos)
  const lastAtIndex = beforeCursor.lastIndexOf('@')

  if (lastAtIndex !== -1 && (lastAtIndex === 0 || inputValue[lastAtIndex - 1] === ' ')) {
    mentionSearch.value = beforeCursor.substring(lastAtIndex + 1)
    showMentionDropdown.value = true
    mentionCursorPos.value = cursorPos

    nextTick(() => {
      const input = document.querySelector('.row .el-textarea__inner') as HTMLTextAreaElement
      if (input) {
        const rect = input.getBoundingClientRect()
        mentionDropdownX.value = rect.left
        mentionDropdownY.value = rect.bottom + 8
      }
    })
  } else {
    showMentionDropdown.value = false
  }

  // Handle typing status (debounced)
  if (typingTimer) clearTimeout(typingTimer)

  if (inputValue.trim().length > 0 && !typingStarted) {
    typingStarted = true
    wsClient.send({
      type: 'typing_start',
      data: {
        user_id: user.user?.id,
        username: user.user?.username,
      },
    })
  }

  typingTimer = window.setTimeout(() => {
    if (typingStarted) {
      typingStarted = false
      wsClient.send({
        type: 'typing_stop',
        data: { user_id: user.user?.id },
      })
    }
  }, 300)
}

function selectMention(member: any) {
  const inputValue = text.value
  const cursorPos = mentionCursorPos.value
  const beforeCursor = inputValue.substring(0, cursorPos)
  const afterCursor = inputValue.substring(cursorPos)

  const lastAtIndex = beforeCursor.lastIndexOf('@')
  const newText = beforeCursor.substring(0, lastAtIndex) + `@${member.name} ` + afterCursor

  text.value = newText
  showMentionDropdown.value = false
  mentionSearch.value = ''

  nextTick(() => {
    const input = document.querySelector('.row .el-textarea__inner') as HTMLTextAreaElement
    if (input) {
      const newPos = lastAtIndex + member.name.length + 2
      input.setSelectionRange(newPos, newPos)
      input.focus()
    }
  })
}

function sendSticker(s: any) {
  const soulId = chat.currentSoulId
  if (!soulId) return
  chat.send('', s.id, false, s.image_url, s.emotion, s.displayEmoji)

  // 更新最近使用
  const existIndex = recentStickers.value.findIndex((r) => r.id === s.id)
  if (existIndex !== -1) {
    recentStickers.value.splice(existIndex, 1)
  }
  recentStickers.value.unshift(s)
  if (recentStickers.value.length > 20) {
    recentStickers.value.pop()
  }
}

async function handleImageSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const files = input.files
  if (!files || files.length === 0) return

  const file = files[0]
  if (!file.type.startsWith('image/')) {
    ElMessage.error('请选择图片文件')
    return
  }

  if (file.size > 10 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过 10MB')
    return
  }

  try {
    uploading.value = true

    const url = URL.createObjectURL(file)
    selectedImage.value = { url, file }

    const formData = new FormData()
    formData.append('file', file)

    const res: any = await api.post('/api/upload/image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    const imageUrl = res?.data?.url || res?.url
    if (!imageUrl) {
      ElMessage.error('上传失败，请重试')
      return
    }

    selectedImage.value = { url: imageUrl, file }
    sendImage(imageUrl)
    selectedImage.value = undefined
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '图片上传失败')
    selectedImage.value = undefined
  } finally {
    uploading.value = false
    if (imageInput.value) imageInput.value.value = ''
  }
}

function sendImage(imageUrl: string) {
  const description = text.value.trim() || '（分享了一张图片）'
  text.value = ''

  if (!chat.isFriendChat) {
    return
  }

  chat.sendFriendMessage(description, undefined, imageUrl)
}

async function toggleRecord() {
  if (recording.value) {
    recording.value = false
    audioProcessor?.disconnect()
    audioSource?.disconnect()
    mediaStream?.getTracks().forEach((track) => track.stop())
    audioProcessor = null
    audioSource = null
    audioContext?.close()
    audioContext = null
    await onRecordStop()
    return
  }
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    audioContext = new AudioContext()
    recordingSampleRate = audioContext.sampleRate
    audioSource = audioContext.createMediaStreamSource(mediaStream)
    audioProcessor = audioContext.createScriptProcessor(4096, 1, 1)
    pcmChunks = []
    audioProcessor.onaudioprocess = (event) => {
      pcmChunks.push(new Float32Array(event.inputBuffer.getChannelData(0)))
    }
    audioSource.connect(audioProcessor)
    audioProcessor.connect(audioContext.destination)
    recording.value = true
  } catch {
    mediaStream?.getTracks().forEach((t) => t.stop())
    audioContext?.close()
    mediaStream = null
    audioContext = null
    ElMessage.error('无法访问麦克风，请检查权限')
  }
}

async function onRecordStop() {
  if (!pcmChunks.length) return
  const blob = encodeWav(pcmChunks, recordingSampleRate)
  try {
    transcribingVoice.value = true
    const form = new FormData()
    form.append('file', blob, 'voice.wav')

    const res: any = await api.post('/api/voice/transcribe', form)
    const transcribedText = cleanVoiceText(res?.text)

    if (!transcribedText) {
      ElMessage.warning('未识别到内容')
      recordedVoiceBlob.value = null
      transcribingVoice.value = false
      return
    }

    text.value = transcribedText
    recordedVoiceBlob.value = blob

    ElMessage.success(`识别成功：${transcribedText}`)
    transcribingVoice.value = false
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '语音转写失败')
    recordedVoiceBlob.value = null
    transcribingVoice.value = false
  }
}

function encodeWav(chunks: Float32Array[], sampleRate: number): Blob {
  const sampleCount = chunks.reduce((total, chunk) => total + chunk.length, 0)
  const buffer = new ArrayBuffer(44 + sampleCount * 2)
  const view = new DataView(buffer)
  const writeString = (offset: number, value: string) => {
    for (let i = 0; i < value.length; i++) view.setUint8(offset + i, value.charCodeAt(i))
  }
  writeString(0, 'RIFF')
  view.setUint32(4, 36 + sampleCount * 2, true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeString(36, 'data')
  view.setUint32(40, sampleCount * 2, true)
  let offset = 44
  for (const chunk of chunks) {
    for (const sample of chunk) {
      const clamped = Math.max(-1, Math.min(1, sample))
      view.setInt16(offset, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true)
      offset += 2
    }
  }
  return new Blob([buffer], { type: 'audio/wav' })
}

function cancelRecordedVoice() {
  recordedVoiceBlob.value = null
  text.value = ''
}

async function sendRecordedVoice() {
  if (!recordedVoiceBlob.value || !text.value.trim()) {
    ElMessage.warning('内容不能为空')
    return
  }

  try {
    const form = new FormData()
    form.append('file', recordedVoiceBlob.value, `voice.${getAudioExtension(recordedVoiceBlob.value)}`)
    const uploadRes: any = await api.post('/api/upload/voice', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const voiceUrl = uploadRes?.data?.url || uploadRes?.url
    if (!voiceUrl) throw new Error('语音上传失败')

    if (chat.isFriendChat) {
      await chat.sendFriendMessage(text.value, undefined, undefined, voiceUrl)
    } else {
      await chat.sendWithVoice(text.value, voiceUrl)
    }

    text.value = ''
    recordedVoiceBlob.value = null
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '发送语音失败')
  }
}
</script>

<style scoped>
.input-area {
  border-top: 1px solid color-mix(in srgb, var(--companion-primary, #d4a5d4) 16%, transparent);
  background: color-mix(in srgb, var(--companion-surface, #fff) 48%, transparent);
  backdrop-filter: blur(10px);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  position: relative;
}

.toolbar {
  margin-bottom: 8px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.toolbar :deep(.el-button) {
  border-radius: var(--radius-btn);
  transition: all 0.2s ease;
}

.toolbar :deep(.el-button:hover) {
  background: color-mix(in srgb, var(--companion-secondary, #d4a5d4) 18%, transparent);
  color: var(--companion-primary, var(--color-primary));
}

.toolbar :deep(.el-button.is-text) {
  color: var(--color-text-secondary);
}

.toolbar :deep(.el-button.is-text:hover) {
  color: var(--companion-primary, var(--color-primary));
}

.row {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  position: relative;
}

.row :deep(.el-input) {
  flex: 1;
}

.row :deep(.el-textarea) {
  border-radius: var(--radius-input) !important;
  border: 1px solid color-mix(in srgb, var(--companion-primary, #d4a5d4) 22%, transparent);
  background: color-mix(in srgb, var(--companion-surface, #fff) 72%, white 28%);
  transition: all 0.2s ease;
}

.row :deep(.el-textarea:hover) {
  border-color: color-mix(in srgb, var(--companion-primary, #d4a5d4) 48%, transparent);
  background: color-mix(in srgb, var(--companion-surface, #fff) 86%, white 14%);
}

.row :deep(.el-textarea__inner) {
  border-radius: var(--radius-input);
  color: var(--color-text-primary);
  font-size: 14px;
  resize: none;
}

.row :deep(.el-textarea__inner::placeholder) {
  color: var(--color-text-light);
}

.send-btn {
  height: 64px;
  border-radius: var(--radius-input);
  background: linear-gradient(135deg, var(--companion-primary, var(--color-primary)) 0%, var(--companion-secondary, var(--color-secondary)) 100%);
  border: none;
  color: #fff;
  font-weight: 600;
  transition: all 0.3s ease;
}

.send-btn:hover {
  box-shadow: var(--shadow-medium);
  transform: translateY(-2px);
}

.send-btn:active {
  transform: translateY(0);
}

/* 表情包弹窗 */
.sticker-popup {
  padding: 12px;
  max-height: 380px;
  overflow-y: auto;
  background: var(--color-bg-main);
}

.sticker-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  border-bottom: 1px solid rgba(212, 165, 212, 0.1);
  overflow-x: auto;
  padding-bottom: 8px;
}

.tab-item {
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
  transition: all 0.2s;
  color: var(--color-text-secondary);
}

.tab-item.active {
  background: rgba(212, 165, 212, 0.15);
  color: var(--color-primary);
  font-weight: 600;
}

.tab-item:hover {
  background: rgba(212, 165, 212, 0.08);
}

.sticker-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
}

.sticker-item {
  cursor: pointer;
  border-radius: var(--radius-card);
  display: flex;
  align-items: center;
  justify-content: center;
  aspect-ratio: 1;
  background: rgba(212, 165, 212, 0.08);
  overflow: hidden;
  transition: all 0.2s;
}

.sticker-item:hover {
  background: rgba(212, 165, 212, 0.15);
  transform: scale(1.08);
}

.sticker-item img {
  display: block;
  width: auto;
  height: auto;
  max-width: calc(100% - 8px);
  max-height: calc(100% - 8px);
  object-fit: contain;
}

.sticker-item .emoji {
  display: block;
  font-family: "Apple Color Emoji", "Segoe UI Emoji", sans-serif;
  font-size: 32px;
  line-height: 1;
}

.empty {
  grid-column: 1 / -1;
  text-align: center;
  color: var(--color-text-light);
  font-size: 12px;
  padding: 16px 0;
}

/* @mention 下拉框 */
.mention-dropdown {
  position: fixed;
  z-index: 2000;
  min-width: 200px;
  max-height: 200px;
  overflow-y: auto;
  background: var(--color-bg, #fff);
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 6px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.16);
  padding: 4px;
}

.mention-item {
  padding: 8px 12px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  transition: all 0.2s;
}

.mention-item:hover {
  background: rgba(212, 165, 212, 0.16);
}

.member-name {
  color: var(--color-text-primary);
}

.member-type {
  font-size: 12px;
  margin-left: 4px;
}
</style>
