import { useState, useEffect, useRef } from 'react'
import {
  Mic,
  MicOff,
  PhoneOff,
  Phone,
  Radio,
  Wifi,
  WifiOff,
  Activity,
  Video,
  VideoOff,
  Monitor,
  MonitorOff,
  MessageSquare,
  Bug,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'
import { useRoomsStore } from '../../stores/roomsStore'
import { useVoiceRoom } from '../../hooks/useVoiceRoom'
import { ConnectionQuality } from 'livekit-client'
import type { VoiceParticipant, MediaDiagnostics } from '../../hooks/useVoiceRoom'

export function VoiceRoomPanel({ channelId }: { channelId: string }) {
  const channels = useRoomsStore((s) => s.channels)
  const channel = channels.find((c) => c.id === channelId)
  const {
    state,
    error,
    participants,
    isMuted,
    isCameraOn,
    isScreenSharing,
    preJoinMicEnabled,
    diagnostics,
    screenShareSupported,
    setPreJoinMicEnabled,
    join,
    leave,
    toggleMute,
    toggleCamera,
    toggleScreenShare,
  } = useVoiceRoom(channelId)

  const [showDiagnostics, setShowDiagnostics] = useState(false)
  const [showChat, setShowChat] = useState(false)
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

        {/* Video tiles */}
        {isConnected && participants.some((p) => p.hasVideo || p.hasScreenShare) && (
          <div className="w-full grid gap-2 mb-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))' }}>
            {participants.map((p) => (
              (p.hasVideo || p.hasScreenShare) && (
                <VideoTile key={p.identity} participant={p} />
              )
            ))}
          </div>
        )}

        {/* Participants */}
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

        {/* Controls */}
        {isConnected ? (
          <JoinedControls
            isMuted={isMuted}
            isCameraOn={isCameraOn}
            isScreenSharing={isScreenSharing}
            screenShareSupported={screenShareSupported}
            toggleMute={toggleMute}
            toggleCamera={toggleCamera}
            toggleScreenShare={toggleScreenShare}
            onToggleChat={() => setShowChat(!showChat)}
            leave={leave}
          />
        ) : (
          <PreJoinControls
            state={state}
            preJoinMicEnabled={preJoinMicEnabled}
            setPreJoinMicEnabled={setPreJoinMicEnabled}
            onToggleChat={() => setShowChat(!showChat)}
            join={join}
          />
        )}

        {state === 'failed' && error && (
          <button
            onClick={join}
            className="text-[10px] font-mono px-3 py-1 rounded border transition-colors mt-2"
            style={{ borderColor: 'var(--color-border)', color: 'var(--color-cyan)' }}
          >
            Retry
          </button>
        )}

        {/* Diagnostics panel */}
        <button
          onClick={() => setShowDiagnostics(!showDiagnostics)}
          className="flex items-center gap-1 text-[9px] font-mono mt-3 transition-colors"
          style={{ color: 'var(--color-text-quaternary)' }}
        >
          <Bug size={10} />
          Diagnostics
          {showDiagnostics ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
        </button>

        {showDiagnostics && (
          <DiagnosticsView diagnostics={diagnostics} state={state} />
        )}
      </div>
    </div>
  )
}

function PreJoinControls({
  state,
  preJoinMicEnabled,
  setPreJoinMicEnabled,
  onToggleChat,
  join,
}: {
  state: string
  preJoinMicEnabled: boolean
  setPreJoinMicEnabled: (v: boolean) => void
  onToggleChat: () => void
  join: () => Promise<void>
}) {
  return (
    <div className="flex gap-2 mb-3 flex-wrap justify-center">
      {/* Mic toggle (pre-join) */}
      <button
        onClick={() => setPreJoinMicEnabled(!preJoinMicEnabled)}
        className="flex items-center gap-2 text-xs font-mono px-4 py-2 rounded transition-colors"
        style={{
          background: preJoinMicEnabled ? 'var(--color-surface-raised)' : 'var(--color-danger)',
          color: preJoinMicEnabled ? 'var(--color-text-primary)' : 'var(--color-canvas)',
        }}
        title={preJoinMicEnabled ? 'Will join unmuted' : 'Will join muted'}
      >
        {preJoinMicEnabled ? <Mic size={14} /> : <MicOff size={14} />}
        {preJoinMicEnabled ? 'Mic On' : 'Mic Off'}
      </button>

      {/* Join button */}
      <button
        onClick={join}
        disabled={state === 'connecting'}
        className="flex items-center gap-2 text-xs font-mono px-4 py-2 rounded transition-colors"
        style={{
          background: state === 'connecting' ? 'var(--color-surface-raised)' : 'var(--color-ok)',
          color: state === 'connecting' ? 'var(--color-text-tertiary)' : 'var(--color-canvas)',
        }}
      >
        <Phone size={14} />
        {state === 'connecting' ? 'Connecting...' : 'Join Voice'}
      </button>

      {/* Chat toggle */}
      <button
        onClick={onToggleChat}
        className="flex items-center gap-2 text-xs font-mono px-3 py-2 rounded transition-colors"
        style={{
          background: 'var(--color-surface-raised)',
          color: 'var(--color-text-secondary)',
        }}
      >
        <MessageSquare size={14} />
        Chat
      </button>
    </div>
  )
}

function JoinedControls({
  isMuted,
  isCameraOn,
  isScreenSharing,
  screenShareSupported,
  toggleMute,
  toggleCamera,
  toggleScreenShare,
  onToggleChat,
  leave,
}: {
  isMuted: boolean
  isCameraOn: boolean
  isScreenSharing: boolean
  screenShareSupported: boolean
  toggleMute: () => void
  toggleCamera: () => Promise<void>
  toggleScreenShare: () => Promise<void>
  onToggleChat: () => void
  leave: () => void
}) {
  return (
    <div className="flex gap-2 mb-3 flex-wrap justify-center">
      {/* Mute/Unmute */}
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

      {/* Video */}
      <button
        onClick={toggleCamera}
        className="flex items-center gap-2 text-xs font-mono px-3 py-2 rounded transition-colors"
        style={{
          background: isCameraOn ? 'var(--color-cyan-glow)' : 'var(--color-surface-raised)',
          color: isCameraOn ? 'var(--color-cyan)' : 'var(--color-text-secondary)',
        }}
      >
        {isCameraOn ? <Video size={14} /> : <VideoOff size={14} />}
        {isCameraOn ? 'Video On' : 'Video Off'}
      </button>

      {/* Screen share */}
      <button
        onClick={screenShareSupported ? toggleScreenShare : undefined}
        disabled={!screenShareSupported}
        className="flex items-center gap-2 text-xs font-mono px-3 py-2 rounded transition-colors relative group"
        style={{
          background: isScreenSharing ? 'var(--color-cyan-glow)' : 'var(--color-surface-raised)',
          color: !screenShareSupported
            ? 'var(--color-text-quaternary)'
            : isScreenSharing
            ? 'var(--color-cyan)'
            : 'var(--color-text-secondary)',
          cursor: screenShareSupported ? 'pointer' : 'not-allowed',
          opacity: screenShareSupported ? 1 : 0.5,
        }}
        title={
          screenShareSupported
            ? isScreenSharing ? 'Stop sharing' : 'Share screen'
            : 'Screen share unavailable on iOS Safari. Join from desktop to share.'
        }
      >
        {isScreenSharing ? <Monitor size={14} /> : <MonitorOff size={14} />}
        Share
        {!screenShareSupported && (
          <div
            className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 rounded text-[9px] font-mono whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"
            style={{ background: 'var(--color-surface-overlay)', color: 'var(--color-warn)' }}
          >
            Unavailable on iOS Safari
          </div>
        )}
      </button>

      {/* Chat */}
      <button
        onClick={onToggleChat}
        className="flex items-center gap-2 text-xs font-mono px-3 py-2 rounded transition-colors"
        style={{
          background: 'var(--color-surface-raised)',
          color: 'var(--color-text-secondary)',
        }}
      >
        <MessageSquare size={14} />
        Chat
      </button>

      {/* Leave */}
      <button
        onClick={leave}
        className="flex items-center gap-2 text-xs font-mono px-4 py-2 rounded transition-colors"
        style={{ background: 'var(--color-danger)', color: 'var(--color-canvas)' }}
      >
        <PhoneOff size={14} /> Leave
      </button>
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
        {p.hasVideo && <Video size={10} style={{ color: 'var(--color-cyan)' }} />}
        {p.hasScreenShare && <Monitor size={10} style={{ color: 'var(--color-cyan)' }} />}
        <div className="w-1.5 h-1.5 rounded-full" style={{ background: qualityColor }} />
      </div>
    </div>
  )
}

function VideoTile({ participant: p }: { participant: VoiceParticipant }) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const screenRef = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    if (p.videoTrack && videoRef.current) {
      p.videoTrack.attach(videoRef.current)
      return () => { p.videoTrack?.detach(videoRef.current!) }
    }
  }, [p.videoTrack])

  useEffect(() => {
    if (p.screenTrack && screenRef.current) {
      p.screenTrack.attach(screenRef.current)
      return () => { p.screenTrack?.detach(screenRef.current!) }
    }
  }, [p.screenTrack])

  return (
    <>
      {p.hasVideo && (
        <div className="relative rounded overflow-hidden" style={{ background: 'var(--color-surface-overlay)' }}>
          <video ref={videoRef} autoPlay playsInline muted className="w-full aspect-video object-cover" />
          <span
            className="absolute bottom-1 left-1 text-[9px] font-mono px-1 rounded"
            style={{ background: 'rgba(0,0,0,0.6)', color: 'var(--color-text-primary)' }}
          >
            {p.name}
          </span>
        </div>
      )}
      {p.hasScreenShare && (
        <div className="relative rounded overflow-hidden" style={{ background: 'var(--color-surface-overlay)' }}>
          <video ref={screenRef} autoPlay playsInline muted className="w-full aspect-video object-contain" />
          <span
            className="absolute bottom-1 left-1 text-[9px] font-mono px-1 rounded flex items-center gap-1"
            style={{ background: 'rgba(0,0,0,0.6)', color: 'var(--color-cyan)' }}
          >
            <Monitor size={8} /> {p.name}
          </span>
        </div>
      )}
    </>
  )
}

function DiagnosticsView({ diagnostics, state }: { diagnostics: MediaDiagnostics; state: string }) {
  const rows: [string, string][] = [
    ['mic permission', String(diagnostics.micPermission)],
    ['mic enabled requested', String(diagnostics.micEnabledRequested)],
    ['mic enabled actual', String(diagnostics.micEnabledActual)],
    ['audio track sid', diagnostics.audioTrackSid || '—'],
    ['camera permission', String(diagnostics.cameraPermission)],
    ['camera enabled actual', String(diagnostics.cameraEnabledActual)],
    ['screen share support', String(diagnostics.screenShareSupported)],
    ['connection state', state],
    ['last media error', diagnostics.lastMediaError || '—'],
  ]

  return (
    <div
      className="w-full rounded border p-2 mt-2"
      style={{ borderColor: 'var(--color-border)' }}
    >
      <span className="text-[9px] font-mono font-semibold block mb-1" style={{ color: 'var(--color-text-secondary)' }}>
        Media Diagnostics
      </span>
      {rows.map(([label, value]) => (
        <div key={label} className="flex justify-between py-0.5">
          <span className="text-[9px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>{label}</span>
          <span
            className="text-[9px] font-mono"
            style={{
              color: value === 'denied' || value.includes('fail') || value.includes('error')
                ? 'var(--color-danger)'
                : value === 'granted' || value === 'true'
                ? 'var(--color-ok)'
                : 'var(--color-text-secondary)',
            }}
          >
            {value}
          </span>
        </div>
      ))}
    </div>
  )
}
