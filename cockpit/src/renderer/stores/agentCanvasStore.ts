import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { clampZoom } from '../utils/canvasCoords'

// ── Types ──────────────────────────────────────────────────────

export interface AgentCanvasNode {
  agentId: string
  label: string
  x: number
  y: number
  width: number
  height: number
  zIndex: number
  collapsed: boolean
  maximized: boolean
  preMaxBounds?: { x: number; y: number; width: number; height: number }
}

export interface AgentCanvasState {
  nodes: AgentCanvasNode[]
  panX: number
  panY: number
  zoom: number
  nextZIndex: number
  dismissedAgentIds: string[]

  addNode: (agentId: string, label: string, x?: number, y?: number) => void
  removeNode: (agentId: string) => void
  updateNode: (agentId: string, partial: Partial<AgentCanvasNode>) => void
  bringToFront: (agentId: string) => void
  toggleCollapse: (agentId: string) => void
  toggleMaximize: (agentId: string) => void

  setPan: (x: number, y: number) => void
  setZoom: (zoom: number) => void
  fitAll: () => void
  tileNodes: () => void

  syncAgents: (agents: Array<{ id: string; name: string; status: string }>) => void
  showAll: () => void
  dismissAgent: (agentId: string) => void
}

// ── Constants ─────────────────────────────────────────────────

const NODE_W = 400
const NODE_H = 500
const GRID_COLS = 3
const GRID_GAP = 20

function mapNode(
  nodes: AgentCanvasNode[],
  agentId: string,
  fn: (n: AgentCanvasNode) => AgentCanvasNode,
): AgentCanvasNode[] {
  return nodes.map((n) => (n.agentId === agentId ? fn(n) : n))
}

// ── Store ─────────────────────────────────────────────────────

export const useAgentCanvasStore = create<AgentCanvasState>()(
  persist(
    (set, get) => ({
      nodes: [],
      panX: 0,
      panY: 0,
      zoom: 1,
      nextZIndex: 1,
      dismissedAgentIds: [],

      addNode: (agentId, label, x, y) => {
        const state = get()
        if (state.nodes.some((n) => n.agentId === agentId)) return
        const idx = state.nodes.length
        const col = idx % GRID_COLS
        const row = Math.floor(idx / GRID_COLS)
        set({
          nodes: [
            ...state.nodes,
            {
              agentId,
              label,
              x: x ?? col * (NODE_W + GRID_GAP) + 50,
              y: y ?? row * (NODE_H + GRID_GAP) + 50,
              width: NODE_W,
              height: NODE_H,
              zIndex: state.nextZIndex,
              collapsed: false,
              maximized: false,
            },
          ],
          nextZIndex: state.nextZIndex + 1,
        })
      },

      removeNode: (agentId) =>
        set((s) => ({ nodes: s.nodes.filter((n) => n.agentId !== agentId) })),

      updateNode: (agentId, partial) =>
        set((s) => ({ nodes: mapNode(s.nodes, agentId, (n) => ({ ...n, ...partial })) })),

      bringToFront: (agentId) =>
        set((s) => ({
          nodes: mapNode(s.nodes, agentId, (n) => ({ ...n, zIndex: s.nextZIndex })),
          nextZIndex: s.nextZIndex + 1,
        })),

      toggleCollapse: (agentId) =>
        set((s) => ({
          nodes: mapNode(s.nodes, agentId, (n) => ({ ...n, collapsed: !n.collapsed })),
        })),

      toggleMaximize: (agentId) =>
        set((s) => ({
          nodes: mapNode(s.nodes, agentId, (n) => {
            if (n.maximized) {
              const b = n.preMaxBounds ?? { x: n.x, y: n.y, width: NODE_W, height: NODE_H }
              return { ...n, maximized: false, x: b.x, y: b.y, width: b.width, height: b.height, preMaxBounds: undefined }
            }
            return { ...n, maximized: true, preMaxBounds: { x: n.x, y: n.y, width: n.width, height: n.height } }
          }),
        })),

      setPan: (x, y) => set({ panX: x, panY: y }),

      setZoom: (zoom) => set({ zoom: clampZoom(zoom) }),

      fitAll: () => {
        const { nodes } = get()
        if (nodes.length === 0) return
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
        for (const n of nodes) {
          minX = Math.min(minX, n.x)
          minY = Math.min(minY, n.y)
          maxX = Math.max(maxX, n.x + n.width)
          maxY = Math.max(maxY, n.y + n.height)
        }
        const bw = maxX - minX + 100
        const bh = maxY - minY + 100
        const vw = window.innerWidth - 240
        const vh = window.innerHeight - 100
        const zoom = clampZoom(Math.min(vw / bw, vh / bh))
        set({ panX: -(minX - 50) * zoom, panY: -(minY - 50) * zoom, zoom })
      },

      tileNodes: () => {
        const { nodes } = get()
        const visible = nodes.filter((n) => !n.collapsed)
        if (visible.length === 0) return
        const cols = Math.ceil(Math.sqrt(visible.length))
        const updated = nodes.map((n) => {
          const idx = visible.indexOf(n)
          if (idx === -1) return n
          const col = idx % cols
          const row = Math.floor(idx / cols)
          return { ...n, x: col * (NODE_W + GRID_GAP) + 50, y: row * (NODE_H + GRID_GAP) + 50 }
        })
        set({ nodes: updated })
      },

      syncAgents: (agents) => {
        const state = get()
        const dismissed = new Set(state.dismissedAgentIds)
        const agentIds = new Set(agents.map((a) => a.id))
        const existingIds = new Set(state.nodes.map((n) => n.agentId))

        const kept = state.nodes.filter((n) => agentIds.has(n.agentId))

        const newAgents = agents.filter((a) => !existingIds.has(a.id) && !dismissed.has(a.id))
        const startIdx = kept.length
        const newNodes: AgentCanvasNode[] = newAgents.map((a, i) => {
          const idx = startIdx + i
          const col = idx % GRID_COLS
          const row = Math.floor(idx / GRID_COLS)
          return {
            agentId: a.id,
            label: a.name,
            x: col * (NODE_W + GRID_GAP) + 50,
            y: row * (NODE_H + GRID_GAP) + 50,
            width: NODE_W,
            height: NODE_H,
            zIndex: state.nextZIndex + i,
            collapsed: false,
            maximized: false,
          }
        })

        if (newNodes.length > 0 || kept.length !== state.nodes.length) {
          set({
            nodes: [...kept, ...newNodes],
            nextZIndex: state.nextZIndex + newNodes.length,
          })
        }
      },

      showAll: () => set({ dismissedAgentIds: [] }),

      dismissAgent: (agentId) =>
        set((s) => ({
          nodes: s.nodes.filter((n) => n.agentId !== agentId),
          dismissedAgentIds: [...s.dismissedAgentIds, agentId],
        })),
    }),
    {
      name: 'cockpit:agent-canvas',
      partialize: (state) => ({
        nodes: state.nodes,
        panX: state.panX,
        panY: state.panY,
        zoom: state.zoom,
        nextZIndex: state.nextZIndex,
        dismissedAgentIds: state.dismissedAgentIds,
      }),
    },
  ),
)
