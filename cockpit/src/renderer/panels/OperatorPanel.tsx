import { useState, useRef, useEffect } from 'react'
import { useCollapseStore } from '../stores/collapseStore'
import { useConfigStore } from '../stores/configStore'
import { useOperatorExperienceStore } from '../stores/operatorExperienceStore'
import { useOperatorLoopStore } from '../stores/operatorLoopStore'
import type { IntentContract, PacketSummary, PacketDetail, ValidationResult, AuditEntry, ExecuteResult } from '../stores/operatorLoopStore'
import { usePolling } from '../hooks/usePolling'
import { ConnectionBanner } from '../components/ConnectionBanner'
import type {
  DexResponse,
  SessionTurn,
  PacketPreview,
  TopologyPreview,
  HumanAction,
  ApprovalGate,
  PropagationPreview,
  PropagationNode,
  WorkcellPreview,
} from '../operator/voiceTypes'

const RISK_COLOR: Record<string, string> = {
  low: 'text-ok',
  medium: 'text-warn',
  high: 'text-danger',
  critical: 'text-danger',
}

type Tab = 'command' | 'loop'

export function OperatorPanel() {
  const [tab, setTab] = useState<Tab>('loop')

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <ConnectionBanner />
      <div className="flex-shrink-0 border-b border-border px-4 pt-2">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold text-text-primary">Operator</h2>
          <div className="flex gap-1 ml-auto">
            <TabBtn active={tab === 'loop'} onClick={() => setTab('loop')}>Work Loop</TabBtn>
            <TabBtn active={tab === 'command'} onClick={() => setTab('command')}>Command</TabBtn>
          </div>
        </div>
      </div>
      {tab === 'command' ? <CommandTab /> : <WorkLoopTab />}
    </div>
  )
}

function TabBtn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 text-xs font-mono rounded-t transition-colors ${
        active
          ? 'bg-surface-secondary text-cyan border-t border-x border-border'
          : 'text-text-tertiary hover:text-text-secondary'
      }`}
    >
      {children}
    </button>
  )
}

/* ─── Work Loop Tab ───────────────────────────────────────── */

function WorkLoopTab() {
  const {
    loopStatus, pendingApprovals, activePackets, selectedPacket,
    lastExecuteResult, loopHealth, loading, executing, lastError,
    fetchLoopStatus, fetchPendingApprovals, fetchActivePackets,
    fetchLoopHealth, selectPacket, clearSelection,
    submitIntent, approvePacket, rejectPacket, executePacket,
    completePacket,
  } = useOperatorLoopStore()

  usePolling(fetchLoopStatus, 10000)
  usePolling(fetchPendingApprovals, 10000)
  usePolling(fetchActivePackets, 10000)
  usePolling(fetchLoopHealth, 30000)

  return (
    <div className="flex-1 overflow-y-auto px-4 pt-3 pb-4 space-y-4">
      {/* Health bar */}
      <HealthBar health={loopHealth} />

      {/* Intent submission form */}
      <IntentForm onSubmit={submitIntent} loading={loading} />

      {/* Pending approvals */}
      {pendingApprovals.length > 0 && (
        <ApprovalQueue
          packets={pendingApprovals}
          onApprove={approvePacket}
          onReject={rejectPacket}
          onSelect={selectPacket}
        />
      )}

      {/* Active packets */}
      {activePackets.length > 0 && (
        <ActivePackets
          packets={activePackets}
          onSelect={selectPacket}
          onExecute={executePacket}
          executing={executing}
        />
      )}

      {/* Execution results */}
      {lastExecuteResult && (
        <ExecutionResults result={lastExecuteResult} />
      )}

      {/* Selected packet detail */}
      {selectedPacket && (
        <PacketDetailView
          packet={selectedPacket}
          onClose={clearSelection}
          onApprove={approvePacket}
          onReject={rejectPacket}
          onExecute={executePacket}
          onComplete={completePacket}
          executing={executing}
        />
      )}

      {/* Loop summary */}
      {loopStatus && (
        <LoopSummary status={loopStatus} />
      )}

      {lastError && (
        <div className="wv-card p-3 border border-danger/30">
          <span className="text-xs text-danger font-mono">{lastError}</span>
        </div>
      )}
    </div>
  )
}

/* ─── Health Bar ──────────────────────────────────────────── */

function HealthBar({ health }: { health: { healthy: boolean; sandbox_summary: { total: number; active: number }; reality_model: string } | null }) {
  if (!health) return null
  return (
    <div className="flex items-center gap-3 text-[10px] font-mono text-text-tertiary">
      <span className={`w-2 h-2 rounded-full ${health.healthy ? 'bg-ok' : 'bg-danger'}`} />
      <span>{health.healthy ? 'LOOP HEALTHY' : 'LOOP DEGRADED'}</span>
      <span className="ml-auto">sandboxes: {health.sandbox_summary.active}/{health.sandbox_summary.total}</span>
      <span>reality: {health.reality_model.split('(')[0].trim()}</span>
    </div>
  )
}

/* ─── Intent Form ─────────────────────────────────────────── */

function IntentForm({ onSubmit, loading }: { onSubmit: (c: IntentContract) => Promise<unknown>; loading: boolean }) {
  const [intent, setIntent] = useState('')
  const [endState, setEndState] = useState('')
  const [criteria, setCriteria] = useState('')
  const [constraints, setConstraints] = useState('')
  const [nonGoals, setNonGoals] = useState('')
  const [riskTolerance, setRiskTolerance] = useState<'low' | 'medium' | 'high' | ''>('')
  const [approvalPolicy, setApprovalPolicy] = useState<'auto' | 'always' | ''>('')
  const expanded = useCollapseStore((s) => s.isOpen('operator:intent-form'))
  const collapseToggle = useCollapseStore((s) => s.toggle)
  const collapseSet = useCollapseStore((s) => s.setOpen)

  const handleSubmit = async () => {
    if (!intent.trim()) return
    const contract: IntentContract = {
      user_intent: intent.trim(),
    }
    if (endState.trim()) contract.desired_end_state = endState.trim()
    if (criteria.trim()) contract.acceptance_criteria = criteria.split('\n').map(s => s.trim()).filter(Boolean)
    if (constraints.trim()) contract.constraints = constraints.split('\n').map(s => s.trim()).filter(Boolean)
    if (nonGoals.trim()) contract.non_goals = nonGoals.split('\n').map(s => s.trim()).filter(Boolean)
    if (riskTolerance) contract.risk_tolerance = riskTolerance
    if (approvalPolicy) contract.approval_policy = approvalPolicy

    await onSubmit(contract)
    setIntent('')
    setEndState('')
    setCriteria('')
    setConstraints('')
    setNonGoals('')
    collapseSet('operator:intent-form', false)
  }

  return (
    <section className="wv-card p-3 border border-cyan/20">
      <div className="flex items-center justify-between mb-2">
        <h3 className="wv-label">Submit Intent</h3>
        <button
          onClick={() => collapseToggle('operator:intent-form')}
          className="text-[10px] text-cyan font-mono hover:underline"
        >
          {expanded ? 'simple' : 'full contract'}
        </button>
      </div>

      <textarea
        value={intent}
        onChange={e => setIntent(e.target.value)}
        placeholder="Describe what you want UMH to do..."
        rows={2}
        className="w-full bg-surface-secondary text-text-primary text-sm rounded px-3 py-2 resize-none focus:outline-none focus:ring-1 focus:ring-cyan/50 placeholder:text-text-tertiary font-mono mb-2"
      />

      {expanded && (
        <div className="space-y-2 mb-2">
          <LabeledInput label="Desired End State" value={endState} onChange={setEndState} placeholder="What should be true when this is done?" />
          <LabeledTextarea label="Acceptance Criteria" value={criteria} onChange={setCriteria} placeholder="One per line..." />
          <LabeledTextarea label="Constraints" value={constraints} onChange={setConstraints} placeholder="One per line..." />
          <LabeledTextarea label="Non-Goals" value={nonGoals} onChange={setNonGoals} placeholder="What NOT to do (one per line)..." />
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="text-[10px] text-text-tertiary mb-1 block">Risk Tolerance</label>
              <select
                value={riskTolerance}
                onChange={e => setRiskTolerance(e.target.value as 'low' | 'medium' | 'high' | '')}
                className="w-full bg-surface-secondary text-text-primary text-xs rounded px-2 py-1.5 font-mono"
              >
                <option value="">auto-detect</option>
                <option value="low">low</option>
                <option value="medium">medium</option>
                <option value="high">high</option>
              </select>
            </div>
            <div className="flex-1">
              <label className="text-[10px] text-text-tertiary mb-1 block">Approval Policy</label>
              <select
                value={approvalPolicy}
                onChange={e => setApprovalPolicy(e.target.value as 'auto' | 'always' | '')}
                className="w-full bg-surface-secondary text-text-primary text-xs rounded px-2 py-1.5 font-mono"
              >
                <option value="">default (risk-based)</option>
                <option value="auto">auto-approve</option>
                <option value="always">always require approval</option>
              </select>
            </div>
          </div>
        </div>
      )}

      <button
        onClick={handleSubmit}
        disabled={!intent.trim() || loading}
        className={`w-full py-2 rounded text-sm font-mono transition-colors ${
          !intent.trim() || loading
            ? 'bg-surface-secondary text-text-tertiary cursor-not-allowed'
            : 'bg-cyan/20 text-cyan hover:bg-cyan/30'
        }`}
      >
        {loading ? 'Submitting...' : 'Submit Intent'}
      </button>
    </section>
  )
}

/* ─── Approval Queue ──────────────────────────────────────── */

function ApprovalQueue({ packets, onApprove, onReject, onSelect }: {
  packets: PacketSummary[]
  onApprove: (id: string) => Promise<boolean>
  onReject: (id: string, reason?: string) => Promise<boolean>
  onSelect: (id: string) => Promise<void>
}) {
  return (
    <section className="wv-card p-3 border border-warn/20">
      <h3 className="wv-label mb-2">Pending Approvals ({packets.length})</h3>
      <div className="space-y-2">
        {packets.map(p => (
          <div key={p.packet_id} className="flex items-start gap-2 px-2 py-2 bg-surface-secondary rounded">
            <span className="w-1.5 h-1.5 rounded-full bg-warn mt-1.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-xs text-text-primary truncate">{p.title || p.user_intent}</p>
              <div className="flex items-center gap-2 mt-1">
                <span className={`text-[9px] font-mono ${RISK_COLOR[p.risk_class] ?? 'text-text-tertiary'}`}>{p.risk_class.toUpperCase()}</span>
                <span className="text-[9px] text-text-tertiary font-mono">{p.domain}</span>
              </div>
            </div>
            <div className="flex gap-1 flex-shrink-0">
              <button onClick={() => onSelect(p.packet_id)} className="px-2 py-1 text-[10px] text-cyan font-mono hover:underline">view</button>
              <button onClick={() => onApprove(p.packet_id)} className="px-2 py-1 text-[10px] text-ok bg-ok/10 rounded font-mono hover:bg-ok/20">approve</button>
              <button onClick={() => onReject(p.packet_id)} className="px-2 py-1 text-[10px] text-danger bg-danger/10 rounded font-mono hover:bg-danger/20">reject</button>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

/* ─── Active Packets ──────────────────────────────────────── */

function ActivePackets({ packets, onSelect, onExecute, executing }: {
  packets: PacketSummary[]
  onSelect: (id: string) => Promise<void>
  onExecute: (id: string) => Promise<unknown>
  executing: boolean
}) {
  return (
    <section className="wv-card p-3">
      <h3 className="wv-label mb-2">Active Packets ({packets.length})</h3>
      <div className="space-y-2">
        {packets.map(p => (
          <div key={p.packet_id} className="flex items-center gap-2 px-2 py-2 bg-surface-secondary rounded">
            <StatusDot status={p.status} />
            <div className="flex-1 min-w-0">
              <p className="text-xs text-text-primary truncate">{p.title || p.user_intent}</p>
              <span className="text-[9px] text-text-tertiary font-mono">{p.status}</span>
            </div>
            <button onClick={() => onSelect(p.packet_id)} className="px-2 py-1 text-[10px] text-cyan font-mono hover:underline">details</button>
            {p.status === 'approved' && (
              <button
                onClick={() => onExecute(p.packet_id)}
                disabled={executing}
                className="px-2 py-1 text-[10px] text-ok bg-ok/10 rounded font-mono hover:bg-ok/20 disabled:opacity-50"
              >
                {executing ? 'running...' : 'execute'}
              </button>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}

/* ─── Execution Results ───────────────────────────────────── */

function ExecutionResults({ result }: { result: ExecuteResult }) {
  const expanded = useCollapseStore((s) => s.isOpen('operator:exec-results', true))
  const toggle = useCollapseStore((s) => s.toggle)

  return (
    <section className={`wv-card p-3 border ${result.all_passed ? 'border-ok/30' : 'border-danger/30'}`}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="wv-label">Execution Result</h3>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-mono uppercase ${result.all_passed ? 'text-ok' : 'text-danger'}`}>
            {result.all_passed ? 'ALL PASSED' : 'FAILED'}
          </span>
          <button onClick={() => toggle('operator:exec-results')} className="text-[10px] text-cyan font-mono hover:underline">
            {expanded ? 'collapse' : 'expand'}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="space-y-3">
          <div className="flex gap-3 text-[10px] font-mono text-text-tertiary">
            <span>sandbox: <span className="text-text-primary">{result.sandbox_id?.slice(0, 12)}</span></span>
            <span>branch: <span className="text-text-primary">{result.branch_name}</span></span>
            <span>files: <span className="text-text-primary">{result.changed_files?.length ?? 0}</span></span>
          </div>

          {result.validation_results?.map((v, i) => (
            <ValidationStep key={i} result={v} />
          ))}

          {result.changed_files?.length > 0 && (
            <div>
              <span className="text-[10px] text-text-tertiary font-mono">Changed Files</span>
              <div className="mt-1 max-h-24 overflow-y-auto">
                {result.changed_files.map((f, i) => (
                  <div key={i} className="text-[11px] text-text-secondary font-mono px-2">{f}</div>
                ))}
              </div>
            </div>
          )}

          {result.diff_summary && (
            <div>
              <span className="text-[10px] text-text-tertiary font-mono">Diff Summary</span>
              <pre className="mt-1 text-[10px] text-text-secondary font-mono bg-surface-secondary rounded p-2 overflow-x-auto max-h-32">
                {result.diff_summary}
              </pre>
            </div>
          )}
        </div>
      )}
    </section>
  )
}

/* ─── Validation Step ─────────────────────────────────────── */

function ValidationStep({ result }: { result: ValidationResult }) {
  const key = `operator:validation:${result.label}`
  const showOutput = useCollapseStore((s) => s.isOpen(key, !result.passed))
  const toggle = useCollapseStore((s) => s.toggle)

  return (
    <div className={`px-2 py-1.5 rounded ${result.passed ? 'bg-ok/5' : 'bg-danger/5'}`}>
      <div className="flex items-center gap-2">
        <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${result.passed ? 'bg-ok' : 'bg-danger'}`} />
        <span className="text-xs text-text-primary flex-1 truncate">{result.label}</span>
        <span className="text-[9px] text-text-tertiary font-mono">{result.duration_seconds}s</span>
        <span className={`text-[9px] font-mono ${result.passed ? 'text-ok' : 'text-danger'}`}>
          exit {result.exit_code}
        </span>
        <button onClick={() => toggle(key)} className="text-[10px] text-cyan font-mono hover:underline">
          {showOutput ? 'hide' : 'output'}
        </button>
      </div>
      {showOutput && (
        <div className="mt-1.5 space-y-1">
          <pre className="text-[9px] font-mono text-text-secondary bg-surface-secondary rounded p-1.5 overflow-x-auto max-h-32 whitespace-pre-wrap">
            $ {result.command}
          </pre>
          {result.stdout && (
            <pre className="text-[9px] font-mono text-text-secondary bg-surface-secondary rounded p-1.5 overflow-x-auto max-h-24 whitespace-pre-wrap">
              {result.stdout}
            </pre>
          )}
          {result.stderr && (
            <pre className="text-[9px] font-mono text-danger/70 bg-surface-secondary rounded p-1.5 overflow-x-auto max-h-24 whitespace-pre-wrap">
              {result.stderr}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

/* ─── Packet Detail View ──────────────────────────────────── */

function PacketDetailView({ packet, onClose, onApprove, onReject, onExecute, onComplete, executing }: {
  packet: PacketDetail
  onClose: () => void
  onApprove: (id: string) => Promise<boolean>
  onReject: (id: string, reason?: string) => Promise<boolean>
  onExecute: (id: string) => Promise<unknown>
  onComplete: (id: string, outcome: string, success: boolean) => Promise<boolean>
  executing: boolean
}) {
  const [completeOutcome, setCompleteOutcome] = useState('')

  const canApprove = ['classified', 'planned', 'ready_for_review', 'approval_pending'].includes(packet.status)
  const canExecute = packet.status === 'approved'
  const canComplete = packet.status === 'validating'

  return (
    <section className="wv-card p-3 border border-cyan/20">
      <div className="flex items-center justify-between mb-3">
        <h3 className="wv-label">Packet Detail</h3>
        <button onClick={onClose} className="text-[10px] text-text-tertiary font-mono hover:text-text-secondary">close</button>
      </div>

      <div className="space-y-2 text-xs">
        <Row label="ID" value={packet.packet_id} mono />
        <Row label="Title" value={packet.title} />
        <Row label="Intent" value={packet.user_intent} multiline />
        {packet.desired_end_state && <Row label="End State" value={packet.desired_end_state} multiline />}
        <Row label="Status" value={packet.status} />
        <Row label="Risk" value={packet.risk_class} color={RISK_COLOR[packet.risk_class]} />
        <Row label="Domain" value={packet.domain} />

        {packet.success_criteria?.length > 0 && (
          <div>
            <span className="text-[10px] text-text-tertiary">Acceptance Criteria</span>
            <ul className="mt-1 list-disc list-inside text-[11px] text-text-secondary">
              {packet.success_criteria.map((c, i) => <li key={i}>{c}</li>)}
            </ul>
          </div>
        )}

        {packet.failure_criteria?.length > 0 && (
          <div>
            <span className="text-[10px] text-text-tertiary">Non-Goals</span>
            <ul className="mt-1 list-disc list-inside text-[11px] text-text-secondary">
              {packet.failure_criteria.map((c, i) => <li key={i}>{c}</li>)}
            </ul>
          </div>
        )}

        {packet.constraints?.length > 0 && (
          <div>
            <span className="text-[10px] text-text-tertiary">Constraints</span>
            <div className="mt-1 flex flex-wrap gap-1">
              {packet.constraints.map((c, i) => (
                <span key={i} className="px-2 py-0.5 bg-surface-secondary text-text-secondary text-[10px] rounded font-mono">{c}</span>
              ))}
            </div>
          </div>
        )}

        {packet.validation_plan && <Row label="Validation" value={packet.validation_plan} multiline />}
        {packet.rollback_plan && <Row label="Rollback" value={packet.rollback_plan} multiline />}

        {packet.linked_sandbox_id && <Row label="Sandbox" value={packet.linked_sandbox_id} mono />}
        {packet.outcome_summary && <Row label="Outcome" value={packet.outcome_summary} multiline />}

        {packet.verification_results?.length > 0 && (
          <div className="pt-2">
            <span className="text-[10px] text-text-tertiary">Verification Results</span>
            <div className="mt-1 space-y-1">
              {packet.verification_results.map((v, i) => (
                <ValidationStep key={i} result={v} />
              ))}
            </div>
          </div>
        )}

        {packet.audit_trail?.length > 0 && (
          <div className="pt-2">
            <span className="text-[10px] text-text-tertiary">Audit Trail ({packet.audit_trail.length})</span>
            <div className="mt-1 max-h-32 overflow-y-auto space-y-1">
              {packet.audit_trail.map((a) => (
                <div key={a.id} className="flex items-center gap-2 text-[10px] font-mono text-text-tertiary">
                  <span>{new Date(a.timestamp * 1000).toLocaleTimeString()}</span>
                  <span className="text-text-secondary">{a.event_type}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="pt-3 flex gap-2">
          {canApprove && (
            <>
              <button onClick={() => onApprove(packet.packet_id)} className="px-3 py-1.5 text-xs text-ok bg-ok/10 rounded font-mono hover:bg-ok/20">Approve</button>
              <button onClick={() => onReject(packet.packet_id)} className="px-3 py-1.5 text-xs text-danger bg-danger/10 rounded font-mono hover:bg-danger/20">Reject</button>
            </>
          )}
          {canExecute && (
            <button
              onClick={() => onExecute(packet.packet_id)}
              disabled={executing}
              className="px-3 py-1.5 text-xs text-cyan bg-cyan/10 rounded font-mono hover:bg-cyan/20 disabled:opacity-50"
            >
              {executing ? 'Executing...' : 'Execute'}
            </button>
          )}
          {canComplete && (
            <div className="flex gap-2 w-full">
              <input
                value={completeOutcome}
                onChange={e => setCompleteOutcome(e.target.value)}
                placeholder="Outcome summary..."
                className="flex-1 bg-surface-secondary text-text-primary text-xs rounded px-2 py-1.5 font-mono"
              />
              <button
                onClick={() => { onComplete(packet.packet_id, completeOutcome, true); setCompleteOutcome('') }}
                className="px-3 py-1.5 text-xs text-ok bg-ok/10 rounded font-mono hover:bg-ok/20"
              >
                Complete
              </button>
              <button
                onClick={() => { onComplete(packet.packet_id, completeOutcome, false); setCompleteOutcome('') }}
                className="px-3 py-1.5 text-xs text-danger bg-danger/10 rounded font-mono hover:bg-danger/20"
              >
                Mark Failed
              </button>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

/* ─── Loop Summary ────────────────────────────────────────── */

function LoopSummary({ status }: { status: { queue_summary: Record<string, unknown>; pending_approval_count: number; blocked_count: number; human_required_count: number; next_best: PacketSummary | null } }) {
  const qs = status.queue_summary
  return (
    <section className="wv-card p-3">
      <h3 className="wv-label mb-2">Loop Summary</h3>
      <div className="grid grid-cols-2 gap-2 text-[11px]">
        <Stat label="Total Packets" value={String(qs.total_packets ?? 0)} />
        <Stat label="Pending Approval" value={String(status.pending_approval_count)} color={status.pending_approval_count > 0 ? 'text-warn' : undefined} />
        <Stat label="Blocked" value={String(status.blocked_count)} color={status.blocked_count > 0 ? 'text-danger' : undefined} />
        <Stat label="Human Required" value={String(status.human_required_count)} color={status.human_required_count > 0 ? 'text-warn' : undefined} />
      </div>
      {status.next_best && (
        <div className="mt-2 pt-2 border-t border-border">
          <span className="text-[10px] text-text-tertiary">Next Best:</span>
          <p className="text-xs text-text-primary mt-1 truncate">{status.next_best.title || status.next_best.user_intent}</p>
        </div>
      )}
    </section>
  )
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="text-text-tertiary text-[10px]">{label}:</span>
      <span className={`font-mono ${color ?? 'text-text-primary'}`}>{value}</span>
    </div>
  )
}

function StatusDot({ status }: { status: string }) {
  const color = status === 'executing' ? 'bg-cyan animate-pulse'
    : status === 'validating' ? 'bg-warn'
    : status === 'completed' ? 'bg-ok'
    : status === 'failed' ? 'bg-danger'
    : 'bg-text-tertiary'
  return <span className={`w-2 h-2 rounded-full flex-shrink-0 ${color}`} />
}

/* ─── Command Tab (original assistant surface) ──────────────────── */

function CommandTab() {
  const {
    currentSession, activeInput, voiceState, voiceSupported,
    interimTranscript, lastResponse, responseHistory,
    pendingApprovals, roadmapStatus, loading, error,
    loadOverview, loadStatus, loadApprovals,
    startVoiceInput, stopVoiceInput, setActiveInput, submitCommand,
  } = useOperatorExperienceStore()

  const inputRef = useRef<HTMLTextAreaElement>(null)
  const historyEndRef = useRef<HTMLDivElement>(null)

  usePolling(loadOverview, 30000)
  usePolling(loadStatus, 30000)
  usePolling(loadApprovals, 30000)

  useEffect(() => {
    historyEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [responseHistory.length])

  const handleSubmit = async () => {
    if (!activeInput.trim() || loading) return
    await submitCommand()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const isListening = voiceState === 'listening' || voiceState === 'processing'

  return (
    <>
      <div className="flex-1 overflow-y-auto px-4 pt-3 pb-20 space-y-4">
        <CommandHeader
          sessionId={currentSession?.session_id ?? null}
          turnCount={currentSession?.turn_count ?? 0}
        />

        {responseHistory.length > 0 && <SessionHistory turns={responseHistory} />}
        {lastResponse && <DexResponseSection response={lastResponse} />}
        {lastResponse?.packet_preview && <PacketPreviewSection packet={lastResponse.packet_preview} />}
        {lastResponse?.topology_preview && <TopologySection topology={lastResponse.topology_preview} />}
        {(lastResponse?.human_actions?.length || lastResponse?.approval_gates?.length) ? (
          <HumanActionsSection actions={lastResponse.human_actions} gates={lastResponse.approval_gates} />
        ) : null}
        {lastResponse?.propagation_preview && <PropagationSection preview={lastResponse.propagation_preview} />}
        <RoadmapSection roadmap={roadmapStatus} approvals={pendingApprovals} />
        {error && (
          <div className="wv-card p-3 border border-danger/30">
            <span className="text-xs text-danger font-mono">{error}</span>
          </div>
        )}
        <div ref={historyEndRef} />
      </div>

      <div className="flex-shrink-0 border-t border-border px-4 py-3 bg-surface-primary">
        {interimTranscript && (
          <div className="mb-2 px-2 py-1 bg-surface-secondary rounded text-xs text-text-tertiary italic font-mono">
            {interimTranscript}...
          </div>
        )}
        <div className="flex items-end gap-2">
          <button
            onClick={isListening ? stopVoiceInput : startVoiceInput}
            disabled={!voiceSupported}
            title={!voiceSupported ? 'Voice unavailable' : isListening ? 'Stop' : 'Push to talk'}
            className={`flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center transition-colors ${
              !voiceSupported ? 'bg-surface-secondary text-text-tertiary cursor-not-allowed'
              : isListening ? 'bg-danger/20 text-danger animate-pulse'
              : 'bg-surface-secondary text-text-secondary hover:bg-surface-tertiary hover:text-cyan'
            }`}
          >
            <MicIcon listening={isListening} />
          </button>
          <textarea
            ref={inputRef}
            value={activeInput}
            onChange={(e) => setActiveInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={voiceSupported ? 'Speak or type...' : 'Type a command...'}
            rows={1}
            className="flex-1 bg-surface-secondary text-text-primary text-sm rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-1 focus:ring-cyan/50 placeholder:text-text-tertiary font-mono"
          />
          <button
            onClick={handleSubmit}
            disabled={!activeInput.trim() || loading}
            className={`flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center transition-colors ${
              !activeInput.trim() || loading ? 'bg-surface-secondary text-text-tertiary cursor-not-allowed' : 'bg-cyan/20 text-cyan hover:bg-cyan/30'
            }`}
          >
            {loading ? <Spinner /> : <SendIcon />}
          </button>
        </div>
        <div className="mt-2 flex items-center gap-2 text-[10px] text-text-tertiary">
          <span className={`w-1.5 h-1.5 rounded-full ${
            voiceState === 'listening' ? 'bg-danger animate-pulse'
            : voiceState === 'processing' ? 'bg-warn'
            : voiceState === 'responded' ? 'bg-ok'
            : voiceState === 'error' ? 'bg-danger'
            : 'bg-text-tertiary'
          }`} />
          <span className="uppercase font-mono">{voiceState}</span>
        </div>
      </div>
    </>
  )
}

/* ─── Shared Components (unchanged from original) ─────────── */

function LabeledInput({ label, value, onChange, placeholder }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string
}) {
  return (
    <div>
      <label className="text-[10px] text-text-tertiary mb-1 block">{label}</label>
      <input
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-surface-secondary text-text-primary text-xs rounded px-2 py-1.5 font-mono focus:outline-none focus:ring-1 focus:ring-cyan/50"
      />
    </div>
  )
}

function LabeledTextarea({ label, value, onChange, placeholder }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string
}) {
  return (
    <div>
      <label className="text-[10px] text-text-tertiary mb-1 block">{label}</label>
      <textarea
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        rows={2}
        className="w-full bg-surface-secondary text-text-primary text-xs rounded px-2 py-1.5 font-mono resize-none focus:outline-none focus:ring-1 focus:ring-cyan/50"
      />
    </div>
  )
}

function CommandHeader({ sessionId, turnCount }: { sessionId: string | null; turnCount: number }) {
  const aiName = useConfigStore((s) => s.aiName)
  return (
    <div className="flex items-center gap-3">
      <div>
        <span className="text-[10px] text-text-tertiary font-mono">{aiName} command surface</span>
      </div>
      <div className="ml-auto flex items-center gap-3 text-[10px] font-mono">
        {sessionId && <span className="text-text-tertiary">{sessionId} · {turnCount} turns</span>}
      </div>
    </div>
  )
}

function SessionHistory({ turns }: { turns: SessionTurn[] }) {
  const expanded = useCollapseStore((s) => s.isOpen('operator:session-history'))
  const toggle = useCollapseStore((s) => s.toggle)
  const visible = expanded ? turns : turns.slice(-3)
  return (
    <section>
      <div className="flex items-center gap-2 mb-2">
        <h3 className="wv-label">History</h3>
        {turns.length > 3 && (
          <button onClick={() => toggle('operator:session-history')} className="text-[10px] text-cyan hover:underline font-mono">
            {expanded ? 'collapse' : `show all ${turns.length}`}
          </button>
        )}
      </div>
      <div className="space-y-2">
        {visible.map((turn) => (
          <div key={turn.turn_id} className="wv-card p-2">
            <div className="flex items-start gap-2">
              <span className="text-[9px] text-text-tertiary font-mono mt-1">{turn.input_mode === 'voice' ? 'MIC' : 'TXT'}</span>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-text-primary truncate">{turn.input}</p>
                {turn.response && <p className="text-[11px] text-text-secondary mt-1 truncate">→ {turn.response.summary || turn.response.intent}</p>}
              </div>
              <span className="text-[9px] text-text-tertiary font-mono flex-shrink-0">{new Date(turn.timestamp).toLocaleTimeString()}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function DexResponseSection({ response }: { response: DexResponse }) {
  const aiName = useConfigStore((s) => s.aiName)
  return (
    <section className="wv-card p-3 border border-cyan/20">
      <h3 className="wv-label mb-2">{aiName} Response</h3>
      <div className="space-y-2 text-xs">
        <Row label="Intent" value={response.intent} />
        <Row label="Summary" value={response.summary} multiline />
        {response.current_state && <Row label="Current State" value={response.current_state} />}
        {response.recommended_next_action && <Row label="Next Action" value={response.recommended_next_action} />}
        <div className="flex gap-4 pt-1">
          <span className="text-text-tertiary">confidence: <span className="text-text-primary font-mono">{(response.confidence * 100).toFixed(0)}%</span></span>
          <span className="text-text-tertiary">safety: <span className="text-ok font-mono">{response.safety_state}</span></span>
          <span className="text-text-tertiary">executed: <span className={`font-mono ${response.execution_occurred ? 'text-danger' : 'text-ok'}`}>{response.execution_occurred ? 'YES' : 'NO'}</span></span>
        </div>
      </div>
    </section>
  )
}

function PacketPreviewSection({ packet }: { packet: PacketPreview }) {
  return (
    <section className="wv-card p-3">
      <h3 className="wv-label mb-2">Work Packet Preview</h3>
      <div className="space-y-1.5 text-xs">
        <Row label="Title" value={packet.title} />
        <Row label="End State" value={packet.desired_end_state} multiline />
        <Row label="Status" value={packet.status} />
        <Row label="Risk" value={packet.risk_class} color={RISK_COLOR[packet.risk_class] ?? 'text-text-primary'} />
      </div>
    </section>
  )
}

function TopologySection({ topology }: { topology: TopologyPreview }) {
  return (
    <section className="wv-card p-3">
      <h3 className="wv-label mb-2">Topology</h3>
      <div className="space-y-1.5 text-xs">
        <Row label="Type" value={topology.topology_type} />
        {topology.workcells.length > 0 && (
          <div className="mt-1 space-y-1">
            {topology.workcells.map((wc: WorkcellPreview, i: number) => (
              <div key={i} className="flex items-center gap-2 px-2 py-1 bg-surface-secondary rounded text-[10px]">
                <span className="text-cyan font-mono">{wc.role}</span>
                <span className={`ml-auto font-mono ${wc.status === 'active' ? 'text-ok' : 'text-text-tertiary'}`}>{wc.status}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

function HumanActionsSection({ actions, gates }: { actions: HumanAction[]; gates: ApprovalGate[] }) {
  return (
    <section className="wv-card p-3 border border-warn/20">
      <h3 className="wv-label mb-2">Actions & Approvals</h3>
      {actions.length > 0 && (
        <div className="space-y-1 mb-2">
          {actions.map((a: HumanAction, i: number) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              <span className={`mt-1 w-1.5 h-1.5 rounded-full flex-shrink-0 ${a.blocking ? 'bg-danger' : 'bg-warn'}`} />
              <span className="text-text-primary">{a.action}</span>
            </div>
          ))}
        </div>
      )}
      {gates.length > 0 && (
        <div className="space-y-1">
          {gates.map((g: ApprovalGate) => (
            <div key={g.gate_id} className="flex items-center gap-2 text-xs">
              <span className={`w-1.5 h-1.5 rounded-full ${g.status === 'approved' ? 'bg-ok' : g.status === 'rejected' ? 'bg-danger' : 'bg-warn'}`} />
              <span className="text-text-primary flex-1">{g.description}</span>
              <span className={`text-[9px] font-mono uppercase ${g.status === 'approved' ? 'text-ok' : 'text-warn'}`}>{g.status}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function PropagationSection({ preview }: { preview: PropagationPreview }) {
  return (
    <section className="wv-card p-3">
      <h3 className="wv-label mb-2">Propagation</h3>
      <div className="flex gap-4 text-[10px] font-mono text-text-tertiary">
        <span>waves: <span className="text-text-primary">{preview.waves}</span></span>
        <span>affected: <span className="text-text-primary">{preview.affected_nodes.length}</span></span>
      </div>
    </section>
  )
}

function RoadmapSection({ roadmap, approvals }: { roadmap: Record<string, unknown> | null; approvals: Array<{ id: string; description: string; status: string }> }) {
  return (
    <section className="wv-card p-3">
      <h3 className="wv-label mb-2">Roadmap</h3>
      <div className="space-y-1.5 text-xs">
        {roadmap ? (
          <>
            {roadmap.current_phase != null && <Row label="Phase" value={String(roadmap.current_phase)} />}
            {roadmap.state != null && <Row label="State" value={String(roadmap.state)} />}
          </>
        ) : (
          <span className="text-text-tertiary">—</span>
        )}
      </div>
    </section>
  )
}

function Row({ label, value, color, mono, multiline }: { label: string; value: string; color?: string; mono?: boolean; multiline?: boolean }) {
  return (
    <div className={multiline ? '' : 'flex items-baseline gap-2'}>
      <span className="text-text-tertiary text-[10px] flex-shrink-0">{label}:</span>
      <span className={`${color ?? 'text-text-primary'} ${mono ? 'font-mono' : ''} ${multiline ? 'block mt-1' : ''}`}>{value}</span>
    </div>
  )
}

function MicIcon({ listening }: { listening: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="22" />
      {listening && <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1" opacity="0.3" />}
    </svg>
  )
}

function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  )
}

function Spinner() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" className="animate-spin" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" opacity="0.25" />
      <path d="M12 2a10 10 0 0 1 10 10" />
    </svg>
  )
}
