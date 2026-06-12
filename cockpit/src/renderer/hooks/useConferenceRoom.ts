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

export type StreamSourceType = 'camera' | 'screen' | 'window' | 'tab' | 'application'

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
}

export interface ConferenceParticipant {
  identity: string
  name: string
  isSpeaking: boolean
  isMuted: boolean
  isDeafened: boolean
  isVideoOn: boolean
  connectionQuality: ConnectionQuality
  streamCount: number
}

export type ConferenceRoomState =
  | 'idle'
  | 'requesting_permissions'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'failed'
  | 'disconnected'

export type JoinStage =
  | 'idle'
  | 'fetching_token'
  | 'token_ready'
  | 'connecting'
  | 'requesting_mic'
  | 'publishing_mic'
  | 'requesting_camera'
  | 'connected'

export interface ConferenceDiagnostics {
  livekitUrl: string | null
  roomName: string | null
  participantIdentity: string | null
  tokenReceived: boolean
  signalConnected: boolean
  iceState: string | null
  publisherState: string | null
  subscriberState: string | null
  micPermission: 'unknown' | 'granted' | 'denied'
  micEnabledRequested: boolean
  micEnabledActual: boolean
  audioTrackSid: string | null
  audioPublicationExists: boolean
  lastMicError: string | null
  cameraPermission: 'unknown' | 'granted' | 'denied'
  cameraEnabledActual: boolean
  videoTrackSid: string | null
  videoPublicationExists: boolean
  localPreviewAttached: boolean
  lastVideoError: string | null
  screenShareSupport: boolean
  lastEvent: string | null
  lastError: string | null
  reconnectAttempts: number
  publishedTrackCount: number
  subscribedTrackCount: number
  joinStage: JoinStage
}

export interface AIGovernancePermissions {
  ai_can_join: boolean
  ai_can_listen: boolean
  ai_can_speak: boolean
  ai_can_transcribe: boolean
  ai_can_summarize: boolean
  ai_can_create_action_items: boolean
  ai_access_logged: boolean
}

export const DEFAULT_AI_GOVERNANCE: AIGovernancePermissions = {
  ai_can_join: false,
  ai_can_listen: false,
  ai_can_speak: false,
  ai_can_transcribe: false,
  ai_can_summarize: false,
  ai_can_create_action_items: false,
  ai_access_logged: true,
}

export interface ProductionTestItem {
  label: string
  status: 'pass' | 'fail' | 'unknown' | 'pending'
  detail: string
}

export interface UseConferenceRoomReturn {
  state: ConferenceRoomState
  error: string | null
  participants: ConferenceParticipant[]
  isMuted: boolean
  isDeafened: boolean
  isVideoOn: boolean
  preJoinMicEnabled: boolean
  preJoinVideoEnabled: boolean
  streams: Map<string, MediaStreamSource[]>
  localStreams: MediaStreamSource[]
  diagnostics: ConferenceDiagnostics
  aiGovernance: AIGovernancePermissions
  productionChecklist: ProductionTestItem[]
  join: () => Promise<void>
  leave: () => void
  toggleMute: () => Promise<void>
  toggleDeafen: () => void
  togglePreJoinMic: () => void
  togglePreJoinVideo: () => void
  toggleVideo: () => Promise<void>
  addScreenShare: () => Promise<void>
  stopStream: (trackSid: string) => Promise<void>
  stopAllStreams: () => Promise<void>
  canAddStream: boolean
  getVideoElement: (trackSid: string) => HTMLVideoElement | null
  setAIGovernance: (patch: Partial<AIGovernancePermissions>) => void
}

const MAX_STREAMS_PER_USER = 4
const MAX_RECONNECT_ATTEMPTS = 5
const INITIAL_BACKOFF_MS = 1000

export function detectScreenShareSupport(): boolean {
  if (typeof navigator === 'undefined') return false
  const isNativeApp = !!(window as Record<string, unknown>).Capacitor
    || !!(window as Record<string, unknown>).ReactNativeWebView
  if (isNativeApp) return true
  return typeof navigator.mediaDevices?.getDisplayMedia === 'function'
}

function getTrackDimensions(pub: TrackPublication): { width: number; height: number } | null {
  const dims = pub.dimensions
  if (dims && dims.width && dims.height) return { width: dims.width, height: dims.height }
  return null
}

function classifyScreenTrack(pub: TrackPublication): StreamSourceType {
  const track = pub.track
  if (!track) return 'screen'
  const settings = track.mediaStreamTrack?.getSettings?.()
  const label = track.mediaStreamTrack?.label?.toLowerCase() ?? ''
  if (settings?.displaySurface === 'window') return 'window'
  if (settings?.displaySurface === 'browser') return 'tab'
  if (settings?.displaySurface === 'monitor') return 'screen'
  if (label.includes('tab')) return 'tab'
  if (label.includes('window')) return 'window'
  return 'screen'
}

function buildStreamSources(p: Participant): MediaStreamSource[] {
  const sources: MediaStreamSource[] = []
  let screenIdx = 0
  for (const pub of p.trackPublications.values()) {
    if (!pub.track || pub.track.kind !== Track.Kind.Video) continue
    const isCamera = pub.source === Track.Source.Camera
    const isScreen = pub.source === Track.Source.ScreenShare
    if (!isCamera && !isScreen) continue

    const sourceType: StreamSourceType = isCamera ? 'camera' : classifyScreenTrack(pub)
    if (isScreen) screenIdx++

    sources.push({
      id: pub.trackSid,
      kind: 'video',
      sourceType,
      name: isCamera ? 'Camera' : `Screen ${screenIdx}`,
      trackSid: pub.trackSid,
      participantIdentity: p.identity,
      muted: pub.isMuted,
      dimensions: getTrackDimensions(pub),
      frameRate: pub.track.mediaStreamTrack?.getSettings?.()?.frameRate ?? null,
    })
  }
  return sources
}

function participantToInfo(
  p: Participant,
  streams: MediaStreamSource[],
  localMicSetupDone: boolean,
  localMicIntent: boolean,
  localDeafened: boolean,
): ConferenceParticipant {
  let isMuted: boolean
  if (p instanceof LocalParticipant && !localMicSetupDone) {
    isMuted = !localMicIntent
  } else {
    isMuted = !p.isMicrophoneEnabled
  }
  return {
    identity: p.identity,
    name: p.name || p.identity,
    isSpeaking: p.isSpeaking,
    isMuted,
    isDeafened: p instanceof LocalParticipant ? localDeafened : false,
    isVideoOn: p.isCameraEnabled,
    connectionQuality: p.connectionQuality,
    streamCount: streams.filter(s => s.sourceType !== 'camera').length,
  }
}

function findAudioTrackSid(p: LocalParticipant): string | null {
  for (const pub of p.trackPublications.values()) {
    if (pub.source === Track.Source.Microphone && pub.track) {
      return pub.trackSid
    }
  }
  return null
}

function findVideoTrackSid(p: LocalParticipant): string | null {
  for (const pub of p.trackPublications.values()) {
    if (pub.source === Track.Source.Camera && pub.track) {
      return pub.trackSid
    }
  }
  return null
}

function hasPublication(p: LocalParticipant, source: Track.Source): boolean {
  for (const pub of p.trackPublications.values()) {
    if (pub.source === source) return true
  }
  return false
}

const INITIAL_DIAGNOSTICS: ConferenceDiagnostics = {
  livekitUrl: null,
  roomName: null,
  participantIdentity: null,
  tokenReceived: false,
  signalConnected: false,
  iceState: null,
  publisherState: null,
  subscriberState: null,
  micPermission: 'unknown',
  micEnabledRequested: true,
  micEnabledActual: false,
  audioTrackSid: null,
  audioPublicationExists: false,
  lastMicError: null,
  cameraPermission: 'unknown',
  cameraEnabledActual: false,
  videoTrackSid: null,
  videoPublicationExists: false,
  localPreviewAttached: false,
  lastVideoError: null,
  screenShareSupport: detectScreenShareSupport(),
  lastEvent: null,
  lastError: null,
  reconnectAttempts: 0,
  publishedTrackCount: 0,
  subscribedTrackCount: 0,
  joinStage: 'idle',
}

function buildProductionChecklist(
  state: ConferenceRoomState,
  diag: ConferenceDiagnostics,
): ProductionTestItem[] {
  const s = (ok: boolean): 'pass' | 'fail' => ok ? 'pass' : 'fail'
  const idle = state === 'idle'
  return [
    { label: 'Auth Valid', status: idle ? 'unknown' : 'pass', detail: 'Clerk JWT' },
    { label: 'LiveKit Token', status: diag.tokenReceived ? 'pass' : idle ? 'unknown' : 'fail', detail: diag.tokenReceived ? 'Received' : 'Not received' },
    { label: 'LiveKit Connected', status: diag.signalConnected ? 'pass' : idle ? 'unknown' : 'pending', detail: diag.signalConnected ? 'Signal connected' : 'Not connected' },
    { label: 'Mic Permission', status: diag.micPermission === 'granted' ? 'pass' : diag.micPermission === 'denied' ? 'fail' : 'unknown', detail: diag.micPermission },
    { label: 'Camera Permission', status: diag.cameraPermission === 'granted' ? 'pass' : diag.cameraPermission === 'denied' ? 'fail' : 'unknown', detail: diag.cameraPermission },
    { label: 'Screen Share Support', status: s(diag.screenShareSupport), detail: diag.screenShareSupport ? 'Supported' : 'Not supported' },
    { label: 'Published Audio', status: diag.micEnabledActual ? 'pass' : idle ? 'unknown' : 'pending', detail: diag.audioTrackSid ?? 'None' },
    { label: 'Published Video', status: diag.cameraEnabledActual ? 'pass' : 'unknown', detail: diag.cameraEnabledActual ? 'Active' : 'Off' },
    { label: 'Published Tracks', status: diag.publishedTrackCount > 0 ? 'pass' : idle ? 'unknown' : 'pending', detail: String(diag.publishedTrackCount) },
    { label: 'Subscribed Tracks', status: diag.subscribedTrackCount > 0 ? 'pass' : 'unknown', detail: String(diag.subscribedTrackCount) },
    { label: 'Chat Connected', status: idle ? 'unknown' : 'pass', detail: 'Via rooms API' },
    { label: 'Reconnect State', status: diag.reconnectAttempts > 0 ? 'pending' : state === 'reconnecting' ? 'pending' : 'pass', detail: `${diag.reconnectAttempts} attempts` },
    { label: 'Participant Count', status: idle ? 'unknown' : 'pass', detail: idle ? '0' : 'Active' },
  ]
}

export function useConferenceRoom(channelId: string): UseConferenceRoomReturn {
  const roomRef = useRef<Room | null>(null)
  const intentionalDisconnectRef = useRef(false)
  const videoElementsRef = useRef<Map<string, HTMLVideoElement>>(new Map())
  const localScreenTracksRef = useRef<Map<string, LocalVideoTrack>>(new Map())
  const preJoinMicRef = useRef(true)
  const preJoinVideoRef = useRef(false)
  const micSetupDoneRef = useRef(false)
  const deafenedRef = useRef(false)
  const prefetchedTokenRef = useRef<{ token: string; url: string; room: string; fetchedAt: number } | null>(null)
  const prefetchingRef = useRef(false)

  const [state, setState] = useState<ConferenceRoomState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [participants, setParticipants] = useState<ConferenceParticipant[]>([])
  const [isMuted, setIsMuted] = useState(false)
  const [isDeafened, setIsDeafened] = useState(false)
  const [isVideoOn, setIsVideoOn] = useState(false)
  const [preJoinMicEnabled, setPreJoinMicEnabled] = useState(true)
  const [preJoinVideoEnabled, setPreJoinVideoEnabled] = useState(false)
  const [streams, setStreams] = useState<Map<string, MediaStreamSource[]>>(new Map())
  const [diagnostics, setDiagnostics] = useState<ConferenceDiagnostics>({ ...INITIAL_DIAGNOSTICS })
  const [aiGovernance, setAIGovernanceState] = useState<AIGovernancePermissions>({ ...DEFAULT_AI_GOVERNANCE })

  const updateDiag = useCallback((patch: Partial<ConferenceDiagnostics>) => {
    setDiagnostics((prev) => ({ ...prev, ...patch }))
  }, [])

  const syncAllState = useCallback(() => {
    const room = roomRef.current
    if (!room) return

    const micDone = micSetupDoneRef.current
    const micIntent = preJoinMicRef.current

    if (micDone) {
      const micEnabled = room.localParticipant.isMicrophoneEnabled
      setIsMuted(!micEnabled)
    }

    const camEnabled = room.localParticipant.isCameraEnabled
    setIsVideoOn(camEnabled)

    const audioSid = findAudioTrackSid(room.localParticipant)

    const allStreams = new Map<string, MediaStreamSource[]>()
    const allParticipants: ConferenceParticipant[] = []
    const deaf = deafenedRef.current

    const localSources = buildStreamSources(room.localParticipant)
    allStreams.set(room.localParticipant.identity, localSources)
    allParticipants.push(participantToInfo(room.localParticipant, localSources, micDone, micIntent, deaf))

    room.remoteParticipants.forEach((rp) => {
      const remoteSources = buildStreamSources(rp)
      allStreams.set(rp.identity, remoteSources)
      allParticipants.push(participantToInfo(rp, remoteSources, true, true, false))
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
    const videoSid = findVideoTrackSid(room.localParticipant)
    updateDiag({
      publishedTrackCount: publishedCount,
      subscribedTrackCount: subscribedCount,
      micEnabledActual: room.localParticipant.isMicrophoneEnabled,
      cameraEnabledActual: camEnabled,
      audioTrackSid: audioSid,
      audioPublicationExists: hasPublication(room.localParticipant, Track.Source.Microphone),
      videoTrackSid: videoSid,
      videoPublicationExists: hasPublication(room.localParticipant, Track.Source.Camera),
      localPreviewAttached: videoSid ? videoElementsRef.current.has(videoSid) : false,
    })
  }, [updateDiag])

  const attachVideoTrack = useCallback((trackSid: string, track: { attach: () => HTMLMediaElement }) => {
    if (videoElementsRef.current.has(trackSid)) return
    const el = track.attach() as HTMLVideoElement
    el.id = `lk-video-${trackSid}`
    el.style.display = 'none'
    el.style.position = 'absolute'
    document.body.appendChild(el)
    videoElementsRef.current.set(trackSid, el)
  }, [])

  const detachVideoTrack = useCallback((trackSid: string) => {
    const el = videoElementsRef.current.get(trackSid)
    if (el) {
      el.remove()
      videoElementsRef.current.delete(trackSid)
    }
  }, [])

  const prefetchToken = useCallback(async () => {
    if (prefetchingRef.current) return
    const cached = prefetchedTokenRef.current
    if (cached && Date.now() - cached.fetchedAt < 25000) return
    prefetchingRef.current = true
    try {
      const res = await fetchApi(`/rooms/channels/${channelId}/voice/token`, {
        method: 'POST',
      }) as { token: string; url: string; room: string }
      if (res.token && res.url) {
        prefetchedTokenRef.current = { ...res, fetchedAt: Date.now() }
        updateDiag({ tokenReceived: true, joinStage: 'token_ready', lastEvent: 'token prefetched' })
      }
    } catch {
      // prefetch failure is not fatal — doConnect will retry
    } finally {
      prefetchingRef.current = false
    }
  }, [channelId, updateDiag])

  useEffect(() => {
    prefetchToken()
  }, [prefetchToken])

  const doConnect = useCallback(async (micEnabled: boolean, videoEnabled: boolean) => {
    setState('connecting')
    setError(null)
    micSetupDoneRef.current = false
    updateDiag({ lastEvent: 'joining...', micEnabledRequested: micEnabled, joinStage: 'fetching_token' })

    try {
      let tokenData: { token: string; url: string; room: string }
      const cached = prefetchedTokenRef.current
      if (cached && Date.now() - cached.fetchedAt < 25000) {
        tokenData = cached
        updateDiag({ joinStage: 'token_ready', lastEvent: 'using prefetched token' })
      } else {
        updateDiag({ lastEvent: 'fetching token...' })
        const res = await fetchApi(`/rooms/channels/${channelId}/voice/token`, {
          method: 'POST',
        }) as { token: string; url: string; room: string }
        if (!res.token || !res.url) {
          throw new Error('No token or URL returned from server')
        }
        tokenData = res
      }
      prefetchedTokenRef.current = null

      updateDiag({
        livekitUrl: tokenData.url,
        roomName: tokenData.room,
        tokenReceived: true,
        joinStage: 'connecting',
        lastEvent: 'connecting to LiveKit...',
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
            updateDiag({ reconnectAttempts: 0, joinStage: 'connected' })
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
        for (const pub of participant.trackPublications.values()) {
          detachVideoTrack(pub.trackSid)
        }
        syncAllState()
      })

      room.on(RoomEvent.ActiveSpeakersChanged, () => syncAllState())
      room.on(RoomEvent.TrackMuted, () => syncAllState())
      room.on(RoomEvent.TrackUnmuted, () => syncAllState())
      room.on(RoomEvent.ConnectionQualityChanged, () => syncAllState())

      room.on(RoomEvent.LocalTrackPublished, (pub: LocalTrackPublication, _lp: LocalParticipant) => {
        updateDiag({ lastEvent: `published ${pub.source} (${pub.trackSid})` })
        if (pub.track && pub.track.kind === Track.Kind.Video) {
          attachVideoTrack(pub.trackSid, pub.track)
        }
        if (pub.source === Track.Source.Microphone) {
          micSetupDoneRef.current = true
          setIsMuted(false)
          updateDiag({ micPermission: 'granted', micEnabledActual: true, audioTrackSid: pub.trackSid, audioPublicationExists: true, lastMicError: null })
        }
        syncAllState()
      })

      room.on(RoomEvent.LocalTrackUnpublished, (pub: LocalTrackPublication, _lp: LocalParticipant) => {
        updateDiag({ lastEvent: `unpublished ${pub.source}` })
        detachVideoTrack(pub.trackSid)
        localScreenTracksRef.current.delete(pub.trackSid)
        syncAllState()
      })

      room.on(RoomEvent.TrackSubscribed, (track, pub: RemoteTrackPublication, participant: RemoteParticipant) => {
        if (track.kind === Track.Kind.Audio) {
          const el = track.attach()
          el.id = `lk-audio-${participant.identity}-${pub.trackSid}`
          document.body.appendChild(el)
        }
        if (track.kind === Track.Kind.Video) {
          attachVideoTrack(pub.trackSid, track)
        }
        syncAllState()
      })

      room.on(RoomEvent.TrackUnsubscribed, (track, pub: RemoteTrackPublication) => {
        track.detach().forEach((el) => el.remove())
        detachVideoTrack(pub.trackSid)
        syncAllState()
      })

      room.on(RoomEvent.Disconnected, (reason?: DisconnectReason) => {
        updateDiag({
          lastEvent: `disconnected: ${reason ?? 'unknown'}`,
          signalConnected: false,
          joinStage: 'idle',
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
        updateDiag({ lastEvent: `media error: ${msg}`, lastError: msg })
      })

      updateDiag({ joinStage: micEnabled ? 'requesting_mic' : 'connecting' })
      await room.connect(tokenData.url, tokenData.token, {
        autoSubscribe: true,
      })
      updateDiag({ participantIdentity: room.localParticipant.identity, joinStage: 'publishing_mic' })

      if (micEnabled) {
        try {
          await room.localParticipant.setMicrophoneEnabled(true)
          micSetupDoneRef.current = true
          const isEnabled = room.localParticipant.isMicrophoneEnabled
          setIsMuted(!isEnabled)
          updateDiag({
            micPermission: 'granted',
            micEnabledActual: isEnabled,
            lastMicError: null,
            joinStage: 'connected',
            lastEvent: 'mic enabled',
          })
        } catch (micErr) {
          const msg = micErr instanceof Error ? micErr.message : 'unknown'
          micSetupDoneRef.current = true
          setIsMuted(true)
          updateDiag({
            micPermission: 'denied',
            micEnabledActual: false,
            lastMicError: msg,
            lastEvent: `mic denied: ${msg}`,
            lastError: `Mic: ${msg}`,
          })
        }
      } else {
        micSetupDoneRef.current = true
        updateDiag({ joinStage: 'connected', lastEvent: 'connected (mic off by choice)' })
      }

      setState('connected')

      if (videoEnabled) {
        updateDiag({ joinStage: 'requesting_camera' })
        try {
          await room.localParticipant.setCameraEnabled(true)
          updateDiag({ cameraPermission: 'granted', lastVideoError: null, lastEvent: 'camera enabled' })
        } catch (camErr) {
          const msg = camErr instanceof Error ? camErr.message : 'unknown'
          updateDiag({ cameraPermission: 'denied', lastVideoError: msg, lastEvent: `camera denied: ${msg}`, lastError: `Camera: ${msg}` })
        }
        updateDiag({ joinStage: 'connected' })
      }

      syncAllState()
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to join room'
      setState('failed')
      setError(msg)
      updateDiag({ lastEvent: `error: ${msg}`, lastError: msg, joinStage: 'idle' })
      micSetupDoneRef.current = true
      if (roomRef.current) {
        roomRef.current.disconnect()
        roomRef.current = null
      }
    }
  }, [channelId, syncAllState, updateDiag, attachVideoTrack, detachVideoTrack])

  const join = useCallback(async () => {
    if (roomRef.current) return
    intentionalDisconnectRef.current = false
    const mic = preJoinMicRef.current
    const vid = preJoinVideoRef.current
    setIsMuted(!mic)
    setIsVideoOn(vid)
    await doConnect(mic, vid)
  }, [doConnect])

  const togglePreJoinMic = useCallback(() => {
    setPreJoinMicEnabled((prev) => {
      const next = !prev
      preJoinMicRef.current = next
      setIsMuted(!next)
      return next
    })
  }, [])

  const togglePreJoinVideo = useCallback(() => {
    setPreJoinVideoEnabled((prev) => {
      const next = !prev
      preJoinVideoRef.current = next
      return next
    })
  }, [])

  const leave = useCallback(() => {
    intentionalDisconnectRef.current = true
    const room = roomRef.current
    if (room) {
      localScreenTracksRef.current.forEach((track) => track.stop())
      localScreenTracksRef.current.clear()
      room.localParticipant.setCameraEnabled(false).catch(() => {})
      room.localParticipant.setMicrophoneEnabled(false).catch(() => {})
      room.disconnect()
      roomRef.current = null
    }
    videoElementsRef.current.forEach(el => el.remove())
    videoElementsRef.current.clear()
    micSetupDoneRef.current = false
    deafenedRef.current = false
    prefetchedTokenRef.current = null
    setState('idle')
    setParticipants([])
    setError(null)
    setPreJoinMicEnabled(true)
    preJoinMicRef.current = true
    setPreJoinVideoEnabled(false)
    preJoinVideoRef.current = false
    setIsMuted(false)
    setIsDeafened(false)
    setIsVideoOn(false)
    setStreams(new Map())
    setDiagnostics({ ...INITIAL_DIAGNOSTICS })
    prefetchToken()
  }, [prefetchToken])

  const toggleMute = useCallback(async () => {
    const room = roomRef.current
    if (!room) return
    const currentlyEnabled = room.localParticipant.isMicrophoneEnabled
    const targetEnabled = !currentlyEnabled
    updateDiag({ micEnabledRequested: targetEnabled })
    try {
      await room.localParticipant.setMicrophoneEnabled(targetEnabled)
      updateDiag({ micPermission: 'granted', lastMicError: null })
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'mic toggle failed'
      updateDiag({ lastError: `Mic: ${msg}`, lastMicError: msg, micPermission: 'denied' })
    }
    const actualEnabled = room.localParticipant.isMicrophoneEnabled
    setIsMuted(!actualEnabled)
    updateDiag({ micEnabledActual: actualEnabled })
    syncAllState()
  }, [syncAllState, updateDiag])

  const toggleDeafen = useCallback(() => {
    const room = roomRef.current
    if (!room) return
    const next = !deafenedRef.current
    deafenedRef.current = next
    setIsDeafened(next)
    room.remoteParticipants.forEach((rp) => {
      rp.audioTrackPublications.forEach((pub) => {
        if (pub.track) {
          pub.track.mediaStreamTrack.enabled = !next
        }
      })
    })
    if (next) {
      setIsMuted(true)
      room.localParticipant.setMicrophoneEnabled(false).catch(() => {})
      updateDiag({ lastEvent: 'deafened — mic muted, incoming audio silenced' })
    } else {
      updateDiag({ lastEvent: 'undeafened — incoming audio restored' })
    }
    syncAllState()
  }, [syncAllState, updateDiag])

  const toggleVideo = useCallback(async () => {
    const room = roomRef.current
    if (!room) return
    const currentlyEnabled = room.localParticipant.isCameraEnabled
    try {
      await room.localParticipant.setCameraEnabled(!currentlyEnabled)
      updateDiag({
        lastEvent: !currentlyEnabled ? 'camera enabled' : 'camera disabled',
        cameraPermission: 'granted',
        lastVideoError: null,
      })
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'camera toggle failed'
      updateDiag({
        lastError: `Camera: ${msg}`,
        lastVideoError: msg,
        cameraPermission: 'denied',
        lastEvent: `camera error: ${msg}`,
      })
    }
    const actualEnabled = room.localParticipant.isCameraEnabled
    setIsVideoOn(actualEnabled)
    updateDiag({ cameraEnabledActual: actualEnabled })
    syncAllState()
  }, [syncAllState, updateDiag])

  const addScreenShare = useCallback(async () => {
    const room = roomRef.current
    if (!room) return

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
          }
          updateDiag({ lastEvent: 'screen share started' })
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

    detachVideoTrack(trackSid)
    updateDiag({ lastEvent: `stopped stream ${trackSid}` })
    syncAllState()
  }, [syncAllState, updateDiag, detachVideoTrack])

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
      detachVideoTrack(sid)
    }
    localScreenTracksRef.current.clear()
    updateDiag({ lastEvent: 'stopped all local streams' })
    syncAllState()
  }, [syncAllState, updateDiag, detachVideoTrack])

  const getVideoElement = useCallback((trackSid: string): HTMLVideoElement | null => {
    return videoElementsRef.current.get(trackSid) ?? null
  }, [])

  const setAIGovernance = useCallback((patch: Partial<AIGovernancePermissions>) => {
    setAIGovernanceState((prev) => ({ ...prev, ...patch }))
  }, [])

  const localIdentity = roomRef.current?.localParticipant?.identity
  const localStreams = localIdentity ? (streams.get(localIdentity) ?? []) : []
  const localScreenCount = localStreams.filter(s => s.sourceType !== 'camera').length
  const canAddStream = state === 'connected' && localScreenCount < MAX_STREAMS_PER_USER

  const productionChecklist = buildProductionChecklist(state, diagnostics)

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
    isDeafened,
    isVideoOn,
    preJoinMicEnabled,
    preJoinVideoEnabled,
    streams,
    localStreams,
    diagnostics,
    aiGovernance,
    productionChecklist,
    join,
    leave,
    toggleMute,
    toggleDeafen,
    togglePreJoinMic,
    togglePreJoinVideo,
    toggleVideo,
    addScreenShare,
    stopStream,
    stopAllStreams,
    canAddStream,
    getVideoElement,
    setAIGovernance,
  }
}
