// 后端地址配置。
// 开发：留空 → 走 vite 代理（/api、/v1 → localhost:8001）
// 生产（Electron file:// 加载）：需在构建时指定，如 VITE_API_BASE=https://api.lunaris.app
export const API_BASE = import.meta.env.VITE_API_BASE || ''
export const API_ORIGIN = API_BASE || (
  typeof window !== 'undefined' && window.location.protocol === 'file:'
    ? 'http://localhost:8001'
    : ''
)

export function resolveApiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path
  const base = API_ORIGIN || window.location.origin
  return `${base.replace(/\/$/, '')}/${path.replace(/^\//, '')}`
}
