// Electron 桥接：Web 环境下 window.electronAPI 不存在，静默降级
const w = window as any
export const electronAPI = w.electronAPI || null

export function minimize() { electronAPI?.minimize?.() }
export function closeToTray() { electronAPI?.closeToTray?.() }
export function isElectron() { return !!electronAPI }

// 窗口非聚焦时弹系统通知（RT-08：WS 收到新消息/动态时联动）
export function notifyIfInactive(title: string, body: string) {
  if (document.hasFocus()) return
  electronAPI?.notify?.(title, body)
}
