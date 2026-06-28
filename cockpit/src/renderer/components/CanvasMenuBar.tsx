import { useState, useRef, useEffect, useCallback } from 'react'
import { useUnifiedCanvasStore } from '../stores/unifiedCanvasStore'
import { useCanvasStore } from '../stores/canvasStore'
import { useAgentCanvasStore } from '../stores/agentCanvasStore'
import { useWorkflowCanvasStore } from '../stores/workflowCanvasStore'
import { useLoopCanvasStore } from '../stores/loopCanvasStore'
import { useHarnessCanvasStore } from '../stores/harnessCanvasStore'
import { useOrganismCanvasStore } from '../stores/organismCanvasStore'
import type { CanvasMode } from '../stores/unifiedCanvasStore'

// ─── Types ──────────────────────────────────────────────────────

interface MenuItem {
  label: string
  shortcut?: string
  disabled?: boolean
  separator?: boolean
  active?: boolean
  action?: () => void
}

interface MenuGroup {
  label: string
  items: MenuItem[]
}

// ─── Zoom helpers ───────────────────────────────────────────────

function getActiveZoom(mode: CanvasMode): number {
  switch (mode) {
    case 'general': return useCanvasStore.getState().zoom
    case 'agents': return useAgentCanvasStore.getState().zoom
    case 'workflows': return useWorkflowCanvasStore.getState().zoom
    case 'loops': return useLoopCanvasStore.getState().zoom
    case 'harnesses': return useHarnessCanvasStore.getState().zoom
    case 'organism': return useOrganismCanvasStore.getState().zoom
  }
}

function setActiveZoom(mode: CanvasMode, zoom: number) {
  switch (mode) {
    case 'general': useCanvasStore.getState().setZoom(zoom); break
    case 'agents': useAgentCanvasStore.getState().setZoom(zoom); break
    case 'workflows': useWorkflowCanvasStore.getState().setZoom(zoom); break
    case 'loops': useLoopCanvasStore.getState().setZoom(zoom); break
    case 'harnesses': useHarnessCanvasStore.getState().setZoom(zoom); break
    case 'organism': useOrganismCanvasStore.getState().setZoom(zoom); break
  }
}

function doFitAll(mode: CanvasMode) {
  switch (mode) {
    case 'general': useCanvasStore.getState().fitAll(); break
    case 'agents': useAgentCanvasStore.getState().fitAll(); break
    default: break
  }
}

function doTile(mode: CanvasMode) {
  switch (mode) {
    case 'general': useCanvasStore.getState().tileWindows(); break
    case 'agents': useAgentCanvasStore.getState().tileNodes(); break
    default: break
  }
}

// ─── Mode definitions ───────────────────────────────────────────

const MODE_ORDER: CanvasMode[] = ['general', 'organism', 'agents', 'harnesses', 'loops', 'workflows']

const MODE_LABELS: Record<CanvasMode, string> = {
  general: 'General',
  organism: 'Organism',
  agents: 'Agents',
  harnesses: 'Harnesses',
  loops: 'Loops',
  workflows: 'Workflows',
}

// ─── Menu definitions ───────────────────────────────────────────

function buildMenus(activeMode: CanvasMode): MenuGroup[] {
  const unified = useUnifiedCanvasStore.getState()
  const activeCanvasId = unified.activeCanvasId[activeMode]
  const hasCanvas = !!activeCanvasId

  return [
    {
      label: 'Canvas',
      items: [
        {
          label: 'New Canvas',
          action: () => {
            const name = prompt('Canvas name:')
            if (name?.trim()) useUnifiedCanvasStore.getState().createCanvas(name.trim())
          },
        },
        {
          label: 'Rename Canvas',
          disabled: !hasCanvas,
          action: () => {
            if (!activeCanvasId) return
            const canvas = useUnifiedCanvasStore.getState().savedCanvases.find(c => c.id === activeCanvasId)
            const name = prompt('New name:', canvas?.name ?? '')
            if (name?.trim()) useUnifiedCanvasStore.getState().renameCanvas(activeCanvasId, name.trim())
          },
        },
        {
          label: 'Delete Canvas',
          disabled: !hasCanvas,
          action: () => {
            if (!activeCanvasId) return
            const canvas = useUnifiedCanvasStore.getState().savedCanvases.find(c => c.id === activeCanvasId)
            if (confirm(`Delete canvas "${canvas?.name}"?`)) {
              useUnifiedCanvasStore.getState().deleteCanvas(activeCanvasId)
            }
          },
        },
        { label: '', separator: true },
        { label: 'Save Layout', disabled: true },
        { label: 'Load Layout', disabled: true },
      ],
    },
    {
      label: 'View',
      items: [
        { label: 'Toggle Palette', shortcut: 'Ctrl+B', action: () => {
          document.dispatchEvent(new CustomEvent('canvas:toggle-palette'))
        }},
        { label: '', separator: true },
        { label: 'Zoom In', shortcut: 'Ctrl+=', action: () => {
          const z = getActiveZoom(activeMode)
          setActiveZoom(activeMode, z + 0.1)
        }},
        { label: 'Zoom Out', shortcut: 'Ctrl+-', action: () => {
          const z = getActiveZoom(activeMode)
          setActiveZoom(activeMode, z - 0.1)
        }},
        { label: 'Reset Zoom', action: () => setActiveZoom(activeMode, 1) },
        { label: '', separator: true },
        { label: 'Fit All', disabled: !['general', 'agents'].includes(activeMode), action: () => doFitAll(activeMode) },
        { label: 'Tile', disabled: !['general', 'agents'].includes(activeMode), action: () => doTile(activeMode) },
        { label: '', separator: true },
        { label: 'Toggle Fullscreen', action: () => {
          if (document.fullscreenElement) {
            document.exitFullscreen().catch(() => {})
          } else {
            document.documentElement.requestFullscreen().catch(() => {})
          }
        }},
      ],
    },
    {
      label: 'Mode',
      items: MODE_ORDER.map(m => ({
        label: MODE_LABELS[m],
        active: m === activeMode,
        action: () => useUnifiedCanvasStore.getState().setMode(m),
      })),
    },
  ]
}

// ─── Component ──────────────────────────────────────────────────

export function CanvasMenuBar() {
  const activeMode = useUnifiedCanvasStore(s => s.activeMode)
  const [openMenu, setOpenMenu] = useState<string | null>(null)
  const barRef = useRef<HTMLDivElement>(null)

  const close = useCallback(() => setOpenMenu(null), [])

  useEffect(() => {
    if (!openMenu) return
    const handler = (e: MouseEvent) => {
      if (barRef.current && !barRef.current.contains(e.target as Node)) close()
    }
    const keyHandler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
    }
    document.addEventListener('mousedown', handler)
    document.addEventListener('keydown', keyHandler)
    return () => {
      document.removeEventListener('mousedown', handler)
      document.removeEventListener('keydown', keyHandler)
    }
  }, [openMenu, close])

  const menus = buildMenus(activeMode)

  return (
    <div ref={barRef} className="flex items-center select-none gap-0.5">
      {menus.map((menu) => (
        <div key={menu.label} className="relative">
          <button
            onClick={() => setOpenMenu(openMenu === menu.label ? null : menu.label)}
            onMouseEnter={() => { if (openMenu) setOpenMenu(menu.label) }}
            className={`px-2 py-1 text-[9px] rounded transition-colors ${
              openMenu === menu.label
                ? 'bg-surface-raised text-text-primary'
                : 'text-text-secondary hover:text-text-primary hover:bg-surface-raised'
            }`}
          >
            {menu.label}
          </button>

          {openMenu === menu.label && (
            <div
              className="absolute top-full left-0 mt-0.5 rounded shadow-lg z-50 min-w-[180px] py-1"
              style={{
                background: 'var(--color-surface-raised)',
                border: '1px solid var(--color-border)',
              }}
            >
              {menu.items.map((item, i) =>
                item.separator ? (
                  <div key={i} className="my-1 border-t border-border" />
                ) : (
                  <button
                    key={item.label}
                    onClick={() => {
                      if (!item.disabled && item.action) {
                        item.action()
                        close()
                      }
                    }}
                    disabled={item.disabled}
                    className={`w-full flex items-center justify-between px-3 py-1 text-[9px] transition-colors ${
                      item.disabled
                        ? 'text-text-tertiary opacity-50 cursor-default'
                        : item.active
                          ? 'bg-surface-overlay text-text-primary'
                          : 'text-text-primary hover:bg-cyan-glow hover:text-cyan'
                    }`}
                  >
                    <span>{item.label}</span>
                    {item.shortcut && (
                      <span className="ml-4 text-[8px] text-text-tertiary font-mono">
                        {item.shortcut}
                      </span>
                    )}
                  </button>
                ),
              )}
            </div>
          )}
        </div>
      ))}

      <div className="ml-3 flex items-center gap-2">
        <span className="text-[9px] font-mono tracking-widest uppercase text-text-primary">
          {MODE_LABELS[activeMode]}
        </span>
      </div>
    </div>
  )
}
