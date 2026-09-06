// Electron 主进程 —— 窗口管理 + 系统托盘 + 全局快捷键 + 系统通知 + IPC
const { app, BrowserWindow, Tray, Menu, globalShortcut, ipcMain, Notification, nativeImage } = require('electron')
const path = require('path')

let mainWindow = null
let tray = null
let isQuitting = false

const isDev = !app.isPackaged
const DEV_URL = process.env.VITE_DEV_SERVER_URL || 'http://localhost:5173'

// ---------- 窗口 ----------
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1100,
    height: 760,
    minWidth: 900,
    minHeight: 640,
    title: 'Lunaris',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  mainWindow.once('ready-to-show', () => mainWindow.show())

  if (isDev) {
    mainWindow.loadURL(DEV_URL)
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    // 生产：加载前端构建产物（vite outDir 输出到 electron/renderer；Vue hash 路由 file:// 可加载）
    mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'))
  }

  // 关闭 → 隐藏到托盘（真正退出走托盘菜单「退出」）
  mainWindow.on('close', (e) => {
    if (!isQuitting) {
      e.preventDefault()
      mainWindow.hide()
    }
  })
  mainWindow.on('closed', () => { mainWindow = null })
}

function showWindow() {
  if (!mainWindow) { createWindow(); return }
  mainWindow.show()
  mainWindow.focus()
}

function toggleWindow() {
  if (mainWindow && mainWindow.isVisible()) mainWindow.hide()
  else showWindow()
}

// ---------- 系统托盘（DESK-01） ----------
function createTray() {
  const iconPath = path.join(__dirname, 'assets', 'icon.png')
  let icon = nativeImage.createFromPath(iconPath)
  if (icon.isEmpty()) icon = nativeImage.createEmpty() // 缺图标时用占位，避免托盘创建失败
  tray = new Tray(icon)
  tray.setToolTip('Lunaris')
  const menu = Menu.buildFromTemplate([
    { label: '显示主界面', click: () => showWindow() },
    { type: 'separator' },
    { label: '退出', click: () => { isQuitting = true; app.quit() } },
  ])
  tray.setContextMenu(menu)
  tray.on('click', () => toggleWindow()) // 左键点击切换显示/隐藏
}

// ---------- IPC（供渲染进程 electron.ts 调用） ----------
function registerIpc() {
  ipcMain.on('window:minimize', () => mainWindow?.minimize())
  ipcMain.on('window:close-to-tray', () => mainWindow?.hide())
  ipcMain.on('badge:set', (_e, count) => {
    const n = Number(count) || 0
    if (process.platform === 'darwin') app.dock?.setBadge(n ? String(n) : '')
  })
  // 系统通知（DESK-02）
  ipcMain.handle('notify', (_e, { title, body }) => {
    if (Notification.isSupported()) new Notification({ title, body }).show()
  })
}

app.whenReady().then(() => {
  createWindow()
  createTray()
  registerIpc()

  // 全局快捷键 Ctrl+Shift+L 唤出/隐藏（DESK-03）
  globalShortcut.register('Control+Shift+L', () => toggleWindow())

  // 开机自启动（DESK-04，P2；默认关闭，按需打开）
  // app.setLoginItemSettings({ openAtLogin: true })

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
    else showWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('will-quit', () => {
  globalShortcut.unregisterAll()
})
