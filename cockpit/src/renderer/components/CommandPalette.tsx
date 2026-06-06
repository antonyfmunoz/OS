import { useState, useEffect, useRef, useCallback } from 'react'
import { useCockpitStore, type Panel } from '../stores/cockpitStore'
import { useConfigStore } from '../stores/configStore'

interface Command {
  id: string
  label: string
  shortcut?: string
  action: () => void
}

export function CommandPalette() {
  const aiName = useConfigStore((s) => s.aiName)
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [jarvisResponse, setJarvisResponse] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const setPanel = useCockpitStore((s) => s.setPanel)
  const toggleChat = useCockpitStore((s) => s.toggleChat)
  const setMode = useCockpitStore((s) => s.setMode)

  const setWindowMode = useCockpitStore((s) => s.setWindowMode)

  const handleJarvisCommand = useCallback(async (text: string) => {
    try {
      const res = await fetch('/api/umh/presence/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, source: 'typed_command' }),
      })
      const data = await res.json()
      if (!data.ok) return

      if (data.panel_target) {
        setPanel(data.panel_target as Panel)
        setOpen(false)
        return
      }

      if (data.mode_target && ['EXECUTE', 'PLAN', 'REVIEW'].includes(data.mode_target)) {
        setMode(data.mode_target as 'EXECUTE' | 'PLAN' | 'REVIEW')
        setOpen(false)
        return
      }

      if (data.response_text) {
        setJarvisResponse(data.response_text)
      }
    } catch { /* silent */ }
  }, [setPanel, setMode])

  const commands: Command[] = [
    { id: 'dashboard', label: 'Go to Dashboard', shortcut: 'Ctrl+1', action: () => setPanel('dashboard') },
    { id: 'agents', label: 'Go to Agents', shortcut: 'Ctrl+2', action: () => setPanel('agents') },
    { id: 'tasks', label: 'Go to Tasks', shortcut: 'Ctrl+3', action: () => setPanel('tasks') },
    { id: 'approvals', label: 'Go to Approvals', shortcut: 'Ctrl+4', action: () => setPanel('approvals') },
    { id: 'knowledge', label: 'Go to Knowledge', shortcut: 'Ctrl+5', action: () => setPanel('knowledge') },
    { id: 'analytics', label: 'Go to Analytics', shortcut: 'Ctrl+6', action: () => setPanel('analytics') },
    { id: 'editor', label: 'Go to IDE', shortcut: 'Ctrl+7', action: () => setPanel('editor') },
    { id: 'settings', label: 'Go to Settings', shortcut: 'Ctrl+8', action: () => setPanel('settings') },
    { id: 'activity', label: 'Go to Activity', shortcut: 'Ctrl+9', action: () => setPanel('activity') },
    { id: 'execution', label: 'Go to Execution', shortcut: 'Ctrl+0', action: () => setPanel('execution') },
    { id: 'portfolio', label: 'Go to Portfolio', shortcut: 'Ctrl+P', action: () => setPanel('portfolio') },
    { id: 'company', label: 'Go to Company', shortcut: 'Ctrl+C', action: () => setPanel('company') },
    { id: 'chat', label: `Toggle ${aiName} Chat`, shortcut: 'Ctrl+/', action: toggleChat },
    { id: 'mode-execute', label: 'Switch to EXECUTE mode', action: () => setMode('EXECUTE') },
    { id: 'mode-plan', label: 'Switch to PLAN mode', action: () => setMode('PLAN') },
    { id: 'mode-review', label: 'Switch to REVIEW mode', action: () => setMode('REVIEW') },
    { id: 'win-maximized', label: 'Window: Maximized', action: () => setWindowMode('maximized') },
    { id: 'win-large-fab', label: 'Window: Large FAB', action: () => setWindowMode('large-fab') },
    { id: 'win-medium-fab', label: 'Window: Medium FAB', action: () => setWindowMode('medium-fab') },
    { id: 'win-small-fab', label: 'Window: Small FAB', action: () => setWindowMode('small-fab') },
    { id: 'win-invisible', label: 'Window: Invisible', action: () => setWindowMode('invisible') },
    { id: 'tmux', label: 'Go to Tmux Sessions', action: () => setPanel('tmux') },
  ]

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.ctrlKey && e.key === 'k' && !e.shiftKey) {
        e.preventDefault()
        setOpen((prev) => !prev)
      }
      if (e.key === 'Escape' && open) {
        setOpen(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [open])

  useEffect(() => {
    if (open) {
      setQuery('')
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open])

  if (!open) return null

  const filtered = query
    ? commands.filter((c) => c.label.toLowerCase().includes(query.toLowerCase()))
    : commands

  function execute(cmd: Command) {
    cmd.action()
    setOpen(false)
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-24"
      style={{ background: 'rgba(0, 0, 0, 0.6)', backdropFilter: 'blur(4px)' }}
      onClick={() => setOpen(false)}
    >
      <div
        className="w-[500px] max-h-96 rounded-lg overflow-hidden"
        style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border-active)' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-4 py-3" style={{ borderBottom: '1px solid var(--color-border)' }}>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command..."
            className="w-full bg-transparent text-sm outline-none"
            style={{ color: 'var(--color-text-primary)' }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                if (filtered.length > 0) {
                  execute(filtered[0])
                } else if (query.length > 2) {
                  handleJarvisCommand(query)
                }
              }
            }}
          />
        </div>
        <div className="overflow-y-auto max-h-72">
          {filtered.map((cmd) => (
            <button
              key={cmd.id}
              onClick={() => execute(cmd)}
              className="w-full flex items-center justify-between px-4 py-2.5 text-sm text-left hover:bg-[var(--color-surface-raised)] transition-colors"
              style={{ color: 'var(--color-text-primary)' }}
            >
              <span>{cmd.label}</span>
              {cmd.shortcut && (
                <span className="font-mono text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
                  {cmd.shortcut}
                </span>
              )}
            </button>
          ))}
          {filtered.length === 0 && query.length > 2 && (
            <button
              className="w-full text-left px-4 py-3 text-sm hover:bg-[var(--color-surface-raised)] transition-colors"
              style={{ color: 'var(--color-cyan)' }}
              onClick={() => handleJarvisCommand(query)}
            >
              Ask Jarvis: "{query}"
            </button>
          )}
          {jarvisResponse && (
            <div className="px-4 py-3 text-sm" style={{ color: 'var(--color-text-secondary)', borderTop: '1px solid var(--color-border)' }}>
              {jarvisResponse}
            </div>
          )}
          {filtered.length === 0 && query.length <= 2 && !jarvisResponse && (
            <p className="px-4 py-3 text-sm" style={{ color: 'var(--color-text-tertiary)' }}>
              No matching commands
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
