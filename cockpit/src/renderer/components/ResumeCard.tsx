import { useState, useEffect } from 'react'
import { PlayCircle, Clock, GitBranch, FileText, CheckCircle2, AlertCircle, X } from 'lucide-react'
import { fetchApi } from '../api/client'
import { useCockpitStore } from '../stores/cockpitStore'
import { useWorkspaceContextStore } from '../stores/workspaceContextStore'
import { ExecutorBadge } from './ExecutorBadge'

interface ResumeSnapshot {
  active_project: string
  active_repo: string
  active_branch: string
  active_file: string
  active_plan: string
  active_packet: string
  current_objective: string
  last_execution_status: string
  last_execution_executor: string
  last_execution_target: string
  last_execution_ago: string
  pending_approvals: number
  next_action: string
  since_away: string[]
  snapshot_at: string
}

export function ResumeCard() {
  const [snapshot, setSnapshot] = useState<ResumeSnapshot | null>(null)
  const [dismissed, setDismissed] = useState(false)
  const [loading, setLoading] = useState(true)
  const setPanel = useCockpitStore(s => s.setPanel)
  const setActiveProject = useWorkspaceContextStore(s => s.setActiveProject)
  const setActiveFile = useWorkspaceContextStore(s => s.setActiveFile)
  const setActiveBranch = useWorkspaceContextStore(s => s.setActiveBranch)

  useEffect(() => {
    const lastDismissed = localStorage.getItem('umh-resume-dismissed-at')
    if (lastDismissed) {
      const elapsed = Date.now() - parseInt(lastDismissed, 10)
      if (elapsed < 60_000) {
        setDismissed(true)
        setLoading(false)
        return
      }
    }

    fetchApi<ResumeSnapshot>('/api/umh/workstation/resume')
      .then(data => {
        if (data.active_project || data.active_file || data.current_objective) {
          setSnapshot(data)
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading || dismissed || !snapshot) return null

  function handleResume() {
    if (snapshot) {
      if (snapshot.active_project) setActiveProject(snapshot.active_project)
      if (snapshot.active_file) setActiveFile(snapshot.active_file)
      if (snapshot.active_branch) setActiveBranch(snapshot.active_branch)
      setPanel('editor')
    }
    handleDismiss()
  }

  function handleDismiss() {
    setDismissed(true)
    localStorage.setItem('umh-resume-dismissed-at', String(Date.now()))
  }

  return (
    <div
      className="absolute inset-x-4 top-4 z-50 rounded-lg shadow-2xl p-4 max-w-lg mx-auto"
      style={{
        background: 'var(--color-surface-raised)',
        border: '1px solid var(--color-border)',
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-text-primary">Resume where you left off</h3>
        <button onClick={handleDismiss} className="p-1 rounded hover:opacity-70">
          <X size={14} style={{ color: 'var(--color-text-tertiary)' }} />
        </button>
      </div>

      <div className="space-y-2 text-xs">
        {snapshot.active_project && (
          <Row icon={<FileText size={12} />} label="Project" value={snapshot.active_project} />
        )}
        {snapshot.current_objective && (
          <Row icon={<AlertCircle size={12} />} label="Objective" value={snapshot.current_objective} />
        )}
        {snapshot.active_file && (
          <Row icon={<FileText size={12} />} label="File" value={snapshot.active_file} />
        )}
        {snapshot.active_branch && (
          <Row icon={<GitBranch size={12} />} label="Branch" value={snapshot.active_branch} />
        )}
        {snapshot.last_execution_status && (
          <div className="flex items-center gap-2">
            <Clock size={12} style={{ color: 'var(--color-text-tertiary)' }} />
            <span className="text-text-tertiary w-24">Last execution</span>
            <span className="text-text-secondary flex items-center gap-1.5">
              <ExecutorBadge executorType={snapshot.last_execution_executor} targetMachine={snapshot.last_execution_target} />
              <span>{snapshot.last_execution_status}</span>
              {snapshot.last_execution_ago && <span className="text-text-tertiary">{snapshot.last_execution_ago}</span>}
            </span>
          </div>
        )}
        {snapshot.pending_approvals > 0 && (
          <Row icon={<CheckCircle2 size={12} />} label="Pending" value={`${snapshot.pending_approvals} approval(s) waiting`} />
        )}
        {snapshot.next_action && (
          <Row icon={<PlayCircle size={12} />} label="Next action" value={snapshot.next_action} highlight />
        )}
      </div>

      {snapshot.since_away && snapshot.since_away.length > 0 && (
        <div className="mt-3 pt-2" style={{ borderTop: '1px solid var(--color-border)' }}>
          <div className="text-[10px] text-text-tertiary mb-1">While you were away:</div>
          <ul className="space-y-0.5">
            {snapshot.since_away.slice(0, 5).map((evt, i) => (
              <li key={i} className="text-[10px] text-text-secondary">· {evt}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex items-center gap-2 mt-4">
        <button
          onClick={handleResume}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium"
          style={{
            background: 'var(--color-accent)',
            color: '#000',
          }}
        >
          <PlayCircle size={14} />
          Resume
        </button>
        <button
          onClick={handleDismiss}
          className="px-3 py-1.5 rounded text-xs"
          style={{ color: 'var(--color-text-tertiary)' }}
        >
          Dismiss
        </button>
      </div>
    </div>
  )
}

function Row({ icon, label, value, highlight }: { icon: React.ReactNode; label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span style={{ color: 'var(--color-text-tertiary)' }}>{icon}</span>
      <span className="text-text-tertiary w-24">{label}</span>
      <span className={highlight ? 'text-cyan font-medium' : 'text-text-secondary'}>{value}</span>
    </div>
  )
}
