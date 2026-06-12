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
} from 'livekit-client'
import { fetchApi } from '../api/client'

export interface VoiceParticipant {
  identity: string
  name: string
  isSpeaking: boolean
  isMuted: boolean
  connectionQuality: ConnectionQuality
}

export type VoiceRoomState = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'failed'

export interface VoiceDiagnostics {
  livekitUrl: string | null
  roomName: string | null
  tokenReceived: boolean
  signalConnected: boolean
  micPermission: 'unknown' | 'granted' | 'denied' | 'prompt'
  lastEvent: string | null
}

interface UseVoiceRoomReturn {
  state: VoiceRoomState
  error: string | null
  participants: VoiceParticipant[]
  isMuted: boolean
  diagnostics: VoiceDiagnostics
  join: () => Promise<void>
  leave: () => void
  toggleMute: () => void
}

function participantToInfo(p: Participant): VoiceParticipant {
  const audioTrack = p.getTrackPublications().find(
    (t) => t.track?.kind === Track.Kind.Audio
  )
  return {
    identity: p.identity,
    name: p.name || p.identity,
    isSpeaking: p.isSpeaking,
    isMuted: audioTrack?.isMuted ?? true,
    connectionQuality: p.connectionQuality,
  }
}

export function useVoiceRoom(channelId: string): UseVoiceRoomReturn {
  const roomRef = useRef<Room | null>(null)
  const [state, setState] = useState<VoiceRoomState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [participants, setParticipants] = useState<VoiceParticipant[]>([])
  const [isMuted, setIsMuted] = useState(false)
  const [diagnostics, setDiagnostics] = useState<VoiceDiagnostics>({
    livekitUrl: null,
    roomName: null,
    tokenReceived: false,
    signalConnected: false,
    micPermission: 'unknown',
    lastEvent: null,
  })

  const updateDiag = useCallback((patch: Partial<VoiceDiagnostics>) => {
    setDiagnostics((prev) => ({ ...prev, ...patch }))
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
  }, [])

  const join = useCallback(async () => {
    if (roomRef.current) return
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
        lastEvent: 'token received, connecting to LiveKit...',
      })

      const room = new Room({
        adaptiveStream: true,
        dynacast: true,
        disconnectOnPageLeave: true,
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
            updateParticipants()
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

      room.on(RoomEvent.ParticipantConnected, () => {
        updateDiag({ lastEvent: 'participant joined' })
        updateParticipants()
      })
      room.on(RoomEvent.ParticipantDisconnected, () => {
        updateDiag({ lastEvent: 'participant left' })
        updateParticipants()
      })
      room.on(RoomEvent.ActiveSpeakersChanged, () => updateParticipants())
      room.on(RoomEvent.TrackMuted, () => updateParticipants())
      room.on(RoomEvent.TrackUnmuted, () => updateParticipants())
      room.on(RoomEvent.ConnectionQualityChanged, () => updateParticipants())

      room.on(RoomEvent.TrackSubscribed, (track, _pub: RemoteTrackPublication, _participant: RemoteParticipant) => {
        if (track.kind === Track.Kind.Audio) {
          const el = track.attach()
          el.id = `lk-audio-${_participant.identity}`
          document.body.appendChild(el)
        }
      })

      room.on(RoomEvent.TrackUnsubscribed, (track) => {
        track.detach().forEach((el) => el.remove())
      })

      room.on(RoomEvent.Disconnected, (reason) => {
        updateDiag({ lastEvent: `disconnected: ${reason ?? 'unknown'}`, signalConnected: false })
        setState('idle')
        setParticipants([])
        roomRef.current = null
      })

      room.on(RoomEvent.MediaDevicesError, (e) => {
        updateDiag({ lastEvent: `media error: ${e?.message ?? 'unknown'}`, micPermission: 'denied' })
      })

      await room.connect(res.url, res.token)
      updateDiag({ lastEvent: 'connected, enabling mic...' })

      try {
        await room.localParticipant.setMicrophoneEnabled(true)
        updateDiag({ micPermission: 'granted', lastEvent: 'mic enabled' })
        setIsMuted(false)
      } catch (micErr) {
        updateDiag({
          micPermission: 'denied',
          lastEvent: `mic error: ${micErr instanceof Error ? micErr.message : 'unknown'}`,
        })
        setIsMuted(true)
      }
      updateParticipants()
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to join voice room'
      setState('failed')
      setError(msg)
      updateDiag({ lastEvent: `error: ${msg}` })
      if (roomRef.current) {
        roomRef.current.disconnect()
        roomRef.current = null
      }
    }
  }, [channelId, updateParticipants, updateDiag])

  const leave = useCallback(() => {
    const room = roomRef.current
    if (room) {
      room.disconnect()
      roomRef.current = null
    }
    setState('idle')
    setParticipants([])
    setError(null)
    setIsMuted(false)
    setDiagnostics({
      livekitUrl: null,
      roomName: null,
      tokenReceived: false,
      signalConnected: false,
      micPermission: 'unknown',
      lastEvent: null,
    })
  }, [])

  const toggleMute = useCallback(() => {
    const room = roomRef.current
    if (!room) return
    const next = !isMuted
    room.localParticipant.setMicrophoneEnabled(!next)
    setIsMuted(next)
    updateParticipants()
  }, [isMuted, updateParticipants])

  useEffect(() => {
    return () => {
      if (roomRef.current) {
        roomRef.current.disconnect()
        roomRef.current = null
      }
    }
  }, [])

  return { state, error, participants, isMuted, diagnostics, join, leave, toggleMute }
}
