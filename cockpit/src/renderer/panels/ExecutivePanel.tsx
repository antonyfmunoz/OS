import { useEffect, useState } from 'react'
import { useExecutiveStore } from '../stores/executiveStore'

const TABS = ['overview', 'allocations', 'budgets', 'tradeoffs', 'drift'] as const

const healthColor: Record<string, string> = {
  optimized: 'text-green-400',
  focused: 'text-blue-400',
  fragmented: 'text-yellow-400',
  overcommitted: 'text-orange-400',
  critical: 'text-red-400',
}

const priorityColor: Record<string, string> = {
  critical: 'text-red-400',
  high: 'text-orange-400',
  medium: 'text-yellow-400',
  low: 'text-blue-400',
  defer: 'text-gray-500',
}

function OverviewTab() {
  const { overview } = useExecutiveStore()
  if (!overview) return <div className="wv-card p-4 text-gray-400">No executive data</div>

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Executive Health</div>
          <div className={`text-xl font-bold ${healthColor[overview.executive_health] || 'text-gray-300'}`}>
            {overview.executive_health.replace('_', ' ')}
          </div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Focus Score</div>
          <div className="text-xl font-bold">{(overview.focus_score * 100).toFixed(0)}%</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Overcommitment</div>
          <div className="text-xl font-bold">{(overview.overcommitment_index * 100).toFixed(0)}%</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Allocation Health</div>
          <div className={`text-xl font-bold ${healthColor[overview.allocation_health] || 'text-gray-300'}`}>
            {overview.allocation_health.replace('_', ' ')}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {Object.entries({
          work: overview.work_health,
          prediction: overview.prediction_health,
          learning: overview.learning_health,
          decisions: overview.decision_health,
          capabilities: overview.capability_health,
          goals: overview.goal_alignment_health,
        }).map(([label, value]) => (
          <div key={label} className="wv-card p-2">
            <div className="text-xs text-gray-500">{label}</div>
            <div className="text-sm">{value}</div>
          </div>
        ))}
      </div>

      {overview.drift_warnings.length > 0 && (
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400 mb-2">Drift Warnings ({overview.drift_warnings.length})</div>
          {overview.drift_warnings.map((w, i) => (
            <div key={i} className="text-sm text-yellow-400 mb-1">
              [{w.severity}] {w.description}
            </div>
          ))}
        </div>
      )}

      {overview.top_recommendations.length > 0 && (
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400 mb-2">Top Recommendations</div>
          {overview.top_recommendations.map((r, i) => (
            <div key={i} className="text-sm mb-1">
              <span className={priorityColor[r.priority] || 'text-gray-300'}>[{r.priority}]</span>{' '}
              {r.target_name} — leverage {(r.leverage_score * 100).toFixed(0)}%
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function AllocationsTab() {
  const { allocations } = useExecutiveStore()
  if (allocations.length === 0) return <div className="wv-card p-4 text-gray-400">No allocations</div>

  return (
    <div className="space-y-2">
      {allocations.map((r) => (
        <div key={r.recommendation_id} className="wv-card p-3">
          <div className="flex justify-between items-center">
            <div>
              <span className={`font-bold ${priorityColor[r.priority] || ''}`}>{r.priority.toUpperCase()}</span>
              <span className="ml-2 text-gray-300">{r.target_name}</span>
              <span className="ml-2 text-xs text-gray-500">({r.target_type})</span>
            </div>
            <div className="text-sm text-gray-400">
              leverage: {(r.leverage_score * 100).toFixed(0)}% | confidence: {(r.allocation_confidence * 100).toFixed(0)}%
            </div>
          </div>
          <div className="text-xs text-gray-500 mt-1">{r.rationale}</div>
          {r.competing_targets.length > 0 && (
            <div className="text-xs text-gray-600 mt-1">
              Competing: {r.competing_targets.slice(0, 3).join(', ')}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function BudgetsTab() {
  const { budgets } = useExecutiveStore()
  if (budgets.length === 0) return <div className="wv-card p-4 text-gray-400">No budget data</div>

  return (
    <div className="space-y-2">
      {budgets.map((b) => (
        <div key={b.resource_type} className="wv-card p-3">
          <div className="flex justify-between">
            <span className="font-bold text-gray-200">{b.resource_type.replace('_', ' ')}</span>
            {b.overcommitted && <span className="text-xs text-red-400 font-bold">OVERCOMMITTED</span>}
          </div>
          <div className="mt-2 h-2 bg-gray-700 rounded">
            <div
              className={`h-full rounded ${b.overcommitted ? 'bg-red-500' : 'bg-blue-500'}`}
              style={{ width: `${Math.min(b.allocated * 100, 100)}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>Allocated: {(b.allocated * 100).toFixed(0)}%</span>
            <span>Available: {(b.available * 100).toFixed(0)}%</span>
          </div>
        </div>
      ))}
    </div>
  )
}

function TradeoffsTab() {
  const { contention } = useExecutiveStore()
  const entries = Object.entries(contention)
  if (entries.length === 0) return <div className="wv-card p-4 text-gray-400">No resource contention</div>

  return (
    <div className="space-y-2">
      {entries.map(([resource, targets]) => (
        <div key={resource} className="wv-card p-3">
          <div className="font-bold text-gray-200">{resource.replace('_', ' ')}</div>
          <div className="text-xs text-gray-400 mt-1">{targets.length} competing targets</div>
          <div className="mt-1">
            {targets.map((t, i) => (
              <span key={i} className="text-xs text-gray-500 mr-2">{t}</span>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function DriftTab() {
  const { drift } = useExecutiveStore()
  if (drift.length === 0) return <div className="wv-card p-4 text-green-400">No executive drift detected</div>

  const severityColor: Record<string, string> = {
    critical: 'text-red-400 border-red-800',
    high: 'text-orange-400 border-orange-800',
    medium: 'text-yellow-400 border-yellow-800',
    low: 'text-blue-400 border-blue-800',
  }

  return (
    <div className="space-y-2">
      {drift.map((w, i) => (
        <div key={i} className={`wv-card p-3 border-l-2 ${severityColor[w.severity] || 'border-gray-700'}`}>
          <div className="flex justify-between">
            <span className="font-bold text-gray-200">{w.drift_type.replace('_', ' ')}</span>
            <span className={`text-xs ${severityColor[w.severity]?.split(' ')[0] || ''}`}>{w.severity}</span>
          </div>
          <div className="text-sm text-gray-400 mt-1">{w.description}</div>
          {w.recommendation && (
            <div className="text-xs text-gray-500 mt-1 italic">{w.recommendation}</div>
          )}
        </div>
      ))}
    </div>
  )
}

export function ExecutivePanel() {
  const [tab, setTab] = useState<typeof TABS[number]>('overview')
  const { fetchAll } = useExecutiveStore()

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  return (
    <div className="p-4 space-y-4">
      <div className="flex gap-2">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-1 rounded text-sm ${
              tab === t ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {tab === 'overview' && <OverviewTab />}
      {tab === 'allocations' && <AllocationsTab />}
      {tab === 'budgets' && <BudgetsTab />}
      {tab === 'tradeoffs' && <TradeoffsTab />}
      {tab === 'drift' && <DriftTab />}
    </div>
  )
}
