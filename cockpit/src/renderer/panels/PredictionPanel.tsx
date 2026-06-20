import { useEffect, useState } from 'react'
import { usePredictionStore } from '../stores/predictionStore'

const TABS = ['overview', 'forecasts', 'scenarios', 'risk', 'confidence'] as const

function OverviewTab() {
  const { overview } = usePredictionStore()
  if (!overview) return <div className="wv-card p-4 text-gray-400">No prediction data</div>

  const healthColor: Record<string, string> = {
    high_confidence: 'text-green-400',
    stable: 'text-blue-400',
    uncertain: 'text-yellow-400',
    volatile: 'text-orange-400',
    blind: 'text-red-400',
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Prediction Health</div>
          <div className={`text-xl font-bold ${healthColor[overview.prediction_health] || 'text-gray-300'}`}>
            {overview.prediction_health.replace('_', ' ')}
          </div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Forecasts</div>
          <div className="text-xl font-bold">{overview.forecast_count}</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Scenarios</div>
          <div className="text-xl font-bold">{overview.scenario_count}</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Uncertainty</div>
          <div className="text-xl font-bold">{(overview.uncertainty_index * 100).toFixed(0)}%</div>
          <div className="text-xs text-gray-500">confidence: {(overview.average_confidence * 100).toFixed(0)}%</div>
        </div>
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
      {overview.critical_risks.length > 0 && (
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400 mb-2">Critical Future Risks</div>
          {overview.critical_risks.map((r, i) => (
            <div key={i} className="text-sm text-red-400 mb-1">{r.risk}</div>
          ))}
        </div>
      )}
    </div>
  )
}

function ForecastsTab() {
  const { forecasts } = usePredictionStore()
  if (!forecasts.length) return <div className="wv-card p-4 text-gray-400">No forecasts</div>

  const statusColor: Record<string, string> = {
    accelerating: 'text-green-400',
    stable: 'text-blue-400',
    slowing: 'text-yellow-400',
    stalled: 'text-orange-400',
    declining: 'text-red-400',
  }

  return (
    <div className="space-y-2">
      {forecasts.map((f) => (
        <div key={f.entity_id} className="wv-card p-3">
          <div className="flex justify-between items-center mb-1">
            <div className="text-sm font-medium">{f.entity_id}</div>
            <div className={`text-sm font-bold ${statusColor[f.status] || 'text-gray-300'}`}>
              {f.status}
            </div>
          </div>
          <div className="text-xs text-gray-400 mb-1">
            type: {f.entity_type} | confidence: {(f.confidence * 100).toFixed(0)}% | horizon: {f.forecast_horizon_days}d
          </div>
          <div className="text-xs text-gray-500">{f.confidence_reason}</div>
          {f.contributing_factors.length > 0 && (
            <div className="text-xs text-gray-500 mt-1">
              factors: {f.contributing_factors.join(', ')}
            </div>
          )}
          {f.source_signals.length > 0 && (
            <div className="text-xs text-gray-600 mt-1">
              signals: {f.source_signals.join(', ')}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function ScenariosTab() {
  const { scenarios } = usePredictionStore()
  if (!scenarios.length) return <div className="wv-card p-4 text-gray-400">No scenarios</div>

  const typeColor: Record<string, string> = {
    best_case: 'border-green-600',
    expected: 'border-blue-600',
    worst_case: 'border-red-600',
    disruption: 'border-purple-600',
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      {scenarios.map((s) => (
        <div key={s.scenario_id} className={`wv-card p-3 border-l-2 ${typeColor[s.scenario_type] || 'border-gray-600'}`}>
          <div className="text-sm font-medium mb-1">{s.title}</div>
          <div className="text-xs text-gray-400 mb-2">
            probability: {(s.probability * 100).toFixed(1)}%
          </div>
          {s.assumptions.length > 0 && (
            <div className="mb-2">
              <div className="text-xs text-gray-500 mb-1">Assumptions:</div>
              {s.assumptions.slice(0, 3).map((a, i) => (
                <div key={i} className="text-xs text-gray-400 ml-2">• {a}</div>
              ))}
            </div>
          )}
          <div className="flex gap-4 text-xs">
            {s.risks.length > 0 && (
              <span className="text-red-400">{s.risks.length} risks</span>
            )}
            {s.opportunities.length > 0 && (
              <span className="text-green-400">{s.opportunities.length} opportunities</span>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

function RiskTab() {
  const { forecasts, drift } = usePredictionStore()

  const atRisk = forecasts.filter(f =>
    f.status === 'slowing' || f.status === 'stalled' || f.status === 'declining'
  )

  return (
    <div className="space-y-4">
      <div className="wv-card p-3">
        <div className="text-xs text-gray-400 mb-2">At-Risk Trajectories ({atRisk.length})</div>
        {atRisk.length === 0 ? (
          <div className="text-sm text-gray-500">No at-risk trajectories</div>
        ) : (
          atRisk.map((f) => (
            <div key={f.entity_id} className="text-sm mb-2">
              <span className="text-orange-400 font-medium">{f.entity_id}</span>
              <span className="text-gray-400 ml-2">{f.status}</span>
              <div className="text-xs text-gray-500">{f.confidence_reason}</div>
            </div>
          ))
        )}
      </div>
      <div className="wv-card p-3">
        <div className="text-xs text-gray-400 mb-2">Prediction Drift ({drift.length})</div>
        {drift.length === 0 ? (
          <div className="text-sm text-gray-500">No drift warnings</div>
        ) : (
          drift.map((w, i) => (
            <div key={i} className="text-sm mb-2">
              <span className="text-yellow-400 font-medium">[{w.severity}]</span>
              <span className="text-gray-300 ml-1">{w.description}</span>
              <div className="text-xs text-gray-500">{w.recommendation}</div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function ConfidenceTab() {
  const { overview, forecasts } = usePredictionStore()

  const avgConf = overview?.average_confidence ?? 0
  const uncertainty = overview?.uncertainty_index ?? 1

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Average Confidence</div>
          <div className="text-xl font-bold">{(avgConf * 100).toFixed(0)}%</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Uncertainty Index</div>
          <div className="text-xl font-bold">{(uncertainty * 100).toFixed(0)}%</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Health</div>
          <div className="text-xl font-bold">{overview?.prediction_health?.replace('_', ' ') || 'unknown'}</div>
        </div>
      </div>
      <div className="wv-card p-3">
        <div className="text-xs text-gray-400 mb-2">Per-Forecast Confidence</div>
        {forecasts.length === 0 ? (
          <div className="text-sm text-gray-500">No forecasts</div>
        ) : (
          forecasts.map((f) => (
            <div key={f.entity_id} className="flex justify-between items-center text-sm mb-1">
              <span className="text-gray-300">{f.entity_id}</span>
              <div className="flex items-center gap-2">
                <div className="w-24 bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-blue-500 rounded-full h-2"
                    style={{ width: `${f.confidence * 100}%` }}
                  />
                </div>
                <span className="text-xs text-gray-400 w-10 text-right">
                  {(f.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export function PredictionPanel() {
  const { fetchAll, loading } = usePredictionStore()
  const [activeTab, setActiveTab] = useState<typeof TABS[number]>('overview')

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  return (
    <div className="h-full flex flex-col p-4 space-y-4 overflow-auto">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold">Prediction Intelligence</h2>
        {loading && <span className="text-xs text-gray-500">—</span>}
      </div>

      <div className="flex gap-2">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-3 py-1 text-sm rounded ${
              activeTab === tab
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto">
        {activeTab === 'overview' && <OverviewTab />}
        {activeTab === 'forecasts' && <ForecastsTab />}
        {activeTab === 'scenarios' && <ScenariosTab />}
        {activeTab === 'risk' && <RiskTab />}
        {activeTab === 'confidence' && <ConfidenceTab />}
      </div>
    </div>
  )
}

