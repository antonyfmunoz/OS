import { useState, useRef, useEffect } from 'react'
import { useOperatorExperienceStore } from '../stores/operatorExperienceStore'
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

export function OperatorPanel() {
  const {
    currentSession,
    activeInput,
    voiceState,
    voiceSupported,
    interimTranscript,
    lastResponse,
    responseHistory,
    pendingApprovals,
    roadmapStatus,
    loading,
    error,
    loadOverview,
    loadStatus,
    loadApprovals,
    startVoiceInput,
    stopVoiceInput,
    setActiveInput,
    submitCommand,
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
    <div className="flex flex-col h-full overflow-hidden">
      <ConnectionBanner />

      <div className="flex-1 overflow-y-auto px-4 pt-3 pb-20 space-y-4">
        {/* 1. Command Header */}
        <CommandHeader
          sessionId={currentSession?.session_id ?? null}
          turnCount={currentSession?.turn_count ?? 0}
        />

        {/* 8. Session History */}
        {responseHistory.length > 0 && (
          <SessionHistory turns={responseHistory} />
        )}

        {/* 3. DEX Response (latest) */}
        {lastResponse && <DexResponseSection response={lastResponse} />}

        {/* 4. Work Packet Preview */}
        {lastResponse?.packet_preview && (
          <PacketPreviewSection packet={lastResponse.packet_preview} />
        )}

        {/* 5. Delegation Topology */}
        {lastResponse?.topology_preview && (
          <TopologySection topology={lastResponse.topology_preview} />
        )}

        {/* 6. Human Actions + Approval Gates */}
        {(lastResponse?.human_actions?.length || lastResponse?.approval_gates?.length) ? (
          <HumanActionsSection
            actions={lastResponse.human_actions}
            gates={lastResponse.approval_gates}
          />
        ) : null}

        {/* 7. Propagation Preview */}
        {lastResponse?.propagation_preview && (
          <PropagationSection preview={lastResponse.propagation_preview} />
        )}

        {/* 9. Roadmap / Status */}
        <RoadmapSection
          roadmap={roadmapStatus}
          approvals={pendingApprovals}
        />

        {error && (
          <div className="wv-card p-3 border border-danger/30">
            <span className="text-xs text-danger font-mono">{error}</span>
          </div>
        )}

        <div ref={historyEndRef} />
      </div>

      {/* 2. Voice/Text Command Box — pinned to bottom */}
      <div className="flex-shrink-0 border-t border-border px-4 py-3 bg-surface-primary">
        {/* Interim transcript */}
        {interimTranscript && (
          <div className="mb-2 px-2 py-1 bg-surface-secondary rounded text-xs text-text-tertiary italic font-mono">
            {interimTranscript}...
          </div>
        )}

        <div className="flex items-end gap-2">
          {/* Push-to-talk */}
          <button
            onClick={isListening ? stopVoiceInput : startVoiceInput}
            disabled={!voiceSupported}
            title={!voiceSupported ? 'Voice unavailable in this browser' : isListening ? 'Stop listening' : 'Push to talk'}
            className={`flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center transition-colors ${
              !voiceSupported
                ? 'bg-surface-secondary text-text-tertiary cursor-not-allowed'
                : isListening
                  ? 'bg-danger/20 text-danger animate-pulse'
                  : 'bg-surface-secondary text-text-secondary hover:bg-surface-tertiary hover:text-cyan'
            }`}
          >
            <MicIcon listening={isListening} />
          </button>

          {/* Text input */}
          <textarea
            ref={inputRef}
            value={activeInput}
            onChange={(e) => setActiveInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={voiceSupported ? 'Speak or type a command...' : 'Type a command...'}
            rows={1}
            className="flex-1 bg-surface-secondary text-text-primary text-sm rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-1 focus:ring-cyan/50 placeholder:text-text-tertiary font-mono"
          />

          {/* Submit */}
          <button
            onClick={handleSubmit}
            disabled={!activeInput.trim() || loading}
            className={`flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center transition-colors ${
              !activeInput.trim() || loading
                ? 'bg-surface-secondary text-text-tertiary cursor-not-allowed'
                : 'bg-cyan/20 text-cyan hover:bg-cyan/30'
            }`}
          >
            {loading ? <Spinner /> : <SendIcon />}
          </button>
        </div>

        {/* Voice state indicator */}
        <div className="mt-1.5 flex items-center gap-2 text-[10px] text-text-tertiary">
          <span className={`w-1.5 h-1.5 rounded-full ${
            voiceState === 'listening' ? 'bg-danger animate-pulse'
              : voiceState === 'processing' ? 'bg-warn'
              : voiceState === 'responded' ? 'bg-ok'
              : voiceState === 'error' ? 'bg-danger'
              : 'bg-text-tertiary'
          }`} />
          <span className="uppercase font-mono">{voiceState}</span>
          <span className="ml-auto font-mono text-text-tertiary">preview only — no execution without approval</span>
        </div>
      </div>
    </div>
  )
}

function CommandHeader({ sessionId, turnCount }: { sessionId: string | null; turnCount: number }) {
  return (
    <div className="flex items-center gap-3">
      <div>
        <h2 className="text-lg font-semibold text-text-primary">Operator</h2>
        <span className="text-[10px] text-text-tertiary font-mono">DEX command surface</span>
      </div>
      <div className="ml-auto flex items-center gap-3 text-[10px] font-mono">
        {sessionId && (
          <span className="text-text-tertiary">{sessionId} · {turnCount} turns</span>
        )}
        <span className="px-1.5 py-0.5 bg-ok/10 text-ok rounded text-[9px] uppercase">
          preview only
        </span>
      </div>
    </div>
  )
}

function SessionHistory({ turns }: { turns: SessionTurn[] }) {
  const [expanded, setExpanded] = useState(false)
  const visible = expanded ? turns : turns.slice(-3)

  return (
    <section>
      <div className="flex items-center gap-2 mb-2">
        <h3 className="wv-label">Session History</h3>
        {turns.length > 3 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-[10px] text-cyan hover:underline font-mono"
          >
            {expanded ? 'collapse' : `show all ${turns.length}`}
          </button>
        )}
      </div>
      <div className="space-y-2">
        {visible.map((turn) => (
          <div key={turn.turn_id} className="wv-card p-2">
            <div className="flex items-start gap-2">
              <span className="text-[9px] text-text-tertiary font-mono mt-0.5">
                {turn.input_mode === 'voice' ? 'MIC' : 'TXT'}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-text-primary truncate">{turn.input}</p>
                {turn.response && (
                  <p className="text-[11px] text-text-secondary mt-0.5 truncate">
                    → {turn.response.summary || turn.response.intent}
                  </p>
                )}
              </div>
              <span className="text-[9px] text-text-tertiary font-mono flex-shrink-0">
                {new Date(turn.timestamp).toLocaleTimeString()}
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function DexResponseSection({ response }: { response: DexResponse }) {
  return (
    <section className="wv-card p-3 border border-cyan/20">
      <h3 className="wv-label mb-2">DEX Response</h3>
      <div className="space-y-2 text-xs">
        <Row label="Intent" value={response.intent} />
        <Row label="Summary" value={response.summary} multiline />
        {response.current_state && <Row label="Current State" value={response.current_state} />}
        {response.recommended_next_action && (
          <Row label="Next Action" value={response.recommended_next_action} />
        )}
        <div className="flex gap-4 pt-1">
          <span className="text-text-tertiary">
            confidence: <span className="text-text-primary font-mono">{(response.confidence * 100).toFixed(0)}%</span>
          </span>
          <span className="text-text-tertiary">
            safety: <span className="text-ok font-mono">{response.safety_state}</span>
          </span>
          <span className="text-text-tertiary">
            executed: <span className={`font-mono ${response.execution_occurred ? 'text-danger' : 'text-ok'}`}>
              {response.execution_occurred ? 'YES' : 'NO'}
            </span>
          </span>
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
        {packet.domain && <Row label="Domain" value={packet.domain} />}
        {packet.project && <Row label="Project" value={packet.project} />}
        {packet.packet_id && <Row label="Packet ID" value={packet.packet_id} mono />}
        {(packet.leverage != null || packet.effectiveness != null) && (
          <div className="flex gap-4 pt-1 text-text-tertiary">
            {packet.leverage != null && <span>leverage: <span className="text-text-primary font-mono">{packet.leverage.toFixed(2)}</span></span>}
            {packet.effectiveness != null && <span>effectiveness: <span className="text-text-primary font-mono">{packet.effectiveness.toFixed(2)}</span></span>}
            {packet.efficiency != null && <span>efficiency: <span className="text-text-primary font-mono">{packet.efficiency.toFixed(2)}</span></span>}
          </div>
        )}
      </div>
    </section>
  )
}

function TopologySection({ topology }: { topology: TopologyPreview }) {
  return (
    <section className="wv-card p-3">
      <h3 className="wv-label mb-2">Delegation Topology</h3>
      <div className="space-y-1.5 text-xs">
        <Row label="Type" value={topology.topology_type} />
        {topology.lead_role_contract && <Row label="Lead" value={topology.lead_role_contract} />}
        {topology.reconvergence_point && <Row label="Reconvergence" value={topology.reconvergence_point} />}
        {topology.workcells.length > 0 && (
          <div className="pt-1">
            <span className="text-text-tertiary text-[10px]">Workcells ({topology.workcells.length})</span>
            <div className="mt-1 space-y-1">
              {topology.workcells.map((wc: WorkcellPreview, i: number) => (
                <div key={i} className="flex items-center gap-2 px-2 py-1 bg-surface-secondary rounded">
                  <span className="text-cyan font-mono text-[10px]">{wc.role}</span>
                  {wc.agent && <span className="text-text-tertiary text-[10px]">→ {wc.agent}</span>}
                  <span className={`ml-auto text-[9px] font-mono ${wc.status === 'active' ? 'text-ok' : 'text-text-tertiary'}`}>
                    {wc.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
        {topology.advisor_branches.length > 0 && (
          <div className="pt-1">
            <span className="text-text-tertiary text-[10px]">Advisors</span>
            <div className="mt-0.5 flex flex-wrap gap-1">
              {topology.advisor_branches.map((a: string, i: number) => (
                <span key={i} className="px-1.5 py-0.5 bg-surface-secondary text-text-secondary text-[10px] rounded font-mono">
                  {a}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  )
}

function HumanActionsSection({ actions, gates }: { actions: HumanAction[]; gates: ApprovalGate[] }) {
  return (
    <section className="wv-card p-3 border border-warn/20">
      <h3 className="wv-label mb-2">Human Actions & Approvals</h3>
      {actions.length > 0 && (
        <div className="mb-2">
          <span className="text-[10px] text-text-tertiary">Required Actions</span>
          <div className="mt-1 space-y-1">
            {actions.map((a: HumanAction, i: number) => (
              <div key={i} className="flex items-start gap-2 text-xs">
                <span className={`mt-0.5 w-1.5 h-1.5 rounded-full flex-shrink-0 ${a.blocking ? 'bg-danger' : 'bg-warn'}`} />
                <div>
                  <span className="text-text-primary">{a.action}</span>
                  <span className="text-text-tertiary ml-1">— {a.reason}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      {gates.length > 0 && (
        <div>
          <span className="text-[10px] text-text-tertiary">Approval Gates</span>
          <div className="mt-1 space-y-1">
            {gates.map((g: ApprovalGate) => (
              <div key={g.gate_id} className="flex items-center gap-2 text-xs">
                <span className={`w-1.5 h-1.5 rounded-full ${
                  g.status === 'approved' ? 'bg-ok' : g.status === 'rejected' ? 'bg-danger' : 'bg-warn'
                }`} />
                <span className="text-text-primary flex-1">{g.description}</span>
                <span className={`text-[9px] font-mono uppercase ${
                  g.status === 'approved' ? 'text-ok' : g.status === 'rejected' ? 'text-danger' : 'text-warn'
                }`}>{g.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}

function PropagationSection({ preview }: { preview: PropagationPreview }) {
  return (
    <section className="wv-card p-3">
      <h3 className="wv-label mb-2">Propagation Preview</h3>
      <div className="space-y-1.5 text-xs">
        <div className="flex gap-4 text-text-tertiary">
          <span>waves: <span className="text-text-primary font-mono">{preview.waves}</span></span>
          <span>affected: <span className="text-text-primary font-mono">{preview.affected_nodes.length}</span></span>
          {preview.validation_required && <span className="text-warn">validation required</span>}
          {preview.approval_required && <span className="text-warn">approval required</span>}
        </div>
        {preview.affected_nodes.length > 0 && (
          <div className="space-y-1 pt-1">
            {preview.affected_nodes.map((n: PropagationNode) => (
              <div key={n.node_id} className="flex items-center gap-2 px-2 py-1 bg-surface-secondary rounded">
                <span className="text-[9px] text-text-tertiary font-mono">W{n.wave}</span>
                <span className="text-text-primary text-[11px] flex-1 truncate">{n.label}</span>
                <span className="text-text-tertiary text-[10px]">{n.impact}</span>
              </div>
            ))}
          </div>
        )}
        {preview.blocked_actions.length > 0 && (
          <div className="pt-1">
            <span className="text-[10px] text-danger">Blocked: {preview.blocked_actions.join(', ')}</span>
          </div>
        )}
        {preview.noop_actions.length > 0 && (
          <div>
            <span className="text-[10px] text-text-tertiary">No-op: {preview.noop_actions.join(', ')}</span>
          </div>
        )}
      </div>
    </section>
  )
}

function RoadmapSection({
  roadmap,
  approvals,
}: {
  roadmap: Record<string, unknown> | null
  approvals: Array<{ id: string; description: string; status: string }>
}) {
  return (
    <section className="wv-card p-3">
      <h3 className="wv-label mb-2">Roadmap & Status</h3>
      <div className="space-y-1.5 text-xs">
        {roadmap ? (
          <>
            {roadmap.current_phase != null && <Row label="Current Phase" value={String(roadmap.current_phase)} />}
            {roadmap.next_phase != null && <Row label="Next Phase" value={String(roadmap.next_phase)} />}
            {roadmap.state != null && <Row label="State" value={String(roadmap.state)} />}
            {Array.isArray(roadmap.blockers) && roadmap.blockers.length > 0 && (
              <div className="pt-1">
                <span className="text-danger text-[10px]">
                  Blockers: {(roadmap.blockers as string[]).join(', ')}
                </span>
              </div>
            )}
          </>
        ) : (
          <span className="text-text-tertiary">Loading roadmap status...</span>
        )}
        <div className="pt-2">
          <span className="text-[10px] text-text-tertiary">
            Pending Approvals: {approvals.length === 0 ? 'none' : approvals.length}
          </span>
          {approvals.length > 0 && (
            <div className="mt-1 space-y-1">
              {approvals.map((a) => (
                <div key={a.id} className="flex items-center gap-2 text-[11px]">
                  <span className="w-1.5 h-1.5 rounded-full bg-warn" />
                  <span className="text-text-primary truncate flex-1">{a.description}</span>
                  <span className="text-warn text-[9px] font-mono uppercase">{a.status}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

function Row({
  label,
  value,
  color,
  mono,
  multiline,
}: {
  label: string
  value: string
  color?: string
  mono?: boolean
  multiline?: boolean
}) {
  return (
    <div className={multiline ? '' : 'flex items-baseline gap-2'}>
      <span className="text-text-tertiary text-[10px] flex-shrink-0">{label}:</span>
      <span className={`${color ?? 'text-text-primary'} ${mono ? 'font-mono' : ''} ${multiline ? 'block mt-0.5' : ''}`}>
        {value}
      </span>
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
