import { defineStore } from 'pinia'
import { wsClient } from '../utils/ws'

export const useWsStore = defineStore('ws', {
  state: () => ({
    connected: false,
  }),
  actions: {
    connect(token: string) {
      wsClient.connect(token)
      wsClient.on('open', () => { this.connected = true })
      wsClient.on('close', () => { this.connected = false })
    },
    disconnect() {
      wsClient.close()
      this.connected = false
    },
    send(obj: any) {
      wsClient.send(obj)
    },
  },
})
