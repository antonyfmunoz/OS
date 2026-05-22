import { useCockpitStore } from '../stores/cockpitStore.ts'
import { clsx } from 'clsx'
import { relativeTime } from '../lib/time.ts'

export function Experiments() {
  const { workflows, tasks } = useCockpitStore()

  const neverRun = workflows.filter((w) => w.last_status === 'never')
  const blockedTasks = tasks.filter((t) => t.status === 'blocked')
  const pendingTasks = tasks.filter((t) => t.status === 'pending' && t.priority === 'low')

  return (
    <div className="h-full flex flex-col p-4 overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">Experiments</h1>
        <span className="text-[10px] font-mono text-text-tertiary uppercase">sandbox</span>
      </div>
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="wv-card p-3 text-center"><div className="wv-metric text-cyan">{neverRun.length}</div><div className="wv-label mt-1">UNTESTED</div></div>
        <div className="wv-card p-3 text-center"><div className="wv-metric text-danger">{blockedTasks.length}</div><div className="wv-label mt-1">BLOCKED</div></div>
        <div className="wv-card p-3 text-center"><div className="wv-metric text-text-tertiary">{pendingTasks.length}</div><div className="wv-label mt-1">LOW-PRI QUEUE</div></div>
      </div>
      <div className="grid grid-cols-2 gap-4 flex-1 min-h-0 overflow-y-auto">
        <div className="wv-card overflow-hidden">
          <div className="px-3 py-2 border-b border-border"><span className="wv-label">UNTESTED WORKFLOWS</span></div>
          <div className="divide-y divide-border/50">
            {neverRun.length === 0 && <div className="text-center text-text-tertiary text-[11px] py-8">All workflows have been run</div>}
            {neverRun.map((w) => (
              <div key={w.id} className="flex items-center gap-3 px-3 py-2 text-[11px] font-mono">
                <span className="wv-badge wv-badge-cyan">new</span>
                <span className="text-text-primary flex-1 truncate">{w.name}</span>
                <span className="text-text-tertiary text-[10px]">{w.schedule}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="wv-card overflow-hidden">
          <div className="px-3 py-2 border-b border-border"><span className="wv-label">BLOCKED / PENDING</span></div>
          <div className="divide-y divide-border/50">
            {blockedTasks.length === 0 && pendingTasks.length === 0 && <div className="text-center text-text-tertiary text-[11px] py-8">No experiments queued</div>}
            {blockedTasks.map((t) => (
              <div key={t.id} className="flex items-center gap-3 px-3 py-2 text-[11px] font-mono">
                <span className="wv-badge wv-badge-danger">blocked</span>
                <span className="text-text-primary flex-1 truncate">{t.title}</span>
                <span className="text-text-tertiary text-[10px]">{relativeTime(t.updated_at)}</span>
              </div>
            ))}
            {pendingTasks.map((t) => (
              <div key={t.id} className="flex items-center gap-3 px-3 py-2 text-[11px] font-mono">
                <span className="wv-badge wv-badge-cyan">pending</span>
                <span className="text-text-primary flex-1 truncate">{t.title}</span>
                <span className="text-text-tertiary text-[10px]">{relativeTime(t.updated_at)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
