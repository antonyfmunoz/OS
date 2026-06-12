import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import {
  Link2, AlertTriangle, Mic, MicOff, Video, VideoOff,
  PhoneOff, Loader2, Monitor, MonitorOff, MessageSquare,
  Send, Volume2, VolumeX, ScreenShare, WifiOff, Activity,
  X,
} from 'lucide-react'
import {
  Room,
  RoomEvent,
  Track,
  ConnectionState,
  RemoteTrackPublication,
  createLocalScreenTracks,
  LocalVideoTrack,
  DataPacket_Kind,
  type RemoteParticipant,
  type Participant,
} from 'livekit-client'
import { fetchApi } from '../../api/client'
import type { GuestPermissions } from '../../types/rooms'

interface InviteInfo {
  valid: boolean
  room_name: string
  room_type: 'voice' | 'meeting'
  server_name: string
  label: string | null
  permissions: GuestPermissions
  requires_email: boolean
  expires_at: string | null
  error?: string
}

interface GuestToken {
  token: string
  url: string
  room: string
  identity: string
}

type GuestJoinStage =
  | 'idle'
  | 'validating_invite'
  | 'requesting_token'
  | 'connecting'
  | 'publishing_mic'
  | 'publishing_camera'
  | 'connected'

const STAGE_LABELS: Record<GuestJoinStage, string> = {
  idle: '',
  validating_invite: 'Validating invite...',
  requesting_token: 'Getting room access...',
  connecting: 'Connecting...',
  publishing_mic: 'Setting up microphone...',
  publishing_camera: 'Setting up camera...',
  connected: 'Connected',
}

export function GuestJoinPage({ inviteCode }: { inviteCode: string }) {
  const [info, setInfo] = useState<InviteInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [guestName, setGuestName] = useState('')
  const [guestEmail, setGuestEmail] = useState('')
  const [joining, setJoining] = useState(false)
  const [joinStage, setJoinStage] = useState<GuestJoinStage>('idle')
  const [error, setError] = useState<string | null>(null)
  const [joined, setJoined] = useState(false)
  const [guestToken, setGuestToken] = useState<GuestToken | null>(null)
  const [micEnabled, setMicEnabled] = useState(true)
  const [videoEnabled, setVideoEnabled] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const result = await fetchApi<InviteInfo>(`/rooms/invite/${inviteCode}/info`)
        if (!cancelled) {
          setInfo(result)
          setLoading(false)
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Invalid invite link')
          setLoading(false)
        }
      }
    }
    load()
    return () => { cancelled = true }
  }, [inviteCode])

  const handleJoin = useCallback(async (e: FormEvent) => {
    e.preventDefault()
    if (joining || !info?.valid) return
    const name = guestName.trim()
    if (!name) return
    if (info.requires_email && !guestEmail.trim()) return

    setJoining(true)
    setError(null)
    setJoinStage('requesting_token')
    try {
      const token = await fetchApi<GuestToken>(`/rooms/invite/${inviteCode}/join`, {
        method: 'POST',
        body: JSON.stringify({
          guest_name: name,
          guest_email: guestEmail.trim() || undefined,
          mic_enabled: micEnabled,
          video_enabled: videoEnabled,
        }),
      })
      setGuestToken(token)
      setJoined(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to join')
      setJoinStage('idle')
    } finally {
      setJoining(false)
    }
  }, [inviteCode, guestName, guestEmail, micEnabled, videoEnabled, joining, info])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--color-canvas, #0a0a0f)' }}>
        <Loader2 size={24} className="animate-spin" style={{ color: 'var(--color-cyan, #00d4ff)' }} />
      </div>
    )
  }

  if (error && !info) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4" style={{ background: 'var(--color-canvas, #0a0a0f)' }}>
        <div className="max-w-sm w-full text-center space-y-4">
          <AlertTriangle size={32} style={{ color: 'var(--color-danger, #ff4444)', margin: '0 auto' }} />
          <h1 className="text-sm font-mono" style={{ color: 'var(--color-text-primary, #e0e0e0)' }}>
            Invalid Invite
          </h1>
          <p className="text-xs font-mono" style={{ color: 'var(--color-text-tertiary, #666)' }}>
            {error}
          </p>
        </div>
      </div>
    )
  }

  if (!info?.valid) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4" style={{ background: 'var(--color-canvas, #0a0a0f)' }}>
        <div className="max-w-sm w-full text-center space-y-4">
          <AlertTriangle size={32} style={{ color: 'var(--color-warn, #ffaa00)', margin: '0 auto' }} />
          <h1 className="text-sm font-mono" style={{ color: 'var(--color-text-primary, #e0e0e0)' }}>
            Invite Expired
          </h1>
          <p className="text-xs font-mono" style={{ color: 'var(--color-text-tertiary, #666)' }}>
            {info?.error || 'This invite link is no longer valid.'}
          </p>
        </div>
      </div>
    )
  }

  if (joined && guestToken) {
    return (
      <GuestRoomView
        token={guestToken}
        roomType={info.room_type}
        roomName={info.room_name}
        guestName={guestName}
        permissions={info.permissions}
        micEnabled={micEnabled}
        videoEnabled={videoEnabled}
      />
    )
  }

  const inputStyle = {
    borderColor: 'var(--color-border, #222)',
    color: 'var(--color-text-primary, #e0e0e0)',
    background: 'transparent',
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: 'var(--color-canvas, #0a0a0f)' }}>
      <div className="max-w-sm w-full space-y-6">
        <div className="text-center space-y-2">
          <Link2 size={24} style={{ color: 'var(--color-cyan, #00d4ff)', margin: '0 auto' }} />
          <h1 className="text-sm font-mono font-semibold" style={{ color: 'var(--color-text-primary, #e0e0e0)' }}>
            Join {info.room_type === 'meeting' ? 'Meeting' : 'Voice Room'}
          </h1>
          <p className="text-xs font-mono" style={{ color: 'var(--color-text-secondary, #999)' }}>
            {info.server_name} — {info.room_name}
          </p>
          {info.label && (
            <p className="text-xs font-mono" style={{ color: 'var(--color-cyan, #00d4ff)' }}>
              {info.label}
            </p>
          )}
          {info.expires_at && (
            <p className="text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary, #666)' }}>
              Link expires: {new Date(info.expires_at).toLocaleString()}
            </p>
          )}
        </div>

        <form onSubmit={handleJoin} className="space-y-3">
          <div>
            <label className="text-[9px] font-mono block mb-1" style={{ color: 'var(--color-text-tertiary, #666)' }}>
              Your name
            </label>
            <input
              type="text"
              value={guestName}
              onChange={(e) => setGuestName(e.target.value)}
              placeholder="Enter your name"
              required
              className="w-full text-[11px] font-mono px-3 py-2 rounded border outline-none"
              style={inputStyle}
              autoFocus
            />
          </div>

          {info.requires_email && (
            <div>
              <label className="text-[9px] font-mono block mb-1" style={{ color: 'var(--color-text-tertiary, #666)' }}>
                Email address
              </label>
              <input
                type="email"
                value={guestEmail}
                onChange={(e) => setGuestEmail(e.target.value)}
                placeholder="you@example.com"
                required
                className="w-full text-[11px] font-mono px-3 py-2 rounded border outline-none"
                style={inputStyle}
              />
            </div>
          )}

          <div className="flex items-center gap-4 justify-center py-2">
            {info.permissions.can_speak && (
              <button
                type="button"
                onClick={() => setMicEnabled((v) => !v)}
                className="flex flex-col items-center gap-1 p-2 rounded transition-colors"
                style={{
                  background: micEnabled ? 'var(--color-cyan-dim, rgba(0,212,255,0.1))' : 'transparent',
                  color: micEnabled ? 'var(--color-cyan, #00d4ff)' : 'var(--color-text-tertiary, #666)',
                }}
              >
                <Mic size={18} />
                <span className="text-[8px] font-mono">{micEnabled ? 'Mic On' : 'Mic Off'}</span>
              </button>
            )}
            {info.permissions.can_video && (
              <button
                type="button"
                onClick={() => setVideoEnabled((v) => !v)}
                className="flex flex-col items-center gap-1 p-2 rounded transition-colors"
                style={{
                  background: videoEnabled ? 'var(--color-cyan-dim, rgba(0,212,255,0.1))' : 'transparent',
                  color: videoEnabled ? 'var(--color-cyan, #00d4ff)' : 'var(--color-text-tertiary, #666)',
                }}
              >
                <Video size={18} />
                <span className="text-[8px] font-mono">{videoEnabled ? 'Video On' : 'Video Off'}</span>
              </button>
            )}
          </div>

          {error && (
            <p className="text-[10px] font-mono text-center" style={{ color: 'var(--color-danger, #ff4444)' }}>
              {error}
            </p>
          )}

          {joining && joinStage !== 'idle' && (
            <div className="flex items-center justify-center gap-2">
              <Loader2 size={12} className="animate-spin" style={{ color: 'var(--color-cyan, #00d4ff)' }} />
              <span className="text-[10px] font-mono" style={{ color: 'var(--color-text-secondary, #999)' }}>
                {STAGE_LABELS[joinStage]}
              </span>
            </div>
          )}

          <button
            type="submit"
            disabled={joining || !guestName.trim()}
            className="w-full text-[11px] font-mono font-semibold py-2.5 rounded transition-colors"
            style={{
              background: guestName.trim() && !joining ? 'var(--color-cyan, #00d4ff)' : 'var(--color-border, #222)',
              color: guestName.trim() && !joining ? 'var(--color-canvas, #0a0a0f)' : 'var(--color-text-tertiary, #666)',
            }}
          >
            {joining ? 'Joining...' : `Join ${info.room_type === 'meeting' ? 'Meeting' : 'Room'}`}
          </button>
        </form>

        <p className="text-[8px] font-mono text-center" style={{ color: 'var(--color-text-tertiary, #666)' }}>
          You will join as a temporary guest with limited access.
          <br />
          You will not have access to other parts of UMH.
        </p>
      </div>
    </div>
  )
}

/* ─── Types ─── */

interface GuestParticipant {
  identity: string
  name: string
  isSpeaking: boolean
  isMuted: boolean
  isVideoOn: boolean
  hasScreenShare: boolean
}

type GuestConnState = 'connecting' | 'connected' | 'reconnecting' | 'disconnected' | 'failed'

interface ChatMessage {
  id: string
  sender: string
  senderName: string
  content: string
  timestamp: number
}

const CHAT_TOPIC = 'umh-chat'
const MAX_RECONNECT_ATTEMPTS = 5

/* ─── Guest Room View — Full Discord-like Call UI ─── */

function GuestRoomView({
  token,
  roomType,
  roomName,
  guestName,
  permissions,
  micEnabled: initialMic,
  videoEnabled: initialVideo,
}: {
  token: GuestToken
  roomType: 'voice' | 'meeting'
  roomName: string
  guestName: string
  permissions: GuestPermissions
  micEnabled: boolean
  videoEnabled: boolean
}) {
  const roomRef = useRef<Room | null>(null)
  const intentionalDisconnectRef = useRef(false)
  const micIntentRef = useRef(initialMic && permissions.can_speak)
  const camIntentRef = useRef(initialVideo && permissions.can_video)
  const backgroundAtRef = useRef<number | null>(null)
  const reconnectCountRef = useRef(0)

  const [connState, setConnState] = useState<GuestConnState>('connecting')
  const [joinStage, setJoinStage] = useState<GuestJoinStage>('connecting')
  const [micOn, setMicOn] = useState(initialMic && permissions.can_speak)
  const [videoOn, setVideoOn] = useState(false)
  const [screenSharing, setScreenSharing] = useState(false)
  const [deafened, setDeafened] = useState(false)
  const [participants, setParticipants] = useState<GuestParticipant[]>([])
  const [connError, setConnError] = useState<string | null>(null)
  const [micError, setMicError] = useState<string | null>(null)
  const [camError, setCamError] = useState<string | null>(null)
  const [chatOpen, setChatOpen] = useState(false)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')

  const localVideoRef = useRef<HTMLVideoElement | null>(null)
  const remoteVideoRefs = useRef<Map<string, HTMLVideoElement>>(new Map())
  const localScreenTracksRef = useRef<Map<string, LocalVideoTrack>>(new Map())

  /* ─── Sync participants from room state ─── */
  const syncParticipants = useCallback(() => {
    const room = roomRef.current
    if (!room) return
    const parts: GuestParticipant[] = []
    // Include self
    parts.push({
      identity: room.localParticipant.identity,
      name: room.localParticipant.name || guestName,
      isSpeaking: room.localParticipant.isSpeaking,
      isMuted: !room.localParticipant.isMicrophoneEnabled,
      isVideoOn: room.localParticipant.isCameraEnabled,
      hasScreenShare: false,
    })
    room.remoteParticipants.forEach((p) => {
      let hasScreen = false
      p.trackPublications.forEach((pub) => {
        if (pub.source === Track.Source.ScreenShare) hasScreen = true
      })
      parts.push({
        identity: p.identity,
        name: p.name || p.identity,
        isSpeaking: p.isSpeaking,
        isMuted: !p.isMicrophoneEnabled,
        isVideoOn: p.isCameraEnabled,
        hasScreenShare: hasScreen,
      })
    })
    setParticipants(parts)
  }, [guestName])

  /* ─── Attach/detach remote video ─── */
  const attachRemoteVideo = useCallback((track: { attach: (el?: HTMLMediaElement) => HTMLMediaElement }, identity: string, source: Track.Source) => {
    const key = source === Track.Source.ScreenShare ? `screen-${identity}` : identity
    const el = remoteVideoRefs.current.get(key)
    if (el) {
      track.attach(el)
    }
  }, [])

  /* ─── Room setup ─── */
  useEffect(() => {
    const room = new Room({
      adaptiveStream: true,
      dynacast: true,
      disconnectOnPageLeave: false,
      reconnectPolicy: {
        nextRetryDelayInMs: (context) => {
          if (context.retryCount >= MAX_RECONNECT_ATTEMPTS) return null
          reconnectCountRef.current = context.retryCount + 1
          return 1000 * Math.pow(2, context.retryCount)
        },
      },
    })
    roomRef.current = room
    intentionalDisconnectRef.current = false

    room.on(RoomEvent.Connected, () => {
      setConnState('connected')
      reconnectCountRef.current = 0
      syncParticipants()
    })

    room.on(RoomEvent.Reconnecting, () => {
      setConnState('reconnecting')
    })

    room.on(RoomEvent.Reconnected, () => {
      setConnState('connected')
      reconnectCountRef.current = 0
      restoreMediaIntents()
      syncParticipants()
    })

    room.on(RoomEvent.Disconnected, () => {
      if (!intentionalDisconnectRef.current) {
        setConnState('disconnected')
      }
    })

    room.on(RoomEvent.ConnectionStateChanged, (state: ConnectionState) => {
      if (state === ConnectionState.Reconnecting) {
        setConnState('reconnecting')
      }
    })

    room.on(RoomEvent.ParticipantConnected, () => syncParticipants())
    room.on(RoomEvent.ParticipantDisconnected, (participant: RemoteParticipant) => {
      participant.trackPublications.forEach((pub) => {
        if (pub.track) {
          pub.track.detach().forEach((el) => el.remove())
        }
      })
      syncParticipants()
    })
    room.on(RoomEvent.ActiveSpeakersChanged, () => syncParticipants())
    room.on(RoomEvent.TrackMuted, () => syncParticipants())
    room.on(RoomEvent.TrackUnmuted, () => syncParticipants())

    room.on(RoomEvent.TrackSubscribed, (track, pub, participant) => {
      if (track.kind === 'audio') {
        const el = track.attach()
        el.id = `guest-audio-${participant.identity}-${pub.trackSid}`
        document.body.appendChild(el)
      }
      if (track.kind === 'video') {
        attachRemoteVideo(track, participant.identity, pub.source)
      }
      syncParticipants()
    })

    room.on(RoomEvent.TrackUnsubscribed, (track) => {
      track.detach().forEach((el) => el.remove())
      syncParticipants()
    })

    room.on(RoomEvent.DataReceived, (payload: Uint8Array, participant: RemoteParticipant | undefined, _kind: DataPacket_Kind, topic: string | undefined) => {
      if (topic !== CHAT_TOPIC) return
      try {
        const msg = JSON.parse(new TextDecoder().decode(payload))
        if (msg.type === 'chat' && msg.content) {
          setChatMessages((prev) => [...prev, {
            id: `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
            sender: participant?.identity || 'unknown',
            senderName: participant?.name || msg.senderName || 'Unknown',
            content: msg.content,
            timestamp: Date.now(),
          }])
        }
      } catch { /* ignore malformed */ }
    })

    room.on(RoomEvent.MediaDevicesError, (e) => {
      const msg = e instanceof Error ? e.message : 'unknown media error'
      const lower = msg.toLowerCase()
      if (lower.includes('camera') || lower.includes('video')) {
        setCamError(msg)
      } else {
        setMicError(msg)
      }
    })

    async function connect() {
      try {
        setJoinStage('connecting')
        console.log('[GuestRoom] connect()', { url: token.url, room: token.room, identity: token.identity, tokenLen: token.token?.length })
        await room.connect(token.url, token.token)
        setConnState('connected')

        if (micIntentRef.current) {
          setJoinStage('publishing_mic')
          try {
            await room.localParticipant.setMicrophoneEnabled(true)
            setMicOn(true)
            setMicError(null)
          } catch (micErr) {
            const msg = micErr instanceof Error ? micErr.message : 'mic failed'
            setMicError(msg)
            setMicOn(false)
            micIntentRef.current = false
          }
        }

        if (camIntentRef.current) {
          setJoinStage('publishing_camera')
          try {
            await room.localParticipant.setCameraEnabled(true)
            const camPub = room.localParticipant.getTrackPublication(Track.Source.Camera)
            if (camPub?.track && localVideoRef.current) {
              camPub.track.attach(localVideoRef.current)
            }
            setVideoOn(true)
            setCamError(null)
          } catch (camErr) {
            const msg = camErr instanceof Error ? camErr.message : 'camera failed'
            setCamError(msg)
            setVideoOn(false)
            camIntentRef.current = false
          }
        }

        setJoinStage('connected')
        syncParticipants()

        room.remoteParticipants.forEach((p) => {
          p.trackPublications.forEach((pub) => {
            if (pub instanceof RemoteTrackPublication && pub.track) {
              if (pub.source === Track.Source.Camera || pub.source === Track.Source.ScreenShare) {
                attachRemoteVideo(pub.track, p.identity, pub.source)
              }
            }
          })
        })
      } catch (e) {
        const msg = e instanceof Error ? e.message : 'Connection failed'
        console.error('[GuestRoom] connect failed', { error: msg, url: token.url, room: token.room, stack: e instanceof Error ? e.stack : undefined })
        setConnState('failed')
        setConnError(msg)
      }
    }
    connect()

    return () => {
      intentionalDisconnectRef.current = true
      localScreenTracksRef.current.forEach((track) => track.stop())
      localScreenTracksRef.current.clear()
      room.disconnect()
      roomRef.current = null
    }
  }, [token, syncParticipants, attachRemoteVideo])

  /* ─── Restore media intents after reconnect/foreground ─── */
  const restoreMediaIntents = useCallback(async () => {
    const room = roomRef.current
    if (!room || room.state !== ConnectionState.Connected) return

    if (micIntentRef.current && !room.localParticipant.isMicrophoneEnabled) {
      try {
        await room.localParticipant.setMicrophoneEnabled(true)
        setMicOn(true)
      } catch { /* mic restore failed — user can toggle manually */ }
    }
    if (camIntentRef.current && !room.localParticipant.isCameraEnabled) {
      try {
        await room.localParticipant.setCameraEnabled(true)
        setVideoOn(true)
      } catch { /* cam restore failed */ }
    }
    syncParticipants()
  }, [syncParticipants])

  /* ─── Visibility change — iPhone Safari app switch ─── */
  useEffect(() => {
    function handleVisibility() {
      if (document.visibilityState === 'hidden') {
        backgroundAtRef.current = Date.now()
      } else if (document.visibilityState === 'visible') {
        backgroundAtRef.current = null
        const room = roomRef.current
        if (room && room.state === ConnectionState.Connected) {
          restoreMediaIntents()
        }
      }
    }
    document.addEventListener('visibilitychange', handleVisibility)
    return () => document.removeEventListener('visibilitychange', handleVisibility)
  }, [restoreMediaIntents])

  /* ─── Mute toggle — optimistic + revert ─── */
  const toggleMic = useCallback(async () => {
    const room = roomRef.current
    if (!room || !permissions.can_speak) return
    const wasEnabled = room.localParticipant.isMicrophoneEnabled
    const target = !wasEnabled

    // Optimistic
    setMicOn(target)
    micIntentRef.current = target

    try {
      await room.localParticipant.setMicrophoneEnabled(target)
      const actual = room.localParticipant.isMicrophoneEnabled
      setMicOn(actual)
      micIntentRef.current = actual
      setMicError(null)
    } catch (err) {
      // Revert
      setMicOn(wasEnabled)
      micIntentRef.current = wasEnabled
      setMicError(err instanceof Error ? err.message : 'mic toggle failed')
    }
    syncParticipants()
  }, [permissions.can_speak, syncParticipants])

  /* ─── Camera toggle — isolated from mic/connection ─── */
  const toggleVideo = useCallback(async () => {
    const room = roomRef.current
    if (!room || !permissions.can_video) return
    const wasEnabled = room.localParticipant.isCameraEnabled
    const target = !wasEnabled

    // Optimistic
    setVideoOn(target)
    camIntentRef.current = target

    try {
      await room.localParticipant.setCameraEnabled(target)
      if (target) {
        const camPub = room.localParticipant.getTrackPublication(Track.Source.Camera)
        if (camPub?.track && localVideoRef.current) {
          camPub.track.attach(localVideoRef.current)
        }
      }
      const actual = room.localParticipant.isCameraEnabled
      setVideoOn(actual)
      camIntentRef.current = actual
      setCamError(null)
    } catch (err) {
      // Revert — camera errors never affect mic or connection
      setVideoOn(wasEnabled)
      camIntentRef.current = wasEnabled
      setCamError(err instanceof Error ? err.message : 'camera toggle failed')
    }
    syncParticipants()
  }, [permissions.can_video, syncParticipants])

  /* ─── Deafen toggle ─── */
  const toggleDeafen = useCallback(() => {
    const room = roomRef.current
    if (!room) return
    const next = !deafened
    setDeafened(next)
    room.remoteParticipants.forEach((rp) => {
      rp.audioTrackPublications.forEach((pub) => {
        if (pub.track) {
          pub.track.mediaStreamTrack.enabled = !next
        }
      })
    })
    if (next && permissions.can_speak) {
      room.localParticipant.setMicrophoneEnabled(false).catch(() => {})
      setMicOn(false)
      micIntentRef.current = false
    }
    syncParticipants()
  }, [deafened, permissions.can_speak, syncParticipants])

  /* ─── Screen share ─── */
  const toggleScreenShare = useCallback(async () => {
    const room = roomRef.current
    if (!room || !permissions.can_screen_share) return

    if (screenSharing) {
      localScreenTracksRef.current.forEach((track) => {
        room.localParticipant.unpublishTrack(track)
        track.stop()
      })
      localScreenTracksRef.current.clear()
      setScreenSharing(false)
      return
    }

    try {
      const tracks = await createLocalScreenTracks({ audio: true })
      for (const track of tracks) {
        if (track.kind === Track.Kind.Video) {
          const pub = await room.localParticipant.publishTrack(track as LocalVideoTrack, {
            source: Track.Source.ScreenShare,
          })
          if (pub.trackSid) {
            localScreenTracksRef.current.set(pub.trackSid, track as LocalVideoTrack)
          }
        } else if (track.kind === Track.Kind.Audio) {
          await room.localParticipant.publishTrack(track, {
            source: Track.Source.ScreenShareAudio,
          })
        }
      }
      setScreenSharing(true)
    } catch { /* user cancelled or not supported */ }
    syncParticipants()
  }, [screenSharing, permissions.can_screen_share, syncParticipants])

  /* ─── Leave ─── */
  const handleLeave = useCallback(() => {
    intentionalDisconnectRef.current = true
    const room = roomRef.current
    if (room) {
      localScreenTracksRef.current.forEach((track) => track.stop())
      localScreenTracksRef.current.clear()
      room.disconnect()
      roomRef.current = null
    }
    setConnState('disconnected')
  }, [])

  /* ─── Rejoin ─── */
  const handleRejoin = useCallback(async () => {
    const room = new Room({
      adaptiveStream: true,
      dynacast: true,
      disconnectOnPageLeave: false,
    })
    roomRef.current = room
    intentionalDisconnectRef.current = false
    setConnState('connecting')
    setConnError(null)
    setJoinStage('connecting')

    // Re-wire all events (same as initial setup)
    room.on(RoomEvent.Connected, () => {
      setConnState('connected')
      syncParticipants()
    })
    room.on(RoomEvent.Reconnecting, () => setConnState('reconnecting'))
    room.on(RoomEvent.Reconnected, () => {
      setConnState('connected')
      restoreMediaIntents()
      syncParticipants()
    })
    room.on(RoomEvent.Disconnected, () => {
      if (!intentionalDisconnectRef.current) setConnState('disconnected')
    })
    room.on(RoomEvent.ParticipantConnected, () => syncParticipants())
    room.on(RoomEvent.ParticipantDisconnected, () => syncParticipants())
    room.on(RoomEvent.ActiveSpeakersChanged, () => syncParticipants())
    room.on(RoomEvent.TrackMuted, () => syncParticipants())
    room.on(RoomEvent.TrackUnmuted, () => syncParticipants())
    room.on(RoomEvent.TrackSubscribed, (track, pub, participant) => {
      if (track.kind === 'audio') {
        const el = track.attach()
        el.id = `guest-audio-${participant.identity}-${pub.trackSid}`
        document.body.appendChild(el)
      }
      if (track.kind === 'video') {
        attachRemoteVideo(track, participant.identity, pub.source)
      }
      syncParticipants()
    })
    room.on(RoomEvent.TrackUnsubscribed, (track) => {
      track.detach().forEach((el) => el.remove())
      syncParticipants()
    })
    room.on(RoomEvent.DataReceived, (payload: Uint8Array, participant: RemoteParticipant | undefined, _kind: DataPacket_Kind, topic: string | undefined) => {
      if (topic !== CHAT_TOPIC) return
      try {
        const msg = JSON.parse(new TextDecoder().decode(payload))
        if (msg.type === 'chat' && msg.content) {
          setChatMessages((prev) => [...prev, {
            id: `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
            sender: participant?.identity || 'unknown',
            senderName: participant?.name || msg.senderName || 'Unknown',
            content: msg.content,
            timestamp: Date.now(),
          }])
        }
      } catch { /* ignore */ }
    })
    room.on(RoomEvent.MediaDevicesError, (e) => {
      const msg = e instanceof Error ? e.message : 'unknown media error'
      const lower = msg.toLowerCase()
      if (lower.includes('camera') || lower.includes('video')) {
        setCamError(msg)
      } else {
        setMicError(msg)
      }
    })

    try {
      console.log('[GuestRoom] rejoin connect()', { url: token.url, room: token.room })
      await room.connect(token.url, token.token)
      setConnState('connected')
      setJoinStage('connected')
      if (micIntentRef.current) {
        try {
          await room.localParticipant.setMicrophoneEnabled(true)
          setMicOn(true)
        } catch { setMicOn(false) }
      }
      if (camIntentRef.current) {
        try {
          await room.localParticipant.setCameraEnabled(true)
          setVideoOn(true)
        } catch { setVideoOn(false) }
      }
      syncParticipants()
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Reconnection failed'
      console.error('[GuestRoom] rejoin failed', { error: msg, url: token.url, stack: e instanceof Error ? e.stack : undefined })
      setConnState('failed')
      setConnError(msg)
    }
  }, [token, syncParticipants, restoreMediaIntents, attachRemoteVideo])

  /* ─── Chat send via LiveKit data channel ─── */
  const sendChatMessage = useCallback(async (e: FormEvent) => {
    e.preventDefault()
    const text = chatInput.trim()
    if (!text) return
    const room = roomRef.current
    if (!room || !permissions.can_chat) return

    const payload = new TextEncoder().encode(JSON.stringify({
      type: 'chat',
      content: text,
      senderName: guestName,
    }))

    try {
      await room.localParticipant.publishData(payload, { reliable: true, topic: CHAT_TOPIC })
      setChatMessages((prev) => [...prev, {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        sender: room.localParticipant.identity,
        senderName: guestName,
        content: text,
        timestamp: Date.now(),
      }])
      setChatInput('')
    } catch { /* send failed */ }
  }, [chatInput, guestName, permissions.can_chat])

  /* ─── Render: Failed ─── */
  if (connState === 'failed') {
    return (
      <div className="min-h-screen flex items-center justify-center p-4" style={{ background: 'var(--color-canvas, #0a0a0f)' }}>
        <div className="text-center space-y-3">
          <AlertTriangle size={28} style={{ color: 'var(--color-danger, #ff4444)', margin: '0 auto' }} />
          <p className="text-xs font-mono" style={{ color: 'var(--color-text-primary, #e0e0e0)' }}>Connection Failed</p>
          <p className="text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary, #666)' }}>
            {connError || 'Could not connect to the room.'}
          </p>
          <p className="text-[8px] font-mono break-all" style={{ color: 'var(--color-text-tertiary, #444)', maxWidth: '300px', margin: '4px auto' }}>
            signal: {token.url}
          </p>
          <button
            onClick={handleRejoin}
            className="text-[10px] font-mono px-4 py-2 rounded transition-colors"
            style={{ background: 'var(--color-ok, #00c853)', color: 'var(--color-canvas, #0a0a0f)' }}
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  /* ─── Render: Disconnected ─── */
  if (connState === 'disconnected') {
    return (
      <div className="min-h-screen flex items-center justify-center p-4" style={{ background: 'var(--color-canvas, #0a0a0f)' }}>
        <div className="text-center space-y-3">
          <PhoneOff size={28} style={{ color: 'var(--color-text-tertiary, #666)', margin: '0 auto' }} />
          <p className="text-xs font-mono" style={{ color: 'var(--color-text-primary, #e0e0e0)' }}>Disconnected</p>
          <p className="text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary, #666)' }}>
            You have left the {roomType === 'meeting' ? 'meeting' : 'voice room'}.
          </p>
          <button
            onClick={handleRejoin}
            className="text-[10px] font-mono px-4 py-2 rounded transition-colors"
            style={{ background: 'var(--color-ok, #00c853)', color: 'var(--color-canvas, #0a0a0f)' }}
          >
            Rejoin
          </button>
        </div>
      </div>
    )
  }

  const isConnected = connState === 'connected' || connState === 'reconnecting'
  const selfIdentity = roomRef.current?.localParticipant?.identity
  const remoteParticipants = participants.filter(p => p.identity !== selfIdentity)
  const hasAnyVideo = videoOn || remoteParticipants.some(p => p.isVideoOn)

  return (
    <div className="min-h-screen flex flex-col" style={{ background: 'var(--color-canvas, #0a0a0f)' }}>
      {/* ─── Header ─── */}
      <div className="flex items-center px-3 sm:px-4 h-10 border-b shrink-0" style={{ borderColor: 'var(--color-border, #222)' }}>
        <Volume2 size={14} style={{ color: 'var(--color-ok, #00c853)' }} />
        <span className="text-[11px] font-mono font-semibold ml-2" style={{ color: 'var(--color-text-primary, #e0e0e0)' }}>
          {roomName}
        </span>
        <span className="text-[9px] font-mono px-1.5 rounded ml-2" style={{ background: 'var(--color-warn-dim, rgba(255,170,0,0.1))', color: 'var(--color-warn, #ffaa00)' }}>
          GUEST
        </span>
        {joinStage !== 'connected' && joinStage !== 'idle' && (
          <div className="flex items-center gap-1.5 ml-2">
            <Loader2 size={10} className="animate-spin" style={{ color: 'var(--color-cyan, #00d4ff)' }} />
            <span className="text-[8px] font-mono" style={{ color: 'var(--color-text-tertiary, #666)' }}>
              {STAGE_LABELS[joinStage]}
            </span>
          </div>
        )}
        <span className="ml-auto text-[9px] font-mono" style={{ color: 'var(--color-text-tertiary, #666)' }}>
          {participants.length} in room
        </span>
      </div>

      {/* ─── Reconnecting banner ─── */}
      {connState === 'reconnecting' && (
        <div className="flex items-center gap-2 px-3 py-1.5 shrink-0"
          style={{ background: 'var(--color-warn-dim, rgba(255,170,0,0.1))' }}
        >
          <Activity size={12} className="animate-pulse" style={{ color: 'var(--color-warn, #ffaa00)' }} />
          <span className="text-[9px] font-mono" style={{ color: 'var(--color-warn, #ffaa00)' }}>
            Reconnecting{reconnectCountRef.current > 0 ? ` (${reconnectCountRef.current}/${MAX_RECONNECT_ATTEMPTS})` : ''}...
          </span>
        </div>
      )}

      {/* ─── Error banners — isolated per subsystem ─── */}
      {(micError || camError) && (
        <div className="px-3 py-1.5 shrink-0 space-y-0.5" style={{ background: 'var(--color-danger-dim, rgba(255,68,68,0.08))' }}>
          {micError && (
            <div className="flex items-center gap-2">
              <p className="text-[9px] font-mono flex-1" style={{ color: 'var(--color-danger, #ff4444)' }}>
                Mic: {micError}
              </p>
              <button onClick={() => setMicError(null)} className="p-0.5"><X size={10} style={{ color: 'var(--color-danger, #ff4444)' }} /></button>
            </div>
          )}
          {camError && (
            <div className="flex items-center gap-2">
              <p className="text-[9px] font-mono flex-1" style={{ color: 'var(--color-danger, #ff4444)' }}>
                Camera: {camError}
              </p>
              <button onClick={() => setCamError(null)} className="p-0.5"><X size={10} style={{ color: 'var(--color-danger, #ff4444)' }} /></button>
            </div>
          )}
        </div>
      )}

      {/* ─── Main content area ─── */}
      <div className="flex-1 flex min-h-0">
        <div className="flex-1 flex flex-col min-h-0 overflow-y-auto overscroll-contain">
          {!isConnected ? (
            <div className="flex flex-col items-center justify-center flex-1 p-4">
              <Loader2 size={24} className="animate-spin mb-3" style={{ color: 'var(--color-cyan, #00d4ff)' }} />
              <span className="text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary, #666)' }}>
                Connecting to room...
              </span>
            </div>
          ) : hasAnyVideo ? (
            /* ─── Video grid layout ─── */
            <div className="flex flex-col flex-1 p-2 gap-2">
              <div className="flex flex-wrap gap-2 justify-center flex-1 items-center">
                {videoOn && (
                  <div className="relative rounded-lg overflow-hidden" style={{ background: 'var(--color-surface, #111)', minWidth: 160, maxWidth: 320 }}>
                    <video
                      ref={localVideoRef}
                      autoPlay
                      playsInline
                      muted
                      className="w-full aspect-video object-cover"
                      style={{ transform: 'scaleX(-1)' }}
                    />
                    <span className="absolute bottom-1 left-1 text-[8px] font-mono px-1 rounded" style={{ background: 'rgba(0,0,0,0.6)', color: '#fff' }}>
                      You {micOn ? '' : '🔇'}
                    </span>
                  </div>
                )}
                {remoteParticipants.filter(p => p.isVideoOn).map(p => (
                  <div key={p.identity} className="relative rounded-lg overflow-hidden" style={{ background: 'var(--color-surface, #111)', minWidth: 160, maxWidth: 320 }}>
                    <video
                      ref={(el) => {
                        if (el) remoteVideoRefs.current.set(p.identity, el)
                        else remoteVideoRefs.current.delete(p.identity)
                      }}
                      autoPlay
                      playsInline
                      muted={false}
                      className="w-full aspect-video object-cover"
                    />
                    <span className="absolute bottom-1 left-1 text-[8px] font-mono px-1 rounded" style={{ background: 'rgba(0,0,0,0.6)', color: '#fff' }}>
                      {p.name} {p.isMuted ? '🔇' : ''}
                    </span>
                  </div>
                ))}
              </div>
              {/* Audio-only participants below video */}
              <GuestParticipantList
                participants={remoteParticipants.filter(p => !p.isVideoOn)}
                selfIdentity={selfIdentity}
              />
            </div>
          ) : (
            /* ─── Voice-only layout — Discord style ─── */
            <div className="flex flex-col p-3 sm:p-4 max-w-lg mx-auto w-full">
              <div className="flex items-center gap-2 mb-2">
                <Volume2 size={14} style={{ color: 'var(--color-ok, #00c853)' }} />
                <span className="text-xs font-mono font-semibold" style={{ color: 'var(--color-text-primary, #e0e0e0)' }}>
                  {roomName}
                </span>
                <span className="text-[9px] font-mono ml-auto" style={{ color: 'var(--color-text-tertiary, #666)' }}>
                  {participants.length}
                </span>
              </div>
              <div className="space-y-0.5">
                {participants.map((p) => (
                  <div key={p.identity}
                    className="flex items-center gap-2.5 py-1 px-1.5 rounded transition-colors"
                    style={{ background: p.isSpeaking ? 'var(--color-ok-dim, rgba(0,200,83,0.05))' : 'transparent' }}
                  >
                    <div className="w-8 h-8 rounded-full flex items-center justify-center text-[10px] font-mono font-bold"
                      style={{
                        background: p.isSpeaking ? 'var(--color-ok-dim, rgba(0,200,83,0.1))' : 'var(--color-surface-overlay, #1a1a1a)',
                        color: p.isSpeaking ? 'var(--color-ok, #00c853)' : 'var(--color-text-secondary, #999)',
                        outline: p.isSpeaking ? '2px solid var(--color-ok, #00c853)' : '2px solid transparent',
                        outlineOffset: '1px',
                        transition: 'outline-color 150ms',
                      }}
                    >
                      {p.name.charAt(0).toUpperCase()}
                    </div>
                    <span className="text-[11px] font-mono flex-1 truncate" style={{
                      color: p.isSpeaking ? 'var(--color-text-primary, #e0e0e0)' : 'var(--color-text-secondary, #999)',
                    }}>
                      {p.name}
                      {p.identity === selfIdentity && (
                        <span className="ml-1 text-[7px] px-1 rounded" style={{ background: 'var(--color-cyan-dim, rgba(0,212,255,0.1))', color: 'var(--color-cyan, #00d4ff)' }}>YOU</span>
                      )}
                      {p.identity.startsWith('temporary_guest:') && p.identity !== selfIdentity && (
                        <span className="ml-1 text-[7px] px-1 rounded" style={{ background: 'var(--color-warn-dim, rgba(255,170,0,0.1))', color: 'var(--color-warn, #ffaa00)' }}>GUEST</span>
                      )}
                    </span>
                    <div className="flex items-center gap-1">
                      {p.hasScreenShare && <ScreenShare size={12} style={{ color: 'var(--color-cyan, #00d4ff)' }} />}
                      {p.isVideoOn && <Video size={12} style={{ color: 'var(--color-ok, #00c853)' }} />}
                      {p.isMuted && <MicOff size={12} style={{ color: 'var(--color-danger, #ff4444)' }} />}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ─── Chat side panel ─── */}
        {chatOpen && permissions.can_chat && (
          <div className="w-72 sm:w-80 flex flex-col border-l shrink-0"
            style={{ borderColor: 'var(--color-border, #222)', maxWidth: '65%', minWidth: 240 }}
          >
            <div className="flex items-center px-3 h-8 border-b shrink-0"
              style={{ borderColor: 'var(--color-border, #222)' }}
            >
              <MessageSquare size={11} style={{ color: 'var(--color-text-tertiary, #666)' }} />
              <span className="text-[10px] font-mono ml-1.5" style={{ color: 'var(--color-text-secondary, #999)' }}>
                Chat
              </span>
              <button onClick={() => setChatOpen(false)} className="ml-auto p-0.5">
                <X size={12} style={{ color: 'var(--color-text-tertiary, #666)' }} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto overscroll-contain p-2 space-y-1">
              {chatMessages.length === 0 && (
                <p className="text-[9px] font-mono text-center py-4" style={{ color: 'var(--color-text-tertiary, #666)' }}>
                  No messages yet
                </p>
              )}
              {chatMessages.map((msg) => (
                <div key={msg.id} className="px-1 py-0.5">
                  <div className="flex items-baseline gap-1.5">
                    <span className="text-[9px] font-mono font-semibold" style={{ color: 'var(--color-cyan, #00d4ff)' }}>
                      {msg.sender === selfIdentity ? 'You' : msg.senderName}
                    </span>
                    <span className="text-[7px] font-mono" style={{ color: 'var(--color-text-tertiary, #666)' }}>
                      {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <p className="text-[10px] font-mono whitespace-pre-wrap break-words" style={{ color: 'var(--color-text-primary, #e0e0e0)' }}>
                    {msg.content}
                  </p>
                </div>
              ))}
              <ChatScrollAnchor messages={chatMessages} />
            </div>
            <form onSubmit={sendChatMessage}
              className="flex items-center gap-1.5 px-2 py-1.5 border-t shrink-0"
              style={{
                borderColor: 'var(--color-border, #222)',
                paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 6px)',
              }}
            >
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Message..."
                className="flex-1 text-[10px] font-mono px-2 py-1.5 rounded border bg-transparent outline-none"
                style={{ borderColor: 'var(--color-border, #222)', color: 'var(--color-text-primary, #e0e0e0)' }}
              />
              <button type="submit"
                disabled={!chatInput.trim()}
                className="p-1.5 rounded transition-colors min-w-[36px] min-h-[36px] flex items-center justify-center"
                style={{
                  background: chatInput.trim() ? 'var(--color-cyan, #00d4ff)' : 'transparent',
                  color: chatInput.trim() ? 'var(--color-canvas, #0a0a0f)' : 'var(--color-text-tertiary, #666)',
                }}
              >
                <Send size={11} />
              </button>
            </form>
          </div>
        )}
      </div>

      {/* ─── Call bar — Discord style ─── */}
      <div className="flex items-center justify-center gap-0.5 sm:gap-1 px-2 sm:px-3 py-2 border-t shrink-0"
        style={{
          borderColor: 'var(--color-border, #222)',
          background: 'var(--color-surface, #111)',
          paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 8px)',
        }}
      >
        {permissions.can_speak && (
          <GuestCallBarButton
            active={micOn}
            danger={!micOn}
            icon={micOn ? Mic : MicOff}
            label={micOn ? 'Mute' : 'Unmute'}
            onClick={toggleMic}
          />
        )}
        <GuestCallBarButton
          active={!deafened}
          danger={deafened}
          icon={deafened ? VolumeX : Volume2}
          label={deafened ? 'Undeafen' : 'Deafen'}
          onClick={toggleDeafen}
        />
        {permissions.can_video && (
          <GuestCallBarButton
            active={videoOn}
            danger={camError !== null}
            icon={camError ? AlertTriangle : videoOn ? Video : VideoOff}
            label={camError ? 'Cam Fail' : videoOn ? 'Stop Video' : 'Video'}
            onClick={toggleVideo}
          />
        )}
        {permissions.can_screen_share && typeof navigator.mediaDevices?.getDisplayMedia === 'function' && (
          <GuestCallBarButton
            active={screenSharing}
            icon={screenSharing ? MonitorOff : Monitor}
            label={screenSharing ? 'Stop Share' : 'Share'}
            onClick={toggleScreenShare}
          />
        )}
        {permissions.can_chat && (
          <GuestCallBarButton
            active={chatOpen}
            icon={MessageSquare}
            label="Chat"
            onClick={() => setChatOpen(!chatOpen)}
          />
        )}
        <div className="w-px h-5 mx-0.5 hidden sm:block" style={{ background: 'var(--color-border, #222)' }} />
        <button onClick={handleLeave}
          className="flex items-center gap-1.5 text-[10px] font-mono px-2.5 sm:px-3 py-2 rounded-lg transition-colors"
          style={{ background: 'var(--color-danger, #ff4444)', color: '#fff' }}
        >
          <PhoneOff size={14} />
          <span className="hidden sm:inline">Leave</span>
        </button>
      </div>
    </div>
  )
}

/* ─── Shared Sub-components ─── */

function GuestCallBarButton({
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
      className="flex flex-col items-center gap-0.5 px-2 sm:px-2.5 py-1.5 rounded-lg transition-all min-w-[40px] min-h-[40px] justify-center"
      style={{
        background: danger ? 'var(--color-danger, #ff4444)' : active ? 'var(--color-surface-raised, #1a1a1a)' : 'transparent',
        color: danger ? '#fff' : active ? 'var(--color-text-primary, #e0e0e0)' : 'var(--color-text-tertiary, #666)',
      }}
      title={label}
    >
      <Icon size={16} />
      <span className="text-[7px] font-mono leading-none">{label}</span>
    </button>
  )
}

function GuestParticipantList({ participants, selfIdentity }: {
  participants: GuestParticipant[]
  selfIdentity: string | undefined
}) {
  if (participants.length === 0) return null
  return (
    <div className="flex gap-1.5 overflow-x-auto py-1 shrink-0 px-1">
      {participants.map(p => (
        <div key={p.identity} className="flex items-center gap-1 px-2 py-1 rounded shrink-0"
          style={{ background: 'var(--color-surface, #111)' }}
        >
          <div className="w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-mono font-bold"
            style={{
              background: p.isSpeaking ? 'var(--color-ok-dim, rgba(0,200,83,0.1))' : 'var(--color-surface-overlay, #1a1a1a)',
              color: p.isSpeaking ? 'var(--color-ok, #00c853)' : 'var(--color-text-secondary, #999)',
              outline: p.isSpeaking ? '1.5px solid var(--color-ok, #00c853)' : 'none',
            }}
          >
            {p.name.charAt(0).toUpperCase()}
          </div>
          <span className="text-[9px] font-mono truncate max-w-[60px]" style={{ color: 'var(--color-text-secondary, #999)' }}>
            {p.name}
          </span>
          {p.isMuted && <MicOff size={9} style={{ color: 'var(--color-danger, #ff4444)' }} />}
        </div>
      ))}
    </div>
  )
}

function ChatScrollAnchor({ messages }: { messages: ChatMessage[] }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    ref.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])
  return <div ref={ref} />
}
