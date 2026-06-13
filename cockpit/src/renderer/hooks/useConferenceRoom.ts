import { useCallback, useEffect, useMemo } from 'react'
import { ConnectionQuality, type TrackPublication } from 'livekit-client'
import { useVoiceSessionStore } from '../stores/voiceSessionStore'

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

export function detectScreenShareSupport(): boolean {
  if (typeof navigator === 'undefined') return false
  const isNativeApp = !!(window as Record<string, unknown>).Capacitor
    || !!(window as Record<string, unknown>).ReactNativeWebView
  if (isNativeApp) return true
  return typeof navigator.mediaDevices?.getDisplayMedia === 'function'
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

/**
 * Thin adapter over voiceSessionStore. All Room lifecycle lives in the store;
 * this hook provides the same UseConferenceRoomReturn interface that all
 * consuming components expect. Panel unmounts no longer disconnect the Room.
 */
export function useConferenceRoom(channelId: string): UseConferenceRoomReturn {
  const store = useVoiceSessionStore()

  useEffect(() => {
    if (store.state === 'idle' || store.activeChannelId !== channelId) {
      store.prefetchToken(channelId)
    }
  }, [channelId]) // eslint-disable-line react-hooks/exhaustive-deps

  const join = useCallback(async () => {
    await store.connect(channelId, store.preJoinMicEnabled, store.preJoinVideoEnabled)
  }, [channelId, store.preJoinMicEnabled, store.preJoinVideoEnabled]) // eslint-disable-line react-hooks/exhaustive-deps

  const togglePreJoinMic = useCallback(() => {
    store.setPreJoinMic(!store.preJoinMicEnabled)
  }, [store.preJoinMicEnabled]) // eslint-disable-line react-hooks/exhaustive-deps

  const togglePreJoinVideo = useCallback(() => {
    store.setPreJoinVideo(!store.preJoinVideoEnabled)
  }, [store.preJoinVideoEnabled]) // eslint-disable-line react-hooks/exhaustive-deps

  const localStreams = useMemo(() => {
    const identity = store.diagnostics.participantIdentity
    if (!identity) return []
    return store.streams.get(identity) ?? []
  }, [store.streams, store.diagnostics.participantIdentity])

  const localScreenCount = localStreams.filter(s => s.sourceType !== 'camera').length
  const canAddStream = store.state === 'connected' && localScreenCount < MAX_STREAMS_PER_USER

  const productionChecklist = useMemo(
    () => buildProductionChecklist(store.state, store.diagnostics),
    [store.state, store.diagnostics],
  )

  return {
    state: store.state,
    error: store.error,
    participants: store.participants,
    isMuted: store.isMuted,
    isDeafened: store.isDeafened,
    isVideoOn: store.isVideoOn,
    preJoinMicEnabled: store.preJoinMicEnabled,
    preJoinVideoEnabled: store.preJoinVideoEnabled,
    micIntent: store.micIntent,
    cameraIntent: store.cameraIntent,
    streams: store.streams,
    localStreams,
    diagnostics: store.diagnostics,
    aiGovernance: store.aiGovernance,
    productionChecklist,
    dataChatMessages: store.dataChatMessages,
    join,
    leave: store.disconnect,
    toggleMute: store.toggleMute,
    toggleDeafen: store.toggleDeafen,
    togglePreJoinMic,
    togglePreJoinVideo,
    toggleVideo: store.toggleVideo,
    addScreenShare: store.addScreenShare,
    stopStream: store.stopStream,
    stopAllStreams: store.stopAllStreams,
    canAddStream,
    getVideoElement: store.getVideoElement,
    setAIGovernance: store.setAIGovernance,
    sendDataChat: store.sendDataChat,
  }
}
