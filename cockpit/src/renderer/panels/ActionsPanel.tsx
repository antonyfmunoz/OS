import { useState, useEffect } from 'react'
import { useActionsStore, ActionDefinition, ActionResult } from '../stores/actionsStore'
import { usePolling } from '../hooks/usePolling'
import { ConnectionBanner } from '../components/ConnectionBanner'
import { useRealtimeStore } from '../stores/realtimeStore'

const RISK_COLORS: Record<string, string> = {
  safe: 'wv-badge-ok',
  low: 'wv-badge-ok',
  medium: 'wv-badge-warn',
  high: 'wv-badge-danger',
  critical: 'wv-badge-danger',
}

const STATUS_COLORS: Record<string, string> = {
  completed: 'wv-badge-ok',
  executing: 'wv-badge-warn',
  awaiting_approval: 'wv-badge-warn',
  failed: 'wv-badge-danger',
  blocked: 'wv-badge-danger',
  pending: 'wv-text-muted',
}

const CATEGORY_ORDER = ['observation', 'test', 'container', 'service', 'build', 'workspace']

export function ActionsPanel() {
  const actions = useActionsStore((s) => s.actions)
  const history = useActionsStore((s) => s.history)
  const loading = useActionsStore((s) => s.loading)
  const executing = useActionsStore((s) => s.executing)
  const error = useActionsStore((s) => s.error)
  const fetchCatalog = useActionsStore((s) => s.fetchCatalog)
  const executeAction = useActionsStore((s) => s.executeAction)
  const approveAction = useActionsStore((s) => s.approveAction)
  const fetchHistory = useActionsStore((s) => s.fetchHistory)
  const realtimeStatus = useRealtimeStore((s) => s.status)

  const [params, setParams] = useState<Record<string, Record<string, string>>>({})
  const [lastResult, setLastResult] = useState<ActionResult | null>(null)
  const [tab, setTab] = useState<'catalog' | 'history'>('catalog')

  usePolling(() => { fetchCatalog(); fetchHistory() },
    realtimeStatus === 'connected' ? 10000 : 5000)

  const grouped = CATEGORY_ORDER
    .map(cat => ({
      category: cat,
      items: actions.filter(a => a.category === cat),
    }))
    .filter(g => g.items.length > 0)

  const handleExecute = async (action: ActionDefinition) => {
    const actionParams = params[action.action_id] ?? {}
    const result = await executeAction(action.action_id, actionParams)
    if (result) setLastResult(result)
  }

  const handleParamChange = (actionId: string, name: string, value: string) => {
    setParams(prev => ({
      ...prev,
      [actionId]: { ...(prev[actionId] ?? {}), [name]: value },
    }))
  }

  return (
    <div className="wv-panel">
      <div className="wv-panel-header">
        <h2 className="wv-panel-title">Actions</h2>
        <div className="wv-tabs">
          <button className={`wv-tab ${tab === 'catalog' ? 'wv-tab-active' : ''}`}
            onClick={() => setTab('catalog')}>Catalog ({actions.length})</button>
          <button className={`wv-tab ${tab === 'history' ? 'wv-tab-active' : ''}`}
            onClick={() => setTab('history')}>History ({history.length})</button>
        </div>
      </div>

      <ConnectionBanner />
      {error && <div className="wv-alert wv-alert-danger">{error}</div>}

      {lastResult && (
        <div className={`wv-alert ${lastResult.status === 'completed' ? 'wv-alert-ok' : lastResult.status === 'awaiting_approval' ? 'wv-alert-warn' : 'wv-alert-danger'}`}>
          <strong>{lastResult.action_id}</strong>: {lastResult.status}
          {lastResult.error && <span> — {lastResult.error}</span>}
          {lastResult.status === 'awaiting_approval' && (
            <button className="wv-btn wv-btn-sm wv-btn-warn"
              onClick={() => { approveAction(lastResult.execution_plan_id); setLastResult(null) }}
              style={{ marginLeft: 8 }}>Approve</button>
          )}
          <button className="wv-btn wv-btn-sm" onClick={() => setLastResult(null)}
            style={{ marginLeft: 4 }}>✕</button>
        </div>
      )}

      {tab === 'catalog' && (
        <div className="wv-grid">
          {loading && actions.length === 0 && <div className="wv-text-muted">Loading catalog…</div>}
          {grouped.map(({ category, items }) => (
            <div key={category} className="wv-section">
              <h3 className="wv-section-title">{category.toUpperCase()}</h3>
              {items.map(action => (
                <ActionCard key={action.action_id} action={action}
                  params={params[action.action_id] ?? {}}
                  onParamChange={(n, v) => handleParamChange(action.action_id, n, v)}
                  onExecute={() => handleExecute(action)}
                  isExecuting={executing === action.action_id} />
              ))}
            </div>
          ))}
        </div>
      )}

      {tab === 'history' && (
        <div className="wv-list">
          {history.length === 0 && <div className="wv-text-muted">No actions executed yet</div>}
          {history.map(r => (
            <div key={r.request_id} className="wv-list-item">
              <span className={STATUS_COLORS[r.status] ?? ''}>{r.status}</span>
              <strong style={{ marginLeft: 8 }}>{r.action_id}</strong>
              {r.error && <span className="wv-text-danger" style={{ marginLeft: 8 }}>{r.error}</span>}
              {r.status === 'awaiting_approval' && (
                <button className="wv-btn wv-btn-sm wv-btn-warn"
                  onClick={() => approveAction(r.execution_plan_id)}
                  style={{ marginLeft: 8 }}>Approve</button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ActionCard({ action, params, onParamChange, onExecute, isExecuting }: {
  action: ActionDefinition
  params: Record<string, string>
  onParamChange: (name: string, value: string) => void
  onExecute: () => void
  isExecuting: boolean
}) {
  const hasRequiredParams = action.parameters
    .filter(p => p.required)
    .every(p => (params[p.name] ?? p.default))

  const preconditionsMet = !action.precondition_state
    || action.precondition_state.every(p => p.passed)

  return (
    <div className="wv-card">
      <div className="wv-card-header">
        <span className="wv-card-title">{action.name}</span>
        <span className={RISK_COLORS[action.risk_level] ?? ''}>{action.risk_level}</span>
      </div>
      <div className="wv-card-body">
        <div className="wv-text-muted" style={{ fontSize: '0.85em' }}>{action.description}</div>

        {action.parameters.filter(p => p.required || !p.default).map(p => (
          <div key={p.name} style={{ marginTop: 4 }}>
            <label className="wv-label">{p.name}{p.required ? ' *' : ''}</label>
            {p.choices.length > 0 ? (
              <select className="wv-input" value={params[p.name] ?? p.default}
                onChange={e => onParamChange(p.name, e.target.value)}>
                <option value="">Select…</option>
                {p.choices.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            ) : (
              <input className="wv-input" type="text" placeholder={p.description || p.name}
                value={params[p.name] ?? ''} onChange={e => onParamChange(p.name, e.target.value)} />
            )}
          </div>
        ))}

        {!preconditionsMet && (
          <div className="wv-text-danger" style={{ fontSize: '0.8em', marginTop: 4 }}>
            Precondition not met
          </div>
        )}
      </div>
      <div className="wv-card-footer">
        <button className="wv-btn wv-btn-primary" onClick={onExecute}
          disabled={isExecuting || !hasRequiredParams || !preconditionsMet}>
          {isExecuting ? 'Executing…' : action.risk_level === 'medium' || action.risk_level === 'high' ? 'Request' : 'Execute'}
        </button>
      </div>
    </div>
  )
}
