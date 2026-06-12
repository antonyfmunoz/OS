import { useConferenceRoom } from './useConferenceRoom'
import type {
  ConferenceParticipant,
  ConferenceRoomState,
  ConferenceDiagnostics,
  MediaStreamSource,
  StreamSourceType,
  UseConferenceRoomReturn,
} from './useConferenceRoom'

export type { StreamSourceType, MediaStreamSource }

export type VoiceParticipant = ConferenceParticipant
export type VoiceRoomState = ConferenceRoomState
export type VoiceDiagnostics = ConferenceDiagnostics

export interface UseVoiceRoomReturn {
  state: VoiceRoomState
  error: string | null
  participants: VoiceParticipant[]
  isMuted: boolean
  isDeafened: boolean
  isVideoOn: boolean
  preJoinMicEnabled: boolean
  streams: Map<string, MediaStreamSource[]>
  localStreams: MediaStreamSource[]
  diagnostics: VoiceDiagnostics
  join: () => Promise<void>
  leave: () => void
  toggleMute: () => Promise<void>
  toggleDeafen: () => void
  togglePreJoinMic: () => void
  toggleVideo: () => Promise<void>
  addScreenShare: () => Promise<void>
  stopStream: (trackSid: string) => Promise<void>
  stopAllStreams: () => Promise<void>
  canAddStream: boolean
  getVideoElement: (trackSid: string) => HTMLVideoElement | null
}

export function useVoiceRoom(channelId: string): UseVoiceRoomReturn {
  const conf = useConferenceRoom(channelId)
  return {
    state: conf.state,
    error: conf.error,
    participants: conf.participants,
    isMuted: conf.isMuted,
    isDeafened: conf.isDeafened,
    isVideoOn: conf.isVideoOn,
    preJoinMicEnabled: conf.preJoinMicEnabled,
    streams: conf.streams,
    localStreams: conf.localStreams,
    diagnostics: conf.diagnostics,
    join: conf.join,
    leave: conf.leave,
    toggleMute: conf.toggleMute,
    toggleDeafen: conf.toggleDeafen,
    togglePreJoinMic: conf.togglePreJoinMic,
    toggleVideo: conf.toggleVideo,
    addScreenShare: conf.addScreenShare,
    stopStream: conf.stopStream,
    stopAllStreams: conf.stopAllStreams,
    canAddStream: conf.canAddStream,
    getVideoElement: conf.getVideoElement,
  }
}
