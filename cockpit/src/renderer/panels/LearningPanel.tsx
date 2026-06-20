import { useEffect } from 'react'
import { useLearningStore } from '../stores/learningStore'

const TABS = ['overview', 'lessons', 'patterns', 'evolution', 'drift'] as const

function OverviewTab() {
  const { overview } = useLearningStore()
  if (!overview) return <div className="wv-card p-4 text-gray-400">No learning data</div>

  const healthColor: Record<string, string> = {
    thriving: 'text-green-400',
    healthy: 'text-blue-400',
    stagnant: 'text-yellow-400',
    declining: 'text-orange-400',
    critical: 'text-red-400',
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Health</div>
          <div className={`text-xl font-bold ${healthColor[overview.health] || 'text-gray-300'}`}>
            {overview.health}
          </div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Lessons</div>
          <div className="text-xl font-bold">{overview.lesson_count}</div>
          <div className="text-xs text-gray-500">{overview.actionable_lesson_count} actionable</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Patterns</div>
          <div className="text-xl font-bold">{overview.pattern_count}</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Compounding</div>
          <div className="text-xl font-bold">{(overview.compounding_score * 100).toFixed(0)}%</div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Lesson Velocity</div>
          <div className="text-lg font-mono">{overview.lesson_velocity.toFixed(2)}/day</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Pattern Velocity</div>
          <div className="text-lg font-mono">{overview.pattern_velocity.toFixed(2)}/day</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Outcome Loop</div>
          <div className="text-lg font-mono">{overview.outcome_loop_health}</div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Advancing</div>
          <div className="text-xl font-bold text-green-400">{overview.advancing_capabilities}</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Declining</div>
          <div className="text-xl font-bold text-red-400">{overview.declining_capabilities}</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Stalled</div>
          <div className="text-xl font-bold text-yellow-400">{overview.stalled_capabilities}</div>
        </div>
      </div>

      {overview.drift_warnings.length > 0 && (
        <div className="wv-card p-4">
          <h3 className="text-sm font-medium text-yellow-400 mb-3">
            Drift Warnings ({overview.drift_warnings.length})
          </h3>
          <div className="space-y-2">
            {overview.drift_warnings.slice(0, 3).map((w, i) => (
              <div key={i} className="p-2 bg-yellow-900/20 border border-yellow-800/30 rounded">
                <div className="text-sm font-medium text-yellow-300">{w.drift_type}</div>
                <div className="text-xs text-gray-300">{w.description}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function LessonsTab() {
  const { lessons, actionableLessons } = useLearningStore()

  const categoryColor: Record<string, string> = {
    success_pattern: 'bg-green-900/30 text-green-300',
    failure_pattern: 'bg-red-900/30 text-red-300',
    assumption_invalidation: 'bg-orange-900/30 text-orange-300',
    decision_consequence: 'bg-blue-900/30 text-blue-300',
    capability_gap: 'bg-purple-900/30 text-purple-300',
    process_improvement: 'bg-cyan-900/30 text-cyan-300',
  }

  const displayLessons = lessons.length > 0 ? lessons : actionableLessons

  if (displayLessons.length === 0) {
    return <div className="wv-card p-4 text-gray-400">No lessons extracted yet</div>
  }

  return (
    <div className="space-y-2">
      {displayLessons.map((l) => (
        <div key={l.id} className="wv-card p-3">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs px-2 py-0.5 rounded ${categoryColor[l.category] || 'bg-gray-700 text-gray-300'}`}>
                  {l.category}
                </span>
                {l.actionable && (
                  <span className="text-xs px-2 py-0.5 rounded bg-green-900/30 text-green-300">actionable</span>
                )}
              </div>
              <div className="text-sm font-medium">{l.title}</div>
              <div className="text-xs text-gray-400 mt-1">{l.description}</div>
              {l.confidence_reason && (
                <div className="text-xs text-gray-500 mt-1">
                  Confidence: {(l.confidence * 100).toFixed(0)}% — {l.confidence_reason}
                </div>
              )}
            </div>
            <div className="text-right ml-3">
              <div className="text-sm font-mono">{(l.confidence * 100).toFixed(0)}%</div>
              <div className="text-xs text-gray-500">{l.source_count} sources</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function PatternsTab() {
  const { patterns } = useLearningStore()

  if (patterns.length === 0) {
    return <div className="wv-card p-4 text-gray-400">No patterns detected yet</div>
  }

  return (
    <div className="space-y-2">
      {patterns.map((p) => (
        <div key={p.id} className="wv-card p-3">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-300">{p.pattern_type}</span>
                <span className="text-xs text-gray-500">{p.occurrences} occurrences</span>
              </div>
              <div className="text-sm font-medium">{p.title}</div>
              <div className="text-xs text-gray-400 mt-1">{p.description}</div>
              {p.recommendation && (
                <div className="text-xs text-blue-400 mt-1">{p.recommendation}</div>
              )}
            </div>
            <div className="text-sm font-mono">{(p.confidence * 100).toFixed(0)}%</div>
          </div>
        </div>
      ))}
    </div>
  )
}

function EvolutionTab() {
  const { trajectories } = useLearningStore()

  if (trajectories.length === 0) {
    return <div className="wv-card p-4 text-gray-400">No capability evolution data</div>
  }

  const trendIcon: Record<string, string> = {
    advancing: 'text-green-400',
    stable: 'text-gray-400',
    declining: 'text-red-400',
    stalled: 'text-yellow-400',
  }

  return (
    <div className="space-y-2">
      {trajectories.map((t) => (
        <div key={t.capability_id} className="wv-card p-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">{t.capability_name}</div>
              <div className="text-xs text-gray-400">
                {t.current_maturity} — <span className={trendIcon[t.maturity_trend] || 'text-gray-400'}>{t.maturity_trend}</span>
              </div>
              {t.predicted_next_level && t.predicted_next_level !== 'unknown' && (
                <div className="text-xs text-gray-500 mt-1">
                  Next: {t.predicted_next_level} ({t.time_to_next_level_days > 0 ? `~${t.time_to_next_level_days}d` : 'unknown'})
                </div>
              )}
            </div>
            <div className="text-right">
              <div className="text-xs text-gray-500">{t.events.length} events</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function DriftTab() {
  const { driftWarnings } = useLearningStore()

  if (driftWarnings.length === 0) {
    return <div className="wv-card p-4 text-green-400">No drift warnings — learning pipeline healthy</div>
  }

  const severityColor: Record<string, string> = {
    high: 'border-red-800/50 bg-red-900/20',
    medium: 'border-yellow-800/50 bg-yellow-900/20',
    low: 'border-gray-700 bg-gray-800/30',
  }

  return (
    <div className="space-y-2">
      {driftWarnings.map((w, i) => (
        <div key={i} className={`wv-card p-3 border ${severityColor[w.severity] || 'border-gray-700'}`}>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium">{w.drift_type}</span>
            <span className={`text-xs px-2 py-0.5 rounded ${
              w.severity === 'high' ? 'bg-red-900/40 text-red-300' :
              w.severity === 'medium' ? 'bg-yellow-900/40 text-yellow-300' :
              'bg-gray-700 text-gray-300'
            }`}>
              {w.severity}
            </span>
          </div>
          <div className="text-xs text-gray-300">{w.description}</div>
          <div className="text-xs text-blue-400 mt-1">{w.recommendation}</div>
        </div>
      ))}
    </div>
  )
}

export function LearningPanel() {
  const { activeTab, setActiveTab, fetchAll, loading, error } = useLearningStore()

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <h2 className="text-lg font-semibold">Learning Intelligence</h2>
        <div className="flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3 py-1 text-sm rounded ${
                activeTab === tab
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {loading && <div className="text-gray-400 text-center py-8">—</div>}
        {error && <div className="text-red-400 text-center py-4">{error}</div>}
        {!loading && activeTab === 'overview' && <OverviewTab />}
        {!loading && activeTab === 'lessons' && <LessonsTab />}
        {!loading && activeTab === 'patterns' && <PatternsTab />}
        {!loading && activeTab === 'evolution' && <EvolutionTab />}
        {!loading && activeTab === 'drift' && <DriftTab />}
      </div>
    </div>
  )
}

export default LearningPanel
