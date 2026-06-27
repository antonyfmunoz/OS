import { useState, useEffect, useCallback } from 'react'
import { useAgentStore } from '../../../stores/agentStore'
import { fetchApi } from '../../../api/client'
import {
  Save,
  RotateCcw,
  Plus,
  X,
  FileText,
  Wrench,
  Zap,
  Workflow,
  Brain,
} from 'lucide-react'

type Tab = 'instructions' | 'tools' | 'skills' | 'workflows' | 'behavior'

const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
  { key: 'instructions', label: 'Instructions', icon: <FileText size={14} /> },
  { key: 'tools', label: 'Tools', icon: <Wrench size={14} /> },
  { key: 'skills', label: 'Skills', icon: <Zap size={14} /> },
  { key: 'workflows', label: 'Workflows', icon: <Workflow size={14} /> },
  { key: 'behavior', label: 'Behavior', icon: <Brain size={14} /> },
]

const ROLES = ['chief', 'manager', 'laborer']
const RISK_CLASSES = ['low', 'medium', 'high', 'critical']

interface Props {
  agentId: string
  onClose: () => void
}

export function AgentConfigView({ agentId, onClose }: Props) {
  const agents = useAgentStore((s) => s.agents)
  const fetchAgents = useAgentStore((s) => s.fetchAgents)
  const agent = agents.find((a) => a.id === agentId)

  const [tab, setTab] = useState<Tab>('instructions')
  const [editingName, setEditingName] = useState(false)

  const [name, setName] = useState(agent?.name ?? '')
  const [role, setRole] = useState(agent?.role ?? 'laborer')
  const [instructions, setInstructions] = useState('')
  const [tools, setTools] = useState<string[]>([] as string[])
  const [skills, setSkills] = useState<string[]>(agent?.skills ?? [])
  const [workflows, setWorkflows] = useState<string[]>([])
  const [behavioralStyle, setBehavioralStyle] = useState('')
  const [autonomyLevel, setAutonomyLevel] = useState(5)
  const [maxRiskClass, setMaxRiskClass] = useState('medium')
  const [autoExecute, setAutoExecute] = useState(false)
  const [saving, setSaving] = useState(false)
  const [addInput, setAddInput] = useState('')

  useEffect(() => {
    if (agents.length === 0) fetchAgents()
  }, [agents.length, fetchAgents])

  useEffect(() => {
    if (agent) {
      setName(agent.name)
      setRole(agent.role ?? 'laborer')
      setSkills(agent.skills ?? [])
    }
  }, [agent])

  const handleSave = useCallback(async () => {
    setSaving(true)
    try {
      await fetchApi(`/organism/agents/${agentId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          role,
          instructions,
          tools,
          skills,
          workflows,
          behavioral_style: behavioralStyle,
          autonomy_level: autonomyLevel,
          max_risk_class: maxRiskClass,
          auto_execute: autoExecute,
        }),
      })
      await fetchAgents()
    } catch {
      // API doesn't exist yet — silent fail
    }
    setSaving(false)
  }, [agentId, name, role, instructions, tools, skills, workflows, behavioralStyle, autonomyLevel, maxRiskClass, autoExecute, fetchAgents])

  const handleReset = useCallback(() => {
    if (agent) {
      setName(agent.name)
      setRole(agent.role ?? 'laborer')
      setSkills(agent.skills ?? [])
    }
    setInstructions('')
    setTools([])
    setWorkflows([])
    setBehavioralStyle('')
    setAutonomyLevel(5)
    setMaxRiskClass('medium')
    setAutoExecute(false)
  }, [agent])

  const addToList = useCallback(
    (setter: React.Dispatch<React.SetStateAction<string[]>>) => {
      if (!addInput.trim()) return
      setter((prev) => (prev.includes(addInput.trim()) ? prev : [...prev, addInput.trim()]))
      setAddInput('')
    },
    [addInput],
  )

  const removeFromList = useCallback(
    (setter: React.Dispatch<React.SetStateAction<string[]>>, item: string) => {
      setter((prev) => prev.filter((v) => v !== item))
    },
    [],
  )

  const statusColor =
    agent?.status === 'active' ? '#22c55e' : agent?.status === 'idle' ? '#f59e0b' : '#6b7280'

  const tabStyle = (t: Tab) => ({
    color: tab === t ? 'var(--color-text-primary)' : 'var(--color-text-tertiary)',
    borderBottom: tab === t ? '2px solid var(--color-cyan)' : '2px solid transparent',
  })

  return (
    <div className="flex h-full" style={{ background: 'var(--color-surface)' }}>
      {/* Left sidebar — identity */}
      <div
        className="flex flex-col gap-3 p-4 shrink-0"
        style={{ width: 240, borderRight: '1px solid var(--color-border)' }}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="self-end p-1 rounded hover:opacity-80"
          style={{ color: 'var(--color-text-tertiary)' }}
          title="Close config"
        >
          <X size={16} />
        </button>

        {/* Agent name */}
        {editingName ? (
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            onBlur={() => setEditingName(false)}
            onKeyDown={(e) => { if (e.key === 'Enter') setEditingName(false) }}
            className="text-[16px] font-medium px-1 rounded"
            style={{
              background: 'var(--color-surface-raised)',
              color: 'var(--color-text-primary)',
              border: '1px solid var(--color-border-active)',
              outline: 'none',
            }}
          />
        ) : (
          <div
            className="text-[16px] font-medium cursor-pointer"
            style={{ color: 'var(--color-text-primary)' }}
            onDoubleClick={() => setEditingName(true)}
            title="Double-click to rename"
          >
            {name || 'Unnamed Agent'}
          </div>
        )}

        {/* Status */}
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: statusColor }} />
          <span className="text-[12px]" style={{ color: 'var(--color-text-secondary)' }}>
            {agent?.status ?? 'unknown'}
          </span>
        </div>

        {/* Role */}
        <div>
          <label className="text-[10px] uppercase tracking-wider block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
            Role
          </label>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="w-full px-2 py-1 text-[12px] rounded"
            style={{
              background: 'var(--color-surface-raised)',
              color: 'var(--color-text-primary)',
              border: '1px solid var(--color-border)',
              outline: 'none',
            }}
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>

        {/* Last active */}
        {agent?.last_active && (
          <div className="text-[10px]" style={{ color: 'var(--color-text-tertiary)' }}>
            Last active: {agent.last_active}
          </div>
        )}

        {/* Save / Reset */}
        <div className="flex gap-2 mt-auto">
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1 px-3 py-1.5 rounded text-[11px]"
            style={{
              background: 'var(--color-cyan)',
              color: 'var(--color-text-inverse)',
              opacity: saving ? 0.5 : 1,
            }}
          >
            <Save size={12} /> {saving ? 'Saving...' : 'Save'}
          </button>
          <button
            onClick={handleReset}
            className="flex items-center gap-1 px-3 py-1.5 rounded text-[11px]"
            style={{
              background: 'var(--color-surface-raised)',
              color: 'var(--color-text-secondary)',
              border: '1px solid var(--color-border)',
            }}
          >
            <RotateCcw size={12} /> Reset
          </button>
        </div>
      </div>

      {/* Right main area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Tab bar */}
        <div className="flex gap-1 px-4 shrink-0" style={{ borderBottom: '1px solid var(--color-border)' }}>
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className="flex items-center gap-1.5 px-3 py-2 text-[12px]"
              style={tabStyle(t.key)}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-auto p-4">
          {tab === 'instructions' && (
            <textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="Agent instructions / system prompt..."
              className="w-full h-full resize-none p-3 rounded text-[12px] leading-[1.6]"
              style={{
                background: 'var(--color-canvas)',
                color: 'var(--color-text-primary)',
                border: '1px solid var(--color-border)',
                outline: 'none',
                fontFamily: 'var(--font-mono)',
              }}
            />
          )}

          {tab === 'tools' && (
            <TagListEditor
              items={tools}
              onAdd={() => addToList(setTools)}
              onRemove={(item) => removeFromList(setTools, item)}
              addInput={addInput}
              setAddInput={setAddInput}
              placeholder="Tool name..."
              label="Assigned Tools"
            />
          )}

          {tab === 'skills' && (
            <TagListEditor
              items={skills}
              onAdd={() => addToList(setSkills)}
              onRemove={(item) => removeFromList(setSkills, item)}
              addInput={addInput}
              setAddInput={setAddInput}
              placeholder="Skill name..."
              label="Assigned Skills"
            />
          )}

          {tab === 'workflows' && (
            <TagListEditor
              items={workflows}
              onAdd={() => addToList(setWorkflows)}
              onRemove={(item) => removeFromList(setWorkflows, item)}
              addInput={addInput}
              setAddInput={setAddInput}
              placeholder="Workflow name..."
              label="Assigned Workflows"
            />
          )}

          {tab === 'behavior' && (
            <div className="space-y-4 max-w-lg">
              {/* Behavioral style */}
              <div>
                <label className="text-[10px] uppercase tracking-wider block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
                  Behavioral Style
                </label>
                <textarea
                  value={behavioralStyle}
                  onChange={(e) => setBehavioralStyle(e.target.value)}
                  placeholder="Direct, concise, technically precise..."
                  rows={3}
                  className="w-full resize-none p-2 rounded text-[12px]"
                  style={{
                    background: 'var(--color-canvas)',
                    color: 'var(--color-text-primary)',
                    border: '1px solid var(--color-border)',
                    outline: 'none',
                  }}
                />
              </div>

              {/* Autonomy level */}
              <div>
                <label className="text-[10px] uppercase tracking-wider block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
                  Autonomy Level: {autonomyLevel}
                </label>
                <input
                  type="range"
                  min={0}
                  max={10}
                  value={autonomyLevel}
                  onChange={(e) => setAutonomyLevel(Number(e.target.value))}
                  className="w-full"
                />
              </div>

              {/* Max risk class */}
              <div>
                <label className="text-[10px] uppercase tracking-wider block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
                  Max Risk Class
                </label>
                <select
                  value={maxRiskClass}
                  onChange={(e) => setMaxRiskClass(e.target.value)}
                  className="w-full px-2 py-1 text-[12px] rounded"
                  style={{
                    background: 'var(--color-surface-raised)',
                    color: 'var(--color-text-primary)',
                    border: '1px solid var(--color-border)',
                    outline: 'none',
                  }}
                >
                  {RISK_CLASSES.map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              </div>

              {/* Auto-execute */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoExecute}
                  onChange={(e) => setAutoExecute(e.target.checked)}
                  className="rounded"
                />
                <span className="text-[12px]" style={{ color: 'var(--color-text-secondary)' }}>
                  Auto-execute (agent acts without approval)
                </span>
              </label>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Reusable tag list editor ────────────────────────────────────

function TagListEditor({
  items,
  onAdd,
  onRemove,
  addInput,
  setAddInput,
  placeholder,
  label,
}: {
  items: string[]
  onAdd: () => void
  onRemove: (item: string) => void
  addInput: string
  setAddInput: (v: string) => void
  placeholder: string
  label: string
}) {
  return (
    <div className="space-y-3">
      <div className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--color-text-tertiary)' }}>
        {label}
      </div>

      {/* Tag pills */}
      <div className="flex flex-wrap gap-1.5">
        {items.map((item) => (
          <span
            key={item}
            className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px]"
            style={{
              background: 'var(--color-surface-raised)',
              color: 'var(--color-text-secondary)',
              border: '1px solid var(--color-border)',
            }}
          >
            {item}
            <button
              onClick={() => onRemove(item)}
              className="hover:opacity-80"
              style={{ color: 'var(--color-text-tertiary)' }}
            >
              <X size={10} />
            </button>
          </span>
        ))}
        {items.length === 0 && (
          <span className="text-[11px]" style={{ color: 'var(--color-text-tertiary)' }}>
            None assigned
          </span>
        )}
      </div>

      {/* Add input */}
      <div className="flex gap-1.5 max-w-xs">
        <input
          type="text"
          value={addInput}
          onChange={(e) => setAddInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') onAdd() }}
          placeholder={placeholder}
          className="flex-1 px-2 py-1 text-[11px] rounded"
          style={{
            background: 'var(--color-canvas)',
            color: 'var(--color-text-primary)',
            border: '1px solid var(--color-border)',
            outline: 'none',
          }}
        />
        <button
          onClick={onAdd}
          className="flex items-center gap-1 px-2 py-1 rounded text-[11px]"
          style={{
            background: 'var(--color-surface-raised)',
            color: 'var(--color-text-secondary)',
            border: '1px solid var(--color-border)',
          }}
        >
          <Plus size={12} /> Add
        </button>
      </div>
    </div>
  )
}
