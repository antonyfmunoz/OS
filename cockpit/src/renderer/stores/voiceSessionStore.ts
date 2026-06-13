import { create } from 'zustand'
import {
  Room,
  RoomEvent,
  Track,
  ConnectionState,
  RemoteParticipant,
  Participant,
  RemoteTrackPublication,
  LocalTrackPublication,
  DisconnectReason,
  LocalParticipant,
  createLocalScreenTracks,
  LocalVideoTrack,
  DataPacket_Kind,
  type TrackPublication,
} from 'livekit-client'
import { fetchApi } from '../api/client'
import { useCockpitStore } from './cockpitStore'
import type {
  ConferenceRoomState,
  ConferenceParticipant,
  MediaStreamSource,
  ConferenceDiagnostics,
  MediaIntent,
  AIGovernancePermissions,
  DataChatMessage,
  StreamSourceType,
  MicState,
  CameraState,
  JoinTiming,
  VisibilityDiagnostics,
} from '../hooks/useConferenceRoom'
import {
  DEFAULT_AI_GOVERNANCE,
  detectScreenShareSupport,
} from '../hooks/useConferenceRoom'

const MAX_STREAMS_PER_USER = 4
const MAX_RECONNECT_ATTEMPTS = 5
const INITIAL_BACKOFF_MS = 1000
const TOKEN_CACHE_TTL_MS = 25000
const RECONNECT_WATCHDOG_MS = 3000
const DATA_CHAT_TOPIC = 'umh-chat'

let actionIdCounter = 0
function nextActionId(): number { return ++actionIdCounter }

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

/* ─── Pure helpers (duplicated from useConferenceRoom to avoid circular deps) ─── */

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
    const transitioning = micIntent.transition === 'publishing'
      || micIntent.transition === 'disabling'
      || micIntent.transition === 'prejoin_on'
      || micIntent.transition === 'prejoin_off'
    isMuted = transitioning ? !micIntent.intended : !micIntent.actual
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
    if (pub.source === Track.Source.Microphone && pub.track) return pub.trackSid
  }
  return null
}

function findVideoTrackSid(p: LocalParticipant): string | null {
  for (const pub of p.trackPublications.values()) {
    if (pub.source === Track.Source.Camera && pub.track) return pub.trackSid
  }
  return null
}

function hasPublication(p: LocalParticipant, source: Track.Source): boolean {
  for (const pub of p.trackPublications.values()) {
    if (pub.source === source) return true
  }
  return false
}

/* ─── Store interface ─── */

interface VoiceSessionState {
  activeChannelId: string | null
  state: ConferenceRoomState
  error: string | null
  participants: ConferenceParticipant[]
  streams: Map<string, MediaStreamSource[]>
  isMuted: boolean
  isDeafened: boolean
  isVideoOn: boolean
  preJoinMicEnabled: boolean
  preJoinVideoEnabled: boolean
  micIntent: MediaIntent
  cameraIntent: MediaIntent
  diagnostics: ConferenceDiagnostics
  aiGovernance: AIGovernancePermissions
  dataChatMessages: DataChatMessage[]

  connect: (channelId: string, micEnabled: boolean, videoEnabled: boolean) => Promise<void>
  disconnect: () => void
  toggleMute: () => Promise<void>
  toggleDeafen: () => void
  toggleVideo: () => Promise<void>
  addScreenShare: () => Promise<void>
  stopStream: (trackSid: string) => Promise<void>
  stopAllStreams: () => Promise<void>
  setPreJoinMic: (enabled: boolean) => void
  setPreJoinVideo: (enabled: boolean) => void
  setAIGovernance: (patch: Partial<AIGovernancePermissions>) => void
  sendDataChat: (content: string) => Promise<void>
  getVideoElement: (trackSid: string) => HTMLVideoElement | null
  prefetchToken: (channelId: string) => Promise<void>
}

/* ─── Non-reactive refs (outside Zustand to avoid re-renders on mutation) ─── */

let _room: Room | null = null
let _intentionalDisconnect = false
const _videoElements = new Map<string, HTMLVideoElement>()
const _localScreenTracks = new Map<string, LocalVideoTrack>()
let _prefetchedToken: { token: string; url: string; room: string; fetchedAt: number; channelId: string } | null = null
let _prefetching = false
let _roomOpenTime = Date.now()
let _joinTiming = { joinClickTs: 0, connectStartTs: 0, connectDoneTs: 0, micDoneTs: 0 }
let _backgroundAt: number | null = null
let _reconnectWatchdog: ReturnType<typeof setTimeout> | null = null
let _micIntentRef: MediaIntent = { ...INITIAL_MIC_INTENT }
let _cameraIntentRef: MediaIntent = { ...INITIAL_CAMERA_INTENT }
let _deafenedRef = false
let _diagnosticsRef: ConferenceDiagnostics = { ...INITIAL_DIAGNOSTICS }

/* ─── Internal helpers ─── */

function updateVoiceStatus(state: ConferenceRoomState) {
  const status = state === 'connected' ? 'connected'
    : (state === 'connecting' || state === 'reconnecting') ? 'connecting'
    : 'disconnected'
  useCockpitStore.getState().setVoiceStatus(status)
}

function attachVideoTrack(trackSid: string, track: { attach: () => HTMLMediaElement }) {
  if (_videoElements.has(trackSid)) return
  const el = track.attach() as HTMLVideoElement
  el.id = `lk-video-${trackSid}`
  el.playsInline = true
  el.autoplay = true
  el.muted = true
  el.setAttribute('playsinline', '')
  el.style.display = 'none'
  el.style.position = 'absolute'
  document.body.appendChild(el)
  _videoElements.set(trackSid, el)
}

function detachVideoTrack(trackSid: string) {
  const el = _videoElements.get(trackSid)
  if (el) {
    el.remove()
    _videoElements.delete(trackSid)
  }
}

function syncAllState() {
  const room = _room
  if (!room) return

  const s = useVoiceSessionStore.getState()
  const micEnabled = room.localParticipant.isMicrophoneEnabled
  const camEnabled = room.localParticipant.isCameraEnabled

  const micTransitioning = _micIntentRef.transition === 'publishing'
    || _micIntentRef.transition === 'disabling'
  const camTransitioning = _cameraIntentRef.transition === 'requesting_permission'
    || _cameraIntentRef.transition === 'disabling'
    || _cameraIntentRef.transition === 'publishing'

  const audioSid = findAudioTrackSid(room.localParticipant)
  const allStreams = new Map<string, MediaStreamSource[]>()
  const allParticipants: ConferenceParticipant[] = []
  const deaf = _deafenedRef

  const localSources = buildStreamSources(room.localParticipant)
  allStreams.set(room.localParticipant.identity, localSources)
  allParticipants.push(participantToInfo(room.localParticipant, localSources, _micIntentRef, deaf))

  room.remoteParticipants.forEach((rp) => {
    const remoteSources = buildStreamSources(rp)
    allStreams.set(rp.identity, remoteSources)
    const remoteMicIntent: MediaIntent = {
      intended: rp.isMicrophoneEnabled,
      transition: rp.isMicrophoneEnabled ? 'enabled' : 'disabled',
      actual: rp.isMicrophoneEnabled,
      lastActionId: 0,
      lastError: null,
      updatedAt: 0,
    }
    allParticipants.push(participantToInfo(rp, remoteSources, remoteMicIntent, false))
  })

  let publishedCount = 0
  let subscribedCount = 0
  room.localParticipant.trackPublications.forEach(() => publishedCount++)
  room.remoteParticipants.forEach((rp) => {
    rp.trackPublications.forEach((pub) => {
      if (pub.isSubscribed) subscribedCount++
    })
  })
  const videoSid = findVideoTrackSid(room.localParticipant)

  const micPatch = micTransitioning ? {} : { isMuted: !micEnabled }
  const camPatch = camTransitioning ? {} : { isVideoOn: camEnabled }

  if (!micTransitioning) {
    _micIntentRef = { ..._micIntentRef, actual: micEnabled, updatedAt: Date.now() }
  }
  if (!camTransitioning) {
    _cameraIntentRef = { ..._cameraIntentRef, actual: camEnabled, updatedAt: Date.now() }
  }

  const diagPatch: Partial<ConferenceDiagnostics> = {
    publishedTrackCount: publishedCount,
    subscribedTrackCount: subscribedCount,
    micEnabledActual: micEnabled,
    cameraEnabledActual: camEnabled,
    audioTrackSid: audioSid,
    audioPublicationExists: hasPublication(room.localParticipant, Track.Source.Microphone),
    videoTrackSid: videoSid,
    videoPublicationExists: hasPublication(room.localParticipant, Track.Source.Camera),
    localPreviewAttached: videoSid ? _videoElements.has(videoSid) : false,
    visibility: {
      ...INITIAL_VISIBILITY,
      intendedMicState: _micIntentRef.intended,
      actualMicState: micEnabled,
      intendedCameraState: _cameraIntentRef.intended,
      actualCameraState: camEnabled,
      reconnectAttempts: _diagnosticsRef.reconnectAttempts,
    },
  }
  _diagnosticsRef = { ..._diagnosticsRef, ...diagPatch }

  useVoiceSessionStore.setState({
    ...micPatch,
    ...camPatch,
    micIntent: { ..._micIntentRef },
    cameraIntent: { ..._cameraIntentRef },
    participants: allParticipants,
    streams: allStreams,
    diagnostics: { ..._diagnosticsRef },
  })
}

function updateDiag(patch: Partial<ConferenceDiagnostics>) {
  _diagnosticsRef = { ..._diagnosticsRef, ...patch }
  useVoiceSessionStore.setState({ diagnostics: { ..._diagnosticsRef } })
}

function updateMicIntent(patch: Partial<MediaIntent>) {
  _micIntentRef = { ..._micIntentRef, ...patch, updatedAt: Date.now() }
  useVoiceSessionStore.setState({ micIntent: { ..._micIntentRef } })
}

function updateCameraIntent(patch: Partial<MediaIntent>) {
  _cameraIntentRef = { ..._cameraIntentRef, ...patch, updatedAt: Date.now() }
  useVoiceSessionStore.setState({ cameraIntent: { ..._cameraIntentRef } })
}

async function restoreMediaAfterForeground() {
  const room = _room
  if (!room || room.state !== ConnectionState.Connected) return

  const bgAt = _backgroundAt
  const bgDuration = bgAt ? Date.now() - bgAt : null
  _backgroundAt = null

  updateDiag({
    visibility: {
      lastVisibilityState: 'visible',
      backgroundDurationMs: bgDuration,
      reconnectAttempts: _diagnosticsRef.reconnectAttempts,
      intendedMicState: _micIntentRef.intended,
      actualMicState: room.localParticipant.isMicrophoneEnabled,
      intendedCameraState: _cameraIntentRef.intended,
      actualCameraState: room.localParticipant.isCameraEnabled,
    },
    lastEvent: `foreground restored (bg ${bgDuration ? Math.round(bgDuration / 1000) + 's' : 'unknown'})`,
  })

  if (_micIntentRef.intended && !room.localParticipant.isMicrophoneEnabled) {
    try {
      await room.localParticipant.setMicrophoneEnabled(true)
      updateMicIntent({ actual: true, transition: 'enabled', lastError: null })
      useVoiceSessionStore.setState({ isMuted: false })
      updateDiag({ lastEvent: 'mic restored after foreground' })
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'mic restore failed'
      updateMicIntent({ lastError: msg })
      updateDiag({ lastEvent: `mic restore failed: ${msg}` })
    }
  }

  if (_cameraIntentRef.intended && !room.localParticipant.isCameraEnabled) {
    try {
      await room.localParticipant.setCameraEnabled(true)
      updateCameraIntent({ actual: true, transition: 'on', lastError: null })
      useVoiceSessionStore.setState({ isVideoOn: true })
      updateDiag({ lastEvent: 'camera restored after foreground' })
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'camera restore failed'
      updateCameraIntent({ lastError: msg })
      updateDiag({ lastEvent: `camera restore failed: ${msg}` })
    }
  }

  syncAllState()
}

async function fetchChatHistory(channelId: string) {
  try {
    const msgs = await fetchApi<Array<{ id: string; sender_identity: string; sender_display_name: string; body: string; created_at: string }>>(`/rooms/channels/${channelId}/room-chat`)
    if (Array.isArray(msgs)) {
      useVoiceSessionStore.setState({
        dataChatMessages: msgs.map(m => ({
          id: m.id,
          sender: m.sender_identity,
          senderName: m.sender_display_name,
          content: m.body,
          timestamp: new Date(m.created_at).getTime(),
        })),
      })
    }
  } catch { /* non-fatal */ }
}

/* ─── Visibility and online listeners (registered once at module scope) ─── */

if (typeof document !== 'undefined') {
  document.addEventListener('visibilitychange', () => {
    if (!_room) return
    if (document.visibilityState === 'hidden') {
      _backgroundAt = Date.now()
      updateDiag({
        visibility: {
          lastVisibilityState: 'hidden',
          backgroundDurationMs: null,
          reconnectAttempts: _diagnosticsRef.reconnectAttempts,
          intendedMicState: _micIntentRef.intended,
          actualMicState: _room.localParticipant.isMicrophoneEnabled,
          intendedCameraState: _cameraIntentRef.intended,
          actualCameraState: _room.localParticipant.isCameraEnabled,
        },
        lastEvent: 'app backgrounded',
      })
    } else if (document.visibilityState === 'visible') {
      if (_room.state === ConnectionState.Connected) {
        restoreMediaAfterForeground()
      } else {
        updateDiag({ lastEvent: 'foreground — room not connected, waiting for reconnect' })
        _reconnectWatchdog = setTimeout(() => {
          if (_room && _room.state !== ConnectionState.Connected) {
            updateDiag({ lastEvent: 'watchdog: room still disconnected after foreground, leaving' })
            useVoiceSessionStore.setState({ state: 'disconnected' })
            updateVoiceStatus('disconnected')
          }
        }, RECONNECT_WATCHDOG_MS)
      }
    }
  })

  window.addEventListener('online', () => {
    if (_room && _room.state !== ConnectionState.Connected) {
      updateDiag({ lastEvent: 'network online — expecting LiveKit reconnect' })
    }
  })

  window.addEventListener('beforeunload', () => {
    if (_room) {
      _intentionalDisconnect = true
      _room.disconnect()
      _room = null
    }
  })
}

/* ─── Store ─── */

export const useVoiceSessionStore = create<VoiceSessionState>((set, get) => ({
  activeChannelId: null,
  state: 'idle',
  error: null,
  participants: [],
  streams: new Map(),
  isMuted: false,
  isDeafened: false,
  isVideoOn: false,
  preJoinMicEnabled: true,
  preJoinVideoEnabled: false,
  micIntent: { ...INITIAL_MIC_INTENT },
  cameraIntent: { ...INITIAL_CAMERA_INTENT },
  diagnostics: { ...INITIAL_DIAGNOSTICS },
  aiGovernance: { ...DEFAULT_AI_GOVERNANCE },
  dataChatMessages: [],

  connect: async (channelId, micEnabled, videoEnabled) => {
    if (_room) {
      get().disconnect()
    }

    _intentionalDisconnect = false
    _roomOpenTime = Date.now()

    set({
      activeChannelId: channelId,
      state: 'connecting',
      error: null,
    })
    updateVoiceStatus('connecting')

    const joinClickTs = Date.now()
    _joinTiming = { joinClickTs, connectStartTs: 0, connectDoneTs: 0, micDoneTs: 0 }

    const micActionId = nextActionId()
    updateMicIntent({
      intended: micEnabled,
      transition: micEnabled ? 'publishing' : 'prejoin_off',
      actual: false,
      lastActionId: micActionId,
      lastError: null,
    })
    set({ isMuted: !micEnabled })
    updateDiag({
      lastEvent: 'joining...',
      micEnabledRequested: micEnabled,
      micState: micEnabled ? 'publishing' : 'prejoin_off',
      joinStage: 'fetching_token',
    })

    try {
      let tokenData: { token: string; url: string; room: string }
      if (_prefetchedToken && _prefetchedToken.channelId === channelId && Date.now() - _prefetchedToken.fetchedAt < TOKEN_CACHE_TTL_MS) {
        tokenData = _prefetchedToken
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
      _prefetchedToken = null

      const connectStartTs = Date.now()
      _joinTiming.connectStartTs = connectStartTs
      updateDiag({
        livekitUrl: tokenData.url,
        roomName: tokenData.room,
        tokenReceived: true,
        joinStage: 'connecting',
        lastEvent: 'connecting to LiveKit...',
        joinTiming: {
          ..._diagnosticsRef.joinTiming,
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
      _room = room

      /* ── Room event handlers ── */

      room.on(RoomEvent.SignalConnected, () => {
        updateDiag({ signalConnected: true, lastEvent: 'signal connected' })
      })

      room.on(RoomEvent.ConnectionStateChanged, (connectionState: ConnectionState) => {
        updateDiag({ lastEvent: `connection: ${connectionState}` })
        switch (connectionState) {
          case ConnectionState.Connected:
            set({ state: 'connected' })
            updateVoiceStatus('connected')
            updateDiag({ reconnectAttempts: 0, joinStage: 'connected' })
            syncAllState()
            break
          case ConnectionState.Reconnecting:
            set({ state: 'reconnecting' })
            updateVoiceStatus('reconnecting')
            break
          case ConnectionState.Disconnected:
            if (!_intentionalDisconnect) {
              set({ state: 'disconnected' })
              updateVoiceStatus('disconnected')
              updateDiag({ signalConnected: false, lastEvent: 'disconnected unexpectedly' })
            }
            break
        }
      })

      room.on(RoomEvent.Reconnected, () => {
        set({ state: 'connected' })
        updateVoiceStatus('connected')
        updateDiag({ reconnectAttempts: 0, signalConnected: true, lastEvent: 'reconnected successfully' })
        restoreMediaAfterForeground()
        fetchChatHistory(channelId)
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
        if (participant instanceof LocalParticipant) {
          if (pub.source === Track.Source.Microphone && (_micIntentRef.transition === 'publishing' || _micIntentRef.transition === 'disabling')) return
          if (pub.source === Track.Source.Camera && (_cameraIntentRef.transition === 'requesting_permission' || _cameraIntentRef.transition === 'disabling')) return
        }
        syncAllState()
      })

      room.on(RoomEvent.TrackUnmuted, (_pub: TrackPublication, participant: Participant) => {
        if (participant instanceof LocalParticipant) {
          if (_micIntentRef.transition === 'publishing' || _micIntentRef.transition === 'disabling') return
        }
        syncAllState()
      })

      room.on(RoomEvent.ConnectionQualityChanged, () => syncAllState())

      room.on(RoomEvent.LocalTrackPublished, (pub: LocalTrackPublication, _lp: LocalParticipant) => {
        updateDiag({ lastEvent: `published ${pub.source} (${pub.trackSid})` })
        if (pub.track && pub.track.kind === Track.Kind.Video) {
          attachVideoTrack(pub.trackSid, pub.track)
        }
        if (pub.source === Track.Source.Microphone) {
          updateMicIntent({ actual: true, transition: 'enabled', lastError: null })
          set({ isMuted: false })
          updateDiag({
            micPermission: 'granted',
            micState: 'enabled',
            micEnabledActual: true,
            audioTrackSid: pub.trackSid,
            audioPublicationExists: true,
            lastMicError: null,
          })
          _joinTiming.micDoneTs = Date.now()
          if (_joinTiming.connectDoneTs > 0) {
            updateDiag({
              joinTiming: {
                ..._diagnosticsRef.joinTiming,
                joinClickToConnectStartMs: _joinTiming.connectStartTs - _joinTiming.joinClickTs,
                connectMs: _joinTiming.connectDoneTs - _joinTiming.connectStartTs,
                micPublishMs: _joinTiming.micDoneTs - _joinTiming.connectDoneTs,
                joinClickToOperationalMs: _joinTiming.micDoneTs - _joinTiming.joinClickTs,
              },
            })
          }
        }
        if (pub.source === Track.Source.Camera) {
          updateCameraIntent({ actual: true, transition: 'on', lastError: null })
          set({ isVideoOn: true })
          updateDiag({ cameraPermission: 'granted', cameraState: 'on', cameraEnabledActual: true, lastVideoError: null })
        }
        syncAllState()
      })

      room.on(RoomEvent.LocalTrackUnpublished, (pub: LocalTrackPublication, _lp: LocalParticipant) => {
        updateDiag({ lastEvent: `unpublished ${pub.source}` })
        detachVideoTrack(pub.trackSid)
        _localScreenTracks.delete(pub.trackSid)
        if (pub.source === Track.Source.Microphone) {
          updateMicIntent({ actual: false, transition: 'disabled' })
          set({ isMuted: true })
          updateDiag({ micState: 'disabled', micEnabledActual: false })
        }
        if (pub.source === Track.Source.Camera) {
          updateCameraIntent({ actual: false, transition: 'off' })
          set({ isVideoOn: false })
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
        if (!_intentionalDisconnect) {
          set({ state: 'disconnected' })
          updateVoiceStatus('disconnected')
        }
        set({ participants: [], streams: new Map() })
        _videoElements.forEach(el => el.remove())
        _videoElements.clear()
        _localScreenTracks.clear()
        _room = null
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
            const senderIdentity = participant?.identity || 'unknown'
            if (senderIdentity === _room?.localParticipant?.identity) return
            const prev = get().dataChatMessages
            const isDup = prev.some(m => m.sender === senderIdentity && m.content === msg.content && Date.now() - m.timestamp < 3000)
            if (!isDup) {
              set({
                dataChatMessages: [...prev, {
                  id: `dc-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                  sender: senderIdentity,
                  senderName: participant?.name || msg.senderName || 'Unknown',
                  content: msg.content,
                  timestamp: Date.now(),
                }],
              })
            }
          }
        } catch { /* ignore malformed */ }
      })

      /* ── Connect with retries ── */

      updateDiag({ joinStage: micEnabled ? 'requesting_mic' : 'connecting', micState: micEnabled ? 'publishing' : 'prejoin_off' })

      const CONNECT_RETRIES = 3
      const CONNECT_BACKOFF = [500, 1000, 2000]
      let connectAttempt = 0
      while (true) {
        try {
          await room.connect(tokenData.url, tokenData.token, { autoSubscribe: true })
          break
        } catch (connectErr) {
          connectAttempt++
          if (connectAttempt >= CONNECT_RETRIES) throw connectErr
          const delay = CONNECT_BACKOFF[connectAttempt - 1] || 2000
          updateDiag({ lastEvent: `connect attempt ${connectAttempt}/${CONNECT_RETRIES} failed, retrying in ${delay}ms...` })
          await new Promise(r => setTimeout(r, delay))
        }
      }

      const connectDoneTs = Date.now()
      _joinTiming.connectDoneTs = connectDoneTs
      updateDiag({
        participantIdentity: room.localParticipant.identity,
        joinStage: 'publishing_mic',
        joinTiming: { ..._diagnosticsRef.joinTiming, connectMs: connectDoneTs - connectStartTs },
      })

      set({ state: 'connected' })
      updateVoiceStatus('connected')
      fetchChatHistory(channelId)

      if (micEnabled) {
        try {
          await room.localParticipant.setMicrophoneEnabled(true)
          const isEnabled = room.localParticipant.isMicrophoneEnabled
          updateMicIntent({ actual: isEnabled, transition: isEnabled ? 'enabled' : 'failed', lastError: null })
          set({ isMuted: !isEnabled })
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
          set({ isMuted: true })
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
          set({ isVideoOn: true })
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
          roomOpenTimeMs: joinClickTs - _roomOpenTime,
          tokenPrefetchStartMs: _diagnosticsRef.joinTiming.tokenPrefetchStartMs,
          tokenPrefetchDoneMs: _diagnosticsRef.joinTiming.tokenPrefetchDoneMs,
          tokenPrefetchMs: _diagnosticsRef.joinTiming.tokenPrefetchMs,
          joinClickToConnectStartMs: connectStartTs - joinClickTs,
          connectMs: connectDoneTs - connectStartTs,
          micPublishMs: operationalTs - connectDoneTs,
          joinClickToOperationalMs: operationalTs - joinClickTs,
        },
      })

      syncAllState()
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to join room'
      set({ state: 'failed', error: msg })
      updateVoiceStatus('disconnected')
      updateMicIntent({ transition: 'failed', lastError: msg })
      updateDiag({ lastEvent: `error: ${msg}`, lastError: msg, joinStage: 'idle', micState: 'failed' })
      if (_room) {
        _room.disconnect()
        _room = null
      }
    }
  },

  disconnect: () => {
    _intentionalDisconnect = true
    if (_room) {
      _localScreenTracks.forEach((track) => track.stop())
      _localScreenTracks.clear()
      _room.localParticipant.setCameraEnabled(false).catch(() => {})
      _room.localParticipant.setMicrophoneEnabled(false).catch(() => {})
      _room.disconnect()
      _room = null
    }
    _videoElements.forEach(el => el.remove())
    _videoElements.clear()
    _deafenedRef = false
    _prefetchedToken = null
    _backgroundAt = null
    if (_reconnectWatchdog) {
      clearTimeout(_reconnectWatchdog)
      _reconnectWatchdog = null
    }
    _micIntentRef = { ...INITIAL_MIC_INTENT }
    _cameraIntentRef = { ...INITIAL_CAMERA_INTENT }
    _diagnosticsRef = { ...INITIAL_DIAGNOSTICS }

    set({
      activeChannelId: null,
      state: 'idle',
      error: null,
      participants: [],
      isMuted: false,
      isDeafened: false,
      isVideoOn: false,
      preJoinMicEnabled: true,
      preJoinVideoEnabled: false,
      micIntent: { ...INITIAL_MIC_INTENT },
      cameraIntent: { ...INITIAL_CAMERA_INTENT },
      streams: new Map(),
      diagnostics: { ...INITIAL_DIAGNOSTICS },
      dataChatMessages: [],
    })
    updateVoiceStatus('disconnected')
  },

  toggleMute: async () => {
    if (!_room) return
    const currentlyEnabled = _room.localParticipant.isMicrophoneEnabled
    const targetEnabled = !currentlyEnabled
    const actionId = nextActionId()

    updateMicIntent({ intended: targetEnabled, transition: targetEnabled ? 'publishing' : 'disabling', lastActionId: actionId })
    set({ isMuted: !targetEnabled })
    updateDiag({ micEnabledRequested: targetEnabled, micState: targetEnabled ? 'publishing' : 'disabling' })

    try {
      await _room.localParticipant.setMicrophoneEnabled(targetEnabled)
      const actualEnabled = _room.localParticipant.isMicrophoneEnabled
      updateMicIntent({ actual: actualEnabled, transition: actualEnabled ? 'enabled' : 'disabled', lastError: null })
      set({ isMuted: !actualEnabled })
      updateDiag({ micPermission: 'granted', micState: actualEnabled ? 'enabled' : 'disabled', micEnabledActual: actualEnabled, lastMicError: null })
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'mic toggle failed'
      updateMicIntent({ intended: currentlyEnabled, actual: currentlyEnabled, transition: currentlyEnabled ? 'enabled' : 'disabled', lastError: msg })
      set({ isMuted: !currentlyEnabled })
      updateDiag({ lastMicError: msg, micPermission: 'denied', micState: currentlyEnabled ? 'enabled' : 'disabled' })
    }
    syncAllState()
  },

  toggleDeafen: () => {
    if (!_room) return
    const next = !_deafenedRef
    _deafenedRef = next
    set({ isDeafened: next })
    _room.remoteParticipants.forEach((rp) => {
      rp.audioTrackPublications.forEach((pub) => {
        if (pub.track) {
          pub.track.mediaStreamTrack.enabled = !next
        }
      })
    })
    if (next) {
      set({ isMuted: true })
      updateMicIntent({ intended: false, transition: 'disabled' })
      _room.localParticipant.setMicrophoneEnabled(false).catch(() => {})
      updateDiag({ lastEvent: 'deafened', micState: 'disabled' })
    } else {
      updateDiag({ lastEvent: 'undeafened' })
    }
    syncAllState()
  },

  toggleVideo: async () => {
    if (!_room) return
    const currentlyEnabled = _room.localParticipant.isCameraEnabled
    const targetEnabled = !currentlyEnabled
    const actionId = nextActionId()

    updateCameraIntent({ intended: targetEnabled, transition: targetEnabled ? 'requesting_permission' : 'disabling', lastActionId: actionId })
    set({ isVideoOn: targetEnabled })
    updateDiag({ cameraState: targetEnabled ? 'requesting_permission' : 'disabling' })

    try {
      await _room.localParticipant.setCameraEnabled(targetEnabled)
      const actualEnabled = _room.localParticipant.isCameraEnabled
      updateCameraIntent({ actual: actualEnabled, transition: actualEnabled ? 'on' : 'off', lastError: null })
      set({ isVideoOn: actualEnabled })
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
      set({ isVideoOn: currentlyEnabled })
      updateDiag({
        lastVideoError: msg,
        cameraPermission: targetEnabled ? 'denied' : _diagnosticsRef.cameraPermission,
        cameraState: 'failed',
        lastEvent: `camera error: ${msg}`,
      })
    }
    syncAllState()
  },

  addScreenShare: async () => {
    if (!_room) return
    const currentLocalStreams = buildStreamSources(_room.localParticipant)
    const screenStreams = currentLocalStreams.filter(s => s.sourceType !== 'camera')
    if (screenStreams.length >= MAX_STREAMS_PER_USER) {
      updateDiag({ lastScreenShareError: `Max ${MAX_STREAMS_PER_USER} streams reached`, lastEvent: 'max streams reached' })
      return
    }
    try {
      const tracks = await createLocalScreenTracks({ audio: true })
      for (const track of tracks) {
        if (track.kind === Track.Kind.Video) {
          const videoTrack = track as LocalVideoTrack
          const pub = await _room!.localParticipant.publishTrack(videoTrack, {
            source: Track.Source.ScreenShare,
            name: `screen-${Date.now()}`,
          })
          if (pub.trackSid) {
            _localScreenTracks.set(pub.trackSid, videoTrack)
          }
          updateDiag({ lastEvent: 'screen share started', lastScreenShareError: null })
        } else if (track.kind === Track.Kind.Audio) {
          await _room!.localParticipant.publishTrack(track, {
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
  },

  stopStream: async (trackSid) => {
    if (!_room) return
    const localTrack = _localScreenTracks.get(trackSid)
    if (localTrack) {
      await _room.localParticipant.unpublishTrack(localTrack)
      localTrack.stop()
      _localScreenTracks.delete(trackSid)
    } else {
      for (const pub of _room.localParticipant.trackPublications.values()) {
        if (pub.trackSid === trackSid && pub.track) {
          await _room.localParticipant.unpublishTrack(pub.track)
          pub.track.stop()
          break
        }
      }
    }
    detachVideoTrack(trackSid)
    updateDiag({ lastEvent: `stopped stream ${trackSid}` })
    syncAllState()
  },

  stopAllStreams: async () => {
    if (!_room) return
    const sids = Array.from(_localScreenTracks.keys())
    for (const sid of sids) {
      const track = _localScreenTracks.get(sid)
      if (track) {
        await _room.localParticipant.unpublishTrack(track)
        track.stop()
      }
      detachVideoTrack(sid)
    }
    _localScreenTracks.clear()
    updateDiag({ lastEvent: 'stopped all local streams' })
    syncAllState()
  },

  setPreJoinMic: (enabled) => {
    set({ preJoinMicEnabled: enabled, isMuted: !enabled })
    updateMicIntent({ intended: enabled, transition: enabled ? 'prejoin_on' : 'prejoin_off' })
    updateDiag({ micState: enabled ? 'prejoin_on' : 'prejoin_off' })
  },

  setPreJoinVideo: (enabled) => {
    set({ preJoinVideoEnabled: enabled })
    updateCameraIntent({ intended: enabled, transition: enabled ? 'requesting_permission' : 'off' })
    updateDiag({ cameraState: enabled ? 'requesting_permission' : 'off' })
  },

  setAIGovernance: (patch) => {
    set((s) => ({ aiGovernance: { ...s.aiGovernance, ...patch } }))
  },

  sendDataChat: async (content) => {
    if (!_room || !content.trim()) return
    const text = content.trim()
    const channelId = get().activeChannelId
    const senderName = _room.localParticipant.name || _room.localParticipant.identity

    const optimisticMsg: DataChatMessage = {
      id: `local-${Date.now()}`,
      sender: _room.localParticipant.identity,
      senderName,
      content: text,
      timestamp: Date.now(),
    }
    set((s) => ({ dataChatMessages: [...s.dataChatMessages, optimisticMsg] }))

    if (channelId) {
      try {
        const saved = await fetchApi<{ id: string }>(`/rooms/channels/${channelId}/room-chat`, {
          method: 'POST',
          body: JSON.stringify({ content: text }),
        })
        set((s) => ({
          dataChatMessages: s.dataChatMessages.map(m => m.id === optimisticMsg.id ? { ...m, id: saved.id } : m),
        }))
      } catch { /* non-fatal */ }
    }

    const payload = new TextEncoder().encode(JSON.stringify({ type: 'chat', content: text, senderName }))
    try {
      await _room.localParticipant.publishData(payload, { reliable: true, topic: DATA_CHAT_TOPIC })
    } catch { /* non-fatal */ }
  },

  getVideoElement: (trackSid) => {
    return _videoElements.get(trackSid) ?? null
  },

  prefetchToken: async (channelId) => {
    if (_prefetching) return
    if (_prefetchedToken && Date.now() - _prefetchedToken.fetchedAt < TOKEN_CACHE_TTL_MS) return
    _prefetching = true
    const t0 = Date.now()
    updateDiag({
      joinTiming: {
        ...INITIAL_JOIN_TIMING,
        roomOpenTimeMs: t0 - _roomOpenTime,
        tokenPrefetchStartMs: t0,
      },
    })
    try {
      const res = await fetchApi(`/rooms/channels/${channelId}/voice/token`, {
        method: 'POST',
      }) as { token: string; url: string; room: string }
      if (res.token && res.url) {
        const doneTs = Date.now()
        _prefetchedToken = { ...res, fetchedAt: doneTs, channelId }
        updateDiag({
          tokenReceived: true,
          joinStage: 'token_ready',
          lastEvent: 'token prefetched',
          joinTiming: {
            ...INITIAL_JOIN_TIMING,
            roomOpenTimeMs: t0 - _roomOpenTime,
            tokenPrefetchStartMs: t0,
            tokenPrefetchDoneMs: doneTs,
            tokenPrefetchMs: doneTs - t0,
          },
        })
      }
    } catch { /* non-fatal */ } finally {
      _prefetching = false
    }
  },
}))
