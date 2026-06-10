import { useCallback, useEffect, useRef, useState } from 'react'
import { clsx } from 'clsx'
import {
  ArrowUp, ArrowDown, ArrowLeft, ArrowRight,
  ZoomIn, ZoomOut, Home, Square,
  Save, Camera, CameraOff, Aperture,
  PictureInPicture2, Maximize2, Minimize2, Circle,
} from 'lucide-react'
import {
  useVisionStore,
  QUALITY_PROFILES,
  type QualityMode,
  type MotionState,
} from '../stores/visionStore'
import { getVisionClient } from '../hooks/useVisionConnection'
import { useVisionPopout } from './VisionPopout'
import { TrackingPanel } from './TrackingPanel'

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

let _motionIdCounter = 0
function nextMotionId(): string {
  return `m_${++_motionIdCounter}_${Date.now()}`
}

const MOTION_UPDATE_INTERVAL_MS = 50
const JOYSTICK_DEADZONE = 0.15

export function CameraController({ compact = false }: { compact?: boolean }) {
  const {
    connected, streaming, cameraStatus, latestFrameUrl,
    presets, activePreset, ptzPosition, ptzMoving,
    hasPtzHardware, qualityMode, streamMetrics, error, frameCount,
    ptzMotion, controlMetrics,
  } = useVisionStore()
  const setQualityMode = useVisionStore((s) => s.setQualityMode)
  const setCameraStatus = useVisionStore((s) => s.setCameraStatus)
  const setStreaming = useVisionStore((s) => s.setStreaming)
  const setActivePreset = useVisionStore((s) => s.setActivePreset)
  const setPtzMoving = useVisionStore((s) => s.setPtzMoving)
  const setPtzMotion = useVisionStore((s) => s.setPtzMotion)
  const updateControlMetrics = useVisionStore((s) => s.updateControlMetrics)

  const { openPopout } = useVisionPopout()
  const [expanded, setExpanded] = useState(false)
  const [presetOpen, setPresetOpen] = useState(false)
  const [savingPreset, setSavingPreset] = useState(false)
  const [newPresetName, setNewPresetName] = useState('')
  const [newPresetLabel, setNewPresetLabel] = useState('')
  const [speed, setSpeed] = useState(1)

  const activeMotionIdRef = useRef<string>('')
  const motionUpdateTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const joystickRef = useRef<HTMLDivElement>(null)
  const joystickDragging = useRef(false)
  const joystickVelocity = useRef({ pan: 0, tilt: 0 })

  const isActive = cameraStatus === 'live' || cameraStatus === 'connecting'

  // ── Emergency stop — window blur / visibility ───────────────────

  useEffect(() => {
    const emergencyStop = () => {
      if (activeMotionIdRef.current) {
        const client = getVisionClient()
        if (client?.connected) {
          client.ptzStopMotion(activeMotionIdRef.current)
          updateControlMetrics({ lastStopSentAt: Date.now() })
        }
        activeMotionIdRef.current = ''
        setPtzMotion({ state: 'idle', motionId: '', panVelocity: 0, tiltVelocity: 0, zoomVelocity: 0 })
        if (motionUpdateTimerRef.current) {
          clearInterval(motionUpdateTimerRef.current)
          motionUpdateTimerRef.current = null
        }
      }
    }

    window.addEventListener('blur', emergencyStop)
    const visibilityHandler = () => {
      if (document.visibilityState === 'hidden') emergencyStop()
    }
    document.addEventListener('visibilitychange', visibilityHandler)

    return () => {
      window.removeEventListener('blur', emergencyStop)
      document.removeEventListener('visibilitychange', visibilityHandler)
      emergencyStop()
    }
  }, [setPtzMotion, updateControlMetrics])

  // ── Camera start/stop ──────────────────────────────────────────

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
    getVisionClient()?.setPreset(name, true, 1.0)
    setActivePreset(name)
    setPresetOpen(false)
  }, [setActivePreset])

  // ── Realtime PTZ motion — press-and-hold D-pad ─────────────────

  const startDirectionMotion = useCallback((panV: number, tiltV: number) => {
    const client = getVisionClient()
    if (!client?.connected) return

    if (activeMotionIdRef.current) {
      client.ptzStopMotion(activeMotionIdRef.current)
    }

    const motionId = nextMotionId()
    activeMotionIdRef.current = motionId
    client.ptzStartMotion({
      motionId,
      panVelocity: panV,
      tiltVelocity: tiltV,
      speed,
      durationGuardMs: 500,
    })
    setPtzMotion({ state: 'moving', motionId, panVelocity: panV, tiltVelocity: tiltV, zoomVelocity: 0, speed })
    setPtzMoving(true)
    updateControlMetrics({ lastCommandSentAt: Date.now() })
  }, [speed, setPtzMotion, setPtzMoving, updateControlMetrics])

  const stopDirectionMotion = useCallback(() => {
    const client = getVisionClient()
    if (!activeMotionIdRef.current) return
    if (client?.connected) {
      client.ptzStopMotion(activeMotionIdRef.current)
      updateControlMetrics({ lastStopSentAt: Date.now() })
    }
    activeMotionIdRef.current = ''
    setPtzMotion({ state: 'idle', motionId: '', panVelocity: 0, tiltVelocity: 0, zoomVelocity: 0 })
    setPtzMoving(false)
    if (motionUpdateTimerRef.current) {
      clearInterval(motionUpdateTimerRef.current)
      motionUpdateTimerRef.current = null
    }
  }, [setPtzMotion, setPtzMoving, updateControlMetrics])

  // ── Continuous zoom — press-and-hold ───────────────────────────

  const startZoomMotion = useCallback((zoomV: number) => {
    const client = getVisionClient()
    if (!client?.connected) return

    if (activeMotionIdRef.current) {
      client.ptzStopMotion(activeMotionIdRef.current)
    }

    const motionId = nextMotionId()
    activeMotionIdRef.current = motionId
    client.zoomStartMotion(motionId, zoomV, speed)
    setPtzMotion({ state: 'moving', motionId, panVelocity: 0, tiltVelocity: 0, zoomVelocity: zoomV, speed })
    setPtzMoving(true)
    updateControlMetrics({ lastCommandSentAt: Date.now() })
  }, [speed, setPtzMotion, setPtzMoving, updateControlMetrics])

  const stopZoomMotion = useCallback(() => {
    const client = getVisionClient()
    if (!activeMotionIdRef.current) return
    if (client?.connected) {
      client.zoomStopMotion(activeMotionIdRef.current)
      updateControlMetrics({ lastStopSentAt: Date.now() })
    }
    activeMotionIdRef.current = ''
    setPtzMotion({ state: 'idle', motionId: '', panVelocity: 0, tiltVelocity: 0, zoomVelocity: 0 })
    setPtzMoving(false)
  }, [setPtzMotion, setPtzMoving, updateControlMetrics])

  // ── Joystick drag ──────────────────────────────────────────────

  const handleJoystickPointerDown = useCallback((e: React.PointerEvent) => {
    const el = joystickRef.current
    if (!el) return
    el.setPointerCapture(e.pointerId)
    joystickDragging.current = true

    const rect = el.getBoundingClientRect()
    const cx = rect.left + rect.width / 2
    const cy = rect.top + rect.height / 2
    const dx = (e.clientX - cx) / (rect.width / 2)
    const dy = -(e.clientY - cy) / (rect.height / 2)
    const panV = Math.abs(dx) > JOYSTICK_DEADZONE ? Math.max(-1, Math.min(1, dx)) : 0
    const tiltV = Math.abs(dy) > JOYSTICK_DEADZONE ? Math.max(-1, Math.min(1, dy)) : 0

    joystickVelocity.current = { pan: panV, tilt: tiltV }

    if (Math.abs(panV) > 0 || Math.abs(tiltV) > 0) {
      startDirectionMotion(panV, tiltV)

      if (motionUpdateTimerRef.current) clearInterval(motionUpdateTimerRef.current)
      motionUpdateTimerRef.current = setInterval(() => {
        const client = getVisionClient()
        const mid = activeMotionIdRef.current
        if (!client?.connected || !mid) return
        const v = joystickVelocity.current
        client.ptzUpdateMotion({
          motionId: mid,
          panVelocity: v.pan,
          tiltVelocity: v.tilt,
          speed,
        })
      }, MOTION_UPDATE_INTERVAL_MS)
    }
  }, [startDirectionMotion, speed])

  const handleJoystickPointerMove = useCallback((e: React.PointerEvent) => {
    if (!joystickDragging.current) return
    const el = joystickRef.current
    if (!el) return

    const rect = el.getBoundingClientRect()
    const cx = rect.left + rect.width / 2
    const cy = rect.top + rect.height / 2
    const dx = (e.clientX - cx) / (rect.width / 2)
    const dy = -(e.clientY - cy) / (rect.height / 2)
    const panV = Math.abs(dx) > JOYSTICK_DEADZONE ? Math.max(-1, Math.min(1, dx)) : 0
    const tiltV = Math.abs(dy) > JOYSTICK_DEADZONE ? Math.max(-1, Math.min(1, dy)) : 0

    joystickVelocity.current = { pan: panV, tilt: tiltV }

    if (!activeMotionIdRef.current && (Math.abs(panV) > 0 || Math.abs(tiltV) > 0)) {
      startDirectionMotion(panV, tiltV)
    }
  }, [startDirectionMotion])

  const handleJoystickPointerUp = useCallback(() => {
    joystickDragging.current = false
    joystickVelocity.current = { pan: 0, tilt: 0 }
    stopDirectionMotion()
  }, [stopDirectionMotion])

  // ── PTZ Home / Emergency Stop ──────────────────────────────────

  const handlePtzHome = useCallback(() => {
    const client = getVisionClient()
    if (!client?.connected) return
    stopDirectionMotion()
    setPtzMoving(true)
    client.ptzHome()
    setTimeout(() => {
      client.requestPosition()
      setPtzMoving(false)
    }, 500)
  }, [setPtzMoving, stopDirectionMotion])

  const handleEmergencyStop = useCallback(() => {
    const client = getVisionClient()
    if (!client?.connected) return
    stopDirectionMotion()
    stopZoomMotion()
    client.ptzStop()
    setPtzMoving(false)
  }, [setPtzMoving, stopDirectionMotion, stopZoomMotion])

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

  // ── Motion state label ─────────────────────────────────────────

  const motionLabel = (state: MotionState): string => {
    const labels: Record<MotionState, string> = {
      idle: 'idle',
      moving: 'moving',
      stopping: 'stopping...',
      blocked: 'blocked',
      disconnected: 'disconnected',
    }
    return labels[state] || state
  }

  // ── Render ─────────────────────────────────────────────────────

  return (
    <div className={clsx('flex flex-col gap-3', expanded && 'fixed inset-0 z-50 bg-surface p-4')}>
      {/* CAMERA LIVE indicator */}
      {isActive && (
        <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-danger/10 text-danger text-[10px] font-mono uppercase tracking-wider">
          <span className="w-2 h-2 rounded-full bg-danger animate-pulse" />
          camera live
          {hasPtzHardware ? ' — physical ptz' : ' — digital roi'}
          {ptzMotion.state === 'moving' && (
            <span className="ml-auto text-warning">{motionLabel(ptzMotion.state)}</span>
          )}
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
        <CtrlBtn icon={<Square size={12} />} label="E-Stop" onClick={handleEmergencyStop} variant="danger" />
      </div>

      {!compact && (
        <>
          {/* PTZ Controls: D-pad (press-and-hold) + Joystick + Zoom */}
          <div className="flex items-start gap-4">
            {/* D-pad with press-and-hold */}
            <div className="flex flex-col items-center gap-1">
              <span className="text-[9px] font-mono text-text-tertiary uppercase tracking-wider">
                {hasPtzHardware ? 'Physical PTZ' : 'Digital ROI'}
              </span>
              <div className="grid grid-cols-3 gap-0.5 w-fit">
                <div />
                <DpadBtn direction="up" onStart={() => startDirectionMotion(0, 1)} onStop={stopDirectionMotion} connected={connected} />
                <div />
                <DpadBtn direction="left" onStart={() => startDirectionMotion(-1, 0)} onStop={stopDirectionMotion} connected={connected} />
                <DpadBtn direction="stop" onStart={handleEmergencyStop} onStop={() => {}} connected={connected} isStop />
                <DpadBtn direction="right" onStart={() => startDirectionMotion(1, 0)} onStop={stopDirectionMotion} connected={connected} />
                <div />
                <DpadBtn direction="down" onStart={() => startDirectionMotion(0, -1)} onStop={stopDirectionMotion} connected={connected} />
                <div />
              </div>
              <div className="flex gap-1 mt-1">
                <PtzBtn icon={<Home size={12} />} onClick={handlePtzHome} title="Home / Center" />
              </div>
            </div>

            {/* Joystick area */}
            <div className="flex flex-col items-center gap-1">
              <span className="text-[9px] font-mono text-text-tertiary uppercase tracking-wider">Joystick</span>
              <div
                ref={joystickRef}
                onPointerDown={handleJoystickPointerDown}
                onPointerMove={handleJoystickPointerMove}
                onPointerUp={handleJoystickPointerUp}
                onPointerCancel={handleJoystickPointerUp}
                className="w-16 h-16 rounded-full border border-border bg-surface-hover relative cursor-crosshair touch-none select-none"
              >
                <div className="absolute inset-0 flex items-center justify-center">
                  <Circle size={8} className="text-text-quaternary" />
                </div>
                {ptzMotion.state === 'moving' && (
                  <div
                    className="absolute w-2 h-2 rounded-full bg-cyan"
                    style={{
                      left: `${50 + ptzMotion.panVelocity * 40}%`,
                      top: `${50 - ptzMotion.tiltVelocity * 40}%`,
                      transform: 'translate(-50%, -50%)',
                    }}
                  />
                )}
              </div>
            </div>

            {/* Zoom (press-and-hold) */}
            <div className="flex flex-col items-center gap-1">
              <span className="text-[9px] font-mono text-text-tertiary uppercase tracking-wider">Zoom</span>
              <div className="flex flex-col gap-0.5">
                <ZoomBtn icon={<ZoomIn size={12} />} onStart={() => startZoomMotion(1)} onStop={stopZoomMotion} connected={connected} title="Zoom in" />
                <ZoomBtn icon={<ZoomOut size={12} />} onStart={() => startZoomMotion(-1)} onStop={stopZoomMotion} connected={connected} title="Zoom out" />
              </div>
            </div>

            {/* Position readout + motion state */}
            <div className="flex flex-col gap-1 text-[10px] font-mono text-text-tertiary mt-3">
              <span>P: {ptzPosition.pan}</span>
              <span>T: {ptzPosition.tilt}</span>
              <span>Z: {ptzPosition.zoom}</span>
              <span className={clsx(
                ptzMotion.state === 'moving' && 'text-warning',
                ptzMotion.state === 'blocked' && 'text-danger',
                ptzMotion.state === 'idle' && 'text-ok',
              )}>
                {motionLabel(ptzMotion.state)}
              </span>
            </div>
          </div>

          {/* Speed slider */}
          <div className="flex items-center gap-2">
            <span className="text-[9px] font-mono text-text-tertiary uppercase tracking-wider w-12">Speed</span>
            <input
              type="range"
              min={0.2}
              max={3}
              step={0.1}
              value={speed}
              onChange={(e) => setSpeed(parseFloat(e.target.value))}
              className="flex-1 accent-cyan h-1"
            />
            <span className="text-[10px] font-mono text-text-tertiary w-8 text-right">{speed.toFixed(1)}x</span>
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

          {/* Stream + Control Metrics */}
          <div className="grid grid-cols-3 gap-x-4 gap-y-1 text-[10px] font-mono text-text-tertiary">
            <span>FPS: <span className={streamMetrics.actualFps > 0 ? 'text-ok' : 'text-text-secondary'}>{streamMetrics.actualFps.toFixed(1)}</span> / {streamMetrics.targetFps}</span>
            <span>Frame: {Math.round(streamMetrics.avgFrameSize / 1024)} KB</span>
            <span>Age: {streamMetrics.lastFrameAge < 1000 ? `${streamMetrics.lastFrameAge}ms` : `${(streamMetrics.lastFrameAge / 1000).toFixed(1)}s`}</span>
            <span>Frames: {frameCount}</span>
            <span>Dropped: {streamMetrics.droppedFrames}</span>
            <span>Quality: {QUALITY_DESCRIPTIONS[qualityMode]}</span>
            {controlMetrics.ptzLoopCadenceHz > 0 && (
              <span>PTZ loop: {controlMetrics.ptzLoopCadenceHz}Hz</span>
            )}
            {controlMetrics.stopLatencyMs > 0 && (
              <span>Stop: {controlMetrics.stopLatencyMs}ms</span>
            )}
            {controlMetrics.guardTimeouts > 0 && (
              <span className="text-warning">Guards: {controlMetrics.guardTimeouts}</span>
            )}
          </div>

          {/* Tracking / Scene Intelligence */}
          <div className="border-t border-border pt-3">
            <TrackingPanel />
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

// ── Press-and-hold D-pad button ──────────────────────────────────

function DpadBtn({
  direction, onStart, onStop, connected, isStop,
}: {
  direction: string
  onStart: () => void
  onStop: () => void
  connected: boolean
  isStop?: boolean
}) {
  const icons: Record<string, React.ReactNode> = {
    up: <ArrowUp size={12} />,
    down: <ArrowDown size={12} />,
    left: <ArrowLeft size={12} />,
    right: <ArrowRight size={12} />,
    stop: <div className="w-2 h-2 rounded-full bg-current" />,
  }
  return (
    <button
      onPointerDown={(e) => {
        e.preventDefault()
        if (!isStop) onStart()
        else onStart()
      }}
      onPointerUp={(e) => {
        e.preventDefault()
        if (!isStop) onStop()
      }}
      onPointerCancel={(e) => {
        e.preventDefault()
        if (!isStop) onStop()
      }}
      onPointerLeave={(e) => {
        e.preventDefault()
        if (!isStop) onStop()
      }}
      disabled={!connected}
      title={`Pan ${direction}`}
      className={clsx(
        'w-7 h-7 flex items-center justify-center rounded border border-border',
        'text-text-secondary hover:text-text-primary hover:bg-surface-hover',
        'transition-colors disabled:opacity-40 disabled:cursor-not-allowed touch-none select-none',
        isStop && 'bg-surface-hover',
      )}
    >
      {icons[direction]}
    </button>
  )
}

// ── Press-and-hold Zoom button ───────────────────────────────────

function ZoomBtn({
  icon, onStart, onStop, connected, title,
}: {
  icon: React.ReactNode
  onStart: () => void
  onStop: () => void
  connected: boolean
  title: string
}) {
  return (
    <button
      onPointerDown={(e) => { e.preventDefault(); onStart() }}
      onPointerUp={(e) => { e.preventDefault(); onStop() }}
      onPointerCancel={(e) => { e.preventDefault(); onStop() }}
      onPointerLeave={(e) => { e.preventDefault(); onStop() }}
      disabled={!connected}
      title={title}
      className={clsx(
        'w-7 h-7 flex items-center justify-center rounded border border-border',
        'text-text-secondary hover:text-text-primary hover:bg-surface-hover',
        'transition-colors disabled:opacity-40 disabled:cursor-not-allowed touch-none select-none',
      )}
    >
      {icon}
    </button>
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
