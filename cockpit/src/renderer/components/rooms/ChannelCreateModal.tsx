import { useState, type FormEvent } from 'react'
import { X } from 'lucide-react'
import { useRoomsStore } from '../../stores/roomsStore'
import type { ChannelType, ServerCategory } from '../../types/rooms'

const CHANNEL_TYPES: { value: ChannelType; label: string }[] = [
  { value: 'text', label: 'Text' },
  { value: 'voice', label: 'Voice' },
  { value: 'video_meeting', label: 'Meeting' },
  { value: 'forum', label: 'Forum' },
  { value: 'announcement', label: 'Announcement' },
  { value: 'files', label: 'Files' },
  { value: 'tasks', label: 'Tasks' },
  { value: 'ai_room', label: 'AI Room' },
]

interface Props {
  serverId: string
  categories: ServerCategory[]
  onClose: () => void
}

export function ChannelCreateModal({ serverId, categories, onClose }: Props) {
  const createChannel = useRoomsStore((s) => s.createChannel)
  const createCategory = useRoomsStore((s) => s.createCategory)
  const setActiveChannel = useRoomsStore((s) => s.setActiveChannel)

  const [mode, setMode] = useState<'channel' | 'category'>('channel')
  const [name, setName] = useState('')
  const [type, setType] = useState<ChannelType>('text')
  const [categoryId, setCategoryId] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!name.trim() || creating) return
    setCreating(true)

    if (mode === 'category') {
      await createCategory(serverId, name.trim())
      onClose()
    } else {
      const ch = await createChannel(serverId, categoryId, name.trim(), type)
      if (ch) {
        setActiveChannel(ch.id)
        onClose()
      }
    }
    setCreating(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.6)' }}>
      <div
        className="w-[400px] rounded-lg"
        style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'var(--color-border)' }}>
          <h3 className="text-sm font-mono font-semibold" style={{ color: 'var(--color-text-primary)' }}>
            Create {mode === 'channel' ? 'Channel' : 'Category'}
          </h3>
          <button onClick={onClose} className="p-1" style={{ color: 'var(--color-text-tertiary)' }}>
            <X size={14} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-3">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setMode('channel')}
              className="text-[10px] font-mono px-3 py-1.5 rounded border"
              style={{
                borderColor: mode === 'channel' ? 'var(--color-cyan)' : 'var(--color-border)',
                color: mode === 'channel' ? 'var(--color-cyan)' : 'var(--color-text-secondary)',
              }}
            >
              Channel
            </button>
            <button
              type="button"
              onClick={() => setMode('category')}
              className="text-[10px] font-mono px-3 py-1.5 rounded border"
              style={{
                borderColor: mode === 'category' ? 'var(--color-cyan)' : 'var(--color-border)',
                color: mode === 'category' ? 'var(--color-cyan)' : 'var(--color-text-secondary)',
              }}
            >
              Category
            </button>
          </div>

          <div>
            <label className="block text-[10px] font-mono uppercase mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
              Name
            </label>
            <input
              autoFocus
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={mode === 'channel' ? 'general' : 'COMMAND'}
              className="w-full text-xs px-3 py-2 rounded border bg-transparent outline-none font-mono"
              style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
            />
          </div>

          {mode === 'channel' && (
            <>
              <div>
                <label className="block text-[10px] font-mono uppercase mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
                  Type
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {CHANNEL_TYPES.map((ct) => (
                    <button
                      key={ct.value}
                      type="button"
                      onClick={() => setType(ct.value)}
                      className="text-[10px] font-mono px-2 py-1 rounded border"
                      style={{
                        borderColor: type === ct.value ? 'var(--color-cyan)' : 'var(--color-border)',
                        color: type === ct.value ? 'var(--color-cyan)' : 'var(--color-text-secondary)',
                        background: type === ct.value ? 'var(--color-cyan-glow)' : 'transparent',
                      }}
                    >
                      {ct.label}
                    </button>
                  ))}
                </div>
              </div>

              {categories.length > 0 && (
                <div>
                  <label className="block text-[10px] font-mono uppercase mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
                    Category
                  </label>
                  <select
                    value={categoryId || ''}
                    onChange={(e) => setCategoryId(e.target.value || null)}
                    className="w-full text-xs px-3 py-2 rounded border bg-transparent outline-none font-mono"
                    style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)', background: 'var(--color-surface)' }}
                  >
                    <option value="">No category</option>
                    {categories.map((cat) => (
                      <option key={cat.id} value={cat.id}>{cat.name}</option>
                    ))}
                  </select>
                </div>
              )}
            </>
          )}

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
            {creating ? 'Creating...' : `Create ${mode === 'channel' ? 'Channel' : 'Category'}`}
          </button>
        </form>
      </div>
    </div>
  )
}
