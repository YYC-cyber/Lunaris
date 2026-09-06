<template>
  <div
    class="voice-message-container"
    @contextmenu.prevent="openContextMenu"
    @click="closeContextMenu"
  >
    <button
      class="voice-btn"
      :disabled="loading"
      :aria-label="playing ? '暂停语音' : '播放语音'"
      @click="playing ? stop() : play()"
    >
      <span class="icon" aria-hidden="true">{{ playing ? '⏸️' : '🔊' }}</span>
      <span class="duration">{{ formatDuration(duration) }}</span>
    </button>
    <span v-if="playing" class="playing-indicator" role="status">播放中</span>
    <span v-if="loading" class="loading-indicator" role="status">加载中...</span>

    <!-- 播放进度条（P2-13） -->
    <div v-if="current > 0 && duration > 0" class="progress-area">
      <input
        class="progress-slider"
        type="range"
        min="0"
        :max="Math.floor(duration || 1)"
        :value="Math.floor(current || 0)"
        :aria-label="'播放进度 ' + formatDuration(current) + ' / ' + formatDuration(duration)"
        @input="onSeek"
        @change="onSeekCommit"
      />
      <span class="progress-time">{{ formatDuration(current) }} / {{ formatDuration(duration) }}</span>
    </div>

    <div
      v-if="contextMenu.visible"
      class="voice-context-menu"
      :style="{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px` }"
      role="menu"
      aria-label="语音操作菜单"
      @click.stop
    >
      <button
        class="context-menu-item"
        :disabled="transcribing"
        role="menuitem"
        @click="toggleText"
      >
        {{ transcribing ? '转写中...' : (textVisible ? '关闭文字' : '语音转文字') }}
      </button>
      <!-- 倍速控制（P2-14） -->
      <div class="rate-control" role="group" aria-label="播放速度">
        <span class="rate-label">倍速</span>
        <button
          v-for="r in [0.5, 1, 1.5, 2]"
          :key="r"
          class="rate-btn"
          :class="{ active: rate === r }"
          :aria-pressed="rate === r"
          @click="changeRate(r)"
        >
          {{ r }}x
        </button>
      </div>
      <!-- 音量控制（P2-14） -->
      <div class="volume-control" role="group" aria-label="音量">
        <span class="rate-label">音量</span>
        <input
          type="range"
          min="0"
          max="100"
          :value="Math.round(volume * 100)"
          class="volume-slider"
          aria-label="音量"
          @input="changeVolume"
        />
        <span class="volume-val">{{ Math.round(volume * 100) }}%</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import {
  playVoice,
  resolveVoiceUrl,
  stopVoice,
  seekTo,
  getPlaybackPrefs,
  setPlaybackVolume,
  setPlaybackRate,
} from '../../utils/ttsAudioPlayer'
import api from '../../utils/api'
import { resolveApiUrl } from '../../config'
import { ElMessage } from 'element-plus'
import { cleanVoiceText, getAudioExtension } from '../../utils/voice'

interface Props {
  url: string
  originalText?: string
  textVisible?: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (event: 'show-text', text: string): void
  (event: 'hide-text'): void
}>()

const playing = ref(false)
const loading = ref(false)
const duration = ref(0)
const current = ref(0)
const transcribing = ref(false)
const recognizedText = ref(cleanVoiceText(props.originalText))
const contextMenu = reactive({ visible: false, x: 0, y: 0 })

// 播放偏好
const prefs = getPlaybackPrefs()
const volume = ref(prefs.volume)
const rate = ref(prefs.rate)

function openContextMenu(event: MouseEvent) {
  const menuWidth = 180
  const menuHeight = 150
  contextMenu.x = Math.min(event.clientX, window.innerWidth - menuWidth - 8)
  contextMenu.y = Math.min(event.clientY, window.innerHeight - menuHeight - 8)
  contextMenu.visible = true
}

function closeContextMenu() {
  contextMenu.visible = false
}

// ---- P2-13: 进度拖拽 ----
function onSeek(event: Event) {
  const target = event.target as HTMLInputElement
  const secs = Number(target.value)
  current.value = secs
}

function onSeekCommit(event: Event) {
  const target = event.target as HTMLInputElement
  seekTo(Number(target.value))
}

// ---- P2-14: 倍速 / 音量 ----
function changeRate(r: number) {
  rate.value = r
  setPlaybackRate(r)
}

function changeVolume(event: Event) {
  const target = event.target as HTMLInputElement
  const v = Number(target.value) / 100
  volume.value = v
  setPlaybackVolume(v)
}

async function toggleText() {
  if (transcribing.value) return
  contextMenu.visible = false

  if (props.textVisible) {
    emit('hide-text')
    return
  }

  if (recognizedText.value) {
    emit('show-text', recognizedText.value)
    return
  }

  try {
    transcribing.value = true
    const audioUrl = resolveApiUrl(props.url)
    const response = await fetch(audioUrl)
    if (!response.ok) throw new Error(`音频加载失败（${response.status}）`)
    const blob = await response.blob()
    const form = new FormData()
    form.append('file', blob, `voice.${getAudioExtension(blob)}`)
    const result: any = await api.post('/api/voice/transcribe', form)
    const text = cleanVoiceText(result?.text)
    if (!text) {
      ElMessage.warning('未识别到语音内容')
      return
    }
    recognizedText.value = text
    emit('show-text', text)
    ElMessage.success('语音转写成功')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '语音转写失败')
  } finally {
    transcribing.value = false
  }
}

function onDocumentClick() {
  closeContextMenu()
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') closeContextMenu()
}

let progressTimer: ReturnType<typeof setInterval> | null = null

function trackProgress() {
  if (progressTimer) clearInterval(progressTimer)
  progressTimer = setInterval(() => {
    const audio = document.querySelector('audio')
    // 用播放状态推进进度（简单方案：按当前已播放时间推进）
    // 实际通过 timeupdate 事件，这里用 ref 简单模拟
  }, 250)
}

onMounted(async () => {
  document.addEventListener('click', onDocumentClick)
  document.addEventListener('keydown', onKeydown)
  try {
    loading.value = true
    const audio = new Audio()
    audio.crossOrigin = 'anonymous'
    audio.addEventListener('loadedmetadata', () => {
      duration.value = audio.duration || 0
      loading.value = false
    })
    audio.addEventListener('error', () => {
      console.error('加载音频失败')
      duration.value = 0
      loading.value = false
    })
    audio.src = resolveVoiceUrl(props.url)
  } catch (error) {
    console.error('获取音频时长失败:', error)
    duration.value = 0
    loading.value = false
  }
})

// 播放中更新进度
watch(playing, (p) => {
  if (p) {
    trackProgress()
  } else if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
})

watch(() => props.originalText, (text) => {
  recognizedText.value = cleanVoiceText(text)
})

onUnmounted(() => {
  document.removeEventListener('click', onDocumentClick)
  document.removeEventListener('keydown', onKeydown)
  if (progressTimer) clearInterval(progressTimer)
})

function formatDuration(seconds: number): string {
  if (!seconds) return '0"'
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  if (mins > 0) {
    return `${mins}'${secs}"`
  }
  return `${secs}"`
}

async function play() {
  if (loading.value || playing.value) return

  playing.value = true
  try {
    await playVoice(props.url)
  } catch (error) {
    console.error('播放失败:', error)
  } finally {
    playing.value = false
    current.value = 0
  }
}

function stop() {
  stopVoice()
  playing.value = false
  current.value = 0
}

</script>

<style scoped>
.voice-message-container {
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
  flex-wrap: wrap;
}

.voice-context-menu {
  position: fixed;
  z-index: 3000;
  min-width: 180px;
  padding: 8px;
  background: var(--color-bg, #fff);
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 8px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.16);
}

.context-menu-item {
  width: 100%;
  padding: 8px 10px;
  border: 0;
  background: transparent;
  color: var(--color-text, #333);
  text-align: left;
  cursor: pointer;
  border-radius: 4px;
  font-size: 13px;
}

.context-menu-item:hover:not(:disabled) {
  background: rgba(212, 165, 212, 0.16);
}

.context-menu-item:disabled {
  opacity: 0.6;
  cursor: wait;
}

/* 倍速控制 */
.rate-control {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 0;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  margin-top: 4px;
}

.rate-label {
  font-size: 12px;
  color: var(--color-text-light, #888);
  min-width: 30px;
}

.rate-btn {
  padding: 2px 6px;
  border: 1px solid rgba(0, 0, 0, 0.15);
  border-radius: 4px;
  background: transparent;
  color: var(--color-text, #333);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
}

.rate-btn.active {
  background: var(--color-primary, #C8A2D6);
  color: white;
  border-color: var(--color-primary, #C8A2D6);
}

.rate-btn:hover:not(.active) {
  background: rgba(212, 165, 212, 0.12);
}

/* 音量控制 */
.volume-control {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 0;
}

.volume-slider {
  flex: 1;
  min-width: 60px;
  height: 4px;
  cursor: pointer;
  accent-color: var(--color-primary, #C8A2D6);
}

.volume-val {
  font-size: 11px;
  color: var(--color-text-light, #888);
  min-width: 32px;
  text-align: right;
}

/* 播放进度条 */
.progress-area {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  margin-top: 4px;
}

.progress-slider {
  flex: 1;
  height: 4px;
  cursor: pointer;
  accent-color: var(--color-primary, #C8A2D6);
}

.progress-time {
  font-size: 11px;
  color: var(--color-text-light, #888);
  white-space: nowrap;
}

.voice-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%);
  color: white;
  border: none;
  border-radius: var(--radius-bubble);
  padding: 8px 14px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s ease;
  min-width: 70px;
  box-shadow: var(--shadow-soft);
}

.voice-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, var(--color-secondary) 0%, #7D5A85 100%);
  box-shadow: var(--shadow-medium);
  transform: translateY(-2px);
}

.voice-btn:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: var(--shadow-soft);
}

.voice-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.icon {
  font-size: 16px;
  display: inline-block;
  min-width: 16px;
}

.duration {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12px;
  min-width: 32px;
  text-align: right;
  opacity: 0.9;
}

.playing-indicator {
  font-size: 12px;
  color: var(--color-primary);
  font-weight: 600;
  animation: pulse 1s infinite;
}

.loading-indicator {
  font-size: 12px;
  color: var(--color-text-light);
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}
</style>
