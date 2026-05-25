import { useCockpitStore, type Panel } from '../stores/cockpitStore'

const NAV_ITEMS: Array<{ panel: Panel; icon: string; label: string; key: string }> = [
  { panel: 'dashboard', icon: '◉', label: 'Dashboard', key: '1' },
  { panel: 'agents', icon: '⬡', label: 'Agents', key: '2' },
  { panel: 'tasks', icon: '▤', label: 'Tasks', key: '3' },
  { panel: 'approvals', icon: '◈', label: 'Approvals', key: '4' },
  { panel: 'knowledge', icon: '◎', label: 'Knowledge', key: '5' },
  { panel: 'analytics', icon: '◧', label: 'Analytics', key: '6' },
  { panel: 'editor', icon: '⟨⟩', label: 'IDE', key: '7' },
  { panel: 'settings', icon: '⚙', label: 'Settings', key: '8' },
  { panel: 'activity', icon: '◌', label: 'Activity', key: '9' },
  { panel: 'execution', icon: '◲', label: 'Execution', key: '0' },
  { panel: 'portfolio', icon: '⬢', label: 'Portfolio', key: 'p' },
]

export function NavRail() {
  const activePanel = useCockpitStore((s) => s.activePanel)
  const setPanel = useCockpitStore((s) => s.setPanel)
  const toggleChat = useCockpitStore((s) => s.toggleChat)
  const chatOpen = useCockpitStore((s) => s.chatOpen)

  return (
    <nav
      className="flex flex-col items-center py-2 gap-1 select-none"
      style={{
        width: 'var(--nav-rail-width)',
        background: 'var(--bg)',
        borderRight: '1px solid var(--border)',
      }}
    >
      {NAV_ITEMS.map((item) => (
        <button
          key={item.panel}
          onClick={() => setPanel(item.panel)}
          title={`${item.label} (Ctrl+${item.key})`}
          className="relative flex items-center justify-center w-10 h-10 rounded-md transition-colors duration-150 text-sm"
          style={{
            color: activePanel === item.panel ? 'var(--accent-cyan)' : 'var(--text-secondary)',
            background: activePanel === item.panel ? 'var(--glow-cyan)' : 'transparent',
          }}
        >
          {activePanel === item.panel && (
            <span
              className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-5 rounded-r"
              style={{ background: 'var(--accent-cyan)' }}
            />
          )}
          <span className="text-lg">{item.icon}</span>
        </button>
      ))}

      <div className="flex-1" />

      <button
        onClick={toggleChat}
        title="DEX Chat (Ctrl+/)"
        className="flex items-center justify-center w-10 h-10 rounded-md transition-colors duration-150"
        style={{
          color: chatOpen ? 'var(--accent-purple)' : 'var(--text-secondary)',
          background: chatOpen ? 'rgba(168, 85, 247, 0.12)' : 'transparent',
        }}
      >
        <span className="text-lg">◫</span>
      </button>
    </nav>
  )
}
