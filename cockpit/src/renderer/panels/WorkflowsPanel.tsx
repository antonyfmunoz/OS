import { useTaskStore } from '../stores/taskStore'
import { usePolling } from '../hooks/usePolling'

export function WorkflowsPanel() {
  const workflows = useTaskStore((s) => s.workflows)
  const fetchWorkflows = useTaskStore((s) => s.fetchWorkflows)
  const triggerWorkflow = useTaskStore((s) => s.triggerWorkflow)

  usePolling(fetchWorkflows, 5000)

  return (
    <div className="flex flex-col h-full overflow-y-auto p-4">
      <div className="flex items-center mb-4">
        <h2 className="text-lg font-semibold text-text-primary">Workflows</h2>
        <span className="ml-2 text-xs text-text-tertiary">{workflows.length} registered</span>
      </div>
      <div className="space-y-2">
        {workflows.map((wf) => (
          <div key={wf.id} className="wv-card flex items-center gap-3 px-3 py-2.5">
            <span
              className="w-2 h-2 rounded-full shrink-0"
              style={{
                background: wf.last_status === 'success'
                  ? 'var(--color-ok)'
                  : wf.last_status === 'failed'
                    ? 'var(--color-danger)'
                    : 'var(--color-warn)',
              }}
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-text-primary truncate">{wf.name}</p>
              <p className="text-xs text-text-tertiary">
                {wf.run_count} runs · avg {wf.avg_duration_ms}ms
              </p>
            </div>
            <button
              onClick={() => triggerWorkflow(wf.id)}
              className="px-2 py-1 text-xs font-mono uppercase rounded text-cyan bg-cyan-glow border border-border transition-colors"
            >
              run
            </button>
          </div>
        ))}
        {workflows.length === 0 && (
          <p className="text-center text-xs py-8 text-text-tertiary">No workflows registered</p>
        )}
      </div>
    </div>
  )
}
