import { useMemo, useEffect, useRef } from 'react'
import {
  Globe,
  Monitor,
  Camera,
  Terminal,
  Eye,
  LayoutDashboard,
  Pause,
  Play,
  Trash2,
  Group,
  Ungroup,
} from 'lucide-react'

interface MenuItem {
  label: string
  icon?: React.ReactNode
  type?: string
  config?: Record<string, string>
  action?: string
  divider?: boolean
  danger?: boolean
}

const ITEMS: MenuItem[] = [
  { label: 'Add Browser Pane', icon: <Globe size={12} />, type: 'browser' },
  { label: 'Add Desktop M0', icon: <Monitor size={12} />, type: 'desktop', config: { monitorId: 'M0' } },
  { label: 'Add Desktop M1', icon: <Monitor size={12} />, type: 'desktop', config: { monitorId: 'M1' } },
  { label: 'Add Vision Camera', icon: <Camera size={12} />, type: 'vision' },
  { label: 'Add Terminal', icon: <Terminal size={12} />, type: 'terminal' },
  { label: 'Add Preview', icon: <Eye size={12} />, type: 'preview' },
  { divider: true, label: '' },
  { label: 'Tile All', icon: <LayoutDashboard size={12} />, action: 'tile' },
  { label: 'Fit All', icon: <LayoutDashboard size={12} />, action: 'fitAll' },
  { divider: true, label: '' },
  { label: 'Pause All', icon: <Pause size={12} />, action: 'pauseAll' },
  { label: 'Resume All', icon: <Play size={12} />, action: 'resumeAll' },
  { divider: true, label: '' },
  { label: 'Clear All', icon: <Trash2 size={12} />, action: 'clearAll', danger: true },
]

interface CanvasContextMenuProps {
  x: number
  y: number
  visible: boolean
  onClose: () => void
  onAddWindow: (type: string, config?: Record<string, string>) => void
  onAction: (action: string) => void
  selectedCount?: number
  targetClusterId?: string | null
}

export function CanvasContextMenu({
  x,
  y,
  visible,
  onClose,
  onAddWindow,
  onAction,
  selectedCount = 0,
  targetClusterId,
}: CanvasContextMenuProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!visible) return
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose()
    }
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('mousedown', handleClick)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handleClick)
      document.removeEventListener('keydown', handleKey)
    }
  }, [visible, onClose])

  const dynamicItems = useMemo(() => {
    const items = [...ITEMS]
    const clusterItems: MenuItem[] = []

    if (selectedCount >= 2) {
      clusterItems.push({ label: 'Group into Cluster', icon: <Group size={12} />, action: 'createCluster' })
    }
    if (targetClusterId) {
      clusterItems.push({ label: 'Remove from Cluster', icon: <Ungroup size={12} />, action: 'removeFromCluster' })
      clusterItems.push({ label: 'Dissolve Cluster', icon: <Ungroup size={12} />, action: 'dissolveCluster' })
    }

    if (clusterItems.length > 0) {
      const lastDividerIdx = items.findLastIndex((i) => i.divider)
      items.splice(lastDividerIdx, 0, { divider: true, label: '' }, ...clusterItems)
    }

    return items
  }, [selectedCount, targetClusterId])

  if (!visible) return null

  return (
    <div
      ref={ref}
      className="py-1"
      style={{
        position: 'fixed',
        left: x,
        top: y,
        zIndex: 100,
        background: 'var(--color-surface-raised)',
        border: '1px solid var(--color-border)',
        borderRadius: 6,
        minWidth: 180,
        boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
      }}
    >
      {dynamicItems.map((item, i) => {
        if (item.divider) {
          return (
            <div
              key={`div-${i}`}
              className="my-1"
              style={{ borderTop: '1px solid var(--color-border)' }}
            />
          )
        }
        return (
          <button
            key={item.label}
            className="flex items-center gap-2 w-full px-3 py-1.5 text-[12px] text-left"
            style={{
              color: item.danger ? 'var(--color-danger)' : 'var(--color-text-primary)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--color-surface-overlay)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent'
            }}
            onClick={() => {
              if (item.type) onAddWindow(item.type, item.config)
              else if (item.action) onAction(item.action)
              onClose()
            }}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        )
      })}
    </div>
  )
}
