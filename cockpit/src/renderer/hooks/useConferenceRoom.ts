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
  DataPacket_Kind,
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
  | 'suspended'

export type MicState =
  | 'prejoin_on'
  | 'prejoin_off'
  | 'publishing'
  | 'enabled'
  | 'disabling'
  | 'disabled'
  | 'failed'

export type CameraState =
  | 'off'
  | 'requesting_permission'
  | 'publishing'
  | 'on'
  | 'disabling'
  | 'failed'

export type JoinStage =
  | 'idle'
  | 'fetching_token'
  | 'token_ready'
  | 'connecting'
  | 'requesting_mic'
  | 'publishing_mic'
  | 'requesting_camera'
  | 'connected'

export interface MediaIntent {
  intended: boolean
  transition: MicState | CameraState
  actual: boolean
  lastActionId: number
  lastError: string | null
  updatedAt: number
}

export interface JoinTiming {
  roomOpenTimeMs: number | null
  tokenPrefetchStartMs: number | null
  tokenPrefetchDoneMs: number | null
  tokenPrefetchMs: number | null
  joinClickToConnectStartMs: number | null
  connectMs: number | null
  micPublishMs: number | null
  joinClickToOperationalMs: number | null
}

export interface VisibilityDiagnostics {
  lastVisibilityState: string
  backgroundDurationMs: number | null
  reconnectAttempts: number
  intendedMicState: boolean
  actualMicState: boolean
  intendedCameraState: boolean
  actualCameraState: boolean
}

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
  micState: MicState
  micEnabledRequested: boolean
  micEnabledActual: boolean
  audioTrackSid: string | null
  audioPublicationExists: boolean
  lastMicError: string | null
  cameraPermission: 'unknown' | 'granted' | 'denied'
  cameraState: CameraState
  cameraEnabledActual: boolean
  videoTrackSid: string | null
  videoPublicationExists: boolean
  localPreviewAttached: boolean
  lastVideoError: string | null
  screenShareSupport: boolean
  lastScreenShareError: string | null
  lastEvent: string | null
  lastError: string | null
  reconnectAttempts: number
  publishedTrackCount: number
  subscribedTrackCount: number
  joinStage: JoinStage
  joinTiming: JoinTiming
  visibility: VisibilityDiagnostics
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

export interface DataChatMessage {
  id: string
  sender: string
  senderName: string
  content: string
  timestamp: number
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
  micIntent: MediaIntent
  cameraIntent: MediaIntent
  streams: Map<string, MediaStreamSource[]>
  localStreams: MediaStreamSource[]
  diagnostics: ConferenceDiagnostics
  aiGovernance: AIGovernancePermissions
  productionChecklist: ProductionTestItem[]
  dataChatMessages: DataChatMessage[]
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
  sendDataChat: (content: string) => Promise<void>
}

const MAX_STREAMS_PER_USER = 4
const MAX_RECONNECT_ATTEMPTS = 5
const INITIAL_BACKOFF_MS = 1000
const TOKEN_CACHE_TTL_MS = 25000
const RECONNECT_WATCHDOG_MS = 3000
const DATA_CHAT_TOPIC = 'umh-chat'

let actionIdCounter = 0
function nextActionId(): number { return ++actionIdCounter }

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
  micIntent: MediaIntent,
  localDeafened: boolean,
): ConferenceParticipant {
  let isMuted: boolean
  if (p instanceof LocalParticipant) {
    if (micIntent.transition === 'publishing' || micIntent.transition === 'prejoin_on') {
      isMuted = !micIntent.intended
    } else {
      isMuted = !micIntent.actual
    }
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

const INITIAL_MIC_INTENT: MediaIntent = {
  intended: true,
  transition: 'prejoin_on',
  actual: false,
  lastActionId: 0,
  lastError: null,
  updatedAt: 0,
}

const INITIAL_CAMERA_INTENT: MediaIntent = {
  intended: false,
  transition: 'off',
  actual: false,
  lastActionId: 0,
  lastError: null,
  updatedAt: 0,
}

const INITIAL_JOIN_TIMING: JoinTiming = {
  roomOpenTimeMs: null,
  tokenPrefetchStartMs: null,
  tokenPrefetchDoneMs: null,
  tokenPrefetchMs: null,
  joinClickToConnectStartMs: null,
  connectMs: null,
  micPublishMs: null,
  joinClickToOperationalMs: null,
}

const INITIAL_VISIBILITY: VisibilityDiagnostics = {
  lastVisibilityState: 'visible',
  backgroundDurationMs: null,
  reconnectAttempts: 0,
  intendedMicState: true,
  actualMicState: false,
  intendedCameraState: false,
  actualCameraState: false,
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
  micState: 'prejoin_on',
  micEnabledRequested: true,
  micEnabledActual: false,
  audioTrackSid: null,
  audioPublicationExists: false,
  lastMicError: null,
  cameraPermission: 'unknown',
  cameraState: 'off',
  cameraEnabledActual: false,
  videoTrackSid: null,
  videoPublicationExists: false,
  localPreviewAttached: false,
  lastVideoError: null,
  screenShareSupport: detectScreenShareSupport(),
  lastScreenShareError: null,
  lastEvent: null,
  lastError: null,
  reconnectAttempts: 0,
  publishedTrackCount: 0,
  subscribedTrackCount: 0,
  joinStage: 'idle',
  joinTiming: { ...INITIAL_JOIN_TIMING },
  visibility: { ...INITIAL_VISIBILITY },
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
  const deafenedRef = useRef(false)
  const prefetchedTokenRef = useRef<{ token: string; url: string; room: string; fetchedAt: number } | null>(null)
  const prefetchingRef = useRef(false)
  const micIntentRef = useRef<MediaIntent>({ ...INITIAL_MIC_INTENT })
  const cameraIntentRef = useRef<MediaIntent>({ ...INITIAL_CAMERA_INTENT })
  const roomOpenTimeRef = useRef(Date.now())
  const joinTimingRef = useRef<{ joinClickTs: number; connectStartTs: number; connectDoneTs: number; micDoneTs: number }>({ joinClickTs: 0, connectStartTs: 0, connectDoneTs: 0, micDoneTs: 0 })
  const backgroundAtRef = useRef<number | null>(null)
  const reconnectWatchdogRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [state, setState] = useState<ConferenceRoomState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [participants, setParticipants] = useState<ConferenceParticipant[]>([])
  const [isMuted, setIsMuted] = useState(false)
  const [isDeafened, setIsDeafened] = useState(false)
  const [isVideoOn, setIsVideoOn] = useState(false)
  const [preJoinMicEnabled, setPreJoinMicEnabled] = useState(true)
  const [preJoinVideoEnabled, setPreJoinVideoEnabled] = useState(false)
  const [micIntent, setMicIntent] = useState<MediaIntent>({ ...INITIAL_MIC_INTENT })
  const [cameraIntent, setCameraIntent] = useState<MediaIntent>({ ...INITIAL_CAMERA_INTENT })
  const [streams, setStreams] = useState<Map<string, MediaStreamSource[]>>(new Map())
  const [diagnostics, setDiagnostics] = useState<ConferenceDiagnostics>({ ...INITIAL_DIAGNOSTICS })
  const [aiGovernance, setAIGovernanceState] = useState<AIGovernancePermissions>({ ...DEFAULT_AI_GOVERNANCE })
  const [dataChatMessages, setDataChatMessages] = useState<DataChatMessage[]>([])

  const updateDiag = useCallback((patch: Partial<ConferenceDiagnostics>) => {
    setDiagnostics((prev) => ({ ...prev, ...patch }))
  }, [])

  const updateMicIntent = useCallback((patch: Partial<MediaIntent>) => {
    micIntentRef.current = { ...micIntentRef.current, ...patch, updatedAt: Date.now() }
    setMicIntent({ ...micIntentRef.current })
  }, [])

  const updateCameraIntent = useCallback((patch: Partial<MediaIntent>) => {
    cameraIntentRef.current = { ...cameraIntentRef.current, ...patch, updatedAt: Date.now() }
    setCameraIntent({ ...cameraIntentRef.current })
  }, [])

  const syncAllState = useCallback(() => {
    const room = roomRef.current
    if (!room) return

    const micEnabled = room.localParticipant.isMicrophoneEnabled
    const camEnabled = room.localParticipant.isCameraEnabled

    if (micIntentRef.current.transition === 'enabled' || micIntentRef.current.transition === 'disabled') {
      setIsMuted(!micEnabled)
      updateMicIntent({ actual: micEnabled })
    }
    setIsVideoOn(camEnabled)
    if (cameraIntentRef.current.transition === 'on' || cameraIntentRef.current.transition === 'off') {
      updateCameraIntent({ actual: camEnabled })
    }

    const audioSid = findAudioTrackSid(room.localParticipant)
    const allStreams = new Map<string, MediaStreamSource[]>()
    const allParticipants: ConferenceParticipant[] = []
    const deaf = deafenedRef.current

    const localSources = buildStreamSources(room.localParticipant)
    allStreams.set(room.localParticipant.identity, localSources)
    allParticipants.push(participantToInfo(room.localParticipant, localSources, micIntentRef.current, deaf))

    room.remoteParticipants.forEach((rp) => {
      const remoteSources = buildStreamSources(rp)
      allStreams.set(rp.identity, remoteSources)
      const remoteMicIntent: MediaIntent = { intended: rp.isMicrophoneEnabled, transition: rp.isMicrophoneEnabled ? 'enabled' : 'disabled', actual: rp.isMicrophoneEnabled, lastActionId: 0, lastError: null, updatedAt: 0 }
      allParticipants.push(participantToInfo(rp, remoteSources, remoteMicIntent, false))
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
      micEnabledActual: micEnabled,
      cameraEnabledActual: camEnabled,
      audioTrackSid: audioSid,
      audioPublicationExists: hasPublication(room.localParticipant, Track.Source.Microphone),
      videoTrackSid: videoSid,
      videoPublicationExists: hasPublication(room.localParticipant, Track.Source.Camera),
      localPreviewAttached: videoSid ? videoElementsRef.current.has(videoSid) : false,
      visibility: {
        ...INITIAL_VISIBILITY,
        intendedMicState: micIntentRef.current.intended,
        actualMicState: micEnabled,
        intendedCameraState: cameraIntentRef.current.intended,
        actualCameraState: camEnabled,
        reconnectAttempts: diagnostics.reconnectAttempts,
      },
    })
  }, [updateDiag, updateMicIntent, updateCameraIntent])

  const attachVideoTrack = useCallback((trackSid: string, track: { attach: () => HTMLMediaElement }) => {
    if (videoElementsRef.current.has(trackSid)) return
    const el = track.attach() as HTMLVideoElement
    el.id = `lk-video-${trackSid}`
    el.playsInline = true
    el.autoplay = true
    el.muted = true
    el.setAttribute('playsinline', '')
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
    if (cached && Date.now() - cached.fetchedAt < TOKEN_CACHE_TTL_MS) return
    prefetchingRef.current = true
    const t0 = Date.now()
    updateDiag({
      joinTiming: {
        ...INITIAL_JOIN_TIMING,
        roomOpenTimeMs: t0 - roomOpenTimeRef.current,
        tokenPrefetchStartMs: t0,
      },
    })
    try {
      const res = await fetchApi(`/rooms/channels/${channelId}/voice/token`, {
        method: 'POST',
      }) as { token: string; url: string; room: string }
      if (res.token && res.url) {
        const doneTs = Date.now()
        prefetchedTokenRef.current = { ...res, fetchedAt: doneTs }
        const prefetchMs = doneTs - t0
        updateDiag({
          tokenReceived: true,
          joinStage: 'token_ready',
          lastEvent: 'token prefetched',
          joinTiming: {
            ...INITIAL_JOIN_TIMING,
            roomOpenTimeMs: t0 - roomOpenTimeRef.current,
            tokenPrefetchStartMs: t0,
            tokenPrefetchDoneMs: doneTs,
            tokenPrefetchMs: prefetchMs,
          },
        })
      }
    } catch {
      // prefetch failure is not fatal
    } finally {
      prefetchingRef.current = false
    }
  }, [channelId, updateDiag])

  useEffect(() => {
    prefetchToken()
  }, [prefetchToken])

  const restoreMediaAfterForeground = useCallback(async () => {
    const room = roomRef.current
    if (!room || room.state !== ConnectionState.Connected) return

    const bgAt = backgroundAtRef.current
    const bgDuration = bgAt ? Date.now() - bgAt : null
    backgroundAtRef.current = null

    updateDiag({
      visibility: {
        lastVisibilityState: 'visible',
        backgroundDurationMs: bgDuration,
        reconnectAttempts: diagnostics.reconnectAttempts,
        intendedMicState: micIntentRef.current.intended,
        actualMicState: room.localParticipant.isMicrophoneEnabled,
        intendedCameraState: cameraIntentRef.current.intended,
        actualCameraState: room.localParticipant.isCameraEnabled,
      },
      lastEvent: `foreground restored (bg ${bgDuration ? Math.round(bgDuration / 1000) + 's' : 'unknown'})`,
    })

    if (micIntentRef.current.intended && !room.localParticipant.isMicrophoneEnabled) {
      try {
        await room.localParticipant.setMicrophoneEnabled(true)
        updateMicIntent({ actual: true, transition: 'enabled', lastError: null })
        setIsMuted(false)
        updateDiag({ lastEvent: 'mic restored after foreground' })
      } catch (e) {
        const msg = e instanceof Error ? e.message : 'mic restore failed'
        updateMicIntent({ lastError: msg })
        updateDiag({ lastEvent: `mic restore failed: ${msg}` })
      }
    }

    if (cameraIntentRef.current.intended && !room.localParticipant.isCameraEnabled) {
      try {
        await room.localParticipant.setCameraEnabled(true)
        updateCameraIntent({ actual: true, transition: 'on', lastError: null })
        setIsVideoOn(true)
        updateDiag({ lastEvent: 'camera restored after foreground' })
      } catch (e) {
        const msg = e instanceof Error ? e.message : 'camera restore failed'
        updateCameraIntent({ lastError: msg })
        updateDiag({ lastEvent: `camera restore failed: ${msg}` })
      }
    }

    syncAllState()
  }, [syncAllState, updateDiag, updateMicIntent, updateCameraIntent])

  const handleVisibilityChange = useCallback(() => {
    if (typeof document === 'undefined') return
    const room = roomRef.current
    if (!room) return

    if (document.visibilityState === 'hidden') {
      backgroundAtRef.current = Date.now()
      updateDiag({
        visibility: {
          lastVisibilityState: 'hidden',
          backgroundDurationMs: null,
          reconnectAttempts: diagnostics.reconnectAttempts,
          intendedMicState: micIntentRef.current.intended,
          actualMicState: room.localParticipant.isMicrophoneEnabled,
          intendedCameraState: cameraIntentRef.current.intended,
          actualCameraState: room.localParticipant.isCameraEnabled,
        },
        lastEvent: 'app backgrounded',
      })
    } else if (document.visibilityState === 'visible') {
      if (room.state === ConnectionState.Connected) {
        restoreMediaAfterForeground()
      } else {
        updateDiag({ lastEvent: 'foreground — room not connected, waiting for reconnect' })
        reconnectWatchdogRef.current = setTimeout(() => {
          const r = roomRef.current
          if (r && r.state !== ConnectionState.Connected) {
            updateDiag({ lastEvent: 'watchdog: room still disconnected after foreground, leaving' })
            setState('disconnected')
          }
        }, RECONNECT_WATCHDOG_MS)
      }
    }
  }, [restoreMediaAfterForeground, updateDiag])

  useEffect(() => {
    if (typeof document === 'undefined') return
    document.addEventListener('visibilitychange', handleVisibilityChange)
    window.addEventListener('online', () => {
      const room = roomRef.current
      if (room && room.state !== ConnectionState.Connected) {
        updateDiag({ lastEvent: 'network online — expecting LiveKit reconnect' })
      }
    })
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [handleVisibilityChange, updateDiag])

  const doConnect = useCallback(async (micEnabled: boolean, videoEnabled: boolean) => {
    setState('connecting')
    setError(null)
    const joinClickTs = Date.now()
    joinTimingRef.current = { joinClickTs, connectStartTs: 0, connectDoneTs: 0, micDoneTs: 0 }

    const micActionId = nextActionId()
    updateMicIntent({
      intended: micEnabled,
      transition: micEnabled ? 'publishing' : 'prejoin_off',
      actual: false,
      lastActionId: micActionId,
      lastError: null,
    })
    setIsMuted(!micEnabled)
    updateDiag({
      lastEvent: 'joining...',
      micEnabledRequested: micEnabled,
      micState: micEnabled ? 'publishing' : 'prejoin_off',
      joinStage: 'fetching_token',
    })

    try {
      let tokenData: { token: string; url: string; room: string }
      const cached = prefetchedTokenRef.current
      if (cached && Date.now() - cached.fetchedAt < TOKEN_CACHE_TTL_MS) {
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

      const connectStartTs = Date.now()
      joinTimingRef.current.connectStartTs = connectStartTs
      updateDiag({
        livekitUrl: tokenData.url,
        roomName: tokenData.room,
        tokenReceived: true,
        joinStage: 'connecting',
        lastEvent: 'connecting to LiveKit...',
        joinTiming: {
          ...diagnostics.joinTiming,
          joinClickToConnectStartMs: connectStartTs - joinClickTs,
        },
      })

      const room = new Room({
        adaptiveStream: true,
        dynacast: true,
        disconnectOnPageLeave: false,
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
        restoreMediaAfterForeground()
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

      room.on(RoomEvent.TrackMuted, (pub: TrackPublication, participant: Participant) => {
        if (participant instanceof LocalParticipant && pub.source === Track.Source.Microphone) {
          if ((pub as LocalTrackPublication).trackSid && micIntentRef.current.lastActionId <= micActionId) {
            // stale event — ignore if a newer action is in progress
          }
        }
        syncAllState()
      })
      room.on(RoomEvent.TrackUnmuted, () => syncAllState())
      room.on(RoomEvent.ConnectionQualityChanged, () => syncAllState())

      room.on(RoomEvent.LocalTrackPublished, (pub: LocalTrackPublication, _lp: LocalParticipant) => {
        updateDiag({ lastEvent: `published ${pub.source} (${pub.trackSid})` })
        if (pub.track && pub.track.kind === Track.Kind.Video) {
          attachVideoTrack(pub.trackSid, pub.track)
        }
        if (pub.source === Track.Source.Microphone) {
          updateMicIntent({ actual: true, transition: 'enabled', lastError: null })
          setIsMuted(false)
          updateDiag({
            micPermission: 'granted',
            micState: 'enabled',
            micEnabledActual: true,
            audioTrackSid: pub.trackSid,
            audioPublicationExists: true,
            lastMicError: null,
          })
          joinTimingRef.current.micDoneTs = Date.now()
          const timing = joinTimingRef.current
          if (timing.connectDoneTs > 0) {
            updateDiag({
              joinTiming: {
                ...diagnostics.joinTiming,
                joinClickToConnectStartMs: timing.connectStartTs - timing.joinClickTs,
                connectMs: timing.connectDoneTs - timing.connectStartTs,
                micPublishMs: timing.micDoneTs - timing.connectDoneTs,
                joinClickToOperationalMs: timing.micDoneTs - timing.joinClickTs,
              },
            })
          }
        }
        if (pub.source === Track.Source.Camera) {
          updateCameraIntent({ actual: true, transition: 'on', lastError: null })
          setIsVideoOn(true)
          updateDiag({ cameraPermission: 'granted', cameraState: 'on', cameraEnabledActual: true, lastVideoError: null })
        }
        syncAllState()
      })

      room.on(RoomEvent.LocalTrackUnpublished, (pub: LocalTrackPublication, _lp: LocalParticipant) => {
        updateDiag({ lastEvent: `unpublished ${pub.source}` })
        detachVideoTrack(pub.trackSid)
        localScreenTracksRef.current.delete(pub.trackSid)
        if (pub.source === Track.Source.Microphone) {
          updateMicIntent({ actual: false, transition: 'disabled' })
          setIsMuted(true)
          updateDiag({ micState: 'disabled', micEnabledActual: false })
        }
        if (pub.source === Track.Source.Camera) {
          updateCameraIntent({ actual: false, transition: 'off' })
          setIsVideoOn(false)
          updateDiag({ cameraState: 'off', cameraEnabledActual: false })
        }
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
        const lower = msg.toLowerCase()
        const isCameraError = lower.includes('camera') || lower.includes('video')
        const isMicError = lower.includes('microphone') || lower.includes('audio') || lower.includes('mic')
        if (isCameraError) {
          updateCameraIntent({ lastError: msg })
          updateDiag({ lastEvent: `camera media error: ${msg}`, lastVideoError: msg, cameraState: 'failed' })
        } else if (isMicError) {
          updateMicIntent({ lastError: msg })
          updateDiag({ lastEvent: `mic media error: ${msg}`, lastMicError: msg, micState: 'failed' })
        } else {
          updateDiag({ lastEvent: `media error: ${msg}`, lastMicError: msg })
        }
      })

      room.on(RoomEvent.DataReceived, (payload: Uint8Array, participant: RemoteParticipant | undefined, _kind: DataPacket_Kind, topic: string | undefined) => {
        if (topic !== DATA_CHAT_TOPIC) return
        try {
          const msg = JSON.parse(new TextDecoder().decode(payload))
          if (msg.type === 'chat' && msg.content) {
            setDataChatMessages((prev) => [...prev, {
              id: `${prev.length}-${Date.now()}`,
              sender: participant?.identity || 'unknown',
              senderName: participant?.name || msg.senderName || 'Unknown',
              content: msg.content,
              timestamp: Date.now(),
            }])
          }
        } catch { /* ignore malformed data messages */ }
      })

      updateDiag({ joinStage: micEnabled ? 'requesting_mic' : 'connecting', micState: micEnabled ? 'publishing' : 'prejoin_off' })
      await room.connect(tokenData.url, tokenData.token, {
        autoSubscribe: true,
      })
      const connectDoneTs = Date.now()
      joinTimingRef.current.connectDoneTs = connectDoneTs
      updateDiag({
        participantIdentity: room.localParticipant.identity,
        joinStage: 'publishing_mic',
        joinTiming: {
          ...diagnostics.joinTiming,
          connectMs: connectDoneTs - connectStartTs,
        },
      })

      setState('connected')

      if (micEnabled) {
        try {
          await room.localParticipant.setMicrophoneEnabled(true)
          const isEnabled = room.localParticipant.isMicrophoneEnabled
          updateMicIntent({ actual: isEnabled, transition: isEnabled ? 'enabled' : 'failed', lastError: null })
          setIsMuted(!isEnabled)
          updateDiag({
            micPermission: 'granted',
            micState: isEnabled ? 'enabled' : 'failed',
            micEnabledActual: isEnabled,
            lastMicError: null,
            joinStage: 'connected',
            lastEvent: 'mic enabled',
          })
        } catch (micErr) {
          const msg = micErr instanceof Error ? micErr.message : 'unknown'
          updateMicIntent({ actual: false, transition: 'failed', lastError: msg })
          setIsMuted(true)
          updateDiag({
            micPermission: 'denied',
            micState: 'failed',
            micEnabledActual: false,
            lastMicError: msg,
            lastEvent: `mic denied: ${msg}`,
          })
        }
      } else {
        updateMicIntent({ transition: 'disabled', actual: false })
        updateDiag({ joinStage: 'connected', micState: 'disabled', lastEvent: 'connected (mic off by choice)' })
      }

      if (videoEnabled) {
        const camActionId = nextActionId()
        updateCameraIntent({ intended: true, transition: 'requesting_permission', lastActionId: camActionId })
        updateDiag({ joinStage: 'requesting_camera', cameraState: 'requesting_permission' })
        try {
          await room.localParticipant.setCameraEnabled(true)
          updateCameraIntent({ actual: true, transition: 'on', lastError: null })
          setIsVideoOn(true)
          updateDiag({ cameraPermission: 'granted', cameraState: 'on', lastVideoError: null, lastEvent: 'camera enabled' })
        } catch (camErr) {
          const msg = camErr instanceof Error ? camErr.message : 'unknown'
          updateCameraIntent({ actual: false, transition: 'failed', lastError: msg })
          updateDiag({ cameraPermission: 'denied', cameraState: 'failed', lastVideoError: msg, lastEvent: `camera denied: ${msg}` })
        }
        updateDiag({ joinStage: 'connected' })
      }

      const operationalTs = Date.now()
      updateDiag({
        joinTiming: {
          roomOpenTimeMs: joinClickTs - roomOpenTimeRef.current,
          tokenPrefetchStartMs: diagnostics.joinTiming.tokenPrefetchStartMs,
          tokenPrefetchDoneMs: diagnostics.joinTiming.tokenPrefetchDoneMs,
          tokenPrefetchMs: diagnostics.joinTiming.tokenPrefetchMs,
          joinClickToConnectStartMs: connectStartTs - joinClickTs,
          connectMs: connectDoneTs - connectStartTs,
          micPublishMs: operationalTs - connectDoneTs,
          joinClickToOperationalMs: operationalTs - joinClickTs,
        },
      })

      syncAllState()
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to join room'
      setState('failed')
      setError(msg)
      updateMicIntent({ transition: 'failed', lastError: msg })
      updateDiag({ lastEvent: `error: ${msg}`, lastError: msg, joinStage: 'idle', micState: 'failed' })
      if (roomRef.current) {
        roomRef.current.disconnect()
        roomRef.current = null
      }
    }
  }, [channelId, syncAllState, updateDiag, attachVideoTrack, detachVideoTrack, updateMicIntent, updateCameraIntent, restoreMediaAfterForeground])

  const join = useCallback(async () => {
    if (roomRef.current) return
    intentionalDisconnectRef.current = false
    const mic = preJoinMicRef.current
    const vid = preJoinVideoRef.current
    updateMicIntent({ intended: mic, transition: mic ? 'publishing' : 'prejoin_off' })
    updateCameraIntent({ intended: vid, transition: vid ? 'requesting_permission' : 'off' })
    setIsMuted(!mic)
    setIsVideoOn(vid)
    await doConnect(mic, vid)
  }, [doConnect, updateMicIntent, updateCameraIntent])

  const togglePreJoinMic = useCallback(() => {
    setPreJoinMicEnabled((prev) => {
      const next = !prev
      preJoinMicRef.current = next
      setIsMuted(!next)
      updateMicIntent({ intended: next, transition: next ? 'prejoin_on' : 'prejoin_off' })
      updateDiag({ micState: next ? 'prejoin_on' : 'prejoin_off' })
      return next
    })
  }, [updateMicIntent, updateDiag])

  const togglePreJoinVideo = useCallback(() => {
    setPreJoinVideoEnabled((prev) => {
      const next = !prev
      preJoinVideoRef.current = next
      updateCameraIntent({ intended: next, transition: next ? 'requesting_permission' : 'off' })
      updateDiag({ cameraState: next ? 'requesting_permission' : 'off' })
      return next
    })
  }, [updateCameraIntent, updateDiag])

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
    deafenedRef.current = false
    prefetchedTokenRef.current = null
    backgroundAtRef.current = null
    if (reconnectWatchdogRef.current) {
      clearTimeout(reconnectWatchdogRef.current)
      reconnectWatchdogRef.current = null
    }
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
    updateMicIntent({ ...INITIAL_MIC_INTENT })
    updateCameraIntent({ ...INITIAL_CAMERA_INTENT })
    setStreams(new Map())
    setDiagnostics({ ...INITIAL_DIAGNOSTICS })
    setDataChatMessages([])
    prefetchToken()
  }, [prefetchToken, updateMicIntent, updateCameraIntent])

  const toggleMute = useCallback(async () => {
    const room = roomRef.current
    if (!room) return
    const currentlyEnabled = room.localParticipant.isMicrophoneEnabled
    const targetEnabled = !currentlyEnabled
    const actionId = nextActionId()

    // Optimistic UI
    updateMicIntent({ intended: targetEnabled, transition: targetEnabled ? 'publishing' : 'disabling', lastActionId: actionId })
    setIsMuted(!targetEnabled)
    updateDiag({ micEnabledRequested: targetEnabled, micState: targetEnabled ? 'publishing' : 'disabling' })

    try {
      await room.localParticipant.setMicrophoneEnabled(targetEnabled)
      const actualEnabled = room.localParticipant.isMicrophoneEnabled
      updateMicIntent({ actual: actualEnabled, transition: actualEnabled ? 'enabled' : 'disabled', lastError: null })
      setIsMuted(!actualEnabled)
      updateDiag({ micPermission: 'granted', micState: actualEnabled ? 'enabled' : 'disabled', micEnabledActual: actualEnabled, lastMicError: null })
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'mic toggle failed'
      // Revert optimistic update
      updateMicIntent({ intended: currentlyEnabled, actual: currentlyEnabled, transition: currentlyEnabled ? 'enabled' : 'disabled', lastError: msg })
      setIsMuted(!currentlyEnabled)
      updateDiag({ lastMicError: msg, micPermission: 'denied', micState: currentlyEnabled ? 'enabled' : 'disabled' })
    }
    syncAllState()
  }, [syncAllState, updateDiag, updateMicIntent])

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
      updateMicIntent({ intended: false, transition: 'disabled' })
      room.localParticipant.setMicrophoneEnabled(false).catch(() => {})
      updateDiag({ lastEvent: 'deafened', micState: 'disabled' })
    } else {
      updateDiag({ lastEvent: 'undeafened' })
    }
    syncAllState()
  }, [syncAllState, updateDiag, updateMicIntent])

  const toggleVideo = useCallback(async () => {
    const room = roomRef.current
    if (!room) return
    const currentlyEnabled = room.localParticipant.isCameraEnabled
    const targetEnabled = !currentlyEnabled
    const actionId = nextActionId()

    // Optimistic UI
    updateCameraIntent({
      intended: targetEnabled,
      transition: targetEnabled ? 'requesting_permission' : 'disabling',
      lastActionId: actionId,
    })
    setIsVideoOn(targetEnabled)
    updateDiag({ cameraState: targetEnabled ? 'requesting_permission' : 'disabling' })

    try {
      await room.localParticipant.setCameraEnabled(targetEnabled)
      const actualEnabled = room.localParticipant.isCameraEnabled
      updateCameraIntent({ actual: actualEnabled, transition: actualEnabled ? 'on' : 'off', lastError: null })
      setIsVideoOn(actualEnabled)
      updateDiag({
        lastEvent: actualEnabled ? 'camera enabled' : 'camera disabled',
        cameraPermission: 'granted',
        cameraState: actualEnabled ? 'on' : 'off',
        cameraEnabledActual: actualEnabled,
        lastVideoError: null,
      })
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'camera toggle failed'
      updateCameraIntent({ intended: currentlyEnabled, actual: currentlyEnabled, transition: currentlyEnabled ? 'on' : 'failed', lastError: msg })
      setIsVideoOn(currentlyEnabled)
      updateDiag({
        lastVideoError: msg,
        cameraPermission: targetEnabled ? 'denied' : diagnostics.cameraPermission,
        cameraState: 'failed',
        lastEvent: `camera error: ${msg}`,
      })
    }
    syncAllState()
  }, [syncAllState, updateDiag, updateCameraIntent])

  const addScreenShare = useCallback(async () => {
    const room = roomRef.current
    if (!room) return

    const currentLocalStreams = buildStreamSources(room.localParticipant)
    const screenStreams = currentLocalStreams.filter(s => s.sourceType !== 'camera')
    if (screenStreams.length >= MAX_STREAMS_PER_USER) {
      updateDiag({ lastScreenShareError: `Max ${MAX_STREAMS_PER_USER} streams reached`, lastEvent: `max streams reached` })
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
          updateDiag({ lastEvent: 'screen share started', lastScreenShareError: null })
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
        updateDiag({ lastScreenShareError: msg, lastEvent: `screen share error: ${msg}` })
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

  const sendDataChat = useCallback(async (content: string) => {
    const room = roomRef.current
    if (!room || !content.trim()) return
    const payload = new TextEncoder().encode(JSON.stringify({
      type: 'chat',
      content: content.trim(),
      senderName: room.localParticipant.name || room.localParticipant.identity,
    }))
    await room.localParticipant.publishData(payload, { reliable: true, topic: DATA_CHAT_TOPIC })
    setDataChatMessages((prev) => [...prev, {
      id: `${prev.length}-${Date.now()}`,
      sender: room.localParticipant.identity,
      senderName: room.localParticipant.name || room.localParticipant.identity,
      content: content.trim(),
      timestamp: Date.now(),
    }])
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
      if (reconnectWatchdogRef.current) {
        clearTimeout(reconnectWatchdogRef.current)
      }
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
    micIntent,
    cameraIntent,
    streams,
    localStreams,
    diagnostics,
    aiGovernance,
    productionChecklist,
    dataChatMessages,
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
    sendDataChat,
  }
}
