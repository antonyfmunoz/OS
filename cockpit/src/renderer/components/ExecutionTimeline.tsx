import { useOrganismStore } from '../stores/organismStore'
import { formatDuration, relativeTime } from '../lib/time'

const LIFECYCLE_STAGES = [
  'proposed',
  'governance_check',
  'pending_approval',
  'approved',
  'executing',
  'verification',
  'completed',
  'failed',
  'rollback',
  'rejected',
] as const

const STAGE_COLORS: Record<string, string> = {
  proposed: 'bg-text-tertiary',
  governance_check: 'bg-purple',
  pending_approval: 'bg-warn',
  approved: 'bg-cyan',
  executing: 'bg-cyan animate-pulse',
  verification: 'bg-blue',
  completed: 'bg-ok',
  verified: 'bg-ok',
  failed: 'bg-danger',
  rollback: 'bg-warn',
  rolled_back: 'bg-warn',
  rejected: 'bg-danger',
  verification_failed: 'bg-danger',
}

const STAGE_TEXT_COLORS: Record<string, string> = {
  proposed: 'text-text-tertiary',
  governance_check: 'text-purple',
  pending_approval: 'text-warn',
  approved: 'text-cyan',
  executing: 'text-cyan',
  verification: 'text-blue',
  completed: 'text-ok',
  verified: 'text-ok',
  failed: 'text-danger',
  rollback: 'text-warn',
  rolled_back: 'text-warn',
  rejected: 'text-danger',
  verification_failed: 'text-danger',
}

const RISK_COLORS: Record<string, string> = {
  low: 'text-ok',
  medium: 'text-warn',
  high: 'text-danger',
  critical: 'text-danger',
}

interface EnvelopeEntry {
  envelope_id: string
  intent: string
  action_type: string
  source: string
  status: string
  risk_level: string
  blast_radius: string
  result_output: string
  result_success: boolean
  started_at: number
  completed_at: number
  approved_by: string
  estimated_manual_seconds: number
  retry_count: number
}

function stageIndex(status: string): number {
  const idx = LIFECYCLE_STAGES.indexOf(status as typeof LIFECYCLE_STAGES[number])
  if (idx >= 0) return idx
  if (status === 'verified') return 6
  if (status === 'verification_failed') return 7
  if (status === 'rolled_back') return 8
  return -1
}

function EnvelopeTimeline({ env }: { env: EnvelopeEntry }) {
  const currentStage = stageIndex(env.status)
  const duration = env.completed_at > 0 && env.started_at > 0
    ? (env.completed_at - env.started_at) * 1000
    : 0
  const isTerminal = ['completed', 'verified', 'failed', 'rejected', 'rolled_back', 'verification_failed', 'rollback'].includes(env.status)

  return (
    <div className="wv-card p-3 mb-2">
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <span className={`w-2 h-2 rounded-full shrink-0 ${STAGE_COLORS[env.status] ?? 'bg-text-tertiary'}`} />
        <span className="text-[11px] text-text-primary font-mono truncate flex-1">{env.intent}</span>
        <span className={`text-[10px] font-mono ${RISK_COLORS[env.risk_level] ?? 'text-text-tertiary'}`}>
          {env.risk_level.toUpperCase()}
        </span>
        <span className={`text-[10px] font-mono ${STAGE_TEXT_COLORS[env.status] ?? 'text-text-tertiary'}`}>
          {env.status.replace(/_/g, ' ').toUpperCase()}
        </span>
      </div>

      {/* Stage progress bar */}
      <div className="flex items-center gap-0.5 mb-2">
        {LIFECYCLE_STAGES.slice(0, 7).map((stage, i) => {
          const isActive = i === currentStage
          const isPast = i < currentStage
          const isFailed = isTerminal && i === currentStage && ['failed', 'rejected', 'rollback'].includes(env.status)

          return (
            <div
              key={stage}
              className={`h-1 flex-1 rounded-full transition-colors ${
                isFailed ? 'bg-danger' :
                isActive ? (isTerminal ? 'bg-ok' : 'bg-cyan') :
                isPast ? 'bg-cyan/40' :
                'bg-border'
              }`}
              title={stage.replace(/_/g, ' ')}
            />
          )
        })}
      </div>

      {/* Metadata */}
      <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[10px]">
        <span className="text-text-tertiary">
          {env.envelope_id.slice(0, 8)}
        </span>
        <span className="text-text-tertiary">{env.source}</span>
        <span className="text-text-tertiary">{env.action_type}</span>
        <span className="text-text-tertiary">{env.blast_radius}</span>
        {duration > 0 && (
          <span className="text-text-secondary font-mono">{formatDuration(duration)}</span>
        )}
        {env.retry_count > 0 && (
          <span className="text-warn font-mono">retry ×{env.retry_count}</span>
        )}
        {env.estimated_manual_seconds > 0 && (
          <span className="text-ok font-mono">
            saved {formatDuration(env.estimated_manual_seconds * 1000)}
          </span>
        )}
        {env.started_at > 0 && (
          <span className="text-text-tertiary">
            {relativeTime(new Date(env.started_at * 1000).toISOString())}
          </span>
        )}
      </div>

      {env.result_output && isTerminal && (
        <div className="mt-1.5 text-[10px] text-text-secondary truncate">{env.result_output}</div>
      )}
    </div>
  )
}

export function ExecutionTimeline() {
  const pending = useOrganismStore((s) => s.pendingEnvelopes)
  const active = useOrganismStore((s) => s.activeEnvelopes)
  const completed = useOrganismStore((s) => s.completedEnvelopes)
  const journalRecent = useOrganismStore((s) => s.journalRecent)

  const allEnvelopes = [
    ...active.map((e) => ({ ...e, _group: 'active' as const })),
    ...pending.map((e) => ({ ...e, _group: 'pending' as const })),
    ...completed.map((e) => ({ ...e, _group: 'completed' as const })),
  ]

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 mb-2">
        <h3 className="wv-label">Execution Lifecycle</h3>
        <span className="text-[10px] text-text-tertiary">
          {active.length} active · {pending.length} pending · {completed.length} completed
        </span>
      </div>

      <div className="overflow-y-auto flex-1 space-y-0">
        {allEnvelopes.length === 0 && (
          <p className="text-xs text-text-tertiary py-2">No envelopes in pipeline</p>
        )}
        {allEnvelopes.map((env) => (
          <EnvelopeTimeline key={env.envelope_id} env={env} />
        ))}
      </div>

      {journalRecent.length > 0 && (
        <div className="mt-3 border-t border-border pt-2">
          <h4 className="wv-label mb-1.5">Journal Trail</h4>
          <div className="space-y-0.5 max-h-32 overflow-y-auto">
            {journalRecent.slice(0, 15).map((entry, i) => (
              <div key={i} className="flex items-center gap-1.5 text-[10px]">
                <span className="font-mono text-text-tertiary w-16 shrink-0 truncate">{entry.phase}</span>
                <span className="text-text-primary truncate flex-1">{entry.envelope_id.slice(0, 8)}</span>
                <span className="text-text-tertiary">{entry.source}</span>
                <span className="text-text-tertiary">
                  {relativeTime(new Date(entry.timestamp * 1000).toISOString())}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
