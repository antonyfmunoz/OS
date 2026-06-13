import { useEffect, useState, useCallback } from 'react'
import {
  Activity,
  Play,
  Pause,
  Square,
  RefreshCw,
  Clock,
  AlertTriangle,
  TrendingUp,
  Zap,
  Eye,
  ChevronRight,
  CheckCircle2,
  XCircle,
  BarChart3,
  Target,
  ThumbsUp,
  ThumbsDown,
} from 'lucide-react'
import { useOperatorLoopStore } from '../stores/operatorLoopStore'
import type { TickStatusData, TickRecord, CandidateItem, DriftWarningData } from '../stores/operatorLoopStore'

type Tab = 'command' | 'candidates' | 'drift' | 'history'

const FREQ_OPTIONS = [
  { value: '30s', label: '30 seconds' },
  { value: '1m', label: '1 minute' },
  { value: '5m', label: '5 minutes' },
  { value: '15m', label: '15 minutes' },
  { value: 'manual', label: 'Manual only' },
]

const PROFILE_OPTIONS = [
  'developer', 'research', 'music', 'design',
  'content', 'command_center', 'finance', 'learning',
]

const DRIFT_COLORS: Record<string, string> = {
  critical: 'text-red-400 bg-red-400/10 border-red-400/30',
  alert: 'text-orange-400 bg-orange-400/10 border-orange-400/30',
  warning: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30',
}

const LIFECYCLE_COLORS: Record<string, string> = {
  proposed: 'text-blue-400 bg-blue-400/10',
  reviewed: 'text-purple-400 bg-purple-400/10',
  accepted: 'text-green-400 bg-green-400/10',
  rejected: 'text-red-400 bg-red-400/10',
  expired: 'text-text-tertiary bg-surface-raised',
  executed: 'text-emerald-400 bg-emerald-400/10',
}

function KpiCard({ label, value, icon: Icon, color = 'text-text-primary' }: {
  label: string; value: string | number; icon: typeof Activity; color?: string
}) {
  return (
    <div className="bg-surface-raised border border-border rounded-lg p-3">
      <div className="flex items-center gap-2 mb-1">
        <Icon className={`w-4 h-4 ${color}`} />
        <span className="text-xs text-text-tertiary">{label}</span>
      </div>
      <span className={`text-lg font-mono font-bold ${color}`}>{value}</span>
    </div>
  )
}

export function TickLoopPanel() {
  const [activeTab, setActiveTab] = useState<Tab>('command')
  const {
    tickStatus, tickStrategicState, tickCandidates, tickDriftWarnings, tickHistory,
    tickLoading,
    fetchTickStatus, fetchTickState, executeTick, startTick, stopTick,
    pauseTick, resumeTick, setTickFrequency, setTickProfiles,
    fetchTickCandidates, acceptCandidate, rejectCandidate,
    fetchTickDrift, fetchTickHistory,
  } = useOperatorLoopStore()

  const refresh = useCallback(() => {
    fetchTickStatus()
    fetchTickState()
    fetchTickCandidates()
    fetchTickDrift()
    fetchTickHistory()
  }, [fetchTickStatus, fetchTickState, fetchTickCandidates, fetchTickDrift, fetchTickHistory])

  useEffect(() => { refresh() }, [refresh])

  const tabs: { id: Tab; label: string; count?: number }[] = [
    { id: 'command', label: 'Command Center' },
    { id: 'candidates', label: 'Candidates', count: tickCandidates.filter(c => c.lifecycle === 'proposed').length },
    { id: 'drift', label: 'Drift', count: tickDriftWarnings.length },
    { id: 'history', label: 'History', count: tickHistory.length },
  ]

  return (
    <div className="h-full flex flex-col bg-surface text-text-primary overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-accent-primary" />
          <h1 className="text-lg font-semibold">Strategic Tick Loop</h1>
          {tickStatus?.running && !tickStatus?.paused && (
            <span className="flex items-center gap-1 text-xs text-green-400 bg-green-400/10 px-2 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
              Running
            </span>
          )}
          {tickStatus?.paused && (
            <span className="text-xs text-yellow-400 bg-yellow-400/10 px-2 py-0.5 rounded-full">Paused</span>
          )}
          {tickStatus && !tickStatus.running && !tickStatus.paused && (
            <span className="text-xs text-text-tertiary bg-surface-raised px-2 py-0.5 rounded-full">Stopped</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => refresh()} className="p-1.5 rounded hover:bg-surface-raised text-text-secondary" title="Refresh">
            <RefreshCw className={`w-4 h-4 ${tickLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="flex border-b border-border px-4">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-2 text-sm border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-accent-primary text-accent-primary'
                : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
          >
            {tab.label}
            {tab.count !== undefined && tab.count > 0 && (
              <span className="ml-1.5 text-xs bg-accent-primary/20 text-accent-primary px-1.5 py-0.5 rounded-full">
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {activeTab === 'command' && <CommandTab />}
        {activeTab === 'candidates' && <CandidatesTab />}
        {activeTab === 'drift' && <DriftTab />}
        {activeTab === 'history' && <HistoryTab />}
      </div>
    </div>
  )
}

function CommandTab() {
  const {
    tickStatus, tickStrategicState, tickLoading,
    executeTick, startTick, stopTick, pauseTick, resumeTick,
    setTickFrequency, setTickProfiles, fetchTickStatus, fetchTickState,
  } = useOperatorLoopStore()

  const [selectedFreq, setSelectedFreq] = useState(tickStatus?.frequency || '1m')
  const [selectedProfiles, setSelectedProfiles] = useState<string[]>(tickStatus?.active_profiles || [])

  useEffect(() => {
    if (tickStatus?.frequency) setSelectedFreq(tickStatus.frequency)
    if (tickStatus?.active_profiles) setSelectedProfiles(tickStatus.active_profiles)
  }, [tickStatus])

  const handleExecuteTick = async () => {
    await executeTick()
    fetchTickStatus()
    fetchTickState()
  }

  const handleFreqChange = async (freq: string) => {
    setSelectedFreq(freq)
    await setTickFrequency(freq)
  }

  const toggleProfile = async (profile: string) => {
    const next = selectedProfiles.includes(profile)
      ? selectedProfiles.filter(p => p !== profile)
      : [...selectedProfiles, profile]
    setSelectedProfiles(next)
    await setTickProfiles(next)
  }

  const state = tickStrategicState
  const lastTick = state?.tick?.last_tick as TickRecord | null

  return (
    <div className="space-y-4">
      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Cycle" value={tickStatus?.cycle_count ?? 0} icon={Activity} color="text-accent-primary" />
        <KpiCard label="Pending Candidates" value={tickStatus?.pending_candidates ?? 0} icon={Target} color="text-blue-400" />
        <KpiCard label="Drift Warnings" value={tickStatus?.drift_warning_count ?? 0} icon={AlertTriangle}
          color={tickStatus?.drift_warning_count ? 'text-orange-400' : 'text-text-tertiary'} />
        <KpiCard label="Operator" value={tickStatus?.operator_present ? 'Present' : 'Away'} icon={Eye}
          color={tickStatus?.operator_present ? 'text-green-400' : 'text-text-tertiary'} />
      </div>

      {/* Controls */}
      <div className="bg-surface-raised border border-border rounded-lg p-4">
        <h3 className="text-sm font-semibold mb-3">Tick Controls</h3>
        <div className="flex flex-wrap gap-2">
          {!tickStatus?.running && (
            <button onClick={() => startTick(selectedFreq)} className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600 hover:bg-green-500 text-white text-sm rounded">
              <Play className="w-3.5 h-3.5" /> Start
            </button>
          )}
          {tickStatus?.running && !tickStatus?.paused && (
            <button onClick={pauseTick} className="flex items-center gap-1.5 px-3 py-1.5 bg-yellow-600 hover:bg-yellow-500 text-white text-sm rounded">
              <Pause className="w-3.5 h-3.5" /> Pause
            </button>
          )}
          {tickStatus?.paused && (
            <button onClick={resumeTick} className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded">
              <Play className="w-3.5 h-3.5" /> Resume
            </button>
          )}
          {tickStatus?.running && (
            <button onClick={stopTick} className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600 hover:bg-red-500 text-white text-sm rounded">
              <Square className="w-3.5 h-3.5" /> Stop
            </button>
          )}
          <button onClick={handleExecuteTick} disabled={tickLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-accent-primary hover:bg-accent-primary/80 text-white text-sm rounded disabled:opacity-50">
            <Zap className="w-3.5 h-3.5" /> Execute Tick
          </button>
        </div>
      </div>

      {/* Frequency */}
      <div className="bg-surface-raised border border-border rounded-lg p-4">
        <h3 className="text-sm font-semibold mb-3">Frequency</h3>
        <div className="flex flex-wrap gap-2">
          {FREQ_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => handleFreqChange(opt.value)}
              className={`px-3 py-1.5 text-xs rounded border ${
                selectedFreq === opt.value
                  ? 'border-accent-primary bg-accent-primary/10 text-accent-primary'
                  : 'border-border text-text-secondary hover:border-text-tertiary'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Profile Modes */}
      <div className="bg-surface-raised border border-border rounded-lg p-4">
        <h3 className="text-sm font-semibold mb-3">Active Profiles</h3>
        <div className="flex flex-wrap gap-2">
          {PROFILE_OPTIONS.map(profile => (
            <button
              key={profile}
              onClick={() => toggleProfile(profile)}
              className={`px-3 py-1.5 text-xs rounded border capitalize ${
                selectedProfiles.includes(profile)
                  ? 'border-accent-primary bg-accent-primary/10 text-accent-primary'
                  : 'border-border text-text-secondary hover:border-text-tertiary'
              }`}
            >
              {profile.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Last Tick Summary */}
      {lastTick && (
        <div className="bg-surface-raised border border-border rounded-lg p-4">
          <h3 className="text-sm font-semibold mb-3">Last Tick</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div><span className="text-text-tertiary">Change:</span>{' '}
              <span className={lastTick.change_detected ? 'text-green-400' : 'text-text-tertiary'}>
                {lastTick.change_detected ? 'Yes' : 'No'}
              </span>
            </div>
            <div><span className="text-text-tertiary">Analysis:</span>{' '}
              <span className={lastTick.analysis_ran ? 'text-blue-400' : 'text-text-tertiary'}>
                {lastTick.analysis_ran ? 'Ran' : 'Skipped'}
              </span>
            </div>
            <div><span className="text-text-tertiary">Gaps:</span> {lastTick.gaps_found}</div>
            <div><span className="text-text-tertiary">Recs:</span> {lastTick.recommendations_generated}</div>
            <div><span className="text-text-tertiary">Candidates:</span> +{lastTick.candidates_added}</div>
            <div><span className="text-text-tertiary">Drift:</span> {lastTick.drift_warnings}</div>
            <div><span className="text-text-tertiary">Elapsed:</span> {lastTick.elapsed_ms.toFixed(0)}ms</div>
            <div><span className="text-text-tertiary">Skipped:</span> {lastTick.skipped_reason || '—'}</div>
          </div>
        </div>
      )}

      {/* Current Changes */}
      {state?.last_delta?.has_meaningful_change && (
        <div className="bg-surface-raised border border-border rounded-lg p-4">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-green-400" />
            Detected Changes
          </h3>
          <div className="space-y-1 text-xs">
            {state.last_delta.new_outcomes.length > 0 && (
              <div className="text-green-400">+{state.last_delta.new_outcomes.length} new outcomes</div>
            )}
            {state.last_delta.new_failures.length > 0 && (
              <div className="text-red-400">+{state.last_delta.new_failures.length} new failures</div>
            )}
            {state.last_delta.new_approvals > 0 && (
              <div className="text-blue-400">+{state.last_delta.new_approvals} new approvals</div>
            )}
            {state.last_delta.new_packets.length > 0 && (
              <div className="text-purple-400">+{state.last_delta.new_packets.length} new work packets</div>
            )}
            {state.last_delta.goal_changes.length > 0 && (
              <div className="text-yellow-400">{state.last_delta.goal_changes.length} goal changes</div>
            )}
            {state.last_delta.domain_changes.length > 0 && (
              <div className="text-orange-400">{state.last_delta.domain_changes.length} domain changes</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function CandidatesTab() {
  const { tickCandidates, fetchTickCandidates, acceptCandidate, rejectCandidate } = useOperatorLoopStore()

  useEffect(() => { fetchTickCandidates() }, [fetchTickCandidates])

  const pending = tickCandidates.filter(c => c.lifecycle === 'proposed')
  const decided = tickCandidates.filter(c => c.lifecycle !== 'proposed')

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold">Pending Candidates ({pending.length})</h3>
      {pending.length === 0 && (
        <div className="text-sm text-text-tertiary py-4 text-center">No pending candidates. Run a tick to generate.</div>
      )}
      {pending.map(item => (
        <div key={item.candidate_id} className="bg-surface-raised border border-border rounded-lg p-3">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="text-sm font-medium">{item.title}</div>
              <div className="flex items-center gap-3 mt-1 text-xs text-text-tertiary">
                <span>Domain: {item.domain || '—'}</span>
                <span>Priority: {item.priority_score.toFixed(1)}</span>
                <span>Impact: {item.impact || '—'}</span>
                <span>Risk: {item.risk || '—'}</span>
              </div>
              {item.dependencies.length > 0 && (
                <div className="text-xs text-text-tertiary mt-1">Deps: {item.dependencies.join(', ')}</div>
              )}
            </div>
            <div className="flex items-center gap-1.5 ml-3">
              <button onClick={async () => { await acceptCandidate(item.candidate_id); fetchTickCandidates() }}
                className="p-1.5 rounded hover:bg-green-400/10 text-green-400" title="Accept">
                <ThumbsUp className="w-4 h-4" />
              </button>
              <button onClick={async () => { await rejectCandidate(item.candidate_id); fetchTickCandidates() }}
                className="p-1.5 rounded hover:bg-red-400/10 text-red-400" title="Reject">
                <ThumbsDown className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      ))}

      {decided.length > 0 && (
        <>
          <h3 className="text-sm font-semibold mt-6">Decided ({decided.length})</h3>
          {decided.map(item => (
            <div key={item.candidate_id} className="bg-surface-raised border border-border rounded-lg p-3 opacity-60">
              <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-0.5 rounded ${LIFECYCLE_COLORS[item.lifecycle] || ''}`}>
                  {item.lifecycle}
                </span>
                <span className="text-sm">{item.title}</span>
                <span className="text-xs text-text-tertiary ml-auto">{item.domain}</span>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  )
}

function DriftTab() {
  const { tickDriftWarnings, fetchTickDrift } = useOperatorLoopStore()

  useEffect(() => { fetchTickDrift() }, [fetchTickDrift])

  if (tickDriftWarnings.length === 0) {
    return (
      <div className="text-sm text-text-tertiary py-8 text-center">
        No drift warnings. All goals are progressing.
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {tickDriftWarnings.map(warning => (
        <div key={warning.warning_id}
          className={`border rounded-lg p-4 ${DRIFT_COLORS[warning.severity] || 'border-border'}`}>
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <div className="text-sm font-medium">{warning.goal_title}</div>
              <div className="text-xs mt-1 opacity-80">{warning.message}</div>
              <div className="flex items-center gap-4 mt-2 text-xs opacity-60">
                <span>Domain: {warning.domain || '—'}</span>
                <span>Stagnant: {warning.days_stagnant.toFixed(0)} days</span>
                <span>Completion: {(warning.completion_ratio * 100).toFixed(0)}%</span>
                <span className="uppercase font-medium">{warning.severity}</span>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function HistoryTab() {
  const { tickHistory, fetchTickHistory } = useOperatorLoopStore()

  useEffect(() => { fetchTickHistory() }, [fetchTickHistory])

  if (tickHistory.length === 0) {
    return (
      <div className="text-sm text-text-tertiary py-8 text-center">
        No tick history. Execute a tick to begin.
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {[...tickHistory].reverse().map(tick => (
        <div key={tick.tick_id} className="bg-surface-raised border border-border rounded-lg p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-xs font-mono text-text-tertiary">#{tick.cycle_number}</span>
              {tick.change_detected ? (
                <span className="text-xs text-green-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> Changed
                </span>
              ) : (
                <span className="text-xs text-text-tertiary flex items-center gap-1">
                  <XCircle className="w-3 h-3" /> No change
                </span>
              )}
              {tick.analysis_ran && (
                <span className="text-xs text-blue-400">Analysis ran</span>
              )}
              {tick.skipped_reason && (
                <span className="text-xs text-yellow-400">Skipped: {tick.skipped_reason}</span>
              )}
            </div>
            <span className="text-xs text-text-tertiary">
              {new Date(tick.timestamp * 1000).toLocaleTimeString()}{' '}
              ({tick.elapsed_ms.toFixed(0)}ms)
            </span>
          </div>
          {tick.analysis_ran && (
            <div className="flex items-center gap-4 mt-1.5 text-xs text-text-tertiary">
              <span>Gaps: {tick.gaps_found}</span>
              <span>Recs: {tick.recommendations_generated}</span>
              <span>+{tick.candidates_added} candidates</span>
              {tick.drift_warnings > 0 && (
                <span className="text-orange-400">{tick.drift_warnings} drift</span>
              )}
              {tick.expired_candidates > 0 && (
                <span>{tick.expired_candidates} expired</span>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
