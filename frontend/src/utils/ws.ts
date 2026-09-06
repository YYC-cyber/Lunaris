// 轻量 WebSocket 客户端：自动重连 + 心跳 + 事件订阅
import { API_ORIGIN } from '../config'

export type WsEvent = { type: string; id: string; data: any; ts: number }

type Listener = (data: any) => void

class WsClient {
  private ws: WebSocket | null = null
  private listeners = new Map<string, Listener[]>()
  private heartbeatTimer: number | null = null
  private reconnectTimer: number | null = null
  private token = ''
  private shouldReconnect = false

  connect(token: string) {
    this.token = token
    this.shouldReconnect = true
    this.open()
  }

  private open() {
    const url = this.wsUrl()
    this.ws = new WebSocket(url)
    this.ws.onopen = () => { this.startHeartbeat(); this.emit('open', null) }
    this.ws.onmessage = (e) => this.handleMessage(e)
    this.ws.onclose = () => this.handleClose()
    this.ws.onerror = () => this.ws?.close()
  }

  private handleMessage(e: MessageEvent) {
    try {
      const msg = JSON.parse(e.data)
      if (msg && msg.type) this.emit(msg.type, msg)
    } catch { /* 忽略非 JSON */ }
  }

  private handleClose() {
    this.stopHeartbeat()
    this.emit('close', null)
    if (this.shouldReconnect && this.reconnectTimer == null) {
      this.reconnectTimer = window.setTimeout(() => { this.reconnectTimer = null; this.open() }, 3000)
    }
  }

  private wsUrl(): string {
    if (API_ORIGIN) return `${API_ORIGIN.replace(/^http/, 'ws')}/api/ws?token=${this.token}`
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    return `${proto}://${location.host}/api/ws?token=${this.token}`
  }

  private startHeartbeat() {
    this.stopHeartbeat()
    this.heartbeatTimer = window.setInterval(() => this.send({ type: 'ping', ts: Date.now() }), 30000)
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) { clearInterval(this.heartbeatTimer); this.heartbeatTimer = null }
  }

  send(obj: any) {
    if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(obj))
  }

  on(type: string, cb: Listener): () => void {
    if (!this.listeners.has(type)) this.listeners.set(type, [])
    this.listeners.get(type)!.push(cb)
    return () => this.off(type, cb)
  }

  private off(type: string, cb: Listener) {
    const arr = this.listeners.get(type)
    if (arr) this.listeners.set(type, arr.filter((x) => x !== cb))
  }

  private emit(type: string, data: any) {
    const arr = this.listeners.get(type)
    if (arr) arr.forEach((cb) => cb(data))
  }

  close() {
    this.shouldReconnect = false
    this.stopHeartbeat()
    if (this.reconnectTimer) { clearTimeout(this.reconnectTimer); this.reconnectTimer = null }
    this.ws?.close()
  }
}

export const wsClient = new WsClient()
