import { useState, useEffect, useRef, useCallback } from 'react'
import { Terminal } from 'lucide-react'
import { fetchApi } from '../../../api/client'

interface Props {
  session?: string
  pane?: string
  paused: boolean
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

export function TerminalWindowContent({ session, pane, paused }: Props) {
  const [output, setOutput] = useState('')
  const [input, setInput] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [failCount, setFailCount] = useState(0)
  const preRef = useRef<HTMLPreElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const sessionName = session ?? 'dex_main'
  const paneId = pane ?? '0'

  useEffect(() => {
    if (paused) return
    let active = true
    const poll = async () => {
      try {
        const res = await fetchApi<{ output?: string; error?: string; ok?: boolean }>(`/tmux/capture/${sessionName}/${paneId}`)
        if (!active) return
        if (res.error || res.ok === false) {
          setFailCount((c) => c + 1)
          setError(res.error ?? 'tmux capture failed')
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
  }, [sessionName, paneId, paused])

  useEffect(() => {
    if (preRef.current) preRef.current.scrollTop = preRef.current.scrollHeight
  }, [output])

  const handleSend = useCallback(() => {
    if (!input.trim()) return
    sendKeys(sessionName, input + '\n')
    setInput('')
  }, [input, sessionName])

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    e.stopPropagation()

    if (e.key === 'Enter') {
      e.preventDefault()
      handleSend()
      return
    }

    if (e.ctrlKey && e.key === 'c') {
      e.preventDefault()
      sendSpecialKey(sessionName, 'C-c')
      return
    }

    if (e.ctrlKey && e.key === 'd') {
      e.preventDefault()
      sendSpecialKey(sessionName, 'C-d')
      return
    }

    if (e.ctrlKey && e.key === 'z') {
      e.preventDefault()
      sendSpecialKey(sessionName, 'C-z')
      return
    }

    if (e.ctrlKey && e.key === 'l') {
      e.preventDefault()
      sendSpecialKey(sessionName, 'C-l')
      return
    }

    const tmuxKey = TMUX_KEY_MAP[e.key]
    if (tmuxKey) {
      e.preventDefault()
      sendSpecialKey(sessionName, tmuxKey)
    }
  }, [handleSend, sessionName])

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
