import { useState, useMemo } from 'react'
import { clsx } from 'clsx'
import { useCockpitStore } from '../stores/cockpitStore.ts'
import { relativeTime } from '../lib/time.ts'
import type { WorkflowResponse } from '../api/client.ts'

const STATUS_COLOR: Record<WorkflowResponse['last_status'], string> = {
  success: 'wv-badge-ok',
  failed: 'wv-badge-danger',
  running: 'wv-badge-warn',
  never: 'wv-badge-cyan',
}

type StatusFilter = WorkflowResponse['last_status'] | 'all'

function StatsBar({ workflows }: { workflows: WorkflowResponse[] }) {
  const running = workflows.filter((w) => w.last_status === 'running').length
  const success = workflows.filter((w) => w.last_status === 'success').length
  const failed = workflows.filter((w) => w.last_status === 'failed').length
  const totalRuns = workflows.reduce((s, w) => s + w.run_count, 0)

  return (
    <div className="grid grid-cols-4 gap-3 mb-4">
      <div className="wv-card p-3 text-center"><div className="wv-metric text-warn">{running}</div><div className="wv-label mt-1">RUNNING</div></div>
      <div className="wv-card p-3 text-center"><div className="wv-metric text-ok">{success}</div><div className="wv-label mt-1">SUCCESS</div></div>
      <div className="wv-card p-3 text-center"><div className="wv-metric text-danger">{failed}</div><div className="wv-label mt-1">FAILED</div></div>
      <div className="wv-card p-3 text-center"><div className="wv-metric text-cyan">{totalRuns}</div><div className="wv-label mt-1">TOTAL RUNS</div></div>
    </div>
  )
}

function WorkflowCard({ workflow, selected, onClick }: { workflow: WorkflowResponse; selected: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={clsx('w-full text-left wv-card p-4 transition-colors', selected && 'ring-1 ring-cyan')}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-[12px] text-text-primary font-mono">{workflow.name}</span>
        <span className={clsx('wv-badge', STATUS_COLOR[workflow.last_status])}>{workflow.last_status}</span>
      </div>
      <div className="text-[10px] text-text-tertiary mb-2 font-mono">{workflow.schedule}</div>
      <div className="flex items-center justify-between text-[10px] text-text-tertiary">
        <span>{workflow.run_count} runs</span>
        <span>{workflow.avg_duration_ms > 0 ? `${(workflow.avg_duration_ms / 1000).toFixed(1)}s avg` : '—'}</span>
        <span>{workflow.last_run ? relativeTime(workflow.last_run) : 'never'}</span>
      </div>
    </button>
  )
}

function DetailPanel({ workflow, onClose }: { workflow: WorkflowResponse; onClose: () => void }) {
  const [triggering, setTriggering] = useState(false)
  const [triggerResult, setTriggerResult] = useState<string | null>(null)

  const handleTrigger = async () => {
    setTriggering(true)
    try {
      const { api } = await import('../api/client.ts')
      const res = await api.workflowTrigger(workflow.id)
      setTriggerResult(res.ok ? `Triggered (trace: ${res.trace_id?.slice(0, 8)}...)` : 'Trigger failed')
      useCockpitStore.getState().fetchAll()
    } catch {
      setTriggerResult('Error triggering workflow')
    } finally {
      setTriggering(false)
    }
  }

  return (
    <div className="w-96 border-l border-border flex flex-col bg-surface">
      <div className="flex items-center justify-between p-4 border-b border-border">
        <span className="wv-label">WORKFLOW DETAIL</span>
        <button onClick={onClose} className="text-text-tertiary hover:text-text-primary text-[14px] transition-colors">✕</button>
      </div>
      <div className="p-4 space-y-4 overflow-y-auto flex-1">
        <div><div className="wv-label mb-1">NAME</div><div className="text-[14px] text-text-primary font-mono">{workflow.name}</div></div>
        <div><div className="wv-label mb-1">SCHEDULE</div><div className="text-[11px] text-cyan font-mono">{workflow.schedule}</div></div>
        <div className="flex gap-4">
          <div><div className="wv-label mb-1">STATUS</div><span className={clsx('wv-badge', STATUS_COLOR[workflow.last_status])}>{workflow.last_status}</span></div>
          <div><div className="wv-label mb-1">RUNS</div><div className="wv-metric text-text-primary">{workflow.run_count}</div></div>
        </div>
        <div><div className="wv-label mb-1">AVG DURATION</div><div className="text-[11px] text-text-secondary">{workflow.avg_duration_ms > 0 ? `${(workflow.avg_duration_ms / 1000).toFixed(1)}s` : 'N/A'}</div></div>
        <div><div className="wv-label mb-1">LAST RUN</div><div className="text-[11px] text-text-secondary">{workflow.last_run ? new Date(workflow.last_run).toLocaleString() : 'Never'}</div></div>
        <button
          onClick={handleTrigger}
          disabled={triggering}
          className="w-full mt-2 px-4 py-2 text-[10px] font-mono uppercase tracking-wider bg-cyan/10 text-cyan border border-cyan-dim hover:bg-cyan/20 transition-colors disabled:opacity-40"
        >
          {triggering ? 'Triggering...' : 'Trigger Run'}
        </button>
        {triggerResult && <div className="text-[10px] text-text-tertiary">{triggerResult}</div>}
      </div>
    </div>
  )
}

export function Workflows() {
  const { workflows } = useCockpitStore()
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const filtered = useMemo(() => {
    return workflows.filter((w) => {
      if (statusFilter !== 'all' && w.last_status !== statusFilter) return false
      if (search) { const q = search.toLowerCase(); return w.name.toLowerCase().includes(q) || w.schedule.toLowerCase().includes(q) }
      return true
    })
  }, [workflows, statusFilter, search])

  const selectedWorkflow = workflows.find((w) => w.id === selectedId) ?? null

  return (
    <div className="h-full flex flex-col p-4 overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">Workflows</h1>
        <span className="text-[10px] font-mono text-text-tertiary uppercase">{workflows.length} registered</span>
      </div>
      <StatsBar workflows={workflows} />
      <div className="wv-card p-3 mb-4 flex items-center gap-3 flex-wrap">
        <div className="flex gap-1">
          {(['all', 'running', 'success', 'failed', 'never'] as const).map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)} className={clsx('px-2 py-1 text-[10px] font-mono uppercase tracking-wider border transition-colors', statusFilter === s ? 'text-cyan bg-cyan-glow border-cyan-dim' : 'text-text-tertiary border-border hover:text-text-secondary hover:border-border-active')}>{s}</button>
          ))}
        </div>
        <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search workflows..." className="flex-1 min-w-[160px] bg-surface border border-border text-text-primary text-[11px] font-mono px-2 py-1 placeholder:text-text-tertiary focus:border-cyan-dim focus:outline-none" />
      </div>
      <div className="flex-1 flex min-h-0">
        <div className="flex-1 overflow-y-auto"><div className="grid grid-cols-2 gap-3">
          {filtered.length === 0 && <div className="col-span-2 text-center text-text-tertiary text-[11px] py-12">No workflows matching current filters</div>}
          {filtered.map((wf) => <WorkflowCard key={wf.id} workflow={wf} selected={wf.id === selectedId} onClick={() => setSelectedId(wf.id === selectedId ? null : wf.id)} />)}
        </div></div>
        {selectedWorkflow && <DetailPanel workflow={selectedWorkflow} onClose={() => setSelectedId(null)} />}
      </div>
    </div>
  )
}
