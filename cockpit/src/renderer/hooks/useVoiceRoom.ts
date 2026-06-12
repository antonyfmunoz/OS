import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Room,
  RoomEvent,
  Track,
  ConnectionState,
  RemoteParticipant,
  LocalParticipant,
  Participant,
  RemoteTrackPublication,
  ConnectionQuality,
} from 'livekit-client'
import { fetchApi } from '../api/client'

export interface VoiceParticipant {
  identity: string
  name: string
  isSpeaking: boolean
  isMuted: boolean
  hasVideo: boolean
  hasScreenShare: boolean
  connectionQuality: ConnectionQuality
  videoTrack: Track | null
  screenTrack: Track | null
}

export type VoiceRoomState = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'failed'

export interface MediaDiagnostics {
  micPermission: PermissionState | 'unknown'
  micEnabledRequested: boolean
  micEnabledActual: boolean
  audioTrackSid: string | null
  cameraPermission: PermissionState | 'unknown'
  cameraEnabledActual: boolean
  screenShareSupported: boolean
  lastMediaError: string | null
}

interface UseVoiceRoomReturn {
  state: VoiceRoomState
  error: string | null
  participants: VoiceParticipant[]
  isMuted: boolean
  isCameraOn: boolean
  isScreenSharing: boolean
  preJoinMicEnabled: boolean
  diagnostics: MediaDiagnostics
  screenShareSupported: boolean
  setPreJoinMicEnabled: (enabled: boolean) => void
  join: () => Promise<void>
  leave: () => void
  toggleMute: () => void
  toggleCamera: () => Promise<void>
  toggleScreenShare: () => Promise<void>
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
    isMuted: audioTrack ? audioTrack.isMuted : !p.isMicrophoneEnabled,
    hasVideo: !!videoTrack?.track && !videoTrack.isMuted,
    hasScreenShare: !!screenTrack?.track && !screenTrack.isMuted,
    connectionQuality: p.connectionQuality,
    videoTrack: videoTrack?.track ?? null,
    screenTrack: screenTrack?.track ?? null,
  }
}

const detectScreenShareSupport = (): boolean => {
  if (typeof navigator === 'undefined') return false
  return typeof navigator.mediaDevices?.getDisplayMedia === 'function'
}

export function useVoiceRoom(channelId: string): UseVoiceRoomReturn {
  const roomRef = useRef<Room | null>(null)
  const [state, setState] = useState<VoiceRoomState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [participants, setParticipants] = useState<VoiceParticipant[]>([])
  const [preJoinMicEnabled, setPreJoinMicEnabled] = useState(true)
  const [diagnostics, setDiagnostics] = useState<MediaDiagnostics>({
    micPermission: 'unknown',
    micEnabledRequested: false,
    micEnabledActual: false,
    audioTrackSid: null,
    cameraPermission: 'unknown',
    cameraEnabledActual: false,
    screenShareSupported: detectScreenShareSupport(),
    lastMediaError: null,
  })

  const screenShareSupported = detectScreenShareSupport()

  const updateParticipants = useCallback(() => {
    const room = roomRef.current
    if (!room) return
    const all: VoiceParticipant[] = []
    all.push(participantToInfo(room.localParticipant))
    room.remoteParticipants.forEach((p) => {
      all.push(participantToInfo(p))
    })
    setParticipants(all)
  }, [])

  const updateDiagnosticsFromRoom = useCallback(() => {
    const room = roomRef.current
    if (!room) return
    const lp = room.localParticipant
    const audioTrack = lp.getTrackPublications().find(
      (t) => t.source === Track.Source.Microphone
    )
    setDiagnostics((prev) => ({
      ...prev,
      micEnabledActual: lp.isMicrophoneEnabled,
      audioTrackSid: audioTrack?.trackSid ?? null,
      cameraEnabledActual: lp.isCameraEnabled,
    }))
  }, [])

  const isMuted = (() => {
    const room = roomRef.current
    if (!room || state !== 'connected') return !preJoinMicEnabled
    return !room.localParticipant.isMicrophoneEnabled
  })()

  const isCameraOn = (() => {
    const room = roomRef.current
    if (!room || state !== 'connected') return false
    return room.localParticipant.isCameraEnabled
  })()

  const isScreenSharing = (() => {
    const room = roomRef.current
    if (!room || state !== 'connected') return false
    return room.localParticipant.isScreenShareEnabled
  })()

  const join = useCallback(async () => {
    if (roomRef.current) return
    setState('connecting')
    setError(null)
    setDiagnostics((prev) => ({ ...prev, micEnabledRequested: preJoinMicEnabled, lastMediaError: null }))

    try {
      // Check mic permission
      try {
        const permResult = await navigator.permissions.query({ name: 'microphone' as PermissionName })
        setDiagnostics((prev) => ({ ...prev, micPermission: permResult.state }))
      } catch {
        setDiagnostics((prev) => ({ ...prev, micPermission: 'unknown' }))
      }

      const res = await fetchApi(`/rooms/channels/${channelId}/voice/token`, {
        method: 'POST',
      }) as { token: string; url: string; room: string }

      if (!res.token || !res.url) {
        throw new Error('No token or URL returned from server')
      }

      const room = new Room({
        adaptiveStream: true,
        dynacast: true,
        disconnectOnPageLeave: true,
      })
      roomRef.current = room

      room.on(RoomEvent.ConnectionStateChanged, (connectionState: ConnectionState) => {
        switch (connectionState) {
          case ConnectionState.Connected:
            setState('connected')
            updateParticipants()
            updateDiagnosticsFromRoom()
            break
          case ConnectionState.Reconnecting:
            setState('reconnecting')
            break
          case ConnectionState.Disconnected:
            setState('idle')
            setParticipants([])
            roomRef.current = null
            break
        }
      })

      room.on(RoomEvent.ParticipantConnected, () => updateParticipants())
      room.on(RoomEvent.ParticipantDisconnected, () => updateParticipants())
      room.on(RoomEvent.ActiveSpeakersChanged, () => updateParticipants())
      room.on(RoomEvent.TrackMuted, () => { updateParticipants(); updateDiagnosticsFromRoom() })
      room.on(RoomEvent.TrackUnmuted, () => { updateParticipants(); updateDiagnosticsFromRoom() })
      room.on(RoomEvent.ConnectionQualityChanged, () => updateParticipants())
      room.on(RoomEvent.LocalTrackPublished, () => { updateParticipants(); updateDiagnosticsFromRoom() })
      room.on(RoomEvent.LocalTrackUnpublished, () => { updateParticipants(); updateDiagnosticsFromRoom() })

      room.on(RoomEvent.TrackSubscribed, (track, _pub: RemoteTrackPublication, _participant: RemoteParticipant) => {
        if (track.kind === Track.Kind.Audio) {
          const el = track.attach()
          el.id = `lk-audio-${_participant.identity}`
          document.body.appendChild(el)
        }
        updateParticipants()
      })

      room.on(RoomEvent.TrackUnsubscribed, (track) => {
        track.detach().forEach((el) => el.remove())
        updateParticipants()
      })

      room.on(RoomEvent.Disconnected, () => {
        setState('idle')
        setParticipants([])
        roomRef.current = null
      })

      await room.connect(res.url, res.token)
      await room.localParticipant.setMicrophoneEnabled(preJoinMicEnabled)
      updateParticipants()
      updateDiagnosticsFromRoom()
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to join voice room'
      setState('failed')
      setError(msg)
      setDiagnostics((prev) => ({ ...prev, lastMediaError: msg }))
      if (roomRef.current) {
        roomRef.current.disconnect()
        roomRef.current = null
      }
    }
  }, [channelId, preJoinMicEnabled, updateParticipants, updateDiagnosticsFromRoom])

  const leave = useCallback(() => {
    const room = roomRef.current
    if (room) {
      room.disconnect()
      roomRef.current = null
    }
    setState('idle')
    setParticipants([])
    setError(null)
    setDiagnostics((prev) => ({
      ...prev,
      micEnabledActual: false,
      micEnabledRequested: false,
      audioTrackSid: null,
      cameraEnabledActual: false,
      lastMediaError: null,
    }))
  }, [])

  const toggleMute = useCallback(() => {
    const room = roomRef.current
    if (!room) return
    const current = room.localParticipant.isMicrophoneEnabled
    room.localParticipant.setMicrophoneEnabled(!current).then(() => {
      updateParticipants()
      updateDiagnosticsFromRoom()
    }).catch((e) => {
      setDiagnostics((prev) => ({
        ...prev,
        lastMediaError: e instanceof Error ? e.message : 'Mute toggle failed',
      }))
    })
  }, [updateParticipants, updateDiagnosticsFromRoom])

  const toggleCamera = useCallback(async () => {
    const room = roomRef.current
    if (!room) return
    try {
      // Check camera permission
      try {
        const permResult = await navigator.permissions.query({ name: 'camera' as PermissionName })
        setDiagnostics((prev) => ({ ...prev, cameraPermission: permResult.state }))
      } catch {
        setDiagnostics((prev) => ({ ...prev, cameraPermission: 'unknown' }))
      }

      const current = room.localParticipant.isCameraEnabled
      await room.localParticipant.setCameraEnabled(!current)
      updateParticipants()
      updateDiagnosticsFromRoom()
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Camera toggle failed'
      setError(msg)
      setDiagnostics((prev) => ({ ...prev, lastMediaError: msg }))
    }
  }, [updateParticipants, updateDiagnosticsFromRoom])

  const toggleScreenShare = useCallback(async () => {
    const room = roomRef.current
    if (!room) return
    if (!screenShareSupported) {
      setError('Screen share unavailable on this browser')
      return
    }
    try {
      const current = room.localParticipant.isScreenShareEnabled
      await room.localParticipant.setScreenShareEnabled(!current)
      updateParticipants()
      updateDiagnosticsFromRoom()
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Screen share failed'
      setError(msg)
      setDiagnostics((prev) => ({ ...prev, lastMediaError: msg }))
    }
  }, [screenShareSupported, updateParticipants, updateDiagnosticsFromRoom])

  useEffect(() => {
    return () => {
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
    isCameraOn,
    isScreenSharing,
    preJoinMicEnabled,
    diagnostics,
    screenShareSupported,
    setPreJoinMicEnabled,
    join,
    leave,
    toggleMute,
    toggleCamera,
    toggleScreenShare,
  }
}
