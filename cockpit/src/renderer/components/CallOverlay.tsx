import { Mic, MicOff, Volume2, VolumeX, PhoneOff, ArrowLeft } from 'lucide-react'
import { useVoiceSessionStore } from '../stores/voiceSessionStore'
import { useCockpitStore } from '../stores/cockpitStore'

export function CallOverlay() {
  const state = useVoiceSessionStore((s) => s.state)
  const isMuted = useVoiceSessionStore((s) => s.isMuted)
  const isDeafened = useVoiceSessionStore((s) => s.isDeafened)
  const activeChannelId = useVoiceSessionStore((s) => s.activeChannelId)
  const toggleMute = useVoiceSessionStore((s) => s.toggleMute)
  const toggleDeafen = useVoiceSessionStore((s) => s.toggleDeafen)
  const disconnect = useVoiceSessionStore((s) => s.disconnect)
  const activePanel = useCockpitStore((s) => s.activePanel)
  const setPanel = useCockpitStore((s) => s.setPanel)

  const isInCall = state === 'connected' || state === 'connecting' || state === 'reconnecting'
  const isOnRoomsPanel = activePanel === 'rooms'

  if (!isInCall || isOnRoomsPanel) return null

  const statusColor = state === 'connected' ? 'bg-green-500' : 'bg-yellow-500'
  const statusText = state === 'connected' ? 'In call' : state === 'reconnecting' ? 'Reconnecting...' : 'Connecting...'

  return (
    <div className="absolute bottom-0 left-0 right-0 z-10 flex items-center justify-between px-3 h-9 bg-surface-raised border-t border-border text-xs">
      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${statusColor} animate-pulse`} />
        <span className="text-text-secondary">{statusText}</span>
        {activeChannelId && (
          <span className="text-text-muted truncate max-w-[120px]">#{activeChannelId.slice(-6)}</span>
        )}
      </div>

      <div className="flex items-center gap-1">
        <button
          onClick={() => toggleMute()}
          className={`p-1.5 rounded hover:bg-surface-hover ${isMuted ? 'text-red-400' : 'text-text-secondary'}`}
          title={isMuted ? 'Unmute' : 'Mute'}
        >
          {isMuted ? <MicOff size={14} /> : <Mic size={14} />}
        </button>

        <button
          onClick={toggleDeafen}
          className={`p-1.5 rounded hover:bg-surface-hover ${isDeafened ? 'text-red-400' : 'text-text-secondary'}`}
          title={isDeafened ? 'Undeafen' : 'Deafen'}
        >
          {isDeafened ? <VolumeX size={14} /> : <Volume2 size={14} />}
        </button>

        <button
          onClick={() => setPanel('rooms')}
          className="p-1.5 rounded hover:bg-surface-hover text-text-secondary"
          title="Return to call"
        >
          <ArrowLeft size={14} />
        </button>

        <button
          onClick={disconnect}
          className="p-1.5 rounded hover:bg-red-500/20 text-red-400"
          title="Leave call"
        >
          <PhoneOff size={14} />
        </button>
      </div>
    </div>
  )
}
