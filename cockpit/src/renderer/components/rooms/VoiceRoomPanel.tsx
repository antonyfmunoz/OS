import { useEffect } from 'react'
import { Mic, MicOff, Headphones, PhoneOff, Users, Lock, Radio } from 'lucide-react'
import { useRoomsStore } from '../../stores/roomsStore'

export function VoiceRoomPanel({ channelId }: { channelId: string }) {
  const voiceStates = useRoomsStore((s) => s.voiceStates)
  const fetchVoiceState = useRoomsStore((s) => s.fetchVoiceState)
  const joinVoice = useRoomsStore((s) => s.joinVoice)
  const leaveVoice = useRoomsStore((s) => s.leaveVoice)
  const channels = useRoomsStore((s) => s.channels)

  const channel = channels.find((c) => c.id === channelId)
  const voiceState = voiceStates[channelId]

  useEffect(() => {
    fetchVoiceState(channelId)
  }, [channelId, fetchVoiceState])

  const isInRoom = voiceState?.participants.some((p) => p.user_id === 'operator')

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 flex flex-col items-center justify-center p-8">
        <div
          className="w-16 h-16 rounded-full flex items-center justify-center mb-4"
          style={{ background: 'var(--color-surface-raised)' }}
        >
          <Radio size={28} style={{ color: 'var(--color-cyan)' }} />
        </div>

        <h3 className="text-sm font-mono font-semibold mb-1" style={{ color: 'var(--color-text-primary)' }}>
          {channel?.name || 'Voice Room'}
        </h3>

        {voiceState?.topic && (
          <p className="text-[10px] font-mono mb-4" style={{ color: 'var(--color-text-tertiary)' }}>
            {voiceState.topic}
          </p>
        )}

        {voiceState?.locked && (
          <div className="flex items-center gap-1 mb-4">
            <Lock size={10} style={{ color: 'var(--color-warn)' }} />
            <span className="text-[9px] font-mono" style={{ color: 'var(--color-warn)' }}>LOCKED</span>
          </div>
        )}

        <div
          className="w-full max-w-sm rounded border p-3 mb-4"
          style={{ borderColor: 'var(--color-border)' }}
        >
          <div className="flex items-center gap-2 mb-2">
            <Users size={12} style={{ color: 'var(--color-text-secondary)' }} />
            <span className="text-[10px] font-mono" style={{ color: 'var(--color-text-secondary)' }}>
              {voiceState?.participants.length || 0}
              {voiceState?.capacity ? ` / ${voiceState.capacity}` : ''} participants
            </span>
          </div>

          {voiceState?.participants.map((p) => (
            <div key={p.user_id} className="flex items-center gap-2 py-1.5">
              <div
                className="w-6 h-6 rounded-full flex items-center justify-center text-[8px] font-mono font-bold"
                style={{ background: 'var(--color-surface-overlay)', color: 'var(--color-text-secondary)' }}
              >
                {p.display_name.charAt(0).toUpperCase()}
              </div>
              <span className="text-[10px] font-mono" style={{ color: 'var(--color-text-primary)' }}>
                {p.display_name}
              </span>
              <div className="flex items-center gap-1 ml-auto">
                {p.is_speaking && (
                  <div
                    className="w-2 h-2 rounded-full animate-pulse"
                    style={{ background: 'var(--color-ok)' }}
                  />
                )}
                {p.is_muted && <MicOff size={10} style={{ color: 'var(--color-danger)' }} />}
                {p.is_deafened && <Headphones size={10} style={{ color: 'var(--color-danger)' }} />}
              </div>
            </div>
          ))}

          {(!voiceState?.participants || voiceState.participants.length === 0) && (
            <p className="text-[9px] font-mono text-center py-2" style={{ color: 'var(--color-text-tertiary)' }}>
              No participants
            </p>
          )}
        </div>

        <div
          className="w-full max-w-sm rounded border p-3 mb-4"
          style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface-raised)' }}
        >
          <p className="text-[10px] font-mono text-center" style={{ color: 'var(--color-text-tertiary)' }}>
            Native WebRTC media transport pending.
          </p>
          <p className="text-[9px] font-mono text-center mt-1" style={{ color: 'var(--color-text-tertiary)' }}>
            Room presence and metadata are functional.
            Audio/video streaming requires SFU infrastructure.
          </p>
        </div>

        <div className="flex gap-2">
          {isInRoom ? (
            <button
              onClick={() => leaveVoice(channelId)}
              className="flex items-center gap-2 text-xs font-mono px-4 py-2 rounded"
              style={{ background: 'var(--color-danger)', color: 'var(--color-canvas)' }}
            >
              <PhoneOff size={14} /> Leave Room
            </button>
          ) : (
            <button
              onClick={() => joinVoice(channelId)}
              className="flex items-center gap-2 text-xs font-mono px-4 py-2 rounded"
              style={{ background: 'var(--color-ok)', color: 'var(--color-canvas)' }}
            >
              <Mic size={14} /> Join Room
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
