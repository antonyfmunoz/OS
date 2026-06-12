import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import {
  Link2, AlertTriangle, Mic, MicOff, Video, VideoOff,
  PhoneOff, Loader2, Monitor, MonitorOff,
} from 'lucide-react'
import {
  Room,
  RoomEvent,
  Track,
  ConnectionState,
  RemoteTrackPublication,
  createLocalScreenTracks,
  LocalVideoTrack,
  type RemoteParticipant,
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

interface GuestParticipant {
  identity: string
  name: string
  isSpeaking: boolean
  isMuted: boolean
  isVideoOn: boolean
}

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
  const [connState, setConnState] = useState<'connecting' | 'connected' | 'disconnected' | 'failed'>('connecting')
  const [joinStage, setJoinStage] = useState<GuestJoinStage>('connecting')
  const [micOn, setMicOn] = useState(initialMic && permissions.can_speak)
  const [videoOn, setVideoOn] = useState(initialVideo && permissions.can_video)
  const [screenSharing, setScreenSharing] = useState(false)
  const [participants, setParticipants] = useState<GuestParticipant[]>([])
  const [connError, setConnError] = useState<string | null>(null)
  const [micError, setMicError] = useState<string | null>(null)
  const [camError, setCamError] = useState<string | null>(null)
  const localVideoRef = useRef<HTMLVideoElement | null>(null)
  const remoteVideoRefs = useRef<Map<string, HTMLVideoElement>>(new Map())
  const localScreenTracksRef = useRef<Map<string, LocalVideoTrack>>(new Map())

  useEffect(() => {
    const room = new Room({
      adaptiveStream: true,
      dynacast: true,
      disconnectOnPageLeave: false,
    })
    roomRef.current = room

    function syncParticipants() {
      const parts: GuestParticipant[] = []
      room.remoteParticipants.forEach((p) => {
        parts.push({
          identity: p.identity,
          name: p.name || p.identity,
          isSpeaking: p.isSpeaking,
          isMuted: !p.isMicrophoneEnabled,
          isVideoOn: p.isCameraEnabled,
        })
      })
      setParticipants(parts)
    }

    room.on(RoomEvent.Connected, () => {
      setConnState('connected')
      syncParticipants()
    })
    room.on(RoomEvent.Disconnected, () => setConnState('disconnected'))
    room.on(RoomEvent.ConnectionStateChanged, (state: ConnectionState) => {
      if (state === ConnectionState.Disconnected) setConnState('disconnected')
    })
    room.on(RoomEvent.ParticipantConnected, syncParticipants)
    room.on(RoomEvent.ParticipantDisconnected, syncParticipants)
    room.on(RoomEvent.ActiveSpeakersChanged, syncParticipants)
    room.on(RoomEvent.TrackMuted, syncParticipants)
    room.on(RoomEvent.TrackUnmuted, syncParticipants)

    room.on(RoomEvent.TrackSubscribed, (track, pub, participant) => {
      if (track.kind === 'audio') {
        const el = track.attach()
        el.id = `guest-audio-${participant.identity}-${pub.trackSid}`
        document.body.appendChild(el)
      }
      if (track.kind === 'video' && pub.source === Track.Source.Camera) {
        const el = remoteVideoRefs.current.get(participant.identity)
        if (el) track.attach(el)
      }
      if (track.kind === 'video' && pub.source === Track.Source.ScreenShare) {
        const el = remoteVideoRefs.current.get(`screen-${participant.identity}`)
        if (el) track.attach(el)
      }
      syncParticipants()
    })
    room.on(RoomEvent.TrackUnsubscribed, (track, pub) => {
      track.detach().forEach((el) => el.remove())
      syncParticipants()
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
        await room.connect(token.url, token.token)
        setConnState('connected')

        if (initialMic && permissions.can_speak) {
          setJoinStage('publishing_mic')
          try {
            await room.localParticipant.setMicrophoneEnabled(true)
            setMicOn(true)
            setMicError(null)
          } catch (micErr) {
            const msg = micErr instanceof Error ? micErr.message : 'mic failed'
            setMicError(msg)
            setMicOn(false)
          }
        }

        if (initialVideo && permissions.can_video) {
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
          }
        }

        setJoinStage('connected')
        syncParticipants()

        room.remoteParticipants.forEach((p) => {
          p.trackPublications.forEach((pub) => {
            if (pub instanceof RemoteTrackPublication && pub.track) {
              if (pub.source === Track.Source.Camera) {
                const el = remoteVideoRefs.current.get(p.identity)
                if (el) pub.track.attach(el)
              }
            }
          })
        })
      } catch (e) {
        setConnState('failed')
        setConnError(e instanceof Error ? e.message : 'Connection failed')
      }
    }
    connect()

    return () => {
      room.disconnect()
      roomRef.current = null
    }
  }, [token, initialMic, initialVideo, permissions])

  const toggleMic = useCallback(async () => {
    const room = roomRef.current
    if (!room || !permissions.can_speak) return
    const next = !micOn
    try {
      await room.localParticipant.setMicrophoneEnabled(next)
      setMicOn(next)
      setMicError(null)
    } catch (err) {
      setMicError(err instanceof Error ? err.message : 'mic toggle failed')
    }
  }, [micOn, permissions.can_speak])

  const toggleVideo = useCallback(async () => {
    const room = roomRef.current
    if (!room || !permissions.can_video) return
    const next = !videoOn
    try {
      await room.localParticipant.setCameraEnabled(next)
      if (next) {
        const camPub = room.localParticipant.getTrackPublication(Track.Source.Camera)
        if (camPub?.track && localVideoRef.current) {
          camPub.track.attach(localVideoRef.current)
        }
      }
      setVideoOn(next)
      setCamError(null)
    } catch (err) {
      setCamError(err instanceof Error ? err.message : 'camera toggle failed')
    }
  }, [videoOn, permissions.can_video])

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
  }, [screenSharing, permissions.can_screen_share])

  const handleLeave = useCallback(() => {
    const room = roomRef.current
    if (room) {
      localScreenTracksRef.current.forEach((track) => track.stop())
      localScreenTracksRef.current.clear()
      room.disconnect()
      roomRef.current = null
    }
    setConnState('disconnected')
  }, [])

  if (connState === 'failed') {
    return (
      <div className="min-h-screen flex items-center justify-center p-4" style={{ background: 'var(--color-canvas, #0a0a0f)' }}>
        <div className="text-center space-y-3">
          <AlertTriangle size={28} style={{ color: 'var(--color-danger, #ff4444)', margin: '0 auto' }} />
          <p className="text-xs font-mono" style={{ color: 'var(--color-text-primary, #e0e0e0)' }}>Connection Failed</p>
          <p className="text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary, #666)' }}>
            {connError || 'Could not connect to the room.'}
          </p>
        </div>
      </div>
    )
  }

  if (connState === 'disconnected') {
    return (
      <div className="min-h-screen flex items-center justify-center p-4" style={{ background: 'var(--color-canvas, #0a0a0f)' }}>
        <div className="text-center space-y-3">
          <PhoneOff size={28} style={{ color: 'var(--color-text-tertiary, #666)', margin: '0 auto' }} />
          <p className="text-xs font-mono" style={{ color: 'var(--color-text-primary, #e0e0e0)' }}>Disconnected</p>
          <p className="text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary, #666)' }}>
            You have left the {roomType === 'meeting' ? 'meeting' : 'voice room'}.
          </p>
        </div>
      </div>
    )
  }

  const hasAnyVideo = videoOn || participants.some(p => p.isVideoOn)

  return (
    <div className="min-h-screen flex flex-col" style={{ background: 'var(--color-canvas, #0a0a0f)' }}>
      {/* Header bar */}
      <div className="flex items-center px-4 h-10 border-b shrink-0" style={{ borderColor: 'var(--color-border, #222)' }}>
        <span className="text-[11px] font-mono font-semibold" style={{ color: 'var(--color-text-primary, #e0e0e0)' }}>
          {roomName}
        </span>
        <span className="mx-2 text-[10px]" style={{ color: 'var(--color-border, #222)' }}>|</span>
        <span className="text-[9px] font-mono px-1.5 rounded" style={{ background: 'var(--color-warn-dim, rgba(255,170,0,0.1))', color: 'var(--color-warn, #ffaa00)' }}>
          GUEST
        </span>
        <span className="text-[9px] font-mono ml-2" style={{ color: 'var(--color-text-tertiary, #666)' }}>
          {guestName}
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
          {participants.length + 1} in room
        </span>
      </div>

      {/* Errors — isolated per subsystem */}
      {(micError || camError) && (
        <div className="px-4 py-1.5 shrink-0 space-y-0.5" style={{ background: 'var(--color-danger-dim, rgba(255,68,68,0.08))' }}>
          {micError && (
            <p className="text-[9px] font-mono" style={{ color: 'var(--color-danger, #ff4444)' }}>
              Mic: {micError}
            </p>
          )}
          {camError && (
            <p className="text-[9px] font-mono" style={{ color: 'var(--color-danger, #ff4444)' }}>
              Camera: {camError}
            </p>
          )}
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col min-h-0 p-3 gap-3 overflow-y-auto">
        {/* Video area */}
        {hasAnyVideo && (
          <div className="flex flex-wrap gap-2 justify-center">
            {videoOn && (
              <div className="relative rounded overflow-hidden" style={{ background: 'var(--color-surface, #111)' }}>
                <video
                  ref={localVideoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-48 h-36 object-cover"
                  style={{ transform: 'scaleX(-1)' }}
                />
                <span className="absolute bottom-1 left-1 text-[8px] font-mono px-1 rounded" style={{ background: 'rgba(0,0,0,0.6)', color: '#fff' }}>
                  You
                </span>
              </div>
            )}
            {participants.filter(p => p.isVideoOn).map(p => (
              <div key={p.identity} className="relative rounded overflow-hidden" style={{ background: 'var(--color-surface, #111)' }}>
                <video
                  ref={(el) => {
                    if (el) remoteVideoRefs.current.set(p.identity, el)
                    else remoteVideoRefs.current.delete(p.identity)
                  }}
                  autoPlay
                  playsInline
                  muted={false}
                  className="w-48 h-36 object-cover"
                />
                <span className="absolute bottom-1 left-1 text-[8px] font-mono px-1 rounded" style={{ background: 'rgba(0,0,0,0.6)', color: '#fff' }}>
                  {p.name}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Participant list */}
        <div className="flex flex-wrap gap-1.5 justify-center">
          {participants.map(p => (
            <div key={p.identity} className="flex items-center gap-1.5 px-2 py-1 rounded" style={{ background: 'var(--color-surface, #111)' }}>
              <div className="w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-mono font-bold"
                style={{
                  background: p.isSpeaking ? 'var(--color-ok-dim, rgba(0,200,83,0.1))' : 'var(--color-surface-overlay, #1a1a1a)',
                  color: p.isSpeaking ? 'var(--color-ok, #00c853)' : 'var(--color-text-secondary, #999)',
                  outline: p.isSpeaking ? '1.5px solid var(--color-ok, #00c853)' : 'none',
                }}
              >
                {p.name.charAt(0).toUpperCase()}
              </div>
              <span className="text-[9px] font-mono" style={{ color: 'var(--color-text-secondary, #999)' }}>{p.name}</span>
              {p.isMuted && <MicOff size={9} style={{ color: 'var(--color-danger, #ff4444)' }} />}
              {p.isVideoOn && <Video size={9} style={{ color: 'var(--color-ok, #00c853)' }} />}
            </div>
          ))}
        </div>
      </div>

      {/* Control bar */}
      <div className="flex items-center justify-center gap-3 py-3 px-4 border-t shrink-0" style={{ borderColor: 'var(--color-border, #222)' }}>
        {permissions.can_speak && (
          <button
            onClick={toggleMic}
            className="flex items-center justify-center w-10 h-10 rounded-full transition-colors"
            style={{
              background: micOn ? 'var(--color-surface, #111)' : 'var(--color-danger-dim, rgba(255,68,68,0.15))',
              color: micOn ? 'var(--color-text-primary, #e0e0e0)' : 'var(--color-danger, #ff4444)',
            }}
            title={micOn ? 'Mute' : 'Unmute'}
          >
            {micOn ? <Mic size={18} /> : <MicOff size={18} />}
          </button>
        )}
        {permissions.can_video && (
          <button
            onClick={toggleVideo}
            className="flex items-center justify-center w-10 h-10 rounded-full transition-colors"
            style={{
              background: videoOn ? 'var(--color-surface, #111)' : 'var(--color-danger-dim, rgba(255,68,68,0.15))',
              color: videoOn ? 'var(--color-text-primary, #e0e0e0)' : 'var(--color-danger, #ff4444)',
            }}
            title={videoOn ? 'Camera Off' : 'Camera On'}
          >
            {videoOn ? <Video size={18} /> : <VideoOff size={18} />}
          </button>
        )}
        {permissions.can_screen_share && typeof navigator.mediaDevices?.getDisplayMedia === 'function' && (
          <button
            onClick={toggleScreenShare}
            className="flex items-center justify-center w-10 h-10 rounded-full transition-colors"
            style={{
              background: screenSharing ? 'var(--color-cyan-dim, rgba(0,212,255,0.15))' : 'var(--color-surface, #111)',
              color: screenSharing ? 'var(--color-cyan, #00d4ff)' : 'var(--color-text-primary, #e0e0e0)',
            }}
            title={screenSharing ? 'Stop Sharing' : 'Share Screen'}
          >
            {screenSharing ? <MonitorOff size={18} /> : <Monitor size={18} />}
          </button>
        )}
        <button
          onClick={handleLeave}
          className="flex items-center justify-center w-10 h-10 rounded-full transition-colors"
          style={{
            background: 'var(--color-danger, #ff4444)',
            color: '#fff',
          }}
          title="Leave"
        >
          <PhoneOff size={18} />
        </button>
      </div>
    </div>
  )
}
