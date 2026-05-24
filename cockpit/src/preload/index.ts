import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('cockpit', {
  window: {
    minimize: () => ipcRenderer.invoke('window:minimize'),
    maximize: () => ipcRenderer.invoke('window:maximize'),
    close: () => ipcRenderer.invoke('window:close'),
    isMaximized: () => ipcRenderer.invoke('window:isMaximized')
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
  }
})
