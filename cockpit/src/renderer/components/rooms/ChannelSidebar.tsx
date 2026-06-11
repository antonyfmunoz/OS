import { useState, useMemo } from 'react'
import {
  ChevronDown,
  ChevronRight,
  Hash,
  Volume2,
  Video,
  MessageSquareText,
  Radio,
  Megaphone,
  FolderOpen,
  ListTodo,
  Bot,
  Shield,
  Plus,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useRoomsStore } from '../../stores/roomsStore'
import type { ChannelType, RoomChannel, ServerCategory } from '../../types/rooms'
import { ChannelCreateModal } from './ChannelCreateModal'

const CHANNEL_ICONS: Record<ChannelType, typeof Hash> = {
  text: Hash,
  voice: Volume2,
  video_meeting: Video,
  forum: MessageSquareText,
  stage: Radio,
  broadcast: Radio,
  announcement: Megaphone,
  files: FolderOpen,
  tasks: ListTodo,
  ai_room: Bot,
  security: Shield,
}

interface CategoryGroupProps {
  category: ServerCategory
  channels: RoomChannel[]
  onSelect?: () => void
}

function CategoryGroup({ category, channels, onSelect }: CategoryGroupProps) {
  const [collapsed, setCollapsed] = useState(category.collapsed)
  const activeChannelId = useRoomsStore((s) => s.activeChannelId)
  const setActiveChannel = useRoomsStore((s) => s.setActiveChannel)

  const handleSelect = (id: string) => {
    setActiveChannel(id)
    onSelect?.()
  }

  return (
    <div className="mb-1">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center gap-1 w-full px-2 py-1 text-left"
      >
        {collapsed ? (
          <ChevronRight size={10} style={{ color: 'var(--color-text-tertiary)' }} />
        ) : (
          <ChevronDown size={10} style={{ color: 'var(--color-text-tertiary)' }} />
        )}
        <span className="text-[9px] font-mono uppercase tracking-wider" style={{ color: 'var(--color-text-tertiary)' }}>
          {category.name}
        </span>
      </button>

      {!collapsed && (
        <div className="mt-0.5">
          {channels
            .sort((a, b) => a.sort_order - b.sort_order)
            .map((ch) => {
              const Icon = CHANNEL_ICONS[ch.type] || Hash
              const active = activeChannelId === ch.id
              return (
                <button
                  key={ch.id}
                  onClick={() => handleSelect(ch.id)}
                  className={clsx(
                    'flex items-center gap-2 w-full px-3 py-1.5 text-left transition-colors',
                    active
                      ? 'bg-cyan-glow'
                      : 'hover:bg-surface-raised',
                  )}
                  style={{
                    color: active ? 'var(--color-cyan)' : ch.muted ? 'var(--color-text-tertiary)' : 'var(--color-text-secondary)',
                  }}
                >
                  <Icon size={13} className="shrink-0" />
                  <span className="text-[11px] font-mono truncate">{ch.name}</span>
                  {ch.unread_count > 0 && (
                    <span
                      className="ml-auto text-[9px] font-mono px-1.5 rounded-full shrink-0"
                      style={{ background: 'var(--color-danger)', color: 'var(--color-canvas)' }}
                    >
                      {ch.unread_count > 99 ? '99+' : ch.unread_count}
                    </span>
                  )}
                  {ch.type === 'voice' && (
                    <span className="ml-auto text-[9px] font-mono" style={{ color: 'var(--color-ok-dim)' }}>
                      VOICE
                    </span>
                  )}
                  {ch.type === 'video_meeting' && (
                    <span className="ml-auto text-[9px] font-mono" style={{ color: 'var(--color-violet-dim)' }}>
                      MEET
                    </span>
                  )}
                </button>
              )
            })}
        </div>
      )}
    </div>
  )
}

interface ChannelSidebarProps {
  onChannelSelect?: () => void
}

export function ChannelSidebar({ onChannelSelect }: ChannelSidebarProps) {
  const activeServerId = useRoomsStore((s) => s.activeServerId)
  const servers = useRoomsStore((s) => s.servers)
  const categories = useRoomsStore((s) => s.categories)
  const channels = useRoomsStore((s) => s.channels)
  const activeChannelId = useRoomsStore((s) => s.activeChannelId)
  const setActiveChannel = useRoomsStore((s) => s.setActiveChannel)
  const [showCreate, setShowCreate] = useState(false)

  const server = servers.find((s) => s.id === activeServerId)

  const channelsByCategory = useMemo(() => {
    const map = new Map<string | null, RoomChannel[]>()
    channels.forEach((ch) => {
      const key = ch.category_id
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(ch)
    })
    return map
  }, [channels])

  const uncategorized = channelsByCategory.get(null) || []

  const handleSelect = (id: string) => {
    setActiveChannel(id)
    onChannelSelect?.()
  }

  return (
    <div
      className="w-52 shrink-0 flex flex-col border-r overflow-hidden"
      style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface)' }}
    >
      <div
        className="flex items-center justify-between px-3 h-9 shrink-0 border-b"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <span className="text-[11px] font-mono font-semibold truncate" style={{ color: 'var(--color-text-primary)' }}>
          {server?.name || 'Server'}
        </span>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowCreate(true)}
            className="p-1 transition-colors"
            style={{ color: 'var(--color-text-tertiary)' }}
            title="Create Channel"
          >
            <Plus size={12} />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto py-1">
        {uncategorized.length > 0 && (
          <div className="mb-1">
            {uncategorized
              .sort((a, b) => a.sort_order - b.sort_order)
              .map((ch) => {
                const Icon = CHANNEL_ICONS[ch.type] || Hash
                const active = activeChannelId === ch.id
                return (
                  <button
                    key={ch.id}
                    onClick={() => handleSelect(ch.id)}
                    className={clsx(
                      'flex items-center gap-2 w-full px-3 py-1.5 text-left transition-colors',
                      active ? 'bg-cyan-glow' : 'hover:bg-surface-raised',
                    )}
                    style={{
                      color: active ? 'var(--color-cyan)' : 'var(--color-text-secondary)',
                    }}
                  >
                    <Icon size={13} className="shrink-0" />
                    <span className="text-[11px] font-mono truncate">{ch.name}</span>
                  </button>
                )
              })}
          </div>
        )}

        {categories
          .sort((a, b) => a.sort_order - b.sort_order)
          .map((cat) => (
            <CategoryGroup
              key={cat.id}
              category={cat}
              channels={channelsByCategory.get(cat.id) || []}
              onSelect={onChannelSelect}
            />
          ))}
      </div>

      {showCreate && activeServerId && (
        <ChannelCreateModal
          serverId={activeServerId}
          categories={categories}
          onClose={() => setShowCreate(false)}
        />
      )}
    </div>
  )
}
