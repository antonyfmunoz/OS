import { create } from 'zustand'
import type { Panel } from './cockpitStore'

export interface ViewContext {
  active_route: Panel
  active_surface: string
  selected_object_type?: string
  selected_object_id?: string
  selected_object_summary?: string
  selected_node?: string
  selected_path?: string
  selected_repo?: string
  selected_branch?: string
  selected_diff_id?: string
  selected_session_id?: string
  selected_agent_run_id?: string
  current_work_packet_id?: string
  visible_context_summary?: string
  available_actions?: string[]
  risk_context?: string
  proof_context?: string
  trace_context?: string
}

interface ViewContextState {
  context: ViewContext
  drawerOpen: boolean
  setContext: (ctx: Partial<ViewContext>) => void
  setRoute: (route: Panel) => void
  selectObject: (type: string, id: string, summary?: string) => void
  clearSelection: () => void
  openDrawer: (type: string, id: string, summary?: string) => void
  closeDrawer: () => void
}

export const useViewContextStore = create<ViewContextState>((set) => ({
  context: {
    active_route: 'commandcenter',
    active_surface: 'main',
  },
  drawerOpen: false,
  setContext: (ctx) =>
    set((s) => ({ context: { ...s.context, ...ctx } })),
  setRoute: (route) =>
    set((s) => ({
      context: {
        ...s.context,
        active_route: route,
        selected_object_type: undefined,
        selected_object_id: undefined,
        selected_object_summary: undefined,
      },
    })),
  selectObject: (type, id, summary) =>
    set((s) => ({
      context: {
        ...s.context,
        selected_object_type: type,
        selected_object_id: id,
        selected_object_summary: summary,
      },
    })),
  clearSelection: () =>
    set((s) => ({
      context: {
        ...s.context,
        selected_object_type: undefined,
        selected_object_id: undefined,
        selected_object_summary: undefined,
      },
    })),
  openDrawer: (type, id, summary) =>
    set((s) => ({
      drawerOpen: true,
      context: {
        ...s.context,
        selected_object_type: type,
        selected_object_id: id,
        selected_object_summary: summary,
      },
    })),
  closeDrawer: () =>
    set(() => ({
      drawerOpen: false,
    })),
}))
