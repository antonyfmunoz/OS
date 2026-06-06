import { StatusBadge } from './StatusBadge'

export interface CronJob {
  id: string
  agent: string
  name: string
  schedule: string
  lastFired: string | null
  nextFire: string | null
  status: string
  onRun?: () => void
}

interface CronTableProps {
  jobs: CronJob[]
  loading?: boolean
}

function formatTime(ts: string | null): string {
  if (!ts) return '-'
  try {
    const d = new Date(ts)
    const now = Date.now()
    const diff = now - d.getTime()
    if (diff < 60000) return 'just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    if (diff < 86400000) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
  } catch {
    return ts.slice(0, 16)
  }
}

export function CronTable({ jobs, loading }: CronTableProps) {
  if (loading) {
    return (
      <div className="text-center py-8 text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
        Loading scheduled workflows...
      </div>
    )
  }

  if (jobs.length === 0) {
    return (
      <div className="text-center py-8 text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
        No scheduled workflows
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs font-mono">
        <thead>
          <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
            <th className="text-left px-3 py-2 text-[10px] uppercase tracking-wider" style={{ color: 'var(--color-text-tertiary)' }}>Agent</th>
            <th className="text-left px-3 py-2 text-[10px] uppercase tracking-wider" style={{ color: 'var(--color-text-tertiary)' }}>Job</th>
            <th className="text-left px-3 py-2 text-[10px] uppercase tracking-wider" style={{ color: 'var(--color-text-tertiary)' }}>Schedule</th>
            <th className="text-left px-3 py-2 text-[10px] uppercase tracking-wider" style={{ color: 'var(--color-text-tertiary)' }}>Last</th>
            <th className="text-left px-3 py-2 text-[10px] uppercase tracking-wider" style={{ color: 'var(--color-text-tertiary)' }}>Next</th>
            <th className="text-left px-3 py-2 text-[10px] uppercase tracking-wider" style={{ color: 'var(--color-text-tertiary)' }}>Status</th>
            <th className="px-3 py-2"></th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr
              key={job.id}
              className="transition-colors"
              style={{ borderBottom: '1px solid var(--color-border)' }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--color-surface-raised)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              <td className="px-3 py-2" style={{ color: 'var(--color-text-secondary)' }}>{job.agent}</td>
              <td className="px-3 py-2" style={{ color: 'var(--color-text-primary)' }}>{job.name}</td>
              <td className="px-3 py-2" style={{ color: 'var(--color-text-tertiary)' }}>{job.schedule}</td>
              <td className="px-3 py-2" style={{ color: 'var(--color-text-tertiary)' }}>{formatTime(job.lastFired)}</td>
              <td className="px-3 py-2" style={{ color: 'var(--color-text-tertiary)' }}>{formatTime(job.nextFire)}</td>
              <td className="px-3 py-2"><StatusBadge status={job.status} dot /></td>
              <td className="px-3 py-2">
                {job.onRun && (
                  <button
                    onClick={job.onRun}
                    className="text-[9px] px-2 py-0.5 rounded uppercase tracking-wider"
                    style={{
                      color: 'var(--color-cyan)',
                      background: 'var(--color-cyan-glow)',
                      border: 'none',
                      cursor: 'pointer',
                    }}
                  >
                    Run
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
