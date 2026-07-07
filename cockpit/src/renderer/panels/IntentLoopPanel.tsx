// Intent-loop panel — P4S-31 read surface + P4S-31B input surface.
//
// Cockpit surface for the substrate-owned MVP operating loop. Renders the
// server-truth read surface (GET /api/umh/intent-loop) AND exposes the bounded
// operating loop: an operator text input that captures one intent (POST
// /intent-loop/submit → held at AWAITING_APPROVAL) and per-loop approve/reject
// controls (POST /intent-loop/{id}/decision). Every write routes through the
// SERVER's governed_mutation runtime under a registered MutationSpec — the
// cockpit never advances the gate itself; it calls the authed routes and
// re-reads server truth. Skeleton controls, not product polish. Modeled on
// OperatingLoopPanel + ProjectionMirrorsPanel: same polling pattern, same
// tailwind tokens, no layout/nav/chat changes.
import { useState } from 'react'
import {
  GitBranch, RefreshCw, CheckCircle2, Clock, ShieldCheck, XCircle, Send, Check, X,
} from 'lucide-react'
import { usePolling } from '../hooks/usePolling'
import { useIntentLoopStore, type IntentLoopRecord } from '../stores/intentLoopStore'
import { useRealtimeStore } from '../stores/realtimeStore'

function stageColor(stage: string): string {
  switch (stage) {
    case 'submitted': return 'bg-blue-400/10 text-blue-400'
    case 'spec_parsed': return 'bg-purple-400/10 text-purple-400'
    case 'packet_drafted': return 'bg-cyan/10 text-cyan'
    case 'awaiting_approval': return 'bg-yellow-400/10 text-yellow-400'
    case 'approved': return 'bg-green-400/10 text-green-400'
    case 'rejected': return 'bg-red-400/10 text-red-400'
    case 'proof_recorded': return 'bg-green-400/10 text-green-400'
    default: return 'bg-text-tertiary/10 text-text-tertiary'
  }
}

function LoopCard({
  loop,
  onDecide,
  deciding,
}: {
  loop: IntentLoopRecord
  onDecide: (loopId: string, decision: 'approve' | 'reject') => void
  deciding: boolean
}) {
  const held = loop.stage === 'awaiting_approval'
  const proof = loop.proof
  return (
    <div className="bg-surface-raised border border-border rounded p-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-mono text-text-primary truncate flex-1">
          {loop.spec.raw_text}
        </span>
        <span className={`text-[9px] font-mono px-2 py-0.5 rounded ml-2 ${stageColor(loop.stage)}`}>
          {loop.stage}
        </span>
      </div>
      <div className="flex items-center gap-2 flex-wrap text-[9px] font-mono text-text-tertiary">
        <span className="px-1.5 py-0.5 rounded bg-text-tertiary/10">{loop.spec.intent_type}</span>
        <span className="px-1.5 py-0.5 rounded bg-text-tertiary/10">risk: {loop.spec.risk_level}</span>
        <span className="px-1.5 py-0.5 rounded bg-text-tertiary/10">
          {loop.draft.actionable ? 'actionable' : 'non-actionable'}
        </span>
        {loop.spec.deterministic && (
          <span className="px-1.5 py-0.5 rounded bg-text-tertiary/10">deterministic</span>
        )}
      </div>
      {held && (
        <div className="flex items-center justify-between gap-2 mt-2">
          <div className="flex items-center gap-1 text-[9px] font-mono text-yellow-400">
            <Clock size={10} />
            approval gate HELD — awaiting governed decision
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => onDecide(loop.loop_id, 'approve')}
              disabled={deciding}
              className="flex items-center gap-1 px-2 py-0.5 text-[9px] font-mono uppercase bg-green-400/10 text-green-400 border border-green-400/30 rounded hover:bg-green-400/20 disabled:opacity-50"
            >
              <Check size={10} /> Approve
            </button>
            <button
              onClick={() => onDecide(loop.loop_id, 'reject')}
              disabled={deciding}
              className="flex items-center gap-1 px-2 py-0.5 text-[9px] font-mono uppercase bg-red-400/10 text-red-400 border border-red-400/30 rounded hover:bg-red-400/20 disabled:opacity-50"
            >
              <X size={10} /> Reject
            </button>
          </div>
        </div>
      )}
      {proof && (
        <div className="flex items-center gap-2 mt-2 text-[9px] font-mono text-text-tertiary flex-wrap">
          <ShieldCheck size={10} className="text-green-400" />
          <span>governed: {proof.governance_status}</span>
          {proof.envelope_id && <span>env: {proof.envelope_id}</span>}
          {proof.degraded && <span className="text-yellow-400">degraded-audited</span>}
          <span>{proof.decision}</span>
        </div>
      )}
    </div>
  )
}

export function IntentLoopPanel() {
  const realtimeStatus = useRealtimeStore((s) => s.status)
  const surface = useIntentLoopStore((s) => s.surface)
  const loading = useIntentLoopStore((s) => s.loading)
  const error = useIntentLoopStore((s) => s.error)
  const submitting = useIntentLoopStore((s) => s.submitting)
  const decidingLoopId = useIntentLoopStore((s) => s.decidingLoopId)
  const fetchSurface = useIntentLoopStore((s) => s.fetchSurface)
  const submitIntent = useIntentLoopStore((s) => s.submitIntent)
  const decideLoop = useIntentLoopStore((s) => s.decideLoop)

  const [text, setText] = useState('')

  usePolling(
    () => { fetchSurface() },
    realtimeStatus === 'connected' ? 15000 : 5000,
  )

  const loops = surface?.loops ?? []

  const handleSubmit = async () => {
    const trimmed = text.trim()
    if (!trimmed || submitting) return
    const result = await submitIntent(trimmed)
    if (result.submitted) setText('')
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between border-b border-border px-4 h-9 shrink-0">
        <div className="flex items-center gap-2">
          <GitBranch size={14} className="text-cyan" />
          <span className="text-[10px] font-mono text-cyan uppercase tracking-wider">Intent Loop</span>
          <span className="text-[9px] text-text-tertiary">MVP operating loop — intent → gate → proof</span>
          {surface && surface.awaiting_approval > 0 && (
            <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-yellow-400/10 text-yellow-400">
              {surface.awaiting_approval} awaiting
            </span>
          )}
        </div>
        <button
          onClick={() => fetchSurface()}
          disabled={loading}
          className="flex items-center gap-1 px-2 py-1 text-[10px] font-mono uppercase bg-cyan/10 text-cyan border border-cyan/30 rounded hover:bg-cyan/20 disabled:opacity-50"
        >
          <RefreshCw size={10} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      <div className="flex items-center gap-2 px-4 py-2 border-b border-border shrink-0">
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSubmit() }}
          placeholder="Capture an intent — submit lands it at the approval gate"
          disabled={submitting}
          className="flex-1 bg-surface-raised border border-border rounded px-2 py-1 text-xs font-mono text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-cyan/50 disabled:opacity-50"
        />
        <button
          onClick={handleSubmit}
          disabled={submitting || text.trim().length === 0}
          className="flex items-center gap-1 px-3 py-1 text-[10px] font-mono uppercase bg-cyan/10 text-cyan border border-cyan/30 rounded hover:bg-cyan/20 disabled:opacity-50"
        >
          <Send size={10} className={submitting ? 'animate-pulse' : ''} />
          Submit
        </button>
      </div>

      {surface && (
        <div className="flex items-center gap-3 px-4 py-2 border-b border-border shrink-0 text-[9px] font-mono text-text-tertiary">
          <span className="flex items-center gap-1">
            <CheckCircle2 size={10} className="text-green-400" /> {surface.proof_recorded} proven
          </span>
          <span className="flex items-center gap-1">
            <Clock size={10} className="text-yellow-400" /> {surface.awaiting_approval} held
          </span>
          <span>total {surface.total}</span>
          {surface.connection_status !== 'connected' && (
            <span className="flex items-center gap-1 text-red-400">
              <XCircle size={10} /> {surface.connection_status}
            </span>
          )}
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {loading && loops.length === 0 && (
          <div className="text-text-tertiary text-xs font-mono">Loading intent loops...</div>
        )}
        {error && (
          <div className="text-red-400 text-xs font-mono">{error}</div>
        )}
        {loops.map((loop) => (
          <LoopCard
            key={loop.loop_id}
            loop={loop}
            onDecide={decideLoop}
            deciding={decidingLoopId === loop.loop_id}
          />
        ))}
        {!loading && loops.length === 0 && !error && (
          <div className="flex items-center gap-2 text-text-tertiary text-xs font-mono">
            <Clock size={14} />
            No intent loops yet
          </div>
        )}
      </div>
    </div>
  )
}
