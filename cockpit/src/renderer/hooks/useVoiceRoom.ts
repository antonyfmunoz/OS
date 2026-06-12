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
  type LocalParticipant,
} from 'livekit-client'
import { fetchApi } from '../api/client'

export interface VoiceParticipant {
  identity: string
  name: string
  isSpeaking: boolean
  isMuted: boolean
  isVideoOn: boolean
  isScreenSharing: boolean
  connectionQuality: ConnectionQuality
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
}

export interface UseVoiceRoomReturn {
  state: VoiceRoomState
  error: string | null
  participants: VoiceParticipant[]
  isMuted: boolean
  isVideoOn: boolean
  isScreenSharing: boolean
  diagnostics: VoiceDiagnostics
  join: () => Promise<void>
  leave: () => void
  toggleMute: () => Promise<void>
  toggleVideo: () => Promise<void>
  toggleScreenShare: () => Promise<void>
}

function getLocalMicEnabled(room: Room): boolean {
  return room.localParticipant.isMicrophoneEnabled
}

function getLocalVideoEnabled(room: Room): boolean {
  return room.localParticipant.isCameraEnabled
}

function getLocalScreenShareEnabled(room: Room): boolean {
  return room.localParticipant.isScreenShareEnabled
}

function participantToInfo(p: Participant): VoiceParticipant {
  const audioTrack = p.getTrackPublications().find(
    (t) => t.track?.kind === Track.Kind.Audio && t.source === Track.Source.Microphone
  )
  const videoTrack = p.getTrackPublications().find(
    (t) => t.track?.kind === Track.Kind.Video && t.source === Track.Source.Camera
  )
  const screenTrack = p.getTrackPublications().find(
    (t) => t.track?.kind === Track.Kind.Video && t.source === Track.Source.ScreenShare
  )
  return {
    identity: p.identity,
    name: p.name || p.identity,
    isSpeaking: p.isSpeaking,
    isMuted: audioTrack ? audioTrack.isMuted : true,
    isVideoOn: videoTrack ? !videoTrack.isMuted : false,
    isScreenSharing: screenTrack ? !screenTrack.isMuted : false,
    connectionQuality: p.connectionQuality,
  }
}

const MAX_RECONNECT_ATTEMPTS = 5
const INITIAL_BACKOFF_MS = 1000

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
}

export function useVoiceRoom(channelId: string): UseVoiceRoomReturn {
  const roomRef = useRef<Room | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const intentionalDisconnectRef = useRef(false)

  const [state, setState] = useState<VoiceRoomState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [participants, setParticipants] = useState<VoiceParticipant[]>([])
  const [isMuted, setIsMuted] = useState(false)
  const [isVideoOn, setIsVideoOn] = useState(false)
  const [isScreenSharing, setIsScreenSharing] = useState(false)
  const [diagnostics, setDiagnostics] = useState<VoiceDiagnostics>({ ...INITIAL_DIAGNOSTICS })

  const updateDiag = useCallback((patch: Partial<VoiceDiagnostics>) => {
    setDiagnostics((prev) => ({ ...prev, ...patch }))
  }, [])

  const syncLocalTrackState = useCallback(() => {
    const room = roomRef.current
    if (!room) return
    setIsMuted(!getLocalMicEnabled(room))
    setIsVideoOn(getLocalVideoEnabled(room))
    setIsScreenSharing(getLocalScreenShareEnabled(room))
  }, [])

  const updateParticipants = useCallback(() => {
    const room = roomRef.current
    if (!room) return
    const all: VoiceParticipant[] = []
    all.push(participantToInfo(room.localParticipant))
    room.remoteParticipants.forEach((p) => {
      all.push(participantToInfo(p))
    })
    setParticipants(all)
    syncLocalTrackState()
  }, [syncLocalTrackState])

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
  }, [])

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
            reconnectAttemptsRef.current = 0
            updateDiag({ reconnectAttempts: 0 })
            updateParticipants()
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
        reconnectAttemptsRef.current = 0
        updateDiag({
          reconnectAttempts: 0,
          signalConnected: true,
          lastEvent: 'reconnected successfully',
        })
        updateParticipants()
      })

      room.on(RoomEvent.ParticipantConnected, (participant: RemoteParticipant) => {
        updateDiag({ lastEvent: `${participant.identity} joined` })
        updateParticipants()
      })
      room.on(RoomEvent.ParticipantDisconnected, (participant: RemoteParticipant) => {
        updateDiag({ lastEvent: `${participant.identity} left` })
        updateParticipants()
      })

      room.on(RoomEvent.ActiveSpeakersChanged, () => updateParticipants())
      room.on(RoomEvent.TrackMuted, () => updateParticipants())
      room.on(RoomEvent.TrackUnmuted, () => updateParticipants())
      room.on(RoomEvent.ConnectionQualityChanged, () => updateParticipants())

      room.on(RoomEvent.LocalTrackPublished, (_pub: LocalTrackPublication, _lp: LocalParticipant) => {
        updateDiag({ lastEvent: `published ${_pub.source}` })
        updateParticipants()
      })
      room.on(RoomEvent.LocalTrackUnpublished, (_pub: LocalTrackPublication, _lp: LocalParticipant) => {
        updateDiag({ lastEvent: `unpublished ${_pub.source}` })
        updateParticipants()
      })

      room.on(RoomEvent.TrackSubscribed, (track, _pub: RemoteTrackPublication, participant: RemoteParticipant) => {
        if (track.kind === Track.Kind.Audio) {
          const el = track.attach()
          el.id = `lk-audio-${participant.identity}`
          document.body.appendChild(el)
        }
        if (track.kind === Track.Kind.Video) {
          updateParticipants()
        }
      })

      room.on(RoomEvent.TrackUnsubscribed, (track) => {
        track.detach().forEach((el) => el.remove())
        updateParticipants()
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
        roomRef.current = null
      })

      room.on(RoomEvent.MediaDevicesError, (e) => {
        const msg = e instanceof Error ? e.message : 'unknown media error'
        updateDiag({
          lastEvent: `media error: ${msg}`,
          lastError: msg,
          micPermission: 'denied',
        })
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
        updateDiag({
          micPermission: 'denied',
          lastEvent: `mic error: ${msg}`,
          lastError: msg,
        })
      }
      syncLocalTrackState()
      updateParticipants()
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
  }, [channelId, updateParticipants, updateDiag, syncLocalTrackState])

  const join = useCallback(async () => {
    if (roomRef.current) return
    intentionalDisconnectRef.current = false
    reconnectAttemptsRef.current = 0
    clearReconnectTimer()
    await doConnect()
  }, [doConnect, clearReconnectTimer])

  const leave = useCallback(() => {
    intentionalDisconnectRef.current = true
    clearReconnectTimer()
    const room = roomRef.current
    if (room) {
      room.localParticipant.setCameraEnabled(false).catch(() => {})
      room.localParticipant.setScreenShareEnabled(false).catch(() => {})
      room.localParticipant.setMicrophoneEnabled(false).catch(() => {})
      room.disconnect()
      roomRef.current = null
    }
    setState('idle')
    setParticipants([])
    setError(null)
    setIsMuted(false)
    setIsVideoOn(false)
    setIsScreenSharing(false)
    setDiagnostics({ ...INITIAL_DIAGNOSTICS })
  }, [clearReconnectTimer])

  const toggleMute = useCallback(async () => {
    const room = roomRef.current
    if (!room) return
    const newEnabled = !getLocalMicEnabled(room)
    try {
      await room.localParticipant.setMicrophoneEnabled(newEnabled)
    } catch (err) {
      updateDiag({
        lastError: err instanceof Error ? err.message : 'mic toggle failed',
        micPermission: 'denied',
      })
    }
    syncLocalTrackState()
    updateParticipants()
  }, [syncLocalTrackState, updateParticipants, updateDiag])

  const toggleVideo = useCallback(async () => {
    const room = roomRef.current
    if (!room) return
    const newEnabled = !getLocalVideoEnabled(room)
    try {
      await room.localParticipant.setCameraEnabled(newEnabled)
      updateDiag({ lastEvent: newEnabled ? 'camera enabled' : 'camera disabled' })
    } catch (err) {
      updateDiag({
        lastError: err instanceof Error ? err.message : 'camera toggle failed',
      })
    }
    syncLocalTrackState()
    updateParticipants()
  }, [syncLocalTrackState, updateParticipants, updateDiag])

  const toggleScreenShare = useCallback(async () => {
    const room = roomRef.current
    if (!room) return
    const newEnabled = !getLocalScreenShareEnabled(room)
    try {
      await room.localParticipant.setScreenShareEnabled(newEnabled)
      updateDiag({ lastEvent: newEnabled ? 'screen share started' : 'screen share stopped' })
    } catch (err) {
      updateDiag({
        lastError: err instanceof Error ? err.message : 'screen share failed',
      })
    }
    syncLocalTrackState()
    updateParticipants()
  }, [syncLocalTrackState, updateParticipants, updateDiag])

  useEffect(() => {
    return () => {
      intentionalDisconnectRef.current = true
      clearReconnectTimer()
      if (roomRef.current) {
        roomRef.current.disconnect()
        roomRef.current = null
      }
    }
  }, [clearReconnectTimer])

  return {
    state,
    error,
    participants,
    isMuted,
    isVideoOn,
    isScreenSharing,
    diagnostics,
    join,
    leave,
    toggleMute,
    toggleVideo,
    toggleScreenShare,
  }
}
