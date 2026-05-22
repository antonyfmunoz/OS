import { useCockpitStore } from '../stores/cockpitStore.ts'
import { clsx } from 'clsx'
import { relativeTime } from '../lib/time.ts'

export function Production() {
  const { workflows, tasks } = useCockpitStore()

  const productionWorkflows = workflows.filter((w) => w.last_status === 'running' || w.last_status === 'success')
  const activeTasks = tasks.filter((t) => t.status === 'in_progress')

  return (
    <div className="h-full flex flex-col p-4 overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">Production</h1>
        <span className="text-[10px] font-mono text-text-tertiary uppercase">{productionWorkflows.length} active pipelines</span>
      </div>
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="wv-card p-3 text-center"><div className="wv-metric text-ok">{productionWorkflows.filter((w) => w.last_status === 'success').length}</div><div className="wv-label mt-1">HEALTHY</div></div>
        <div className="wv-card p-3 text-center"><div className="wv-metric text-warn">{productionWorkflows.filter((w) => w.last_status === 'running').length}</div><div className="wv-label mt-1">RUNNING</div></div>
        <div className="wv-card p-3 text-center"><div className="wv-metric text-cyan">{activeTasks.length}</div><div className="wv-label mt-1">ACTIVE TASKS</div></div>
      </div>
      <div className="grid grid-cols-2 gap-4 flex-1 min-h-0 overflow-y-auto">
        <div className="wv-card overflow-hidden">
          <div className="px-3 py-2 border-b border-border"><span className="wv-label">PIPELINES</span></div>
          <div className="divide-y divide-border/50">
            {productionWorkflows.length === 0 && <div className="text-center text-text-tertiary text-[11px] py-8">No active pipelines</div>}
            {productionWorkflows.map((w) => (
              <div key={w.id} className="flex items-center gap-3 px-3 py-2 text-[11px] font-mono">
                <span className={clsx('wv-badge', w.last_status === 'success' ? 'wv-badge-ok' : 'wv-badge-warn')}>{w.last_status}</span>
                <span className="text-text-primary flex-1 truncate">{w.name}</span>
                <span className="text-text-tertiary text-[10px]">{w.run_count} runs</span>
                <span className="text-text-tertiary text-[10px]">{w.last_run ? relativeTime(w.last_run) : '—'}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="wv-card overflow-hidden">
          <div className="px-3 py-2 border-b border-border"><span className="wv-label">ACTIVE WORK</span></div>
          <div className="divide-y divide-border/50">
            {activeTasks.length === 0 && <div className="text-center text-text-tertiary text-[11px] py-8">No tasks in progress</div>}
            {activeTasks.map((t) => (
              <div key={t.id} className="flex items-center gap-3 px-3 py-2 text-[11px] font-mono">
                <span className="wv-badge wv-badge-warn">active</span>
                <span className="text-text-primary flex-1 truncate">{t.title}</span>
                <span className="text-cyan text-[10px]">{t.agent}</span>
                <span className="text-text-tertiary text-[10px]">{relativeTime(t.updated_at)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
