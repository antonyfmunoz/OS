import { useState } from 'react'
import { Users, Bot, MessageSquare, Shield, Link2, X } from 'lucide-react'
import { clsx } from 'clsx'
import { MemberListPanel } from './MemberListPanel'
import { RoomDexPanel } from './RoomDexPanel'
import { ThreadPanel } from './ThreadPanel'
import { RoomAuditLog } from './RoomAuditLog'
import { InvitePanel } from './InvitePanel'

type Tab = 'members' | 'dex' | 'threads' | 'invites' | 'audit'

const TABS: { id: Tab; label: string; icon: typeof Users }[] = [
  { id: 'members', label: 'Members', icon: Users },
  { id: 'dex', label: 'DEX', icon: Bot },
  { id: 'threads', label: 'Threads', icon: MessageSquare },
  { id: 'invites', label: 'Invites', icon: Link2 },
  { id: 'audit', label: 'Audit', icon: Shield },
]

interface Props {
  onClose?: () => void
}

export function RoomRightRail({ onClose }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('members')

  return (
    <div
      className="w-52 shrink-0 flex flex-col border-l overflow-hidden"
      style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface)' }}
    >
      <div className="flex items-center h-9 shrink-0 border-b px-1" style={{ borderColor: 'var(--color-border)' }}>
        {TABS.map((tab) => {
          const Icon = tab.icon
          const active = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={clsx('flex items-center gap-0.5 px-1.5 py-1 text-[9px] font-mono uppercase transition-colors')}
              style={{
                color: active ? 'var(--color-cyan)' : 'var(--color-text-tertiary)',
              }}
              title={tab.label}
            >
              <Icon size={11} />
              <span className="hidden xl:inline">{tab.label}</span>
            </button>
          )
        })}
        {onClose && (
          <button
            onClick={onClose}
            className="ml-auto p-1 transition-colors"
            style={{ color: 'var(--color-text-tertiary)' }}
            title="Close"
          >
            <X size={12} />
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        {activeTab === 'members' && <MemberListPanel />}
        {activeTab === 'dex' && <RoomDexPanel />}
        {activeTab === 'threads' && <ThreadPanel />}
        {activeTab === 'invites' && <InvitePanel />}
        {activeTab === 'audit' && <RoomAuditLog />}
      </div>
    </div>
  )
}
