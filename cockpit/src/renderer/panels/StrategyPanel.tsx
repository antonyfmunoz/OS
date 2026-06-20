import { useEffect, useState, useCallback } from 'react'
import {
  Target,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ChevronRight,
  Plus,
  Play,
  Eye,
  ThumbsUp,
  ThumbsDown,
  History,
  RefreshCw,
  Zap,
} from 'lucide-react'
import { useCollapseStore } from '../stores/collapseStore'
import { useOperatorLoopStore } from '../stores/operatorLoopStore'
import type { GoalData, GapData, RecommendationData, DecisionData } from '../stores/operatorLoopStore'

type Tab = 'overview' | 'goals' | 'gaps' | 'recommendations' | 'decisions'

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'text-red-400 bg-red-400/10 border-red-400/30',
  high: 'text-orange-400 bg-orange-400/10 border-orange-400/30',
  medium: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30',
  low: 'text-text-tertiary bg-surface-raised border-border',
}

const STATUS_COLORS: Record<string, string> = {
  active: 'text-cyan bg-cyan/10',
  completed: 'text-green-400 bg-green-400/10',
  paused: 'text-yellow-400 bg-yellow-400/10',
  abandoned: 'text-text-tertiary bg-surface-raised',
}

export function StrategyPanel() {
  const [tab, setTab] = useState<Tab>('overview')
  const [showAddGoal, setShowAddGoal] = useState(false)

  const {
    goals, gaps, recommendations, decisions, lastAnalysis,
    strategyLoading, runAnalysis, fetchGoals, fetchRecommendations,
    fetchDecisions, approveRecommendation, rejectRecommendation,
  } = useOperatorLoopStore()

  useEffect(() => {
    fetchGoals()
    fetchRecommendations()
    fetchDecisions()
  }, [])

  const handleAnalyze = useCallback(async () => {
    await runAnalysis()
  }, [runAnalysis])

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 h-9 shrink-0">
        <div className="flex items-center gap-2">
          <Target size={14} className="text-cyan" />
          <span className="text-[10px] font-mono text-cyan uppercase tracking-wider">Strategic Gap Engine</span>
        </div>
        <button
          onClick={handleAnalyze}
          disabled={strategyLoading}
          className="flex items-center gap-1 px-2 py-1 text-[10px] font-mono uppercase bg-cyan/10 text-cyan border border-cyan/30 rounded hover:bg-cyan/20 disabled:opacity-50"
        >
          {strategyLoading ? <RefreshCw size={10} className="animate-spin" /> : <Play size={10} />}
          {strategyLoading ? 'Analyzing...' : 'Run Analysis'}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border shrink-0">
        {(['overview', 'goals', 'gaps', 'recommendations', 'decisions'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-[10px] font-mono uppercase transition-colors ${
              tab === t ? 'text-cyan border-b-2 border-cyan' : 'text-text-tertiary hover:text-text-secondary'
            }`}
          >
            {t}
            {t === 'gaps' && gaps.length > 0 && (
              <span className="ml-1 px-1 bg-orange-400/20 text-orange-400 rounded text-[9px]">{gaps.length}</span>
            )}
            {t === 'recommendations' && recommendations.filter((r) => r.status === 'pending').length > 0 && (
              <span className="ml-1 px-1 bg-cyan/20 text-cyan rounded text-[9px]">
                {recommendations.filter((r) => r.status === 'pending').length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {tab === 'overview' && <OverviewTab goals={goals} gaps={gaps} recommendations={recommendations} decisions={decisions} lastAnalysis={lastAnalysis} />}
        {tab === 'goals' && <GoalsTab goals={goals} showAddGoal={showAddGoal} setShowAddGoal={setShowAddGoal} />}
        {tab === 'gaps' && <GapsTab gaps={gaps} />}
        {tab === 'recommendations' && (
          <RecommendationsTab
            recommendations={recommendations}
            onApprove={approveRecommendation}
            onReject={rejectRecommendation}
          />
        )}
        {tab === 'decisions' && <DecisionsTab decisions={decisions} />}
      </div>
    </div>
  )
}

/* ── Overview Tab ───────────────────────────────────────────────── */

function OverviewTab({
  goals, gaps, recommendations, decisions, lastAnalysis,
}: {
  goals: GoalData[]
  gaps: GapData[]
  recommendations: RecommendationData[]
  decisions: DecisionData[]
  lastAnalysis: ReturnType<typeof useOperatorLoopStore.getState>['lastAnalysis']
}) {
  const activeGoals = goals.filter((g) => g.status === 'active')
  const criticalGaps = gaps.filter((g) => g.severity === 'critical')
  const pendingRecs = recommendations.filter((r) => r.status === 'pending')
  const effectiveDecisions = decisions.filter((d) => d.was_effective === true)

  return (
    <div className="space-y-4">
      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-3">
        <KpiCard label="Active Goals" value={activeGoals.length} icon={Target} color="text-cyan" />
        <KpiCard label="Open Gaps" value={gaps.length} icon={AlertTriangle} color="text-orange-400" />
        <KpiCard label="Pending Actions" value={pendingRecs.length} icon={Zap} color="text-yellow-400" />
        <KpiCard label="Effective Decisions" value={effectiveDecisions.length} icon={CheckCircle2} color="text-green-400" />
      </div>

      {/* Top Recommendation */}
      {lastAnalysis?.top_recommendation && (
        <div className="border border-cyan/30 bg-cyan/5 rounded p-3">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp size={12} className="text-cyan" />
            <span className="text-[10px] font-mono text-cyan uppercase">Top Recommendation</span>
          </div>
          <p className="text-xs text-text-primary">{lastAnalysis.top_recommendation.title}</p>
          <p className="text-[10px] text-text-secondary mt-1">{lastAnalysis.top_recommendation.rationale}</p>
          <div className="flex items-center gap-3 mt-2 text-[9px] text-text-tertiary font-mono uppercase">
            <span>Impact: {lastAnalysis.top_recommendation.impact_estimate}</span>
            <span>Risk: {lastAnalysis.top_recommendation.risk_estimate}</span>
            <span>Domain: {lastAnalysis.top_recommendation.suggested_domain}</span>
          </div>
        </div>
      )}

      {/* Critical Gaps */}
      {criticalGaps.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={12} className="text-red-400" />
            <span className="text-[10px] font-mono text-red-400 uppercase">Critical Gaps</span>
          </div>
          <div className="space-y-2">
            {criticalGaps.map((gap) => (
              <GapCard key={gap.gap_id} gap={gap} />
            ))}
          </div>
        </div>
      )}

      {/* Recent Reality */}
      {lastAnalysis?.reality && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Eye size={12} className="text-text-secondary" />
            <span className="text-[10px] font-mono text-text-secondary uppercase">Current Reality</span>
          </div>
          <div className="grid grid-cols-3 gap-2 text-[10px]">
            <div className="border border-border rounded p-2">
              <div className="text-text-tertiary font-mono uppercase mb-1">Active Domains</div>
              <div className="text-text-primary">{lastAnalysis.reality.active_domains.join(', ') || 'None'}</div>
            </div>
            <div className="border border-border rounded p-2">
              <div className="text-text-tertiary font-mono uppercase mb-1">Open Approvals</div>
              <div className="text-text-primary">{lastAnalysis.reality.open_approvals}</div>
            </div>
            <div className="border border-border rounded p-2">
              <div className="text-text-tertiary font-mono uppercase mb-1">Blocked Items</div>
              <div className="text-text-primary">{lastAnalysis.reality.blocked_items.length}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function KpiCard({ label, value, icon: Icon, color }: { label: string; value: number; icon: typeof Target; color: string }) {
  return (
    <div className="border border-border rounded p-3 flex items-center gap-3">
      <Icon size={16} className={color} />
      <div>
        <div className="text-lg font-mono text-text-primary">{value}</div>
        <div className="text-[9px] font-mono text-text-tertiary uppercase">{label}</div>
      </div>
    </div>
  )
}

/* ── Goals Tab ──────────────────────────────────────────────────── */

function GoalsTab({
  goals, showAddGoal, setShowAddGoal,
}: {
  goals: GoalData[]
  showAddGoal: boolean
  setShowAddGoal: (v: boolean) => void
}) {
  const addGoal = useOperatorLoopStore((s) => s.addGoal)
  const deleteGoal = useOperatorLoopStore((s) => s.deleteGoal)

  const [newTitle, setNewTitle] = useState('')
  const [newDomain, setNewDomain] = useState('')
  const [newType, setNewType] = useState('goal')
  const [newPriority, setNewPriority] = useState(50)
  const [newDescription, setNewDescription] = useState('')

  const handleAdd = async () => {
    if (!newTitle.trim()) return
    await addGoal({
      title: newTitle,
      description: newDescription,
      domain: newDomain,
      goal_type: newType,
      priority: newPriority,
    })
    setNewTitle('')
    setNewDescription('')
    setNewDomain('')
    setShowAddGoal(false)
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-mono text-text-tertiary uppercase">{goals.length} Goals</span>
        <button
          onClick={() => setShowAddGoal(!showAddGoal)}
          className="flex items-center gap-1 px-2 py-1 text-[10px] font-mono uppercase bg-cyan/10 text-cyan border border-cyan/30 rounded hover:bg-cyan/20"
        >
          <Plus size={10} />
          Add Goal
        </button>
      </div>

      {showAddGoal && (
        <div className="border border-cyan/30 bg-surface-raised rounded p-3 space-y-2">
          <input
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Goal title..."
            className="w-full bg-surface border border-border rounded px-2 py-1 text-xs text-text-primary placeholder:text-text-tertiary"
          />
          <textarea
            value={newDescription}
            onChange={(e) => setNewDescription(e.target.value)}
            placeholder="Description..."
            rows={2}
            className="w-full bg-surface border border-border rounded px-2 py-1 text-xs text-text-primary placeholder:text-text-tertiary resize-none"
          />
          <div className="flex gap-2">
            <select
              value={newDomain}
              onChange={(e) => setNewDomain(e.target.value)}
              className="bg-surface border border-border rounded px-2 py-1 text-xs text-text-primary"
            >
              <option value="">Domain...</option>
              {['engineering', 'business_operations', 'content', 'sales', 'marketing', 'finance', 'music', 'infrastructure'].map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
            <select
              value={newType}
              onChange={(e) => setNewType(e.target.value)}
              className="bg-surface border border-border rounded px-2 py-1 text-xs text-text-primary"
            >
              {['goal', 'project', 'roadmap', 'milestone'].map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
            <input
              type="number"
              value={newPriority}
              onChange={(e) => setNewPriority(Number(e.target.value))}
              min={0}
              max={100}
              className="w-16 bg-surface border border-border rounded px-2 py-1 text-xs text-text-primary"
              title="Priority (0-100)"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={() => setShowAddGoal(false)} className="px-2 py-1 text-[10px] font-mono text-text-tertiary hover:text-text-secondary">Cancel</button>
            <button onClick={handleAdd} className="px-2 py-1 text-[10px] font-mono bg-cyan/20 text-cyan rounded hover:bg-cyan/30">Create</button>
          </div>
        </div>
      )}

      {goals.map((goal) => (
        <GoalCard key={goal.goal_id} goal={goal} onDelete={deleteGoal} />
      ))}

      {goals.length === 0 && (
        <div className="text-center py-8 text-text-tertiary text-xs">
          No goals defined. Add goals to enable strategic gap detection.
        </div>
      )}
    </div>
  )
}

function GoalCard({ goal, onDelete }: { goal: GoalData; onDelete: (id: string) => Promise<boolean> }) {
  const key = `strategy:goal:${goal.id}`
  const expanded = useCollapseStore((s) => s.isOpen(key))
  const toggle = useCollapseStore((s) => s.toggle)
  const met = goal.success_criteria.filter((c) => c.met).length
  const total = goal.success_criteria.length
  const progress = total > 0 ? Math.round((met / total) * 100) : 0

  return (
    <div className="border border-border rounded overflow-hidden">
      <button onClick={() => toggle(key)} className="flex items-center gap-2 w-full px-3 py-2 text-left hover:bg-surface-raised">
        <ChevronRight size={12} className={`text-text-tertiary transition-transform ${expanded ? 'rotate-90' : ''}`} />
        <span className="text-xs text-text-primary flex-1">{goal.title}</span>
        <span className={`px-1.5 py-0.5 text-[9px] font-mono uppercase rounded ${STATUS_COLORS[goal.status] ?? ''}`}>{goal.status}</span>
        <span className="text-[9px] font-mono text-text-tertiary">{goal.goal_type}</span>
        {total > 0 && <span className="text-[9px] font-mono text-text-tertiary">{progress}%</span>}
      </button>
      {expanded && (
        <div className="px-3 pb-3 border-t border-border bg-surface-raised space-y-2">
          {goal.description && <p className="text-[10px] text-text-secondary">{goal.description}</p>}
          <div className="flex gap-4 text-[9px] font-mono text-text-tertiary">
            {goal.domain && <span>Domain: {goal.domain}</span>}
            <span>Priority: {goal.priority}</span>
            {goal.target_date && <span>Target: {goal.target_date}</span>}
          </div>
          {goal.success_criteria.length > 0 && (
            <div className="space-y-1">
              <div className="text-[9px] font-mono text-text-tertiary uppercase">Success Criteria</div>
              {goal.success_criteria.map((c, i) => (
                <div key={i} className="flex items-center gap-2 text-[10px]">
                  {c.met ? <CheckCircle2 size={10} className="text-green-400" /> : <XCircle size={10} className="text-text-tertiary" />}
                  <span className={c.met ? 'text-green-400' : 'text-text-secondary'}>{c.description}</span>
                </div>
              ))}
            </div>
          )}
          {goal.required_capabilities.length > 0 && (
            <div className="flex gap-1 flex-wrap">
              {goal.required_capabilities.map((cap) => (
                <span key={cap} className="px-1.5 py-0.5 text-[9px] font-mono text-text-tertiary bg-surface border border-border rounded">{cap}</span>
              ))}
            </div>
          )}
          <div className="flex justify-end">
            <button
              onClick={() => onDelete(goal.goal_id)}
              className="text-[9px] font-mono text-red-400/60 hover:text-red-400"
            >Delete</button>
          </div>
        </div>
      )}
    </div>
  )
}

/* ── Gaps Tab ───────────────────────────────────────────────────── */

function GapsTab({ gaps }: { gaps: GapData[] }) {
  const sorted = [...gaps].sort((a, b) => b.priority_score - a.priority_score)

  return (
    <div className="space-y-2">
      <div className="text-[10px] font-mono text-text-tertiary uppercase">{gaps.length} Gaps Detected</div>
      {sorted.map((gap) => (
        <GapCard key={gap.gap_id} gap={gap} />
      ))}
      {gaps.length === 0 && (
        <div className="text-center py-8 text-text-tertiary text-xs">
          No gaps detected. Run analysis to scan goals against reality.
        </div>
      )}
    </div>
  )
}

function GapCard({ gap }: { gap: GapData }) {
  return (
    <div className={`border rounded p-3 ${SEVERITY_COLORS[gap.severity] ?? 'border-border'}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-text-primary">{gap.title}</span>
        <div className="flex items-center gap-2">
          <span className="text-[9px] font-mono uppercase">{gap.severity}</span>
          <span className="text-[9px] font-mono text-text-tertiary">{gap.priority_score.toFixed(1)}</span>
        </div>
      </div>
      <p className="text-[10px] text-text-secondary">{gap.description}</p>
      <div className="flex gap-3 mt-2 text-[9px] font-mono text-text-tertiary">
        {gap.domain && <span>Domain: {gap.domain}</span>}
        <span>Type: {gap.gap_type}</span>
        {gap.current_state && <span>Current: {gap.current_state}</span>}
      </div>
    </div>
  )
}

/* ── Recommendations Tab ────────────────────────────────────────── */

function RecommendationsTab({
  recommendations,
  onApprove,
  onReject,
}: {
  recommendations: RecommendationData[]
  onApprove: (id: string, reason?: string) => Promise<Record<string, unknown> | null>
  onReject: (id: string, reason?: string) => Promise<boolean>
}) {
  const pending = recommendations.filter((r) => r.status === 'pending')
  const decided = recommendations.filter((r) => r.status !== 'pending')

  return (
    <div className="space-y-4">
      {pending.length > 0 && (
        <div className="space-y-2">
          <div className="text-[10px] font-mono text-cyan uppercase">Pending Approval ({pending.length})</div>
          {pending.map((rec) => (
            <RecCard key={rec.recommendation_id} rec={rec} onApprove={onApprove} onReject={onReject} />
          ))}
        </div>
      )}
      {decided.length > 0 && (
        <div className="space-y-2">
          <div className="text-[10px] font-mono text-text-tertiary uppercase">Decided ({decided.length})</div>
          {decided.map((rec) => (
            <RecCard key={rec.recommendation_id} rec={rec} onApprove={onApprove} onReject={onReject} />
          ))}
        </div>
      )}
      {recommendations.length === 0 && (
        <div className="text-center py-8 text-text-tertiary text-xs">
          No recommendations. Run analysis to generate strategic recommendations.
        </div>
      )}
    </div>
  )
}

function RecCard({
  rec, onApprove, onReject,
}: {
  rec: RecommendationData
  onApprove: (id: string, reason?: string) => Promise<Record<string, unknown> | null>
  onReject: (id: string, reason?: string) => Promise<boolean>
}) {
  const [acting, setActing] = useState(false)

  const handleApprove = async () => {
    setActing(true)
    await onApprove(rec.recommendation_id)
    setActing(false)
  }

  const handleReject = async () => {
    setActing(true)
    await onReject(rec.recommendation_id)
    setActing(false)
  }

  const isPending = rec.status === 'pending'

  return (
    <div className="border border-border rounded p-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-text-primary">{rec.title}</span>
        <span className="text-[9px] font-mono text-text-tertiary">{rec.priority_score.toFixed(1)}</span>
      </div>
      <p className="text-[10px] text-text-secondary mb-2">{rec.rationale}</p>
      <div className="flex gap-3 text-[9px] font-mono text-text-tertiary mb-2">
        <span>Impact: {rec.impact_estimate}</span>
        <span>Risk: {rec.risk_estimate}</span>
        <span>Domain: {rec.suggested_domain}</span>
        {rec.suggested_agents.length > 0 && <span>Agents: {rec.suggested_agents.join(', ')}</span>}
      </div>
      {isPending && (
        <div className="flex gap-2">
          <button
            onClick={handleApprove}
            disabled={acting}
            className="flex items-center gap-1 px-2 py-1 text-[10px] font-mono text-green-400 bg-green-400/10 border border-green-400/30 rounded hover:bg-green-400/20 disabled:opacity-50"
          >
            <ThumbsUp size={10} />
            Approve → WorkPacket
          </button>
          <button
            onClick={handleReject}
            disabled={acting}
            className="flex items-center gap-1 px-2 py-1 text-[10px] font-mono text-red-400 bg-red-400/10 border border-red-400/30 rounded hover:bg-red-400/20 disabled:opacity-50"
          >
            <ThumbsDown size={10} />
            Reject
          </button>
        </div>
      )}
      {!isPending && (
        <div className="flex items-center gap-1 text-[9px] font-mono">
          {rec.status === 'converted' && <CheckCircle2 size={10} className="text-green-400" />}
          {rec.status === 'rejected' && <XCircle size={10} className="text-red-400" />}
          <span className="text-text-tertiary uppercase">{rec.status}</span>
          {rec.converted_packet_id && <span className="text-text-tertiary">→ {rec.converted_packet_id}</span>}
        </div>
      )}
    </div>
  )
}

/* ── Decisions Tab ──────────────────────────────────────────────── */

function DecisionsTab({ decisions }: { decisions: DecisionData[] }) {
  const recordOutcome = useOperatorLoopStore((s) => s.recordDecisionOutcome)

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 mb-2">
        <History size={12} className="text-text-secondary" />
        <span className="text-[10px] font-mono text-text-secondary uppercase">Decision History ({decisions.length})</span>
      </div>
      {decisions.map((dec) => (
        <DecisionCard key={dec.decision_id} decision={dec} onRecordOutcome={recordOutcome} />
      ))}
      {decisions.length === 0 && (
        <div className="text-center py-8 text-text-tertiary text-xs">
          No decisions recorded yet. Approve or reject recommendations to build decision history.
        </div>
      )}
    </div>
  )
}

function DecisionCard({
  decision, onRecordOutcome,
}: {
  decision: DecisionData
  onRecordOutcome: (id: string, effective: boolean, summary?: string) => Promise<boolean>
}) {
  return (
    <div className="border border-border rounded p-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-text-primary capitalize">{decision.action}: {decision.recommendation_id}</span>
        <div className="flex items-center gap-1">
          {decision.was_effective === true && <CheckCircle2 size={10} className="text-green-400" />}
          {decision.was_effective === false && <XCircle size={10} className="text-red-400" />}
          {decision.was_effective === null && (
            <div className="flex gap-1">
              <button
                onClick={() => onRecordOutcome(decision.decision_id, true)}
                className="p-0.5 text-text-tertiary hover:text-green-400"
                title="Mark effective"
              >
                <ThumbsUp size={10} />
              </button>
              <button
                onClick={() => onRecordOutcome(decision.decision_id, false)}
                className="p-0.5 text-text-tertiary hover:text-red-400"
                title="Mark ineffective"
              >
                <ThumbsDown size={10} />
              </button>
            </div>
          )}
        </div>
      </div>
      {decision.reason && <p className="text-[10px] text-text-secondary">{decision.reason}</p>}
      {decision.outcome_summary && <p className="text-[10px] text-text-tertiary mt-1">{decision.outcome_summary}</p>}
      <div className="flex gap-3 mt-1 text-[9px] font-mono text-text-tertiary">
        {decision.outcome_packet_id && <span>Packet: {decision.outcome_packet_id}</span>}
        <span>{new Date(decision.created_at * 1000).toLocaleDateString()}</span>
      </div>
    </div>
  )
}
