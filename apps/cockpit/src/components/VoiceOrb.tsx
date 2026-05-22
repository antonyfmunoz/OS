/**
 * VoiceOrb — persistent voice-first interface for the UMH cockpit.
 *
 * Renders as a floating orb in the bottom-right corner. States:
 *   idle       — subtle pulse, click to activate
 *   listening  — cyan glow, active mic
 *   processing — amber pulse, waiting for LLM
 *   speaking   — green pulse, playing TTS
 *   error      — red flash, auto-recovers
 *
 * Shows live transcript while listening and last response while speaking.
 */

import { useVoice } from '../hooks/useVoice.ts'
import type { VoiceState } from '../hooks/useVoice.ts'
import { Mic, MicOff, Loader2, Volume2 } from 'lucide-react'
import { clsx } from 'clsx'

const STATE_CONFIG: Record<VoiceState, {
  ring: string
  bg: string
  icon: typeof Mic
  label: string
  animate: string
}> = {
  idle: {
    ring: 'ring-zinc-700',
    bg: 'bg-zinc-900',
    icon: Mic,
    label: 'Tap to speak',
    animate: '',
  },
  listening: {
    ring: 'ring-cyan-400',
    bg: 'bg-cyan-950',
    icon: Mic,
    label: 'Listening...',
    animate: 'animate-pulse',
  },
  processing: {
    ring: 'ring-amber-400',
    bg: 'bg-amber-950',
    icon: Loader2,
    label: 'Thinking...',
    animate: 'animate-spin',
  },
  speaking: {
    ring: 'ring-emerald-400',
    bg: 'bg-emerald-950',
    icon: Volume2,
    label: 'Speaking...',
    animate: 'animate-pulse',
  },
  error: {
    ring: 'ring-red-400',
    bg: 'bg-red-950',
    icon: MicOff,
    label: 'Error — tap to retry',
    animate: '',
  },
}

export function VoiceOrb() {
  const { state, transcript, lastResponse, supported, toggle } = useVoice()

  if (!supported) return null

  const config = STATE_CONFIG[state]
  const Icon = config.icon

  const showText = state === 'listening' && transcript
  const showResponse = (state === 'speaking' || state === 'processing') && lastResponse

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">
      {/* Transcript / response bubble */}
      {(showText || showResponse) && (
        <div className="max-w-sm rounded-lg bg-zinc-900/95 border border-zinc-700 px-4 py-3 text-sm text-zinc-200 backdrop-blur-sm shadow-2xl">
          {showText && (
            <p className="text-cyan-300 font-mono text-xs">{transcript}</p>
          )}
          {showResponse && (
            <p className="text-zinc-300">{lastResponse}</p>
          )}
        </div>
      )}

      {/* Orb button */}
      <button
        onClick={toggle}
        className={clsx(
          'relative flex items-center justify-center',
          'w-16 h-16 rounded-full ring-2 shadow-2xl',
          'transition-all duration-300 cursor-pointer',
          'hover:scale-105 active:scale-95',
          config.bg,
          config.ring,
        )}
        title={config.label}
        aria-label={config.label}
      >
        {/* Outer glow ring for active states */}
        {state !== 'idle' && state !== 'error' && (
          <span
            className={clsx(
              'absolute inset-0 rounded-full opacity-30',
              config.ring.replace('ring-', 'bg-'),
              'animate-ping',
            )}
          />
        )}

        <Icon
          className={clsx(
            'w-6 h-6 relative z-10',
            state === 'listening' ? 'text-cyan-400' :
            state === 'processing' ? 'text-amber-400' :
            state === 'speaking' ? 'text-emerald-400' :
            state === 'error' ? 'text-red-400' :
            'text-zinc-400',
            config.animate,
          )}
        />
      </button>

      {/* State label */}
      <span className="text-xs text-zinc-500 font-mono pr-1">
        {config.label}
      </span>
    </div>
  )
}
