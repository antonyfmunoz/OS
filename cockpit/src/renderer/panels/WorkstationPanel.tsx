import { useEffect, useState, useCallback } from 'react'
import { fetchApi } from '../api/client'

type Tab = 'preparation' | 'templates' | 'snapshots' | 'restoration' | 'recommendations'

interface PreparationStep {
  step_type: string
  target: string
  reason: string
  priority: number
}

interface PreparationPlan {
  plan_id: string
  mode: string
  template_id: string
  profile_mode: string
  intent: string
  steps: PreparationStep[]
  context_summary: Record<string, unknown>
  active_work_packets: Record<string, unknown>[]
  continuity_context: Record<string, unknown>
  projection_context: Record<string, unknown>
  recommendations: Record<string, unknown>[]
  status: string
  created_at: number
}

interface Template {
  template_id: string
  mode: string
  label: string
  required_applications: string[]
  required_repositories: string[]
  recommended_cockpit_panels: string[]
  recommended_browser_tabs: string[]
  required_context_sources: string[]
  description: string
}

interface Snapshot {
  snapshot_id: string
  trigger: string
  open_objectives: string[]
  active_profile: string
  active_session_id: string
  active_loops: string[]
  active_work_packets: Record<string, unknown>[]
  operator_notes: string
  created_at: number
}

interface Recommendation {
  recommendation_id: string
  recommendation_type: string
  title: string
  description: string
  source_system: string
  priority: number
  created_at: number
}

interface WorkstationState {
  mode: string
  template_id: string
  templates_available: number
  latest_snapshot: Snapshot | null
}

function getStepTypeBadge(type: string): string {
  const map: Record<string, string> = {
    application: 'bg-blue-900/50 text-blue-300',
    repository: 'bg-purple-900/50 text-purple-300',
    browser_tab: 'bg-green-900/50 text-green-300',
    cockpit_panel: 'bg-yellow-900/50 text-yellow-300',
    work_packet: 'bg-red-900/50 text-red-300',
    context_source: 'bg-cyan-900/50 text-cyan-300',
  }
  return map[type] || 'bg-zinc-800 text-zinc-300'
}

function getRecTypeBadge(type: string): string {
  const map: Record<string, string> = {
    resume_work: 'bg-blue-900/50 text-blue-300',
    review_blocked: 'bg-red-900/50 text-red-300',
    approve_proposal: 'bg-yellow-900/50 text-yellow-300',
    investigate_risk: 'bg-orange-900/50 text-orange-300',
    continue_draft: 'bg-green-900/50 text-green-300',
    address_gap: 'bg-purple-900/50 text-purple-300',
    follow_up: 'bg-cyan-900/50 text-cyan-300',
  }
  return map[type] || 'bg-zinc-800 text-zinc-300'
}

function formatTimestamp(ts: number): string {
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleString()
}

function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
      <div className="text-xs text-zinc-500 uppercase tracking-wider">{label}</div>
      <div className="text-xl font-bold text-zinc-100 mt-1">{value}</div>
      {sub && <div className="text-xs text-zinc-500 mt-1">{sub}</div>}
    </div>
  )
}

export function WorkstationPanel() {
  const [tab, setTab] = useState<Tab>('preparation')
  const [state, setState] = useState<WorkstationState | null>(null)
  const [templates, setTemplates] = useState<Template[]>([])
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [intentInput, setIntentInput] = useState('')
  const [prepResult, setPrepResult] = useState<PreparationPlan | null>(null)
  const [restoreResult, setRestoreResult] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const [stateRes, tplRes, snapRes, recRes] = await Promise.all([
        fetchApi('/workstation/state'),
        fetchApi('/workstation/templates'),
        fetchApi('/workstation/snapshots?limit=20'),
        fetchApi('/workstation/recommendations'),
      ])
      if (stateRes?.success) setState(stateRes.state)
      if (tplRes?.success) setTemplates(tplRes.templates || [])
      if (snapRes?.success) setSnapshots(snapRes.snapshots || [])
      if (recRes?.success) setRecommendations(recRes.recommendations || [])
    } catch { /* swallow */ }
  }, [])

  useEffect(() => { refresh() }, [refresh])
  useEffect(() => { const id = setInterval(refresh, 15000); return () => clearInterval(id) }, [refresh])

  const handlePrepare = async () => {
    if (!intentInput.trim() || loading) return
    setLoading(true)
    try {
      const res = await fetchApi('/workstation/prepare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intent: intentInput }),
      })
      if (res?.success) setPrepResult(res.plan)
    } catch { /* swallow */ }
    setLoading(false)
  }

  const handleSnapshot = async () => {
    setLoading(true)
    try {
      await fetchApi('/workstation/snapshots/take', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trigger: 'manual', operator_notes: '' }),
      })
      await refresh()
    } catch { /* swallow */ }
    setLoading(false)
  }

  const handleRestore = async (snapshotId: string) => {
    setLoading(true)
    try {
      const res = await fetchApi('/workstation/restore', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ snapshot_id: snapshotId }),
      })
      if (res?.success) {
        setRestoreResult(res.plan)
        setTab('restoration')
      }
    } catch { /* swallow */ }
    setLoading(false)
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'preparation', label: 'Preparation' },
    { key: 'templates', label: 'Templates' },
    { key: 'snapshots', label: 'Snapshots' },
    { key: 'restoration', label: 'Restoration' },
    { key: 'recommendations', label: 'Recommendations' },
  ]

  return (
    <div className="h-full flex flex-col bg-zinc-950 text-zinc-100 overflow-hidden">
      <div className="flex items-center gap-4 px-4 py-3 border-b border-zinc-800">
        <h2 className="text-lg font-semibold">Workstation</h2>
        <div className="flex gap-1 ml-auto">
          {tabs.map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-3 py-1 text-xs rounded transition-colors ${
                tab === t.key
                  ? 'bg-zinc-700 text-zinc-100'
                  : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-4 gap-3 px-4 py-3 border-b border-zinc-800">
        <KpiCard label="Mode" value={state?.mode || '—'} />
        <KpiCard label="Templates" value={String(state?.templates_available || 0)} />
        <KpiCard label="Snapshots" value={String(snapshots.length)} />
        <KpiCard label="Recommendations" value={String(recommendations.length)} />
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3">
        {tab === 'preparation' && (
          <div className="space-y-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={intentInput}
                onChange={e => setIntentInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handlePrepare()}
                placeholder="What do you want to work on?"
                className="flex-1 bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-500"
              />
              <button
                onClick={handlePrepare}
                disabled={loading || !intentInput.trim()}
                className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Planning...' : 'Prepare'}
              </button>
            </div>

            <div className="grid grid-cols-3 gap-2 text-xs text-zinc-500">
              {['Work on Operator', 'Write content for the newsletter', 'Review revenue forecast',
                'Produce a new beat', 'Research the API benchmark', 'Configure backup schedule'
              ].map(ex => (
                <button key={ex} onClick={() => setIntentInput(ex)}
                  className="text-left px-2 py-1 rounded bg-zinc-900 hover:bg-zinc-800 truncate">{ex}</button>
              ))}
            </div>

            {prepResult && (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">Plan: {prepResult.plan_id}</span>
                  <span className="px-2 py-0.5 text-xs rounded bg-green-900/50 text-green-300">{prepResult.mode}</span>
                  <span className="px-2 py-0.5 text-xs rounded bg-zinc-800 text-zinc-400">{prepResult.status}</span>
                </div>

                <div className="text-xs text-zinc-500">
                  Template: {prepResult.template_id} | Confidence: {(prepResult.context_summary as Record<string, number>)?.classification_confidence ?? '—'}
                </div>

                <div className="space-y-1">
                  <div className="text-xs font-medium text-zinc-400 uppercase">Preparation Steps ({prepResult.steps.length})</div>
                  {prepResult.steps.map((s, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs bg-zinc-900 rounded px-3 py-2">
                      <span className={`px-1.5 py-0.5 rounded ${getStepTypeBadge(s.step_type)}`}>{s.step_type}</span>
                      <span className="text-zinc-100 font-medium">{s.target}</span>
                      <span className="text-zinc-500 ml-auto">{s.reason}</span>
                    </div>
                  ))}
                </div>

                {prepResult.active_work_packets.length > 0 && (
                  <div className="space-y-1">
                    <div className="text-xs font-medium text-zinc-400 uppercase">Active Work Packets ({prepResult.active_work_packets.length})</div>
                    {prepResult.active_work_packets.map((wp, i) => (
                      <div key={i} className="text-xs bg-zinc-900 rounded px-3 py-2 text-zinc-300">
                        {(wp as Record<string, string>).title || (wp as Record<string, string>).packet_id || `Packet ${i + 1}`}
                      </div>
                    ))}
                  </div>
                )}

                {prepResult.recommendations.length > 0 && (
                  <div className="space-y-1">
                    <div className="text-xs font-medium text-zinc-400 uppercase">Recommendations ({prepResult.recommendations.length})</div>
                    {prepResult.recommendations.map((rec, i) => (
                      <div key={i} className="text-xs bg-zinc-900 rounded px-3 py-2 text-zinc-300">
                        {(rec as Record<string, string>).title || `Recommendation ${i + 1}`}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {tab === 'templates' && (
          <div className="space-y-3">
            {templates.map(tpl => (
              <div key={tpl.template_id} className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-sm font-bold text-zinc-100">{tpl.label}</span>
                  <span className="px-2 py-0.5 text-xs rounded bg-zinc-800 text-zinc-400">{tpl.template_id}</span>
                </div>
                <div className="text-xs text-zinc-500 mb-3">{tpl.description}</div>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <div className="text-zinc-500 font-medium mb-1">Applications</div>
                    <div className="flex flex-wrap gap-1">
                      {tpl.required_applications.map(a => (
                        <span key={a} className="px-1.5 py-0.5 bg-blue-900/30 text-blue-300 rounded">{a}</span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <div className="text-zinc-500 font-medium mb-1">Cockpit Panels</div>
                    <div className="flex flex-wrap gap-1">
                      {tpl.recommended_cockpit_panels.map(p => (
                        <span key={p} className="px-1.5 py-0.5 bg-yellow-900/30 text-yellow-300 rounded">{p}</span>
                      ))}
                    </div>
                  </div>
                  {tpl.required_repositories.length > 0 && (
                    <div>
                      <div className="text-zinc-500 font-medium mb-1">Repositories</div>
                      <div className="flex flex-wrap gap-1">
                        {tpl.required_repositories.map(r => (
                          <span key={r} className="px-1.5 py-0.5 bg-purple-900/30 text-purple-300 rounded">{r}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  <div>
                    <div className="text-zinc-500 font-medium mb-1">Context Sources</div>
                    <div className="flex flex-wrap gap-1">
                      {tpl.required_context_sources.map(c => (
                        <span key={c} className="px-1.5 py-0.5 bg-cyan-900/30 text-cyan-300 rounded">{c}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === 'snapshots' && (
          <div className="space-y-3">
            <div className="flex justify-end">
              <button
                onClick={handleSnapshot}
                disabled={loading}
                className="px-3 py-1.5 text-xs bg-zinc-700 text-zinc-100 rounded hover:bg-zinc-600 disabled:opacity-50"
              >
                Take Snapshot
              </button>
            </div>
            {snapshots.length === 0 ? (
              <div className="text-sm text-zinc-500 text-center py-8">No snapshots yet</div>
            ) : snapshots.map(snap => (
              <div key={snap.snapshot_id} className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-mono text-zinc-400">{snap.snapshot_id}</span>
                  <span className="px-2 py-0.5 text-xs rounded bg-zinc-800 text-zinc-400">{snap.trigger}</span>
                  <span className="text-xs text-zinc-500 ml-auto">{formatTimestamp(snap.created_at)}</span>
                </div>
                {snap.operator_notes && (
                  <div className="text-xs text-zinc-300 mb-2">{snap.operator_notes}</div>
                )}
                <div className="flex gap-4 text-xs text-zinc-500 mb-2">
                  <span>Profile: {snap.active_profile || '—'}</span>
                  <span>Objectives: {snap.open_objectives?.length || 0}</span>
                  <span>Packets: {snap.active_work_packets?.length || 0}</span>
                  <span>Loops: {snap.active_loops?.length || 0}</span>
                </div>
                <button
                  onClick={() => handleRestore(snap.snapshot_id)}
                  className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-500"
                >
                  Restore
                </button>
              </div>
            ))}
          </div>
        )}

        {tab === 'restoration' && (
          <div className="space-y-3">
            {!restoreResult ? (
              <div className="text-sm text-zinc-500 text-center py-8">
                Select a snapshot to restore, or click Restore on the Snapshots tab
              </div>
            ) : (
              <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-3">
                <div className="text-sm font-medium text-zinc-100">
                  Restoration Plan: {(restoreResult as Record<string, string>).restoration_id}
                </div>
                <div className="text-xs text-zinc-500">
                  Source: {(restoreResult as Record<string, string>).source_snapshot_id || 'fresh context'} |
                  Mode: {(restoreResult as Record<string, string>).target_mode}
                </div>

                {(restoreResult as Record<string, string>).operator_notes && (
                  <div className="text-xs text-zinc-300 bg-zinc-800/50 rounded p-2">
                    {(restoreResult as Record<string, string>).operator_notes}
                  </div>
                )}

                {((restoreResult as Record<string, unknown[]>).objectives_to_restore || []).length > 0 && (
                  <div>
                    <div className="text-xs font-medium text-zinc-400 uppercase mb-1">Objectives to Restore</div>
                    {((restoreResult as Record<string, string[]>).objectives_to_restore).map((obj, i) => (
                      <div key={i} className="text-xs text-zinc-300 bg-zinc-800/30 rounded px-2 py-1 mb-1">{obj}</div>
                    ))}
                  </div>
                )}

                {((restoreResult as Record<string, unknown[]>).work_packets_to_load || []).length > 0 && (
                  <div>
                    <div className="text-xs font-medium text-zinc-400 uppercase mb-1">Work Packets to Load</div>
                    {((restoreResult as Record<string, Record<string, string>[]>).work_packets_to_load).map((wp, i) => (
                      <div key={i} className="text-xs text-zinc-300 bg-zinc-800/30 rounded px-2 py-1 mb-1">
                        {wp.title || wp.packet_id || `Packet ${i + 1}`}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {tab === 'recommendations' && (
          <div className="space-y-2">
            {recommendations.length === 0 ? (
              <div className="text-sm text-zinc-500 text-center py-8">No recommendations available</div>
            ) : recommendations.map(rec => (
              <div key={rec.recommendation_id} className="flex items-start gap-3 bg-zinc-900 border border-zinc-800 rounded-lg p-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-1.5 py-0.5 text-xs rounded ${getRecTypeBadge(rec.recommendation_type)}`}>
                      {rec.recommendation_type.replace(/_/g, ' ')}
                    </span>
                    <span className="text-xs text-zinc-500">P{rec.priority}</span>
                  </div>
                  <div className="text-sm text-zinc-100">{rec.title}</div>
                  {rec.description && <div className="text-xs text-zinc-500 mt-1">{rec.description}</div>}
                  <div className="text-xs text-zinc-600 mt-1">Source: {rec.source_system}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
