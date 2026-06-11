import { useState } from 'react'
import { Users, Bot, MessageSquare, FileText, Shield, Settings, Search } from 'lucide-react'
import { clsx } from 'clsx'
import { MemberListPanel } from './MemberListPanel'
import { RoomDexPanel } from './RoomDexPanel'
import { ThreadPanel } from './ThreadPanel'
import { RoomAuditLog } from './RoomAuditLog'

type Tab = 'members' | 'dex' | 'threads' | 'audit'

const TABS: { id: Tab; label: string; icon: typeof Users }[] = [
  { id: 'members', label: 'Members', icon: Users },
  { id: 'dex', label: 'DEX', icon: Bot },
  { id: 'threads', label: 'Threads', icon: MessageSquare },
  { id: 'audit', label: 'Audit', icon: Shield },
]

export function RoomRightRail() {
  const [activeTab, setActiveTab] = useState<Tab>('members')

  return (
    <div
      className="w-56 shrink-0 flex flex-col border-l overflow-hidden"
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
              className={clsx('flex items-center gap-1 px-2 py-1 text-[9px] font-mono uppercase transition-colors')}
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
      </div>

      <div className="flex-1 overflow-y-auto">
        {activeTab === 'members' && <MemberListPanel />}
        {activeTab === 'dex' && <RoomDexPanel />}
        {activeTab === 'threads' && <ThreadPanel />}
        {activeTab === 'audit' && <RoomAuditLog />}
      </div>
    </div>
  )
}
