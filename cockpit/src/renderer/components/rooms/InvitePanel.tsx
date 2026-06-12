import { useEffect, useState, useCallback, type FormEvent } from 'react'
import { Link2, Copy, Check, Trash2, Plus, Clock, ChevronDown, ChevronUp, Shield, Users, X } from 'lucide-react'
import { useRoomsStore, type CreateInviteOptions } from '../../stores/roomsStore'
import { DEFAULT_GUEST_PERMISSIONS, type GuestPermissions } from '../../types/rooms'

export function InvitePanel() {
  const activeServerId = useRoomsStore((s) => s.activeServerId)
  const activeChannelId = useRoomsStore((s) => s.activeChannelId)
  const channels = useRoomsStore((s) => s.channels)
  const invites = useRoomsStore((s) => s.invites)
  const fetchInvites = useRoomsStore((s) => s.fetchInvites)
  const createInvite = useRoomsStore((s) => s.createInvite)
  const revokeInvite = useRoomsStore((s) => s.revokeInvite)

  const [showForm, setShowForm] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const channel = channels.find((c) => c.id === activeChannelId)
  const isVoiceOrMeeting = channel?.type === 'voice' || channel?.type === 'video_meeting' || channel?.type === 'stage' || channel?.type === 'broadcast'

  useEffect(() => {
    if (activeServerId) fetchInvites(activeServerId)
  }, [activeServerId, fetchInvites])

  const handleCopy = useCallback((code: string, id: string) => {
    const link = `${window.location.origin}/join/${code}`
    navigator.clipboard.writeText(link).then(() => {
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 2000)
    })
  }, [])

  const activeInvites = invites.filter((inv) => !inv.revoked)
  const channelInvites = activeChannelId
    ? activeInvites.filter((inv) => inv.channel_id === activeChannelId)
    : activeInvites

  return (
    <div className="py-2 px-3 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Link2 size={12} style={{ color: 'var(--color-cyan)' }} />
          <span className="text-[10px] font-mono font-semibold" style={{ color: 'var(--color-text-primary)' }}>
            Guest Invite Links
          </span>
        </div>
        {isVoiceOrMeeting && (
          <button
            onClick={() => setShowForm((v) => !v)}
            className="flex items-center gap-1 text-[9px] font-mono px-2 py-1 rounded border transition-colors"
            style={{ borderColor: 'var(--color-cyan)', color: 'var(--color-cyan)' }}
          >
            {showForm ? <X size={10} /> : <Plus size={10} />}
            {showForm ? 'Cancel' : 'New Invite'}
          </button>
        )}
      </div>

      {showForm && activeServerId && activeChannelId && (
        <CreateInviteForm
          serverId={activeServerId}
          channelId={activeChannelId}
          roomType={channel?.type === 'video_meeting' ? 'meeting' : 'voice'}
          onCreated={() => setShowForm(false)}
          createInvite={createInvite}
        />
      )}

      {channelInvites.length === 0 && !showForm && (
        <div className="text-center py-4">
          <p className="text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
            No active invite links
          </p>
          {isVoiceOrMeeting && (
            <p className="text-[9px] font-mono mt-1" style={{ color: 'var(--color-text-tertiary)' }}>
              Create a temporary guest link to share
            </p>
          )}
        </div>
      )}

      {channelInvites.map((invite) => (
        <InviteCard
          key={invite.id}
          invite={invite}
          copiedId={copiedId}
          onCopy={handleCopy}
          onRevoke={revokeInvite}
        />
      ))}
    </div>
  )
}

function CreateInviteForm({
  serverId,
  channelId,
  roomType,
  onCreated,
  createInvite,
}: {
  serverId: string
  channelId: string
  roomType: 'voice' | 'meeting'
  onCreated: () => void
  createInvite: (serverId: string, opts: CreateInviteOptions) => Promise<unknown>
}) {
  const [label, setLabel] = useState('')
  const [expiresHours, setExpiresHours] = useState('24')
  const [maxUses, setMaxUses] = useState('')
  const [emailDomains, setEmailDomains] = useState('')
  const [emails, setEmails] = useState('')
  const [permissions, setPermissions] = useState<GuestPermissions>({ ...DEFAULT_GUEST_PERMISSIONS })
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [creating, setCreating] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (creating) return
    setCreating(true)

    const parsedDomains = emailDomains.trim()
      ? emailDomains.split(',').map((d) => d.trim()).filter(Boolean)
      : null
    const parsedEmails = emails.trim()
      ? emails.split(',').map((e) => e.trim()).filter(Boolean)
      : null

    await createInvite(serverId, {
      channel_id: channelId,
      room_type: roomType,
      label: label.trim() || null,
      max_uses: maxUses ? parseInt(maxUses, 10) : null,
      expires_hours: expiresHours ? parseInt(expiresHours, 10) : null,
      allowed_email_domains: parsedDomains,
      allowed_emails: parsedEmails,
      permissions,
    })

    setCreating(false)
    onCreated()
  }

  const inputStyle = {
    borderColor: 'var(--color-border)',
    color: 'var(--color-text-primary)',
    background: 'transparent',
  }

  return (
    <form onSubmit={handleSubmit} className="rounded border p-2.5 space-y-2" style={{ borderColor: 'var(--color-cyan)' }}>
      <div>
        <label className="text-[8px] font-mono block mb-0.5" style={{ color: 'var(--color-text-tertiary)' }}>Label (optional)</label>
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="e.g. Client demo call"
          className="w-full text-[10px] font-mono px-2 py-1 rounded border outline-none"
          style={inputStyle}
        />
      </div>

      <div className="flex gap-2">
        <div className="flex-1">
          <label className="text-[8px] font-mono block mb-0.5" style={{ color: 'var(--color-text-tertiary)' }}>Expires in</label>
          <select
            value={expiresHours}
            onChange={(e) => setExpiresHours(e.target.value)}
            className="w-full text-[10px] font-mono px-2 py-1 rounded border outline-none"
            style={inputStyle}
          >
            <option value="1">1 hour</option>
            <option value="6">6 hours</option>
            <option value="24">24 hours</option>
            <option value="72">3 days</option>
            <option value="168">7 days</option>
          </select>
        </div>
        <div className="flex-1">
          <label className="text-[8px] font-mono block mb-0.5" style={{ color: 'var(--color-text-tertiary)' }}>Max uses</label>
          <input
            type="number"
            value={maxUses}
            onChange={(e) => setMaxUses(e.target.value)}
            placeholder="Unlimited"
            min={1}
            className="w-full text-[10px] font-mono px-2 py-1 rounded border outline-none"
            style={inputStyle}
          />
        </div>
      </div>

      <button
        type="button"
        onClick={() => setShowAdvanced((v) => !v)}
        className="flex items-center gap-1 text-[9px] font-mono"
        style={{ color: 'var(--color-text-tertiary)' }}
      >
        {showAdvanced ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
        Advanced options
      </button>

      {showAdvanced && (
        <div className="space-y-2 pl-1 border-l-2" style={{ borderColor: 'var(--color-border)' }}>
          <div>
            <label className="text-[8px] font-mono block mb-0.5" style={{ color: 'var(--color-text-tertiary)' }}>
              Allowed email domains (comma-separated)
            </label>
            <input
              type="text"
              value={emailDomains}
              onChange={(e) => setEmailDomains(e.target.value)}
              placeholder="e.g. company.com, partner.org"
              className="w-full text-[10px] font-mono px-2 py-1 rounded border outline-none"
              style={inputStyle}
            />
          </div>
          <div>
            <label className="text-[8px] font-mono block mb-0.5" style={{ color: 'var(--color-text-tertiary)' }}>
              Allowed emails (comma-separated)
            </label>
            <input
              type="text"
              value={emails}
              onChange={(e) => setEmails(e.target.value)}
              placeholder="e.g. john@acme.com"
              className="w-full text-[10px] font-mono px-2 py-1 rounded border outline-none"
              style={inputStyle}
            />
          </div>
          <div>
            <label className="flex items-center gap-1 text-[8px] font-mono mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
              <Shield size={9} /> Guest Permissions
            </label>
            <div className="space-y-1">
              {(['can_speak', 'can_video', 'can_screen_share', 'can_chat'] as const).map((key) => (
                <label key={key} className="flex items-center gap-1.5 text-[9px] font-mono cursor-pointer">
                  <input
                    type="checkbox"
                    checked={permissions[key]}
                    onChange={(e) => setPermissions((p) => ({ ...p, [key]: e.target.checked }))}
                    className="accent-cyan-500"
                  />
                  <span style={{ color: 'var(--color-text-secondary)' }}>{key.replace('can_', '').replace('_', ' ')}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      )}

      <button
        type="submit"
        disabled={creating}
        className="w-full text-[10px] font-mono py-1.5 rounded transition-colors"
        style={{ background: 'var(--color-cyan)', color: 'var(--color-canvas)' }}
      >
        {creating ? 'Creating...' : 'Create Guest Invite'}
      </button>
    </form>
  )
}

function InviteCard({
  invite,
  copiedId,
  onCopy,
  onRevoke,
}: {
  invite: ReturnType<typeof useRoomsStore.getState>['invites'][number]
  copiedId: string | null
  onCopy: (code: string, id: string) => void
  onRevoke: (id: string) => void
}) {
  const expired = invite.expires_at && new Date(invite.expires_at) < new Date()
  const maxedOut = invite.max_uses !== null && invite.uses >= invite.max_uses
  const inactive = expired || maxedOut

  return (
    <div
      className="rounded border p-2 space-y-1.5"
      style={{
        borderColor: inactive ? 'var(--color-border)' : 'var(--color-cyan)',
        opacity: inactive ? 0.5 : 1,
      }}
    >
      <div className="flex items-center gap-2">
        {invite.label && (
          <span className="text-[9px] font-mono font-semibold truncate" style={{ color: 'var(--color-text-primary)' }}>
            {invite.label}
          </span>
        )}
        <code className="text-[10px] font-mono flex-1 truncate" style={{ color: 'var(--color-text-secondary)' }}>
          /join/{invite.code}
        </code>
        <button
          onClick={() => onCopy(invite.code, invite.id)}
          className="p-1 transition-colors"
          style={{ color: copiedId === invite.id ? 'var(--color-ok)' : 'var(--color-text-tertiary)' }}
          title="Copy invite link"
        >
          {copiedId === invite.id ? <Check size={10} /> : <Copy size={10} />}
        </button>
        <button
          onClick={() => onRevoke(invite.id)}
          className="p-1 transition-colors"
          style={{ color: 'var(--color-danger)' }}
          title="Revoke invite"
        >
          <Trash2 size={10} />
        </button>
      </div>
      <div className="flex items-center gap-3 flex-wrap text-[8px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
        <span className="flex items-center gap-0.5">
          <Users size={8} />
          {invite.guest_role === 'temporary_guest' ? 'Guest' : invite.guest_role}
        </span>
        <span>{invite.room_type}</span>
        {invite.max_uses !== null && (
          <span>{invite.uses}/{invite.max_uses} uses</span>
        )}
        {invite.expires_at && (
          <span className="flex items-center gap-0.5">
            <Clock size={8} />
            {expired ? 'Expired' : formatTimeRemaining(invite.expires_at)}
          </span>
        )}
        {!invite.max_uses && !invite.expires_at && <span>No limit</span>}
        {invite.allowed_email_domains && invite.allowed_email_domains.length > 0 && (
          <span>@{invite.allowed_email_domains.join(', @')}</span>
        )}
      </div>
      {invite.permissions && (
        <div className="flex gap-1.5 flex-wrap">
          {(['can_speak', 'can_video', 'can_screen_share', 'can_chat'] as const).map((key) => (
            <span
              key={key}
              className="text-[7px] font-mono px-1 rounded"
              style={{
                background: invite.permissions[key] ? 'var(--color-ok-dim, rgba(0,200,100,0.1))' : 'var(--color-danger-dim, rgba(200,0,0,0.1))',
                color: invite.permissions[key] ? 'var(--color-ok)' : 'var(--color-danger)',
              }}
            >
              {invite.permissions[key] ? '' : ''}{key.replace('can_', '')}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function formatTimeRemaining(expiresAt: string): string {
  const diff = new Date(expiresAt).getTime() - Date.now()
  if (diff <= 0) return 'Expired'
  const hours = Math.floor(diff / 3600000)
  const mins = Math.floor((diff % 3600000) / 60000)
  if (hours > 24) return `${Math.floor(hours / 24)}d ${hours % 24}h`
  if (hours > 0) return `${hours}h ${mins}m`
  return `${mins}m`
}
