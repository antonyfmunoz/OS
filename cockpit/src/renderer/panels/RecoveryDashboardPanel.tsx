import { useEffect, useState } from 'react'
import { useRecoveryDashboardStore } from '../stores/recoveryDashboardStore'

const TABS = ['overview', 'queue', 'detail', 'actions', 'history'] as const
type Tab = typeof TABS[number]

const stateColor: Record<string, string> = {
  failed: 'text-red-400',
  blocked: 'text-orange-400',
  interrupted: 'text-yellow-400',
  resumable: 'text-blue-400',
  active: 'text-green-400',
  complete: 'text-gray-400',
}

const stateBg: Record<string, string> = {
  failed: 'bg-red-900/30 border-red-800',
  blocked: 'bg-orange-900/30 border-orange-800',
  interrupted: 'bg-yellow-900/30 border-yellow-800',
  resumable: 'bg-blue-900/30 border-blue-800',
}

function OverviewTab() {
  const { summary } = useRecoveryDashboardStore()
  if (!summary) return <div className="wv-card p-4 text-gray-400">Loading summary...</div>
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Recoverable</div>
          <div className="text-lg font-bold text-white">{summary.total_recoverable}</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Failed</div>
          <div className="text-lg font-bold text-red-400">{summary.failed}</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Blocked</div>
          <div className="text-lg font-bold text-orange-400">{summary.blocked}</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Interrupted</div>
          <div className="text-lg font-bold text-yellow-400">{summary.interrupted}</div>
        </div>
      </div>
      <div className="wv-card p-3">
        <div className="text-xs text-gray-400 mb-1">Runtime Status</div>
        <div className={`text-sm ${summary.runtime_available ? 'text-green-400' : 'text-red-400'}`}>
          {summary.runtime_available ? 'Available' : 'Unavailable — recovery actions disabled'}
        </div>
      </div>
      {summary.total_recoverable === 0 && (
        <div className="wv-card p-4 text-center text-gray-400">
          No items need recovery. System healthy.
        </div>
      )}
    </div>
  )
}

function QueueTab() {
  const { queue, loading, fetchQueueDetail } = useRecoveryDashboardStore()

  if (loading) return <div className="text-gray-400 text-sm">Loading...</div>
  if (queue.length === 0) return <div className="wv-card p-4 text-gray-400">No items in recovery queue</div>

  return (
    <div className="space-y-2">
      {queue.map((item) => (
        <div
          key={item.work_id}
          className={`wv-card p-3 cursor-pointer hover:border-blue-500 transition-colors border ${stateBg[item.state] || ''}`}
          onClick={() => fetchQueueDetail(item.work_id)}
        >
          <div className="flex justify-between items-start">
            <div className="text-sm font-mono text-gray-300">{item.work_id}</div>
            <span className={`text-xs px-2 py-0.5 rounded bg-gray-800 ${stateColor[item.state] || 'text-gray-400'}`}>
              {item.state}
            </span>
          </div>
          <div className="flex gap-3 mt-2 text-xs text-gray-500">
            <span>{item.actions.length} action{item.actions.length !== 1 ? 's' : ''} available</span>
            <span>{new Date(item.assessed_at * 1000).toLocaleString()}</span>
          </div>
        </div>
      ))}
    </div>
  )
}

function DetailTab() {
  const { selectedItem } = useRecoveryDashboardStore()
  if (!selectedItem) return <div className="wv-card p-4 text-gray-400">Select an item from the Queue tab</div>

  const item = selectedItem
  return (
    <div className="space-y-4">
      <div className="wv-card p-4">
        <div className="flex justify-between items-start mb-3">
          <div className="text-sm font-mono text-white">{item.work_id}</div>
          <span className={`text-xs px-2 py-0.5 rounded bg-gray-800 ${stateColor[item.state] || 'text-gray-400'}`}>
            {item.state}
          </span>
        </div>
        <div className="text-xs text-gray-400">
          Assessed: {new Date(item.assessed_at * 1000).toLocaleString()}
        </div>
      </div>

      {item.actions.length > 0 && (
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400 mb-2">Available Recovery Actions</div>
          <div className="space-y-2">
            {item.actions.map((a, i) => (
              <div key={i} className="bg-gray-800 p-2 rounded">
                <div className="flex justify-between items-center">
                  <span className="text-xs font-bold text-gray-300 uppercase">{a.action}</span>
                  {a.auto_recoverable && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-900 text-green-300">AUTO</span>
                  )}
                </div>
                <div className="text-xs text-gray-400 mt-1">{a.reason}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {item.journal_entries && item.journal_entries.length > 0 && (
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400 mb-2">Journal Entries</div>
          <div className="space-y-1">
            {item.journal_entries.map((e, i) => (
              <div key={i} className="flex justify-between text-xs bg-gray-800 p-2 rounded">
                <div>
                  <span className="text-gray-300 font-bold">{e.phase}</span>
                  {e.source && <span className="text-gray-500 ml-2">({e.source})</span>}
                </div>
                <span className="text-gray-500">{new Date(e.timestamp * 1000).toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function ActionsTab() {
  const { selectedItem, executeAction, actionResult, error } = useRecoveryDashboardStore()
  const [confirmAction, setConfirmAction] = useState<string | null>(null)
  const [reason, setReason] = useState('')

  if (!selectedItem) return <div className="wv-card p-4 text-gray-400">Select an item from the Queue tab</div>

  const handleExecute = async (actionType: string) => {
    await executeAction(selectedItem.work_id, actionType, reason)
    setConfirmAction(null)
    setReason('')
  }

  return (
    <div className="space-y-4">
      <div className="wv-card p-3">
        <div className="text-xs text-gray-400 mb-1">Recovery Target</div>
        <div className="text-sm font-mono text-white">{selectedItem.work_id}</div>
        <div className={`text-xs mt-1 ${stateColor[selectedItem.state] || 'text-gray-400'}`}>{selectedItem.state}</div>
      </div>

      {actionResult && (
        <div className="wv-card p-3 border-green-700">
          <div className="text-xs text-green-400">{actionResult}</div>
        </div>
      )}

      {error && (
        <div className="wv-card p-3 border-red-700">
          <div className="text-xs text-red-400">{error}</div>
        </div>
      )}

      <div className="space-y-2">
        {selectedItem.actions.map((a, i) => (
          <div key={i} className="wv-card p-3">
            <div className="flex justify-between items-center mb-2">
              <div>
                <span className="text-xs font-bold text-gray-300 uppercase">{a.action}</span>
                {a.auto_recoverable && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-900 text-green-300 ml-2">AUTO</span>
                )}
              </div>
              {confirmAction === a.action ? (
                <div className="flex gap-2">
                  <button
                    onClick={() => handleExecute(a.action)}
                    className="px-2 py-1 text-xs bg-red-700 hover:bg-red-600 text-white rounded"
                  >
                    Confirm
                  </button>
                  <button
                    onClick={() => setConfirmAction(null)}
                    className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-white rounded"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmAction(a.action)}
                  className="px-2 py-1 text-xs bg-blue-700 hover:bg-blue-600 text-white rounded"
                >
                  Execute
                </button>
              )}
            </div>
            <div className="text-xs text-gray-400">{a.reason}</div>
            {confirmAction === a.action && (
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Reason (optional)"
                className="w-full mt-2 bg-gray-800 border border-gray-600 rounded p-2 text-xs text-gray-300"
                rows={2}
              />
            )}
          </div>
        ))}
      </div>

      {selectedItem.actions.length === 0 && (
        <div className="wv-card p-4 text-gray-400">No recovery actions available for this item</div>
      )}
    </div>
  )
}

function HistoryTab() {
  const { actionHistory } = useRecoveryDashboardStore()
  if (actionHistory.length === 0) return <div className="wv-card p-4 text-gray-400">No recovery history</div>
  return (
    <div className="space-y-2">
      {actionHistory.map((entry, i) => (
        <div key={i} className="wv-card p-3">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-xs font-bold text-gray-300 uppercase">{entry.action_type}</span>
              <span className="text-xs font-mono text-gray-400 ml-2">{entry.work_id}</span>
            </div>
            <span className="text-xs text-gray-500">{new Date(entry.timestamp * 1000).toLocaleString()}</span>
          </div>
          {entry.reason && <div className="text-xs text-gray-400 mt-1">{entry.reason}</div>}
          <div className="text-xs text-gray-500 mt-1">State before: {entry.state_before}</div>
        </div>
      ))}
    </div>
  )
}

export function RecoveryDashboardPanel() {
  const [tab, setTab] = useState<Tab>('overview')
  const { fetchSummary, fetchQueue, fetchHistory } = useRecoveryDashboardStore()

  useEffect(() => {
    fetchSummary()
    fetchQueue()
    fetchHistory()
  }, [])

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 px-4 py-2 border-b border-gray-700">
        <h2 className="text-sm font-bold text-white">Recovery Dashboard</h2>
        <div className="flex gap-1 ml-auto">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-2 py-1 text-xs rounded ${tab === t ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {tab === 'overview' && <OverviewTab />}
        {tab === 'queue' && <QueueTab />}
        {tab === 'detail' && <DetailTab />}
        {tab === 'actions' && <ActionsTab />}
        {tab === 'history' && <HistoryTab />}
      </div>
    </div>
  )
}
