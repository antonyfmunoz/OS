import { useState, useMemo } from 'react'
import { clsx } from 'clsx'
import { useCockpitStore } from '../stores/cockpitStore.ts'
import { relativeTime } from '../lib/time.ts'
import type { CommsMessage } from '../api/client.ts'

const DIR_COLOR: Record<CommsMessage['direction'], string> = {
  inbound: 'wv-badge-ok',
  outbound: 'wv-badge-cyan',
  internal: 'wv-badge-warn',
}

type DirFilter = CommsMessage['direction'] | 'all'

function StatsBar({ messages }: { messages: CommsMessage[] }) {
  const inbound = messages.filter((m) => m.direction === 'inbound').length
  const outbound = messages.filter((m) => m.direction === 'outbound').length
  const internal = messages.filter((m) => m.direction === 'internal').length
  const channels = new Set(messages.map((m) => m.channel)).size

  return (
    <div className="grid grid-cols-4 gap-3 mb-4">
      <div className="wv-card p-3 text-center"><div className="wv-metric text-ok">{inbound}</div><div className="wv-label mt-1">INBOUND</div></div>
      <div className="wv-card p-3 text-center"><div className="wv-metric text-cyan">{outbound}</div><div className="wv-label mt-1">OUTBOUND</div></div>
      <div className="wv-card p-3 text-center"><div className="wv-metric text-warn">{internal}</div><div className="wv-label mt-1">INTERNAL</div></div>
      <div className="wv-card p-3 text-center"><div className="wv-metric text-text-primary">{channels}</div><div className="wv-label mt-1">CHANNELS</div></div>
    </div>
  )
}

function MessageRow({ msg, selected, onClick }: { msg: CommsMessage; selected: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={clsx('w-full text-left flex items-center gap-3 py-3 px-3 text-[11px] font-mono border-b border-border/50 transition-colors', selected ? 'bg-cyan/5 border-l-2 border-l-cyan' : 'hover:bg-surface-hover')}>
      <span className={clsx('wv-badge shrink-0', DIR_COLOR[msg.direction])}>{msg.direction.slice(0, 3)}</span>
      <span className="text-cyan shrink-0 w-20 truncate">{msg.from_agent}</span>
      <span className="text-text-tertiary shrink-0 w-16 truncate">{msg.channel}</span>
      <span className="text-text-primary flex-1 truncate">{msg.content}</span>
      <span className="text-text-tertiary shrink-0 w-14 text-right text-[10px]">{relativeTime(msg.timestamp)}</span>
    </button>
  )
}

function DetailPanel({ msg, onClose }: { msg: CommsMessage; onClose: () => void }) {
  return (
    <div className="w-96 border-l border-border flex flex-col bg-surface">
      <div className="flex items-center justify-between p-4 border-b border-border">
        <span className="wv-label">MESSAGE DETAIL</span>
        <button onClick={onClose} className="text-text-tertiary hover:text-text-primary text-[14px] transition-colors">✕</button>
      </div>
      <div className="p-4 space-y-4 overflow-y-auto flex-1">
        <div className="flex gap-4">
          <div><div className="wv-label mb-1">DIRECTION</div><span className={clsx('wv-badge', DIR_COLOR[msg.direction])}>{msg.direction}</span></div>
          <div><div className="wv-label mb-1">CHANNEL</div><span className="wv-badge wv-badge-cyan">{msg.channel}</span></div>
        </div>
        <div><div className="wv-label mb-1">FROM</div><div className="text-[12px] text-cyan font-mono">{msg.from_agent}</div></div>
        <div><div className="wv-label mb-1">CONTENT</div><div className="text-[11px] text-text-secondary leading-relaxed whitespace-pre-wrap">{msg.content}</div></div>
        <div><div className="wv-label mb-1">TIMESTAMP</div><div className="text-[11px] text-text-secondary">{new Date(msg.timestamp).toLocaleString()}</div></div>
      </div>
    </div>
  )
}

export function Comms() {
  const { comms } = useCockpitStore()
  const [dirFilter, setDirFilter] = useState<DirFilter>('all')
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const filtered = useMemo(() => {
    return comms.filter((m) => {
      if (dirFilter !== 'all' && m.direction !== dirFilter) return false
      if (search) { const q = search.toLowerCase(); return m.content.toLowerCase().includes(q) || m.from_agent.toLowerCase().includes(q) || m.channel.toLowerCase().includes(q) }
      return true
    })
  }, [comms, dirFilter, search])

  const selectedMsg = comms.find((m) => m.id === selectedId) ?? null

  return (
    <div className="h-full flex flex-col p-4 overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">Comms</h1>
        <span className="text-[10px] font-mono text-text-tertiary uppercase">{comms.length} messages</span>
      </div>
      <StatsBar messages={comms} />
      <div className="wv-card p-3 mb-4 flex items-center gap-3 flex-wrap">
        <div className="flex gap-1">
          {(['all', 'inbound', 'outbound', 'internal'] as const).map((d) => (
            <button key={d} onClick={() => setDirFilter(d)} className={clsx('px-2 py-1 text-[10px] font-mono uppercase tracking-wider border transition-colors', dirFilter === d ? 'text-cyan bg-cyan-glow border-cyan-dim' : 'text-text-tertiary border-border hover:text-text-secondary hover:border-border-active')}>{d}</button>
          ))}
        </div>
        <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search messages..." className="flex-1 min-w-[160px] bg-surface border border-border text-text-primary text-[11px] font-mono px-2 py-1 placeholder:text-text-tertiary focus:border-cyan-dim focus:outline-none" />
      </div>
      <div className="flex-1 flex min-h-0">
        <div className="flex-1 wv-card overflow-y-auto">
          <div className="sticky top-0 bg-surface border-b border-border px-3 py-2 flex items-center gap-3 text-[10px] font-mono text-text-tertiary uppercase tracking-wider">
            <span className="w-10">DIR</span><span className="w-20">FROM</span><span className="w-16">CH</span><span className="flex-1">CONTENT</span><span className="w-14 text-right">AGE</span>
          </div>
          {filtered.length === 0 && <div className="text-center text-text-tertiary text-[11px] py-12">No messages matching current filters</div>}
          {filtered.map((msg) => <MessageRow key={msg.id} msg={msg} selected={msg.id === selectedId} onClick={() => setSelectedId(msg.id === selectedId ? null : msg.id)} />)}
        </div>
        {selectedMsg && <DetailPanel msg={selectedMsg} onClose={() => setSelectedId(null)} />}
      </div>
    </div>
  )
}
