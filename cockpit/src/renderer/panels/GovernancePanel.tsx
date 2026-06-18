import { useEffect, useState } from 'react'
import { useGovernanceStore } from '../stores/governanceStore'

const TABS = ['overview', 'conflicts', 'coordination', 'knowledge', 'health'] as const
type Tab = typeof TABS[number]

const healthColor: Record<string, string> = {
  coherent: 'text-green-400',
  synchronized: 'text-green-400',
  thriving: 'text-green-400',
  optimized: 'text-green-400',
  aligned: 'text-blue-400',
  focused: 'text-blue-400',
  growing: 'text-blue-400',
  strained: 'text-yellow-400',
  drifting: 'text-yellow-400',
  stagnant: 'text-yellow-400',
  fragmented: 'text-orange-400',
  overcommitted: 'text-orange-400',
  decaying: 'text-orange-400',
  critical: 'text-red-400',
}

const severityColor: Record<string, string> = {
  critical: 'text-red-400',
  high: 'text-orange-400',
  medium: 'text-yellow-400',
  low: 'text-gray-400',
}

function OverviewTab() {
  const { overview } = useGovernanceStore()
  if (!overview) return <div className="wv-card p-4 text-gray-400">No data</div>
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Organism Health</div>
          <div className={`text-lg font-bold ${healthColor[overview.organism_health] || 'text-gray-300'}`}>
            {overview.organism_health}
          </div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Coherence Score</div>
          <div className="text-lg font-bold text-white">{(overview.coherence_score * 100).toFixed(1)}%</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Subsystems</div>
          <div className="text-lg font-bold text-white">{overview.subsystem_health?.length || 0}</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Drift Warnings</div>
          <div className={`text-lg font-bold ${overview.total_drift_count > 0 ? 'text-yellow-400' : 'text-green-400'}`}>
            {overview.total_drift_count}
          </div>
        </div>
      </div>
      {overview.subsystem_health && overview.subsystem_health.length > 0 && (
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400 mb-2">Subsystem Health</div>
          <div className="grid grid-cols-4 gap-2">
            {overview.subsystem_health.map((s) => (
              <div key={s.subsystem} className="flex items-center gap-2 text-xs">
                <span className="text-gray-400">{s.subsystem}</span>
                <span className={healthColor[s.health] || 'text-gray-300'}>{s.health}</span>
                {s.drift_count > 0 && <span className="text-yellow-400">({s.drift_count})</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function ConflictsTab() {
  const { conflicts } = useGovernanceStore()
  if (conflicts.length === 0) return <div className="wv-card p-4 text-gray-400">No active conflicts</div>
  return (
    <div className="space-y-2">
      {conflicts.map((c) => (
        <div key={c.conflict_id} className="wv-card p-3">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs font-bold ${severityColor[c.severity] || 'text-gray-400'}`}>{c.severity}</span>
            <span className="text-xs text-gray-400">{c.conflict_type}</span>
          </div>
          <div className="text-xs text-gray-300 mb-1">
            <span className="text-green-400">{c.winning_authority}</span>
            <span className="text-gray-500"> beats </span>
            <span className="text-red-400">{c.losing_authority}</span>
          </div>
          <div className="text-xs text-gray-400">{c.resolution}</div>
          <div className="text-xs text-gray-500 mt-1">{c.rationale}</div>
        </div>
      ))}
    </div>
  )
}

function CoordinationTab() {
  const { coordination } = useGovernanceStore()
  if (!coordination) return <div className="wv-card p-4 text-gray-400">No data</div>
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Coordination Health</div>
          <div className={`text-lg font-bold ${healthColor[coordination.coordination_health] || 'text-gray-300'}`}>
            {coordination.coordination_health}
          </div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Sync Score</div>
          <div className="text-lg font-bold text-white">{(coordination.synchronization_score * 100).toFixed(1)}%</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Bottlenecks</div>
          <div className={`text-lg font-bold ${coordination.bottleneck_count > 0 ? 'text-orange-400' : 'text-green-400'}`}>
            {coordination.bottleneck_count}
          </div>
        </div>
      </div>
      {coordination.issues && coordination.issues.length > 0 && (
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400 mb-2">Issues ({coordination.issues.length})</div>
          {coordination.issues.map((issue, i) => (
            <div key={i} className="text-xs text-gray-300 mb-1">
              <span className={severityColor[String(issue.severity)] || 'text-gray-400'}>{String(issue.severity)}</span>
              {' '}{String(issue.description || '')}
            </div>
          ))}
        </div>
      )}
      {coordination.subsystem_alignment && (
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400 mb-2">Subsystem Alignment</div>
          <div className="grid grid-cols-3 gap-2">
            {Object.entries(coordination.subsystem_alignment).map(([name, health]) => (
              <div key={name} className="flex items-center gap-2 text-xs">
                <span className="text-gray-400">{name}</span>
                <span className={healthColor[health] || 'text-gray-300'}>{health}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function KnowledgeTab() {
  const { institutionalMemory } = useGovernanceStore()
  if (!institutionalMemory) return <div className="wv-card p-4 text-gray-400">No data</div>
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Memory Health</div>
          <div className={`text-lg font-bold ${healthColor[institutionalMemory.memory_health] || 'text-gray-300'}`}>
            {institutionalMemory.memory_health}
          </div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Total Knowledge</div>
          <div className="text-lg font-bold text-white">{institutionalMemory.total_knowledge}</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Canonical</div>
          <div className="text-lg font-bold text-green-400">{institutionalMemory.canonical_count}</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Validation Rate</div>
          <div className="text-lg font-bold text-white">{(institutionalMemory.validation_rate * 100).toFixed(1)}%</div>
        </div>
      </div>
      {institutionalMemory.knowledge_by_state && (
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400 mb-2">Knowledge by State</div>
          <div className="grid grid-cols-5 gap-2">
            {Object.entries(institutionalMemory.knowledge_by_state).map(([state, count]) => (
              <div key={state} className="text-xs">
                <span className="text-gray-400">{state}: </span>
                <span className="text-white font-bold">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {institutionalMemory.recent_promotions && institutionalMemory.recent_promotions.length > 0 && (
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400 mb-2">Recent Promotions</div>
          {institutionalMemory.recent_promotions.map((p, i) => (
            <div key={i} className="text-xs text-gray-300 mb-1">{String(p.content || p.knowledge_id || '')}</div>
          ))}
        </div>
      )}
    </div>
  )
}

function HealthTab() {
  const { overview, drift } = useGovernanceStore()
  if (!overview) return <div className="wv-card p-4 text-gray-400">No data</div>
  return (
    <div className="space-y-4">
      {overview.subsystem_health && (
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400 mb-2">All Subsystem Health</div>
          <div className="space-y-1">
            {overview.subsystem_health.map((s) => (
              <div key={s.subsystem} className="flex items-center justify-between text-xs">
                <span className="text-gray-300">{s.subsystem}</span>
                <div className="flex items-center gap-3">
                  <span className={healthColor[s.health] || 'text-gray-300'}>{s.health}</span>
                  <span className="text-gray-500 w-12 text-right">{(s.score * 100).toFixed(0)}%</span>
                  {s.drift_count > 0 && <span className="text-yellow-400">{s.drift_count} drift</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      {drift.length > 0 && (
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400 mb-2">Drift Warnings ({drift.length})</div>
          {drift.map((w, i) => (
            <div key={i} className="text-xs text-gray-300 mb-1">
              <span className={severityColor[w.severity] || 'text-gray-400'}>{w.severity}</span>
              {' '}<span className="text-gray-500">[{w.drift_type}]</span>
              {' '}{w.description}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function GovernancePanel() {
  const [tab, setTab] = useState<Tab>('overview')
  const { fetchAll } = useGovernanceStore()
  useEffect(() => { fetchAll() }, [])
  return (
    <div className="flex flex-col h-full">
      <div className="flex gap-2 p-2 border-b border-gray-700">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-1 text-xs rounded ${
              tab === t ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            {t}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto p-3">
        {tab === 'overview' && <OverviewTab />}
        {tab === 'conflicts' && <ConflictsTab />}
        {tab === 'coordination' && <CoordinationTab />}
        {tab === 'knowledge' && <KnowledgeTab />}
        {tab === 'health' && <HealthTab />}
      </div>
    </div>
  )
}
