import { useState } from 'react'
import {
  Mic,
  MicOff,
  PhoneOff,
  Radio,
  Wifi,
  WifiOff,
  Activity,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'
import { useRoomsStore } from '../../stores/roomsStore'
import { useVoiceRoom } from '../../hooks/useVoiceRoom'
import { ConnectionQuality } from 'livekit-client'
import type { VoiceParticipant, VoiceDiagnostics } from '../../hooks/useVoiceRoom'

export function VoiceRoomPanel({ channelId }: { channelId: string }) {
  const channels = useRoomsStore((s) => s.channels)
  const channel = channels.find((c) => c.id === channelId)
  const { state, error, participants, isMuted, diagnostics, join, leave, toggleMute } = useVoiceRoom(channelId)

  const isConnected = state === 'connected'

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="flex-1 flex flex-col items-center justify-start p-6 max-w-lg mx-auto w-full">
        <div
          className="w-14 h-14 rounded-full flex items-center justify-center mb-3"
          style={{ background: 'var(--color-surface-raised)' }}
        >
          <Radio size={24} style={{ color: isConnected ? 'var(--color-ok)' : 'var(--color-cyan)' }} />
        </div>

        <h3 className="text-sm font-mono font-semibold mb-1" style={{ color: 'var(--color-text-primary)' }}>
          {channel?.name || 'Voice Room'}
        </h3>

        <ConnectionBanner state={state} error={error} />

        {participants.length > 0 && (
          <div
            className="w-full rounded border p-3 mb-3"
            style={{ borderColor: 'var(--color-border)' }}
          >
            <span className="text-[10px] font-mono mb-2 block" style={{ color: 'var(--color-text-secondary)' }}>
              {participants.length} participant{participants.length !== 1 ? 's' : ''}
            </span>
            {participants.map((p) => (
              <ParticipantRow key={p.identity} participant={p} />
            ))}
          </div>
        )}

        <div className="flex gap-2 mb-3">
          {isConnected ? (
            <>
              <button
                onClick={toggleMute}
                className="flex items-center gap-2 text-xs font-mono px-4 py-2 rounded transition-colors"
                style={{
                  background: isMuted ? 'var(--color-danger)' : 'var(--color-surface-raised)',
                  color: isMuted ? 'var(--color-canvas)' : 'var(--color-text-primary)',
                }}
              >
                {isMuted ? <MicOff size={14} /> : <Mic size={14} />}
                {isMuted ? 'Unmute' : 'Mute'}
              </button>
              <button
                onClick={leave}
                className="flex items-center gap-2 text-xs font-mono px-4 py-2 rounded transition-colors"
                style={{ background: 'var(--color-danger)', color: 'var(--color-canvas)' }}
              >
                <PhoneOff size={14} /> Leave
              </button>
            </>
          ) : (
            <button
              onClick={join}
              disabled={state === 'connecting'}
              className="flex items-center gap-2 text-xs font-mono px-4 py-2 rounded transition-colors"
              style={{
                background: state === 'connecting' ? 'var(--color-surface-raised)' : 'var(--color-ok)',
                color: state === 'connecting' ? 'var(--color-text-tertiary)' : 'var(--color-canvas)',
              }}
            >
              <Mic size={14} />
              {state === 'connecting' ? 'Connecting...' : 'Join Voice'}
            </button>
          )}
        </div>

        {state === 'failed' && error && (
          <button
            onClick={join}
            className="text-[10px] font-mono px-3 py-1 rounded border transition-colors mb-3"
            style={{ borderColor: 'var(--color-border)', color: 'var(--color-cyan)' }}
          >
            Retry
          </button>
        )}

        <DiagnosticsPanel diagnostics={diagnostics} state={state} />
      </div>
    </div>
  )
}

function ConnectionBanner({ state, error }: { state: string; error: string | null }) {
  if (state === 'idle') return null

  const config: Record<string, { bg: string; color: string; text: string; icon: typeof Wifi }> = {
    connecting: { bg: 'var(--color-cyan-glow)', color: 'var(--color-cyan)', text: 'Connecting...', icon: Activity },
    connected: { bg: 'var(--color-ok-dim)', color: 'var(--color-ok)', text: 'Connected', icon: Wifi },
    reconnecting: { bg: 'var(--color-warn-dim)', color: 'var(--color-warn)', text: 'Reconnecting...', icon: Activity },
    failed: { bg: 'var(--color-danger-dim)', color: 'var(--color-danger)', text: error || 'Connection failed', icon: WifiOff },
  }

  const c = config[state]
  if (!c) return null
  const Icon = c.icon

  return (
    <div
      className="w-full rounded px-3 py-2 mb-3 flex items-center gap-2"
      style={{ background: c.bg }}
    >
      <Icon size={12} style={{ color: c.color }} className={state === 'connecting' || state === 'reconnecting' ? 'animate-pulse' : ''} />
      <span className="text-[10px] font-mono" style={{ color: c.color }}>{c.text}</span>
    </div>
  )
}

function ParticipantRow({ participant: p }: { participant: VoiceParticipant }) {
  const qualityColor = p.connectionQuality === ConnectionQuality.Excellent ? 'var(--color-ok)'
    : p.connectionQuality === ConnectionQuality.Good ? 'var(--color-ok)'
    : p.connectionQuality === ConnectionQuality.Poor ? 'var(--color-warn)'
    : 'var(--color-text-tertiary)'

  return (
    <div className="flex items-center gap-2 py-1.5">
      <div
        className="w-6 h-6 rounded-full flex items-center justify-center text-[8px] font-mono font-bold"
        style={{ background: 'var(--color-surface-overlay)', color: 'var(--color-text-secondary)' }}
      >
        {p.name.charAt(0).toUpperCase()}
      </div>
      <span className="text-[10px] font-mono flex-1" style={{ color: 'var(--color-text-primary)' }}>
        {p.name}
      </span>
      <div className="flex items-center gap-1.5">
        {p.isSpeaking && (
          <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: 'var(--color-ok)' }} />
        )}
        {p.isMuted && <MicOff size={10} style={{ color: 'var(--color-danger)' }} />}
        <div className="w-1.5 h-1.5 rounded-full" style={{ background: qualityColor }} />
      </div>
    </div>
  )
}

function DiagnosticsPanel({ diagnostics, state }: { diagnostics: VoiceDiagnostics; state: string }) {
  const [expanded, setExpanded] = useState(false)

  if (state === 'idle' && !diagnostics.lastEvent) return null

  return (
    <div
      className="w-full rounded border mt-2"
      style={{ borderColor: 'var(--color-border)' }}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-1 px-3 py-1.5 text-[9px] font-mono"
        style={{ color: 'var(--color-text-tertiary)' }}
      >
        {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
        diagnostics
      </button>
      {expanded && (
        <div className="px-3 pb-2 space-y-1">
          <DiagRow label="state" value={state} />
          <DiagRow label="url" value={diagnostics.livekitUrl} />
          <DiagRow label="room" value={diagnostics.roomName} />
          <DiagRow label="token" value={diagnostics.tokenReceived ? 'received' : 'none'} />
          <DiagRow label="signal" value={diagnostics.signalConnected ? 'connected' : 'no'} />
          <DiagRow label="mic" value={diagnostics.micPermission} />
          <DiagRow label="last" value={diagnostics.lastEvent} />
        </div>
      )}
    </div>
  )
}

function DiagRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="flex gap-2 text-[9px] font-mono">
      <span style={{ color: 'var(--color-text-tertiary)', minWidth: 48 }}>{label}</span>
      <span style={{ color: 'var(--color-text-secondary)', wordBreak: 'break-all' }}>{value ?? '—'}</span>
    </div>
  )
}
