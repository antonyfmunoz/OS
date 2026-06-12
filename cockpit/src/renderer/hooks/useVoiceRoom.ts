import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Room,
  RoomEvent,
  Track,
  ConnectionState,
  RemoteParticipant,
  Participant,
  RemoteTrackPublication,
  ConnectionQuality,
  LocalTrackPublication,
  DisconnectReason,
  LocalParticipant,
  createLocalScreenTracks,
  LocalVideoTrack,
  type TrackPublication,
} from 'livekit-client'
import { fetchApi } from '../api/client'

export type StreamSourceType = 'camera' | 'screen' | 'window' | 'tab' | 'application' | 'second_camera'

export interface MediaStreamSource {
  id: string
  kind: 'audio' | 'video'
  sourceType: StreamSourceType
  name: string
  trackSid: string
  participantIdentity: string
  muted: boolean
  dimensions: { width: number; height: number } | null
  frameRate: number | null
  createdAt: number
  aiVisible: boolean
  allowAiAnalysis: boolean
  captureToMemory: boolean
}

export interface VoiceParticipant {
  identity: string
  name: string
  isSpeaking: boolean
  isMuted: boolean
  isVideoOn: boolean
  connectionQuality: ConnectionQuality
  streamCount: number
}

export type VoiceRoomState =
  | 'idle'
  | 'requesting-permission'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'failed'
  | 'disconnected'

export interface VoiceDiagnostics {
  livekitUrl: string | null
  roomName: string | null
  participantIdentity: string | null
  tokenReceived: boolean
  signalConnected: boolean
  iceState: string | null
  publisherState: string | null
  subscriberState: string | null
  micPermission: 'unknown' | 'granted' | 'denied' | 'prompt'
  lastEvent: string | null
  lastError: string | null
  reconnectAttempts: number
  publishedTrackCount: number
  subscribedTrackCount: number
}

export interface UseVoiceRoomReturn {
  state: VoiceRoomState
  error: string | null
  participants: VoiceParticipant[]
  isMuted: boolean
  isVideoOn: boolean
  streams: Map<string, MediaStreamSource[]>
  localStreams: MediaStreamSource[]
  diagnostics: VoiceDiagnostics
  join: () => Promise<void>
  leave: () => void
  toggleMute: () => Promise<void>
  toggleVideo: () => Promise<void>
  addScreenShare: () => Promise<void>
  stopStream: (trackSid: string) => Promise<void>
  stopAllStreams: () => Promise<void>
  canAddStream: boolean
  getTrackElement: (trackSid: string) => HTMLVideoElement | null
}

const MAX_STREAMS_PER_USER = 4
const MAX_RECONNECT_ATTEMPTS = 5
const INITIAL_BACKOFF_MS = 1000

function getLocalMicEnabled(room: Room): boolean {
  return room.localParticipant.isMicrophoneEnabled
}

function getLocalVideoEnabled(room: Room): boolean {
  return room.localParticipant.isCameraEnabled
}

function classifyScreenSource(track: LocalVideoTrack): StreamSourceType {
  const settings = track.mediaStreamTrack?.getSettings?.()
  const label = track.mediaStreamTrack?.label?.toLowerCase() ?? ''
  if (settings?.displaySurface === 'monitor') return 'screen'
  if (settings?.displaySurface === 'window') return 'window'
  if (settings?.displaySurface === 'browser') return 'tab'
  if (label.includes('tab')) return 'tab'
  if (label.includes('window')) return 'window'
  return 'screen'
}

function getTrackDimensions(pub: TrackPublication): { width: number; height: number } | null {
  const dims = pub.dimensions
  if (dims && dims.width && dims.height) return { width: dims.width, height: dims.height }
  return null
}

function buildStreamSources(p: Participant): MediaStreamSource[] {
  const sources: MediaStreamSource[] = []
  for (const pub of p.trackPublications.values()) {
    if (!pub.track || pub.track.kind !== Track.Kind.Video) continue
    const isCamera = pub.source === Track.Source.Camera
    const isScreen = pub.source === Track.Source.ScreenShare

    if (!isCamera && !isScreen) continue

    let sourceType: StreamSourceType = 'camera'
    if (isScreen) {
      const label = pub.track.mediaStreamTrack?.label?.toLowerCase() ?? ''
      const settings = pub.track.mediaStreamTrack?.getSettings?.()
      if (settings?.displaySurface === 'window') sourceType = 'window'
      else if (settings?.displaySurface === 'browser') sourceType = 'tab'
      else if (label.includes('tab')) sourceType = 'tab'
      else if (label.includes('window')) sourceType = 'window'
      else sourceType = 'screen'
    }

    sources.push({
      id: pub.trackSid,
      kind: 'video',
      sourceType,
      name: pub.trackName || (isCamera ? 'Camera' : `Screen ${sources.filter(s => s.sourceType !== 'camera').length + 1}`),
      trackSid: pub.trackSid,
      participantIdentity: p.identity,
      muted: pub.isMuted,
      dimensions: getTrackDimensions(pub),
      frameRate: pub.track.mediaStreamTrack?.getSettings?.()?.frameRate ?? null,
      createdAt: Date.now(),
      aiVisible: true,
      allowAiAnalysis: false,
      captureToMemory: false,
    })
  }
  return sources
}

function participantToInfo(p: Participant, streams: MediaStreamSource[]): VoiceParticipant {
  const audioTrack = Array.from(p.trackPublications.values()).find(
    (t) => t.track?.kind === Track.Kind.Audio && t.source === Track.Source.Microphone
  )
  return {
    identity: p.identity,
    name: p.name || p.identity,
    isSpeaking: p.isSpeaking,
    isMuted: audioTrack ? audioTrack.isMuted : true,
    isVideoOn: streams.some(s => s.sourceType === 'camera' && !s.muted),
    connectionQuality: p.connectionQuality,
    streamCount: streams.length,
  }
}

const INITIAL_DIAGNOSTICS: VoiceDiagnostics = {
  livekitUrl: null,
  roomName: null,
  participantIdentity: null,
  tokenReceived: false,
  signalConnected: false,
  iceState: null,
  publisherState: null,
  subscriberState: null,
  micPermission: 'unknown',
  lastEvent: null,
  lastError: null,
  reconnectAttempts: 0,
  publishedTrackCount: 0,
  subscribedTrackCount: 0,
}

export function useVoiceRoom(channelId: string): UseVoiceRoomReturn {
  const roomRef = useRef<Room | null>(null)
  const intentionalDisconnectRef = useRef(false)
  const videoElementsRef = useRef<Map<string, HTMLVideoElement>>(new Map())
  const localScreenTracksRef = useRef<Map<string, LocalVideoTrack>>(new Map())

  const [state, setState] = useState<VoiceRoomState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [participants, setParticipants] = useState<VoiceParticipant[]>([])
  const [isMuted, setIsMuted] = useState(false)
  const [isVideoOn, setIsVideoOn] = useState(false)
  const [streams, setStreams] = useState<Map<string, MediaStreamSource[]>>(new Map())
  const [diagnostics, setDiagnostics] = useState<VoiceDiagnostics>({ ...INITIAL_DIAGNOSTICS })

  const updateDiag = useCallback((patch: Partial<VoiceDiagnostics>) => {
    setDiagnostics((prev) => ({ ...prev, ...patch }))
  }, [])

  const syncAllState = useCallback(() => {
    const room = roomRef.current
    if (!room) return

    setIsMuted(!getLocalMicEnabled(room))
    setIsVideoOn(getLocalVideoEnabled(room))

    const allStreams = new Map<string, MediaStreamSource[]>()
    const allParticipants: VoiceParticipant[] = []

    const localSources = buildStreamSources(room.localParticipant)
    allStreams.set(room.localParticipant.identity, localSources)
    allParticipants.push(participantToInfo(room.localParticipant, localSources))

    room.remoteParticipants.forEach((rp) => {
      const remoteSources = buildStreamSources(rp)
      allStreams.set(rp.identity, remoteSources)
      allParticipants.push(participantToInfo(rp, remoteSources))
    })

    setStreams(allStreams)
    setParticipants(allParticipants)

    let publishedCount = 0
    let subscribedCount = 0
    room.localParticipant.trackPublications.forEach(() => publishedCount++)
    room.remoteParticipants.forEach((rp) => {
      rp.trackPublications.forEach((pub) => {
        if (pub.isSubscribed) subscribedCount++
      })
    })
    updateDiag({ publishedTrackCount: publishedCount, subscribedTrackCount: subscribedCount })
  }, [updateDiag])

  const doConnect = useCallback(async () => {
    setState('connecting')
    setError(null)
    updateDiag({ lastEvent: 'requesting token...' })

    try {
      const res = await fetchApi(`/rooms/channels/${channelId}/voice/token`, {
        method: 'POST',
      }) as { token: string; url: string; room: string }

      if (!res.token || !res.url) {
        throw new Error('No token or URL returned from server')
      }

      updateDiag({
        livekitUrl: res.url,
        roomName: res.room,
        tokenReceived: true,
        lastEvent: 'token received, connecting...',
      })

      const room = new Room({
        adaptiveStream: true,
        dynacast: true,
        disconnectOnPageLeave: true,
        reconnectPolicy: {
          nextRetryDelayInMs: (context) => {
            if (context.retryCount >= MAX_RECONNECT_ATTEMPTS) return null
            const delay = INITIAL_BACKOFF_MS * Math.pow(2, context.retryCount)
            updateDiag({
              reconnectAttempts: context.retryCount + 1,
              lastEvent: `reconnect attempt ${context.retryCount + 1}/${MAX_RECONNECT_ATTEMPTS} in ${delay}ms`,
            })
            return delay
          },
        },
      })
      roomRef.current = room

      room.on(RoomEvent.SignalConnected, () => {
        updateDiag({ signalConnected: true, lastEvent: 'signal connected' })
      })

      room.on(RoomEvent.ConnectionStateChanged, (connectionState: ConnectionState) => {
        updateDiag({ lastEvent: `connection: ${connectionState}` })
        switch (connectionState) {
          case ConnectionState.Connected:
            setState('connected')
            updateDiag({ reconnectAttempts: 0 })
            syncAllState()
            break
          case ConnectionState.Reconnecting:
            setState('reconnecting')
            break
          case ConnectionState.Disconnected:
            if (!intentionalDisconnectRef.current) {
              setState('disconnected')
              updateDiag({ signalConnected: false, lastEvent: 'disconnected unexpectedly' })
            }
            break
        }
      })

      room.on(RoomEvent.Reconnected, () => {
        setState('connected')
        updateDiag({ reconnectAttempts: 0, signalConnected: true, lastEvent: 'reconnected successfully' })
        syncAllState()
      })

      room.on(RoomEvent.ParticipantConnected, (participant: RemoteParticipant) => {
        updateDiag({ lastEvent: `${participant.identity} joined` })
        syncAllState()
      })
      room.on(RoomEvent.ParticipantDisconnected, (participant: RemoteParticipant) => {
        updateDiag({ lastEvent: `${participant.identity} left` })
        videoElementsRef.current.forEach((el, sid) => {
          const pubs = Array.from(participant.trackPublications.values())
          if (pubs.some(p => p.trackSid === sid)) {
            el.remove()
            videoElementsRef.current.delete(sid)
          }
        })
        syncAllState()
      })

      room.on(RoomEvent.ActiveSpeakersChanged, () => syncAllState())
      room.on(RoomEvent.TrackMuted, () => syncAllState())
      room.on(RoomEvent.TrackUnmuted, () => syncAllState())
      room.on(RoomEvent.ConnectionQualityChanged, () => syncAllState())

      room.on(RoomEvent.LocalTrackPublished, (_pub: LocalTrackPublication, _lp: LocalParticipant) => {
        updateDiag({ lastEvent: `published ${_pub.source} (${_pub.trackSid})` })
        syncAllState()
      })
      room.on(RoomEvent.LocalTrackUnpublished, (_pub: LocalTrackPublication, _lp: LocalParticipant) => {
        updateDiag({ lastEvent: `unpublished ${_pub.source}` })
        if (_pub.trackSid) {
          const el = videoElementsRef.current.get(_pub.trackSid)
          if (el) {
            el.remove()
            videoElementsRef.current.delete(_pub.trackSid)
          }
          localScreenTracksRef.current.delete(_pub.trackSid)
        }
        syncAllState()
      })

      room.on(RoomEvent.TrackSubscribed, (track, _pub: RemoteTrackPublication, participant: RemoteParticipant) => {
        if (track.kind === Track.Kind.Audio) {
          const el = track.attach()
          el.id = `lk-audio-${participant.identity}-${_pub.trackSid}`
          document.body.appendChild(el)
        }
        if (track.kind === Track.Kind.Video) {
          const videoEl = track.attach() as HTMLVideoElement
          videoEl.id = `lk-video-${_pub.trackSid}`
          videoEl.style.display = 'none'
          document.body.appendChild(videoEl)
          videoElementsRef.current.set(_pub.trackSid, videoEl)
        }
        syncAllState()
      })

      room.on(RoomEvent.TrackUnsubscribed, (track, pub: RemoteTrackPublication) => {
        track.detach().forEach((el) => el.remove())
        if (pub.trackSid) {
          videoElementsRef.current.delete(pub.trackSid)
        }
        syncAllState()
      })

      room.on(RoomEvent.Disconnected, (reason?: DisconnectReason) => {
        updateDiag({
          lastEvent: `disconnected: ${reason ?? 'unknown'}`,
          signalConnected: false,
        })
        if (!intentionalDisconnectRef.current) {
          setState('disconnected')
        }
        setParticipants([])
        setStreams(new Map())
        videoElementsRef.current.forEach(el => el.remove())
        videoElementsRef.current.clear()
        localScreenTracksRef.current.clear()
        roomRef.current = null
      })

      room.on(RoomEvent.MediaDevicesError, (e) => {
        const msg = e instanceof Error ? e.message : 'unknown media error'
        updateDiag({ lastEvent: `media error: ${msg}`, lastError: msg, micPermission: 'denied' })
      })

      updateDiag({ participantIdentity: null })
      await room.connect(res.url, res.token)
      updateDiag({
        lastEvent: 'connected, enabling mic...',
        participantIdentity: room.localParticipant.identity,
      })

      try {
        await room.localParticipant.setMicrophoneEnabled(true)
        updateDiag({ micPermission: 'granted', lastEvent: 'mic enabled' })
      } catch (micErr) {
        const msg = micErr instanceof Error ? micErr.message : 'unknown'
        updateDiag({ micPermission: 'denied', lastEvent: `mic error: ${msg}`, lastError: msg })
      }
      syncAllState()
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to join voice room'
      setState('failed')
      setError(msg)
      updateDiag({ lastEvent: `error: ${msg}`, lastError: msg })
      if (roomRef.current) {
        roomRef.current.disconnect()
        roomRef.current = null
      }
    }
  }, [channelId, syncAllState, updateDiag])

  const join = useCallback(async () => {
    if (roomRef.current) return
    intentionalDisconnectRef.current = false
    await doConnect()
  }, [doConnect])

  const leave = useCallback(() => {
    intentionalDisconnectRef.current = true
    const room = roomRef.current
    if (room) {
      localScreenTracksRef.current.forEach((track) => {
        track.stop()
      })
      localScreenTracksRef.current.clear()
      room.localParticipant.setCameraEnabled(false).catch(() => {})
      room.localParticipant.setMicrophoneEnabled(false).catch(() => {})
      room.disconnect()
      roomRef.current = null
    }
    videoElementsRef.current.forEach(el => el.remove())
    videoElementsRef.current.clear()
    setState('idle')
    setParticipants([])
    setError(null)
    setIsMuted(false)
    setIsVideoOn(false)
    setStreams(new Map())
    setDiagnostics({ ...INITIAL_DIAGNOSTICS })
  }, [])

  const toggleMute = useCallback(async () => {
    const room = roomRef.current
    if (!room) return
    const newEnabled = !getLocalMicEnabled(room)
    try {
      await room.localParticipant.setMicrophoneEnabled(newEnabled)
    } catch (err) {
      updateDiag({ lastError: err instanceof Error ? err.message : 'mic toggle failed', micPermission: 'denied' })
    }
    syncAllState()
  }, [syncAllState, updateDiag])

  const toggleVideo = useCallback(async () => {
    const room = roomRef.current
    if (!room) return
    const newEnabled = !getLocalVideoEnabled(room)
    try {
      await room.localParticipant.setCameraEnabled(newEnabled)
      updateDiag({ lastEvent: newEnabled ? 'camera enabled' : 'camera disabled' })
    } catch (err) {
      updateDiag({ lastError: err instanceof Error ? err.message : 'camera toggle failed' })
    }
    syncAllState()
  }, [syncAllState, updateDiag])

  const addScreenShare = useCallback(async () => {
    const room = roomRef.current
    if (!room) return

    const localIdentity = room.localParticipant.identity
    const currentLocalStreams = buildStreamSources(room.localParticipant)
    const screenStreams = currentLocalStreams.filter(s => s.sourceType !== 'camera')
    if (screenStreams.length >= MAX_STREAMS_PER_USER) {
      updateDiag({ lastError: `Max ${MAX_STREAMS_PER_USER} streams reached` })
      return
    }

    try {
      const tracks = await createLocalScreenTracks({ audio: true })
      for (const track of tracks) {
        if (track.kind === Track.Kind.Video) {
          const videoTrack = track as LocalVideoTrack
          const pub = await room.localParticipant.publishTrack(videoTrack, {
            source: Track.Source.ScreenShare,
            name: `screen-${Date.now()}`,
          })
          if (pub.trackSid) {
            localScreenTracksRef.current.set(pub.trackSid, videoTrack)

            const videoEl = videoTrack.attach() as HTMLVideoElement
            videoEl.id = `lk-video-${pub.trackSid}`
            videoEl.style.display = 'none'
            document.body.appendChild(videoEl)
            videoElementsRef.current.set(pub.trackSid, videoEl)
          }
          const sourceType = classifyScreenSource(videoTrack)
          updateDiag({ lastEvent: `screen share started (${sourceType})` })
        } else if (track.kind === Track.Kind.Audio) {
          await room.localParticipant.publishTrack(track, {
            source: Track.Source.ScreenShareAudio,
          })
        }
      }
      syncAllState()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'screen share failed'
      if (msg.includes('Permission denied') || msg.includes('NotAllowedError') || msg.includes('AbortError')) {
        updateDiag({ lastEvent: 'screen share cancelled by user' })
      } else {
        updateDiag({ lastError: msg, lastEvent: `screen share error: ${msg}` })
      }
    }
  }, [syncAllState, updateDiag])

  const stopStream = useCallback(async (trackSid: string) => {
    const room = roomRef.current
    if (!room) return

    const localTrack = localScreenTracksRef.current.get(trackSid)
    if (localTrack) {
      await room.localParticipant.unpublishTrack(localTrack)
      localTrack.stop()
      localScreenTracksRef.current.delete(trackSid)
    } else {
      for (const pub of room.localParticipant.trackPublications.values()) {
        if (pub.trackSid === trackSid && pub.track) {
          await room.localParticipant.unpublishTrack(pub.track)
          pub.track.stop()
          break
        }
      }
    }

    const el = videoElementsRef.current.get(trackSid)
    if (el) {
      el.remove()
      videoElementsRef.current.delete(trackSid)
    }

    updateDiag({ lastEvent: `stopped stream ${trackSid}` })
    syncAllState()
  }, [syncAllState, updateDiag])

  const stopAllStreams = useCallback(async () => {
    const room = roomRef.current
    if (!room) return

    const sids = Array.from(localScreenTracksRef.current.keys())
    for (const sid of sids) {
      const track = localScreenTracksRef.current.get(sid)
      if (track) {
        await room.localParticipant.unpublishTrack(track)
        track.stop()
      }
    }
    localScreenTracksRef.current.clear()

    videoElementsRef.current.forEach((el, sid) => {
      if (!Array.from(room.remoteParticipants.values()).some(rp =>
        Array.from(rp.trackPublications.values()).some(p => p.trackSid === sid)
      )) {
        el.remove()
        videoElementsRef.current.delete(sid)
      }
    })

    updateDiag({ lastEvent: 'stopped all local streams' })
    syncAllState()
  }, [syncAllState, updateDiag])

  const getTrackElement = useCallback((trackSid: string): HTMLVideoElement | null => {
    return videoElementsRef.current.get(trackSid) ?? null
  }, [])

  const localIdentity = roomRef.current?.localParticipant?.identity
  const localStreams = localIdentity ? (streams.get(localIdentity) ?? []) : []
  const localScreenCount = localStreams.filter(s => s.sourceType !== 'camera').length
  const canAddStream = state === 'connected' && localScreenCount < MAX_STREAMS_PER_USER

  useEffect(() => {
    return () => {
      intentionalDisconnectRef.current = true
      localScreenTracksRef.current.forEach(track => track.stop())
      localScreenTracksRef.current.clear()
      videoElementsRef.current.forEach(el => el.remove())
      videoElementsRef.current.clear()
      if (roomRef.current) {
        roomRef.current.disconnect()
        roomRef.current = null
      }
    }
  }, [])

  return {
    state,
    error,
    participants,
    isMuted,
    isVideoOn,
    streams,
    localStreams,
    diagnostics,
    join,
    leave,
    toggleMute,
    toggleVideo,
    addScreenShare,
    stopStream,
    stopAllStreams,
    canAddStream,
    getTrackElement,
  }
}
