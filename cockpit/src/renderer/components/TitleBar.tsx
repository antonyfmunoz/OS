declare global {
  interface Window {
    cockpit: {
      window: {
        minimize: () => void
        maximize: () => void
        close: () => void
        isMaximized: () => Promise<boolean>
        setMode?: (mode: string) => void
      }
      voice: {
        start: () => void
        stop: () => void
        onLog: (cb: (msg: string) => void) => void
        onError: (cb: (msg: string) => void) => void
        onExit: (cb: (code: number | null) => void) => void
      }
      readDir: (dirPath: string) => Promise<{ name: string; path: string; type: 'file' | 'directory' }[]>
      readFile: (filePath: string) => Promise<string>
      writeFile: (filePath: string, content: string) => Promise<boolean>
    }
  }
}

export function TitleBar() {
  return (
    <header
      className="titlebar-drag relative flex items-center px-3 select-none bg-canvas border-b border-border"
      style={{ height: 'var(--spacing-titlebar-height)' }}
    >
      <div className="wv-scanline absolute inset-0" />

      <span className="relative font-mono text-xs tracking-widest uppercase text-cyan">
        UMH
      </span>

      <div className="flex-1" />

      <div className="titlebar-no-drag relative flex items-center gap-1">
        <button
          onClick={() => window.cockpit?.window.minimize()}
          className="w-8 h-6 flex items-center justify-center rounded text-xs text-text-secondary hover:bg-surface-raised transition-colors"
        >
          ─
        </button>
        <button
          onClick={() => window.cockpit?.window.maximize()}
          className="w-8 h-6 flex items-center justify-center rounded text-xs text-text-secondary hover:bg-surface-raised transition-colors"
        >
          □
        </button>
        <button
          onClick={() => window.cockpit?.window.close()}
          className="w-8 h-6 flex items-center justify-center rounded text-xs text-text-secondary hover:bg-danger hover:text-white transition-colors"
        >
          ✕
        </button>
      </div>
    </header>
  )
}
