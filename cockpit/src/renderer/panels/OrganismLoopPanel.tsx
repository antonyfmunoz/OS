import { useState } from 'react'
import { useOrganismLoopStore } from '../stores/organismLoopStore'
import { usePolling } from '../hooks/usePolling'

const STATUS_COLORS: Record<string, string> = {
  completed: 'bg-ok/20 text-ok',
  failed: 'bg-danger/20 text-danger',
  denied: 'bg-warn/20 text-warn',
  blocked: 'bg-warn/20 text-warn',
  approved: 'bg-cyan/20 text-cyan',
  created: 'bg-surface-overlay text-text-secondary',
  queued: 'bg-surface-overlay text-text-secondary',
  executing: 'bg-cyan/20 text-cyan',
  governance_pending: 'bg-warn/20 text-warn',
}

const LOOP_STEPS = [
  'Intent',
  'Reality',
  'WorkPacket',
  'Governance',
  'Execution',
  'Proof',
  'Memory',
  'Reality Update',
  'Cockpit',
] as const

const STEP_KEYS: Record<string, number> = {
  reality_check: 1,
  work_packet_created: 2,
  queue_ingested: 2,
  governance_evaluated: 3,
  governance_approved: 3,
  governance_denied: 3,
  execution_completed: 4,
  memory_written: 6,
  memory_write_failed: 6,
}

function stepReachedIndex(stepsCompleted: string[]): number {
  let max = 0
  for (const step of stepsCompleted) {
    const idx = STEP_KEYS[step]
    if (idx !== undefined && idx > max) max = idx
  }
  // If execution completed, proof is implicit (step 5)
  if (stepsCompleted.includes('execution_completed') && max >= 4) max = Math.max(max, 5)
  // If memory written, reality update is implicit (step 7)
  if (stepsCompleted.includes('memory_written') && max >= 6) max = Math.max(max, 7)
  // If we have any completion event, cockpit is updated (step 8)
  if (max >= 6) max = Math.max(max, 8)
  return max
}

interface CycleEvent {
  event_id: string
  event_type: string
  timestamp: number
  data: {
    result_id?: string
    work_packet_id?: string
    governance_decision_id?: string
    execution_bundle_id?: string | null
    memory_write_receipt_id?: string | null
    reality_update_id?: string | null
    final_status?: string
    steps_completed?: string[]
    total_duration_ms?: number
    active_domains?: string[]
    error?: string | null
  }
}

function CurrentReality({ cycles }: { cycles: CycleEvent[] }) {
  const latest = cycles.length > 0 ? cycles[cycles.length - 1] : null

  if (!latest) {
    return (
      <section>
        <h3 className="wv-label mb-2">Current Reality</h3>
        <p className="text-xs text-text-tertiary">No cycle data available yet</p>
      </section>
    )
  }

  const domains = latest.data.active_domains ?? []
  const blocked = cycles
    .filter((c) => c.data.final_status === 'blocked' || c.data.final_status === 'denied')
    .slice(-5)

  return (
    <section className="space-y-3">
      <h3 className="wv-label mb-2">Current Reality</h3>
      <div className="grid grid-cols-2 gap-2">
        <div className="wv-card p-2">
          <div className="text-[8px] text-text-tertiary uppercase">Active Domains</div>
          <div className="flex flex-wrap gap-1 mt-1">
            {domains.length > 0 ? (
              domains.map((d) => (
                <span key={d} className="text-[10px] font-mono px-2 py-1 rounded bg-cyan/10 text-cyan">
                  {d}
                </span>
              ))
            ) : (
              <span className="text-[10px] text-text-tertiary">None detected</span>
            )}
          </div>
        </div>
        <div className="wv-card p-2">
          <div className="text-[8px] text-text-tertiary uppercase">Blocked Items</div>
          {blocked.length > 0 ? (
            <div className="mt-1 space-y-1">
              {blocked.map((b) => (
                <div key={b.event_id} className="text-[10px] text-danger/80 truncate">
                  {b.data.error || `${b.data.final_status}: ${b.data.work_packet_id}`}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-[10px] text-ok mt-1">No blockers</div>
          )}
        </div>
      </div>
    </section>
  )
}

function RecentCycles({ cycles }: { cycles: CycleEvent[] }) {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  return (
    <section>
      <h3 className="wv-label mb-2">Recent Cycles ({cycles.length})</h3>
      {cycles.length > 0 ? (
        <div className="space-y-1">
          {[...cycles].reverse().map((c) => {
            const status = c.data.final_status ?? 'unknown'
            const steps = c.data.steps_completed ?? []
            const isExpanded = expandedId === c.event_id

            return (
              <div key={c.event_id} className="wv-card p-2">
                <div
                  className="flex items-center gap-2 cursor-pointer"
                  onClick={() => setExpandedId(isExpanded ? null : c.event_id)}
                >
                  <span className={`text-[9px] font-mono uppercase px-2 py-0.5 rounded ${STATUS_COLORS[status] ?? 'bg-surface-overlay text-text-tertiary'}`}>
                    {status}
                  </span>
                  <span className="text-[10px] text-text-tertiary">
                    {new Date(c.timestamp * 1000).toLocaleTimeString()}
                  </span>
                  <span className="text-[10px] text-text-tertiary ml-auto">
                    {c.data.total_duration_ms ?? 0}ms
                  </span>
                </div>

                <div className="flex flex-wrap gap-1 mt-1">
                  {steps.map((s) => (
                    <span
                      key={s}
                      className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-surface-overlay text-text-secondary"
                    >
                      {s}
                    </span>
                  ))}
                </div>

                {c.data.error && (
                  <div className="text-[10px] text-danger/80 mt-1 truncate">{c.data.error}</div>
                )}

                {isExpanded && (
                  <div className="mt-2 space-y-1 text-[10px] font-mono text-text-tertiary border-t border-border pt-2">
                    {c.data.result_id && <div>result: {c.data.result_id}</div>}
                    {c.data.work_packet_id && <div>work_packet: {c.data.work_packet_id}</div>}
                    {c.data.governance_decision_id && <div>governance: {c.data.governance_decision_id}</div>}
                    {c.data.execution_bundle_id && <div>execution: {c.data.execution_bundle_id}</div>}
                    {c.data.memory_write_receipt_id && <div>memory: {c.data.memory_write_receipt_id}</div>}
                    {c.data.reality_update_id && <div>reality_update: {c.data.reality_update_id}</div>}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      ) : (
        <p className="text-xs text-text-tertiary text-center py-4">No cycles recorded yet</p>
      )}
    </section>
  )
}

function ExecuteIntent() {
  const [intent, setIntent] = useState('')
  const [desiredEndState, setDesiredEndState] = useState('')
  const executeIntent = useOrganismLoopStore((s) => s.executeIntent)
  const executing = useOrganismLoopStore((s) => s.executing)
  const lastResult = useOrganismLoopStore((s) => s.lastResult)
  const error = useOrganismLoopStore((s) => s.error)

  const handleExecute = () => {
    if (intent.trim()) {
      executeIntent(intent.trim(), desiredEndState.trim() || undefined)
    }
  }

  return (
    <section className="space-y-3">
      <h3 className="wv-label mb-2">Execute Intent</h3>
      <div className="space-y-2">
        <input
          type="text"
          value={intent}
          onChange={(e) => setIntent(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleExecute() }}
          placeholder="Intent -- what should the organism do?"
          className="w-full px-3 py-2 text-xs font-mono bg-surface border border-border rounded text-text-primary placeholder-text-tertiary focus:border-cyan focus:outline-none"
        />
        <input
          type="text"
          value={desiredEndState}
          onChange={(e) => setDesiredEndState(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleExecute() }}
          placeholder="Desired end state (optional)"
          className="w-full px-3 py-2 text-xs font-mono bg-surface border border-border rounded text-text-primary placeholder-text-tertiary focus:border-cyan focus:outline-none"
        />
        <button
          onClick={handleExecute}
          disabled={executing || !intent.trim()}
          className="px-4 py-2 text-xs font-mono bg-cyan/20 text-cyan rounded hover:bg-cyan/30 disabled:opacity-50"
        >
          {executing ? 'EXECUTING...' : 'EXECUTE'}
        </button>
      </div>

      {error && (
        <div className="wv-card p-2 border border-danger/30">
          <span className="text-[10px] text-danger">{error}</span>
        </div>
      )}

      {lastResult && (
        <div className="wv-card p-3 border border-cyan/30">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-semibold text-text-primary">Result</span>
            <span className={`text-[9px] font-mono uppercase px-2 py-0.5 rounded ${STATUS_COLORS[lastResult.final_status] ?? 'bg-surface-overlay text-text-tertiary'}`}>
              {lastResult.final_status}
            </span>
            <span className="text-[10px] text-text-tertiary ml-auto">{lastResult.total_duration_ms}ms</span>
          </div>
          <div className="space-y-1 text-[10px] font-mono text-text-tertiary">
            <div>result: {lastResult.result_id}</div>
            {lastResult.work_packet_id && <div>work_packet: {lastResult.work_packet_id}</div>}
            {lastResult.governance_decision_id && <div>governance: {lastResult.governance_decision_id}</div>}
            {lastResult.execution_bundle_id && <div>execution: {lastResult.execution_bundle_id}</div>}
            {lastResult.memory_write_receipt_id && <div>memory: {lastResult.memory_write_receipt_id}</div>}
          </div>
          <div className="flex flex-wrap gap-1 mt-2">
            {lastResult.steps_completed.map((s: string) => (
              <span key={s} className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-ok/10 text-ok">
                {s}
              </span>
            ))}
          </div>
          {lastResult.error && (
            <div className="text-[10px] text-danger mt-2">{lastResult.error}</div>
          )}
        </div>
      )}
    </section>
  )
}

function LoopWiring({ cycles }: { cycles: CycleEvent[] }) {
  const latest = cycles.length > 0 ? cycles[cycles.length - 1] : null
  const stepsCompleted = latest?.data.steps_completed ?? []
  const reachedIdx = stepReachedIndex(stepsCompleted)

  return (
    <section>
      <h3 className="wv-label mb-2">Loop Wiring (9-step)</h3>
      <div className="flex items-center gap-0.5 flex-wrap">
        {LOOP_STEPS.map((step, i) => {
          const reached = i <= reachedIdx
          return (
            <div key={step} className="flex items-center gap-0.5">
              <span
                className={`text-[9px] font-mono px-2 py-1 rounded ${
                  reached ? 'bg-ok/20 text-ok' : 'bg-surface-overlay text-text-tertiary'
                }`}
              >
                {step}
              </span>
              {i < LOOP_STEPS.length - 1 && (
                <span className={`text-[10px] ${reached ? 'text-ok' : 'text-text-tertiary'}`}>
                  &rarr;
                </span>
              )}
            </div>
          )
        })}
      </div>
      {!latest && (
        <p className="text-[10px] text-text-tertiary mt-2">No cycles -- wiring shows gray until first cycle completes.</p>
      )}
    </section>
  )
}

export function OrganismLoopPanel() {
  const fetchCycles = useOrganismLoopStore((s) => s.fetchCycles)
  const cycles = useOrganismLoopStore((s) => s.cycles)
  const loading = useOrganismLoopStore((s) => s.loading)

  usePolling(fetchCycles, 10000)

  if (loading && cycles.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-text-tertiary text-sm">Loading organism loop data...</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-canvas">
        <span className="text-xs font-mono text-cyan uppercase tracking-wider">Organism Loop</span>
        <span className="text-[10px] text-text-tertiary ml-auto">{cycles.length} cycles</span>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <CurrentReality cycles={cycles} />
        <LoopWiring cycles={cycles} />
        <ExecuteIntent />
        <RecentCycles cycles={cycles} />
      </div>
    </div>
  )
}
