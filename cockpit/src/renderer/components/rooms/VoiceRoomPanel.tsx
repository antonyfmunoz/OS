import { useEffect, useCallback } from 'react'
import {
  Radio,
  Lock,
  AlertTriangle,
} from 'lucide-react'
import { useRoomsStore } from '../../stores/roomsStore'

export function VoiceRoomPanel({ channelId }: { channelId: string }) {
  const channels = useRoomsStore((s) => s.channels)
  const fetchVoiceState = useRoomsStore((s) => s.fetchVoiceState)

  const channel = channels.find((c) => c.id === channelId)

  useEffect(() => {
    fetchVoiceState(channelId)
  }, [channelId, fetchVoiceState])

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="flex-1 flex flex-col items-center justify-center p-6 max-w-md mx-auto w-full">
        <div
          className="w-14 h-14 rounded-full flex items-center justify-center mb-3"
          style={{ background: 'var(--color-surface-raised)' }}
        >
          <Radio size={24} style={{ color: 'var(--color-text-tertiary)' }} />
        </div>

        <h3 className="text-sm font-mono font-semibold mb-1" style={{ color: 'var(--color-text-primary)' }}>
          {channel?.name || 'Voice Room'}
        </h3>

        <div
          className="flex items-center gap-2 px-3 py-1.5 rounded mb-4"
          style={{ background: 'var(--color-warn-dim)' }}
        >
          <AlertTriangle size={12} style={{ color: 'var(--color-warn)' }} />
          <span className="text-[10px] font-mono font-semibold uppercase" style={{ color: 'var(--color-warn)' }}>
            Shell Only
          </span>
        </div>

        <div
          className="w-full rounded border p-4 mb-4"
          style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface-raised)' }}
        >
          <p className="text-[11px] font-mono mb-3" style={{ color: 'var(--color-text-primary)' }}>
            Voice rooms require WebRTC/SFU infrastructure to function.
          </p>
          <p className="text-[10px] font-mono mb-3" style={{ color: 'var(--color-text-secondary)' }}>
            No real audio/video is available yet. This is a room metadata shell only.
            Joining does not create an audio session.
          </p>

          <div className="border-t pt-3 mt-3" style={{ borderColor: 'var(--color-border)' }}>
            <p className="text-[9px] font-mono uppercase mb-2" style={{ color: 'var(--color-text-tertiary)' }}>
              Next Build Target
            </p>
            <div className="space-y-1.5">
              <StatusLine label="WebRTC peer connections" status="not started" />
              <StatusLine label="getUserMedia (mic/camera)" status="not started" />
              <StatusLine label="SFU media server" status="not started" />
              <StatusLine label="Mute / unmute / deafen" status="not started" />
              <StatusLine label="Speaking indicators" status="not started" />
              <StatusLine label="Screen share" status="not started" />
              <StatusLine label="Participant presence (live)" status="not started" />
              <StatusLine label="Reconnect handling" status="not started" />
              <StatusLine label="AI participant integration" status="not started" />
              <StatusLine label="Meeting transcription" status="not started" />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatusLine({ label, status }: { label: string; status: 'not started' | 'in progress' | 'done' }) {
  const color = status === 'done' ? 'var(--color-ok)' : status === 'in progress' ? 'var(--color-warn)' : 'var(--color-text-tertiary)'
  return (
    <div className="flex items-center justify-between">
      <span className="text-[9px] font-mono" style={{ color: 'var(--color-text-secondary)' }}>{label}</span>
      <div className="flex items-center gap-1">
        <div className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
        <span className="text-[9px] font-mono uppercase" style={{ color }}>{status}</span>
      </div>
    </div>
  )
}
