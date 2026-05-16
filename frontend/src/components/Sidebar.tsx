import { MessageSquare, Brain, Server } from 'lucide-react'
import clsx from 'clsx'

export type View = 'chat' | 'knowledge' | 'system'

interface SidebarProps {
  currentView: View
  onViewChange: (view: View) => void
}

const navItems: { id: View; label: string; icon: typeof MessageSquare }[] = [
  { id: 'chat', label: 'Chat', icon: MessageSquare },
  { id: 'knowledge', label: 'Knowledge', icon: Brain },
  { id: 'system', label: 'System', icon: Server },
]

export default function Sidebar({ currentView, onViewChange }: SidebarProps) {
  return (
    <aside className="w-56 bg-zinc-950 border-r border-zinc-800 flex flex-col h-screen">
      <div className="p-4 border-b border-zinc-800">
        <h1 className="text-sm font-bold text-zinc-100 tracking-wide uppercase">
          UMH Operator
        </h1>
        <p className="text-xs text-zinc-500 mt-1">Workstation</p>
      </div>

      <nav className="flex-1 p-2">
        {navItems.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => onViewChange(id)}
            className={clsx(
              'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors mb-1',
              currentView === id
                ? 'bg-zinc-800 text-zinc-100'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
            )}
          >
            <Icon size={18} />
            {label}
          </button>
        ))}
      </nav>

      <div className="p-4 border-t border-zinc-800 text-xs text-zinc-600">
        UMH v1.0
      </div>
    </aside>
  )
}
