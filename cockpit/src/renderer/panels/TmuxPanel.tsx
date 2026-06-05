import { useState, useEffect, useCallback } from 'react'
import { usePolling } from '../hooks/usePolling'
import { ConnectionBanner } from '../components/ConnectionBanner'

interface TmuxSession {
  name: string
  windows: number
  attached: boolean
}

export function TmuxPanel() {
  const [sessions, setSessions] = useState<TmuxSession[]>([])
  const [selectedSession, setSelectedSession] = useState<string>('')
  const [paneOutput, setPaneOutput] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')

  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch('/api/umh/tmux/sessions')
      const data = await res.json()
      if (data.ok) {
        setSessions(data.sessions)
        setError('')
      } else {
        setError(data.error || 'Failed to fetch tmux sessions')
      }
    } catch {
      setError('API unreachable')
    }
  }, [])

  usePolling(fetchSessions, 5000)

  const capturePane = useCallback(async (sessionName: string, paneId: string) => {
    setLoading(true)
    setPaneOutput('')
    try {
      const res = await fetch(`/api/umh/tmux/capture/${sessionName}/${paneId}`)
      const data = await res.json()
      if (data.ok) {
        setPaneOutput(data.output)
        setError('')
      } else {
        setError(data.error || 'Capture failed')
      }
    } catch {
      setError('Capture request failed')
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    if (selectedSession) {
      capturePane(selectedSession, '0.0')
    }
  }, [selectedSession, capturePane])

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <ConnectionBanner />

      <div className="flex items-center gap-4 px-4 py-2 flex-shrink-0 border-b border-border">
        <h2 className="text-sm font-semibold text-text-primary">Tmux Sessions</h2>
        <span className="text-[10px] text-text-tertiary">{sessions.length} sessions</span>
        <div className="flex-1" />
        {error && <span className="text-[10px] text-danger">{error}</span>}
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Session list */}
        <div className="w-48 border-r border-border overflow-y-auto">
          {sessions.map((s) => (
            <button
              key={s.name}
              onClick={() => setSelectedSession(s.name)}
              className={`w-full text-left px-3 py-2 text-xs font-mono border-b border-border transition-colors ${
                selectedSession === s.name
                  ? 'bg-surface-raised text-text-primary'
                  : 'text-text-secondary hover:bg-surface'
              }`}
            >
              <div className="flex items-center gap-2">
                <span className={`w-1.5 h-1.5 rounded-full ${s.attached ? 'bg-ok' : 'bg-text-tertiary'}`} />
                <span className="truncate">{s.name}</span>
              </div>
              <div className="text-[10px] text-text-tertiary mt-0.5">
                {s.windows} window{s.windows !== 1 ? 's' : ''}
              </div>
            </button>
          ))}
          {sessions.length === 0 && (
            <p className="px-3 py-4 text-xs text-text-tertiary">No tmux sessions</p>
          )}
        </div>

        {/* Pane output */}
        <div className="flex-1 overflow-auto p-3">
          {loading && <p className="text-xs text-text-tertiary">Capturing...</p>}
          {!loading && !selectedSession && (
            <p className="text-xs text-text-tertiary">Select a session to view pane output</p>
          )}
          {!loading && selectedSession && (
            <pre className="text-[11px] font-mono text-text-secondary whitespace-pre-wrap leading-relaxed">
              {paneOutput || '(empty pane)'}
            </pre>
          )}
        </div>
      </div>
    </div>
  )
}
