import { useEffect, useState } from 'react'
import {
  Brain,
  FileText,
  AlertCircle,
  Clock,
  Shield,
  Zap,
  RefreshCw,
  ChevronRight,
  ArrowLeft,
} from 'lucide-react'
import { useMemoryStore } from '../stores/memoryStore'

type Tab = 'decisions' | 'assumptions' | 'timeline' | 'validity' | 'impact'

const TABS: { id: Tab; label: string; icon: typeof Brain }[] = [
  { id: 'decisions', label: 'Decisions', icon: FileText },
  { id: 'assumptions', label: 'Assumptions', icon: AlertCircle },
  { id: 'timeline', label: 'Timeline', icon: Clock },
  { id: 'validity', label: 'Validity', icon: Shield },
  { id: 'impact', label: 'Impact', icon: Zap },
]

function Badge({ label, variant = 'default' }: { label: string; variant?: string }) {
  const colors: Record<string, string> = {
    active: 'bg-emerald-500/20 text-emerald-400',
    proposed: 'bg-blue-500/20 text-blue-400',
    superseded: 'bg-amber-500/20 text-amber-400',
    invalidated: 'bg-red-500/20 text-red-400',
    archived: 'bg-zinc-500/20 text-zinc-400',
    validated: 'bg-emerald-500/20 text-emerald-400',
    unknown: 'bg-zinc-500/20 text-zinc-400',
    valid: 'bg-emerald-500/20 text-emerald-400',
    watch: 'bg-amber-500/20 text-amber-400',
    at_risk: 'bg-orange-500/20 text-orange-400',
    invalid: 'bg-red-500/20 text-red-400',
    low: 'bg-emerald-500/20 text-emerald-400',
    medium: 'bg-amber-500/20 text-amber-400',
    high: 'bg-orange-500/20 text-orange-400',
    critical: 'bg-red-500/20 text-red-400',
    default: 'bg-zinc-500/20 text-zinc-400',
  }
  const cls = colors[variant] || colors[label] || colors.default
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {label}
    </span>
  )
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4 mb-3">
      <h3 className="text-sm font-semibold text-secondary mb-2">{title}</h3>
      {children}
    </div>
  )
}

// ── Decision Detail View ─────────────────────────────────────────────

function DecisionDetail({
  decisionId,
  onBack,
}: {
  decisionId: string
  onBack: () => void
}) {
  const { selectedDecision, lineage, validity, impact, fetchDecisionDetail, fetchLineage, fetchValidity, fetchImpact } = useMemoryStore()

  useEffect(() => {
    fetchDecisionDetail(decisionId)
    fetchLineage(decisionId)
    fetchValidity(decisionId)
    fetchImpact(decisionId)
  }, [decisionId])

  const d = selectedDecision
  if (!d) return <div className="p-4 text-secondary">Loading...</div>

  return (
    <div className="p-4 space-y-3 overflow-y-auto h-full">
      <button onClick={onBack} className="flex items-center gap-1 text-xs text-secondary hover:text-primary mb-2">
        <ArrowLeft size={14} /> Back to decisions
      </button>
      <h2 className="text-lg font-bold text-primary">{String(d.title || 'Untitled')}</h2>
      <div className="flex gap-2">
        <Badge label={String(d.status || 'unknown')} />
      </div>

      {d.summary && (
        <SectionCard title="Summary">
          <p className="text-sm text-secondary">{String(d.summary)}</p>
        </SectionCard>
      )}

      {d.rationale && (
        <SectionCard title="Rationale">
          <p className="text-sm text-secondary">{String(d.rationale)}</p>
        </SectionCard>
      )}

      {Array.isArray(d.alternatives_considered) && d.alternatives_considered.length > 0 && (
        <SectionCard title="Alternatives Considered">
          {(d.alternatives_considered as Record<string, unknown>[]).map((alt, i) => (
            <div key={i} className="text-sm text-secondary mb-1">
              <span className="text-primary font-medium">{String(alt.title || '')}</span>
              {alt.reason_rejected && <span className="text-zinc-500"> — {String(alt.reason_rejected)}</span>}
            </div>
          ))}
        </SectionCard>
      )}

      {lineage && (
        <SectionCard title="Lineage">
          <div className="text-sm text-secondary">
            <div className="mb-1">Upstream: {Array.isArray((lineage as Record<string, unknown>).upstream) ? ((lineage as Record<string, unknown>).upstream as unknown[]).length : 0} goals</div>
            <div>Downstream: {Array.isArray((lineage as Record<string, unknown>).downstream) ? ((lineage as Record<string, unknown>).downstream as unknown[]).length : 0} items</div>
          </div>
        </SectionCard>
      )}

      {validity && (
        <SectionCard title="Validity">
          <div className="flex items-center gap-2">
            <Badge label={String((validity as Record<string, unknown>).validity || 'unknown')} />
            <span className="text-xs text-secondary">
              Recommendation: {String((validity as Record<string, unknown>).recommendation || 'n/a')}
            </span>
          </div>
        </SectionCard>
      )}

      {impact && (
        <SectionCard title="Impact">
          <div className="text-sm text-secondary">
            <div>Blast radius: {String((impact as Record<string, unknown>).blast_radius || 0)}</div>
            <div className="flex items-center gap-2 mt-1">
              Risk: <Badge label={String((impact as Record<string, unknown>).risk_level || 'low')} />
            </div>
          </div>
        </SectionCard>
      )}

      {Array.isArray(d.goal_refs) && d.goal_refs.length > 0 && (
        <SectionCard title="Linked Goals">
          {(d.goal_refs as string[]).map((g, i) => (
            <div key={i} className="text-xs text-secondary font-mono">{g}</div>
          ))}
        </SectionCard>
      )}

      {Array.isArray(d.work_packet_refs) && d.work_packet_refs.length > 0 && (
        <SectionCard title="Linked Work Packets">
          {(d.work_packet_refs as string[]).map((w, i) => (
            <div key={i} className="text-xs text-secondary font-mono">{w}</div>
          ))}
        </SectionCard>
      )}
    </div>
  )
}

// ── Tab Components ───────────────────────────────────────────────────

function DecisionsTab() {
  const { decisions, fetchDecisions } = useMemoryStore()
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => { fetchDecisions() }, [])

  if (selectedId) {
    return <DecisionDetail decisionId={selectedId} onBack={() => setSelectedId(null)} />
  }

  if (!decisions.length) {
    return <div className="p-4 text-secondary text-sm">No strategic decisions recorded yet.</div>
  }

  return (
    <div className="p-4 space-y-2">
      {decisions.map((d, i) => (
        <button
          key={i}
          onClick={() => setSelectedId(String(d.decision_id || ''))}
          className="w-full text-left bg-surface border border-border rounded-lg p-3 hover:border-cyan-500/30 transition-colors"
        >
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-primary">{String(d.title || 'Untitled')}</span>
            <div className="flex items-center gap-2">
              <Badge label={String(d.status || 'unknown')} />
              <ChevronRight size={14} className="text-zinc-500" />
            </div>
          </div>
          {d.summary && (
            <p className="text-xs text-secondary mt-1 line-clamp-2">{String(d.summary)}</p>
          )}
        </button>
      ))}
    </div>
  )
}

function AssumptionsTab() {
  const { assumptions, invalidatedAssumptions, fetchAssumptions, fetchInvalidatedAssumptions } = useMemoryStore()

  useEffect(() => {
    fetchAssumptions()
    fetchInvalidatedAssumptions()
  }, [])

  return (
    <div className="p-4 space-y-3">
      {invalidatedAssumptions.length > 0 && (
        <SectionCard title={`Invalidated (${invalidatedAssumptions.length})`}>
          {invalidatedAssumptions.map((a, i) => (
            <div key={i} className="flex items-start gap-2 mb-2">
              <AlertCircle size={14} className="text-red-400 mt-0.5 shrink-0" />
              <div>
                <div className="text-sm text-primary">{String(a.statement || '')}</div>
                {Array.isArray(a.evidence_against) && (a.evidence_against as string[]).length > 0 && (
                  <div className="text-xs text-zinc-500 mt-0.5">
                    Evidence: {(a.evidence_against as string[]).join(', ')}
                  </div>
                )}
              </div>
            </div>
          ))}
        </SectionCard>
      )}

      <SectionCard title={`All Assumptions (${assumptions.length})`}>
        {assumptions.length === 0 ? (
          <p className="text-sm text-secondary">No assumptions tracked yet.</p>
        ) : (
          assumptions.map((a, i) => (
            <div key={i} className="flex items-center justify-between mb-2">
              <span className="text-sm text-secondary">{String(a.statement || '')}</span>
              <Badge label={String(a.status || 'unknown')} />
            </div>
          ))
        )}
      </SectionCard>
    </div>
  )
}

function TimelineTab() {
  const { timeline, fetchTimeline } = useMemoryStore()

  useEffect(() => { fetchTimeline() }, [])

  if (!timeline.length) {
    return <div className="p-4 text-secondary text-sm">No decision events yet.</div>
  }

  return (
    <div className="p-4">
      <div className="relative border-l border-border ml-2">
        {timeline.map((e, i) => (
          <div key={i} className="ml-4 mb-4 relative">
            <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-cyan-500 border-2 border-background" />
            <div className="text-xs text-zinc-500 mb-0.5">
              {new Date(Number(e.timestamp || 0) * 1000).toLocaleString()}
            </div>
            <div className="text-sm text-primary">
              {String(e.title || '')}
            </div>
            <div className="flex gap-2 mt-0.5">
              <Badge label={String(e.action || '')} />
              <Badge label={String(e.status || '')} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function ValidityTab() {
  const { health, fetchHealth, summary, fetchSummary } = useMemoryStore()

  useEffect(() => {
    fetchHealth()
    fetchSummary()
  }, [])

  const validitySummary = summary ? (summary as Record<string, unknown>).validity as Record<string, unknown> | undefined : undefined

  return (
    <div className="p-4 space-y-3">
      {health && (
        <SectionCard title="Decision Health">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="text-xs text-zinc-500">Overall</div>
              <Badge label={String((health as Record<string, unknown>).overall || 'unknown')} />
            </div>
            <div>
              <div className="text-xs text-zinc-500">Decisions</div>
              <div className="text-lg font-bold text-primary">{String((health as Record<string, unknown>).total_decisions || 0)}</div>
            </div>
            <div>
              <div className="text-xs text-zinc-500">At Risk</div>
              <div className="text-lg font-bold text-orange-400">{String((health as Record<string, unknown>).at_risk_decisions || 0)}</div>
            </div>
            <div>
              <div className="text-xs text-zinc-500">Invalid</div>
              <div className="text-lg font-bold text-red-400">{String((health as Record<string, unknown>).invalid_decisions || 0)}</div>
            </div>
          </div>
        </SectionCard>
      )}

      {validitySummary && Array.isArray((validitySummary as Record<string, unknown>).recommendations) && (
        <SectionCard title="Recommendations">
          {((validitySummary as Record<string, unknown>).recommendations as Record<string, unknown>[]).map((r, i) => (
            <div key={i} className="flex items-center justify-between mb-1">
              <span className="text-xs text-secondary font-mono">{String(r.decision_id || '')}</span>
              <Badge label={String(r.recommendation || '')} />
            </div>
          ))}
        </SectionCard>
      )}
    </div>
  )
}

function ImpactTab() {
  const { summary, fetchSummary } = useMemoryStore()

  useEffect(() => { fetchSummary() }, [])

  const impactSummary = summary ? (summary as Record<string, unknown>).impact as Record<string, unknown> | undefined : undefined

  return (
    <div className="p-4 space-y-3">
      {impactSummary ? (
        <>
          <SectionCard title="Impact Overview">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-xs text-zinc-500">Assessed</div>
                <div className="text-lg font-bold text-primary">{String(impactSummary.total_assessed || 0)}</div>
              </div>
              <div>
                <div className="text-xs text-zinc-500">High Impact</div>
                <div className="text-lg font-bold text-orange-400">{String(impactSummary.high_impact_count || 0)}</div>
              </div>
              <div className="col-span-2">
                <div className="text-xs text-zinc-500">Avg Blast Radius</div>
                <div className="text-lg font-bold text-primary">
                  {Number(impactSummary.average_blast_radius || 0).toFixed(1)}
                </div>
              </div>
            </div>
          </SectionCard>
        </>
      ) : (
        <div className="text-sm text-secondary">No impact data available.</div>
      )}
    </div>
  )
}

// ── Main Panel ───────────────────────────────────────────────────────

export function MemoryPanel() {
  const [activeTab, setActiveTab] = useState<Tab>('decisions')
  const { loading, fetchDecisions, fetchHealth } = useMemoryStore()

  const handleRefresh = () => {
    fetchDecisions()
    fetchHealth()
  }

  const renderTab = () => {
    switch (activeTab) {
      case 'decisions': return <DecisionsTab />
      case 'assumptions': return <AssumptionsTab />
      case 'timeline': return <TimelineTab />
      case 'validity': return <ValidityTab />
      case 'impact': return <ImpactTab />
      default: return null
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border">
        <div className="flex items-center gap-2">
          <Brain size={16} className="text-cyan-400" />
          <h2 className="text-sm font-semibold text-primary">Strategic Memory</h2>
        </div>
        <button
          onClick={handleRefresh}
          className="p-1.5 rounded hover:bg-surface transition-colors"
          title="Refresh"
        >
          <RefreshCw size={14} className={`text-secondary ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="flex border-b border-border">
        {TABS.map((tab) => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors ${
                activeTab === tab.id
                  ? 'text-cyan-400 border-b-2 border-cyan-400'
                  : 'text-secondary hover:text-primary'
              }`}
            >
              <Icon size={13} />
              {tab.label}
            </button>
          )
        })}
      </div>

      <div className="flex-1 overflow-y-auto">
        {renderTab()}
      </div>
    </div>
  )
}
