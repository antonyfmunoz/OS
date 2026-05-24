import { app, BrowserWindow, shell, ipcMain } from 'electron'
import { join } from 'path'
import { readdir, stat, readFile, writeFile } from 'fs/promises'
import { is } from '@electron-toolkit/utils'
import { spawn, ChildProcess } from 'child_process'

let mainWindow: BrowserWindow | null = null
let voiceServer: ChildProcess | null = null

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

app.whenReady().then(() => {
  createWindow()
})

app.on('window-all-closed', () => {
  voiceServer?.kill()
  app.quit()
})

app.on('before-quit', () => {
  voiceServer?.kill()
})
