import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('cockpit', {
  window: {
    minimize: () => ipcRenderer.invoke('window:minimize'),
    maximize: () => ipcRenderer.invoke('window:maximize'),
    close: () => ipcRenderer.invoke('window:close'),
    isMaximized: () => ipcRenderer.invoke('window:isMaximized'),
    setMode: (mode: string) => ipcRenderer.invoke('window:setMode', mode),
    onModeChange: (cb: (mode: string) => void) => {
      ipcRenderer.on('window:modeChanged', (_e, mode) => cb(mode))
    }
  },
  voice: {
    start: () => ipcRenderer.invoke('voice:start'),
    stop: () => ipcRenderer.invoke('voice:stop'),
    onLog: (cb: (msg: string) => void) => {
      ipcRenderer.on('voice-server-log', (_e, msg) => cb(msg))
    },
    onError: (cb: (msg: string) => void) => {
      ipcRenderer.on('voice-server-error', (_e, msg) => cb(msg))
    },
    onExit: (cb: (code: number | null) => void) => {
      ipcRenderer.on('voice-server-exit', (_e, code) => cb(code))
    }
  },
  notify: {
    show: (title: string, body: string) => ipcRenderer.invoke('notify:show', title, body)
  },
  readDir: (dirPath: string) => ipcRenderer.invoke('fs:readDir', dirPath),
  readFile: (filePath: string) => ipcRenderer.invoke('fs:readFile', filePath),
  writeFile: (filePath: string, content: string) => ipcRenderer.invoke('fs:writeFile', filePath, content)
})
