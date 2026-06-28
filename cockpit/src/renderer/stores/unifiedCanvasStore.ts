import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type CanvasMode = 'general' | 'agents' | 'workflows'

export interface SavedCanvas {
  id: string
  name: string
  mode: CanvasMode
  state: Record<string, unknown>
  updatedAt: string
}

interface UnifiedCanvasState {
  activeMode: CanvasMode
  savedCanvases: SavedCanvas[]
  activeCanvasId: { general: string | null; agents: string | null; workflows: string | null }

  setMode: (mode: CanvasMode) => void
  createCanvas: (name: string) => string
  renameCanvas: (id: string, name: string) => void
  deleteCanvas: (id: string) => void
  setActiveCanvas: (mode: CanvasMode, id: string | null) => void
  updateCanvasState: (id: string, state: Record<string, unknown>) => void
}

export const useUnifiedCanvasStore = create<UnifiedCanvasState>()(
  persist(
    (set, get) => ({
      activeMode: 'general',
      savedCanvases: [],
      activeCanvasId: { general: null, agents: null, workflows: null },

      setMode: (mode) => set({ activeMode: mode }),

      createCanvas: (name) => {
        const id = crypto.randomUUID()
        const { activeMode, savedCanvases, activeCanvasId } = get()
        set({
          savedCanvases: [
            ...savedCanvases,
            { id, name, mode: activeMode, state: {}, updatedAt: new Date().toISOString() },
          ],
          activeCanvasId: { ...activeCanvasId, [activeMode]: id },
        })
        return id
      },

      renameCanvas: (id, name) =>
        set((s) => ({
          savedCanvases: s.savedCanvases.map((c) => (c.id === id ? { ...c, name } : c)),
        })),

      deleteCanvas: (id) =>
        set((s) => {
          const canvas = s.savedCanvases.find((c) => c.id === id)
          const updated: Partial<UnifiedCanvasState> = {
            savedCanvases: s.savedCanvases.filter((c) => c.id !== id),
          }
          if (canvas && s.activeCanvasId[canvas.mode] === id) {
            updated.activeCanvasId = { ...s.activeCanvasId, [canvas.mode]: null }
          }
          return updated
        }),

      setActiveCanvas: (mode, id) =>
        set((s) => ({ activeCanvasId: { ...s.activeCanvasId, [mode]: id } })),

      updateCanvasState: (id, state) =>
        set((s) => ({
          savedCanvases: s.savedCanvases.map((c) =>
            c.id === id ? { ...c, state, updatedAt: new Date().toISOString() } : c,
          ),
        })),
    }),
    {
      name: 'cockpit:unified-canvas',
      version: 2,
      migrate: () => ({
        activeMode: 'general' as const,
        savedCanvases: [],
        activeCanvasId: { general: null, agents: null, workflows: null },
      }),
      partialize: (s) => ({
        activeMode: s.activeMode,
        savedCanvases: s.savedCanvases,
        activeCanvasId: s.activeCanvasId,
      }),
    },
  ),
)

export function selectCanvasesForMode(mode: CanvasMode): (state: UnifiedCanvasState) => SavedCanvas[] {
  return (state) => state.savedCanvases.filter((c) => c.mode === mode)
}
