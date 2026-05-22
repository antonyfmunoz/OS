import { useState, useMemo } from 'react'
import { clsx } from 'clsx'
import { useCockpitStore } from '../stores/cockpitStore.ts'
import { relativeTime } from '../lib/time.ts'
import type { SkillResponse } from '../api/client.ts'

const CATEGORY_COLOR: Record<string, string> = { tool: 'wv-badge-cyan', workflow: 'wv-badge-ok', agent: 'wv-badge-violet', system: 'wv-badge-warn' }
const TRIGGER_LABEL: Record<string, string> = { scheduled: 'SCHED', conversational: 'CONV', both: 'BOTH' }
const EFFORT_COLOR: Record<string, string> = { low: 'text-ok', medium: 'text-text-secondary', high: 'text-warn', max: 'text-danger' }

function StatsBar({ skills }: { skills: SkillResponse[] }) {
  const totalUsage = skills.reduce((s, sk) => s + sk.usage_count, 0)
  const automated = skills.filter((s) => s.trigger === 'scheduled' || s.trigger === 'both').length
  return (
    <div className="grid grid-cols-4 gap-3 mb-4">
      <div className="wv-card p-3 text-center"><div className="wv-metric text-text-primary">{skills.length}</div><div className="wv-label mt-1">SKILLS</div></div>
      <div className="wv-card p-3 text-center"><div className="wv-metric text-cyan">{totalUsage}</div><div className="wv-label mt-1">TOTAL USES</div></div>
      <div className="wv-card p-3 text-center"><div className="wv-metric text-text-primary">{new Set(skills.map((s) => s.category)).size}</div><div className="wv-label mt-1">CATEGORIES</div></div>
      <div className="wv-card p-3 text-center"><div className="wv-metric text-ok">{automated}</div><div className="wv-label mt-1">AUTOMATED</div></div>
    </div>
  )
}

function SkillCard({ skill, selected, onClick }: { skill: SkillResponse; selected: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={clsx('w-full text-left wv-card p-4 transition-colors', selected && 'ring-1 ring-cyan')}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-[12px] text-text-primary font-mono">{skill.name}</span>
        <div className="flex items-center gap-2">
          <span className={clsx('wv-badge', CATEGORY_COLOR[skill.category] ?? 'wv-badge-cyan')}>{skill.category}</span>
          <span className="text-[9px] text-text-tertiary font-mono">{TRIGGER_LABEL[skill.trigger] ?? skill.trigger}</span>
        </div>
      </div>
      <div className="text-[11px] text-text-secondary mb-2 truncate">{skill.description}</div>
      <div className="flex items-center justify-between text-[10px] text-text-tertiary">
        <span>{skill.usage_count} uses</span>
        <span className={EFFORT_COLOR[skill.effort] ?? 'text-text-secondary'}>{skill.effort} effort</span>
        <span>{relativeTime(skill.last_used)}</span>
      </div>
    </button>
  )
}

function DetailPanel({ skill, onClose }: { skill: SkillResponse; onClose: () => void }) {
  return (
    <div className="w-96 border-l border-border flex flex-col bg-surface">
      <div className="flex items-center justify-between p-4 border-b border-border">
        <span className="wv-label">SKILL DETAIL</span>
        <button onClick={onClose} className="text-text-tertiary hover:text-text-primary text-[14px] transition-colors">✕</button>
      </div>
      <div className="p-4 space-y-4 overflow-y-auto flex-1">
        <div><div className="wv-label mb-1">NAME</div><div className="text-[14px] text-text-primary font-mono">{skill.name}</div></div>
        <div><div className="wv-label mb-1">DESCRIPTION</div><div className="text-[11px] text-text-secondary leading-relaxed">{skill.description}</div></div>
        <div className="flex gap-4">
          <div><div className="wv-label mb-1">CATEGORY</div><span className={clsx('wv-badge', CATEGORY_COLOR[skill.category] ?? 'wv-badge-cyan')}>{skill.category}</span></div>
          <div><div className="wv-label mb-1">TRIGGER</div><span className="wv-badge wv-badge-cyan">{skill.trigger}</span></div>
          <div><div className="wv-label mb-1">EFFORT</div><span className={clsx('text-[11px] font-mono', EFFORT_COLOR[skill.effort] ?? '')}>{skill.effort}</span></div>
        </div>
        <div><div className="wv-label mb-1">USAGE COUNT</div><div className="wv-metric text-cyan">{skill.usage_count}</div></div>
        <div><div className="wv-label mb-1">LAST USED</div><div className="text-[11px] text-text-secondary">{new Date(skill.last_used).toLocaleString()}</div></div>
      </div>
    </div>
  )
}

export function Skills() {
  const { skills } = useCockpitStore()
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const filtered = useMemo(() => {
    return skills.filter((sk) => {
      if (categoryFilter !== 'all' && sk.category !== categoryFilter) return false
      if (search) { const q = search.toLowerCase(); return sk.name.toLowerCase().includes(q) || sk.description.toLowerCase().includes(q) }
      return true
    }).sort((a, b) => b.usage_count - a.usage_count)
  }, [skills, categoryFilter, search])

  const selectedSkill = skills.find((s) => s.id === selectedId) ?? null

  return (
    <div className="h-full flex flex-col p-4 overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">Skills</h1>
        <span className="text-[10px] font-mono text-text-tertiary uppercase">{skills.length} registered</span>
      </div>
      <StatsBar skills={skills} />
      <div className="wv-card p-3 mb-4 flex items-center gap-3 flex-wrap">
        <div className="flex gap-1">
          {['all', 'tool', 'workflow', 'agent', 'system'].map((c) => (
            <button key={c} onClick={() => setCategoryFilter(c)} className={clsx('px-2 py-1 text-[10px] font-mono uppercase tracking-wider border transition-colors', categoryFilter === c ? 'text-cyan bg-cyan-glow border-cyan-dim' : 'text-text-tertiary border-border hover:text-text-secondary hover:border-border-active')}>{c}</button>
          ))}
        </div>
        <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search skills..." className="flex-1 min-w-[160px] bg-surface border border-border text-text-primary text-[11px] font-mono px-2 py-1 placeholder:text-text-tertiary focus:border-cyan-dim focus:outline-none" />
      </div>
      <div className="flex-1 flex min-h-0">
        <div className="flex-1 overflow-y-auto"><div className="grid grid-cols-2 gap-3">
          {filtered.length === 0 && <div className="col-span-2 text-center text-text-tertiary text-[11px] py-12">No skills matching current filters</div>}
          {filtered.map((skill) => <SkillCard key={skill.id} skill={skill} selected={skill.id === selectedId} onClick={() => setSelectedId(skill.id === selectedId ? null : skill.id)} />)}
        </div></div>
        {selectedSkill && <DetailPanel skill={selectedSkill} onClose={() => setSelectedId(null)} />}
      </div>
    </div>
  )
}
