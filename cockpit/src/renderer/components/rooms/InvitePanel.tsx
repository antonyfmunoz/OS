import { useEffect, useState, useCallback } from 'react'
import { Link2, Copy, Check, Trash2, Plus, Clock } from 'lucide-react'
import { useRoomsStore } from '../../stores/roomsStore'

export function InvitePanel() {
  const activeServerId = useRoomsStore((s) => s.activeServerId)
  const invites = useRoomsStore((s) => s.invites)
  const fetchInvites = useRoomsStore((s) => s.fetchInvites)
  const createInvite = useRoomsStore((s) => s.createInvite)
  const revokeInvite = useRoomsStore((s) => s.revokeInvite)

  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    if (activeServerId) fetchInvites(activeServerId)
  }, [activeServerId, fetchInvites])

  const handleCreate = useCallback(async () => {
    if (!activeServerId || creating) return
    setCreating(true)
    await createInvite(activeServerId, null, null, 24, null)
    setCreating(false)
  }, [activeServerId, creating, createInvite])

  const handleCopy = useCallback((code: string, id: string) => {
    const link = `${window.location.origin}/invite/${code}`
    navigator.clipboard.writeText(link).then(() => {
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 2000)
    })
  }, [])

  const activeInvites = invites.filter((inv) => !inv.revoked)

  return (
    <div className="py-2 px-3 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Link2 size={12} style={{ color: 'var(--color-cyan)' }} />
          <span className="text-[10px] font-mono font-semibold" style={{ color: 'var(--color-text-primary)' }}>
            Invite Links
          </span>
        </div>
        <button
          onClick={handleCreate}
          disabled={creating}
          className="flex items-center gap-1 text-[9px] font-mono px-2 py-1 rounded border transition-colors"
          style={{ borderColor: 'var(--color-cyan)', color: 'var(--color-cyan)' }}
          title="Create invite link"
        >
          <Plus size={10} />
          {creating ? 'Creating...' : 'New'}
        </button>
      </div>

      {activeInvites.length === 0 && (
        <div className="text-center py-4">
          <p className="text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
            No active invite links
          </p>
          <p className="text-[9px] font-mono mt-1" style={{ color: 'var(--color-text-tertiary)' }}>
            Create one to share with collaborators
          </p>
        </div>
      )}

      {activeInvites.map((invite) => {
        const expired = invite.expires_at && new Date(invite.expires_at) < new Date()
        const maxedOut = invite.max_uses !== null && invite.uses >= invite.max_uses
        const inactive = expired || maxedOut

        return (
          <div
            key={invite.id}
            className="rounded border p-2 space-y-1.5"
            style={{
              borderColor: inactive ? 'var(--color-border)' : 'var(--color-cyan)',
              opacity: inactive ? 0.5 : 1,
            }}
          >
            <div className="flex items-center gap-2">
              <code
                className="text-[10px] font-mono flex-1 truncate"
                style={{ color: 'var(--color-text-primary)' }}
              >
                /invite/{invite.code}
              </code>
              <button
                onClick={() => handleCopy(invite.code, invite.id)}
                className="p-1 transition-colors"
                style={{ color: copiedId === invite.id ? 'var(--color-ok)' : 'var(--color-text-tertiary)' }}
                title="Copy invite link"
              >
                {copiedId === invite.id ? <Check size={10} /> : <Copy size={10} />}
              </button>
              <button
                onClick={() => revokeInvite(invite.id)}
                className="p-1 transition-colors"
                style={{ color: 'var(--color-danger)' }}
                title="Revoke invite"
              >
                <Trash2 size={10} />
              </button>
            </div>
            <div className="flex items-center gap-3 text-[8px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
              {invite.max_uses !== null && (
                <span>{invite.uses}/{invite.max_uses} uses</span>
              )}
              {invite.expires_at && (
                <span className="flex items-center gap-0.5">
                  <Clock size={8} />
                  {expired ? 'Expired' : new Date(invite.expires_at).toLocaleDateString()}
                </span>
              )}
              {!invite.max_uses && !invite.expires_at && (
                <span>No limit</span>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
