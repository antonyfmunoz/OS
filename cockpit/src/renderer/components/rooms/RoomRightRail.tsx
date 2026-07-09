import { useEffect, useState } from 'react'
import { Users, Bot, MessageSquare, Shield, Link2, ChevronLeft, ChevronRight } from 'lucide-react'
import { clsx } from 'clsx'
import { MemberListPanel } from './MemberListPanel'
import { RoomDexPanel } from './RoomDexPanel'
import { RoomChatPanel } from './RoomChatPanel'
import { RoomAuditLog } from './RoomAuditLog'
import { InvitePanel } from './InvitePanel'
import { useConfigStore } from '../../stores/configStore'

type Tab = 'members' | 'dex' | 'chat' | 'invites' | 'audit'

// The 'dex' tab's label is the instance AI name (resolved at render from config),
// never a hardcoded literal. Empty label here = "use aiName" in the render map.
const TABS: { id: Tab; label: string; icon: typeof Users }[] = [
  { id: 'members', label: 'Members', icon: Users },
  { id: 'dex', label: '', icon: Bot },
  { id: 'chat', label: 'Chat', icon: MessageSquare },
  { id: 'invites', label: 'Invites', icon: Link2 },
  { id: 'audit', label: 'Audit', icon: Shield },
]

interface Props {
  collapsed: boolean
  onToggleCollapse: () => void
  chatRequested?: boolean
  onChatOpened?: () => void
}

export function RoomRightRail({ collapsed, onToggleCollapse, chatRequested, onChatOpened }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('members')
  const aiName = useConfigStore((s) => s.aiName)

  useEffect(() => {
    if (!chatRequested) return
    if (collapsed) onToggleCollapse()
    setActiveTab('chat')
    onChatOpened?.()
  }, [chatRequested, collapsed, onToggleCollapse, onChatOpened])

  const isChatActive = activeTab === 'chat'
  const railWidth = isChatActive ? 'w-80' : 'w-56'

  if (collapsed) {
    return (
      <div
        className="shrink-0 flex items-start pt-2 border-l"
        style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface)' }}
      >
        <button
          onClick={onToggleCollapse}
          className="p-1.5 transition-colors"
          style={{ color: 'var(--color-text-tertiary)' }}
          title="Show details"
        >
          <ChevronLeft size={14} />
        </button>
      </div>
    )
  }

  return (
    <div
      className={`${railWidth} shrink-0 flex flex-col border-l overflow-hidden transition-all`}
      style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface)' }}
    >
      <div className="flex items-center h-9 shrink-0 border-b px-2" style={{ borderColor: 'var(--color-border)' }}>
        <button
          onClick={onToggleCollapse}
          className="p-1 transition-colors shrink-0"
          style={{ color: 'var(--color-text-tertiary)' }}
          title="Hide details"
        >
          <ChevronRight size={14} />
        </button>
        <div className="flex items-center justify-end flex-1 min-w-0">
          {TABS.map((tab) => {
            const Icon = tab.icon
            const active = activeTab === tab.id
            const label = tab.label || (tab.id === 'dex' ? aiName : tab.id)
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={clsx('flex items-center gap-1 px-2 py-1 text-[9px] font-mono uppercase transition-colors')}
                style={{
                  color: active ? 'var(--color-cyan)' : 'var(--color-text-tertiary)',
                }}
                title={label}
              >
                <Icon size={11} />
                <span className="hidden xl:inline">{label}</span>
              </button>
            )
          })}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {activeTab === 'members' && <MemberListPanel />}
        {activeTab === 'dex' && <RoomDexPanel />}
        {activeTab === 'chat' && <RoomChatPanel />}
        {activeTab === 'invites' && <InvitePanel />}
        {activeTab === 'audit' && <RoomAuditLog />}
      </div>
    </div>
  )
}
