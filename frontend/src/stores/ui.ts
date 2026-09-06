import { defineStore } from 'pinia'
import api from '../utils/api'

export type Theme = 'light' | 'dark'
export type FontSize = 'small' | 'normal' | 'large' | 'xlarge'

export const useUiStore = defineStore('ui', {
  state: () => ({
    theme: (localStorage.getItem('theme') as Theme) || 'light',
    fontSize: (localStorage.getItem('fontSize') as FontSize) || 'normal',
  }),
  actions: {
    async setTheme(theme: Theme) {
      this.theme = theme
      localStorage.setItem('theme', theme)
      this.applyTheme()
      try {
        await api.patch('/api/user/preferences', { theme })
      } catch {
        // Fallback: preference saved locally even if API fails
      }
    },
    async setFontSize(size: FontSize) {
      this.fontSize = size
      localStorage.setItem('fontSize', size)
      this.applyFontSize()
      try {
        await api.patch('/user/preferences', { font_size: size })
      } catch {
        // Fallback: preference saved locally even if API fails
      }
    },
    applyTheme() {
      const html = document.documentElement
      html.classList.remove('light', 'dark')
      html.classList.add(this.theme)
    },
    applyFontSize() {
      const html = document.documentElement
      html.classList.remove('font-size-small', 'font-size-normal', 'font-size-large', 'font-size-xlarge')
      html.classList.add(`font-size-${this.fontSize}`)
    },
    init() {
      this.applyTheme()
      this.applyFontSize()
    },
  },
})
