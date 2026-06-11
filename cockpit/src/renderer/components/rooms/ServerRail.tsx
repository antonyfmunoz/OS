import { useState, useCallback, type FormEvent } from 'react'
import { Plus, Archive, Pin } from 'lucide-react'
import { clsx } from 'clsx'
import { useRoomsStore } from '../../stores/roomsStore'
import { ServerCreateModal } from './ServerCreateModal'

export function ServerRail() {
  const servers = useRoomsStore((s) => s.servers)
  const activeServerId = useRoomsStore((s) => s.activeServerId)
  const setActiveServer = useRoomsStore((s) => s.setActiveServer)
  const [showCreate, setShowCreate] = useState(false)

  const visibleServers = servers
    .filter((s) => !s.archived)
    .sort((a, b) => {
      if (a.pinned !== b.pinned) return a.pinned ? -1 : 1
      return a.sort_order - b.sort_order
    })

  return (
    <div
      className="flex flex-col items-center w-[60px] shrink-0 py-2 gap-1 overflow-y-auto border-r"
      style={{ borderColor: 'var(--color-border)', background: 'var(--color-canvas)' }}
    >
      {visibleServers.map((server) => (
        <button
          key={server.id}
          onClick={() => setActiveServer(server.id)}
          title={server.name}
          className={clsx(
            'w-10 h-10 rounded-xl flex items-center justify-center text-base transition-all shrink-0',
            activeServerId === server.id
              ? 'rounded-2xl'
              : 'hover:rounded-2xl',
          )}
          style={{
            background: activeServerId === server.id ? 'var(--color-cyan)' : 'var(--color-surface-raised)',
            color: activeServerId === server.id ? 'var(--color-canvas)' : 'var(--color-text-secondary)',
          }}
        >
          {server.icon_emoji || server.name.charAt(0).toUpperCase()}
        </button>
      ))}

      <div
        className="w-8 my-1"
        style={{ borderTop: '1px solid var(--color-border)' }}
      />

      <button
        onClick={() => setShowCreate(true)}
        title="Create Server"
        className="w-10 h-10 rounded-xl flex items-center justify-center transition-all hover:rounded-2xl"
        style={{ background: 'var(--color-surface-raised)', color: 'var(--color-ok)' }}
      >
        <Plus size={18} />
      </button>

      {showCreate && <ServerCreateModal onClose={() => setShowCreate(false)} />}
    </div>
  )
}
