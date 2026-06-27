import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { clampZoom } from '../utils/canvasCoords'

// ── Types ──────────────────────────────────────────────────────

export type CanvasWindowType = 'browser' | 'desktop' | 'vision' | 'terminal' | 'preview' | 'agent' | 'panel'
export type CanvasConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'error'

export interface CanvasWindowConfig {
  paneId?: string
  monitorId?: string
  session?: string
  pane?: string
  url?: string
  agentId?: string
  panelId?: string
}

export interface CanvasWindow {
  id: string
  type: CanvasWindowType
  label: string
  x: number
  y: number
  width: number
  height: number
  zIndex: number
  collapsed: boolean
  maximized: boolean
  paused: boolean
  poppedOut: boolean
  badgeCount: number
  clusterId: string | null
  connectionStatus: CanvasConnectionStatus
  preMaxBounds?: { x: number; y: number; width: number; height: number }
  config: CanvasWindowConfig
}

export interface CanvasCluster {
  id: string
  label: string
  windowIds: string[]
  color: string
  collapsed: boolean
}

export interface CanvasPreset {
  id: string
  name: string
  windows: Omit<CanvasWindow, 'connectionStatus' | 'badgeCount' | 'poppedOut'>[]
  clusters: CanvasCluster[]
  panX: number
  panY: number
  zoom: number
}

// ── Defaults ───────────────────────────────────────────────────

const DEFAULT_SIZES: Record<CanvasWindowType, { width: number; height: number }> = {
  browser: { width: 800, height: 600 },
  desktop: { width: 960, height: 540 },
  vision: { width: 640, height: 480 },
  terminal: { width: 600, height: 400 },
  preview: { width: 800, height: 600 },
  agent: { width: 400, height: 500 },
  panel: { width: 600, height: 500 },
}

const DEFAULT_LABELS: Record<CanvasWindowType, string> = {
  browser: 'Browser',
  desktop: 'Desktop',
  vision: 'Vision',
  terminal: 'Terminal',
  preview: 'Preview',
  agent: 'Agent',
  panel: 'Panel',
}

const CLUSTER_COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#f97316', '#22c55e', '#06b6d4']

function mapWindow(
  windows: CanvasWindow[],
  id: string,
  fn: (w: CanvasWindow) => CanvasWindow,
): CanvasWindow[] {
  return windows.map((w) => (w.id === id ? fn(w) : w))
}

// ── Store ──────────────────────────────────────────────────────

export interface CanvasState {
  windows: CanvasWindow[]
  clusters: CanvasCluster[]
  presets: CanvasPreset[]
  panX: number
  panY: number
  zoom: number
  nextZIndex: number

  addWindow: (type: CanvasWindowType, config?: CanvasWindowConfig) => string
  removeWindow: (id: string) => void
  updateWindow: (id: string, partial: Partial<CanvasWindow>) => void

  bringToFront: (id: string) => void
  toggleCollapse: (id: string) => void
  toggleMaximize: (id: string) => void
  togglePause: (id: string) => void
  popOut: (id: string) => void
  popIn: (id: string) => void
  renameWindow: (id: string, label: string) => void
  setBadge: (id: string, count: number) => void
  setConnectionStatus: (id: string, status: CanvasConnectionStatus) => void

  createCluster: (label: string, windowIds: string[], color?: string) => string
  dissolveCluster: (clusterId: string) => void
  addToCluster: (clusterId: string, windowId: string) => void
  removeFromCluster: (windowId: string) => void
  toggleClusterCollapse: (clusterId: string) => void
  moveCluster: (clusterId: string, deltaX: number, deltaY: number) => void

  savePreset: (name: string) => string
  loadPreset: (presetId: string) => void
  deletePreset: (presetId: string) => void

  setPan: (x: number, y: number) => void
  setZoom: (zoom: number) => void
  fitAll: () => void
  tileWindows: () => void
  clearAll: () => void

  collapseByType: (type: CanvasWindowType) => void
  removeByType: (type: CanvasWindowType) => void
  pauseAll: () => void
  resumeAll: () => void
  collapseAll: () => void
  expandAll: () => void
}

export const useCanvasStore = create<CanvasState>()(
  persist(
    (set, get) => ({
      windows: [],
      clusters: [],
      presets: [],
      panX: 0,
      panY: 0,
      zoom: 1,
      nextZIndex: 1,

      // ── Window CRUD ────────────────────────────────────────

      addWindow: (type, config) => {
        const id = crypto.randomUUID()
        const size = DEFAULT_SIZES[type]
        const state = get()
        const last = state.windows[state.windows.length - 1]
        const x = last ? last.x + 30 : 100
        const y = last ? last.y + 30 : 100
        const label = DEFAULT_LABELS[type]
        const zIndex = state.nextZIndex

        const win: CanvasWindow = {
          id,
          type,
          label,
          x,
          y,
          width: size.width,
          height: size.height,
          zIndex,
          collapsed: false,
          maximized: false,
          paused: false,
          poppedOut: false,
          badgeCount: 0,
          clusterId: null,
          connectionStatus: 'disconnected',
          config: config ?? {},
        }

        set({ windows: [...state.windows, win], nextZIndex: zIndex + 1 })
        return id
      },

      removeWindow: (id) => {
        set((s) => ({
          windows: s.windows.filter((w) => w.id !== id),
          clusters: s.clusters.map((c) => ({
            ...c,
            windowIds: c.windowIds.filter((wid) => wid !== id),
          })),
        }))
      },

      updateWindow: (id, partial) => {
        set((s) => ({ windows: mapWindow(s.windows, id, (w) => ({ ...w, ...partial })) }))
      },

      // ── Window actions ─────────────────────────────────────

      bringToFront: (id) => {
        set((s) => ({
          windows: mapWindow(s.windows, id, (w) => ({ ...w, zIndex: s.nextZIndex })),
          nextZIndex: s.nextZIndex + 1,
        }))
      },

      toggleCollapse: (id) => {
        set((s) => ({
          windows: mapWindow(s.windows, id, (w) => ({ ...w, collapsed: !w.collapsed })),
        }))
      },

      toggleMaximize: (id) => {
        set((s) => ({
          windows: mapWindow(s.windows, id, (w) => {
            if (w.maximized) {
              const b = w.preMaxBounds
              return {
                ...w,
                maximized: false,
                x: b?.x ?? w.x,
                y: b?.y ?? w.y,
                width: b?.width ?? w.width,
                height: b?.height ?? w.height,
                preMaxBounds: undefined,
              }
            }
            return {
              ...w,
              maximized: true,
              preMaxBounds: { x: w.x, y: w.y, width: w.width, height: w.height },
              x: -s.panX / s.zoom,
              y: -s.panY / s.zoom,
              width: window.innerWidth / s.zoom,
              height: window.innerHeight / s.zoom,
              zIndex: s.nextZIndex,
            }
          }),
          nextZIndex: s.nextZIndex + 1,
        }))
      },

      togglePause: (id) => {
        set((s) => ({
          windows: mapWindow(s.windows, id, (w) => ({ ...w, paused: !w.paused })),
        }))
      },

      popOut: (id) => {
        set((s) => ({
          windows: mapWindow(s.windows, id, (w) => ({ ...w, poppedOut: true })),
        }))
      },

      popIn: (id) => {
        set((s) => ({
          windows: mapWindow(s.windows, id, (w) => ({ ...w, poppedOut: false })),
        }))
      },

      renameWindow: (id, label) => {
        set((s) => ({
          windows: mapWindow(s.windows, id, (w) => ({ ...w, label })),
        }))
      },

      setBadge: (id, count) => {
        set((s) => ({
          windows: mapWindow(s.windows, id, (w) => ({ ...w, badgeCount: count })),
        }))
      },

      setConnectionStatus: (id, status) => {
        set((s) => ({
          windows: mapWindow(s.windows, id, (w) => ({ ...w, connectionStatus: status })),
        }))
      },

      // ── Cluster actions ────────────────────────────────────

      createCluster: (label, windowIds, color) => {
        const id = crypto.randomUUID()
        const clusterColor = color ?? CLUSTER_COLORS[get().clusters.length % CLUSTER_COLORS.length]
        set((s) => ({
          clusters: [...s.clusters, { id, label, windowIds, color: clusterColor, collapsed: false }],
          windows: s.windows.map((w) =>
            windowIds.includes(w.id) ? { ...w, clusterId: id } : w,
          ),
        }))
        return id
      },

      dissolveCluster: (clusterId) => {
        set((s) => ({
          clusters: s.clusters.filter((c) => c.id !== clusterId),
          windows: s.windows.map((w) =>
            w.clusterId === clusterId ? { ...w, clusterId: null } : w,
          ),
        }))
      },

      addToCluster: (clusterId, windowId) => {
        set((s) => ({
          clusters: s.clusters.map((c) =>
            c.id === clusterId
              ? { ...c, windowIds: [...c.windowIds, windowId] }
              : c,
          ),
          windows: mapWindow(s.windows, windowId, (w) => ({ ...w, clusterId })),
        }))
      },

      removeFromCluster: (windowId) => {
        set((s) => {
          const win = s.windows.find((w) => w.id === windowId)
          if (!win?.clusterId) return s
          return {
            clusters: s.clusters.map((c) =>
              c.id === win.clusterId
                ? { ...c, windowIds: c.windowIds.filter((id) => id !== windowId) }
                : c,
            ),
            windows: mapWindow(s.windows, windowId, (w) => ({ ...w, clusterId: null })),
          }
        })
      },

      toggleClusterCollapse: (clusterId) => {
        set((s) => {
          const cluster = s.clusters.find((c) => c.id === clusterId)
          if (!cluster) return s
          const newCollapsed = !cluster.collapsed
          return {
            clusters: s.clusters.map((c) =>
              c.id === clusterId ? { ...c, collapsed: newCollapsed } : c,
            ),
            windows: s.windows.map((w) =>
              cluster.windowIds.includes(w.id) ? { ...w, collapsed: newCollapsed } : w,
            ),
          }
        })
      },

      moveCluster: (clusterId, deltaX, deltaY) => {
        set((s) => {
          const cluster = s.clusters.find((c) => c.id === clusterId)
          if (!cluster) return s
          return {
            windows: s.windows.map((w) =>
              cluster.windowIds.includes(w.id)
                ? { ...w, x: w.x + deltaX, y: w.y + deltaY }
                : w,
            ),
          }
        })
      },

      // ── Preset actions ─────────────────────────────────────

      savePreset: (name) => {
        const id = crypto.randomUUID()
        const state = get()
        const preset: CanvasPreset = {
          id,
          name,
          windows: state.windows.map(({ connectionStatus, badgeCount, poppedOut, ...rest }) => rest),
          clusters: [...state.clusters],
          panX: state.panX,
          panY: state.panY,
          zoom: state.zoom,
        }
        set((s) => ({ presets: [...s.presets, preset] }))
        return id
      },

      loadPreset: (presetId) => {
        const preset = get().presets.find((p) => p.id === presetId)
        if (!preset) return
        const maxZ = preset.windows.reduce((m, w) => Math.max(m, w.zIndex), 0)
        set({
          windows: preset.windows.map((w) => ({
            ...w,
            connectionStatus: 'disconnected' as const,
            badgeCount: 0,
            poppedOut: false,
          })),
          clusters: [...preset.clusters],
          panX: preset.panX,
          panY: preset.panY,
          zoom: preset.zoom,
          nextZIndex: maxZ + 1,
        })
      },

      deletePreset: (presetId) => {
        set((s) => ({ presets: s.presets.filter((p) => p.id !== presetId) }))
      },

      // ── Canvas actions ─────────────────────────────────────

      setPan: (x, y) => set({ panX: x, panY: y }),

      setZoom: (zoom) => set({ zoom: clampZoom(zoom) }),

      fitAll: () => {
        const { windows } = get()
        if (windows.length === 0) {
          set({ panX: 0, panY: 0, zoom: 1 })
          return
        }
        const minX = Math.min(...windows.map((w) => w.x))
        const minY = Math.min(...windows.map((w) => w.y))
        const maxX = Math.max(...windows.map((w) => w.x + w.width))
        const maxY = Math.max(...windows.map((w) => w.y + w.height))
        const bw = maxX - minX
        const bh = maxY - minY
        const vw = window.innerWidth
        const vh = window.innerHeight
        const padding = 80
        const zoom = clampZoom(Math.min((vw - padding * 2) / bw, (vh - padding * 2) / bh))
        const panX = (vw - bw * zoom) / 2 - minX * zoom
        const panY = (vh - bh * zoom) / 2 - minY * zoom
        set({ panX, panY, zoom })
      },

      tileWindows: () => {
        const { windows } = get()
        const visible = windows.filter((w) => !w.collapsed)
        if (visible.length === 0) return
        const cols = Math.ceil(Math.sqrt(visible.length))
        const vw = window.innerWidth
        const vh = window.innerHeight
        const padding = 20
        const tileW = (vw - padding * (cols + 1)) / cols
        const rows = Math.ceil(visible.length / cols)
        const tileH = (vh - padding * (rows + 1)) / rows

        const tiled = new Map<string, Partial<CanvasWindow>>()
        visible.forEach((w, i) => {
          const col = i % cols
          const row = Math.floor(i / cols)
          tiled.set(w.id, {
            x: padding + col * (tileW + padding),
            y: padding + row * (tileH + padding),
            width: Math.max(200, tileW),
            height: Math.max(150, tileH),
            maximized: false,
            preMaxBounds: undefined,
          })
        })

        set((s) => ({
          windows: s.windows.map((w) => {
            const tile = tiled.get(w.id)
            return tile ? { ...w, ...tile } : w
          }),
          panX: 0,
          panY: 0,
          zoom: 1,
        }))
      },

      clearAll: () => set({ windows: [], clusters: [], panX: 0, panY: 0, zoom: 1, nextZIndex: 1 }),

      // ── Batch actions ──────────────────────────────────────

      collapseByType: (type) => {
        set((s) => ({
          windows: s.windows.map((w) => (w.type === type ? { ...w, collapsed: true } : w)),
        }))
      },

      removeByType: (type) => {
        set((s) => ({
          windows: s.windows.filter((w) => w.type !== type),
          clusters: s.clusters.map((c) => ({
            ...c,
            windowIds: c.windowIds.filter(
              (wid) => !s.windows.find((w) => w.id === wid && w.type === type),
            ),
          })),
        }))
      },

      pauseAll: () => {
        set((s) => ({ windows: s.windows.map((w) => ({ ...w, paused: true })) }))
      },

      resumeAll: () => {
        set((s) => ({ windows: s.windows.map((w) => ({ ...w, paused: false })) }))
      },

      collapseAll: () => {
        set((s) => ({ windows: s.windows.map((w) => ({ ...w, collapsed: true })) }))
      },

      expandAll: () => {
        set((s) => ({ windows: s.windows.map((w) => ({ ...w, collapsed: false })) }))
      },
    }),
    {
      name: 'cockpit:canvas',
      partialize: (state) => ({
        windows: state.windows.map(({ connectionStatus, badgeCount, poppedOut, ...rest }) => rest),
        clusters: state.clusters,
        presets: state.presets,
        panX: state.panX,
        panY: state.panY,
        zoom: state.zoom,
        nextZIndex: state.nextZIndex,
      }),
    },
  ),
)
