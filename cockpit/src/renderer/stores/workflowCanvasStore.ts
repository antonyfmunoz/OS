import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { clampZoom } from '../utils/canvasCoords'

// ── Types ──────────────────────────────────────────────────────

export interface WorkflowSummary {
  id: string
  name: string
  triggerType: string
  stepCount: number
  active: boolean
  lastRun?: string
  lastStatus?: string
}

export type WorkflowStepType =
  | 'action'
  | 'decision'
  | 'approval_gate'
  | 'wait'
  | 'parallel'
  | 'notification'
  | 'trigger'
  | 'end'

export type WorkflowExecutionMode = 'human' | 'ai' | 'automated' | 'hybrid'

export interface WorkflowNodeConfig {
  executionMode?: WorkflowExecutionMode
  actionType?: string
  description?: string
  timeout?: number
  approvalRequired?: boolean
  branchConditions?: Record<string, string>
  metadata?: Record<string, unknown>
}

export interface WorkflowNode {
  id: string
  stepType: WorkflowStepType
  label: string
  x: number
  y: number
  width: number
  height: number
  config: WorkflowNodeConfig
}

export type WorkflowPort = 'default' | 'true' | 'false'

export interface WorkflowConnection {
  id: string
  fromNodeId: string
  fromPort: WorkflowPort
  toNodeId: string
}

export interface WorkflowCanvasState {
  workflows: WorkflowSummary[]
  activeWorkflowId: string | null

  nodes: WorkflowNode[]
  connections: WorkflowConnection[]
  selectedNodeId: string | null
  panX: number
  panY: number
  zoom: number
  isDirty: boolean

  setWorkflows: (workflows: WorkflowSummary[]) => void
  openWorkflow: (id: string) => void
  closeWorkflow: () => void
  createWorkflow: (name: string) => string
  deleteWorkflow: (id: string) => void

  addNode: (stepType: WorkflowStepType, x: number, y: number) => string
  removeNode: (id: string) => void
  updateNode: (id: string, partial: Partial<WorkflowNode>) => void
  moveNode: (id: string, x: number, y: number) => void
  selectNode: (id: string | null) => void

  addConnection: (fromId: string, fromPort: string, toId: string) => string
  removeConnection: (id: string) => void

  setPan: (x: number, y: number) => void
  setZoom: (zoom: number) => void

  markDirty: () => void
  markClean: () => void
}

// ── Default heights per step type ──────────────────────────────

const STEP_HEIGHT: Record<WorkflowStepType, number> = {
  trigger: 60,
  end: 60,
  action: 100,
  decision: 100,
  approval_gate: 100,
  wait: 80,
  parallel: 100,
  notification: 80,
}

const STEP_LABEL: Record<WorkflowStepType, string> = {
  trigger: 'Trigger',
  end: 'End',
  action: 'Action',
  decision: 'Decision',
  approval_gate: 'Approval Gate',
  wait: 'Wait',
  parallel: 'Parallel',
  notification: 'Notification',
}

// ── Store ──────────────────────────────────────────────────────

export const useWorkflowCanvasStore = create<WorkflowCanvasState>()(
  persist(
    (set, get) => ({
      workflows: [],
      activeWorkflowId: null,

      nodes: [],
      connections: [],
      selectedNodeId: null,
      panX: 0,
      panY: 0,
      zoom: 1,
      isDirty: false,

      setWorkflows: (workflows) => set({ workflows }),

      openWorkflow: (id) =>
        set({
          activeWorkflowId: id,
          nodes: [],
          connections: [],
          selectedNodeId: null,
          isDirty: false,
          panX: 0,
          panY: 0,
          zoom: 1,
        }),

      closeWorkflow: () =>
        set({
          activeWorkflowId: null,
          nodes: [],
          connections: [],
          selectedNodeId: null,
          isDirty: false,
        }),

      createWorkflow: (name) => {
        const id = crypto.randomUUID()
        const triggerId = crypto.randomUUID()
        const endId = crypto.randomUUID()
        const connId = crypto.randomUUID()

        set((s) => ({
          workflows: [
            ...s.workflows,
            { id, name, triggerType: 'manual', stepCount: 0, active: false },
          ],
          activeWorkflowId: id,
          nodes: [
            {
              id: triggerId,
              stepType: 'trigger' as const,
              label: 'Trigger',
              x: 100,
              y: 200,
              width: 200,
              height: 60,
              config: {},
            },
            {
              id: endId,
              stepType: 'end' as const,
              label: 'End',
              x: 600,
              y: 200,
              width: 200,
              height: 60,
              config: {},
            },
          ],
          connections: [
            {
              id: connId,
              fromNodeId: triggerId,
              fromPort: 'default' as const,
              toNodeId: endId,
            },
          ],
          selectedNodeId: null,
          isDirty: true,
          panX: 0,
          panY: 0,
          zoom: 1,
        }))

        return id
      },

      deleteWorkflow: (id) =>
        set((s) => ({
          workflows: s.workflows.filter((w) => w.id !== id),
          ...(s.activeWorkflowId === id
            ? {
                activeWorkflowId: null,
                nodes: [],
                connections: [],
                selectedNodeId: null,
                isDirty: false,
              }
            : {}),
        })),

      addNode: (stepType, x, y) => {
        const id = crypto.randomUUID()
        set((s) => ({
          nodes: [
            ...s.nodes,
            {
              id,
              stepType,
              label: STEP_LABEL[stepType],
              x,
              y,
              width: 200,
              height: STEP_HEIGHT[stepType],
              config: {},
            },
          ],
          isDirty: true,
        }))
        return id
      },

      removeNode: (id) =>
        set((s) => ({
          nodes: s.nodes.filter((n) => n.id !== id),
          connections: s.connections.filter(
            (c) => c.fromNodeId !== id && c.toNodeId !== id,
          ),
          selectedNodeId: s.selectedNodeId === id ? null : s.selectedNodeId,
          isDirty: true,
        })),

      updateNode: (id, partial) =>
        set((s) => ({
          nodes: s.nodes.map((n) =>
            n.id === id ? { ...n, ...partial } : n,
          ),
          isDirty: true,
        })),

      moveNode: (id, x, y) =>
        set((s) => ({
          nodes: s.nodes.map((n) => (n.id === id ? { ...n, x, y } : n)),
          isDirty: true,
        })),

      selectNode: (id) => set({ selectedNodeId: id }),

      addConnection: (fromId, fromPort, toId) => {
        const id = crypto.randomUUID()
        set((s) => ({
          connections: [
            ...s.connections,
            { id, fromNodeId: fromId, fromPort: fromPort as WorkflowPort, toNodeId: toId },
          ],
          isDirty: true,
        }))
        return id
      },

      removeConnection: (id) =>
        set((s) => ({
          connections: s.connections.filter((c) => c.id !== id),
          isDirty: true,
        })),

      setPan: (x, y) => set({ panX: x, panY: y }),
      setZoom: (zoom) => set({ zoom: clampZoom(zoom) }),

      markDirty: () => set({ isDirty: true }),
      markClean: () => set({ isDirty: false }),
    }),
    {
      name: 'cockpit:workflow-canvas',
      partialize: (state) => ({
        workflows: state.workflows,
        panX: state.panX,
        panY: state.panY,
        zoom: state.zoom,
      }),
    },
  ),
)
