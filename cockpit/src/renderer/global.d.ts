import type { WindowMode } from './stores/cockpitStore'

interface CockpitBridge {
  window: {
    minimize: () => Promise<void>
    maximize: () => Promise<void>
    close: () => Promise<void>
    isMaximized: () => Promise<boolean>
    setMode: (mode: WindowMode) => Promise<void>
    onModeChange: (cb: (mode: WindowMode) => void) => void
  }
  voice: {
    start: () => Promise<void>
    stop: () => Promise<void>
    onLog: (cb: (msg: string) => void) => void
    onError: (cb: (msg: string) => void) => void
    onExit: (cb: (code: number | null) => void) => void
  }
  notify: {
    show: (title: string, body: string) => Promise<void>
  }
  readDir: (dirPath: string) => Promise<Array<{ name: string; path: string; type: 'file' | 'directory' }>>
  readFile: (filePath: string) => Promise<string>
  writeFile: (filePath: string, content: string) => Promise<boolean>
}

declare global {
  interface Window {
    cockpit?: CockpitBridge
  }
}
