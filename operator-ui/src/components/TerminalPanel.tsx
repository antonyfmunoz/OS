import React, { useState, useRef } from 'react'
import { execute } from '../api/code-engine'

interface TerminalLine {
  type: 'input' | 'output' | 'error'
  text: string
}

export function TerminalPanel() {
  const [lines, setLines] = useState<TerminalLine[]>([
    { type: 'output', text: '# UMH Operator Terminal' },
    { type: 'output', text: '# Type a command and press Enter' },
  ])
  const [input, setInput] = useState('')
  const [running, setRunning] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!input.trim() || running) return

    const cmd = input.trim()
    setInput('')
    setLines((prev) => [...prev, { type: 'input', text: `$ ${cmd}` }])
    setRunning(true)

    try {
      const result = await execute(cmd)
      const outputLines = result.output.split('\n').map((line) => ({
        type: (result.exitCode === 0 ? 'output' : 'error') as TerminalLine['type'],
        text: line,
      }))
      setLines((prev) => [...prev, ...outputLines])
    } catch (err) {
      setLines((prev) => [
        ...prev,
        { type: 'error', text: `Error: ${err instanceof Error ? err.message : String(err)}` },
      ])
    } finally {
      setRunning(false)
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
    }
  }

  return (
    <div className="flex flex-col h-full bg-surface">
      {/* Output area */}
      <div className="flex-1 overflow-y-auto p-2 font-mono text-xs">
        {lines.map((line, i) => (
          <div
            key={i}
            className={
              line.type === 'input'
                ? 'text-accent'
                : line.type === 'error'
                  ? 'text-red-400'
                  : 'text-gray-300'
            }
          >
            {line.text}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      {/* Input */}
      <form onSubmit={handleSubmit} className="flex border-t border-border">
        <span className="px-2 py-1.5 text-xs text-accent font-mono">$</span>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={running}
          className="flex-1 bg-transparent text-xs text-white font-mono outline-none py-1.5 pr-2"
          placeholder={running ? 'Running...' : 'Enter command...'}
          autoFocus
        />
      </form>
    </div>
  )
}
