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
  LocalTrackPublication,
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

interface UseVoiceRoomReturn {
  state: VoiceRoomState
  error: string | null
  participants: VoiceParticipant[]
  isMuted: boolean
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

    try {
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

      room.on(RoomEvent.TrackUnsubscribed, (track, _pub: RemoteTrackPublication, _participant: RemoteParticipant) => {
        track.detach().forEach((el) => el.remove())
      })

      room.on(RoomEvent.Disconnected, () => {
        setState('idle')
        setParticipants([])
        roomRef.current = null
      })

      await room.connect(res.url, res.token)
      await room.localParticipant.setMicrophoneEnabled(true)
      setIsMuted(false)
      updateParticipants()
    } catch (e) {
      setState('failed')
      setError(e instanceof Error ? e.message : 'Failed to join voice room')
      if (roomRef.current) {
        roomRef.current.disconnect()
        roomRef.current = null
      }
    }
  }, [channelId, updateParticipants])

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

  return { state, error, participants, isMuted, join, leave, toggleMute }
}
