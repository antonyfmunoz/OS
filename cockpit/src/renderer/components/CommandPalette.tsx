import { useState, useEffect, useRef } from 'react'
import { useCockpitStore, type Panel } from '../stores/cockpitStore'

interface Command {
  id: string
  label: string
  shortcut?: string
  action: () => void
}

export function CommandPalette() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const setPanel = useCockpitStore((s) => s.setPanel)
  const toggleChat = useCockpitStore((s) => s.toggleChat)
  const setMode = useCockpitStore((s) => s.setMode)

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
    { id: 'chat', label: 'Toggle DEX Chat', shortcut: 'Ctrl+/', action: toggleChat },
    { id: 'mode-execute', label: 'Switch to EXECUTE mode', action: () => setMode('EXECUTE') },
    { id: 'mode-plan', label: 'Switch to PLAN mode', action: () => setMode('PLAN') },
    { id: 'mode-review', label: 'Switch to REVIEW mode', action: () => setMode('REVIEW') },
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
        style={{ background: 'var(--surface-1)', border: '1px solid var(--border-focus)' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-4 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command..."
            className="w-full bg-transparent text-sm outline-none"
            style={{ color: 'var(--text-primary)' }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && filtered.length > 0) {
                execute(filtered[0])
              }
            }}
          />
        </div>
        <div className="overflow-y-auto max-h-72">
          {filtered.map((cmd) => (
            <button
              key={cmd.id}
              onClick={() => execute(cmd)}
              className="w-full flex items-center justify-between px-4 py-2.5 text-sm text-left hover:bg-[var(--surface-2)] transition-colors"
              style={{ color: 'var(--text-primary)' }}
            >
              <span>{cmd.label}</span>
              {cmd.shortcut && (
                <span className="font-mono text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  {cmd.shortcut}
                </span>
              )}
            </button>
          ))}
          {filtered.length === 0 && (
            <p className="px-4 py-3 text-sm" style={{ color: 'var(--text-tertiary)' }}>
              No matching commands
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
