import { useMemo } from 'react'
import { useRoomsStore } from '../../stores/roomsStore'
import type { PresenceStatus } from '../../types/rooms'

const STATUS_COLORS: Record<PresenceStatus, string> = {
  online: 'var(--color-ok)',
  away: 'var(--color-warn)',
  busy: 'var(--color-danger)',
  offline: 'var(--color-text-tertiary)',
}

export function MemberListPanel() {
  const members = useRoomsStore((s) => s.members)
  const roles = useRoomsStore((s) => s.roles)

  const grouped = useMemo(() => {
    const online = members.filter((m) => m.presence !== 'offline')
    const offline = members.filter((m) => m.presence === 'offline')
    return { online, offline }
  }, [members])

  const roleMap = useMemo(() => {
    const map = new Map<string, string>()
    roles.forEach((r) => map.set(r.id, r.name))
    return map
  }, [roles])

  return (
    <div className="py-1">
      <div className="px-3 py-1">
        <span className="text-[9px] font-mono uppercase tracking-wider" style={{ color: 'var(--color-text-tertiary)' }}>
          Online — {grouped.online.length}
        </span>
      </div>

      {grouped.online.map((member) => (
        <MemberRow key={member.id} member={member} roleMap={roleMap} />
      ))}

      {grouped.offline.length > 0 && (
        <>
          <div className="px-3 py-1 mt-2">
            <span className="text-[9px] font-mono uppercase tracking-wider" style={{ color: 'var(--color-text-tertiary)' }}>
              Offline — {grouped.offline.length}
            </span>
          </div>
          {grouped.offline.map((member) => (
            <MemberRow key={member.id} member={member} roleMap={roleMap} />
          ))}
        </>
      )}

      {members.length === 0 && (
        <div className="px-3 py-4 text-center">
          <span className="text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
            No members
          </span>
        </div>
      )}
    </div>
  )
}

function MemberRow({
  member,
  roleMap,
}: {
  member: { user_id: string; display_name: string; presence: PresenceStatus; roles: string[]; is_typing: boolean }
  roleMap: Map<string, string>
}) {
  const topRole = member.roles[0] ? roleMap.get(member.roles[0]) : null

  return (
    <div className="flex items-center gap-2 px-3 py-1.5">
      <div className="relative">
        <div
          className="w-6 h-6 rounded-full flex items-center justify-center text-[8px] font-mono font-bold"
          style={{
            background: 'var(--color-surface-overlay)',
            color: member.presence === 'offline' ? 'var(--color-text-tertiary)' : 'var(--color-text-secondary)',
          }}
        >
          {member.display_name.charAt(0).toUpperCase()}
        </div>
        <div
          className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2"
          style={{
            background: STATUS_COLORS[member.presence],
            borderColor: 'var(--color-surface)',
          }}
        />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1">
          <span
            className="text-[10px] font-mono truncate"
            style={{
              color: member.presence === 'offline' ? 'var(--color-text-tertiary)' : 'var(--color-text-primary)',
            }}
          >
            {member.display_name}
          </span>
          {member.is_typing && (
            <span className="text-[8px] italic" style={{ color: 'var(--color-text-tertiary)' }}>typing...</span>
          )}
        </div>
        {topRole && (
          <span className="text-[8px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
            {topRole}
          </span>
        )}
      </div>
    </div>
  )
}
