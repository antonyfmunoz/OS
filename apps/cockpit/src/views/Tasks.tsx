import { useState, useMemo } from 'react'
import { clsx } from 'clsx'
import { useCockpitStore } from '../stores/cockpitStore.ts'
import { relativeTime } from '../lib/time.ts'
import type { TaskResponse } from '../api/client.ts'

type StatusFilter = TaskResponse['status'] | 'all'

const STATUS_COLOR: Record<TaskResponse['status'], string> = {
  pending: 'wv-badge-cyan',
  in_progress: 'wv-badge-warn',
  completed: 'wv-badge-ok',
  blocked: 'wv-badge-danger',
}

const PRIORITY_COLOR: Record<TaskResponse['priority'], string> = {
  low: 'text-text-tertiary',
  medium: 'text-text-secondary',
  high: 'text-warn',
  critical: 'text-danger',
}

function StatsBar({ tasks }: { tasks: TaskResponse[] }) {
  const pending = tasks.filter((t) => t.status === 'pending').length
  const inProgress = tasks.filter((t) => t.status === 'in_progress').length
  const completed = tasks.filter((t) => t.status === 'completed').length
  const blocked = tasks.filter((t) => t.status === 'blocked').length

  return (
    <div className="grid grid-cols-4 gap-3 mb-4">
      <div className="wv-card p-3 text-center"><div className="wv-metric text-cyan">{pending}</div><div className="wv-label mt-1">PENDING</div></div>
      <div className="wv-card p-3 text-center"><div className="wv-metric text-warn">{inProgress}</div><div className="wv-label mt-1">IN PROGRESS</div></div>
      <div className="wv-card p-3 text-center"><div className="wv-metric text-ok">{completed}</div><div className="wv-label mt-1">COMPLETED</div></div>
      <div className="wv-card p-3 text-center"><div className="wv-metric text-danger">{blocked}</div><div className="wv-label mt-1">BLOCKED</div></div>
    </div>
  )
}

function TaskRow({ task, selected, onClick }: { task: TaskResponse; selected: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={clsx('w-full text-left flex items-center gap-3 py-3 px-3 text-[11px] font-mono border-b border-border/50 transition-colors', selected ? 'bg-cyan/5 border-l-2 border-l-cyan' : 'hover:bg-surface-hover')}>
      <span className={clsx('wv-badge shrink-0', STATUS_COLOR[task.status])}>{task.status.replace('_', ' ')}</span>
      <span className={clsx('text-[10px] shrink-0 uppercase', PRIORITY_COLOR[task.priority])}>{task.priority}</span>
      <span className="text-text-primary flex-1 truncate">{task.title}</span>
      <span className="text-text-tertiary shrink-0 text-[10px]">{task.agent}</span>
      <span className="text-text-tertiary shrink-0 w-14 text-right text-[10px]">{relativeTime(task.updated_at)}</span>
    </button>
  )
}

function DetailPanel({ task, onClose }: { task: TaskResponse; onClose: () => void }) {
  return (
    <div className="w-96 border-l border-border flex flex-col bg-surface">
      <div className="flex items-center justify-between p-4 border-b border-border">
        <span className="wv-label">TASK DETAIL</span>
        <button onClick={onClose} className="text-text-tertiary hover:text-text-primary text-[14px] transition-colors">✕</button>
      </div>
      <div className="p-4 space-y-4 overflow-y-auto flex-1">
        <div><div className="wv-label mb-1">TITLE</div><div className="text-[12px] text-text-primary">{task.title}</div></div>
        <div className="flex gap-4">
          <div><div className="wv-label mb-1">STATUS</div><span className={clsx('wv-badge', STATUS_COLOR[task.status])}>{task.status.replace('_', ' ')}</span></div>
          <div><div className="wv-label mb-1">PRIORITY</div><span className={clsx('text-[11px] font-mono uppercase', PRIORITY_COLOR[task.priority])}>{task.priority}</span></div>
        </div>
        <div><div className="wv-label mb-1">AGENT</div><div className="text-[11px] text-cyan font-mono">{task.agent}</div></div>
        <div><div className="wv-label mb-1">CREATED</div><div className="text-[11px] text-text-secondary">{new Date(task.created_at).toLocaleString()}</div></div>
        <div><div className="wv-label mb-1">UPDATED</div><div className="text-[11px] text-text-secondary">{new Date(task.updated_at).toLocaleString()}</div></div>
      </div>
    </div>
  )
}

export function Tasks() {
  const { tasks } = useCockpitStore()
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const filtered = useMemo(() => {
    return tasks.filter((t) => {
      if (statusFilter !== 'all' && t.status !== statusFilter) return false
      if (search) { const q = search.toLowerCase(); return t.title.toLowerCase().includes(q) || t.agent.toLowerCase().includes(q) }
      return true
    })
  }, [tasks, statusFilter, search])

  const selectedTask = tasks.find((t) => t.id === selectedId) ?? null

  return (
    <div className="h-full flex flex-col p-4 overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">Tasks</h1>
        <span className="text-[10px] font-mono text-text-tertiary uppercase">{tasks.length} total</span>
      </div>
      <StatsBar tasks={tasks} />
      <div className="wv-card p-3 mb-4 flex items-center gap-3 flex-wrap">
        <div className="flex gap-1">
          {(['all', 'pending', 'in_progress', 'completed', 'blocked'] as const).map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)} className={clsx('px-2 py-1 text-[10px] font-mono uppercase tracking-wider border transition-colors', statusFilter === s ? 'text-cyan bg-cyan-glow border-cyan-dim' : 'text-text-tertiary border-border hover:text-text-secondary hover:border-border-active')}>{s === 'in_progress' ? 'Active' : s}</button>
          ))}
        </div>
        <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search tasks..." className="flex-1 min-w-[160px] bg-surface border border-border text-text-primary text-[11px] font-mono px-2 py-1 placeholder:text-text-tertiary focus:border-cyan-dim focus:outline-none" />
      </div>
      <div className="flex-1 flex min-h-0">
        <div className="flex-1 wv-card overflow-y-auto">
          <div className="sticky top-0 bg-surface border-b border-border px-3 py-2 flex items-center gap-3 text-[10px] font-mono text-text-tertiary uppercase tracking-wider">
            <span className="w-20">STATUS</span><span className="w-14">PRI</span><span className="flex-1">TITLE</span><span className="w-20">AGENT</span><span className="w-14 text-right">AGE</span>
          </div>
          {filtered.length === 0 && <div className="text-center text-text-tertiary text-[11px] py-12">No tasks matching current filters</div>}
          {filtered.map((task) => <TaskRow key={task.id} task={task} selected={task.id === selectedId} onClick={() => setSelectedId(task.id === selectedId ? null : task.id)} />)}
        </div>
        {selectedTask && <DetailPanel task={selectedTask} onClose={() => setSelectedId(null)} />}
      </div>
    </div>
  )
}
