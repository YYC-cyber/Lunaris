// Electron 预加载脚本 —— 用 contextBridge 暴露最小白名单 API
const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  minimize: () => ipcRenderer.send('window:minimize'),
  closeToTray: () => ipcRenderer.send('window:close-to-tray'),
  notify: (title, body) => ipcRenderer.invoke('notify', { title, body }),
  setBadge: (count) => ipcRenderer.send('badge:set', count),
})
