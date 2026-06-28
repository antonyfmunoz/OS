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

import { useCockpitStore } from '../stores/cockpitStore'
import { useWorkspaceContextStore } from '../stores/workspaceContextStore'
import { useUnifiedCanvasStore } from '../stores/unifiedCanvasStore'
import { ROUTES } from '../types/routes'
import { IDEMenuBar } from './IDEMenuBar'

const CANVAS_PANELS = new Set(['canvas', 'agents', 'workflows'])

const MODE_LABELS: Record<string, string> = {
  general: 'General',
  agents: 'Agents',
  workflows: 'Workflows',
  loops: 'Loops',
  harnesses: 'Harnesses',
  organism: 'Organism',
}

function getPanelLabel(panelId: string): string {
  const route = ROUTES.find(r => r.id === panelId)
  return route?.label ?? panelId
}

export function TitleBar() {
  const activePanel = useCockpitStore(s => s.activePanel)
  const panelLabel = getPanelLabel(activePanel)
  const activeMode = useUnifiedCanvasStore(s => s.activeMode)
  const contextLine = useWorkspaceContextStore(s => s.contextLine())

  const toggleFullscreen = () => {
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {})
    } else {
      document.documentElement.requestFullscreen().catch(() => {})
    }
  }

  return (
    <header
      className="titlebar-drag flex items-center px-3 select-none bg-surface border-b border-border"
      style={{ height: 'var(--spacing-titlebar-height)' }}
    >
      {activePanel === 'editor' ? (
        <IDEMenuBar />
      ) : CANVAS_PANELS.has(activePanel) ? (
        <>
          <span className="font-mono text-[10px] tracking-widest uppercase leading-none text-text-secondary">
            Canvas
          </span>
          <span className="ml-2 font-mono text-[10px] leading-none text-text-tertiary">/</span>
          <span className="ml-2 font-mono text-[10px] tracking-widest uppercase leading-none text-text-primary">
            {MODE_LABELS[activeMode] ?? activeMode}
          </span>
        </>
      ) : (
        <>
          <span className="font-mono text-[10px] tracking-widest uppercase leading-none text-text-secondary">
            {panelLabel}
          </span>
          {contextLine && (
            <span className="ml-3 font-mono text-[10px] leading-none text-text-tertiary truncate max-w-[400px]">
              {contextLine}
            </span>
          )}
        </>
      )}

      <div className="flex-1" />

      {activePanel !== 'editor' && (
        <div className="titlebar-no-drag flex items-center gap-1">
          <button
            onClick={toggleFullscreen}
            className="w-8 h-6 flex items-center justify-center rounded text-[10px] text-text-secondary hover:bg-surface-raised transition-colors"
            title="Toggle full-screen"
          >
            ⛶
          </button>
          <button
            onClick={() => window.cockpit?.window.minimize()}
            className="w-8 h-6 flex items-center justify-center rounded text-[10px] text-text-secondary hover:bg-surface-raised transition-colors"
          >
            ─
          </button>
          <button
            onClick={() => window.cockpit?.window.maximize()}
            className="w-8 h-6 flex items-center justify-center rounded text-[10px] text-text-secondary hover:bg-surface-raised transition-colors"
          >
            □
          </button>
          <button
            onClick={() => window.cockpit?.window.close()}
            className="w-8 h-6 flex items-center justify-center rounded text-[10px] text-text-secondary hover:bg-danger hover:text-white transition-colors"
          >
            ✕
          </button>
        </div>
      )}
    </header>
  )
}
