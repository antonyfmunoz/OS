import { useEffect } from 'react'
import { Shield } from 'lucide-react'
import { useRoomsStore } from '../../stores/roomsStore'

export function RoomAuditLog() {
  const activeServerId = useRoomsStore((s) => s.activeServerId)
  const auditLog = useRoomsStore((s) => s.auditLog)
  const fetchAuditLog = useRoomsStore((s) => s.fetchAuditLog)

  useEffect(() => {
    if (activeServerId) fetchAuditLog(activeServerId)
  }, [activeServerId, fetchAuditLog])

  return (
    <div className="py-2 px-3 space-y-2">
      <div className="flex items-center gap-2">
        <Shield size={12} style={{ color: 'var(--color-text-secondary)' }} />
        <span className="text-[10px] font-mono font-semibold" style={{ color: 'var(--color-text-primary)' }}>
          Audit Log
        </span>
      </div>

      {auditLog.length === 0 && (
        <p className="text-[9px] font-mono text-center py-4" style={{ color: 'var(--color-text-tertiary)' }}>
          No audit events
        </p>
      )}

      {auditLog.map((event) => (
        <div
          key={event.id}
          className="py-1.5 border-b"
          style={{ borderColor: 'var(--color-border)' }}
        >
          <div className="flex items-center gap-1">
            <span className="text-[9px] font-mono font-semibold" style={{ color: 'var(--color-text-secondary)' }}>
              {event.actor_name}
            </span>
            <span className="text-[9px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
              {event.type.replace(/_/g, ' ')}
            </span>
          </div>
          <span className="text-[8px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
            {new Date(event.created_at).toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  )
}
