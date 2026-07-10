import { useEffect, useState } from 'react'
import { Bot, Sparkles } from 'lucide-react'
import { useRoomsStore } from '../../stores/roomsStore'
import { useConfigStore } from '../../stores/configStore'
import type { DexRoomMode } from '../../types/rooms'

const DEX_MODES: { value: DexRoomMode; label: string }[] = [
  { value: 'founder_operator', label: 'Founder Operator' },
  { value: 'sales_coach', label: 'Sales Coach' },
  { value: 'client_success', label: 'Client Success' },
  { value: 'engineering_pm', label: 'Engineering PM' },
  { value: 'technical_reviewer', label: 'Technical Reviewer' },
  { value: 'meeting_notetaker', label: 'Meeting Notetaker' },
  { value: 'podcast_producer', label: 'Podcast Producer' },
  { value: 'broadcast_director', label: 'Broadcast Director' },
  { value: 'security_analyst', label: 'Security Analyst' },
  { value: 'education_facilitator', label: 'Education Facilitator' },
  { value: 'community_moderator', label: 'Community Moderator' },
  { value: 'disabled', label: 'Disabled' },
]

export function RoomDexPanel() {
  const aiName = useConfigStore((s) => s.aiName)
  const activeChannelId = useRoomsStore((s) => s.activeChannelId)
  const dexSettings = useRoomsStore((s) => s.dexSettings)
  const updateDexSettings = useRoomsStore((s) => s.updateDexSettings)
  const dexSummarize = useRoomsStore((s) => s.dexSummarize)

  const [summary, setSummary] = useState<string | null>(null)
  const [summarizing, setSummarizing] = useState(false)

  if (!activeChannelId) return null

  const settings = dexSettings[activeChannelId]

  const handleSummarize = async () => {
    setSummarizing(true)
    const result = await dexSummarize(activeChannelId)
    setSummary(result)
    setSummarizing(false)
  }

  return (
    <div className="py-2 px-3 space-y-3">
      <div className="flex items-center gap-2">
        <Bot size={12} style={{ color: 'var(--color-cyan)' }} />
        <span className="text-[10px] font-mono font-semibold" style={{ color: 'var(--color-text-primary)' }}>
          Room {aiName}
        </span>
      </div>

      <div>
        <div className="text-[9px] font-mono uppercase mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
          Mode
        </div>
        <select
          value={settings?.mode || 'founder_operator'}
          onChange={(e) => updateDexSettings(activeChannelId, { mode: e.target.value as DexRoomMode })}
          className="w-full text-[10px] font-mono px-2 py-1.5 rounded border bg-transparent outline-none"
          style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)', background: 'var(--color-surface)' }}
        >
          {DEX_MODES.map((m) => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </select>
      </div>

      <div>
        <div className="text-[9px] font-mono uppercase mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
          Memory Scope
        </div>
        <div className="flex gap-1">
          {(['room', 'server', 'global'] as const).map((scope) => (
            <button
              key={scope}
              onClick={() => updateDexSettings(activeChannelId, { memory_scope: scope })}
              className="text-[9px] font-mono px-2 py-1 rounded border"
              style={{
                borderColor: settings?.memory_scope === scope ? 'var(--color-cyan)' : 'var(--color-border)',
                color: settings?.memory_scope === scope ? 'var(--color-cyan)' : 'var(--color-text-tertiary)',
              }}
            >
              {scope}
            </button>
          ))}
        </div>
      </div>

      <div>
        <div className="text-[9px] font-mono uppercase mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
          Autonomy
        </div>
        <div className="flex gap-1">
          {(['passive', 'suggest', 'active', 'autonomous'] as const).map((level) => (
            <button
              key={level}
              onClick={() => updateDexSettings(activeChannelId, { autonomy_level: level })}
              className="text-[9px] font-mono px-1.5 py-1 rounded border"
              style={{
                borderColor: settings?.autonomy_level === level ? 'var(--color-cyan)' : 'var(--color-border)',
                color: settings?.autonomy_level === level ? 'var(--color-cyan)' : 'var(--color-text-tertiary)',
              }}
            >
              {level}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-1">
        <ToggleRow
          label="Meeting Listener"
          value={settings?.meeting_listener ?? false}
          onChange={(v) => updateDexSettings(activeChannelId, { meeting_listener: v })}
        />
        <ToggleRow
          label="Transcript"
          value={settings?.transcript_enabled ?? false}
          onChange={(v) => updateDexSettings(activeChannelId, { transcript_enabled: v })}
        />
        <ToggleRow
          label="Action Creation"
          value={settings?.action_creation ?? false}
          onChange={(v) => updateDexSettings(activeChannelId, { action_creation: v })}
        />
        <ToggleRow
          label="Summarization"
          value={settings?.summarization ?? true}
          onChange={(v) => updateDexSettings(activeChannelId, { summarization: v })}
        />
      </div>

      <button
        onClick={handleSummarize}
        disabled={summarizing}
        className="w-full flex items-center justify-center gap-1 text-[10px] font-mono py-1.5 rounded border transition-colors"
        style={{
          borderColor: 'var(--color-cyan)',
          color: 'var(--color-cyan)',
          background: 'var(--color-cyan-glow)',
        }}
      >
        <Sparkles size={10} />
        {summarizing ? 'Summarizing...' : 'Summarize Room'}
      </button>

      {summary && (
        <div
          className="p-2 rounded border text-[10px] font-mono whitespace-pre-wrap"
          style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' }}
        >
          {summary}
        </div>
      )}
    </div>
  )
}

function ToggleRow({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!value)}
      className="flex items-center justify-between w-full py-1"
    >
      <span className="text-[9px] font-mono" style={{ color: 'var(--color-text-secondary)' }}>{label}</span>
      <div
        className="w-6 h-3 rounded-full relative transition-colors"
        style={{ background: value ? 'var(--color-cyan)' : 'var(--color-surface-raised)' }}
      >
        <div
          className="absolute top-0.5 w-2 h-2 rounded-full transition-all"
          style={{
            left: value ? '14px' : '2px',
            background: value ? 'var(--color-canvas)' : 'var(--color-text-tertiary)',
          }}
        />
      </div>
    </button>
  )
}
