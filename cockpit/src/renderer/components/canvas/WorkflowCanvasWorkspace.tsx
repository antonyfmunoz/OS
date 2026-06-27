import { useState, useCallback } from 'react'
import { Plus, ArrowLeft } from 'lucide-react'
import { BaseCanvas } from './BaseCanvas'
import { CanvasToolbar } from './CanvasToolbar'
import { useWorkflowCanvasStore } from '../../stores/workflowCanvasStore'
import { WorkflowNode as WorkflowNodeComponent } from './WorkflowNode'
import { WorkflowConnection } from './WorkflowConnection'
import { clampZoom } from '../../utils/canvasCoords'

function WorkflowList() {
  const workflows = useWorkflowCanvasStore((s) => s.workflows)
  const openWorkflow = useWorkflowCanvasStore((s) => s.openWorkflow)
  const createWorkflow = useWorkflowCanvasStore((s) => s.createWorkflow)
  const deleteWorkflow = useWorkflowCanvasStore((s) => s.deleteWorkflow)

  const [newName, setNewName] = useState('')

  const handleCreate = useCallback(() => {
    if (!newName.trim()) return
    const id = createWorkflow(newName.trim())
    setNewName('')
    openWorkflow(id)
  }, [newName, createWorkflow, openWorkflow])

  return (
    <div className="h-full overflow-auto p-4" style={{ background: 'var(--color-canvas)' }}>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-[14px] font-medium" style={{ color: 'var(--color-text-primary)' }}>Workflows</h2>
        <div className="flex-1" />
        <div className="flex gap-1">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleCreate() }}
            placeholder="New workflow name..."
            className="px-2 py-1 text-[12px] rounded"
            style={{ background: 'var(--color-surface)', color: 'var(--color-text-primary)', border: '1px solid var(--color-border)', outline: 'none', width: 180 }}
          />
          <button
            onClick={handleCreate}
            className="flex items-center gap-1 px-2 py-1 rounded text-[12px]"
            style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }}
          >
            <Plus size={12} /> Create
          </button>
        </div>
      </div>

      {workflows.length === 0 ? (
        <div className="text-[12px] mt-8 text-center" style={{ color: 'var(--color-text-tertiary)' }}>
          No workflows yet. Create one to get started.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {workflows.map((wf) => (
            <div
              key={wf.id}
              className="p-3 rounded-lg cursor-pointer"
              style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
              onClick={() => openWorkflow(wf.id)}
              onContextMenu={(e) => {
                e.preventDefault()
                if (confirm(`Delete workflow "${wf.name}"?`)) deleteWorkflow(wf.id)
              }}
            >
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full" style={{ background: wf.active ? '#22c55e' : '#6b7280' }} />
                <span className="text-[13px] font-medium truncate" style={{ color: 'var(--color-text-primary)' }}>{wf.name}</span>
              </div>
              <div className="flex gap-2 mt-1.5">
                <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-tertiary)' }}>
                  {wf.triggerType}
                </span>
                <span className="text-[10px]" style={{ color: 'var(--color-text-tertiary)' }}>
                  {wf.stepCount} steps
                </span>
              </div>
              {wf.lastRun && (
                <div className="text-[10px] mt-1" style={{ color: 'var(--color-text-tertiary)' }}>
                  Last: {wf.lastStatus} — {wf.lastRun}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function WorkflowEditor() {
  const nodes = useWorkflowCanvasStore((s) => s.nodes)
  const connections = useWorkflowCanvasStore((s) => s.connections)
  const selectedNodeId = useWorkflowCanvasStore((s) => s.selectedNodeId)
  const panX = useWorkflowCanvasStore((s) => s.panX)
  const panY = useWorkflowCanvasStore((s) => s.panY)
  const zoom = useWorkflowCanvasStore((s) => s.zoom)
  const setPan = useWorkflowCanvasStore((s) => s.setPan)
  const setZoom = useWorkflowCanvasStore((s) => s.setZoom)
  const closeWorkflow = useWorkflowCanvasStore((s) => s.closeWorkflow)
  const addNode = useWorkflowCanvasStore((s) => s.addNode)
  const moveNode = useWorkflowCanvasStore((s) => s.moveNode)
  const selectNode = useWorkflowCanvasStore((s) => s.selectNode)
  const removeConnection = useWorkflowCanvasStore((s) => s.removeConnection)
  const isDirty = useWorkflowCanvasStore((s) => s.isDirty)

  const [selectedConnectionId, setSelectedConnectionId] = useState<string | null>(null)

  const handleContextMenu = useCallback(
    (canvasX: number, canvasY: number) => {
      addNode('action', canvasX, canvasY)
    },
    [addNode],
  )

  const handleZoomIn = useCallback(() => setZoom(clampZoom(zoom + 0.1)), [zoom, setZoom])
  const handleZoomOut = useCallback(() => setZoom(clampZoom(zoom - 0.1)), [zoom, setZoom])
  const handleZoomReset = useCallback(() => {
    setZoom(1)
    setPan(0, 0)
  }, [setZoom, setPan])

  return (
    <div className="h-full flex flex-col">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 px-3 h-8 shrink-0" style={{ borderBottom: '1px solid var(--color-border)', background: 'var(--color-surface)' }}>
        <button onClick={closeWorkflow} className="flex items-center gap-1 text-[11px]" style={{ color: 'var(--color-text-secondary)' }}>
          <ArrowLeft size={12} /> All Workflows
        </button>
        {isDirty && <span className="text-[10px] px-1 rounded" style={{ background: 'var(--color-warn-dim)', color: 'var(--color-warn)' }}>Unsaved</span>}
      </div>

      <div className="flex-1">
        <BaseCanvas
          panX={panX}
          panY={panY}
          zoom={zoom}
          setPan={setPan}
          setZoom={setZoom}
          onContextMenu={handleContextMenu}
          toolbar={
            <CanvasToolbar
              zoom={zoom}
              onZoomIn={handleZoomIn}
              onZoomOut={handleZoomOut}
              onZoomReset={handleZoomReset}
              onFitAll={() => {}}
              onTile={() => {}}
              onTogglePalette={() => {}}
              paletteOpen={false}
            />
          }
        >
          {/* SVG layer for connections */}
          <svg className="absolute inset-0 pointer-events-none" style={{ overflow: 'visible', width: 1, height: 1 }}>
            <defs>
              <marker id="wf-arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                <path d="M0,0 L8,3 L0,6" fill="var(--color-text-tertiary)" />
              </marker>
              <marker id="wf-arrowhead-active" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                <path d="M0,0 L8,3 L0,6" fill="var(--color-cyan)" />
              </marker>
            </defs>
            {connections.map((conn) => (
              <WorkflowConnection
                key={conn.id}
                connection={conn}
                nodes={nodes}
                selected={conn.id === selectedConnectionId}
                onSelect={(id) => { setSelectedConnectionId(id); selectNode(null) }}
              />
            ))}
          </svg>

          {/* Nodes */}
          {nodes.map((node) => (
            <WorkflowNodeComponent
              key={node.id}
              node={node}
              zoom={zoom}
              selected={node.id === selectedNodeId}
              onSelect={selectNode}
              onMove={moveNode}
            />
          ))}
        </BaseCanvas>
      </div>
    </div>
  )
}

export function WorkflowCanvasWorkspace() {
  const activeWorkflowId = useWorkflowCanvasStore((s) => s.activeWorkflowId)

  if (activeWorkflowId) {
    return <WorkflowEditor />
  }
  return <WorkflowList />
}
