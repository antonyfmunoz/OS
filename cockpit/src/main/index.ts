import { app, BrowserWindow, shell, ipcMain, Tray, Menu, nativeImage, Notification } from 'electron'
import { join } from 'path'
import { readdir, stat, readFile, writeFile } from 'fs/promises'
import { is } from '@electron-toolkit/utils'
import { spawn, ChildProcess } from 'child_process'

let mainWindow: BrowserWindow | null = null
let voiceServer: ChildProcess | null = null
let tray: Tray | null = null
let currentWindowMode = 'maximized'

const WINDOW_MODES = ['maximized', 'large-fab', 'medium-fab', 'small-fab', 'invisible'] as const

const FAB_SIZES: Record<string, { width: number; height: number }> = {
  'large-fab': { width: 296, height: 200 },
  'medium-fab': { width: 160, height: 64 },
  'small-fab': { width: 64, height: 64 },
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 600,
    backgroundColor: '#07080a',
    titleBarStyle: 'hiddenInset',
    frame: false,
    show: false,
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true
    }
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow?.show()
  })

  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

function spawnVoiceServer(): void {
  const voicePath = join(process.env['UMH_ROOT'] || '/opt/OS', 'umh', 'voice_server.py')
  voiceServer = spawn('python3', [voicePath], {
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
    stdio: ['ignore', 'pipe', 'pipe']
  })

  voiceServer.stdout?.on('data', (data: Buffer) => {
    mainWindow?.webContents.send('voice-server-log', data.toString())
  })

  voiceServer.stderr?.on('data', (data: Buffer) => {
    mainWindow?.webContents.send('voice-server-error', data.toString())
  })

  voiceServer.on('exit', (code) => {
    mainWindow?.webContents.send('voice-server-exit', code)
    voiceServer = null
  })
}

ipcMain.handle('window:minimize', () => mainWindow?.minimize())
ipcMain.handle('window:maximize', () => {
  if (mainWindow?.isMaximized()) {
    mainWindow.unmaximize()
  } else {
    mainWindow?.maximize()
  }
})
ipcMain.handle('window:close', () => mainWindow?.close())
ipcMain.handle('window:isMaximized', () => mainWindow?.isMaximized() ?? false)

ipcMain.handle('voice:start', () => {
  if (!voiceServer) spawnVoiceServer()
})
ipcMain.handle('voice:stop', () => {
  voiceServer?.kill()
  voiceServer = null
})

ipcMain.handle('fs:readDir', async (_e, dirPath: string) => {
  const entries = await readdir(dirPath, { withFileTypes: true })
  const result = []
  for (const entry of entries) {
    if (entry.name.startsWith('.') || entry.name === 'node_modules' || entry.name === '__pycache__') continue
    const fullPath = join(dirPath, entry.name)
    const isDir = entry.isDirectory()
    result.push({ name: entry.name, path: fullPath, type: isDir ? 'directory' : 'file' })
  }
  return result.sort((a, b) => {
    if (a.type !== b.type) return a.type === 'directory' ? -1 : 1
    return a.name.localeCompare(b.name)
  })
})

ipcMain.handle('fs:readFile', async (_e, filePath: string) => {
  const info = await stat(filePath)
  if (info.size > 2 * 1024 * 1024) return '[File too large to display]'
  return readFile(filePath, 'utf-8')
})

ipcMain.handle('fs:writeFile', async (_e, filePath: string, content: string) => {
  await writeFile(filePath, content, 'utf-8')
  return true
})

ipcMain.handle('window:setMode', (_e, mode: string) => {
  if (!mainWindow) return
  currentWindowMode = mode

  if (mode === 'maximized') {
    mainWindow.setAlwaysOnTop(false)
    mainWindow.setResizable(true)
    mainWindow.setMinimumSize(1024, 600)
    mainWindow.setSize(1440, 900, true)
    mainWindow.center()
    mainWindow.show()
  } else if (mode === 'invisible') {
    mainWindow.hide()
  } else {
    const size = FAB_SIZES[mode] || { width: 280, height: 180 }
    mainWindow.setAlwaysOnTop(true, 'floating')
    mainWindow.setResizable(false)
    mainWindow.setMinimumSize(size.width, size.height)
    mainWindow.setSize(size.width, size.height, true)
    mainWindow.show()
  }

  mainWindow.webContents.send('window:modeChanged', mode)
  updateTrayMenu()
})

ipcMain.handle('notify:show', (_e, title: string, body: string) => {
  if (Notification.isSupported()) {
    const notification = new Notification({ title, body })
    notification.on('click', () => {
      if (mainWindow) {
        mainWindow.show()
        mainWindow.focus()
      }
    })
    notification.show()
  }
})

function createTray(): void {
  const icon = nativeImage.createEmpty()
  tray = new Tray(icon)
  tray.setToolTip('UMH Cockpit')
  tray.on('click', () => {
    if (mainWindow) {
      if (currentWindowMode === 'invisible') {
        currentWindowMode = 'maximized'
        mainWindow.setAlwaysOnTop(false)
        mainWindow.setResizable(true)
        mainWindow.setMinimumSize(1024, 600)
        mainWindow.setSize(1440, 900, true)
        mainWindow.center()
        mainWindow.webContents.send('window:modeChanged', 'maximized')
      }
      mainWindow.show()
      mainWindow.focus()
    }
  })
  updateTrayMenu()
}

function updateTrayMenu(): void {
  if (!tray) return
  const menu = Menu.buildFromTemplate(
    WINDOW_MODES.map((mode) => ({
      label: mode === 'maximized' ? 'Maximized' :
             mode === 'large-fab' ? 'Large FAB' :
             mode === 'medium-fab' ? 'Medium FAB' :
             mode === 'small-fab' ? 'Small FAB' : 'Invisible',
      type: 'radio' as const,
      checked: currentWindowMode === mode,
      click: () => {
        ipcMain.emit('window:setMode', null, mode)
        mainWindow?.webContents.send('window:modeChanged', mode)
      },
    }))
  )
  tray.setContextMenu(menu)
}

app.whenReady().then(() => {
  createWindow()
  createTray()
})

app.on('window-all-closed', () => {
  voiceServer?.kill()
  tray?.destroy()
  app.quit()
})

app.on('before-quit', () => {
  voiceServer?.kill()
  tray?.destroy()
})
