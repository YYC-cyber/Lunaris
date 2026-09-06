// 语音播放封装（AI 语音条 / 用户录音回放）
// P2-13/P2-14: 支持进度拖拽、音量调节、倍速控制
import { resolveApiUrl } from '../config'

let currentAudio: HTMLAudioElement | null = null

// 播放偏好（本地持久化）
const PLAYBACK_KEY = 'lunaris_playback_prefs'

interface PlaybackPrefs {
  volume: number   // 0-1
  rate: number     // 0.5-2.0
}

function loadPrefs(): PlaybackPrefs {
  try {
    const raw = localStorage.getItem(PLAYBACK_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      return {
        volume: typeof parsed.volume === 'number' ? Math.min(1, Math.max(0, parsed.volume)) : 1,
        rate: typeof parsed.rate === 'number' ? Math.min(2, Math.max(0.5, parsed.rate)) : 1,
      }
    }
  } catch { /* ignore */ }
  return { volume: 1, rate: 1 }
}

function savePrefs(prefs: PlaybackPrefs) {
  try { localStorage.setItem(PLAYBACK_KEY, JSON.stringify(prefs)) } catch { /* ignore */ }
}

export function getPlaybackPrefs(): PlaybackPrefs {
  return loadPrefs()
}

export function setPlaybackVolume(volume: number): void {
  const prefs = loadPrefs()
  prefs.volume = Math.min(1, Math.max(0, volume))
  savePrefs(prefs)
  if (currentAudio) currentAudio.volume = prefs.volume
}

export function setPlaybackRate(rate: number): void {
  const prefs = loadPrefs()
  prefs.rate = Math.min(2, Math.max(0.5, rate))
  savePrefs(prefs)
  if (currentAudio) currentAudio.playbackRate = prefs.rate
}

export function resolveVoiceUrl(url: string) {
  if (!url) return ''
  if (/^https?:\/\//i.test(url) || url.startsWith('blob:') || url.startsWith('data:')) return url
  return resolveApiUrl(url)
}

export function playVoice(url: string): Promise<void> {
  if (!url) return Promise.reject(new Error('音频地址为空'))
  currentAudio?.pause()
  const audio = new Audio(resolveVoiceUrl(url))
  currentAudio = audio
  // 应用播放偏好
  const prefs = loadPrefs()
  audio.volume = prefs.volume
  audio.playbackRate = prefs.rate
  return new Promise((resolve, reject) => {
    audio.onended = () => {
      if (currentAudio === audio) currentAudio = null
      resolve()
    }
    audio.onerror = () => {
      if (currentAudio === audio) currentAudio = null
      reject(new Error('音频加载失败'))
    }
    audio.play().catch(reject)
  })
}

export function stopVoice() {
  currentAudio?.pause()
  currentAudio = null
}

// ============================================================
// 进度控制（P2-13）
// ============================================================

/** 获取当前正在播放的音频元素（供 VoiceMessage 控制进度）。 */
export function getCurrentAudio(): HTMLAudioElement | null {
  return currentAudio
}

/** 跳转到指定秒数。 */
export function seekTo(seconds: number): void {
  if (!currentAudio) return
  const dur = currentAudio.duration
  const clamped = Math.min(Math.max(0, seconds), dur || 0)
  currentAudio.currentTime = clamped
}

/** 监听当前音频播放进度。返回取消函数。 */
export function onAudioProgress(cb: (current: number, duration: number) => void): () => void {
  const audio = currentAudio
  if (!audio) return () => {}
  const handler = () => {
    cb(audio.currentTime || 0, audio.duration || 0)
  }
  audio.addEventListener('timeupdate', handler)
  return () => audio.removeEventListener('timeupdate', handler)
}
