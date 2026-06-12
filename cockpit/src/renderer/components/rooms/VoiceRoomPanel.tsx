import { useEffect, useRef, useState, useCallback, type FormEvent } from 'react'
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
  Video,
  VideoOff,
  Monitor,
  MonitorOff,
  MessageSquare,
  Send,
  Signal,
  SignalHigh,
  SignalLow,
  SignalZero,
  Plus,
  X,
  Maximize2,
  Minimize2,
  Pin,
  AppWindow,
  Globe,
  Camera,
  ScreenShare,
  AlertTriangle,
} from 'lucide-react'
import { useRoomsStore } from '../../stores/roomsStore'
import { useVoiceRoom } from '../../hooks/useVoiceRoom'
import { ConnectionQuality } from 'livekit-client'
import type { VoiceParticipant, VoiceDiagnostics, VoiceRoomState, MediaStreamSource, StreamSourceType } from '../../hooks/useVoiceRoom'
import type { RoomMessage } from '../../types/rooms'

const SOURCE_TYPE_ICONS: Record<StreamSourceType, typeof Monitor> = {
  camera: Camera,
  screen: Monitor,
  window: AppWindow,
  tab: Globe,
  application: AppWindow,
  second_camera: Camera,
}

const SOURCE_TYPE_LABELS: Record<StreamSourceType, string> = {
  camera: 'Camera',
  screen: 'Screen',
  window: 'Window',
  tab: 'Browser Tab',
  application: 'Application',
  second_camera: 'Camera 2',
}

function isIOSSafari(): boolean {
  if (typeof navigator === 'undefined') return false
  const ua = navigator.userAgent
  return /iPad|iPhone|iPod/.test(ua) || (ua.includes('Macintosh') && 'ontouchend' in document)
}

export function VoiceRoomPanel({ channelId }: { channelId: string }) {
  const channels = useRoomsStore((s) => s.channels)
  const channel = channels.find((c) => c.id === channelId)
  const voice = useVoiceRoom(channelId)
  const [chatOpen, setChatOpen] = useState(false)
  const [focusedStream, setFocusedStream] = useState<string | null>(null)

  const isConnected = voice.state === 'connected'
  const showChat = chatOpen && isConnected

  const allStreams: Array<MediaStreamSource & { participantName: string }> = []
  voice.streams.forEach((sources, identity) => {
    const participant = voice.participants.find(p => p.identity === identity)
    const name = participant?.name || identity
    for (const source of sources) {
      allStreams.push({ ...source, participantName: name })
    }
  })

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex flex-1 min-h-0">
        <div className={`flex-1 flex flex-col min-h-0 ${showChat ? 'border-r' : ''}`}
          style={{ borderColor: 'var(--color-border)' }}
        >
          <div className="flex-1 overflow-y-auto">
            <div className="flex flex-col items-center justify-start p-4 max-w-3xl mx-auto w-full">
              <ChannelHeader name={channel?.name || 'Voice Room'} isConnected={isConnected} />
              <ConnectionBanner state={voice.state} error={voice.error} reconnectAttempts={voice.diagnostics.reconnectAttempts} />

              {isConnected && allStreams.length > 0 && (
                <StreamGrid
                  streams={allStreams}
                  focusedStream={focusedStream}
                  onFocus={setFocusedStream}
                  getTrackElement={voice.getTrackElement}
                  onStopStream={voice.stopStream}
                  localIdentity={voice.participants.find(p => p.identity === voice.diagnostics.participantIdentity)?.identity}
                />
              )}

              {isConnected && voice.participants.length > 0 && (
                <ParticipantGrid participants={voice.participants} />
              )}

              {voice.state === 'disconnected' && (
                <div className="w-full rounded px-3 py-2 mb-3 text-center"
                  style={{ background: 'var(--color-warn-dim)' }}
                >
                  <p className="text-[10px] font-mono mb-1" style={{ color: 'var(--color-warn)' }}>
                    Connection lost
                  </p>
                  <button onClick={voice.join}
                    className="text-[10px] font-mono px-3 py-1 rounded"
                    style={{ background: 'var(--color-ok)', color: 'var(--color-canvas)' }}
                  >
                    Reconnect
                  </button>
                </div>
              )}

              <DiagnosticsPanel diagnostics={voice.diagnostics} state={voice.state} />
            </div>
          </div>

          <ControlBar
            state={voice.state}
            isMuted={voice.isMuted}
            isVideoOn={voice.isVideoOn}
            localStreamCount={voice.localStreams.filter(s => s.sourceType !== 'camera').length}
            canAddStream={voice.canAddStream}
            chatOpen={chatOpen}
            error={voice.error}
            onJoin={voice.join}
            onLeave={voice.leave}
            onToggleMute={voice.toggleMute}
            onToggleVideo={voice.toggleVideo}
            onAddScreenShare={voice.addScreenShare}
            onStopAllStreams={voice.stopAllStreams}
            onToggleChat={() => setChatOpen(!chatOpen)}
          />
        </div>

        {showChat && (
          <div className="w-80 flex flex-col min-h-0" style={{ maxWidth: '50%' }}>
            <VoiceChat channelId={channelId} />
          </div>
        )}
      </div>
    </div>
  )
}

function ChannelHeader({ name, isConnected }: { name: string; isConnected: boolean }) {
  return (
    <div className="flex flex-col items-center mb-3">
      <div className="w-12 h-12 rounded-full flex items-center justify-center mb-2"
        style={{ background: 'var(--color-surface-raised)' }}
      >
        <Radio size={20} style={{ color: isConnected ? 'var(--color-ok)' : 'var(--color-cyan)' }} />
      </div>
      <h3 className="text-sm font-mono font-semibold" style={{ color: 'var(--color-text-primary)' }}>
        {name}
      </h3>
    </div>
  )
}

function StreamGrid({
  streams,
  focusedStream,
  onFocus,
  getTrackElement,
  onStopStream,
  localIdentity,
}: {
  streams: Array<MediaStreamSource & { participantName: string }>
  focusedStream: string | null
  onFocus: (sid: string | null) => void
  getTrackElement: (sid: string) => HTMLVideoElement | null
  onStopStream: (sid: string) => Promise<void>
  localIdentity: string | undefined
}) {
  if (streams.length === 0) return null

  const focused = focusedStream ? streams.find(s => s.trackSid === focusedStream) : null

  if (focused) {
    return (
      <div className="w-full mb-3">
        <StreamTile
          stream={focused}
          focused
          getTrackElement={getTrackElement}
          onFocus={() => onFocus(null)}
          onStop={focused.participantIdentity === localIdentity ? () => onStopStream(focused.trackSid) : undefined}
          isOwner={focused.participantIdentity === localIdentity}
        />
        {streams.length > 1 && (
          <div className="flex gap-1.5 mt-1.5 overflow-x-auto pb-1">
            {streams.filter(s => s.trackSid !== focusedStream).map(s => (
              <div key={s.trackSid} className="flex-shrink-0" style={{ width: 120, height: 68 }}>
                <StreamTile
                  stream={s}
                  compact
                  getTrackElement={getTrackElement}
                  onFocus={() => onFocus(s.trackSid)}
                  onStop={s.participantIdentity === localIdentity ? () => onStopStream(s.trackSid) : undefined}
                  isOwner={s.participantIdentity === localIdentity}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  const gridCols = streams.length === 1 ? 'grid-cols-1' :
    streams.length <= 4 ? 'grid-cols-2' : 'grid-cols-3'

  return (
    <div className={`w-full grid ${gridCols} gap-1.5 mb-3`}>
      {streams.map(s => (
        <StreamTile
          key={s.trackSid}
          stream={s}
          getTrackElement={getTrackElement}
          onFocus={() => onFocus(s.trackSid)}
          onStop={s.participantIdentity === localIdentity ? () => onStopStream(s.trackSid) : undefined}
          isOwner={s.participantIdentity === localIdentity}
        />
      ))}
    </div>
  )
}

function StreamTile({
  stream,
  focused,
  compact,
  getTrackElement,
  onFocus,
  onStop,
  isOwner,
}: {
  stream: MediaStreamSource & { participantName: string }
  focused?: boolean
  compact?: boolean
  getTrackElement: (sid: string) => HTMLVideoElement | null
  onFocus: () => void
  onStop?: () => void
  isOwner: boolean
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const videoMountedRef = useRef(false)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const el = getTrackElement(stream.trackSid)
    if (el && !videoMountedRef.current) {
      el.style.display = 'block'
      el.style.width = '100%'
      el.style.height = '100%'
      el.style.objectFit = 'contain'
      el.style.borderRadius = '4px'
      container.appendChild(el)
      videoMountedRef.current = true
    }

    return () => {
      if (el && videoMountedRef.current) {
        el.style.display = 'none'
        document.body.appendChild(el)
        videoMountedRef.current = false
      }
    }
  }, [stream.trackSid, getTrackElement])

  const Icon = SOURCE_TYPE_ICONS[stream.sourceType] || Monitor
  const label = SOURCE_TYPE_LABELS[stream.sourceType] || stream.sourceType
  const dims = stream.dimensions
  const fps = stream.frameRate

  return (
    <div
      className={`relative rounded border overflow-hidden group ${focused ? 'aspect-video' : compact ? '' : 'aspect-video'}`}
      style={{
        borderColor: 'var(--color-border)',
        background: 'var(--color-surface)',
        height: compact ? '100%' : undefined,
      }}
    >
      <div ref={containerRef} className="absolute inset-0" />

      {/* Overlay info bar */}
      <div className="absolute bottom-0 left-0 right-0 px-2 py-1 flex items-center gap-1.5"
        style={{ background: 'rgba(0,0,0,0.6)' }}
      >
        <Icon size={compact ? 8 : 10} style={{ color: 'var(--color-cyan)' }} />
        {!compact && (
          <>
            <span className="text-[9px] font-mono truncate" style={{ color: '#fff' }}>
              {stream.participantName}
            </span>
            <span className="text-[8px] font-mono" style={{ color: 'rgba(255,255,255,0.6)' }}>
              {label}
            </span>
            {dims && (
              <span className="text-[7px] font-mono ml-auto" style={{ color: 'rgba(255,255,255,0.5)' }}>
                {dims.width}x{dims.height}{fps ? `@${Math.round(fps)}` : ''}
              </span>
            )}
          </>
        )}
      </div>

      {/* Hover controls */}
      <div className="absolute top-1 right-1 flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
        <button onClick={onFocus}
          className="p-1 rounded"
          style={{ background: 'rgba(0,0,0,0.6)' }}
          title={focused ? 'Minimize' : 'Focus'}
        >
          {focused ? <Minimize2 size={10} color="#fff" /> : <Maximize2 size={10} color="#fff" />}
        </button>
        {isOwner && onStop && (
          <button onClick={onStop}
            className="p-1 rounded"
            style={{ background: 'rgba(220,38,38,0.8)' }}
            title="Stop stream"
          >
            <X size={10} color="#fff" />
          </button>
        )}
      </div>
    </div>
  )
}

function ControlBar({
  state,
  isMuted,
  isVideoOn,
  localStreamCount,
  canAddStream,
  chatOpen,
  error,
  onJoin,
  onLeave,
  onToggleMute,
  onToggleVideo,
  onAddScreenShare,
  onStopAllStreams,
  onToggleChat,
}: {
  state: VoiceRoomState
  isMuted: boolean
  isVideoOn: boolean
  localStreamCount: number
  canAddStream: boolean
  chatOpen: boolean
  error: string | null
  onJoin: () => void
  onLeave: () => void
  onToggleMute: () => void
  onToggleVideo: () => void
  onAddScreenShare: () => void
  onStopAllStreams: () => void
  onToggleChat: () => void
}) {
  const [shareMenuOpen, setShareMenuOpen] = useState(false)
  const isConnected = state === 'connected' || state === 'reconnecting'
  const iosBlocked = isIOSSafari()

  if (!isConnected && state !== 'failed' && state !== 'disconnected') {
    return (
      <div className="flex items-center justify-center px-4 py-3 border-t shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <button onClick={onJoin}
          disabled={state === 'connecting' || state === 'requesting-permission'}
          className="flex items-center gap-2 text-xs font-mono px-6 py-2.5 rounded transition-colors"
          style={{
            background: state === 'connecting' ? 'var(--color-surface-raised)' : 'var(--color-ok)',
            color: state === 'connecting' ? 'var(--color-text-tertiary)' : 'var(--color-canvas)',
          }}
        >
          <Mic size={14} />
          {state === 'connecting' ? 'Connecting...' : 'Join Voice'}
        </button>
      </div>
    )
  }

  if (state === 'failed' || state === 'disconnected') {
    return (
      <div className="flex items-center justify-center gap-2 px-4 py-3 border-t shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <button onClick={onJoin}
          className="flex items-center gap-2 text-xs font-mono px-4 py-2 rounded transition-colors"
          style={{ background: 'var(--color-ok)', color: 'var(--color-canvas)' }}
        >
          <Mic size={14} /> Retry
        </button>
        {error && (
          <span className="text-[9px] font-mono max-w-48 truncate" style={{ color: 'var(--color-danger)' }}>
            {error}
          </span>
        )}
      </div>
    )
  }

  return (
    <div className="relative flex items-center justify-center gap-1.5 px-3 py-2.5 border-t shrink-0"
      style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface)' }}
    >
      <ControlButton
        active={!isMuted}
        danger={isMuted}
        icon={isMuted ? MicOff : Mic}
        label={isMuted ? 'Unmute' : 'Mute'}
        onClick={onToggleMute}
      />
      <ControlButton
        active={isVideoOn}
        icon={isVideoOn ? Video : VideoOff}
        label={isVideoOn ? 'Stop Video' : 'Video'}
        onClick={onToggleVideo}
      />

      {/* Share button with count badge */}
      <div className="relative">
        <ControlButton
          active={localStreamCount > 0}
          icon={localStreamCount > 0 ? ScreenShare : Monitor}
          label={localStreamCount > 0 ? `Sharing (${localStreamCount})` : 'Share'}
          onClick={() => setShareMenuOpen(!shareMenuOpen)}
        />
        {localStreamCount > 0 && (
          <div className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full flex items-center justify-center text-[7px] font-mono font-bold"
            style={{ background: 'var(--color-cyan)', color: 'var(--color-canvas)' }}
          >
            {localStreamCount}
          </div>
        )}
      </div>

      <ControlButton
        active={chatOpen}
        icon={MessageSquare}
        label="Chat"
        onClick={onToggleChat}
      />
      <div className="w-px h-6 mx-1" style={{ background: 'var(--color-border)' }} />
      <button onClick={onLeave}
        className="flex items-center gap-1.5 text-[10px] font-mono px-3 py-2 rounded transition-colors"
        style={{ background: 'var(--color-danger)', color: 'var(--color-canvas)' }}
      >
        <PhoneOff size={13} /> Leave
      </button>

      {/* Share menu popup */}
      {shareMenuOpen && (
        <ShareMenu
          canAdd={canAddStream}
          iosBlocked={iosBlocked}
          localStreamCount={localStreamCount}
          onAddScreen={() => { onAddScreenShare(); setShareMenuOpen(false) }}
          onStopAll={() => { onStopAllStreams(); setShareMenuOpen(false) }}
          onClose={() => setShareMenuOpen(false)}
        />
      )}
    </div>
  )
}

function ShareMenu({
  canAdd,
  iosBlocked,
  localStreamCount,
  onAddScreen,
  onStopAll,
  onClose,
}: {
  canAdd: boolean
  iosBlocked: boolean
  localStreamCount: number
  onAddScreen: () => void
  onStopAll: () => void
  onClose: () => void
}) {
  return (
    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 rounded-lg border shadow-lg overflow-hidden"
      style={{ background: 'var(--color-surface-raised)', borderColor: 'var(--color-border)', zIndex: 50 }}
    >
      <div className="px-3 py-2 border-b flex items-center justify-between"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <span className="text-[10px] font-mono font-semibold" style={{ color: 'var(--color-text-primary)' }}>
          Share Sources
        </span>
        <button onClick={onClose} className="p-0.5 rounded hover:bg-surface">
          <X size={10} style={{ color: 'var(--color-text-tertiary)' }} />
        </button>
      </div>

      {iosBlocked && (
        <div className="px-3 py-2 flex items-start gap-2"
          style={{ background: 'var(--color-warn-dim)' }}
        >
          <AlertTriangle size={12} style={{ color: 'var(--color-warn)' }} className="flex-shrink-0 mt-0.5" />
          <p className="text-[9px] font-mono" style={{ color: 'var(--color-warn)' }}>
            Screen sharing is not supported from iOS Safari. Join from desktop to share. You can still watch streams.
          </p>
        </div>
      )}

      {!iosBlocked && (
        <div className="p-1">
          <ShareMenuItem
            icon={Monitor}
            label="Screen"
            desc="Share your entire screen"
            disabled={!canAdd}
            onClick={onAddScreen}
          />
          <ShareMenuItem
            icon={AppWindow}
            label="Window"
            desc="Share an application window"
            disabled={!canAdd}
            onClick={onAddScreen}
          />
          <ShareMenuItem
            icon={Globe}
            label="Browser Tab"
            desc="Share a browser tab"
            disabled={!canAdd}
            onClick={onAddScreen}
          />
          <ShareMenuItem
            icon={Plus}
            label="Additional Source"
            desc={canAdd ? `${4 - localStreamCount} more allowed` : 'Max 4 streams reached'}
            disabled={!canAdd}
            onClick={onAddScreen}
          />
        </div>
      )}

      {localStreamCount > 0 && (
        <div className="px-1 pb-1 border-t" style={{ borderColor: 'var(--color-border)' }}>
          <button onClick={onStopAll}
            className="w-full flex items-center gap-2 px-2 py-1.5 rounded text-[9px] font-mono transition-colors hover:bg-surface"
            style={{ color: 'var(--color-danger)' }}
          >
            <MonitorOff size={12} />
            Stop All Streams ({localStreamCount})
          </button>
        </div>
      )}
    </div>
  )
}

function ShareMenuItem({
  icon: Icon,
  label,
  desc,
  disabled,
  onClick,
}: {
  icon: typeof Monitor
  label: string
  desc: string
  disabled: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="w-full flex items-center gap-2 px-2 py-1.5 rounded text-left transition-colors hover:bg-surface disabled:opacity-40 disabled:cursor-not-allowed"
    >
      <Icon size={14} style={{ color: disabled ? 'var(--color-text-tertiary)' : 'var(--color-cyan)' }} />
      <div>
        <span className="text-[10px] font-mono block" style={{ color: 'var(--color-text-primary)' }}>{label}</span>
        <span className="text-[8px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>{desc}</span>
      </div>
    </button>
  )
}

function ControlButton({
  active,
  danger,
  icon: Icon,
  label,
  onClick,
}: {
  active: boolean
  danger?: boolean
  icon: typeof Mic
  label: string
  onClick: () => void
}) {
  return (
    <button onClick={onClick}
      className="flex flex-col items-center gap-0.5 px-2.5 py-1.5 rounded transition-colors"
      style={{
        background: danger ? 'var(--color-danger)' : active ? 'var(--color-surface-raised)' : 'transparent',
        color: danger ? 'var(--color-canvas)' : active ? 'var(--color-text-primary)' : 'var(--color-text-tertiary)',
      }}
      title={label}
    >
      <Icon size={16} />
      <span className="text-[8px] font-mono">{label}</span>
    </button>
  )
}

function ConnectionBanner({ state, error, reconnectAttempts }: { state: VoiceRoomState; error: string | null; reconnectAttempts: number }) {
  if (state === 'idle') return null

  const config: Record<string, { bg: string; color: string; text: string; icon: typeof Wifi }> = {
    'requesting-permission': { bg: 'var(--color-cyan-glow)', color: 'var(--color-cyan)', text: 'Requesting mic permission...', icon: Activity },
    connecting: { bg: 'var(--color-cyan-glow)', color: 'var(--color-cyan)', text: 'Connecting...', icon: Activity },
    connected: { bg: 'var(--color-ok-dim)', color: 'var(--color-ok)', text: 'Connected', icon: Wifi },
    reconnecting: {
      bg: 'var(--color-warn-dim)',
      color: 'var(--color-warn)',
      text: reconnectAttempts > 0 ? `Reconnecting (${reconnectAttempts}/5)...` : 'Reconnecting...',
      icon: Activity,
    },
    failed: { bg: 'var(--color-danger-dim)', color: 'var(--color-danger)', text: error || 'Connection failed', icon: WifiOff },
    disconnected: { bg: 'var(--color-warn-dim)', color: 'var(--color-warn)', text: 'Disconnected', icon: WifiOff },
  }

  const c = config[state]
  if (!c) return null
  const Icon = c.icon

  return (
    <div className="w-full rounded px-3 py-2 mb-3 flex items-center gap-2" style={{ background: c.bg }}>
      <Icon size={12} style={{ color: c.color }}
        className={state === 'connecting' || state === 'reconnecting' || state === 'requesting-permission' ? 'animate-pulse' : ''}
      />
      <span className="text-[10px] font-mono flex-1" style={{ color: c.color }}>{c.text}</span>
    </div>
  )
}

function ParticipantGrid({ participants }: { participants: VoiceParticipant[] }) {
  return (
    <div className="w-full rounded border p-3 mb-3" style={{ borderColor: 'var(--color-border)' }}>
      <span className="text-[10px] font-mono mb-2 block" style={{ color: 'var(--color-text-secondary)' }}>
        {participants.length} participant{participants.length !== 1 ? 's' : ''}
      </span>
      <div className="space-y-0.5">
        {participants.map((p) => (
          <ParticipantRow key={p.identity} participant={p} />
        ))}
      </div>
    </div>
  )
}

function ParticipantRow({ participant: p }: { participant: VoiceParticipant }) {
  const QualityIcon = p.connectionQuality === ConnectionQuality.Excellent ? SignalHigh
    : p.connectionQuality === ConnectionQuality.Good ? Signal
    : p.connectionQuality === ConnectionQuality.Poor ? SignalLow
    : SignalZero

  const qualityColor = p.connectionQuality === ConnectionQuality.Excellent ? 'var(--color-ok)'
    : p.connectionQuality === ConnectionQuality.Good ? 'var(--color-ok)'
    : p.connectionQuality === ConnectionQuality.Poor ? 'var(--color-warn)'
    : 'var(--color-text-tertiary)'

  return (
    <div className="flex items-center gap-2 py-1.5 px-1 rounded transition-colors"
      style={p.isSpeaking ? { background: 'var(--color-ok-dim)' } : undefined}
    >
      <div className="relative">
        <div className="w-7 h-7 rounded-full flex items-center justify-center text-[9px] font-mono font-bold"
          style={{
            background: 'var(--color-surface-overlay)',
            color: 'var(--color-text-secondary)',
            outline: p.isSpeaking ? '2px solid var(--color-ok)' : 'none',
          }}
        >
          {p.name.charAt(0).toUpperCase()}
        </div>
      </div>

      <span className="text-[10px] font-mono flex-1 truncate" style={{ color: 'var(--color-text-primary)' }}>
        {p.name}
      </span>

      <div className="flex items-center gap-1">
        {p.isSpeaking && (
          <div className="flex gap-0.5 items-end h-3">
            <div className="w-0.5 bg-green-400 animate-pulse" style={{ height: '40%' }} />
            <div className="w-0.5 bg-green-400 animate-pulse" style={{ height: '80%', animationDelay: '0.1s' }} />
            <div className="w-0.5 bg-green-400 animate-pulse" style={{ height: '60%', animationDelay: '0.2s' }} />
          </div>
        )}

        {p.streamCount > 0 && (
          <div className="flex items-center gap-0.5">
            <ScreenShare size={10} style={{ color: 'var(--color-cyan)' }} />
            {p.streamCount > 1 && (
              <span className="text-[7px] font-mono font-bold" style={{ color: 'var(--color-cyan)' }}>
                {p.streamCount}
              </span>
            )}
          </div>
        )}

        {p.isVideoOn && (
          <Video size={10} style={{ color: 'var(--color-ok)' }} />
        )}

        {p.isMuted ? (
          <MicOff size={10} style={{ color: 'var(--color-danger)' }} />
        ) : (
          <Mic size={10} style={{ color: 'var(--color-ok)' }} />
        )}

        <QualityIcon size={10} style={{ color: qualityColor }} />
      </div>
    </div>
  )
}

function VoiceChat({ channelId }: { channelId: string }) {
  const messages = useRoomsStore((s) => s.messages)
  const fetchMessages = useRoomsStore((s) => s.fetchMessages)
  const sendMessage = useRoomsStore((s) => s.sendMessage)
  const typingUsers = useRoomsStore((s) => s.typingUsers)

  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchMessages(channelId)
  }, [channelId, fetchMessages])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  const handleSend = async (e: FormEvent) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || sending) return
    setSending(true)
    setInput('')
    await sendMessage(channelId, text)
    setSending(false)
  }

  const channelMessages = messages.filter((m) => m.channel_id === channelId)
  const typing = typingUsers[channelId] || []

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center px-3 h-8 border-b shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <MessageSquare size={11} style={{ color: 'var(--color-text-tertiary)' }} />
        <span className="text-[10px] font-mono ml-1.5" style={{ color: 'var(--color-text-secondary)' }}>
          Chat
        </span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {channelMessages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <p className="text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
              No messages yet
            </p>
          </div>
        )}

        {channelMessages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      {typing.length > 0 && (
        <div className="px-3 py-0.5">
          <span className="text-[8px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
            {typing.join(', ')} typing...
          </span>
        </div>
      )}

      <form onSubmit={handleSend}
        className="flex items-center gap-1.5 px-2 py-1.5 border-t shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message..."
          disabled={sending}
          className="flex-1 text-[10px] font-mono px-2 py-1.5 rounded border bg-transparent outline-none"
          style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
        />
        <button type="submit"
          disabled={!input.trim() || sending}
          className="p-1.5 rounded transition-colors"
          style={{
            background: input.trim() ? 'var(--color-cyan)' : 'transparent',
            color: input.trim() ? 'var(--color-canvas)' : 'var(--color-text-tertiary)',
          }}
        >
          <Send size={11} />
        </button>
      </form>
    </div>
  )
}

function ChatMessage({ message: msg }: { message: RoomMessage }) {
  if (msg.deleted) return null

  return (
    <div className="px-3 py-1 hover:bg-surface-raised transition-colors">
      <div className="flex items-baseline gap-1.5">
        <span className="text-[9px] font-mono font-semibold" style={{ color: 'var(--color-cyan)' }}>
          {msg.author_name}
        </span>
        <span className="text-[8px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
          {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
      <p className="text-[10px] font-mono whitespace-pre-wrap break-words" style={{ color: 'var(--color-text-primary)' }}>
        {msg.content}
      </p>
    </div>
  )
}

function DiagnosticsPanel({ diagnostics, state }: { diagnostics: VoiceDiagnostics; state: string }) {
  const [expanded, setExpanded] = useState(false)

  if (state === 'idle' && !diagnostics.lastEvent) return null

  return (
    <div className="w-full rounded border mt-2" style={{ borderColor: 'var(--color-border)' }}>
      <button onClick={() => setExpanded(!expanded)}
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
          <DiagRow label="identity" value={diagnostics.participantIdentity} />
          <DiagRow label="token" value={diagnostics.tokenReceived ? 'received' : 'none'} />
          <DiagRow label="signal" value={diagnostics.signalConnected ? 'connected' : 'no'} />
          <DiagRow label="ice" value={diagnostics.iceState} />
          <DiagRow label="pub" value={diagnostics.publisherState} />
          <DiagRow label="sub" value={diagnostics.subscriberState} />
          <DiagRow label="mic" value={diagnostics.micPermission} />
          <DiagRow label="reconnects" value={String(diagnostics.reconnectAttempts)} />
          <DiagRow label="published" value={String(diagnostics.publishedTrackCount)} />
          <DiagRow label="subscribed" value={String(diagnostics.subscribedTrackCount)} />
          <DiagRow label="last" value={diagnostics.lastEvent} />
          {diagnostics.lastError && (
            <DiagRow label="error" value={diagnostics.lastError} error />
          )}
        </div>
      )}
    </div>
  )
}

function DiagRow({ label, value, error }: { label: string; value: string | null; error?: boolean }) {
  return (
    <div className="flex gap-2 text-[9px] font-mono">
      <span style={{ color: 'var(--color-text-tertiary)', minWidth: 64 }}>{label}</span>
      <span style={{ color: error ? 'var(--color-danger)' : 'var(--color-text-secondary)', wordBreak: 'break-all' }}>
        {value ?? '—'}
      </span>
    </div>
  )
}
