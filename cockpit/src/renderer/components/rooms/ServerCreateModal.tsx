import { useState, type FormEvent } from 'react'
import { X } from 'lucide-react'
import { useRoomsStore } from '../../stores/roomsStore'
import type { ServerPrivacy, ServerTemplate } from '../../types/rooms'

const TEMPLATES: { value: ServerTemplate; label: string; emoji: string }[] = [
  { value: 'founder_war_room', label: 'Founder War Room', emoji: '⚔️' },
  { value: 'sales_team', label: 'Sales Team', emoji: '💰' },
  { value: 'client_delivery', label: 'Client Delivery', emoji: '📦' },
  { value: 'engineering', label: 'Engineering', emoji: '⚙️' },
  { value: 'creator_studio', label: 'Creator Studio', emoji: '🎬' },
  { value: 'community', label: 'Community', emoji: '🌐' },
  { value: 'coaching_cohort', label: 'Coaching Cohort', emoji: '🎯' },
  { value: 'broadcast_studio', label: 'Broadcast Studio', emoji: '📡' },
  { value: 'security_ops', label: 'Security Ops', emoji: '🔒' },
  { value: 'empty', label: 'Empty Server', emoji: '📁' },
]

const PRIVACY_OPTIONS: { value: ServerPrivacy; label: string }[] = [
  { value: 'private', label: 'Private' },
  { value: 'internal', label: 'Internal' },
  { value: 'client_facing', label: 'Client-Facing' },
  { value: 'community', label: 'Community' },
]

interface Props {
  onClose: () => void
}

export function ServerCreateModal({ onClose }: Props) {
  const createServer = useRoomsStore((s) => s.createServer)
  const setActiveServer = useRoomsStore((s) => s.setActiveServer)

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [privacy, setPrivacy] = useState<ServerPrivacy>('private')
  const [template, setTemplate] = useState<ServerTemplate | null>('empty')
  const [creating, setCreating] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!name.trim() || creating) return
    setCreating(true)
    const server = await createServer(name.trim(), description.trim(), privacy, template)
    if (server) {
      setActiveServer(server.id)
      onClose()
    }
    setCreating(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.6)' }}>
      <div
        className="w-[480px] max-h-[80vh] rounded-lg overflow-y-auto"
        style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'var(--color-border)' }}>
          <h3 className="text-sm font-mono font-semibold" style={{ color: 'var(--color-text-primary)' }}>
            Create Server
          </h3>
          <button onClick={onClose} className="p-1" style={{ color: 'var(--color-text-tertiary)' }}>
            <X size={14} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block text-[10px] font-mono uppercase mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
              Server Name
            </label>
            <input
              autoFocus
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Empyrean HQ"
              className="w-full text-xs px-3 py-2 rounded border bg-transparent outline-none font-mono"
              style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
            />
          </div>

          <div>
            <label className="block text-[10px] font-mono uppercase mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
              Description
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this server for?"
              className="w-full text-xs px-3 py-2 rounded border bg-transparent outline-none font-mono"
              style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
            />
          </div>

          <div>
            <label className="block text-[10px] font-mono uppercase mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
              Privacy
            </label>
            <div className="flex gap-2">
              {PRIVACY_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setPrivacy(opt.value)}
                  className="text-[10px] font-mono px-3 py-1.5 rounded border transition-colors"
                  style={{
                    borderColor: privacy === opt.value ? 'var(--color-cyan)' : 'var(--color-border)',
                    color: privacy === opt.value ? 'var(--color-cyan)' : 'var(--color-text-secondary)',
                    background: privacy === opt.value ? 'var(--color-cyan-glow)' : 'transparent',
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-[10px] font-mono uppercase mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
              Template
            </label>
            <div className="grid grid-cols-2 gap-2">
              {TEMPLATES.map((t) => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => setTemplate(t.value)}
                  className="flex items-center gap-2 text-[10px] font-mono px-3 py-2 rounded border transition-colors text-left"
                  style={{
                    borderColor: template === t.value ? 'var(--color-cyan)' : 'var(--color-border)',
                    color: template === t.value ? 'var(--color-cyan)' : 'var(--color-text-secondary)',
                    background: template === t.value ? 'var(--color-cyan-glow)' : 'transparent',
                  }}
                >
                  <span>{t.emoji}</span>
                  <span>{t.label}</span>
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={!name.trim() || creating}
            className="w-full text-xs font-mono font-semibold py-2 rounded transition-colors"
            style={{
              background: name.trim() ? 'var(--color-cyan)' : 'var(--color-surface-raised)',
              color: name.trim() ? 'var(--color-canvas)' : 'var(--color-text-tertiary)',
              cursor: name.trim() ? 'pointer' : 'default',
            }}
          >
            {creating ? 'Creating...' : 'Create Server'}
          </button>
        </form>
      </div>
    </div>
  )
}
