import { useCallback, useRef, useEffect } from 'react'
import { useUnifiedCanvasStore } from '../../stores/unifiedCanvasStore'
import { useCanvasStore } from '../../stores/canvasStore'
import { useAgentCanvasStore } from '../../stores/agentCanvasStore'
import { useWorkflowCanvasStore } from '../../stores/workflowCanvasStore'
import { useLoopCanvasStore } from '../../stores/loopCanvasStore'
import { useHarnessCanvasStore } from '../../stores/harnessCanvasStore'
import { useOrganismCanvasStore } from '../../stores/organismCanvasStore'
import { useAgentStore } from '../../stores/agentStore'
import { useCockpitStore } from '../../stores/cockpitStore'
import { fetchApi } from '../../api/client'
import { CanvasPalette } from './CanvasPalette'
import { CanvasWorkspace } from './CanvasWorkspace'
import { AgentCanvasWorkspace } from './AgentCanvasWorkspace'
import { WorkflowCanvasWorkspace } from './WorkflowCanvasWorkspace'
import { LoopCanvasWorkspace } from './LoopCanvasWorkspace'
import { HarnessCanvasWorkspace } from './HarnessCanvasWorkspace'
import { OrganismCanvasWorkspace } from './OrganismCanvasWorkspace'
import { LeftDrawer } from '../LeftDrawer'
import type { CanvasMode } from '../../stores/unifiedCanvasStore'
import { useState } from 'react'

function snapshotModeState(mode: CanvasMode): Record<string, unknown> {
  switch (mode) {
    case 'general': {
      const s = useCanvasStore.getState()
      return { windows: s.windows, clusters: s.clusters, presets: s.presets, panX: s.panX, panY: s.panY, zoom: s.zoom, nextZIndex: s.nextZIndex }
    }
    case 'agents': {
      const s = useAgentCanvasStore.getState()
      return { nodes: s.nodes, panX: s.panX, panY: s.panY, zoom: s.zoom, nextZIndex: s.nextZIndex, dismissedAgentIds: s.dismissedAgentIds }
    }
    case 'workflows': {
      const s = useWorkflowCanvasStore.getState()
      return { workflows: s.workflows, panX: s.panX, panY: s.panY, zoom: s.zoom, activeWorkflowId: s.activeWorkflowId, nodes: s.nodes, connections: s.connections }
    }
    case 'loops': {
      const s = useLoopCanvasStore.getState()
      return { panX: s.panX, panY: s.panY, zoom: s.zoom, activeLoopId: s.activeLoopId, activeLoopType: s.activeLoopType }
    }
    case 'harnesses': {
      const s = useHarnessCanvasStore.getState()
      return { panX: s.panX, panY: s.panY, zoom: s.zoom, activeHarnessId: s.activeHarnessId }
    }
    case 'organism': {
      const s = useOrganismCanvasStore.getState()
      return { panX: s.panX, panY: s.panY, zoom: s.zoom, activeNodeId: s.activeNodeId }
    }
  }
}

function restoreModeState(mode: CanvasMode, state: Record<string, unknown>) {
  switch (mode) {
    case 'general':
      useCanvasStore.setState(state)
      break
    case 'agents':
      useAgentCanvasStore.setState(state)
      break
    case 'workflows':
      useWorkflowCanvasStore.setState(state)
      break
    case 'loops':
      useLoopCanvasStore.setState(state)
      break
    case 'harnesses':
      useHarnessCanvasStore.setState(state)
      break
    case 'organism':
      useOrganismCanvasStore.setState(state)
      break
  }
}

export function UnifiedCanvasWorkspace() {
  const activeMode = useUnifiedCanvasStore((s) => s.activeMode)
  const savedCanvases = useUnifiedCanvasStore((s) => s.savedCanvases)
  const activeCanvasId = useUnifiedCanvasStore((s) => s.activeCanvasId)

  const storeAgents = useAgentStore((s) => s.agents)
  const fetchAgents = useAgentStore((s) => s.fetchAgents)
  const leftDrawerOpen = useCockpitStore((s) => s.leftDrawerOpen)
  const toggleLeftDrawer = useCockpitStore((s) => s.toggleLeftDrawer)
  const [tmuxSessions, setTmuxSessions] = useState<Array<{ name: string; windows: number }>>([])
  const [beastSessions, setBeastSessions] = useState<Array<{ name: string; shell?: string; shell_type?: string }>>([])
  const [vpsShells, setVpsShells] = useState<Array<{ id: string; label: string }>>([])
  const [beastShells, setBeastShells] = useState<Array<{ id: string; label: string }>>([])
  const [vpsMultiplexers, setVpsMultiplexers] = useState<Array<{ id: string; label: string; via: string }>>([])
  const [beastMultiplexers, setBeastMultiplexers] = useState<Array<{ id: string; label: string; via: string }>>([])
  const prevMode = useRef(activeMode)

  const KNOWN_AGENTS = [
    { id: 'agent-ceo', name: 'CEO' },
    { id: 'agent-computer_use', name: 'Computer Use' },
    { id: 'agent-customer_success', name: 'Customer Success' },
    { id: 'agent-engineering', name: 'Engineering' },
    { id: 'agent-finance', name: 'Finance' },
    { id: 'agent-hr', name: 'HR' },
    { id: 'agent-legal', name: 'Legal' },
    { id: 'agent-marketing', name: 'Marketing' },
    { id: 'agent-operations', name: 'Operations' },
    { id: 'agent-product', name: 'Product' },
    { id: 'agent-sales', name: 'Sales' },
    { id: 'organism-builder', name: 'Builder' },
    { id: 'organism-researcher', name: 'Researcher' },
    { id: 'organism-reviewer', name: 'Reviewer' },
    { id: 'organism-strategist', name: 'Strategist' },
    { id: 'organism-operator', name: 'Operator' },
    { id: 'organism-qa', name: 'QA' },
    { id: 'organism-finance_analyst', name: 'Finance Analyst' },
    { id: 'organism-content_producer', name: 'Content Producer' },
    { id: 'organism-sales_assistant', name: 'Sales Assistant' },
    { id: 'organism-infrastructure', name: 'Infrastructure' },
    { id: 'cc-code-reviewer', name: 'Code Reviewer' },
    { id: 'cc-researcher', name: 'EOS Researcher' },
    { id: 'cc-simplifier', name: 'Simplifier' },
    { id: 'cc-verifier', name: 'Verifier' },
  ]
  const agents = storeAgents.length > 0
    ? storeAgents
    : KNOWN_AGENTS.map((a) => ({ ...a, status: 'idle', skills: [] as string[], role: 'agent', last_action: '', last_active: '' }))

  useEffect(() => { fetchAgents() }, [fetchAgents])

  useEffect(() => {
    fetchApi<{ sessions?: Array<{ name: string; windows: number }> }>('/tmux/sessions')
      .then((data) => { if (data?.sessions) setTmuxSessions(data.sessions) })
      .catch(() => {})
    fetchApi<{ ok?: boolean; result_data?: { ok?: boolean; sessions?: Array<{ name: string; shell_type?: string }> }; sessions?: Array<{ name: string; shell_type?: string }> }>('/terminal/remote/sessions?node_id=windows-desktop')
      .then((data) => {
        const sessions = data?.result_data?.sessions ?? data?.sessions
        if (sessions) setBeastSessions(sessions)
      })
      .catch(() => {})
    fetchApi<{ ok?: boolean; shells?: Array<{ id: string; label: string }>; multiplexers?: Array<{ id: string; label: string; via: string }> }>('/tmux/shells')
      .then((data) => {
        if (data?.shells) setVpsShells(data.shells)
        if (data?.multiplexers) setVpsMultiplexers(data.multiplexers)
      })
      .catch(() => {})
    fetchApi<{ ok?: boolean; result_data?: { ok?: boolean; shells?: Array<{ id: string; label: string }>; multiplexers?: Array<{ id: string; label: string; via: string }> }; shells?: Array<{ id: string; label: string }>; multiplexers?: Array<{ id: string; label: string; via: string }> }>('/terminal/remote/shells?node_id=windows-desktop')
      .then((data) => {
        const shells = data?.result_data?.shells ?? data?.shells
        const muxes = data?.result_data?.multiplexers ?? data?.multiplexers
        if (shells) setBeastShells(shells)
        if (muxes) setBeastMultiplexers(muxes)
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    const handler = () => toggleLeftDrawer()
    document.addEventListener('canvas:toggle-palette', handler)
    return () => document.removeEventListener('canvas:toggle-palette', handler)
  }, [toggleLeftDrawer])

  const handleSetMode = useCallback((newMode: CanvasMode) => {
    const currentMode = useUnifiedCanvasStore.getState().activeMode
    const currentActiveId = useUnifiedCanvasStore.getState().activeCanvasId[currentMode]

    if (currentActiveId) {
      const snapshot = snapshotModeState(currentMode)
      useUnifiedCanvasStore.getState().updateCanvasState(currentActiveId, snapshot)
    }

    useUnifiedCanvasStore.getState().setMode(newMode)
    prevMode.current = newMode

    const newActiveId = useUnifiedCanvasStore.getState().activeCanvasId[newMode]
    if (newActiveId) {
      const canvas = useUnifiedCanvasStore.getState().savedCanvases.find((c) => c.id === newActiveId)
      if (canvas && Object.keys(canvas.state).length > 0) {
        restoreModeState(newMode, canvas.state)
      }
    }
  }, [])

  const handleAddWindow = useCallback((type: string, config?: Record<string, string>) => {
    const mode = useUnifiedCanvasStore.getState().activeMode
    if (mode === 'general') {
      useCanvasStore.getState().addWindow(type as never, config)
    } else if (mode === 'agents' && type === 'agent' && config?.agentId) {
      useAgentCanvasStore.getState().addNode(config.agentId, config.agentName ?? config.agentId)
    }
  }, [])

  const handleAction = useCallback((action: string) => {
    const mode = useUnifiedCanvasStore.getState().activeMode
    if (mode === 'agents') {
      const store = useAgentCanvasStore.getState()
      switch (action) {
        case 'showAll': store.showAll(); break
        case 'tile': store.tileNodes(); break
        case 'fitAll': store.fitAll(); break
      }
    } else if (mode === 'workflows') {
      const store = useWorkflowCanvasStore.getState()
      switch (action) {
        case 'addAction': store.addNode('action', 200, 200); break
        case 'addCondition': store.addNode('decision', 200, 200); break
        case 'addTrigger': store.addNode('trigger', 200, 200); break
      }
    } else if (mode === 'loops') {
      const store = useLoopCanvasStore.getState()
      switch (action) {
        case 'refreshLoops': store.fetchLoops(); store.fetchStages(); break
        case 'startAll':
          Object.entries(store.persistentLoops).forEach(([name, loop]) => {
            if (loop.state === 'stopped') store.startLoop(name)
          })
          break
        case 'stopAll':
          Object.entries(store.persistentLoops).forEach(([name, loop]) => {
            if (loop.state === 'running') store.stopLoop(name)
          })
          break
      }
    } else if (mode === 'harnesses') {
      const store = useHarnessCanvasStore.getState()
      switch (action) {
        case 'refreshRuntimes': store.fetchRuntimes(); break
      }
    } else if (mode === 'organism') {
      const store = useOrganismCanvasStore.getState()
      switch (action) {
        case 'refreshTopology': store.fetchTopology(); store.fetchHealth(); break
        case 'fitView': store.setPan(0, 0); store.setZoom(1); break
      }
    }
  }, [])

  const handleCreateCanvas = useCallback((name: string) => {
    const mode = useUnifiedCanvasStore.getState().activeMode
    const id = useUnifiedCanvasStore.getState().createCanvas(name)
    const snapshot = snapshotModeState(mode)
    useUnifiedCanvasStore.getState().updateCanvasState(id, snapshot)
  }, [])

  const handleLoadCanvas = useCallback((id: string) => {
    const canvas = useUnifiedCanvasStore.getState().savedCanvases.find((c) => c.id === id)
    if (!canvas) return

    const currentActiveId = useUnifiedCanvasStore.getState().activeCanvasId[canvas.mode]
    if (currentActiveId && currentActiveId !== id) {
      const snapshot = snapshotModeState(canvas.mode)
      useUnifiedCanvasStore.getState().updateCanvasState(currentActiveId, snapshot)
    }

    useUnifiedCanvasStore.getState().setActiveCanvas(canvas.mode, id)
    if (Object.keys(canvas.state).length > 0) {
      restoreModeState(canvas.mode, canvas.state)
    }
  }, [])

  const handleRenameCanvas = useCallback((id: string, name: string) => {
    useUnifiedCanvasStore.getState().renameCanvas(id, name)
  }, [])

  const handleDeleteCanvas = useCallback((id: string) => {
    useUnifiedCanvasStore.getState().deleteCanvas(id)
  }, [])

  const currentActiveCanvasId = activeCanvasId[activeMode]

  const modeProps = {
    mode: activeMode,
    onSetMode: handleSetMode,
    paletteOpen: leftDrawerOpen,
    onTogglePalette: toggleLeftDrawer,
  }

  return (
    <div className="relative w-full h-full">
      {activeMode === 'general' && <CanvasWorkspace {...modeProps} />}
      {activeMode === 'agents' && <AgentCanvasWorkspace {...modeProps} />}
      {activeMode === 'workflows' && <WorkflowCanvasWorkspace {...modeProps} />}
      {activeMode === 'loops' && <LoopCanvasWorkspace {...modeProps} />}
      {activeMode === 'harnesses' && <HarnessCanvasWorkspace {...modeProps} />}
      {activeMode === 'organism' && <OrganismCanvasWorkspace {...modeProps} />}

      <LeftDrawer>
        <CanvasPalette
          mode={activeMode}
          onAddWindow={handleAddWindow}
          onAction={handleAction}
          savedCanvases={savedCanvases}
          activeCanvasId={currentActiveCanvasId}
          onCreateCanvas={handleCreateCanvas}
          onLoadCanvas={handleLoadCanvas}
          onRenameCanvas={handleRenameCanvas}
          onDeleteCanvas={handleDeleteCanvas}
          open={true}
          onToggle={toggleLeftDrawer}
          agents={agents.map((a) => ({ id: a.id, name: a.name }))}
          tmuxSessions={tmuxSessions}
          beastSessions={beastSessions}
          vpsShells={vpsShells}
          beastShells={beastShells}
          vpsMultiplexers={vpsMultiplexers}
          beastMultiplexers={beastMultiplexers}
        />
      </LeftDrawer>
    </div>
  )
}
