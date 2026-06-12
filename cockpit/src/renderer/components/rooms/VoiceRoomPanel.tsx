import { useEffect, useRef, useState } from 'react'
import {
  Mic,
  MicOff,
  PhoneOff,
  WifiOff,
  Activity,
  ChevronDown,
  ChevronRight,
  Video,
  VideoOff,
  Monitor,
  MonitorOff,
  Plus,
  X,
  Maximize2,
  Minimize2,
  AppWindow,
  Globe,
  Camera,
  ScreenShare,
  AlertTriangle,
  VolumeX,
  Volume2,
  Shield,
  Bot,
  Eye,
  Settings,
} from 'lucide-react'
import { useRoomsStore } from '../../stores/roomsStore'
import { useConferenceRoom } from '../../hooks/useConferenceRoom'
import type {
  ConferenceParticipant as VoiceParticipant,
  ConferenceDiagnostics as VoiceDiagnostics,
  ConferenceRoomState as VoiceRoomState,
  MediaStreamSource,
  AIGovernancePermissions,
  ProductionTestItem,
  MediaIntent,
  JoinTiming,
} from '../../hooks/useConferenceRoom'

const SOURCE_TYPE_ICONS: Record<string, typeof Monitor> = {
  camera: Camera,
  screen: Monitor,
  window: AppWindow,
  tab: Globe,
  application: AppWindow,
}

const SOURCE_TYPE_LABELS: Record<string, string> = {
  camera: 'Camera',
  screen: 'Screen',
  window: 'Window',
  tab: 'Browser Tab',
  application: 'Application',
}

function detectScreenShareCapability(): 'native' | 'browser' | 'none' {
  if (typeof navigator === 'undefined') return 'none'
  const isNativeApp = !!(window as Record<string, unknown>).Capacitor
    || !!(window as Record<string, unknown>).ReactNativeWebView
  if (isNativeApp) return 'native'
  if (typeof navigator.mediaDevices?.getDisplayMedia === 'function') return 'browser'
  return 'none'
}

function isIOS(): boolean {
  if (typeof navigator === 'undefined') return false
  return /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
}

export function VoiceRoomPanel({ channelId }: { channelId: string }) {
  const channels = useRoomsStore((s) => s.channels)
  const channel = channels.find((c) => c.id === channelId)
  const conf = useConferenceRoom(channelId)
  const voice = conf
  const [sidePanel, setSidePanel] = useState<'settings' | null>(null)
  const [focusedStream, setFocusedStream] = useState<string | null>(null)

  const isConnected = voice.state === 'connected'
  const hasVideo = voice.participants.some(p => p.isVideoOn)

  const allStreams: Array<MediaStreamSource & { participantName: string }> = []
  voice.streams.forEach((sources, identity) => {
    const participant = voice.participants.find(p => p.identity === identity)
    const name = participant?.name || identity
    for (const source of sources) {
      allStreams.push({ ...source, participantName: name })
    }
  })

  const screenShares = allStreams.filter(s => s.sourceType !== 'camera')
  const cameraStreams = allStreams.filter(s => s.sourceType === 'camera')
  const hasScreenShare = screenShares.length > 0

  return (
    <div className="flex flex-col h-full overflow-hidden voice-room-root"
      style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
    >
      <div className="flex flex-1 min-h-0">
        {/* Main area */}
        <div className="flex-1 flex flex-col min-h-0">
          {/* Content area — changes based on media state */}
          <div className="flex-1 overflow-y-auto overscroll-contain">
            {!isConnected ? (
              /* Pre-join / connecting / disconnected */
              <div className="flex flex-col items-center justify-center h-full p-4">
                <ChannelHeader name={channel?.name || 'Voice Room'} state={voice.state} />
                <ConnectionBanner state={voice.state} error={voice.error} reconnectAttempts={voice.diagnostics.reconnectAttempts} />
              </div>
            ) : hasScreenShare ? (
              /* Screen share layout — prominent screen, strip of other media */
              <div className="flex flex-col h-full p-2 gap-2">
                <div className="flex-1 min-h-0">
                  <StreamTile
                    stream={focusedStream ? allStreams.find(s => s.trackSid === focusedStream) || screenShares[0] : screenShares[0]}
                    focused
                    getVideoElement={voice.getVideoElement}
                    onFocus={() => setFocusedStream(null)}
                    onStop={voice.stopStream}
                    localIdentity={voice.diagnostics.participantIdentity || undefined}
                  />
                </div>
                {(screenShares.length > 1 || cameraStreams.length > 0) && (
                  <div className="flex gap-1.5 overflow-x-auto pb-1 shrink-0" style={{ height: 80 }}>
                    {[...screenShares.slice(1), ...cameraStreams].map(s => (
                      <div key={s.trackSid} className="flex-shrink-0" style={{ width: 120, height: 72 }}>
                        <StreamTile
                          stream={s}
                          compact
                          getVideoElement={voice.getVideoElement}
                          onFocus={() => setFocusedStream(s.trackSid)}
                          onStop={voice.stopStream}
                          localIdentity={voice.diagnostics.participantIdentity || undefined}
                        />
                      </div>
                    ))}
                  </div>
                )}
                <ParticipantStrip participants={voice.participants} />
              </div>
            ) : hasVideo ? (
              /* Video grid layout */
              <div className="flex flex-col h-full p-2 gap-2">
                <VideoGrid
                  streams={cameraStreams}
                  getVideoElement={voice.getVideoElement}
                  onFocus={setFocusedStream}
                  focusedStream={focusedStream}
                  onStopStream={voice.stopStream}
                  localIdentity={voice.diagnostics.participantIdentity || undefined}
                />
                <ParticipantStrip
                  participants={voice.participants.filter(p => !p.isVideoOn)}
                />
              </div>
            ) : (
              /* Voice-only layout — Discord style */
              <div className="flex flex-col p-3 sm:p-4 max-w-lg mx-auto w-full">
                <VoiceHeader name={channel?.name || 'Voice Room'} participantCount={voice.participants.length} />
                <div className="space-y-0.5 mt-2">
                  {voice.participants.map((p) => (
                    <VoiceParticipantRow key={p.identity} participant={p} />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Reconnect prompt */}
          {voice.state === 'disconnected' && (
            <ReconnectBar onReconnect={voice.join} />
          )}

          {/* Bottom call bar */}
          <CallBar
            state={voice.state}
            isMuted={voice.isMuted}
            isDeafened={voice.isDeafened}
            isVideoOn={voice.isVideoOn}
            micIntent={voice.micIntent}
            cameraIntent={voice.cameraIntent}
            preJoinMicEnabled={voice.preJoinMicEnabled}
            preJoinVideoEnabled={conf.preJoinVideoEnabled}
            localStreamCount={voice.localStreams.filter(s => s.sourceType !== 'camera').length}
            canAddStream={voice.canAddStream}
            settingsOpen={sidePanel === 'settings'}
            error={voice.error}
            onJoin={voice.join}
            onLeave={voice.leave}
            onToggleMute={voice.toggleMute}
            onToggleDeafen={voice.toggleDeafen}
            onTogglePreJoinMic={voice.togglePreJoinMic}
            onTogglePreJoinVideo={conf.togglePreJoinVideo}
            onToggleVideo={voice.toggleVideo}
            onAddScreenShare={voice.addScreenShare}
            onStopAllStreams={voice.stopAllStreams}
            onToggleSettings={() => setSidePanel(sidePanel === 'settings' ? null : 'settings')}
          />
        </div>

        {/* Settings panel — inline flex sibling */}
        {sidePanel === 'settings' && (
          <div className="w-72 flex flex-col min-h-0 border-l"
            style={{ borderColor: 'var(--color-border)', maxWidth: '50%' }}
          >
            <SettingsPanel
              diagnostics={voice.diagnostics}
              state={voice.state}
              aiGovernance={conf.aiGovernance}
              onUpdateGovernance={conf.setAIGovernance}
              productionChecklist={conf.productionChecklist}
            />
          </div>
        )}
      </div>
    </div>
  )
}

/* ─── Voice-Only Layout Components ─── */

function VoiceHeader({ name, participantCount }: { name: string; participantCount: number }) {
  return (
    <div className="flex items-center gap-2 mb-1">
      <Volume2 size={14} style={{ color: 'var(--color-ok)' }} />
      <span className="text-xs font-mono font-semibold" style={{ color: 'var(--color-text-primary)' }}>
        {name}
      </span>
      {participantCount > 0 && (
        <span className="text-[9px] font-mono ml-auto" style={{ color: 'var(--color-text-tertiary)' }}>
          {participantCount}
        </span>
      )}
    </div>
  )
}

function VoiceParticipantRow({ participant: p }: { participant: VoiceParticipant }) {
  return (
    <div className="flex items-center gap-2.5 py-1 px-1.5 rounded transition-colors hover:bg-surface-raised">
      <div className="relative">
        <div className="w-8 h-8 rounded-full flex items-center justify-center text-[10px] font-mono font-bold"
          style={{
            background: p.isSpeaking ? 'var(--color-ok-dim)' : 'var(--color-surface-overlay)',
            color: p.isSpeaking ? 'var(--color-ok)' : 'var(--color-text-secondary)',
            outline: p.isSpeaking ? '2px solid var(--color-ok)' : '2px solid transparent',
            outlineOffset: '1px',
            transition: 'outline-color 150ms',
          }}
        >
          {p.name.charAt(0).toUpperCase()}
        </div>
      </div>

      <span className="text-[11px] font-mono flex-1 truncate" style={{
        color: p.isSpeaking ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
      }}>
        {p.name}
      </span>

      <div className="flex items-center gap-1">
        {p.streamCount > 0 && (
          <ScreenShare size={12} style={{ color: 'var(--color-cyan)' }} />
        )}
        {p.isVideoOn && (
          <Video size={12} style={{ color: 'var(--color-ok)' }} />
        )}
        {p.isDeafened ? (
          <VolumeX size={12} style={{ color: 'var(--color-danger)' }} />
        ) : p.isMuted ? (
          <MicOff size={12} style={{ color: 'var(--color-danger)' }} />
        ) : null}
      </div>
    </div>
  )
}

function ParticipantStrip({ participants }: { participants: VoiceParticipant[] }) {
  if (participants.length === 0) return null
  return (
    <div className="flex gap-1 overflow-x-auto py-1 shrink-0">
      {participants.map(p => (
        <div key={p.identity} className="flex items-center gap-1 px-2 py-1 rounded shrink-0"
          style={{ background: 'var(--color-surface)' }}
        >
          <div className="w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-mono font-bold"
            style={{
              background: p.isSpeaking ? 'var(--color-ok-dim)' : 'var(--color-surface-overlay)',
              color: p.isSpeaking ? 'var(--color-ok)' : 'var(--color-text-secondary)',
              outline: p.isSpeaking ? '1.5px solid var(--color-ok)' : 'none',
            }}
          >
            {p.name.charAt(0).toUpperCase()}
          </div>
          <span className="text-[9px] font-mono truncate max-w-[60px]" style={{ color: 'var(--color-text-secondary)' }}>
            {p.name}
          </span>
          {p.isMuted && <MicOff size={9} style={{ color: 'var(--color-danger)' }} />}
        </div>
      ))}
    </div>
  )
}

/* ─── Video/Stream Layout Components ─── */

function VideoGrid({
  streams,
  getVideoElement,
  onFocus,
  focusedStream,
  onStopStream,
  localIdentity,
}: {
  streams: Array<MediaStreamSource & { participantName: string }>
  getVideoElement: (sid: string) => HTMLVideoElement | null
  onFocus: (sid: string | null) => void
  focusedStream: string | null
  onStopStream: (sid: string) => Promise<void>
  localIdentity: string | undefined
}) {
  if (streams.length === 0) return null

  const focused = focusedStream ? streams.find(s => s.trackSid === focusedStream) : null
  if (focused) {
    return (
      <div className="flex-1 min-h-0 flex flex-col gap-1.5">
        <div className="flex-1 min-h-0">
          <StreamTile
            stream={focused}
            focused
            getVideoElement={getVideoElement}
            onFocus={() => onFocus(null)}
            onStop={onStopStream}
            localIdentity={localIdentity}
          />
        </div>
        {streams.length > 1 && (
          <div className="flex gap-1.5 overflow-x-auto shrink-0" style={{ height: 72 }}>
            {streams.filter(s => s.trackSid !== focusedStream).map(s => (
              <div key={s.trackSid} className="flex-shrink-0" style={{ width: 120, height: 72 }}>
                <StreamTile
                  stream={s}
                  compact
                  getVideoElement={getVideoElement}
                  onFocus={() => onFocus(s.trackSid)}
                  onStop={onStopStream}
                  localIdentity={localIdentity}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  const gridCols = streams.length === 1 ? 'grid-cols-1' :
    streams.length <= 4 ? 'grid-cols-2' : 'grid-cols-2 sm:grid-cols-3'

  return (
    <div className={`flex-1 min-h-0 grid ${gridCols} gap-1.5 auto-rows-fr`}>
      {streams.map(s => (
        <StreamTile
          key={s.trackSid}
          stream={s}
          getVideoElement={getVideoElement}
          onFocus={() => onFocus(s.trackSid)}
          onStop={onStopStream}
          localIdentity={localIdentity}
        />
      ))}
    </div>
  )
}

function StreamTile({
  stream,
  focused,
  compact,
  getVideoElement,
  onFocus,
  onStop,
  localIdentity,
}: {
  stream: MediaStreamSource & { participantName: string }
  focused?: boolean
  compact?: boolean
  getVideoElement: (sid: string) => HTMLVideoElement | null
  onFocus: () => void
  onStop: (sid: string) => Promise<void>
  localIdentity: string | undefined
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mountedSidRef = useRef<string | null>(null)
  const isOwner = stream.participantIdentity === localIdentity

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let cancelled = false
    let pollTimer: ReturnType<typeof setInterval> | undefined

    function tryMount() {
      if (cancelled || !container) return
      if (mountedSidRef.current === stream.trackSid) return

      const el = getVideoElement(stream.trackSid)
      if (el) {
        el.playsInline = true
        el.autoplay = true
        el.muted = true
        el.setAttribute('playsinline', '')
        el.style.display = 'block'
        el.style.width = '100%'
        el.style.height = '100%'
        el.style.objectFit = 'contain'
        el.style.borderRadius = '6px'
        el.style.position = 'absolute'
        container.appendChild(el)
        mountedSidRef.current = stream.trackSid
        if (pollTimer) clearInterval(pollTimer)
      }
    }

    tryMount()
    if (mountedSidRef.current !== stream.trackSid) {
      pollTimer = setInterval(tryMount, 200)
    }

    return () => {
      cancelled = true
      if (pollTimer) clearInterval(pollTimer)
      if (mountedSidRef.current === stream.trackSid) {
        const el = getVideoElement(stream.trackSid)
        if (el) {
          el.style.display = 'none'
          el.style.position = 'absolute'
          document.body.appendChild(el)
        }
        mountedSidRef.current = null
      }
    }
  }, [stream.trackSid, getVideoElement])

  const Icon = SOURCE_TYPE_ICONS[stream.sourceType] || Monitor
  const label = SOURCE_TYPE_LABELS[stream.sourceType] || stream.sourceType

  return (
    <div
      className={`relative rounded-lg overflow-hidden group h-full ${focused ? '' : compact ? '' : 'aspect-video'}`}
      style={{
        background: '#1a1a1a',
        minHeight: compact ? undefined : focused ? undefined : 120,
      }}
    >
      <div ref={containerRef} className="absolute inset-0" />

      {/* Name overlay */}
      <div className="absolute bottom-0 left-0 right-0 px-2 py-1.5 flex items-center gap-1.5"
        style={{ background: 'linear-gradient(transparent, rgba(0,0,0,0.7))' }}
      >
        <span className={`font-mono truncate ${compact ? 'text-[8px]' : 'text-[10px]'}`} style={{ color: '#fff' }}>
          {stream.participantName}
        </span>
        {!compact && (
          <span className="text-[8px] font-mono ml-auto" style={{ color: 'rgba(255,255,255,0.5)' }}>
            {label}
          </span>
        )}
      </div>

      {/* Hover controls */}
      <div className="absolute top-1.5 right-1.5 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button onClick={onFocus}
          className="p-1 rounded-md"
          style={{ background: 'rgba(0,0,0,0.6)' }}
          title={focused ? 'Minimize' : 'Focus'}
        >
          {focused ? <Minimize2 size={12} color="#fff" /> : <Maximize2 size={12} color="#fff" />}
        </button>
        {isOwner && (
          <button onClick={() => onStop(stream.trackSid)}
            className="p-1 rounded-md"
            style={{ background: 'rgba(220,38,38,0.8)' }}
            title="Stop"
          >
            <X size={12} color="#fff" />
          </button>
        )}
      </div>
    </div>
  )
}

/* ─── UI Components ─── */

function ChannelHeader({ name, state }: { name: string; state: VoiceRoomState }) {
  const isConnected = state === 'connected'
  const isActive = state !== 'idle'

  return (
    <div className="flex flex-col items-center mb-3">
      <div className="w-14 h-14 rounded-full flex items-center justify-center mb-2"
        style={{ background: 'var(--color-surface-raised)' }}
      >
        <Volume2 size={24} style={{
          color: isConnected ? 'var(--color-ok)' :
            isActive ? 'var(--color-cyan)' : 'var(--color-text-tertiary)',
        }} />
      </div>
      <h3 className="text-sm font-mono font-semibold" style={{ color: 'var(--color-text-primary)' }}>
        {name}
      </h3>
    </div>
  )
}

function ConnectionBanner({ state, error, reconnectAttempts }: { state: VoiceRoomState; error: string | null; reconnectAttempts: number }) {
  if (state === 'idle' || state === 'connected') return null

  const config: Record<string, { bg: string; color: string; text: string; icon: typeof Wifi }> = {
    requesting_permissions: { bg: 'var(--color-cyan-glow)', color: 'var(--color-cyan)', text: 'Requesting mic...', icon: Mic },
    connecting: { bg: 'var(--color-cyan-glow)', color: 'var(--color-cyan)', text: 'Joining...', icon: Activity },
    reconnecting: {
      bg: 'var(--color-warn-dim)',
      color: 'var(--color-warn)',
      text: reconnectAttempts > 0 ? `Reconnecting (${reconnectAttempts}/5)...` : 'Reconnecting...',
      icon: Activity,
    },
    suspended: { bg: 'var(--color-warn-dim)', color: 'var(--color-warn)', text: 'Backgrounded — tap to resume', icon: Activity },
    failed: { bg: 'var(--color-danger-dim)', color: 'var(--color-danger)', text: error || 'Connection failed', icon: WifiOff },
    disconnected: { bg: 'var(--color-warn-dim)', color: 'var(--color-warn)', text: 'Disconnected', icon: WifiOff },
  }

  const c = config[state]
  if (!c) return null
  const Icon = c.icon
  const animating = state === 'connecting' || state === 'reconnecting' || state === 'requesting_permissions'

  return (
    <div className="w-full max-w-xs rounded-lg px-3 py-2 flex items-center gap-2" style={{ background: c.bg }}>
      <Icon size={14} style={{ color: c.color }} className={animating ? 'animate-pulse' : ''} />
      <span className="text-[10px] font-mono" style={{ color: c.color }}>{c.text}</span>
    </div>
  )
}

function ReconnectBar({ onReconnect }: { onReconnect: () => void }) {
  return (
    <div className="flex items-center justify-center gap-2 px-3 py-2 border-t"
      style={{ borderColor: 'var(--color-border)', background: 'var(--color-warn-dim)' }}
    >
      <WifiOff size={12} style={{ color: 'var(--color-warn)' }} />
      <span className="text-[10px] font-mono" style={{ color: 'var(--color-warn)' }}>
        Connection lost
      </span>
      <button onClick={onReconnect}
        className="text-[10px] font-mono px-3 py-1 rounded"
        style={{ background: 'var(--color-ok)', color: 'var(--color-canvas)' }}
      >
        Reconnect
      </button>
    </div>
  )
}

/* ─── Call Bar (Discord-style bottom bar) ─── */

function CallBar({
  state,
  isMuted,
  isDeafened,
  isVideoOn,
  micIntent,
  cameraIntent,
  preJoinMicEnabled,
  preJoinVideoEnabled,
  localStreamCount,
  canAddStream,
  sidePanel,
  error,
  onJoin,
  onLeave,
  onToggleMute,
  onToggleDeafen,
  onTogglePreJoinMic,
  onTogglePreJoinVideo,
  onToggleVideo,
  onAddScreenShare,
  onStopAllStreams,
  onToggleChat,
  onToggleSettings,
}: {
  state: VoiceRoomState
  isMuted: boolean
  isDeafened: boolean
  isVideoOn: boolean
  micIntent: MediaIntent
  cameraIntent: MediaIntent
  preJoinMicEnabled: boolean
  preJoinVideoEnabled: boolean
  localStreamCount: number
  canAddStream: boolean
  settingsOpen: boolean
  error: string | null
  onJoin: () => void
  onLeave: () => void
  onToggleMute: () => void
  onToggleDeafen: () => void
  onTogglePreJoinMic: () => void
  onTogglePreJoinVideo: () => void
  onToggleVideo: () => void
  onAddScreenShare: () => void
  onStopAllStreams: () => void
  onToggleSettings: () => void
}) {
  const [shareMenuOpen, setShareMenuOpen] = useState(false)
  const isConnected = state === 'connected' || state === 'reconnecting'
  const screenShareCap = detectScreenShareCapability()
  const showIOSShareNote = isIOS() && screenShareCap === 'none'

  const micTransitioning = micIntent.transition === 'publishing' || micIntent.transition === 'disabling'
  const camTransitioning = cameraIntent.transition === 'requesting_permission' || cameraIntent.transition === 'disabling' || cameraIntent.transition === 'publishing'

  // Pre-join state
  if (!isConnected && state !== 'failed' && state !== 'disconnected') {
    const isJoining = state === 'connecting' || state === 'requesting_permissions'
    return (
      <div className="flex flex-col items-center gap-2 px-3 sm:px-4 py-3 border-t shrink-0"
        style={{
          borderColor: 'var(--color-border)',
          background: 'var(--color-surface)',
          paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 12px)',
        }}
      >
        {/* Primary row: Mic / Join */}
        <div className="flex items-center justify-center gap-1.5">
          <CallBarButton
            active={preJoinMicEnabled}
            danger={!preJoinMicEnabled}
            icon={preJoinMicEnabled ? Mic : MicOff}
            label={preJoinMicEnabled ? 'Mic On' : 'Mic Off'}
            onClick={onTogglePreJoinMic}
            disabled={isJoining}
          />
          <button onClick={onJoin}
            disabled={isJoining}
            className="flex items-center gap-2 text-xs font-mono px-5 py-2.5 rounded-lg transition-colors"
            style={{
              background: isJoining ? 'var(--color-surface-raised)' : 'var(--color-ok)',
              color: isJoining ? 'var(--color-text-tertiary)' : 'var(--color-canvas)',
            }}
          >
            {isJoining ? 'Joining...' : 'Join Voice'}
          </button>
        </div>
        {/* Secondary row: Video + Settings */}
        <div className="flex items-center justify-center gap-1.5">
          <CallBarButton
            active={preJoinVideoEnabled}
            icon={preJoinVideoEnabled ? Video : VideoOff}
            label={preJoinVideoEnabled ? 'Cam On' : 'Cam Off'}
            onClick={onTogglePreJoinVideo}
            disabled={isJoining}
          />
          <CallBarButton
            active={settingsOpen}
            icon={Settings}
            label="Settings"
            onClick={onToggleSettings}
            disabled={false}
          />
        </div>
      </div>
    )
  }

  // Failed/disconnected
  if (state === 'failed' || state === 'disconnected') {
    return (
      <div className="flex items-center justify-center gap-1.5 px-3 sm:px-4 py-3 border-t shrink-0"
        style={{
          borderColor: 'var(--color-border)',
          background: 'var(--color-surface)',
          paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 12px)',
        }}
      >
        <button onClick={onJoin}
          className="flex items-center gap-2 text-xs font-mono px-4 py-2 rounded-lg transition-colors"
          style={{ background: 'var(--color-ok)', color: 'var(--color-canvas)' }}
        >
          Retry
        </button>
        {error && (
          <span className="text-[9px] font-mono max-w-48 truncate" style={{ color: 'var(--color-danger)' }}>
            {error}
          </span>
        )}
      </div>
    )
  }

  // Connected — Discord-style control bar
  return (
    <div className="relative flex items-center justify-center gap-0.5 sm:gap-1 px-2 sm:px-3 py-2 border-t shrink-0"
      style={{
        borderColor: 'var(--color-border)',
        background: 'var(--color-surface)',
        paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 8px)',
      }}
    >
      <CallBarButton
        active={!isMuted}
        danger={isMuted}
        icon={isMuted ? MicOff : Mic}
        label={isMuted ? 'Unmute' : 'Mute'}
        onClick={onToggleMute}
        transitioning={micTransitioning}
      />
      <CallBarButton
        active={!isDeafened}
        danger={isDeafened}
        icon={isDeafened ? VolumeX : Volume2}
        label={isDeafened ? 'Undeafen' : 'Deafen'}
        onClick={onToggleDeafen}
      />
      <CallBarButton
        active={isVideoOn}
        danger={cameraIntent.transition === 'failed'}
        icon={cameraIntent.transition === 'failed' ? AlertTriangle : isVideoOn ? Video : VideoOff}
        label={cameraIntent.transition === 'failed' ? 'Cam Fail' : isVideoOn ? 'Stop Video' : 'Video'}
        onClick={onToggleVideo}
        transitioning={camTransitioning}
      />

      <div className="relative">
        <CallBarButton
          active={localStreamCount > 0}
          icon={localStreamCount > 0 ? ScreenShare : Monitor}
          label="Share"
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

      <CallBarButton
        active={settingsOpen}
        icon={Settings}
        label="Settings"
        onClick={onToggleSettings}
      />

      <div className="w-px h-5 mx-0.5 hidden sm:block" style={{ background: 'var(--color-border)' }} />

      <button onClick={onLeave}
        className="flex items-center gap-1.5 text-[10px] font-mono px-2.5 sm:px-3 py-2 rounded-lg transition-colors"
        style={{ background: 'var(--color-danger)', color: '#fff' }}
      >
        <PhoneOff size={14} />
        <span className="hidden sm:inline">Leave</span>
      </button>

      {shareMenuOpen && (
        <ShareMenu
          canAdd={canAddStream}
          screenShareCap={screenShareCap}
          showIOSNote={showIOSShareNote}
          localStreamCount={localStreamCount}
          onAddScreen={() => { onAddScreenShare(); setShareMenuOpen(false) }}
          onStopAll={() => { onStopAllStreams(); setShareMenuOpen(false) }}
          onClose={() => setShareMenuOpen(false)}
        />
      )}
    </div>
  )
}

function CallBarButton({
  active,
  danger,
  icon: Icon,
  label,
  onClick,
  disabled,
  transitioning,
}: {
  active: boolean
  danger?: boolean
  icon: typeof Mic
  label: string
  onClick: () => void
  disabled?: boolean
  transitioning?: boolean
}) {
  return (
    <button onClick={onClick}
      disabled={disabled}
      className={`flex flex-col items-center gap-0.5 px-2 sm:px-2.5 py-1.5 rounded-lg transition-all min-w-[40px] min-h-[40px] justify-center ${transitioning ? 'animate-pulse' : ''}`}
      style={{
        background: danger ? 'var(--color-danger)' : active ? 'var(--color-surface-raised)' : 'transparent',
        color: danger ? '#fff' : active ? 'var(--color-text-primary)' : 'var(--color-text-tertiary)',
        opacity: disabled ? 0.4 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
      }}
      title={label}
    >
      <Icon size={16} />
      <span className="text-[7px] font-mono leading-none">{label}</span>
    </button>
  )
}

/* ─── Share Menu ─── */

function ShareMenu({
  canAdd,
  screenShareCap,
  showIOSNote,
  localStreamCount,
  onAddScreen,
  onStopAll,
  onClose,
}: {
  canAdd: boolean
  screenShareCap: 'native' | 'browser' | 'none'
  showIOSNote: boolean
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
        <button onClick={onClose} className="p-0.5 rounded">
          <X size={10} style={{ color: 'var(--color-text-tertiary)' }} />
        </button>
      </div>

      {screenShareCap === 'none' && (
        <div className="px-3 py-2 flex items-start gap-2"
          style={{ background: 'var(--color-warn-dim)' }}
        >
          <AlertTriangle size={12} style={{ color: 'var(--color-warn)' }} className="flex-shrink-0 mt-0.5" />
          <p className="text-[9px] font-mono" style={{ color: 'var(--color-warn)' }}>
            {showIOSNote
              ? 'Screen share is not supported in iOS Safari. Use the native app or a desktop browser.'
              : 'Screen share not available in this browser.'}
          </p>
        </div>
      )}

      {screenShareCap === 'native' && (
        <div className="p-1">
          <ShareMenuItem icon={Monitor} label="Broadcast Screen" desc="Share your device screen" disabled={!canAdd} onClick={onAddScreen} />
        </div>
      )}

      {screenShareCap === 'browser' && (
        <div className="p-1">
          <ShareMenuItem icon={Monitor} label="Screen" desc="Entire screen" disabled={!canAdd} onClick={onAddScreen} />
          <ShareMenuItem icon={AppWindow} label="Window" desc="Application window" disabled={!canAdd} onClick={onAddScreen} />
          <ShareMenuItem icon={Globe} label="Browser Tab" desc="Browser tab" disabled={!canAdd} onClick={onAddScreen} />
          <ShareMenuItem icon={Plus} label="Additional Source" desc={canAdd ? `${4 - localStreamCount} more` : 'Max 4'} disabled={!canAdd} onClick={onAddScreen} />
        </div>
      )}

      {localStreamCount > 0 && (
        <div className="px-1 pb-1 border-t" style={{ borderColor: 'var(--color-border)' }}>
          <button onClick={onStopAll}
            className="w-full flex items-center gap-2 px-2 py-1.5 rounded text-[9px] font-mono transition-colors"
            style={{ color: 'var(--color-danger)' }}
          >
            <MonitorOff size={12} />
            Stop All ({localStreamCount})
          </button>
        </div>
      )}
    </div>
  )
}

function ShareMenuItem({ icon: Icon, label, desc, disabled, onClick }: {
  icon: typeof Monitor; label: string; desc: string; disabled: boolean; onClick: () => void
}) {
  return (
    <button onClick={onClick} disabled={disabled}
      className="w-full flex items-center gap-2 px-2 py-1.5 rounded text-left transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
    >
      <Icon size={14} style={{ color: disabled ? 'var(--color-text-tertiary)' : 'var(--color-cyan)' }} />
      <div>
        <span className="text-[10px] font-mono block" style={{ color: 'var(--color-text-primary)' }}>{label}</span>
        <span className="text-[8px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>{desc}</span>
      </div>
    </button>
  )
}

/* ─── Settings Panel (diagnostics + governance — hidden by default) ─── */

function SettingsPanel({
  diagnostics,
  state,
  aiGovernance,
  onUpdateGovernance,
  productionChecklist,
}: {
  diagnostics: VoiceDiagnostics
  state: string
  aiGovernance: AIGovernancePermissions
  onUpdateGovernance: (patch: Partial<AIGovernancePermissions>) => void
  productionChecklist: ProductionTestItem[]
}) {
  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="hidden sm:flex items-center px-3 h-8 border-b shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <Settings size={11} style={{ color: 'var(--color-text-tertiary)' }} />
        <span className="text-[10px] font-mono ml-1.5" style={{ color: 'var(--color-text-secondary)' }}>
          Settings
        </span>
      </div>
      <div className="p-3 space-y-3">
        <AIGovernanceSection governance={aiGovernance} onUpdate={onUpdateGovernance} />
        <TimingSection timing={diagnostics.joinTiming} />
        <ProductionTestChecklist items={productionChecklist} />
        <DiagnosticsSection diagnostics={diagnostics} state={state} />
      </div>
    </div>
  )
}

function TimingSection({ timing }: { timing: JoinTiming }) {
  const hasData = timing.joinClickToOperationalMs !== null
  if (!hasData) return null

  return (
    <div className="rounded border p-2" style={{ borderColor: 'var(--color-border)' }}>
      <span className="text-[9px] font-mono font-semibold block mb-1" style={{ color: 'var(--color-text-secondary)' }}>
        Join Timing
      </span>
      <div className="space-y-0.5">
        {timing.tokenPrefetchMs !== null && <DiagRow label="token prefetch" value={`${timing.tokenPrefetchMs}ms`} />}
        {timing.joinClickToConnectStartMs !== null && <DiagRow label="click→connect" value={`${timing.joinClickToConnectStartMs}ms`} />}
        {timing.connectMs !== null && <DiagRow label="connect" value={`${timing.connectMs}ms`} />}
        {timing.micPublishMs !== null && <DiagRow label="mic publish" value={`${timing.micPublishMs}ms`} />}
        {timing.joinClickToOperationalMs !== null && (
          <DiagRow label="total" value={`${timing.joinClickToOperationalMs}ms`}
            highlight={timing.joinClickToOperationalMs < 2000}
          />
        )}
      </div>
    </div>
  )
}

function AIGovernanceSection({
  governance,
  onUpdate,
}: {
  governance: AIGovernancePermissions
  onUpdate: (patch: Partial<AIGovernancePermissions>) => void
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="rounded border" style={{ borderColor: 'var(--color-border)' }}>
      <button onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-1.5 px-2 py-1.5 text-[9px] font-mono"
        style={{ color: 'var(--color-text-tertiary)' }}
      >
        <Bot size={10} style={{ color: 'var(--color-violet)' }} />
        <span>AI Governance</span>
        {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
      </button>
      {expanded && (
        <div className="px-2 pb-2 space-y-1.5">
          <GovernanceToggle icon={Eye} label="Listen" field="ai_can_listen" value={governance.ai_can_listen} onUpdate={onUpdate} />
          <GovernanceToggle icon={Mic} label="Speak" field="ai_can_speak" value={governance.ai_can_speak} onUpdate={onUpdate} />
          <GovernanceToggle icon={Bot} label="Transcribe" field="ai_can_transcribe" value={governance.ai_can_transcribe} onUpdate={onUpdate} />
          <GovernanceRow icon={Shield} label="Audit Log" value={governance.ai_access_logged ? 'On' : 'Off'} />
        </div>
      )}
    </div>
  )
}

function GovernanceToggle({ icon: Icon, label, field, value, onUpdate }: {
  icon: typeof Bot; label: string; field: keyof AIGovernancePermissions; value: boolean; onUpdate: (patch: Partial<AIGovernancePermissions>) => void
}) {
  return (
    <button onClick={() => onUpdate({ [field]: !value })} className="flex items-center gap-2 text-[9px] font-mono w-full">
      <Icon size={10} style={{ color: 'var(--color-violet)' }} />
      <span style={{ color: 'var(--color-text-secondary)', minWidth: 56 }}>{label}</span>
      <div className="w-3 h-3 rounded-full border"
        style={{
          borderColor: value ? 'var(--color-ok)' : 'var(--color-border)',
          background: value ? 'var(--color-ok)' : 'transparent',
        }}
      />
      <span style={{ color: value ? 'var(--color-ok)' : 'var(--color-text-tertiary)' }}>
        {value ? 'On' : 'Off'}
      </span>
    </button>
  )
}

function GovernanceRow({ icon: Icon, label, value }: { icon: typeof Bot; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 text-[9px] font-mono">
      <Icon size={10} style={{ color: 'var(--color-violet)' }} />
      <span style={{ color: 'var(--color-text-secondary)', minWidth: 56 }}>{label}</span>
      <span style={{ color: 'var(--color-text-tertiary)' }}>{value}</span>
    </div>
  )
}

function ProductionTestChecklist({ items }: { items: ProductionTestItem[] }) {
  const [expanded, setExpanded] = useState(false)
  const passCount = items.filter(i => i.status === 'pass').length

  return (
    <div className="rounded border" style={{ borderColor: 'var(--color-border)' }}>
      <button onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-1.5 px-2 py-1.5 text-[9px] font-mono"
        style={{ color: 'var(--color-text-tertiary)' }}
      >
        <Activity size={10} style={{ color: passCount === items.length ? 'var(--color-ok)' : 'var(--color-text-tertiary)' }} />
        <span>Checklist ({passCount}/{items.length})</span>
        {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
      </button>
      {expanded && (
        <div className="px-2 pb-2 space-y-0.5">
          {items.map((item) => (
            <div key={item.label} className="flex items-center justify-between">
              <span className="text-[9px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>{item.label}</span>
              <div className="flex items-center gap-1">
                <div className="w-1.5 h-1.5 rounded-full"
                  style={{
                    background: item.status === 'pass' ? 'var(--color-ok)' :
                      item.status === 'fail' ? 'var(--color-danger)' :
                        item.status === 'pending' ? 'var(--color-warn)' : 'var(--color-text-tertiary)',
                  }}
                />
                <span className="text-[9px] font-mono max-w-[120px] truncate" style={{ color: 'var(--color-text-secondary)' }}>
                  {item.detail}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function DiagnosticsSection({ diagnostics, state }: { diagnostics: VoiceDiagnostics; state: string }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="rounded border" style={{ borderColor: 'var(--color-border)' }}>
      <button onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-1 px-2 py-1.5 text-[9px] font-mono"
        style={{ color: 'var(--color-text-tertiary)' }}
      >
        {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
        Diagnostics
      </button>
      {expanded && (
        <div className="px-2 pb-2 space-y-0.5">
          <DiagRow label="state" value={state} />
          <DiagRow label="join stage" value={diagnostics.joinStage} />
          <DiagRow label="mic state" value={diagnostics.micState} />
          <DiagRow label="cam state" value={diagnostics.cameraState} />
          <DiagRow label="url" value={diagnostics.livekitUrl} />
          <DiagRow label="room" value={diagnostics.roomName} />
          <DiagRow label="identity" value={diagnostics.participantIdentity} />
          <DiagRow label="token" value={diagnostics.tokenReceived ? 'yes' : 'no'} />
          <DiagRow label="signal" value={diagnostics.signalConnected ? 'yes' : 'no'} />
          <DiagRow label="mic perm" value={diagnostics.micPermission} />
          <DiagRow label="mic actual" value={diagnostics.micEnabledActual ? 'on' : 'off'} />
          <DiagRow label="audio sid" value={diagnostics.audioTrackSid} />
          {diagnostics.lastMicError && <DiagRow label="mic err" value={diagnostics.lastMicError} error />}
          <DiagRow label="cam perm" value={diagnostics.cameraPermission} />
          <DiagRow label="cam actual" value={diagnostics.cameraEnabledActual ? 'on' : 'off'} />
          <DiagRow label="video sid" value={diagnostics.videoTrackSid} />
          {diagnostics.lastVideoError && <DiagRow label="cam err" value={diagnostics.lastVideoError} error />}
          <DiagRow label="screenshare" value={diagnostics.screenShareSupport ? 'yes' : 'no'} />
          <DiagRow label="reconnects" value={String(diagnostics.reconnectAttempts)} />
          <DiagRow label="published" value={String(diagnostics.publishedTrackCount)} />
          <DiagRow label="subscribed" value={String(diagnostics.subscribedTrackCount)} />
          <DiagRow label="visibility" value={diagnostics.visibility.lastVisibilityState} />
          {diagnostics.visibility.backgroundDurationMs !== null && (
            <DiagRow label="bg duration" value={`${Math.round(diagnostics.visibility.backgroundDurationMs / 1000)}s`} />
          )}
          <DiagRow label="last" value={diagnostics.lastEvent} />
          {diagnostics.lastError && <DiagRow label="error" value={diagnostics.lastError} error />}
        </div>
      )}
    </div>
  )
}

/* ─── Shared helpers ─── */

function DiagRow({ label, value, error, highlight }: { label: string; value: string | null; error?: boolean; highlight?: boolean }) {
  return (
    <div className="flex gap-2 text-[9px] font-mono">
      <span style={{ color: 'var(--color-text-tertiary)', minWidth: 72 }}>{label}</span>
      <span style={{
        color: error ? 'var(--color-danger)' : highlight ? 'var(--color-ok)' : 'var(--color-text-secondary)',
        wordBreak: 'break-all',
      }}>
        {value ?? '—'}
      </span>
    </div>
  )
}
