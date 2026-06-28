import { useState, useEffect, useRef, useCallback } from 'react'
import { Terminal } from 'lucide-react'
import { fetchApi } from '../../../api/client'

interface Props {
  session?: string
  pane?: string
  paused: boolean
}

export function TerminalWindowContent({ session, pane, paused }: Props) {
  const [output, setOutput] = useState('')
  const [input, setInput] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [failCount, setFailCount] = useState(0)
  const preRef = useRef<HTMLPreElement>(null)
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

  const handleSend = useCallback(async () => {
    if (!input.trim()) return
    try {
      await fetchApi('/tmux/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_name: sessionName, text: input + '\n' }),
      })
      setInput('')
    } catch { /* send failure silent */ }
  }, [input, sessionName])

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
    <div className="flex flex-col h-full">
      <pre
        ref={preRef}
        className="flex-1 overflow-auto p-2 text-[11px] leading-[1.4]"
        style={{ color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)', background: 'var(--color-canvas)' }}
      >
        {output || 'Waiting for output...'}
      </pre>
      <div className="flex gap-1 p-1" style={{ borderTop: '1px solid var(--color-border)' }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSend() }}
          placeholder="Command..."
          className="flex-1 px-2 py-0.5 text-[11px] rounded"
          style={{ background: 'var(--color-bg-secondary, #0A0A0A)', color: 'var(--color-text-primary)', border: '1px solid var(--color-border)', outline: 'none', fontFamily: 'var(--font-mono)' }}
        />
      </div>
    </div>
  )
}
