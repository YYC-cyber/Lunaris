import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: './', // Electron 打包后 file:// 加载所需
  server: {
    port: 5173,
    proxy: {
      // REST 接口 + WebSocket（后端 /api/ws）统一走 /api 代理
      '/api': { target: 'http://localhost:8001', changeOrigin: true, ws: true },
      '/v1': { target: 'http://localhost:8001', changeOrigin: true },
      '/static': { target: 'http://localhost:8001', changeOrigin: true },
    },
  },
  build: { outDir: '../electron/renderer', emptyOutDir: true },
})
