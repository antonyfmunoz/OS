import { useState, type FormEvent } from 'react'
import { MessageSquare, Plus, Archive, Lock } from 'lucide-react'
import { useRoomsStore } from '../../stores/roomsStore'

export function ThreadPanel() {
  const threads = useRoomsStore((s) => s.threads)
  const activeChannelId = useRoomsStore((s) => s.activeChannelId)
  const createThread = useRoomsStore((s) => s.createThread)
  const updateThread = useRoomsStore((s) => s.updateThread)

  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [creating, setCreating] = useState(false)

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !activeChannelId || creating) return
    setCreating(true)
    await createThread(activeChannelId, name.trim())
    setName('')
    setShowCreate(false)
    setCreating(false)
  }

  const activeThreads = threads.filter((t) => !t.archived)
  const archivedThreads = threads.filter((t) => t.archived)

  return (
    <div className="py-2 px-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageSquare size={12} style={{ color: 'var(--color-text-secondary)' }} />
          <span className="text-[10px] font-mono font-semibold" style={{ color: 'var(--color-text-primary)' }}>
            Threads
          </span>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="p-1"
          style={{ color: 'var(--color-text-tertiary)' }}
        >
          <Plus size={10} />
        </button>
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} className="flex gap-1">
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Thread name"
            className="flex-1 text-[10px] font-mono px-2 py-1 rounded border bg-transparent outline-none"
            style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
          />
          <button
            type="submit"
            disabled={!name.trim()}
            className="text-[9px] font-mono px-2 py-1 rounded"
            style={{ background: 'var(--color-cyan)', color: 'var(--color-canvas)' }}
          >
            Go
          </button>
        </form>
      )}

      {activeThreads.map((thread) => (
        <div
          key={thread.id}
          className="flex items-center gap-2 py-1 px-1 rounded transition-colors hover:bg-surface-raised cursor-pointer"
        >
          <MessageSquare size={10} style={{ color: 'var(--color-text-tertiary)' }} />
          <div className="flex-1 min-w-0">
            <span className="text-[10px] font-mono truncate block" style={{ color: 'var(--color-text-primary)' }}>
              {thread.name}
            </span>
            <span className="text-[8px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
              {thread.message_count} msgs
            </span>
          </div>
          {thread.locked && <Lock size={8} style={{ color: 'var(--color-warn)' }} />}
        </div>
      ))}

      {activeThreads.length === 0 && !showCreate && (
        <p className="text-[9px] font-mono text-center py-2" style={{ color: 'var(--color-text-tertiary)' }}>
          No active threads
        </p>
      )}

      {archivedThreads.length > 0 && (
        <div className="mt-2">
          <div className="flex items-center gap-1 mb-1">
            <Archive size={9} style={{ color: 'var(--color-text-tertiary)' }} />
            <span className="text-[8px] font-mono uppercase" style={{ color: 'var(--color-text-tertiary)' }}>
              Archived ({archivedThreads.length})
            </span>
          </div>
          {archivedThreads.map((thread) => (
            <div key={thread.id} className="flex items-center gap-2 py-0.5 px-1">
              <span className="text-[9px] font-mono truncate" style={{ color: 'var(--color-text-tertiary)' }}>
                {thread.name}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
