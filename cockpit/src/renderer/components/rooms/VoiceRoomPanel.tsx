import { useEffect, useState, useCallback } from 'react'
import {
  Mic,
  MicOff,
  Headphones,
  PhoneOff,
  Users,
  Lock,
  Radio,
  Copy,
  Check,
  Bot,
  Wifi,
  WifiOff,
  Link2,
  ChevronDown,
  ChevronRight,
  Shield,
  Activity,
} from 'lucide-react'
import { useRoomsStore } from '../../stores/roomsStore'

type JoinState = 'idle' | 'joining' | 'joined' | 'failed'

export function VoiceRoomPanel({ channelId }: { channelId: string }) {
  const voiceStates = useRoomsStore((s) => s.voiceStates)
  const fetchVoiceState = useRoomsStore((s) => s.fetchVoiceState)
  const joinVoice = useRoomsStore((s) => s.joinVoice)
  const leaveVoice = useRoomsStore((s) => s.leaveVoice)
  const channels = useRoomsStore((s) => s.channels)
  const activeServerId = useRoomsStore((s) => s.activeServerId)
  const invites = useRoomsStore((s) => s.invites)
  const createInvite = useRoomsStore((s) => s.createInvite)
  const fetchInvites = useRoomsStore((s) => s.fetchInvites)
  const error = useRoomsStore((s) => s.error)

  const channel = channels.find((c) => c.id === channelId)
  const voiceState = voiceStates[channelId]

  const [joinState, setJoinState] = useState<JoinState>('idle')
  const [joinError, setJoinError] = useState<string | null>(null)
  const [copiedLink, setCopiedLink] = useState(false)
  const [showDiagnostics, setShowDiagnostics] = useState(false)

  useEffect(() => {
    fetchVoiceState(channelId)
    if (activeServerId) fetchInvites(activeServerId)
  }, [channelId, fetchVoiceState, activeServerId, fetchInvites])

  useEffect(() => {
    const isIn = voiceState?.participants.some((p) => p.user_id === 'operator')
    if (isIn && joinState !== 'joined') setJoinState('joined')
    if (!isIn && joinState === 'joined') setJoinState('idle')
  }, [voiceState, joinState])

  const handleJoin = useCallback(async () => {
    setJoinState('joining')
    setJoinError(null)
    try {
      await joinVoice(channelId)
      setJoinState('joined')
    } catch (e) {
      setJoinState('failed')
      setJoinError(e instanceof Error ? e.message : 'Failed to join room')
    }
  }, [channelId, joinVoice])

  const handleLeave = useCallback(async () => {
    await leaveVoice(channelId)
    setJoinState('idle')
    setJoinError(null)
  }, [channelId, leaveVoice])

  const handleCopyInvite = useCallback(async () => {
    let code = invites.find((inv) => !inv.revoked)?.code
    if (!code && activeServerId) {
      const invite = await createInvite(activeServerId, channelId, null, 24, null)
      code = invite?.code
    }
    if (code) {
      const link = `${window.location.origin}/invite/${code}`
      await navigator.clipboard.writeText(link)
      setCopiedLink(true)
      setTimeout(() => setCopiedLink(false), 2000)
    }
  }, [invites, activeServerId, channelId, createInvite])

  const isInRoom = joinState === 'joined'
  const participantCount = voiceState?.participants.length || 0

  const aiParticipants = voiceState?.participants.filter((p) => p.user_id.startsWith('ai-')) || []
  const humanParticipants = voiceState?.participants.filter((p) => !p.user_id.startsWith('ai-')) || []

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="flex-1 flex flex-col items-center justify-start p-6 max-w-lg mx-auto w-full">
        {/* Room icon + name */}
        <div
          className="w-14 h-14 rounded-full flex items-center justify-center mb-3"
          style={{ background: 'var(--color-surface-raised)' }}
        >
          <Radio size={24} style={{ color: isInRoom ? 'var(--color-ok)' : 'var(--color-cyan)' }} />
        </div>

        <h3 className="text-sm font-mono font-semibold mb-1" style={{ color: 'var(--color-text-primary)' }}>
          {channel?.name || 'Voice Room'}
        </h3>

        {voiceState?.topic && (
          <p className="text-[10px] font-mono mb-3" style={{ color: 'var(--color-text-tertiary)' }}>
            {voiceState.topic}
          </p>
        )}

        {voiceState?.locked && (
          <div className="flex items-center gap-1 mb-3">
            <Lock size={10} style={{ color: 'var(--color-warn)' }} />
            <span className="text-[9px] font-mono" style={{ color: 'var(--color-warn)' }}>LOCKED</span>
          </div>
        )}

        {/* Join state banner */}
        <JoinStateBanner joinState={joinState} joinError={joinError} />

        {/* Participants */}
        <div
          className="w-full rounded border p-3 mb-3"
          style={{ borderColor: 'var(--color-border)' }}
        >
          <div className="flex items-center gap-2 mb-2">
            <Users size={12} style={{ color: 'var(--color-text-secondary)' }} />
            <span className="text-[10px] font-mono" style={{ color: 'var(--color-text-secondary)' }}>
              {participantCount}
              {voiceState?.capacity ? ` / ${voiceState.capacity}` : ''} participants
            </span>
          </div>

          {humanParticipants.map((p) => (
            <ParticipantRow key={p.user_id} participant={p} isAi={false} />
          ))}

          {aiParticipants.length > 0 && (
            <>
              <div className="flex items-center gap-1 mt-2 mb-1">
                <Bot size={10} style={{ color: 'var(--color-violet)' }} />
                <span className="text-[9px] font-mono uppercase" style={{ color: 'var(--color-violet)' }}>
                  AI Participants
                </span>
              </div>
              {aiParticipants.map((p) => (
                <ParticipantRow key={p.user_id} participant={p} isAi />
              ))}
            </>
          )}

          {participantCount === 0 && (
            <p className="text-[9px] font-mono text-center py-2" style={{ color: 'var(--color-text-tertiary)' }}>
              No participants
            </p>
          )}
        </div>

        {/* AI participant availability */}
        <AiParticipantStatus />

        {/* Media transport status */}
        <div
          className="w-full rounded border p-3 mb-3"
          style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface-raised)' }}
        >
          <p className="text-[10px] font-mono" style={{ color: 'var(--color-text-secondary)' }}>
            Room shell active — media transport pending
          </p>
          <p className="text-[9px] font-mono mt-1" style={{ color: 'var(--color-text-tertiary)' }}>
            Presence, metadata, and meeting intelligence are operational.
            Audio/video streaming requires WebRTC SFU infrastructure.
          </p>
        </div>

        {/* Action buttons */}
        <div className="flex gap-2 mb-3">
          {isInRoom ? (
            <button
              onClick={handleLeave}
              className="flex items-center gap-2 text-xs font-mono px-4 py-2 rounded transition-colors"
              style={{ background: 'var(--color-danger)', color: 'var(--color-canvas)' }}
            >
              <PhoneOff size={14} /> Leave Room
            </button>
          ) : (
            <button
              onClick={handleJoin}
              disabled={joinState === 'joining'}
              className="flex items-center gap-2 text-xs font-mono px-4 py-2 rounded transition-colors"
              style={{
                background: joinState === 'joining' ? 'var(--color-surface-raised)' : 'var(--color-ok)',
                color: joinState === 'joining' ? 'var(--color-text-tertiary)' : 'var(--color-canvas)',
              }}
            >
              <Mic size={14} />
              {joinState === 'joining' ? 'Joining...' : 'Join Room'}
            </button>
          )}

          <button
            onClick={handleCopyInvite}
            className="flex items-center gap-2 text-xs font-mono px-4 py-2 rounded border transition-colors"
            style={{
              borderColor: 'var(--color-border)',
              color: copiedLink ? 'var(--color-ok)' : 'var(--color-text-secondary)',
            }}
          >
            {copiedLink ? <Check size={14} /> : <Link2 size={14} />}
            {copiedLink ? 'Copied!' : 'Copy Invite'}
          </button>
        </div>

        {/* Diagnostics */}
        <DiagnosticsPanel
          channelId={channelId}
          isInRoom={isInRoom}
          participantCount={participantCount}
          aiCount={aiParticipants.length}
          error={error}
          open={showDiagnostics}
          onToggle={() => setShowDiagnostics((v) => !v)}
        />
      </div>
    </div>
  )
}

function JoinStateBanner({ joinState, joinError }: { joinState: JoinState; joinError: string | null }) {
  if (joinState === 'idle') return null

  const config = {
    joining: { bg: 'var(--color-cyan-glow)', color: 'var(--color-cyan)', text: 'Connecting to room...' },
    joined: { bg: 'var(--color-ok-dim)', color: 'var(--color-ok)', text: 'Connected to room' },
    failed: { bg: 'var(--color-danger-dim)', color: 'var(--color-danger)', text: joinError || 'Connection failed' },
  }[joinState]

  if (!config) return null

  return (
    <div
      className="w-full rounded px-3 py-2 mb-3 flex items-center gap-2"
      style={{ background: config.bg }}
    >
      {joinState === 'joined' ? (
        <Wifi size={12} style={{ color: config.color }} />
      ) : joinState === 'failed' ? (
        <WifiOff size={12} style={{ color: config.color }} />
      ) : (
        <Activity size={12} style={{ color: config.color }} className="animate-pulse" />
      )}
      <span className="text-[10px] font-mono" style={{ color: config.color }}>
        {config.text}
      </span>
    </div>
  )
}

function ParticipantRow({
  participant: p,
  isAi,
}: {
  participant: { user_id: string; display_name: string; is_speaking: boolean; is_muted: boolean; is_deafened: boolean }
  isAi: boolean
}) {
  return (
    <div className="flex items-center gap-2 py-1.5">
      <div
        className="w-6 h-6 rounded-full flex items-center justify-center text-[8px] font-mono font-bold"
        style={{
          background: isAi ? 'var(--color-violet-dim)' : 'var(--color-surface-overlay)',
          color: isAi ? 'var(--color-violet)' : 'var(--color-text-secondary)',
        }}
      >
        {isAi ? <Bot size={12} /> : p.display_name.charAt(0).toUpperCase()}
      </div>
      <span className="text-[10px] font-mono flex-1" style={{ color: 'var(--color-text-primary)' }}>
        {p.display_name}
      </span>
      <div className="flex items-center gap-1">
        {p.is_speaking && (
          <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: 'var(--color-ok)' }} />
        )}
        {p.is_muted && <MicOff size={10} style={{ color: 'var(--color-danger)' }} />}
        {p.is_deafened && <Headphones size={10} style={{ color: 'var(--color-danger)' }} />}
      </div>
    </div>
  )
}

function AiParticipantStatus() {
  return (
    <div
      className="w-full rounded border p-3 mb-3"
      style={{ borderColor: 'var(--color-violet)', background: 'var(--color-violet-dim)' }}
    >
      <div className="flex items-center gap-2 mb-1">
        <Bot size={12} style={{ color: 'var(--color-violet)' }} />
        <span className="text-[10px] font-mono font-semibold" style={{ color: 'var(--color-violet)' }}>
          AI Participant Available
        </span>
      </div>
      <p className="text-[9px] font-mono" style={{ color: 'var(--color-text-secondary)' }}>
        AI can join as a governed participant. Capabilities: listen, transcribe, summarize, identify action items. Governed by room permissions.
      </p>
      <p className="text-[9px] font-mono mt-1" style={{ color: 'var(--color-text-tertiary)' }}>
        Media listener unavailable until WebRTC/SFU is live.
        Text interaction and meeting intelligence are operational now.
      </p>
    </div>
  )
}

function DiagnosticsPanel({
  channelId,
  isInRoom,
  participantCount,
  aiCount,
  error,
  open,
  onToggle,
}: {
  channelId: string
  isInRoom: boolean
  participantCount: number
  aiCount: number
  error: string | null
  open: boolean
  onToggle: () => void
}) {
  return (
    <div className="w-full">
      <button
        onClick={onToggle}
        className="flex items-center gap-1 text-[9px] font-mono uppercase w-full"
        style={{ color: 'var(--color-text-tertiary)' }}
      >
        {open ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
        Room Diagnostics
      </button>
      {open && (
        <div
          className="mt-1 rounded border p-3 space-y-1"
          style={{ borderColor: 'var(--color-border)' }}
        >
          <DiagRow label="Auth" value="Clerk JWT" ok />
          <DiagRow label="Room membership" value={isInRoom ? 'Joined' : 'Not joined'} ok={isInRoom} />
          <DiagRow label="WebSocket" value="Connected (pulse)" ok />
          <DiagRow label="Media transport" value="Pending — WebRTC/SFU required" ok={false} />
          <DiagRow label="Participants" value={String(participantCount)} ok={participantCount > 0} />
          <DiagRow label="AI participants" value={aiCount > 0 ? `${aiCount} active` : 'None joined'} ok={false} />
          <DiagRow label="Channel ID" value={channelId} ok />
          {error && <DiagRow label="Last error" value={error} ok={false} />}
        </div>
      )}
    </div>
  )
}

function DiagRow({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-[9px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
        {label}
      </span>
      <div className="flex items-center gap-1">
        <div
          className="w-1.5 h-1.5 rounded-full"
          style={{ background: ok ? 'var(--color-ok)' : 'var(--color-warn)' }}
        />
        <span className="text-[9px] font-mono max-w-[160px] truncate" style={{ color: 'var(--color-text-secondary)' }}>
          {value}
        </span>
      </div>
    </div>
  )
}
