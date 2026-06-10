import { useCallback, useState } from 'react'
import { clsx } from 'clsx'
import {
  ArrowUp, ArrowDown, ArrowLeft, ArrowRight,
  ZoomIn, ZoomOut, Home, Square,
  Save, Camera, CameraOff, Aperture,
  ChevronDown, PictureInPicture2, Maximize2, Minimize2,
} from 'lucide-react'
import {
  useVisionStore,
  QUALITY_PROFILES,
  type QualityMode,
} from '../stores/visionStore'
import { getVisionClient } from '../hooks/useVisionConnection'
import type { PtzDirection } from '../api/vision-ws'
import { useVisionPopout } from './VisionPopout'

const QUALITY_LABELS: Record<QualityMode, string> = {
  smooth: 'Smooth',
  balanced: 'Balanced',
  sharp: 'Sharp',
  analysis: 'Analysis',
}

const QUALITY_DESCRIPTIONS: Record<QualityMode, string> = {
  smooth: '720p 30fps',
  balanced: '720p 15fps',
  sharp: '1080p 10fps',
  analysis: '1080p 1fps',
}

export function CameraController({ compact = false }: { compact?: boolean }) {
  const {
    connected, streaming, cameraStatus, latestFrameUrl,
    presets, activePreset, ptzPosition, ptzMoving,
    hasPtzHardware, qualityMode, streamMetrics, error, frameCount,
  } = useVisionStore()
  const setQualityMode = useVisionStore((s) => s.setQualityMode)
  const setCameraStatus = useVisionStore((s) => s.setCameraStatus)
  const setStreaming = useVisionStore((s) => s.setStreaming)
  const setActivePreset = useVisionStore((s) => s.setActivePreset)
  const setPtzMoving = useVisionStore((s) => s.setPtzMoving)

  const { openPopout } = useVisionPopout()
  const [expanded, setExpanded] = useState(false)
  const [presetOpen, setPresetOpen] = useState(false)
  const [savingPreset, setSavingPreset] = useState(false)
  const [newPresetName, setNewPresetName] = useState('')
  const [newPresetLabel, setNewPresetLabel] = useState('')

  const isActive = cameraStatus === 'live' || cameraStatus === 'connecting'

  const handleStart = useCallback(() => {
    const client = getVisionClient()
    if (!client?.connected) return
    setCameraStatus('connecting')
    const profile = QUALITY_PROFILES[qualityMode]
    client.startCamera(profile)
    client.subscribe(profile.fps, profile.quality)
  }, [qualityMode, setCameraStatus])

  const handleStop = useCallback(() => {
    const client = getVisionClient()
    if (!client?.connected) return
    client.stopCamera()
    client.unsubscribe()
    setCameraStatus('off')
    setStreaming(false)
  }, [setCameraStatus, setStreaming])

  const handleSnapshot = useCallback(() => {
    getVisionClient()?.requestSnapshot({ width: 1920, height: 1080, quality: 90 })
  }, [])

  const handlePreset = useCallback((name: string) => {
    getVisionClient()?.setPreset(name)
    setActivePreset(name)
    setPresetOpen(false)
  }, [setActivePreset])

  const handlePtzMove = useCallback((direction: PtzDirection) => {
    const client = getVisionClient()
    if (!client?.connected) return
    setPtzMoving(true)
    client.ptzMove(direction, 1, 200)
    setTimeout(() => client.requestPosition(), 300)
  }, [setPtzMoving])

  const handlePtzStop = useCallback(() => {
    getVisionClient()?.ptzStop()
    setPtzMoving(false)
  }, [setPtzMoving])

  const handlePtzHome = useCallback(() => {
    const client = getVisionClient()
    if (!client?.connected) return
    setPtzMoving(true)
    client.ptzHome()
    setTimeout(() => client.requestPosition(), 500)
  }, [setPtzMoving])

  const handleZoomIn = useCallback(() => {
    const client = getVisionClient()
    if (!client?.connected) return
    setPtzMoving(true)
    client.zoomIn(10)
    setTimeout(() => client.requestPosition(), 300)
  }, [setPtzMoving])

  const handleZoomOut = useCallback(() => {
    const client = getVisionClient()
    if (!client?.connected) return
    setPtzMoving(true)
    client.zoomOut(10)
    setTimeout(() => client.requestPosition(), 300)
  }, [setPtzMoving])

  const handleQualityChange = useCallback((mode: QualityMode) => {
    setQualityMode(mode)
    const client = getVisionClient()
    if (!client?.connected || !streaming) return
    client.switchQuality(QUALITY_PROFILES[mode])
  }, [streaming, setQualityMode])

  const handleSavePreset = useCallback(() => {
    if (!newPresetName.trim()) return
    const client = getVisionClient()
    if (!client?.connected) return
    const slug = newPresetName.trim().toLowerCase().replace(/\s+/g, '_')
    client.savePreset(slug, newPresetLabel.trim() || newPresetName.trim())
    setSavingPreset(false)
    setNewPresetName('')
    setNewPresetLabel('')
  }, [newPresetName, newPresetLabel])

  const DPad = () => (
    <div className="grid grid-cols-3 gap-0.5 w-fit">
      <div />
      <PtzBtn icon={<ArrowUp size={12} />} onClick={() => handlePtzMove('up')} title="Pan up" />
      <div />
      <PtzBtn icon={<ArrowLeft size={12} />} onClick={() => handlePtzMove('left')} title="Pan left" />
      <PtzBtn
        icon={<div className="w-2 h-2 rounded-full bg-current" />}
        onClick={handlePtzStop}
        title="Stop"
        className="bg-surface-hover"
      />
      <PtzBtn icon={<ArrowRight size={12} />} onClick={() => handlePtzMove('right')} title="Pan right" />
      <div />
      <PtzBtn icon={<ArrowDown size={12} />} onClick={() => handlePtzMove('down')} title="Pan down" />
      <div />
    </div>
  )

  return (
    <div className={clsx('flex flex-col gap-3', expanded && 'fixed inset-0 z-50 bg-surface p-4')}>
      {/* Privacy indicator */}
      {isActive && (
        <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-danger/10 text-danger text-[10px] font-mono uppercase tracking-wider">
          <span className="w-1.5 h-1.5 rounded-full bg-danger animate-pulse" />
          camera active
          {hasPtzHardware ? ' — physical ptz' : ' — digital roi'}
        </div>
      )}

      {/* Preview frame */}
      <div className={clsx(
        'relative rounded border overflow-hidden bg-black',
        expanded ? 'flex-1 min-h-0' : 'aspect-video',
        isActive ? 'border-danger/30' : 'border-border',
      )}>
        {latestFrameUrl ? (
          <img
            src={latestFrameUrl}
            alt="Camera preview"
            className="w-full h-full object-contain"
          />
        ) : (
          <div className="flex items-center justify-center w-full h-full text-text-tertiary">
            <Camera size={24} className="opacity-30" />
          </div>
        )}

        {streaming && (
          <div className="absolute top-1 right-1 px-1.5 py-0.5 rounded bg-black/60 text-[9px] font-mono text-text-secondary">
            {streamMetrics.actualFps.toFixed(1)} fps | {Math.round(streamMetrics.avgFrameSize / 1024)}KB
          </div>
        )}

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

      {/* Start/Stop + Snapshot */}
      <div className="flex items-center gap-1.5">
        {!isActive ? (
          <CtrlBtn icon={<Camera size={12} />} label="Start" onClick={handleStart} disabled={!connected} variant="ok" />
        ) : (
          <CtrlBtn icon={<CameraOff size={12} />} label="Stop" onClick={handleStop} variant="danger" />
        )}
        <CtrlBtn icon={<Aperture size={12} />} label="Snap" onClick={handleSnapshot} disabled={!connected} variant="cyan" />
      </div>

      {!compact && (
        <>
          {/* PTZ Joystick + Zoom */}
          <div className="flex items-start gap-4">
            <div className="flex flex-col items-center gap-1">
              <span className="text-[9px] font-mono text-text-tertiary uppercase tracking-wider">
                {hasPtzHardware ? 'Physical PTZ' : 'Digital ROI'}
              </span>
              <DPad />
              <div className="flex gap-1 mt-1">
                <PtzBtn icon={<Home size={12} />} onClick={handlePtzHome} title="Home / Center" />
                <PtzBtn icon={<Square size={12} />} onClick={handlePtzStop} title="Stop movement" />
              </div>
            </div>

            <div className="flex flex-col items-center gap-1">
              <span className="text-[9px] font-mono text-text-tertiary uppercase tracking-wider">Zoom</span>
              <div className="flex flex-col gap-0.5">
                <PtzBtn icon={<ZoomIn size={12} />} onClick={handleZoomIn} title="Zoom in" />
                <PtzBtn icon={<ZoomOut size={12} />} onClick={handleZoomOut} title="Zoom out" />
              </div>
            </div>

            {/* Position readout */}
            <div className="flex flex-col gap-1 text-[10px] font-mono text-text-tertiary mt-3">
              <span>P: {ptzPosition.pan}</span>
              <span>T: {ptzPosition.tilt}</span>
              <span>Z: {ptzPosition.zoom}</span>
              {ptzMoving && <span className="text-warning">moving...</span>}
            </div>
          </div>

          {/* Presets */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[9px] font-mono text-text-tertiary uppercase tracking-wider">Presets</span>
              <button
                onClick={() => setSavingPreset(!savingPreset)}
                className="flex items-center gap-1 text-[9px] font-mono text-text-tertiary hover:text-text-primary uppercase tracking-wider transition-colors"
              >
                <Save size={10} />
                Save current
              </button>
            </div>

            <div className="flex flex-wrap gap-1">
              {Object.entries(presets).map(([name, preset]) => (
                <button
                  key={name}
                  onClick={() => handlePreset(name)}
                  disabled={!connected}
                  className={clsx(
                    'px-2 py-1 rounded text-[10px] font-mono uppercase tracking-wider transition-colors',
                    activePreset === name
                      ? 'bg-cyan/20 text-cyan border border-cyan/30'
                      : 'bg-surface-hover text-text-secondary hover:text-text-primary border border-transparent',
                    !connected && 'opacity-50 cursor-not-allowed',
                  )}
                >
                  {preset.label || name}
                </button>
              ))}
            </div>

            {savingPreset && (
              <div className="flex items-center gap-1.5 p-2 rounded border border-border bg-surface-hover">
                <input
                  type="text"
                  value={newPresetName}
                  onChange={(e) => setNewPresetName(e.target.value)}
                  placeholder="Slug (e.g. custom_1)"
                  className="flex-1 px-2 py-1 rounded bg-surface border border-border text-[10px] font-mono text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-cyan/50"
                />
                <input
                  type="text"
                  value={newPresetLabel}
                  onChange={(e) => setNewPresetLabel(e.target.value)}
                  placeholder="Label (e.g. Left monitor)"
                  className="flex-1 px-2 py-1 rounded bg-surface border border-border text-[10px] font-mono text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-cyan/50"
                />
                <button
                  onClick={handleSavePreset}
                  disabled={!newPresetName.trim()}
                  className="px-2 py-1 rounded bg-cyan/10 text-cyan text-[10px] font-mono uppercase tracking-wider hover:bg-cyan/20 disabled:opacity-50"
                >
                  Save
                </button>
              </div>
            )}
          </div>

          {/* Quality mode selector */}
          <div className="flex flex-col gap-1.5">
            <span className="text-[9px] font-mono text-text-tertiary uppercase tracking-wider">Stream Quality</span>
            <div className="flex gap-1">
              {(Object.keys(QUALITY_PROFILES) as QualityMode[]).map((mode) => (
                <button
                  key={mode}
                  onClick={() => handleQualityChange(mode)}
                  className={clsx(
                    'flex-1 px-2 py-1.5 rounded text-[10px] font-mono uppercase tracking-wider transition-colors text-center',
                    qualityMode === mode
                      ? 'bg-cyan/20 text-cyan border border-cyan/30'
                      : 'bg-surface-hover text-text-secondary hover:text-text-primary border border-transparent',
                  )}
                  title={QUALITY_DESCRIPTIONS[mode]}
                >
                  {QUALITY_LABELS[mode]}
                </button>
              ))}
            </div>
          </div>

          {/* Stream Metrics */}
          <div className="grid grid-cols-3 gap-x-4 gap-y-1 text-[10px] font-mono text-text-tertiary">
            <span>FPS: <span className={streamMetrics.actualFps > 0 ? 'text-ok' : 'text-text-secondary'}>{streamMetrics.actualFps.toFixed(1)}</span> / {streamMetrics.targetFps}</span>
            <span>Frame: {Math.round(streamMetrics.avgFrameSize / 1024)} KB</span>
            <span>Age: {streamMetrics.lastFrameAge < 1000 ? `${streamMetrics.lastFrameAge}ms` : `${(streamMetrics.lastFrameAge / 1000).toFixed(1)}s`}</span>
            <span>Frames: {frameCount}</span>
            <span>Dropped: {streamMetrics.droppedFrames}</span>
            <span>Quality: {QUALITY_DESCRIPTIONS[qualityMode]}</span>
          </div>
        </>
      )}

      {/* Connection status */}
      <div className="flex items-center gap-2 text-[10px] font-mono text-text-tertiary">
        <span className={clsx(
          'w-1.5 h-1.5 rounded-full',
          connected ? 'bg-ok' : 'bg-danger',
        )} />
        {connected ? 'vision relay connected' : 'vision relay disconnected'}
      </div>

      {error && (
        <div className="px-2 py-1 rounded bg-danger/10 text-danger text-[10px] font-mono">
          {error}
        </div>
      )}
    </div>
  )
}

function PtzBtn({
  icon, onClick, title, className,
}: {
  icon: React.ReactNode
  onClick: () => void
  title: string
  className?: string
}) {
  const connected = useVisionStore((s) => s.connected)
  return (
    <button
      onClick={onClick}
      disabled={!connected}
      title={title}
      className={clsx(
        'w-7 h-7 flex items-center justify-center rounded border border-border',
        'text-text-secondary hover:text-text-primary hover:bg-surface-hover',
        'transition-colors disabled:opacity-40 disabled:cursor-not-allowed',
        className,
      )}
    >
      {icon}
    </button>
  )
}

function CtrlBtn({
  icon, label, onClick, disabled, variant,
}: {
  icon: React.ReactNode
  label: string
  onClick: () => void
  disabled?: boolean
  variant: 'ok' | 'danger' | 'cyan'
}) {
  const colors = {
    ok: 'bg-ok/10 text-ok hover:bg-ok/20',
    danger: 'bg-danger/10 text-danger hover:bg-danger/20',
    cyan: 'bg-cyan/10 text-cyan hover:bg-cyan/20',
  }
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        'flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono uppercase tracking-wider transition-colors',
        disabled ? 'bg-surface text-text-tertiary cursor-not-allowed' : colors[variant],
      )}
    >
      {icon}
      {label}
    </button>
  )
}
