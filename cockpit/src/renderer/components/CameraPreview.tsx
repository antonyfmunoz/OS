import { useRef, useCallback, useState } from 'react'
import { clsx } from 'clsx'
import { Camera, CameraOff, Aperture, Eye, ChevronDown, Maximize2, Minimize2, PictureInPicture2 } from 'lucide-react'
import { useVisionStore } from '../stores/visionStore'
import { getVisionClient } from '../hooks/useVisionConnection'
import { useVisionPopout } from './VisionPopout'
import { VisionConnectionStatus } from './vision/VisionConnectionStatus'
import { VisionOverlay } from './vision'

// Minimal operator HUD shown on preview frame (mirrors the one in CameraController)
function PreviewHud() {
  const connected = useVisionStore((s) => s.connected)
  const streaming = useVisionStore((s) => s.streaming)
  const streamMetrics = useVisionStore((s) => s.streamMetrics)
  const overlays = useVisionStore((s) => s.overlays)
  const error = useVisionStore((s) => s.error)
  const chainHealth = useVisionStore((s) => s.chainHealth)

  const wsColor = connected ? '#22c55e' : '#ef4444'
  const frameAge = streamMetrics.lastFrameAge
  const frameAgeStr = frameAge <= 0 ? 'no frames' : frameAge < 1000 ? `${frameAge}ms` : `${(frameAge / 1000).toFixed(1)}s`
  const frameAgeColor = frameAge > 5000 ? '#ef4444' : frameAge > 2000 ? '#f59e0b' : '#22c55e'

  return (
    <div style={{
      position: 'absolute', bottom: 6, left: 6, zIndex: 20,
      pointerEvents: 'none', fontFamily: '"JetBrains Mono", monospace',
      fontSize: 9, lineHeight: '14px',
    }}>
      <div style={{
        background: 'rgba(0,0,0,0.72)', borderRadius: 4,
        padding: '4px 7px', display: 'flex', flexDirection: 'column', gap: 1, minWidth: 148,
      }}>
        <div style={{ display: 'flex', gap: 6 }}>
          <span style={{ color: wsColor }}>● {connected ? 'WS' : 'DISCONNECTED'}</span>
          {connected && <span style={{ color: '#555' }}>{chainHealth.status.replace('_', ' ')}</span>}
        </div>
        <div style={{ color: frameAgeColor }}>
          frame: {streaming ? frameAgeStr : 'not streaming'}
        </div>
        <div style={{ color: '#888' }}>
          fps: <span style={{ color: streamMetrics.actualFps > 0 ? '#22c55e' : '#555' }}>
            {streaming ? streamMetrics.actualFps.toFixed(1) : '0'}
          </span>
          {' '}<span style={{ color: overlays.length > 0 ? '#22c55e' : '#555' }}>{overlays.length} ovr</span>
        </div>
        {error && (
          <div style={{ color: '#ef4444', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            ! {error}
          </div>
        )}
      </div>
    </div>
  )
}

export function CameraPreview() {
  const {
    connected, streaming, cameraStatus, activePreset, latestFrameUrl,
    error, presets, frameCount,
    setCameraStatus, setActivePreset, setStreaming,
  } = useVisionStore()

  const overlays = useVisionStore((s) => s.overlays)
  const overlayVisible = useVisionStore((s) => s.overlayVisible)
  const width = useVisionStore((s) => s.width)
  const height = useVisionStore((s) => s.height)
  const poppedOut = useVisionStore((s) => s.poppedOut)
  const { openPopout } = useVisionPopout()
  const [expanded, setExpanded] = useState(false)
  const [presetOpen, setPresetOpen] = useState(false)
  const imgRef = useRef<HTMLImageElement>(null)

  const handleStart = useCallback(() => {
    const client = getVisionClient()
    if (!client?.connected) return
    setCameraStatus('connecting')
    client.startCamera({ fps: 15, width: 640, height: 480, quality: 65 })
    client.subscribe(15, 65)
  }, [])

  const handleStop = useCallback(() => {
    const client = getVisionClient()
    if (!client?.connected) return
    client.stopCamera()
    client.unsubscribe()
    setCameraStatus('off')
    setStreaming(false)
  }, [])

  const handleSnapshot = useCallback(() => {
    getVisionClient()?.requestSnapshot()
  }, [])

  const handlePreset = useCallback((name: string) => {
    getVisionClient()?.setPreset(name)
    setActivePreset(name)
    setPresetOpen(false)
  }, [])

  const isActive = cameraStatus === 'live' || cameraStatus === 'connecting'

  return (
    <div className={clsx('flex flex-col gap-2', expanded && 'fixed inset-0 z-50 bg-surface p-4')}>
      {/* Privacy indicator */}
      {isActive && (
        <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-danger/10 text-danger text-[10px] font-mono uppercase tracking-wider">
          <span className="w-1.5 h-1.5 rounded-full bg-danger animate-pulse" />
          camera active
        </div>
      )}

      {/* Preview frame */}
      <div className={clsx(
        'relative rounded border overflow-hidden bg-black',
        expanded ? 'flex-1' : 'aspect-video',
        isActive ? 'border-danger/30' : 'border-border',
      )}>
        {latestFrameUrl ? (
          <>
            <img
              ref={imgRef}
              src={latestFrameUrl}
              alt="Camera preview"
              decoding="async"
              className="w-full h-full object-contain"
            />
            <VisionOverlay
              overlays={overlays}
              width={width || 1280}
              height={height || 720}
              visible={overlayVisible}
            />
          </>
        ) : (
          <div className="flex items-center justify-center w-full h-full text-text-tertiary">
            <Camera size={24} className="opacity-30" />
          </div>
        )}

        {/* Operator pipeline HUD */}
        <PreviewHud />

        {/* FPS overlay */}
        {streaming && (
          <div className="absolute top-1 right-1 px-1.5 py-0.5 rounded bg-black/60 text-[9px] font-mono text-text-secondary">
            {frameCount} frames
          </div>
        )}

        {/* Expand/collapse + Pop-out */}
        <div className="absolute top-1 left-1 flex items-center gap-1">
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-1 rounded bg-black/60 text-text-secondary hover:text-white"
            title={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
          </button>
          <button
            onClick={openPopout}
            className="p-1 rounded bg-black/60 text-text-secondary hover:text-white"
            title="Pop out"
          >
            <PictureInPicture2 size={12} />
          </button>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-1.5">
        {!isActive ? (
          <button
            onClick={handleStart}
            disabled={!connected}
            className={clsx(
              'flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono uppercase tracking-wider transition-colors',
              connected
                ? 'bg-ok/10 text-ok hover:bg-ok/20'
                : 'bg-surface text-text-tertiary cursor-not-allowed',
            )}
          >
            <Camera size={12} />
            Start
          </button>
        ) : (
          <button
            onClick={handleStop}
            className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono uppercase tracking-wider bg-danger/10 text-danger hover:bg-danger/20"
          >
            <CameraOff size={12} />
            Stop
          </button>
        )}

        <button
          onClick={handleSnapshot}
          disabled={!connected}
          className={clsx(
            'flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono uppercase tracking-wider transition-colors',
            connected
              ? 'bg-cyan/10 text-cyan hover:bg-cyan/20'
              : 'bg-surface text-text-tertiary cursor-not-allowed',
          )}
        >
          <Aperture size={12} />
          Snap
        </button>

        <div className="relative">
          <button
            onClick={() => setPresetOpen(!presetOpen)}
            disabled={!connected}
            className={clsx(
              'flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono uppercase tracking-wider transition-colors',
              connected
                ? 'bg-surface-hover text-text-secondary hover:text-text-primary'
                : 'bg-surface text-text-tertiary cursor-not-allowed',
            )}
          >
            <Eye size={12} />
            {activePreset || 'Preset'}
            <ChevronDown size={10} />
          </button>

          {presetOpen && (
            <div className="absolute bottom-full left-0 mb-1 w-40 rounded border border-border bg-surface shadow-lg z-10">
              {Object.entries(presets).map(([name, preset]) => (
                <button
                  key={name}
                  onClick={() => handlePreset(name)}
                  className={clsx(
                    'block w-full text-left px-3 py-1.5 text-[11px] font-mono hover:bg-surface-hover transition-colors',
                    activePreset === name ? 'text-cyan' : 'text-text-secondary',
                  )}
                >
                  {preset.label || name}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Connection health chain */}
      <VisionConnectionStatus />

      {/* Error display */}
      {error && (
        <div className="px-2 py-1 rounded bg-danger/10 text-danger text-[10px] font-mono">
          {error}
        </div>
      )}
    </div>
  )
}
