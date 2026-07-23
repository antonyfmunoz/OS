import { useState, useEffect, useCallback } from 'react'
import { fetchApi } from '../api/client'
import { useViewContextStore } from '../stores/viewContextStore'
import { useExecutionAttemptStore } from '../stores/executionAttemptStore'
import { CronTable, type CronJob } from '../components/CronTable'
import { DetailDrawer } from '../components/DetailDrawer'
import { StatusBadge } from '../components/StatusBadge'

interface WorkPacket {
  packet_id: string
  title: string
  status: string
  risk_class: string
  domain: string
  intent_summary: string
  parent_packet_id: string
  child_packet_ids: string[]
  dependencies: string[]
  leverage_score: number
  priority: number
}

interface OvernightItem {
  packet_id: string
  title: string
  risk_class: string
  safety: string
}

type WorkTab = 'packets' | 'tasks' | 'workflows' | 'overnight'

const RISK_COLOR: Record<string, string> = {
  low: 'text-ok',
  medium: 'text-warn',
  high: 'text-danger',
  critical: 'text-danger',
}

const STATUS_COLOR: Record<string, string> = {
  drafted: 'text-text-tertiary',
  classified: 'text-text-secondary',
  planned: 'text-cyan',
  executing: 'text-ok',
  paused: 'text-warn',
  completed: 'text-ok',
  failed: 'text-danger',
  blocked: 'text-warn',
}

const OVERNIGHT_SAFETY_COLOR: Record<string, string> = {
  safe: 'bg-ok',
  approval_needed: 'bg-warn',
  blocked: 'bg-danger',
}

export function WorkPanel() {
  const [activeTab, setActiveTab] = useState<WorkTab>('packets')
  const [packets, setPackets] = useState<WorkPacket[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [decomposeInput, setDecomposeInput] = useState('')
  const [decomposing, setDecomposing] = useState(false)
  const [expandedBatches, setExpandedBatches] = useState<Set<string>>(new Set())
  const [overnightStatus, setOvernightStatus] = useState<{
    safe: OvernightItem[]
    pending: OvernightItem[]
    blocked: OvernightItem[]
  }>({ safe: [], pending: [], blocked: [] })
  const setViewContext = useViewContextStore((s) => s.setContext)
  const openDrawer = useViewContextStore((s) => s.openDrawer)
  const closeDrawer = useViewContextStore((s) => s.closeDrawer)
  const drawerOpen = useViewContextStore((s) => s.drawerOpen)
  const [drawerPacket, setDrawerPacket] = useState<WorkPacket | null>(null)

  type DrawerTab = 'Details' | 'Dependencies' | 'History' | 'Proof' | 'Comms'
  const [drawerTab, setDrawerTab] = useState<DrawerTab>('Details')

  const fetchPackets = useCallback(async () => {
    try {
      const data = await fetchApi<{ packets?: WorkPacket[] }>('/command-center/work-packets?limit=100')
      setPackets(data.packets || [])
      setError('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'fetch failed')
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchOvernight = useCallback(async () => {
    try {
      const data = await fetchApi<{ safe_items?: OvernightItem[]; pending_items?: OvernightItem[]; blocked_items?: OvernightItem[] }>('/workstation/overnight/status')
      setOvernightStatus({
        safe: data.safe_items || [],
        pending: data.pending_items || [],
        blocked: data.blocked_items || [],
      })
    } catch {
      /* silent */
    }
  }, [])

  useEffect(() => {
    fetchPackets()
    fetchOvernight()
    const id = setInterval(() => {
      fetchPackets()
      fetchOvernight()
    }, 10000)
    return () => clearInterval(id)
  }, [fetchPackets, fetchOvernight])

  const handleDecompose = useCallback(async () => {
    if (!decomposeInput.trim()) return
    setDecomposing(true)
    try {
      await fetchApi('/command-center/work-packets/decompose', {
        method: 'POST',
        body: JSON.stringify({ user_intent: decomposeInput }),
      })
      setDecomposeInput('')
      fetchPackets()
    } catch {
      /* silent */
    }
    setDecomposing(false)
  }, [decomposeInput, fetchPackets])

  const handleControl = useCallback(
    async (packetId: string, action: 'pause' | 'resume' | 'stop') => {
      try {
        await fetchApi(`/workstation/execution/${action}`, {
          method: 'POST',
          body: JSON.stringify({ reason: `operator_${action}`, packet_id: packetId }),
        })
        fetchPackets()
      } catch {
        /* silent */
      }
    },
    [fetchPackets],
  )

  const handleOvernightApprove = useCallback(
    async (packetId: string) => {
      try {
        await fetchApi('/workstation/overnight/approve', {
          method: 'POST',
          body: JSON.stringify({ packet_id: packetId }),
        })
        fetchOvernight()
      } catch {
        /* silent */
      }
    },
    [fetchOvernight],
  )

  const toggleBatch = (id: string) => {
    setExpandedBatches((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  // Group packets by parent
  const parentPackets = packets.filter((p) => p.child_packet_ids?.length > 0)
  const standalonePackets = packets.filter(
    (p) => !p.parent_packet_id && !(p.child_packet_ids?.length > 0),
  )

  // Derive overnight safety from risk_class
  const overnightSafety = (riskClass: string): string => {
    if (riskClass === 'low') return 'safe'
    if (riskClass === 'medium') return 'approval_needed'
    return 'blocked'
  }

  const tabs: Array<{ id: WorkTab; label: string }> = [
    { id: 'packets', label: 'Packets' },
    { id: 'tasks', label: 'Tasks' },
    { id: 'workflows', label: 'Workflows' },
    { id: 'overnight', label: 'Overnight' },
  ]

  if (loading)
    return <div className="p-4 text-xs font-mono text-text-tertiary">Loading work packets...</div>
  if (error) return <div className="p-4 text-xs font-mono text-danger">Error: {error}</div>

  return (
    <div className="flex flex-col h-full text-xs font-mono">
      {/* Tab bar */}
      <div className="flex items-center border-b border-border px-4 shrink-0">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`px-3 py-2 text-[10px] uppercase tracking-wider transition-colors ${
              activeTab === t.id
                ? 'text-cyan border-b-2 border-cyan'
                : 'text-text-tertiary hover:text-text-secondary'
            }`}
          >
            {t.label}
          </button>
        ))}
        <div className="flex-1" />
        <span className="text-[10px] text-text-tertiary">{packets.length} packets</span>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'packets' && (
          <div className="space-y-2">
            {/* Decompose input */}
            <div className="flex gap-2 mb-3">
              <input
                value={decomposeInput}
                onChange={(e) => setDecomposeInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleDecompose()}
                placeholder="Describe complex intent to decompose into batch..."
                className="flex-1 px-3 py-2 bg-surface-raised border border-border rounded text-text-primary placeholder-text-tertiary text-[11px]"
              />
              <button
                onClick={handleDecompose}
                disabled={decomposing || !decomposeInput.trim()}
                className="px-3 py-2 bg-cyan-glow text-cyan border border-cyan/30 rounded text-[10px] uppercase tracking-wider hover:bg-cyan/20 disabled:opacity-30"
              >
                {decomposing ? '...' : 'Decompose'}
              </button>
            </div>

            {/* Batch groups (parent packets) */}
            {parentPackets.map((parent) => {
              const children = packets.filter(
                (p) => p.parent_packet_id === parent.packet_id,
              )
              const isExpanded = expandedBatches.has(parent.packet_id)
              return (
                <div key={parent.packet_id} className="border border-border rounded">
                  <button
                    onClick={() => toggleBatch(parent.packet_id)}
                    className="w-full flex items-center gap-2 px-3 py-2 hover:bg-surface-raised transition-colors text-left"
                  >
                    <span className="text-text-tertiary">
                      {isExpanded ? '▾' : '▸'}
                    </span>
                    <span className="text-cyan flex-1 truncate">{parent.title}</span>
                    <span className="text-[9px] text-text-tertiary">
                      {children.length} children
                    </span>
                    <span
                      className={`text-[9px] ${RISK_COLOR[parent.risk_class] || ''}`}
                    >
                      {parent.risk_class}
                    </span>
                    <span
                      className={`text-[9px] ${STATUS_COLOR[parent.status] || ''}`}
                    >
                      {parent.status}
                    </span>
                  </button>
                  {isExpanded && (
                    <div className="border-t border-border">
                      {children.map((child) => (
                        <PacketCard
                          key={child.packet_id}
                          packet={child}
                          overnightSafety={overnightSafety(child.risk_class)}
                          onControl={handleControl}
                          onSelect={() => {
                            setDrawerPacket(child)
                            setDrawerTab('Details')
                            openDrawer('work_packet', child.packet_id, child.title)
                          }}
                          indent
                        />
                      ))}
                    </div>
                  )}
                </div>
              )
            })}

            {/* Standalone packets */}
            {standalonePackets.map((p) => (
              <PacketCard
                key={p.packet_id}
                packet={p}
                overnightSafety={overnightSafety(p.risk_class)}
                onControl={handleControl}
                onSelect={() => {
                  setDrawerPacket(p)
                  setDrawerTab('Details')
                  openDrawer('work_packet', p.packet_id, p.title)
                }}
              />
            ))}

            {packets.length === 0 && (
              <p className="text-text-tertiary text-center py-8">
                No work packets. Use the decompose bar above or create from Command
                Center.
              </p>
            )}
          </div>
        )}

        {activeTab === 'tasks' && (
          <div className="text-text-tertiary text-center py-8">
            <p>Task tracking integrated with work packets.</p>
            <p className="mt-1">Use Packets tab for full work lifecycle.</p>
          </div>
        )}

        {activeTab === 'workflows' && (
          <CronTable jobs={[]} />
        )}

        {activeTab === 'overnight' && (
          <div className="space-y-4">
            <OvernightSection
              title="Safe to Run"
              items={overnightStatus.safe}
              color="ok"
            />
            <OvernightSection
              title="Pending Approval"
              items={overnightStatus.pending}
              color="warn"
              onApprove={handleOvernightApprove}
            />
            <OvernightSection
              title="Blocked (Requires Return)"
              items={overnightStatus.blocked}
              color="danger"
            />
          </div>
        )}
      </div>

      {/* Work Packet DetailDrawer */}
      <DetailDrawer
        open={drawerOpen && drawerPacket !== null}
        onClose={() => {
          closeDrawer()
          setDrawerPacket(null)
        }}
        title={drawerPacket?.title || ''}
        subtitle={drawerPacket ? `${drawerPacket.domain} / ${drawerPacket.risk_class}` : ''}
        badge={drawerPacket ? <StatusBadge status={drawerPacket.status} dot /> : undefined}
        tabs={['Details', 'Dependencies', 'History', 'Proof', 'Comms']}
        activeTab={drawerTab}
        onTabChange={(t) => setDrawerTab(t as DrawerTab)}
      >
        {drawerPacket && drawerTab === 'Details' && (
          <div className="space-y-3 text-xs">
            <div>
              <span className="wv-label">Status</span>
              <div className="mt-1"><StatusBadge status={drawerPacket.status} dot /></div>
            </div>
            <div>
              <span className="wv-label">Risk</span>
              <p className="mt-1" style={{ color: 'var(--color-text-primary)' }}>{drawerPacket.risk_class}</p>
            </div>
            <div>
              <span className="wv-label">Domain</span>
              <p className="mt-1" style={{ color: 'var(--color-text-primary)' }}>{drawerPacket.domain}</p>
            </div>
            {drawerPacket.intent_summary && (
              <div>
                <span className="wv-label">Intent</span>
                <p className="mt-1" style={{ color: 'var(--color-text-secondary)' }}>{drawerPacket.intent_summary}</p>
              </div>
            )}
            <div className="flex gap-4">
              <div>
                <span className="wv-label">Priority</span>
                <p className="mt-1" style={{ color: 'var(--color-text-primary)' }}>{drawerPacket.priority}</p>
              </div>
              <div>
                <span className="wv-label">Leverage</span>
                <p className="mt-1" style={{ color: 'var(--color-text-primary)' }}>{drawerPacket.leverage_score}</p>
              </div>
            </div>
            {drawerPacket.parent_packet_id && (
              <div>
                <span className="wv-label">Parent</span>
                <p className="mt-1 font-mono text-[10px]" style={{ color: 'var(--color-cyan)' }}>{drawerPacket.parent_packet_id}</p>
              </div>
            )}
            {drawerPacket.child_packet_ids?.length > 0 && (
              <div>
                <span className="wv-label">Children ({drawerPacket.child_packet_ids.length})</span>
                <div className="mt-1 space-y-1">
                  {drawerPacket.child_packet_ids.map((id) => (
                    <p key={id} className="font-mono text-[10px]" style={{ color: 'var(--color-text-secondary)' }}>{id}</p>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {drawerPacket && drawerTab === 'Dependencies' && (
          <div className="text-xs">
            {drawerPacket.dependencies?.length > 0 ? (
              <div className="space-y-1">
                {drawerPacket.dependencies.map((dep) => (
                  <p key={dep} className="font-mono text-[10px]" style={{ color: 'var(--color-text-secondary)' }}>{dep}</p>
                ))}
              </div>
            ) : (
              <p style={{ color: 'var(--color-text-tertiary)' }}>No dependencies</p>
            )}
          </div>
        )}

        {drawerPacket && drawerTab === 'History' && (
          <p className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
            No history available for this packet
          </p>
        )}

        {drawerPacket && drawerTab === 'Proof' && (
          <p className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
            No proof attached yet
          </p>
        )}

        {drawerPacket && drawerTab === 'Comms' && (
          <p className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
            No comms thread linked yet
          </p>
        )}
      </DetailDrawer>
    </div>
  )
}

function PacketCard({
  packet,
  overnightSafety,
  onControl,
  onSelect,
  indent,
}: {
  packet: WorkPacket
  overnightSafety: string
  onControl: (id: string, action: 'pause' | 'resume' | 'stop') => void
  onSelect: () => void
  indent?: boolean
}) {
  return (
    <div
      onClick={onSelect}
      className={`flex items-center gap-2 px-3 py-2 hover:bg-surface-raised transition-colors cursor-pointer ${indent ? 'pl-8' : ''}`}
    >
      {/* Overnight safety dot */}
      <span
        className={`w-2 h-2 rounded-full shrink-0 ${OVERNIGHT_SAFETY_COLOR[overnightSafety] || 'bg-text-tertiary'}`}
        title={`Overnight: ${overnightSafety}`}
      />
      {/* Title + meta */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-text-primary truncate">{packet.title}</span>
          <span
            className={`text-[9px] shrink-0 ${STATUS_COLOR[packet.status] || ''}`}
          >
            {packet.status}
          </span>
        </div>
        {packet.dependencies?.length > 0 && (
          <div className="text-[9px] text-text-tertiary mt-1">
            depends on: {packet.dependencies.map((d) => d.slice(0, 12)).join(', ')}
          </div>
        )}
      </div>
      {/* Risk + domain */}
      <span className={`text-[9px] shrink-0 ${RISK_COLOR[packet.risk_class] || ''}`}>
        {packet.risk_class}
      </span>
      <span className="text-[9px] text-text-tertiary shrink-0">{packet.domain}</span>
      {/* Execution overlay — attempt count / phase / blocker / proof */}
      <ExecutionOverlayChip packetId={packet.packet_id} />
      {/* Control buttons */}
      <div className="flex gap-1 shrink-0">
        {packet.status === 'executing' && (
          <>
            <button
              onClick={(e) => {
                e.stopPropagation()
                onControl(packet.packet_id, 'pause')
              }}
              className="text-[8px] text-warn hover:underline"
            >
              pause
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation()
                onControl(packet.packet_id, 'stop')
              }}
              className="text-[8px] text-danger hover:underline"
            >
              stop
            </button>
          </>
        )}
        {packet.status === 'paused' && (
          <button
            onClick={(e) => {
              e.stopPropagation()
              onControl(packet.packet_id, 'resume')
            }}
            className="text-[8px] text-ok hover:underline"
          >
            resume
          </button>
        )}
      </div>
    </div>
  )
}

// Execution overlay chip — per-Task attempt count / active phase / blocker /
// Proof, fed by the canonical /execution/overlay route. Additive: renders
// nothing until an attempt exists for the packet.
function ExecutionOverlayChip({ packetId }: { packetId: string }) {
  const overlay = useExecutionAttemptStore((s) => s.overlayByPacket[packetId])
  const fetchOverlay = useExecutionAttemptStore((s) => s.fetchOverlay)
  useEffect(() => { fetchOverlay([packetId]) }, [packetId, fetchOverlay])
  if (!overlay || overlay.attempt_count === 0) return null
  return (
    <span className="flex items-center gap-1 shrink-0" data-testid="w2-work-overlay" data-packet-id={packetId}>
      <span className="text-[9px] px-1 rounded bg-surface-raised text-text-tertiary font-mono">
        {overlay.attempt_count} att
      </span>
      {overlay.active_phase && (
        <span className="text-[9px] px-1 rounded bg-cyan/10 text-cyan font-mono">{overlay.active_phase}</span>
      )}
      {overlay.blocker_state && (
        <span className="text-[9px] px-1 rounded bg-red-400/10 text-red-400 font-mono">blocked</span>
      )}
      {overlay.proof_id && (
        <span className="text-[9px] px-1 rounded bg-green-400/10 text-green-400 font-mono">proof</span>
      )}
    </span>
  )
}

function OvernightSection({
  title,
  items,
  color,
  onApprove,
}: {
  title: string
  items: OvernightItem[]
  color: string
  onApprove?: (id: string) => void
}) {
  const colorClass =
    color === 'ok' ? 'text-ok' : color === 'warn' ? 'text-warn' : 'text-danger'
  return (
    <div className="border border-border rounded p-3">
      <div className="flex items-center gap-2 mb-2">
        <span className={`wv-label ${colorClass}`}>{title}</span>
        <span className="text-[10px] text-text-tertiary">{items.length}</span>
      </div>
      {items.length === 0 && <p className="text-[10px] text-text-tertiary">None</p>}
      {items.map((item) => (
        <div
          key={item.packet_id}
          className="flex items-center gap-2 py-1 text-[10px]"
        >
          <span className="text-text-primary flex-1 truncate">
            {item.title || item.packet_id}
          </span>
          <span className={`${RISK_COLOR[item.risk_class] || ''}`}>
            {item.risk_class}
          </span>
          {onApprove && (
            <button
              onClick={() => onApprove(item.packet_id)}
              className="px-2 py-1 bg-cyan-glow text-cyan border border-cyan/30 rounded text-[9px] hover:bg-cyan/20"
            >
              Approve
            </button>
          )}
        </div>
      ))}
    </div>
  )
}
