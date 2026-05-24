import { useTaskStore } from '../stores/taskStore'
import { usePolling } from '../hooks/usePolling'
import { TaskBlock } from '../components/TaskBlock'

export function TasksPanel() {
  const tasks = useTaskStore((s) => s.tasks)
  const workflows = useTaskStore((s) => s.workflows)
  const viewMode = useTaskStore((s) => s.viewMode)
  const fetchTasks = useTaskStore((s) => s.fetchTasks)
  const fetchWorkflows = useTaskStore((s) => s.fetchWorkflows)
  const setViewMode = useTaskStore((s) => s.setViewMode)
  const triggerWorkflow = useTaskStore((s) => s.triggerWorkflow)

  usePolling(() => {
    fetchTasks()
    fetchWorkflows()
  }, 5000)

  const tabs = [
    { id: 'tasks' as const, label: 'Tasks', count: tasks.length },
    { id: 'workflows' as const, label: 'Workflows', count: workflows.length },
  ]

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar */}
      <div
        className="flex items-center gap-4 px-4 h-10 shrink-0"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setViewMode(tab.id)}
            className="hud-text pb-2 transition-colors"
            style={{
              color: viewMode === tab.id ? 'var(--accent-cyan)' : 'var(--text-secondary)',
              borderBottom: viewMode === tab.id ? '2px solid var(--accent-cyan)' : '2px solid transparent',
            }}
          >
            {tab.label}
            <span className="ml-1" style={{ color: 'var(--text-tertiary)' }}>
              {tab.count}
            </span>
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {viewMode === 'tasks' && (
          <div className="space-y-2">
            {tasks.map((task) => (
              <TaskBlock
                key={task.id}
                id={task.id}
                title={task.title}
                status={task.status}
                agent={task.agent}
                timestamp={task.updated_at}
              />
            ))}
            {tasks.length === 0 && (
              <p className="text-center text-xs py-8" style={{ color: 'var(--text-tertiary)' }}>
                No tasks recorded
              </p>
            )}
          </div>
        )}

        {viewMode === 'workflows' && (
          <div className="space-y-2">
            {workflows.map((wf) => (
              <div
                key={wf.id}
                className="flex items-center gap-3 px-3 py-2.5 rounded"
                style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}
              >
                <span
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{
                    background: wf.last_status === 'success'
                      ? 'var(--accent-green)'
                      : wf.last_status === 'failed'
                        ? 'var(--accent-red)'
                        : 'var(--accent-amber)',
                  }}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm truncate">{wf.name}</p>
                  <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                    {wf.run_count} runs · avg {wf.avg_duration_ms}ms
                  </p>
                </div>
                <button
                  onClick={() => triggerWorkflow(wf.id)}
                  className="px-2 py-1 text-xs font-mono uppercase rounded transition-colors"
                  style={{ color: 'var(--accent-cyan)', background: 'var(--glow-cyan)', border: '1px solid var(--border)' }}
                >
                  run
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
