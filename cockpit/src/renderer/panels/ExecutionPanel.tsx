import { useState, useEffect, useRef } from 'react'
import { useExecutionStore, type ExecutionLayer } from '../stores/executionStore'

const LAYERS: Array<{ id: ExecutionLayer; icon: string; label: string; enabled: boolean }> = [
  { id: 'native', icon: '◲', label: 'Native Windows', enabled: true },
  { id: 'container', icon: '⊞', label: 'Container', enabled: true },
  { id: 'wsl', icon: '⊟', label: 'WSL2', enabled: false },
  { id: 'vm', icon: '⊠', label: 'Hypervisor VM', enabled: false },
]

const AUTHORITY_COLORS: Record<string, string> = {
  autonomous_execute: 'bg-ok',
  supervised_execute: 'bg-warn',
  approve_execute: 'bg-cyan',
  notify_execute: 'bg-cyan',
  deny: 'bg-danger',
}

const RISK_COLORS: Record<string, string> = {
  negligible: 'text-ok',
  low: 'text-cyan',
  medium: 'text-warn',
  high: 'text-danger',
  critical: 'text-danger',
}

export function ExecutionPanel() {
  const [selectedLayer, setSelectedLayer] = useState<ExecutionLayer>('container')
  const [taskInput, setTaskInput] = useState('')
  const slots = useExecutionStore((s) => s.slots)
  const selectedSlot = useExecutionStore((s) => s.selectedSlot)
  const authorityPreview = useExecutionStore((s) => s.authorityPreview)
  const fetchStatus = useExecutionStore((s) => s.fetchStatus)
  const fetchLog = useExecutionStore((s) => s.fetchLog)
  const previewAuthority = useExecutionStore((s) => s.previewAuthority)
  const startExecution = useExecutionStore((s) => s.startExecution)
  const stopExecution = useExecutionStore((s) => s.stopExecution)
  const pauseExecution = useExecutionStore((s) => s.pauseExecution)
  const resumeExecution = useExecutionStore((s) => s.resumeExecution)
  const selectSlot = useExecutionStore((s) => s.selectSlot)
  const logEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchStatus()
    previewAuthority(selectedLayer)
    const interval = setInterval(fetchStatus, 3000)
    return () => clearInterval(interval)
  }, [fetchStatus, previewAuthority, selectedLayer])

  useEffect(() => {
    if (slots.length > 0) {
      fetchLog(selectedSlot)
    }
  }, [selectedSlot, slots.length, fetchLog])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [slots])

  const activeSlot = slots.find((s) => s.slot === selectedSlot)

  function handleStart() {
    if (!taskInput.trim()) return
    startExecution(selectedLayer, taskInput.trim())
    setTaskInput('')
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Top bar */}
      <div className="flex items-center gap-3 px-4 py-2 flex-shrink-0 border-b border-border">
        <h2 className="text-sm font-semibold text-text-primary mr-2">Execution Substrate</h2>

        <div className="flex gap-1">
          {LAYERS.map((layer) => (
            <button
              key={layer.id}
              disabled={!layer.enabled}
              onClick={() => {
                setSelectedLayer(layer.id)
                previewAuthority(layer.id)
              }}
              className={`px-2.5 py-1 rounded text-xs border transition-colors ${
                selectedLayer === layer.id
                  ? 'text-cyan bg-cyan-glow border-cyan'
                  : 'text-text-secondary border-border'
              }`}
              style={{ opacity: layer.enabled ? 1 : 0.3 }}
            >
              {layer.icon} {layer.label}
            </button>
          ))}
        </div>

        <div className="flex-1" />

        <div className="flex gap-1">
          {(slots.length > 0 ? slots : [{ slot: 0 }]).map((s) => (
            <button
              key={s.slot}
              onClick={() => selectSlot(s.slot)}
              className={`px-2 py-0.5 rounded text-xs ${
                selectedSlot === s.slot ? 'text-text-primary bg-surface-raised' : 'text-text-tertiary'
              }`}
            >
              Agent {s.slot + 1}
            </button>
          ))}
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Canvas area (70%) */}
        <div className="flex-1 flex items-center justify-center bg-surface-raised">
          {activeSlot && activeSlot.status === 'running' ? (
            selectedLayer === 'container' ? (
              <div className="text-center">
                <p className="text-sm text-text-secondary">noVNC Canvas</p>
                <p className="text-xs mt-1 text-text-tertiary">
                  Connect to ws://beast:608{selectedSlot}/websockify
                </p>
              </div>
            ) : (
              <div className="text-center">
                <p className="text-sm text-text-secondary">Native Screenshot Stream</p>
                <p className="text-xs mt-1 text-text-tertiary">Polling desktop.screenshot via node mesh</p>
              </div>
            )
          ) : (
            <div className="text-center">
              <p className="text-sm text-text-secondary">No active execution</p>
              <p className="text-xs mt-1 text-text-tertiary">Select a layer and assign a task to begin</p>
            </div>
          )}
        </div>

        {/* Sidebar (30%) */}
        <div className="flex flex-col gap-3 overflow-y-auto p-3 w-80 border-l border-border bg-canvas">
          {/* Authority badge */}
          {authorityPreview && (
            <div className="wv-card flex items-center gap-2 px-3 py-2">
              <span className={`w-2 h-2 rounded-full ${AUTHORITY_COLORS[authorityPreview.authority_class] || 'bg-text-tertiary'}`} />
              <div className="flex-1">
                <p className="text-xs font-mono text-text-primary">
                  {authorityPreview.authority_class.toUpperCase().replace(/_/g, ' ')}
                </p>
                <p className="text-xs text-text-tertiary">
                  Risk:{' '}
                  <span className={RISK_COLORS[authorityPreview.risk_class] || 'text-text-tertiary'}>
                    {authorityPreview.risk_class}
                  </span>
                  {' | '}
                  Approval: {authorityPreview.approval_requirement.replace(/_/g, ' ')}
                </p>
              </div>
            </div>
          )}

          {/* Task input */}
          <div>
            <label className="text-xs mb-1 block text-text-secondary">Task</label>
            <textarea
              value={taskInput}
              onChange={(e) => setTaskInput(e.target.value)}
              placeholder="Describe the task..."
              rows={3}
              className="w-full px-2 py-1.5 rounded text-xs bg-transparent text-text-primary border border-border outline-none resize-none"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && e.ctrlKey) {
                  e.preventDefault()
                  handleStart()
                }
              }}
            />
            <div className="flex gap-1.5 mt-1.5">
              <button
                onClick={handleStart}
                disabled={!taskInput.trim() || authorityPreview?.authority_class === 'deny'}
                className="flex-1 px-2 py-1 rounded text-xs font-medium bg-cyan text-canvas disabled:opacity-30"
              >
                Start
              </button>
              {activeSlot && activeSlot.status === 'running' && (
                <>
                  <button
                    onClick={() => pauseExecution(selectedSlot)}
                    className="px-2 py-1 rounded text-xs text-warn border border-warn"
                  >
                    Pause
                  </button>
                  <button
                    onClick={() => stopExecution(selectedSlot)}
                    className="px-2 py-1 rounded text-xs text-danger border border-danger"
                  >
                    Stop
                  </button>
                </>
              )}
              {activeSlot && activeSlot.status === 'paused' && (
                <button
                  onClick={() => resumeExecution(selectedSlot)}
                  className="px-2 py-1 rounded text-xs text-ok border border-ok"
                >
                  Resume
                </button>
              )}
            </div>
          </div>

          {/* Step counter */}
          {activeSlot && (
            <div className="flex items-center justify-between px-2">
              <span className="text-xs text-text-tertiary">Steps: {activeSlot.stepCount} / 50</span>
              <span className={`text-xs font-mono px-1.5 py-0.5 rounded bg-surface-raised ${
                activeSlot.status === 'running' ? 'text-ok'
                  : activeSlot.status === 'paused' ? 'text-warn'
                  : 'text-text-tertiary'
              }`}>
                {activeSlot.status.toUpperCase()}
              </span>
            </div>
          )}

          {/* Governance + Action log */}
          <div className="flex-1 overflow-y-auto">
            <p className="text-xs font-medium mb-1 text-text-secondary">Execution Log</p>
            {activeSlot?.actionLog.length ? (
              <div className="flex flex-col gap-1">
                {activeSlot.actionLog.map((entry, i) => (
                  <div key={i} className="px-2 py-1.5 rounded text-xs bg-surface-raised">
                    <div className="flex items-center justify-between">
                      <span className="text-text-primary">#{entry.step} {entry.action_type}</span>
                      <span className={`text-xs ${entry.approved ? 'text-ok' : 'text-danger'}`}>
                        {entry.approved ? 'APPROVED' : 'DENIED'}
                      </span>
                    </div>
                    <p className="mt-0.5 font-mono text-[10px] text-text-tertiary">{entry.authority_class}</p>
                  </div>
                ))}
                <div ref={logEndRef} />
              </div>
            ) : (
              <p className="text-xs px-2 text-text-tertiary">No actions yet</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
