// Work Detail panel — MVP Wave 1. The contextual Plan/Task inspection surface,
// reached from Cockpit Chat and from the Work kanban's "Open Plan" buttons —
// NEVER from the Top HUD. It refactors the earlier ObjectivePlanPanel: a full
// read surface over the server's versioned objective-plan records
// (chat-originated, governed).
//
// DOCTRINE (mirrors IntentLoopPanel): plans originate ONLY on the server-side
// planning rail via Cockpit Chat. This panel has NO plan-authoring input. It is
// a downstream control surface: it lists plans (GET /objective-plan), shows the
// full detail of a selected plan (GET /objective-plan/{id}) including every
// version (GET .../versions), renders the work-graph via the shared GraphView
// (superseded/removed nodes GHOSTED, never hidden), lets the operator inspect a
// node in a drawer, and cancel (through objectivePlanStore.decide('cancel'),
// which routes through the SERVER's governed runtime and re-reads server truth).
// Approve/reject are HUD-only — this panel never carries decision buttons and
// never advances state itself.
import { useEffect, useState } from 'react'
import {
  Workflow, RefreshCw, Clock, ShieldCheck, Ban, X,
} from 'lucide-react'
import { usePolling } from '../hooks/usePolling'
import { GraphView } from '../components/GraphView'
import { useRealtimeStore } from '../stores/realtimeStore'
import {
  useObjectivePlanStore,
  type PlanSummary,
  type PlanDetail,
  type PlanNode,
} from '../stores/objectivePlanStore'

// Node color by kind + status. Ghost color for superseded/removed so a dropped
// packet stays VISIBLE (never hidden) but reads as inactive.
const GHOST = 'var(--color-text-tertiary)'
function nodeColor(node: PlanNode): string {
  const s = (node.status || '').toLowerCase()
  if (s === 'superseded' || s === 'removed') return GHOST
  switch (node.kind) {
    case 'packet': return 'var(--color-cyan)'
    case 'decision_gate': return 'var(--color-warn)'
    case 'verification': return 'var(--color-ok)'
    case 'milestone': return '#a78bfa'
    default: return 'var(--color-cyan)'
  }
}

const LANE_LEGEND: Array<{ kind: string; label: string; color: string }> = [
  { kind: 'packet', label: 'Task', color: 'var(--color-cyan)' },
  { kind: 'decision_gate', label: 'Decision gate', color: 'var(--color-warn)' },
  { kind: 'verification', label: 'Verification', color: 'var(--color-ok)' },
  { kind: 'milestone', label: 'Milestone', color: '#a78bfa' },
  { kind: 'ghost', label: 'Superseded', color: GHOST },
]

function statusColor(status: string): string {
  switch ((status || '').toLowerCase()) {
    case 'awaiting_approval': return 'bg-yellow-400/10 text-yellow-400'
    case 'approved': return 'bg-green-400/10 text-green-400'
    case 'rejected':
    case 'cancelled':
    case 'failed': return 'bg-red-400/10 text-red-400'
    case 'clarification_required': return 'bg-cyan/10 text-cyan'
    case 'superseded': return 'bg-text-tertiary/10 text-text-tertiary'
    default: return 'bg-text-tertiary/10 text-text-tertiary'
  }
}

function PlanListRow({
  plan, selected, onSelect,
}: { plan: PlanSummary; selected: boolean; onSelect: () => void }) {
  return (
    <button
      onClick={onSelect}
      className={`w-full text-left bg-surface-raised border rounded p-2 transition-colors ${
        selected ? 'border-cyan' : 'border-border hover:border-cyan/40'
      }`}
    >
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[10px] font-mono text-text-primary truncate flex-1">
          {plan.objective_text || plan.objective_id}
        </span>
        <span className={`text-[8px] font-mono px-1.5 py-0.5 rounded uppercase ${statusColor(plan.status)}`}>
          {plan.status.replace(/_/g, ' ')}
        </span>
      </div>
      <div className="flex items-center gap-2 text-[8px] font-mono text-text-tertiary">
        <span>v{plan.graph_version}</span>
        <span>{plan.packet_count} tasks</span>
        <span className="truncate">{plan.plan_record_id}</span>
      </div>
    </button>
  )
}

function NodeDrawer({
  node, plan, onClose,
}: { node: PlanNode; plan: PlanDetail; onClose: () => void }) {
  const packet = plan.packets.find((p) => p.packet_id === node.workpacket_id)
  return (
    <div className="absolute inset-y-0 right-0 w-72 bg-surface border-l border-border shadow-lg z-10 flex flex-col">
      <div className="flex items-center justify-between px-3 h-9 border-b border-border shrink-0">
        <span className="text-[10px] font-mono uppercase text-cyan truncate">{node.title}</span>
        <button onClick={onClose} className="text-text-tertiary hover:text-text-primary">
          <X size={14} />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-2 text-[10px] font-mono">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="px-1.5 py-0.5 rounded bg-surface-raised text-text-tertiary">{node.kind}</span>
          <span className={`px-1.5 py-0.5 rounded ${statusColor(node.status)}`}>{node.status}</span>
          <span className="px-1.5 py-0.5 rounded bg-surface-raised text-text-tertiary">lane: {node.lane}</span>
        </div>
        {node.depends_on.length > 0 && (
          <div>
            <div className="text-text-tertiary uppercase text-[8px] mb-0.5">depends on</div>
            {node.depends_on.map((d) => (
              <div key={d} className="text-text-secondary truncate">{d}</div>
            ))}
          </div>
        )}
        {packet && (
          <>
            <div>
              <div className="text-text-tertiary uppercase text-[8px] mb-0.5">task</div>
              <div className="text-text-primary">{packet.title || packet.user_intent || packet.packet_id}</div>
              <div className="flex gap-2 mt-1 text-text-tertiary">
                <span>risk: {packet.risk_class}</span>
                <span>{packet.status}</span>
              </div>
            </div>
            {packet.current_state && (
              <div>
                <div className="text-text-tertiary uppercase text-[8px] mb-0.5">current state</div>
                <div className="text-text-secondary whitespace-pre-wrap">{packet.current_state}</div>
              </div>
            )}
            {packet.desired_state && (
              <div>
                <div className="text-text-tertiary uppercase text-[8px] mb-0.5">desired state</div>
                <div className="text-text-secondary whitespace-pre-wrap">{packet.desired_state}</div>
              </div>
            )}
            {packet.success_criteria && packet.success_criteria.length > 0 && (
              <div>
                <div className="text-text-tertiary uppercase text-[8px] mb-0.5">success criteria</div>
                <ul className="list-disc list-inside text-text-secondary">
                  {packet.success_criteria.map((c, i) => <li key={i}>{c}</li>)}
                </ul>
              </div>
            )}
          </>
        )}
        {node.evidence_refs.length > 0 && (
          <div>
            <div className="text-text-tertiary uppercase text-[8px] mb-0.5">evidence refs</div>
            {node.evidence_refs.map((e, i) => (
              <div key={i} className="text-text-secondary truncate">{e}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Plan-context definition lists (Wave 1 first-class typed context) ─────────
//
// Scope, planning scale, decomposition, archetype policy, development profile,
// and readiness — surfaced as plain definition lists, never hidden in evidence
// blobs. Reuses the file's existing tailwind conventions.

function DefRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-2">
      <span className="text-text-tertiary uppercase text-[8px] w-28 shrink-0 pt-0.5">{label}</span>
      <span className="text-text-secondary flex-1 min-w-0 break-words">{children}</span>
    </div>
  )
}

function PlanContextSections({ plan }: { plan: PlanDetail }) {
  const scope = plan.work_scope
  const decomp = plan.decomposition
  const arch = plan.archetype_resolution
  const dev = plan.development_profile
  const readinessState = plan.readiness_assessment?.state
  const deferredCount = decomp?.deferred_child_objectives?.length ?? 0

  // Required development layers = layers whose assessment status marks work
  // still owed (required / existing_but_deficient / missing artifacts).
  const layers = dev?.layer_assessments ?? []
  const requiredLayers = layers.filter((l) =>
    ['required', 'existing_but_deficient', 'blocked'].includes((l.status || '').toLowerCase()),
  )
  const missingArtifacts = dev?.missing_required_artifacts ?? []

  const hasScope = !!(scope && (scope.tenant_id || scope.target_kind))
  const hasArch = !!(arch && (arch.archetype_id || arch.default_role_contract_id))
  const hasDev = !!(dev && (layers.length > 0 || missingArtifacts.length > 0))
  const hasCurrentDesiredIds = !!(plan.current_state_id || plan.desired_state_id)

  if (!hasScope && !plan.planning_scale && !decomp && !hasArch && !hasDev
      && !readinessState && !hasCurrentDesiredIds) {
    return null
  }

  return (
    <section data-testid="wg-work-detail-context" className="space-y-3">
      {(hasScope || plan.planning_scale) && (
        <div>
          <div className="text-[9px] font-mono uppercase tracking-wider text-cyan mb-1">
            Work scope
          </div>
          <div className="space-y-1 text-[10px] font-mono">
            {scope?.tenant_id && <DefRow label="tenant">{scope.tenant_id}</DefRow>}
            {scope?.target_kind && <DefRow label="target kind">{scope.target_kind}</DefRow>}
            {plan.planning_scale && <DefRow label="planning scale">{plan.planning_scale}</DefRow>}
          </div>
        </div>
      )}

      {decomp && (decomp.stop_reason || deferredCount > 0 || (decomp.decomposition_frontier?.length ?? 0) > 0) && (
        <div>
          <div className="text-[9px] font-mono uppercase tracking-wider text-cyan mb-1">
            Decomposition
          </div>
          <div className="space-y-1 text-[10px] font-mono">
            {decomp.stop_reason && <DefRow label="stop reason">{decomp.stop_reason}</DefRow>}
            <DefRow label="deferred">
              {deferredCount} child objective{deferredCount === 1 ? '' : 's'}
            </DefRow>
            {typeof decomp.decomposition_depth === 'number' && (
              <DefRow label="depth">{decomp.decomposition_depth}</DefRow>
            )}
          </div>
        </div>
      )}

      {hasArch && (
        <div>
          <div className="text-[9px] font-mono uppercase tracking-wider text-cyan mb-1">
            Archetype resolution
          </div>
          <div className="space-y-1 text-[10px] font-mono">
            {arch?.archetype_id && (
              <DefRow label="archetype">
                {arch.archetype_id}
                {typeof arch.archetype_version === 'number' ? ` v${arch.archetype_version}` : ''}
              </DefRow>
            )}
            {arch?.default_role_contract_id && (
              <DefRow label="default role">{arch.default_role_contract_id}</DefRow>
            )}
            {arch?.required_skill_refs && arch.required_skill_refs.length > 0 && (
              <DefRow label="required skills">
                <ul className="list-disc list-inside">
                  {arch.required_skill_refs.map((r, i) => (
                    <li key={i} className="truncate">
                      {String(r.skill_ref ?? r.skill_id ?? r.ref ?? JSON.stringify(r))}
                    </li>
                  ))}
                </ul>
              </DefRow>
            )}
          </div>
        </div>
      )}

      {hasDev && (
        <div>
          <div className="text-[9px] font-mono uppercase tracking-wider text-cyan mb-1">
            Development profile
          </div>
          <div className="space-y-1 text-[10px] font-mono">
            {dev?.target_kind && <DefRow label="target kind">{dev.target_kind}</DefRow>}
            <DefRow label="required layers">
              {requiredLayers.length} of {layers.length}
            </DefRow>
            {missingArtifacts.length > 0 && (
              <DefRow label="missing artifacts">{missingArtifacts.length}</DefRow>
            )}
          </div>
        </div>
      )}

      {(readinessState || hasCurrentDesiredIds) && (
        <div>
          <div className="text-[9px] font-mono uppercase tracking-wider text-cyan mb-1">
            Readiness
          </div>
          <div className="space-y-1 text-[10px] font-mono">
            {readinessState && (
              <DefRow label="state">
                <span className={`px-1.5 py-0.5 rounded ${statusColor(readinessState)}`}>
                  {readinessState.replace(/_/g, ' ')}
                </span>
              </DefRow>
            )}
            {plan.current_state_id && (
              <DefRow label="current state id">{plan.current_state_id}</DefRow>
            )}
            {plan.desired_state_id && (
              <DefRow label="desired state id">{plan.desired_state_id}</DefRow>
            )}
          </div>
        </div>
      )}
    </section>
  )
}

function PlanDetailView({ plan }: { plan: PlanDetail }) {
  const decide = useObjectivePlanStore((s) => s.decide)
  const decidingPlanId = useObjectivePlanStore((s) => s.decidingPlanId)
  const fetchVersions = useObjectivePlanStore((s) => s.fetchVersions)
  const fetchPlan = useObjectivePlanStore((s) => s.fetchPlan)
  const selectPlan = useObjectivePlanStore((s) => s.selectPlan)
  const versionsByObjective = useObjectivePlanStore((s) => s.versionsByObjective)
  const [selectedNode, setSelectedNode] = useState<PlanNode | null>(null)
  const [decisionError, setDecisionError] = useState<string | null>(null)

  useEffect(() => {
    fetchVersions(plan.plan_record_id)
  }, [plan.plan_record_id, fetchVersions])

  const versions = versionsByObjective[plan.objective_id] ?? []
  const deciding = decidingPlanId === plan.plan_record_id
  const isSuperseded = plan.status === 'superseded'
  const held = plan.status === 'awaiting_approval'
  // Cancel is available while awaiting approval OR approved (execution not started).
  const canCancel = plan.status === 'awaiting_approval' || plan.status === 'approved'

  const nodes = plan.nodes.map((n) => ({ id: n.node_id, label: n.title, type: n.kind, status: n.status }))
  const edges = plan.edges.map((e) => ({ source: e.from, target: e.to, type: e.type ?? '' }))
  const colorMap: Record<string, string> = {}
  for (const n of plan.nodes) colorMap[n.kind] = nodeColor(n)
  const laneById = new Map(plan.nodes.map((n) => [n.node_id, n.lane]))

  // Only 'cancel' is issued from the panel; approve/reject route through the
  // Top-HUD unified-approval strip (see ControlPanel.tsx).
  const onDecide = async (decision: 'cancel') => {
    setDecisionError(null)
    const result = await decide(plan.plan_record_id, decision, undefined, plan.graph_version)
    if (!result.ok) {
      setDecisionError(
        result.conflict
          ? 'Plan version changed on the server — refresh and retry.'
          : result.error || 'Decision failed.',
      )
    }
  }

  return (
    <div className="relative flex flex-col h-full overflow-hidden">
      {/* Version selector + status */}
      <div className="flex items-center gap-2 flex-wrap px-4 py-2 border-b border-border shrink-0">
        <span className={`text-[9px] font-mono px-2 py-0.5 rounded uppercase ${statusColor(plan.status)}`}>
          {plan.status.replace(/_/g, ' ')}
        </span>
        {isSuperseded && (
          <span className="text-[8px] font-mono text-text-tertiary italic">read-only (superseded)</span>
        )}
        <div className="flex items-center gap-1 ml-auto">
          <span className="text-[8px] font-mono text-text-tertiary uppercase">version</span>
          {versions.length > 0 ? (
            versions.map((v) => (
              <button
                key={v.plan_record_id}
                onClick={() => { selectPlan(v.plan_record_id); fetchPlan(v.plan_record_id) }}
                className={`text-[9px] font-mono px-1.5 py-0.5 rounded border transition-colors ${
                  v.plan_record_id === plan.plan_record_id
                    ? 'border-cyan text-cyan'
                    : v.status === 'superseded'
                      ? 'border-border text-text-tertiary opacity-50 hover:opacity-80'
                      : 'border-border text-text-secondary hover:border-cyan/40'
                }`}
                title={v.status === 'superseded' ? 'superseded — read-only' : v.status}
              >
                v{v.graph_version}
              </button>
            ))
          ) : (
            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded border border-cyan text-cyan">
              v{plan.graph_version}
            </span>
          )}
        </div>
      </div>

      {/* Lane legend */}
      <div className="flex items-center gap-3 flex-wrap px-4 py-1.5 border-b border-border shrink-0 text-[8px] font-mono text-text-tertiary">
        {plan.lanes.length > 0 && (
          <span className="uppercase">lanes: {plan.lanes.join(' · ')}</span>
        )}
        <span className="flex items-center gap-2">
          {LANE_LEGEND.map((l) => (
            <span key={l.kind} className="flex items-center gap-1">
              <span className="inline-block w-2 h-2 rounded-full" style={{ background: l.color }} />
              {l.label}
            </span>
          ))}
        </span>
      </div>

      {/* Graph */}
      <div className="relative h-56 border-b border-border shrink-0">
        {nodes.length > 0 ? (
          <GraphView
            nodes={nodes}
            edges={edges}
            colorMap={colorMap}
            laneOf={(n) => laneById.get(n.id) ?? ''}
            onNodeClick={(n) => {
              const full = plan.nodes.find((pn) => pn.node_id === n.id)
              if (full) setSelectedNode(full)
            }}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-[10px] font-mono text-text-tertiary">
            No graph nodes
          </div>
        )}
      </div>

      {/* Decision controls — OWNER DESIGN: approve/reject for an objective plan
          live in the Top-HUD ControlPanel unified-approval strip, NOT here. The
          panel shows read-only status and keeps ONLY the Cancel control (cancel
          is a plan-owner action on the plan record, distinct from the unified
          approval gate). While awaiting approval the panel points the operator
          to the Top HUD. */}
      <div className="flex items-center gap-2 flex-wrap px-4 py-2 border-b border-border shrink-0">
        {held && (
          <span className="flex items-center gap-1 text-[9px] font-mono text-yellow-400">
            <Clock size={10} /> awaiting approval — approve or reject in the Top HUD approvals strip
          </span>
        )}
        {canCancel && (
          <button
            data-testid="wg-cancel-btn"
            onClick={() => onDecide('cancel')}
            disabled={deciding}
            className="flex items-center gap-1 px-2 py-0.5 text-[9px] font-mono uppercase bg-text-tertiary/10 text-text-tertiary border border-border rounded hover:bg-text-tertiary/20 disabled:opacity-50"
          >
            <Ban size={10} /> Cancel
          </button>
        )}
        {plan.status === 'approved' && (
          <span className="flex items-center gap-1 text-[9px] font-mono text-green-400">
            <ShieldCheck size={10} /> PLAN APPROVED — EXECUTION NOT STARTED
          </span>
        )}
        {plan.status === 'rejected' && (
          <span className="text-[9px] font-mono text-red-400">Plan rejected.</span>
        )}
        {plan.status === 'cancelled' && (
          <span className="text-[9px] font-mono text-red-400">Plan cancelled.</span>
        )}
        {decisionError && (
          <span className="text-[9px] font-mono text-red-400">{decisionError}</span>
        )}
      </div>

      {/* State sections + gap model + first-class plan context */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 text-[10px]">
        <PlanContextSections plan={plan} />

        <section>
          <div className="text-[9px] font-mono uppercase tracking-wider text-cyan mb-1">
            Current state (evidence)
          </div>
          {plan.current_state && plan.current_state.statements.length > 0 ? (
            <ul className="space-y-1">
              {plan.current_state.statements.map((s, i) => (
                <li key={i} className="text-text-secondary">
                  {s.statement}
                  {s.evidence_refs && s.evidence_refs.length > 0 && (
                    <span className="text-text-tertiary"> [{s.evidence_refs.length} evidence]</span>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-text-tertiary font-mono">No current-state statements.</p>
          )}
          {plan.current_state && plan.current_state.unknowns.length > 0 && (
            <p className="text-text-tertiary mt-1">Unknowns: {plan.current_state.unknowns.join('; ')}</p>
          )}
        </section>

        <section>
          <div className="text-[9px] font-mono uppercase tracking-wider text-cyan mb-1">
            Desired state (requested)
          </div>
          {plan.desired_state && plan.desired_state.statements.length > 0 ? (
            <ul className="space-y-1">
              {plan.desired_state.statements.map((s, i) => (
                <li key={i} className="text-text-secondary">
                  {s.statement}
                  {s.acceptance_criteria && s.acceptance_criteria.length > 0 && (
                    <ul className="list-disc list-inside text-text-tertiary ml-2">
                      {s.acceptance_criteria.map((c, j) => <li key={j}>{c}</li>)}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-text-tertiary font-mono">No desired-state statements.</p>
          )}
          {plan.desired_state && plan.desired_state.constraints.length > 0 && (
            <p className="text-warn mt-1">Constraints: {plan.desired_state.constraints.join('; ')}</p>
          )}
        </section>

        {plan.gap_model && (
          <section>
            <div className="text-[9px] font-mono uppercase tracking-wider text-cyan mb-1">
              Gap model
            </div>
            {plan.gap_model.gaps.length > 0 && (
              <div className="mb-1">
                <div className="text-text-tertiary uppercase text-[8px] mb-0.5">gaps</div>
                <ul className="space-y-0.5">
                  {plan.gap_model.gaps.map((g) => (
                    <li key={g.gap_id} className="text-text-secondary">
                      <span className={`text-[8px] font-mono px-1 rounded mr-1 ${statusColor(g.severity)}`}>{g.severity}</span>
                      {g.description}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {plan.gap_model.assumptions.length > 0 && (
              <GapList label="assumptions" items={plan.gap_model.assumptions} />
            )}
            {plan.gap_model.contradictions.length > 0 && (
              <GapList label="contradictions" items={plan.gap_model.contradictions} tone="text-danger" />
            )}
            {plan.gap_model.unknowns.length > 0 && (
              <GapList label="unknowns" items={plan.gap_model.unknowns} />
            )}
            {plan.gap_model.owner_decisions.length > 0 && (
              <div className="mb-1">
                <div className="text-text-tertiary uppercase text-[8px] mb-0.5">owner decisions</div>
                <ul className="space-y-0.5">
                  {plan.gap_model.owner_decisions.map((d, i) => (
                    <li key={i} className="text-text-secondary">
                      {d.question}
                      {d.why_material && <span className="text-text-tertiary"> — {d.why_material}</span>}
                      {d.dimension && (
                        <span className="ml-1 text-[8px] font-mono px-1 rounded bg-surface-raised text-text-tertiary">{d.dimension}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}

        {plan.decision_log.length > 0 && (
          <section>
            <div className="text-[9px] font-mono uppercase tracking-wider text-cyan mb-1">Decision log</div>
            <ul className="space-y-0.5">
              {plan.decision_log.map((d, i) => (
                <li key={i} className="text-text-secondary font-mono text-[9px]">
                  {d.decision} · {d.decided_by} ·{' '}
                  {d.decided_at != null
                    ? new Date(Number(d.decided_at) * 1000).toLocaleString()
                    : (d.at ?? '')}
                  {d.reason && <span className="text-text-tertiary"> — {d.reason}</span>}
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>

      {selectedNode && (
        <NodeDrawer node={selectedNode} plan={plan} onClose={() => setSelectedNode(null)} />
      )}
    </div>
  )
}

function GapList({ label, items, tone = 'text-text-secondary' }: { label: string; items: string[]; tone?: string }) {
  return (
    <div className="mb-1">
      <div className="text-text-tertiary uppercase text-[8px] mb-0.5">{label}</div>
      <ul className="space-y-0.5">
        {items.map((it, i) => <li key={i} className={tone}>{it}</li>)}
      </ul>
    </div>
  )
}

export function WorkDetailPanel() {
  const realtimeStatus = useRealtimeStore((s) => s.status)
  const plans = useObjectivePlanStore((s) => s.plans)
  const loading = useObjectivePlanStore((s) => s.loading)
  const error = useObjectivePlanStore((s) => s.error)
  const selectedPlanId = useObjectivePlanStore((s) => s.selectedPlanId)
  const planById = useObjectivePlanStore((s) => s.planById)
  const fetchSurface = useObjectivePlanStore((s) => s.fetchSurface)
  const fetchPlan = useObjectivePlanStore((s) => s.fetchPlan)
  const selectPlan = useObjectivePlanStore((s) => s.selectPlan)

  usePolling(
    () => { fetchSurface() },
    realtimeStatus === 'connected' ? 15000 : 5000,
  )

  // Warm the detail cache when a plan is selected but not yet fetched.
  useEffect(() => {
    if (selectedPlanId && !planById[selectedPlanId]) {
      fetchPlan(selectedPlanId)
    }
  }, [selectedPlanId, planById, fetchPlan])

  const selectedPlan = selectedPlanId ? planById[selectedPlanId] : null

  return (
    <div data-testid="wg-work-detail" className="flex flex-col h-full overflow-hidden">
      <div data-testid="wg-objective-plan-panel" className="flex flex-col h-full overflow-hidden">
        <div className="flex items-center justify-between border-b border-border px-4 h-9 shrink-0">
          <div className="flex items-center gap-2">
            <Workflow size={14} className="text-cyan" />
            <span className="text-[10px] font-mono text-cyan uppercase tracking-wider">Plan Detail</span>
            <span className="text-[9px] text-text-tertiary">chat objective → grounded gap model → governed work-graph</span>
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

        <div className="flex flex-1 overflow-hidden">
          {/* Plan list */}
          <div className="w-64 border-r border-border overflow-y-auto p-3 space-y-2 shrink-0">
            {loading && plans.length === 0 && (
              <div className="text-text-tertiary text-xs font-mono">Loading plans...</div>
            )}
            {error && <div className="text-red-400 text-xs font-mono">{error}</div>}
            {plans.map((p) => (
              <PlanListRow
                key={p.plan_record_id}
                plan={p}
                selected={p.plan_record_id === selectedPlanId}
                onSelect={() => { selectPlan(p.plan_record_id); fetchPlan(p.plan_record_id) }}
              />
            ))}
            {!loading && plans.length === 0 && !error && (
              <div className="flex items-center gap-2 text-text-tertiary text-xs font-mono">
                <Clock size={14} />
                No plans yet — state an objective in Cockpit Chat
              </div>
            )}
          </div>

          {/* Detail */}
          <div className="flex-1 overflow-hidden">
            {selectedPlan ? (
              <PlanDetailView plan={selectedPlan} />
            ) : (
              <div className="flex items-center justify-center h-full text-[11px] font-mono text-text-tertiary">
                Select a plan to inspect its work-graph
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
