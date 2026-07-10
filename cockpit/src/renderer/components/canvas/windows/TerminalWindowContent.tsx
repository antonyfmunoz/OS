import { useState, useEffect, useRef, useCallback } from 'react'
import { Terminal } from 'lucide-react'
import { fetchApi } from '../../../api/client'

interface Props {
  session?: string
  pane?: string
  paused: boolean
  node?: string   // undefined | "local" = VPS tmux, anything else = remote terminal
  shell?: string  // "powershell" | "cmd" (for creating new Beast sessions)
}

const TMUX_KEY_MAP: Record<string, string> = {
  ArrowUp: 'Up', ArrowDown: 'Down', ArrowLeft: 'Left', ArrowRight: 'Right',
  Backspace: 'BSpace', Delete: 'DC', Escape: 'Escape', Tab: 'Tab',
  Home: 'Home', End: 'End', PageUp: 'PPage', PageDown: 'NPage',
  F1: 'F1', F2: 'F2', F3: 'F3', F4: 'F4', F5: 'F5', F6: 'F6',
  F7: 'F7', F8: 'F8', F9: 'F9', F10: 'F10', F11: 'F11', F12: 'F12',
}

function sendKeys(sessionName: string, text: string) {
  fetchApi('/tmux/send', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_name: sessionName, text }),
  }).catch(() => {})
}

function sendSpecialKey(sessionName: string, key: string) {
  fetchApi('/tmux/send-key', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_name: sessionName, key }),
  }).catch(() => {})
}

function isRemote(node: string | undefined): boolean {
  return !!node && node !== 'local'
}

function getCapturePath(node: string | undefined, session: string, pane: string): string {
  if (!isRemote(node)) return `/tmux/capture/${session}/${pane}`
  return `/terminal/remote/capture/${session}?node_id=${node}`
}

function doSendInput(node: string | undefined, session: string, text: string) {
  if (!isRemote(node)) {
    sendKeys(session, text + '\n')
  } else {
    fetchApi('/terminal/remote/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ node_id: node, session_name: session, text }),
    }).catch(() => {})
  }
}

function doSendKey(node: string | undefined, session: string, key: string) {
  if (!isRemote(node)) {
    sendSpecialKey(session, key)
  } else {
    fetchApi('/terminal/remote/send-key', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ node_id: node, session_name: session, key }),
    }).catch(() => {})
  }
}

export function TerminalWindowContent({ session, pane, paused, node, shell }: Props) {
  const [output, setOutput] = useState('')
  const [input, setInput] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [failCount, setFailCount] = useState(0)
  const [alive, setAlive] = useState(true)
  const [sessionName, setSessionName] = useState(session === '__create__' ? '' : (session ?? 'assistant_main'))
  const [creating, setCreating] = useState(session === '__create__')
  const [restartKey, setRestartKey] = useState(0)
  const preRef = useRef<HTMLPreElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const paneId = pane ?? '0'

  // Auto-create session on remote nodes
  useEffect(() => {
    if (session !== '__create__' || !node || !creating) return
    let active = true
    const create = async () => {
      try {
        const res = await fetchApi<{ ok?: boolean; session_name?: string; error?: string }>('/terminal/remote/create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ node_id: node, shell: shell ?? 'powershell' }),
        })
        if (!active) return
        if (res.ok && res.session_name) {
          setSessionName(res.session_name)
          setCreating(false)
          setAlive(true)
        } else {
          setError(res.error ?? 'Failed to create session')
          setCreating(false)
        }
      } catch {
        if (active) {
          setError('Failed to reach node')
          setCreating(false)
        }
      }
    }
    create()
    return () => { active = false }
  }, [session, node, shell, creating, restartKey])

  // Poll for output
  useEffect(() => {
    if (paused || creating || !sessionName) return
    let active = true
    const poll = async () => {
      try {
        const res = await fetchApi<{ output?: string; error?: string; ok?: boolean; alive?: boolean }>(getCapturePath(node, sessionName, paneId))
        if (!active) return
        if (res.alive === false) {
          setAlive(false)
          if (res.output) setOutput(res.output)
          return
        }
        if (res.error || res.ok === false) {
          setFailCount((c) => c + 1)
          setError(res.error ?? 'capture failed')
        } else {
          setOutput(res.output ?? '')
          setError(null)
          setFailCount(0)
        }
      } catch {
        if (active) {
          setFailCount((c) => c + 1)
          setError('Connecting to terminal...')
        }
      }
    }
    poll()
    const id = setInterval(poll, 3000)
    return () => { active = false; clearInterval(id) }
  }, [sessionName, paneId, paused, creating, node])

  useEffect(() => {
    if (preRef.current) preRef.current.scrollTop = preRef.current.scrollHeight
  }, [output])

  const handleSend = useCallback(() => {
    if (!input.trim()) return
    doSendInput(node, sessionName, input)
    setInput('')
  }, [input, sessionName, node])

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    e.stopPropagation()

    if (e.key === 'Enter') {
      e.preventDefault()
      handleSend()
      return
    }

    if (e.ctrlKey && e.key === 'c') {
      e.preventDefault()
      doSendKey(node, sessionName, 'C-c')
      return
    }

    if (e.ctrlKey && e.key === 'd') {
      e.preventDefault()
      doSendKey(node, sessionName, 'C-d')
      return
    }

    if (e.ctrlKey && e.key === 'z') {
      e.preventDefault()
      doSendKey(node, sessionName, 'C-z')
      return
    }

    if (e.ctrlKey && e.key === 'l') {
      e.preventDefault()
      doSendKey(node, sessionName, 'C-l')
      return
    }

    const tmuxKey = TMUX_KEY_MAP[e.key]
    if (tmuxKey) {
      e.preventDefault()
      doSendKey(node, sessionName, tmuxKey)
    }
  }, [handleSend, sessionName, node])

  if (creating) {
    return (
      <div className="flex items-center justify-center h-full"
        style={{ color: 'var(--color-text-tertiary)' }}>
        <span className="text-[12px]">Creating session...</span>
      </div>
    )
  }

  if (!alive && !creating) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3"
        style={{ color: 'var(--color-text-tertiary)' }}>
        <Terminal size={24} />
        <span className="text-[12px]">Session ended</span>
        {isRemote(node) && (
          <button
            className="px-3 py-1 text-[11px] rounded"
            style={{ border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }}
            onClick={() => {
              setRestartKey((k) => k + 1)
              setCreating(true)
              setAlive(true)
              setOutput('')
              setError(null)
            }}
          >
            Restart
          </button>
        )}
      </div>
    )
  }

  if (paused) {
    return (
      <div className="flex items-center justify-center h-full"
        style={{ color: 'var(--color-text-tertiary)' }}>
        <span className="text-[12px]">Terminal paused</span>
      </div>
    )
  }

  if (error && failCount > 2 && !output) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3"
        style={{ color: 'var(--color-text-tertiary)' }}>
        <Terminal size={24} />
        <span className="text-[12px]">{error}</span>
        <span className="text-[10px]">Retrying... (attempt {failCount})</span>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full" onClick={() => inputRef.current?.focus()}>
      <pre
        ref={preRef}
        className="flex-1 overflow-auto p-2 text-[11px] leading-[1.4]"
        style={{ color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)', background: 'var(--color-canvas)' }}
      >
        {output || 'Waiting for output...'}
      </pre>
      <div className="flex gap-1 p-1" style={{ borderTop: '1px solid var(--color-border)' }}>
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Command... (Ctrl+C/D/Z work)"
          className="flex-1 px-2 py-1 text-[11px] rounded"
          style={{
            background: 'var(--color-bg-secondary, #0A0A0A)',
            color: 'var(--color-text-primary)',
            border: '1px solid var(--color-border)',
            outline: 'none',
            fontFamily: 'var(--font-mono)',
            minHeight: 28,
          }}
        />
      </div>
    </div>
  )
}
