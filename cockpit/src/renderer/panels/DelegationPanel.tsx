import { useEffect, useState } from 'react'
import { Workflow, RefreshCw, Check, X, Layers } from 'lucide-react'
import { useDelegationStore } from '../stores/delegationStore'

type Tab = 'proposals' | 'missions' | 'queue'

function str(obj: Record<string, unknown>, key: string, fallback = ''): string {
  const v = obj[key]
  return v === undefined || v === null ? fallback : String(v)
}

function num(obj: Record<string, unknown> | null, key: string): number {
  if (!obj) return 0
  const v = obj[key]
  return typeof v === 'number' ? v : 0
}

function missionStatusColor(status: string): string {
  switch (status) {
    case 'queued': return 'bg-blue-400/10 text-blue-400'
    case 'claimed':
    case 'planning': return 'bg-purple-400/10 text-purple-400'
    case 'work_packet_drafted': return 'bg-cyan/10 text-cyan'
    case 'work_packet_approved': return 'bg-yellow-400/10 text-yellow-400'
    case 'executing': return 'bg-orange-400/10 text-orange-400'
    case 'completed': return 'bg-green-400/10 text-green-400'
    case 'failed': return 'bg-red-400/10 text-red-400'
    case 'cancelled': return 'bg-text-tertiary/10 text-text-tertiary'
    default: return 'bg-text-tertiary/10 text-text-tertiary'
  }
}

export function DelegationPanel() {
  const [tab, setTab] = useState<Tab>('proposals')
  const {
    summary,
    proposals,
    missions,
    activeMissions,
    loading,
    fetchSummary,
    fetchProposals,
    fetchMissions,
    fetchActiveMissions,
    approveProposal,
    rejectProposal,
    approveWorkPacket,
    cancelMission,
  } = useDelegationStore()

  useEffect(() => {
    fetchSummary()
    fetchProposals()
    fetchMissions()
    fetchActiveMissions()
  }, [])

  const refresh = () => {
    fetchSummary()
    fetchProposals()
    fetchMissions()
    fetchActiveMissions()
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between border-b border-border px-4 h-9 shrink-0">
        <div className="flex items-center gap-2">
          <Workflow size={14} className="text-cyan" />
          <span className="text-[10px] font-mono text-cyan uppercase tracking-wider">Delegation</span>
          {activeMissions.length > 0 && (
            <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-cyan/10 text-cyan">
              {activeMissions.length} active
            </span>
          )}
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="flex items-center gap-1 px-2 py-1 text-[10px] font-mono uppercase bg-cyan/10 text-cyan border border-cyan/30 rounded hover:bg-cyan/20 disabled:opacity-50"
        >
          <RefreshCw size={10} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      <div className="flex border-b border-border shrink-0">
        {(['proposals', 'missions', 'queue'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-[10px] font-mono uppercase transition-colors ${
              tab === t ? 'text-cyan border-b-2 border-cyan' : 'text-text-tertiary hover:text-text-secondary'
            }`}
          >
            {t}
            {t === 'proposals' && proposals.length > 0 && (
              <span className="ml-1 px-1 bg-cyan/20 text-cyan rounded text-[9px]">{proposals.length}</span>
            )}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {loading && proposals.length === 0 && missions.length === 0 && (
          <div className="text-text-tertiary text-xs font-mono">Loading delegation...</div>
        )}

        {tab === 'proposals' && (
          <div className="space-y-2">
            {proposals.map((p, i) => {
              const id = str(p, 'id', `proposal-${i}`)
              const intent = str(p, 'clarified_intent') || str(p, 'intent', `Proposal ${i}`)
              const keeps = str(p, 'what_orchestrator_keeps')
              const delegated = str(p, 'what_gets_delegated')
              return (
                <div key={id} className="bg-surface-raised border border-border rounded p-3">
                  <div className="text-xs font-mono text-text-primary mb-2">{intent}</div>
                  {keeps && (
                    <div className="mb-1">
                      <div className="text-text-tertiary text-[9px] font-mono uppercase">Orchestrator keeps</div>
                      <div className="text-[10px] font-mono text-text-secondary">{keeps}</div>
                    </div>
                  )}
                  {delegated && (
                    <div className="mb-2">
                      <div className="text-text-tertiary text-[9px] font-mono uppercase">Gets delegated</div>
                      <div className="text-[10px] font-mono text-text-secondary">{delegated}</div>
                    </div>
                  )}
                  <div className="flex gap-2">
                    <button
                      onClick={() => approveProposal(id)}
                      className="flex items-center gap-1 px-2 py-1 text-[9px] font-mono uppercase bg-green-400/10 text-green-400 border border-green-400/30 rounded hover:bg-green-400/20"
                    >
                      <Check size={10} />
                      Approve
                    </button>
                    <button
                      onClick={() => rejectProposal(id)}
                      className="flex items-center gap-1 px-2 py-1 text-[9px] font-mono uppercase bg-red-400/10 text-red-400 border border-red-400/30 rounded hover:bg-red-400/20"
                    >
                      <X size={10} />
                      Reject
                    </button>
                  </div>
                </div>
              )
            })}
            {proposals.length === 0 && (
              <div className="text-text-tertiary text-xs font-mono">No pending proposals</div>
            )}
          </div>
        )}

        {tab === 'missions' && (
          <div className="space-y-2">
            {missions.map((m, i) => {
              const id = str(m, 'id', `mission-${i}`)
              const status = str(m, 'status', 'queued')
              const intent = str(m, 'clarified_intent') || str(m, 'intent', `Mission ${i}`)
              const needsApproval = status === 'work_packet_drafted'
              const cancellable = !['completed', 'failed', 'cancelled'].includes(status)
              return (
                <div key={id} className="bg-surface-raised border border-border rounded p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-text-primary truncate flex-1">{intent}</span>
                    <span className={`text-[9px] font-mono px-2 py-0.5 rounded ml-2 ${missionStatusColor(status)}`}>
                      {status}
                    </span>
                  </div>
                  <div className="text-[9px] font-mono text-text-tertiary mb-2">{id}</div>
                  <div className="flex gap-2">
                    {needsApproval && (
                      <button
                        onClick={() => approveWorkPacket(id)}
                        className="flex items-center gap-1 px-2 py-1 text-[9px] font-mono uppercase bg-yellow-400/10 text-yellow-400 border border-yellow-400/30 rounded hover:bg-yellow-400/20"
                      >
                        <Check size={10} />
                        Approve Work Packet
                      </button>
                    )}
                    {cancellable && (
                      <button
                        onClick={() => cancelMission(id)}
                        className="flex items-center gap-1 px-2 py-1 text-[9px] font-mono uppercase bg-red-400/10 text-red-400 border border-red-400/30 rounded hover:bg-red-400/20"
                      >
                        <X size={10} />
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
            {missions.length === 0 && (
              <div className="text-text-tertiary text-xs font-mono">No missions</div>
            )}
          </div>
        )}

        {tab === 'queue' && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-surface-raised border border-border rounded p-3 text-center">
                <div className="text-text-tertiary text-[9px] font-mono uppercase mb-1">Queue Depth</div>
                <div className="text-2xl font-mono text-cyan">{num(summary, 'queue_depth')}</div>
              </div>
              <div className="bg-surface-raised border border-border rounded p-3 text-center">
                <div className="text-text-tertiary text-[9px] font-mono uppercase mb-1">Max Concurrent</div>
                <div className="text-2xl font-mono text-text-primary">{num(summary, 'max_concurrent')}</div>
              </div>
            </div>
            <div>
              <div className="text-text-tertiary text-[9px] font-mono uppercase mb-2">Mission Ordering</div>
              <div className="space-y-2">
                {activeMissions.map((m, i) => {
                  const id = str(m, 'id', `mission-${i}`)
                  const status = str(m, 'status', 'queued')
                  const intent = str(m, 'clarified_intent') || str(m, 'intent', `Mission ${i}`)
                  return (
                    <div key={id} className="bg-surface-raised border border-border rounded p-3 flex items-center gap-2">
                      <span className="text-[9px] font-mono text-text-tertiary w-5 shrink-0">{i + 1}</span>
                      <Layers size={12} className="text-cyan shrink-0" />
                      <span className="text-xs font-mono text-text-primary truncate flex-1">{intent}</span>
                      <span className={`text-[9px] font-mono px-2 py-0.5 rounded ${missionStatusColor(status)}`}>
                        {status}
                      </span>
                    </div>
                  )
                })}
                {activeMissions.length === 0 && (
                  <div className="text-text-tertiary text-xs font-mono">Queue is empty</div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
