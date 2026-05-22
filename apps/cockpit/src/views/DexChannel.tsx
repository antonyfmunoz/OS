import { useState, useRef, useEffect } from 'react'
import { clsx } from 'clsx'
import { useCockpitStore } from '../stores/cockpitStore.ts'
import { api } from '../api/client.ts'
import { relativeTime } from '../lib/time.ts'
import type { DexExchange } from '../api/client.ts'

function ExchangeBlock({ exchange }: { exchange: DexExchange }) {
  const response = exchange.response as Record<string, unknown> | null
  const delegatedTo = response?.delegated_to as string | undefined
  const deliverable = response?.deliverable as Record<string, unknown> | null
  const traceId = response?.trace_id as string | undefined
  const critiqueScore = deliverable?.self_critique
    ? (deliverable.self_critique as Record<string, unknown>).score
    : null

  return (
    <div className="border-b border-border/50 py-4 px-4">
      {exchange.content && (
        <div className="mb-3">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[9px] font-mono uppercase tracking-wider text-text-tertiary">OPERATOR</span>
            <span className="text-[9px] text-text-tertiary">{relativeTime(exchange.timestamp)}</span>
          </div>
          <div className="text-[12px] text-text-primary font-mono pl-2 border-l-2 border-cyan">
            {exchange.content}
          </div>
        </div>
      )}

      {response && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[9px] font-mono uppercase tracking-wider text-cyan">DEX</span>
            {delegatedTo && (
              <span className="wv-badge wv-badge-cyan">{delegatedTo}</span>
            )}
            {traceId && (
              <span className="text-[9px] text-text-tertiary font-mono">
                {(traceId as string).slice(0, 12)}...
              </span>
            )}
            {critiqueScore != null && (
              <span className={clsx('wv-badge', Number(critiqueScore) >= 7 ? 'wv-badge-ok' : 'wv-badge-warn')}>
                {String(critiqueScore)}/10
              </span>
            )}
          </div>

          {deliverable && (
            <div className="wv-card p-3 text-[11px] text-text-secondary leading-relaxed">
              {String((deliverable as Record<string, unknown>).content ?? JSON.stringify(deliverable)).slice(0, 500)}
            </div>
          )}

          {!deliverable && (
            <div className="text-[11px] text-text-tertiary pl-2 border-l-2 border-border">
              {response.signal
                ? `Signal processed: ${String(response.signal).slice(0, 200)}`
                : 'Command acknowledged'}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function StatusBar() {
  const { organismRunning, organismAgents } = useCockpitStore()
  const activeCount = organismAgents.filter((a) => a.status !== 'offline').length

  return (
    <div className="flex items-center gap-4 px-4 py-2 border-b border-border text-[10px] font-mono">
      <div className="flex items-center gap-2">
        <span className={clsx('w-2 h-2 rounded-full', organismRunning ? 'bg-ok wv-pulse' : 'bg-danger')} />
        <span className="text-text-tertiary uppercase">
          {organismRunning ? 'ORGANISM ONLINE' : 'ORGANISM OFFLINE'}
        </span>
      </div>
      <span className="text-text-tertiary">
        {activeCount} agent{activeCount !== 1 ? 's' : ''} active
      </span>
      <div className="flex-1" />
      <button
        onClick={async () => {
          await api.organismControl(organismRunning ? 'stop' : 'start')
          useCockpitStore.getState().fetchAll()
        }}
        className={clsx(
          'px-2 py-0.5 text-[9px] font-mono uppercase tracking-wider border transition-colors',
          organismRunning
            ? 'text-danger border-danger-dim hover:bg-danger/10'
            : 'text-ok border-ok-dim hover:bg-ok/10',
        )}
      >
        {organismRunning ? 'Stop' : 'Start'}
      </button>
    </div>
  )
}

export function DexChannel() {
  const { dexHistory, organismRunning } = useCockpitStore()
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [localExchanges, setLocalExchanges] = useState<DexExchange[]>([])
  const scrollRef = useRef<HTMLDivElement>(null)

  const allExchanges = [...dexHistory, ...localExchanges]

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [allExchanges.length])

  const handleSubmit = async () => {
    if (!input.trim() || sending || !organismRunning) return
    const content = input.trim()
    setInput('')
    setSending(true)

    const pendingExchange: DexExchange = {
      id: `pending-${Date.now()}`,
      timestamp: new Date().toISOString(),
      sender: 'operator',
      content,
      response: null,
    }
    setLocalExchanges((prev) => [...prev, pendingExchange])

    try {
      const res = await api.dexConverse(content)
      setLocalExchanges((prev) =>
        prev.map((e) =>
          e.id === pendingExchange.id
            ? { ...e, id: res.message_id, response: res.response, timestamp: res.timestamp }
            : e,
        ),
      )
      useCockpitStore.getState().fetchAll()
    } catch {
      setLocalExchanges((prev) =>
        prev.map((e) =>
          e.id === pendingExchange.id
            ? { ...e, response: { error: 'Failed to reach DEX' } }
            : e,
        ),
      )
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">
          DEX Channel
        </h1>
        <span className="text-[10px] font-mono text-text-tertiary uppercase">
          directed control
        </span>
      </div>

      <StatusBar />

      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {allExchanges.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-text-tertiary">
            <div className="text-[13px] font-mono mb-2">No exchanges yet</div>
            <div className="text-[10px] max-w-xs text-center leading-relaxed">
              Send commands to DEX from here. DEX will delegate to agents, execute tasks, and return results.
            </div>
          </div>
        )}
        {allExchanges.map((exchange) => (
          <ExchangeBlock key={exchange.id} exchange={exchange} />
        ))}
        {sending && (
          <div className="px-4 py-3 text-[10px] text-cyan font-mono animate-pulse">
            DEX processing...
          </div>
        )}
      </div>

      <div className="border-t border-border p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            placeholder={organismRunning ? 'Command DEX...' : 'Organism offline — start it to use DEX'}
            disabled={sending || !organismRunning}
            className="flex-1 bg-surface border border-border text-text-primary text-[12px] font-mono px-3 py-2 placeholder:text-text-tertiary focus:border-cyan-dim focus:outline-none disabled:opacity-40"
          />
          <button
            onClick={handleSubmit}
            disabled={sending || !input.trim() || !organismRunning}
            className="px-4 py-2 text-[10px] font-mono uppercase tracking-wider bg-cyan/10 text-cyan border border-cyan-dim hover:bg-cyan/20 transition-colors disabled:opacity-40"
          >
            {sending ? '...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  )
}
