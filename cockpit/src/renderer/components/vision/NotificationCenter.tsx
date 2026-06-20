import { useState } from 'react'
import { clsx } from 'clsx'
import { Bell, BellOff, Check, Trash2, X, ChevronDown, ChevronRight } from 'lucide-react'
import { useVisionStore, type SecurityNotification, type NotificationSeverity } from '../../stores/visionStore'
import { useCollapseStore } from '../../stores/collapseStore'

const SEVERITY_STYLES: Record<NotificationSeverity, { bg: string; border: string; text: string; dot: string }> = {
  info: { bg: 'bg-cyan/5', border: 'border-cyan/20', text: 'text-cyan', dot: 'bg-cyan' },
  warn: { bg: 'bg-warning/5', border: 'border-warning/20', text: 'text-warning', dot: 'bg-warning' },
  critical: { bg: 'bg-danger/5', border: 'border-danger/20', text: 'text-danger', dot: 'bg-danger' },
}

function formatAge(ts: number): string {
  const sec = Math.round((Date.now() - ts) / 1000)
  if (sec < 60) return `${sec}s ago`
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`
  return `${Math.floor(sec / 86400)}d ago`
}

function NotificationRow({ n, onAck, onClear }: {
  n: SecurityNotification
  onAck: (id: string) => void
  onClear: (id: string) => void
}) {
  const s = SEVERITY_STYLES[n.severity]
  return (
    <div className={clsx(
      'flex items-start gap-2 px-2.5 py-2 rounded-lg border text-[10px] font-mono transition-opacity',
      s.bg, s.border,
      n.acknowledged && 'opacity-50',
    )}>
      <span className={clsx('w-1.5 h-1.5 rounded-full shrink-0 mt-1', s.dot)} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className={clsx('uppercase tracking-wider font-bold', s.text)}>{n.severity}</span>
          <span className="text-text-quaternary">{formatAge(n.timestamp)}</span>
          {n.persistent && <span className="text-[8px] text-text-quaternary border border-border rounded px-1">persisted</span>}
        </div>
        <div className="text-text-secondary mt-0.5">{n.event}</div>
        <div className="text-text-tertiary">{n.detail}</div>
        {n.action && <div className="text-text-quaternary mt-0.5">action: {n.action}</div>}
        <div className="text-text-quaternary">source: {n.source}</div>
      </div>
      <div className="flex items-center gap-0.5 shrink-0">
        {!n.acknowledged && (
          <button onClick={() => onAck(n.id)} className="p-1 rounded hover:bg-surface-hover text-text-quaternary hover:text-ok" title="Acknowledge">
            <Check size={10} />
          </button>
        )}
        <button onClick={() => onClear(n.id)} className="p-1 rounded hover:bg-surface-hover text-text-quaternary hover:text-danger" title="Dismiss">
          <X size={10} />
        </button>
      </div>
    </div>
  )
}

export function NotificationCenter() {
  const notifications = useVisionStore((s) => s.notifications)
  const unreadCount = useVisionStore((s) => s.notificationUnreadCount)
  const acknowledgeNotification = useVisionStore((s) => s.acknowledgeNotification)
  const clearNotification = useVisionStore((s) => s.clearNotification)
  const clearAllNotifications = useVisionStore((s) => s.clearAllNotifications)
  const expanded = useCollapseStore((s) => s.isOpen('vision:notifications'))
  const toggle = useCollapseStore((s) => s.toggle)

  const sorted = [...notifications].sort((a, b) => b.timestamp - a.timestamp)
  const criticalCount = sorted.filter((n) => n.severity === 'critical' && !n.acknowledged).length

  return (
    <div className="border-t border-border pt-2">
      <button
        onClick={() => toggle('vision:notifications')}
        className="flex items-center gap-1.5 text-[10px] font-mono text-text-quaternary hover:text-text-secondary uppercase tracking-wider w-full"
      >
        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        <Bell size={12} />
        Notifications
        {unreadCount > 0 && (
          <span className={clsx(
            'ml-1 px-1.5 py-0.5 rounded-full text-[9px] font-mono',
            criticalCount > 0 ? 'bg-danger/20 text-danger' : 'bg-warning/20 text-warning',
          )}>
            {unreadCount}
          </span>
        )}
        {criticalCount > 0 && (
          <span className="text-danger animate-pulse">!</span>
        )}
      </button>

      {expanded && (
        <div className="mt-2 flex flex-col gap-1.5 max-h-[300px] overflow-y-auto">
          {sorted.length === 0 ? (
            <div className="flex items-center gap-2 px-2 py-3 text-[10px] font-mono text-text-tertiary">
              <BellOff size={14} className="opacity-40" />
              No notifications
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between px-1">
                <span className="text-[9px] font-mono text-text-quaternary">
                  {sorted.length} event{sorted.length !== 1 ? 's' : ''}
                  {unreadCount > 0 && ` · ${unreadCount} unread`}
                </span>
                <button
                  onClick={clearAllNotifications}
                  className="flex items-center gap-1 text-[9px] font-mono text-text-quaternary hover:text-danger"
                >
                  <Trash2 size={10} />
                  Clear all
                </button>
              </div>
              {sorted.map((n) => (
                <NotificationRow
                  key={n.id}
                  n={n}
                  onAck={acknowledgeNotification}
                  onClear={clearNotification}
                />
              ))}
            </>
          )}
        </div>
      )}
    </div>
  )
}
