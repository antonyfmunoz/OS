import { useState } from 'react'
import { clsx } from 'clsx'
import { useCockpitStore } from '../stores/cockpitStore.ts'
import { relativeTime } from '../lib/time.ts'
import type { AwarenessTier, GlobalLayer, GlobalEvent, AISynthesis } from '../types/awareness.ts'

const TIERS: { id: AwarenessTier; label: string; desc: string }[] = [
  { id: 'embodied', label: 'Embodied', desc: 'Physical self — health, location, biometrics' },
  { id: 'workspace', label: 'Workspace', desc: 'Immediate environment — desk, screens, tools' },
  { id: 'network', label: 'Network', desc: 'People and relationships — team, contacts' },
  { id: 'cloud', label: 'Cloud', desc: 'Digital infrastructure — services, APIs, data' },
  { id: 'global', label: 'Global', desc: 'World state — markets, geopolitics, weather' },
  { id: 'learning', label: 'Learning', desc: 'Meta-cognition — what the system is learning' },
]

const LAYERS: { id: GlobalLayer; label: string }[] = [
  { id: 'news', label: 'News' },
  { id: 'markets', label: 'Markets' },
  { id: 'weather', label: 'Weather' },
  { id: 'geopolitical', label: 'Geopolitical' },
  { id: 'aviation', label: 'Aviation' },
  { id: 'maritime', label: 'Maritime' },
  { id: 'infrastructure', label: 'Infrastructure' },
  { id: 'satellite', label: 'Satellite' },
  { id: 'cyber', label: 'Cyber' },
  { id: 'scientific', label: 'Scientific' },
  { id: 'government', label: 'Government' },
  { id: 'custom-feeds', label: 'Custom Feeds' },
]

function TierSelector() {
  const { awarenessTier, setAwarenessTier } = useCockpitStore()

  return (
    <div className="flex gap-1 mb-4">
      {TIERS.map((t) => (
        <button
          key={t.id}
          onClick={() => setAwarenessTier(t.id)}
          className={clsx(
            'px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider transition-colors border',
            awarenessTier === t.id
              ? 'text-cyan bg-cyan-glow border-cyan-dim'
              : 'text-text-tertiary border-border hover:text-text-secondary hover:border-border-active',
          )}
          title={t.desc}
        >
          {t.label}
        </button>
      ))}
    </div>
  )
}

function TierPlaceholder({ tier }: { tier: AwarenessTier }) {
  const info = TIERS.find((t) => t.id === tier)!
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center">
        <div className="text-[48px] text-border mb-4">◎</div>
        <div className="text-[14px] text-text-secondary font-mono uppercase tracking-wider mb-2">{info.label}</div>
        <div className="text-[11px] text-text-tertiary max-w-[400px]">{info.desc}</div>
        <div className="text-[10px] text-text-tertiary mt-4 wv-badge wv-badge-cyan">Awaiting adapters</div>
      </div>
    </div>
  )
}

function LayerToggles() {
  const { globalLayers, toggleGlobalLayer } = useCockpitStore()

  return (
    <div className="wv-card p-3 mb-4">
      <div className="wv-label mb-2">LAYER TOGGLES</div>
      <div className="flex flex-wrap gap-1.5">
        {LAYERS.map((l) => {
          const active = globalLayers.has(l.id)
          return (
            <button
              key={l.id}
              onClick={() => toggleGlobalLayer(l.id)}
              className={clsx(
                'px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider border transition-colors',
                active
                  ? 'text-cyan bg-cyan-glow border-cyan-dim'
                  : 'text-text-tertiary border-border hover:border-border-active',
              )}
            >
              {l.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function TacticalMap() {
  return (
    <div className="wv-card flex-1 relative overflow-hidden">
      <div className="absolute inset-0 wv-scanline" />
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="text-center">
          <div className="text-[120px] leading-none text-border/30 font-mono">⊕</div>
          <div className="text-[11px] text-text-tertiary font-mono mt-2">TACTICAL MAP — AWAITING RENDERER</div>
          <div className="text-[10px] text-text-tertiary mt-1">Globe/Mapbox/Deck.gl integration point</div>
        </div>
      </div>
      <svg className="absolute inset-0 w-full h-full opacity-5">
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeWidth="0.5" className="text-cyan" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
      </svg>
    </div>
  )
}

function EventFeed({ events }: { events: GlobalEvent[] }) {
  const { globalLayers } = useCockpitStore()
  const [filter, setFilter] = useState<'all' | 'critical' | 'warning'>('all')

  const filtered = events
    .filter((e) => globalLayers.has(e.layer))
    .filter((e) => filter === 'all' || e.severity === filter)
    .sort((a, b) => b.relevance - a.relevance)

  const severityColor: Record<string, string> = {
    info: 'text-text-secondary',
    warning: 'text-warn',
    critical: 'text-danger',
  }
  const severityBadge: Record<string, string> = {
    info: 'wv-badge-cyan',
    warning: 'wv-badge-warn',
    critical: 'wv-badge-danger',
  }

  return (
    <div className="wv-card p-3 flex-1 overflow-hidden flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <span className="wv-label">GLOBAL EVENTS</span>
        <div className="flex gap-1">
          {(['all', 'critical', 'warning'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={clsx(
                'px-2 py-0.5 text-[9px] font-mono uppercase border transition-colors',
                filter === f ? 'text-cyan border-cyan-dim bg-cyan-glow' : 'text-text-tertiary border-border',
              )}
            >
              {f}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto space-y-2">
        {filtered.map((e) => (
          <div key={e.id} className="wv-card-raised p-2">
            <div className="flex items-center gap-2 mb-1">
              <span className={clsx('wv-badge', severityBadge[e.severity])}>{e.layer}</span>
              <span className={clsx('text-[11px] flex-1 truncate', severityColor[e.severity])}>
                {e.title}
              </span>
              <span className="text-[9px] text-text-tertiary shrink-0">{relativeTime(e.timestamp)}</span>
            </div>
            <div className="text-[10px] text-text-tertiary leading-relaxed">{e.summary}</div>
            <div className="flex items-center gap-3 mt-1 text-[9px]">
              <span className="text-text-tertiary">SRC: {e.source}</span>
              <span className="text-cyan">REL: {(e.relevance * 100).toFixed(0)}%</span>
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <div className="text-center text-text-tertiary text-[11px] py-8">
            No events — awaiting live feed adapters
          </div>
        )}
      </div>
    </div>
  )
}

function SynthesisRail({ syntheses }: { syntheses: AISynthesis[] }) {
  return (
    <div className="w-80 flex flex-col gap-3">
      <div className="wv-label px-1">AI SYNTHESIS</div>
      {syntheses.length === 0 && (
        <div className="wv-card p-3 text-center text-text-tertiary text-[11px]">No syntheses available</div>
      )}
      {syntheses.map((s) => (
        <div key={s.id} className="wv-card p-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] text-cyan">{s.title}</span>
            <span className="text-[9px] text-text-tertiary">{(s.confidence * 100).toFixed(0)}% conf</span>
          </div>
          <div className="text-[10px] text-text-secondary leading-relaxed mb-2">{s.body}</div>
          <div className="text-[9px] text-text-tertiary">
            Events: {s.relatedEvents.join(', ')} · {relativeTime(s.timestamp)}
          </div>
        </div>
      ))}
    </div>
  )
}

function GlobalView() {
  const events: GlobalEvent[] = []
  const syntheses: AISynthesis[] = []

  return (
    <div className="flex-1 flex flex-col gap-3 overflow-hidden">
      <LayerToggles />
      <div className="flex gap-3 flex-1 min-h-0">
        <div className="flex-1 flex flex-col gap-3">
          <TacticalMap />
          <EventFeed events={events} />
        </div>
        <SynthesisRail syntheses={syntheses} />
      </div>
    </div>
  )
}

export function Awareness() {
  const { awarenessTier } = useCockpitStore()

  return (
    <div className="h-full flex flex-col p-4 overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">
          Awareness
        </h1>
      </div>
      <TierSelector />
      {awarenessTier === 'global' ? <GlobalView /> : <TierPlaceholder tier={awarenessTier} />}
    </div>
  )
}
