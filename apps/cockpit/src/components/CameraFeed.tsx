import { useCamera } from '../hooks/useCamera.ts'
import type { CameraState } from '../hooks/useCamera.ts'
import { Camera, CameraOff, Eye, Loader2 } from 'lucide-react'
import { clsx } from 'clsx'
import { useState } from 'react'

const STATE_STYLE: Record<CameraState, { border: string; label: string }> = {
  off: { border: 'border-zinc-700', label: 'Camera off' },
  starting: { border: 'border-amber-500', label: 'Starting...' },
  live: { border: 'border-cyan-500', label: 'Live' },
  capturing: { border: 'border-amber-500', label: 'Analyzing...' },
  error: { border: 'border-red-500', label: 'Camera error' },
}

export function CameraFeed() {
  const { state, videoRef, lastVisionResult, supported, toggle, captureAndAnalyze } = useCamera()
  const [expanded, setExpanded] = useState(false)

  if (!supported) return null

  const style = STATE_STYLE[state]
  const isActive = state === 'live' || state === 'capturing'

  if (!expanded) {
    return (
      <div className="fixed bottom-6 right-24 z-50">
        <button
          onClick={() => {
            setExpanded(true)
            if (state === 'off') toggle()
          }}
          className={clsx(
            'flex items-center justify-center',
            'w-12 h-12 rounded-full ring-2 shadow-2xl',
            'transition-all duration-300 cursor-pointer',
            'hover:scale-105 active:scale-95',
            'bg-zinc-900',
            isActive ? 'ring-cyan-400' : 'ring-zinc-700',
          )}
          title="Open camera"
          aria-label="Open camera"
        >
          <Camera className={clsx('w-5 h-5', isActive ? 'text-cyan-400' : 'text-zinc-400')} />
        </button>
      </div>
    )
  }

  return (
    <div className="fixed bottom-6 right-24 z-50 flex flex-col items-end gap-2">
      {/* Vision result bubble */}
      {lastVisionResult && (
        <div className="max-w-sm rounded-lg bg-zinc-900/95 border border-zinc-700 px-4 py-3 text-sm text-zinc-200 backdrop-blur-sm shadow-2xl">
          <p className="text-zinc-300">{lastVisionResult.text}</p>
          {lastVisionResult.provider && (
            <p className="text-xs text-zinc-500 mt-1 font-mono">
              via {lastVisionResult.provider}
              {lastVisionResult.durationMs ? ` · ${lastVisionResult.durationMs}ms` : ''}
            </p>
          )}
        </div>
      )}

      {/* Video feed card */}
      <div className={clsx(
        'rounded-xl overflow-hidden border-2 shadow-2xl bg-black',
        'transition-all duration-300',
        style.border,
      )}>
        <div className="relative w-64 h-48">
          <video
            ref={videoRef}
            className="w-full h-full object-cover"
            autoPlay
            playsInline
            muted
          />

          {/* Overlay for non-live states */}
          {state !== 'live' && state !== 'capturing' && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/60">
              {state === 'starting' && <Loader2 className="w-8 h-8 text-amber-400 animate-spin" />}
              {state === 'off' && <CameraOff className="w-8 h-8 text-zinc-500" />}
              {state === 'error' && <CameraOff className="w-8 h-8 text-red-400" />}
            </div>
          )}

          {/* Capturing indicator */}
          {state === 'capturing' && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/30">
              <Loader2 className="w-8 h-8 text-amber-400 animate-spin" />
            </div>
          )}

          {/* Status badge */}
          <div className={clsx(
            'absolute top-2 left-2 px-2 py-0.5 rounded text-xs font-mono',
            state === 'live' ? 'bg-cyan-500/20 text-cyan-400' :
            state === 'capturing' ? 'bg-amber-500/20 text-amber-400' :
            'bg-zinc-800/80 text-zinc-400',
          )}>
            {style.label}
          </div>
        </div>

        {/* Controls bar */}
        <div className="flex items-center justify-between px-3 py-2 bg-zinc-900">
          <button
            onClick={toggle}
            className={clsx(
              'flex items-center gap-1.5 px-2 py-1 rounded text-xs font-mono',
              'transition-colors cursor-pointer',
              isActive
                ? 'text-red-400 hover:bg-red-500/10'
                : 'text-cyan-400 hover:bg-cyan-500/10',
            )}
          >
            {isActive ? <CameraOff className="w-3.5 h-3.5" /> : <Camera className="w-3.5 h-3.5" />}
            {isActive ? 'Stop' : 'Start'}
          </button>

          {isActive && (
            <button
              onClick={() => captureAndAnalyze()}
              disabled={state === 'capturing'}
              className={clsx(
                'flex items-center gap-1.5 px-2 py-1 rounded text-xs font-mono',
                'transition-colors cursor-pointer',
                'text-emerald-400 hover:bg-emerald-500/10',
                'disabled:opacity-40 disabled:cursor-not-allowed',
              )}
            >
              <Eye className="w-3.5 h-3.5" />
              Analyze
            </button>
          )}

          <button
            onClick={() => {
              if (isActive) toggle()
              setExpanded(false)
            }}
            className="text-zinc-500 hover:text-zinc-300 text-xs font-mono cursor-pointer px-1"
          >
            ×
          </button>
        </div>
      </div>
    </div>
  )
}
