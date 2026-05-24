declare global {
  interface Window {
    cockpit: {
      window: {
        minimize: () => void
        maximize: () => void
        close: () => void
        isMaximized: () => Promise<boolean>
      }
      voice: {
        start: () => void
        stop: () => void
        onLog: (cb: (msg: string) => void) => void
        onError: (cb: (msg: string) => void) => void
        onExit: (cb: (code: number | null) => void) => void
      }
    }
  }
}

export function TitleBar() {
  return (
    <header
      className="titlebar-drag flex items-center px-3 select-none"
      style={{
        height: 'var(--titlebar-height)',
        background: 'var(--bg)',
        borderBottom: '1px solid var(--border)',
      }}
    >
      <span
        className="font-mono text-xs tracking-widest uppercase"
        style={{ color: 'var(--accent-cyan)' }}
      >
        UMH
      </span>
      <span className="ml-1.5 text-xs" style={{ color: 'var(--text-tertiary)' }}>
        cockpit
      </span>

      <div className="flex-1" />

      <div className="titlebar-no-drag flex items-center gap-1">
        <button
          onClick={() => window.cockpit?.window.minimize()}
          className="w-8 h-6 flex items-center justify-center rounded text-xs hover:bg-[var(--surface-2)] transition-colors"
          style={{ color: 'var(--text-secondary)' }}
        >
          ─
        </button>
        <button
          onClick={() => window.cockpit?.window.maximize()}
          className="w-8 h-6 flex items-center justify-center rounded text-xs hover:bg-[var(--surface-2)] transition-colors"
          style={{ color: 'var(--text-secondary)' }}
        >
          □
        </button>
        <button
          onClick={() => window.cockpit?.window.close()}
          className="w-8 h-6 flex items-center justify-center rounded text-xs hover:bg-[var(--accent-red)] hover:text-white transition-colors"
          style={{ color: 'var(--text-secondary)' }}
        >
          ✕
        </button>
      </div>
    </header>
  )
}
