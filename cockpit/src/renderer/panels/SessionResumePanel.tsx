import { useEffect, useState } from 'react'
import { MonitorSmartphone, RefreshCw, Play, Pause, Save, X, Clock } from 'lucide-react'
import { useWorkstationSessionStore } from '../stores/workstationSessionStore'

type Tab = 'active' | 'history'

export function SessionResumePanel() {
  const [tab, setTab] = useState<Tab>('active')
  const {
    activeSession, history, lastCheckpoint, loading,
    fetchActiveSession, fetchHistory, startSession, checkpoint, pause, resumeSession, close,
  } = useWorkstationSessionStore()

  useEffect(() => {
    fetchActiveSession()
    fetchHistory()
  }, [])

  const refresh = () => {
    fetchActiveSession()
    fetchHistory()
  }

  const sessionId = activeSession
    ? ((activeSession as Record<string, unknown>).session as Record<string, unknown> | null)
      ? (((activeSession as Record<string, unknown>).session as Record<string, unknown>).id as string)
      : (activeSession as Record<string, unknown>).id as string ?? null
    : null

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between border-b border-border px-4 h-9 shrink-0">
        <div className="flex items-center gap-2">
          <MonitorSmartphone size={14} className="text-cyan" />
          <span className="text-[10px] font-mono text-cyan uppercase tracking-wider">Workstation Session</span>
          {sessionId && (
            <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-green-400/10 text-green-400">Active</span>
          )}
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="flex items-center gap-1 px-2 py-1 text-[10px] font-mono uppercase bg-cyan/10 text-cyan border border-cyan/30 rounded hover:bg-cyan/20 disabled:opacity-50"
        >
          <RefreshCw size={10} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      <div className="flex border-b border-border shrink-0">
        {(['active', 'history'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-[10px] font-mono uppercase transition-colors ${
              tab === t ? 'text-cyan border-b-2 border-cyan' : 'text-text-tertiary hover:text-text-secondary'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {loading && !activeSession && (
          <div className="text-text-tertiary text-xs font-mono">Loading session data...</div>
        )}

        {tab === 'active' && (
          <div className="space-y-4">
            {sessionId ? (
              <>
                <div className="bg-surface-raised border border-border rounded p-3">
                  <div className="text-text-tertiary text-[9px] font-mono uppercase mb-2">Active Session</div>
                  <div className="text-xs font-mono text-text-secondary whitespace-pre-wrap">
                    {JSON.stringify(activeSession, null, 2)}
                  </div>
                </div>

                <div className="flex gap-2 flex-wrap">
                  <button
                    onClick={() => checkpoint(sessionId)}
                    className="flex items-center gap-1 px-3 py-1.5 text-[10px] font-mono uppercase bg-blue-500/10 text-blue-400 border border-blue-500/30 rounded hover:bg-blue-500/20"
                  >
                    <Save size={10} /> Checkpoint
                  </button>
                  <button
                    onClick={() => pause(sessionId)}
                    className="flex items-center gap-1 px-3 py-1.5 text-[10px] font-mono uppercase bg-yellow-500/10 text-yellow-400 border border-yellow-500/30 rounded hover:bg-yellow-500/20"
                  >
                    <Pause size={10} /> Pause
                  </button>
                  <button
                    onClick={() => resumeSession(sessionId)}
                    className="flex items-center gap-1 px-3 py-1.5 text-[10px] font-mono uppercase bg-green-500/10 text-green-400 border border-green-500/30 rounded hover:bg-green-500/20"
                  >
                    <Play size={10} /> Resume
                  </button>
                  <button
                    onClick={() => close(sessionId)}
                    className="flex items-center gap-1 px-3 py-1.5 text-[10px] font-mono uppercase bg-red-500/10 text-red-400 border border-red-500/30 rounded hover:bg-red-500/20"
                  >
                    <X size={10} /> Close
                  </button>
                </div>

                {lastCheckpoint && (
                  <div className="bg-surface-raised border border-border rounded p-3">
                    <div className="text-text-tertiary text-[9px] font-mono uppercase mb-2">Last Checkpoint</div>
                    <div className="text-xs font-mono text-text-secondary whitespace-pre-wrap">
                      {JSON.stringify(lastCheckpoint, null, 2)}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-text-tertiary text-xs font-mono">
                  <Clock size={14} />
                  No active session
                </div>
                <button
                  onClick={() => startSession()}
                  className="flex items-center gap-1 px-3 py-1.5 text-[10px] font-mono uppercase bg-cyan/10 text-cyan border border-cyan/30 rounded hover:bg-cyan/20"
                >
                  <Play size={10} /> Start Session
                </button>
              </div>
            )}
          </div>
        )}

        {tab === 'history' && (
          <div className="space-y-2">
            {history.map((session, i) => {
              const id = (session as Record<string, unknown>).id as string ?? `session-${i}`
              const status = (session as Record<string, unknown>).status as string ?? 'unknown'
              return (
                <div key={id} className="bg-surface-raised border border-border rounded p-3 flex items-center justify-between">
                  <div>
                    <div className="text-xs font-mono text-text-primary">{id}</div>
                    <div className="text-[9px] font-mono text-text-tertiary mt-0.5">
                      {(session as Record<string, unknown>).started_at as string ?? ''}
                    </div>
                  </div>
                  <span className={`text-[9px] font-mono px-2 py-0.5 rounded ${
                    status === 'closed' ? 'bg-text-tertiary/10 text-text-tertiary'
                      : status === 'paused' ? 'bg-yellow-400/10 text-yellow-400'
                      : 'bg-green-400/10 text-green-400'
                  }`}>
                    {status}
                  </span>
                </div>
              )
            })}
            {history.length === 0 && (
              <div className="text-text-tertiary text-xs font-mono">No session history</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
