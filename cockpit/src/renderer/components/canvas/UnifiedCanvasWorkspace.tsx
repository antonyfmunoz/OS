import { useState, useCallback, useRef } from 'react'
import { useUnifiedCanvasStore } from '../../stores/unifiedCanvasStore'
import { useCanvasStore } from '../../stores/canvasStore'
import { useAgentCanvasStore } from '../../stores/agentCanvasStore'
import { useWorkflowCanvasStore } from '../../stores/workflowCanvasStore'
import { CanvasPalette } from './CanvasPalette'
import { CanvasWorkspace } from './CanvasWorkspace'
import { AgentCanvasWorkspace } from './AgentCanvasWorkspace'
import { WorkflowCanvasWorkspace } from './WorkflowCanvasWorkspace'
import type { CanvasMode } from '../../stores/unifiedCanvasStore'

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
  }
}

export function UnifiedCanvasWorkspace() {
  const activeMode = useUnifiedCanvasStore((s) => s.activeMode)
  const savedCanvases = useUnifiedCanvasStore((s) => s.savedCanvases)
  const activeCanvasId = useUnifiedCanvasStore((s) => s.activeCanvasId)

  const [paletteOpen, setPaletteOpen] = useState(true)
  const prevMode = useRef(activeMode)

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

  const palette = (
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
      open={paletteOpen}
      onToggle={() => setPaletteOpen((v) => !v)}
    />
  )

  const modeProps = {
    palette,
    mode: activeMode,
    onSetMode: handleSetMode,
  }

  return (
    <div className="relative w-full h-full">
      {activeMode === 'general' && <CanvasWorkspace {...modeProps} />}
      {activeMode === 'agents' && <AgentCanvasWorkspace {...modeProps} />}
      {activeMode === 'workflows' && <WorkflowCanvasWorkspace {...modeProps} />}
    </div>
  )
}
