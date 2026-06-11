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
  type StreamMetrics,
  type ControlMetrics,
} from '../stores/visionStore'
import { getVisionClient } from '../hooks/useVisionConnection'
import { useVisionPopout } from './VisionPopout'
import { TrackingPanel } from './TrackingPanel'
import { VisionOverlay } from './vision'

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
  const overlays = useVisionStore((s) => s.overlays)
  const chainHealth = useVisionStore((s) => s.chainHealth)
  const controlsEnabled = connected && chainHealth.beastConnected
  const overlayVisible = useVisionStore((s) => s.overlayVisible)
  const setOverlayVisible = useVisionStore((s) => s.setOverlayVisible)
  const diagnosticOverlay = useVisionStore((s) => s.diagnosticOverlay)
  const setDiagnosticOverlay = useVisionStore((s) => s.setDiagnosticOverlay)
  const width = useVisionStore((s) => s.width)
  const height = useVisionStore((s) => s.height)
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
  const [thumbPos, setThumbPos] = useState({ x: 0, y: 0 })

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

  const ensureUpdateTimer = useCallback(() => {
    if (motionUpdateTimerRef.current) return
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
  }, [speed])

  const startDirectionMotion = useCallback((panV: number, tiltV: number) => {
    const client = getVisionClient()
    if (!client?.connected) return
    if (!useVisionStore.getState().chainHealth.beastConnected) return

    if (activeMotionIdRef.current) {
      client.ptzStopMotion(activeMotionIdRef.current)
      if (motionUpdateTimerRef.current) {
        clearInterval(motionUpdateTimerRef.current)
        motionUpdateTimerRef.current = null
      }
    }

    const motionId = nextMotionId()
    activeMotionIdRef.current = motionId
    joystickVelocity.current = { pan: panV, tilt: tiltV }
    client.ptzStartMotion({
      motionId,
      panVelocity: panV,
      tiltVelocity: tiltV,
      speed,
      durationGuardMs: 3000,
    })
    setPtzMotion({ state: 'moving', motionId, panVelocity: panV, tiltVelocity: tiltV, zoomVelocity: 0, speed })
    setPtzMoving(true)
    updateControlMetrics({ lastCommandSentAt: Date.now() })
    ensureUpdateTimer()
  }, [speed, setPtzMotion, setPtzMoving, updateControlMetrics, ensureUpdateTimer])

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
    if (!useVisionStore.getState().chainHealth.beastConnected) return

    if (activeMotionIdRef.current) {
      client.ptzStopMotion(activeMotionIdRef.current)
      if (motionUpdateTimerRef.current) {
        clearInterval(motionUpdateTimerRef.current)
        motionUpdateTimerRef.current = null
      }
    }

    const motionId = nextMotionId()
    activeMotionIdRef.current = motionId
    joystickVelocity.current = { pan: 0, tilt: 0 }
    client.zoomStartMotion(motionId, zoomV, speed)
    setPtzMotion({ state: 'moving', motionId, panVelocity: 0, tiltVelocity: 0, zoomVelocity: zoomV, speed })
    setPtzMoving(true)
    updateControlMetrics({ lastCommandSentAt: Date.now() })
    if (!motionUpdateTimerRef.current) {
      motionUpdateTimerRef.current = setInterval(() => {
        const c = getVisionClient()
        const mid = activeMotionIdRef.current
        if (!c?.connected || !mid) return
        c.zoomUpdateMotion(mid, zoomV, speed)
      }, MOTION_UPDATE_INTERVAL_MS)
    }
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
    if (motionUpdateTimerRef.current) {
      clearInterval(motionUpdateTimerRef.current)
      motionUpdateTimerRef.current = null
    }
  }, [setPtzMotion, setPtzMoving, updateControlMetrics])

  // ── Joystick drag ──────────────────────────────────────────────


  // iOS Safari does not reliably fire Pointer Events when an ancestor has
  // overflow-y-auto (the scroll container intercepts touch). We therefore
  // also attach Touch event handlers as a parallel path.  Both paths call
  // the same internal helpers so motion behaviour is identical.

  const computeJoystickVectorFromClient = useCallback((clientX: number, clientY: number) => {
    const el = joystickRef.current
    if (!el) return { dx: 0, dy: 0, panV: 0, tiltV: 0 }
    const rect = el.getBoundingClientRect()
    const radius = rect.width / 2
    const cx = rect.left + radius
    const cy = rect.top + radius
    let dx = (clientX - cx) / radius
    let dy = -(clientY - cy) / radius
    const dist = Math.sqrt(dx * dx + dy * dy)
    if (dist > 1) { dx /= dist; dy /= dist }
    const panV = Math.abs(dx) > JOYSTICK_DEADZONE ? dx : 0
    const tiltV = Math.abs(dy) > JOYSTICK_DEADZONE ? dy : 0
    return { dx, dy, panV, tiltV }
  }, [])

  const handleJoystickPointerDown = useCallback((e: React.PointerEvent) => {
    const el = joystickRef.current
    if (!el) return
    e.preventDefault()
    // Pointer capture allows tracking outside the element
    try { el.setPointerCapture(e.pointerId) } catch { /* Safari may throw */ }
    joystickDragging.current = true

    const { dx, dy, panV, tiltV } = computeJoystickVectorFromClient(e.clientX, e.clientY)
    setThumbPos({ x: dx, y: -dy })
    joystickVelocity.current = { pan: panV, tilt: tiltV }

    if (Math.abs(panV) > 0 || Math.abs(tiltV) > 0) {
      startDirectionMotion(panV, tiltV)
    }
  }, [startDirectionMotion, computeJoystickVectorFromClient])

  const handleJoystickPointerMove = useCallback((e: React.PointerEvent) => {
    if (!joystickDragging.current) return
    e.preventDefault()

    const { dx, dy, panV, tiltV } = computeJoystickVectorFromClient(e.clientX, e.clientY)
    setThumbPos({ x: dx, y: -dy })
    joystickVelocity.current = { pan: panV, tilt: tiltV }

    if (!activeMotionIdRef.current && (Math.abs(panV) > 0 || Math.abs(tiltV) > 0)) {
      startDirectionMotion(panV, tiltV)
    }
  }, [startDirectionMotion, computeJoystickVectorFromClient])

  const handleJoystickPointerUp = useCallback((e: React.PointerEvent) => {
    const el = joystickRef.current
    if (el) {
      try { el.releasePointerCapture(e.pointerId) } catch { /* already released */ }
    }
    joystickDragging.current = false
    joystickVelocity.current = { pan: 0, tilt: 0 }
    setThumbPos({ x: 0, y: 0 })
    stopDirectionMotion()
  }, [stopDirectionMotion])

  // ── Touch fallback for iOS Safari ─────────────────────────────────
  // Runs in parallel with pointer events. On iOS Safari the scroll
  // container's touchstart fires first; preventDefault() here stops
  // the page from scrolling and lets us handle the gesture.

  const handleJoystickTouchStart = useCallback((e: React.TouchEvent) => {
    e.stopPropagation()
    e.preventDefault()
    const t = e.touches[0]
    if (!t) return
    joystickDragging.current = true
    const { dx, dy, panV, tiltV } = computeJoystickVectorFromClient(t.clientX, t.clientY)
    setThumbPos({ x: dx, y: -dy })
    joystickVelocity.current = { pan: panV, tilt: tiltV }
    if (Math.abs(panV) > 0 || Math.abs(tiltV) > 0) {
      startDirectionMotion(panV, tiltV)
    }
  }, [startDirectionMotion, computeJoystickVectorFromClient])

  const handleJoystickTouchMove = useCallback((e: React.TouchEvent) => {
    e.stopPropagation()
    e.preventDefault()
    const t = e.touches[0]
    if (!t || !joystickDragging.current) return
    const { dx, dy, panV, tiltV } = computeJoystickVectorFromClient(t.clientX, t.clientY)
    setThumbPos({ x: dx, y: -dy })
    joystickVelocity.current = { pan: panV, tilt: tiltV }
    if (!activeMotionIdRef.current && (Math.abs(panV) > 0 || Math.abs(tiltV) > 0)) {
      startDirectionMotion(panV, tiltV)
    }
  }, [startDirectionMotion, computeJoystickVectorFromClient])

  const handleJoystickTouchEnd = useCallback((e: React.TouchEvent) => {
    e.stopPropagation()
    e.preventDefault()
    joystickDragging.current = false
    joystickVelocity.current = { pan: 0, tilt: 0 }
    setThumbPos({ x: 0, y: 0 })
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
          <>
            <img
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

        {/* Operator HUD: always-visible pipeline health overlay */}
        <VisionHud
          connected={connected}
          streaming={streaming}
          streamMetrics={streamMetrics}
          overlayCount={overlays.length}
          ptzMotion={ptzMotion}
          controlMetrics={controlMetrics}
          error={error}
        />

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
          <button
            onClick={() => setOverlayVisible(!overlayVisible)}
            className={clsx(
              'px-1.5 py-0.5 rounded text-[9px] font-mono uppercase tracking-wider',
              overlayVisible
                ? 'bg-ok/30 text-ok'
                : 'bg-black/60 text-text-tertiary hover:text-white',
            )}
            title={overlayVisible ? 'Hide overlays' : 'Show overlays'}
          >
            OVR
          </button>
          <button
            onClick={() => {
              const next = !diagnosticOverlay
              setDiagnosticOverlay(next)
              getVisionClient()?.setDiagnosticOverlay(next)
            }}
            className={clsx(
              'px-1.5 py-0.5 rounded text-[9px] font-mono uppercase tracking-wider',
              diagnosticOverlay
                ? 'bg-warning/30 text-warning'
                : 'bg-black/60 text-text-tertiary hover:text-white',
            )}
            title={diagnosticOverlay ? 'Disable diagnostic overlay' : 'Enable diagnostic overlay'}
          >
            DIAG
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
                <DpadBtn direction="up" onStart={() => startDirectionMotion(0, 1)} onStop={stopDirectionMotion} connected={controlsEnabled} />
                <div />
                <DpadBtn direction="left" onStart={() => startDirectionMotion(-1, 0)} onStop={stopDirectionMotion} connected={controlsEnabled} />
                <DpadBtn direction="stop" onStart={handleEmergencyStop} onStop={() => {}} connected={controlsEnabled} isStop />
                <DpadBtn direction="right" onStart={() => startDirectionMotion(1, 0)} onStop={stopDirectionMotion} connected={controlsEnabled} />
                <div />
                <DpadBtn direction="down" onStart={() => startDirectionMotion(0, -1)} onStop={stopDirectionMotion} connected={controlsEnabled} />
                <div />
              </div>
              <div className="flex gap-1 mt-1">
                <PtzBtn icon={<Home size={12} />} onClick={handlePtzHome} title="Home / Center" />
              </div>
            </div>

            {/* Joystick area — true draggable thumbstick */}
            <div className="flex flex-col items-center gap-1">
              <span className="text-[9px] font-mono text-text-tertiary uppercase tracking-wider">Joystick</span>
              <div
                ref={joystickRef}
                onPointerDown={handleJoystickPointerDown}
                onPointerMove={handleJoystickPointerMove}
                onPointerUp={handleJoystickPointerUp}
                onPointerCancel={handleJoystickPointerUp}
                onPointerLeave={handleJoystickPointerUp}
                onTouchStart={handleJoystickTouchStart}
                onTouchMove={handleJoystickTouchMove}
                onTouchEnd={handleJoystickTouchEnd}
                onTouchCancel={handleJoystickTouchEnd}
                className="w-20 h-20 rounded-full border-2 border-border bg-surface-hover relative cursor-crosshair select-none"
                style={{ touchAction: 'none', userSelect: 'none', WebkitUserSelect: 'none' }}
              >
                {/* Crosshair guides */}
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="absolute w-px h-full bg-border/30" />
                  <div className="absolute h-px w-full bg-border/30" />
                  <Circle size={6} className="text-text-quaternary" />
                </div>
                {/* Draggable thumbstick */}
                <div
                  className={clsx(
                    'absolute w-5 h-5 rounded-full border-2 transition-colors',
                    joystickDragging.current || ptzMotion.state === 'moving'
                      ? 'bg-cyan/80 border-cyan shadow-[0_0_8px_rgba(34,211,238,0.5)]'
                      : 'bg-text-quaternary/40 border-text-quaternary/60',
                  )}
                  style={{
                    left: `calc(50% + ${thumbPos.x * 35}%)`,
                    top: `calc(50% + ${thumbPos.y * 35}%)`,
                    transform: 'translate(-50%, -50%)',
                    pointerEvents: 'none',
                  }}
                />
              </div>
              {(joystickDragging.current || ptzMotion.state === 'moving') && (
                <span className="text-[8px] font-mono text-cyan">
                  {joystickVelocity.current.pan.toFixed(2)}, {joystickVelocity.current.tilt.toFixed(2)}
                </span>
              )}
            </div>

            {/* Zoom (press-and-hold) */}
            <div className="flex flex-col items-center gap-1">
              <span className="text-[9px] font-mono text-text-tertiary uppercase tracking-wider">Zoom</span>
              <div className="flex flex-col gap-0.5">
                <ZoomBtn icon={<ZoomIn size={12} />} onStart={() => startZoomMotion(1)} onStop={stopZoomMotion} connected={controlsEnabled} title="Zoom in" />
                <ZoomBtn icon={<ZoomOut size={12} />} onStart={() => startZoomMotion(-1)} onStop={stopZoomMotion} connected={controlsEnabled} title="Zoom out" />
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

          {/* Controller diagnostics */}
          {ptzMotion.state !== 'idle' && (
            <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[9px] font-mono text-text-quaternary border border-dashed border-border/50 rounded p-2">
              <span>motion_id: {ptzMotion.motionId || '—'}</span>
              <span>state: <span className={clsx(
                ptzMotion.state === 'moving' && 'text-warning',
                ptzMotion.state === 'blocked' && 'text-danger',
              )}>{ptzMotion.state}</span></span>
              <span>pan_v: {ptzMotion.panVelocity.toFixed(2)}</span>
              <span>tilt_v: {ptzMotion.tiltVelocity.toFixed(2)}</span>
              <span>zoom_v: {ptzMotion.zoomVelocity.toFixed(2)}</span>
              <span>speed: {speed.toFixed(1)}x</span>
              <span>update: {MOTION_UPDATE_INTERVAL_MS}ms interval</span>
              <span>joystick: {joystickDragging.current ? 'dragging' : 'idle'}</span>
              {controlMetrics.lastCommandSentAt > 0 && (
                <span>last_cmd: {Date.now() - controlMetrics.lastCommandSentAt < 2000
                  ? `${Date.now() - controlMetrics.lastCommandSentAt}ms ago`
                  : 'stale'}</span>
              )}
              {controlMetrics.guardTimeouts > 0 && (
                <span className="text-danger">guard_kills: {controlMetrics.guardTimeouts}</span>
              )}
            </div>
          )}

          {/* PTZ + Overlay Diagnostics Panel */}
          <PtzDiagnosticsPanel
            ptzMotion={ptzMotion}
            controlMetrics={controlMetrics}
            joystickDragging={joystickDragging.current}
            joystickVelocity={joystickVelocity.current}
            speed={speed}
            overlays={overlays}
            overlayVisible={overlayVisible}
            diagnosticOverlay={diagnosticOverlay}
            connected={connected}
          />

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
        onStart()
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
      // Touch fallbacks for iOS Safari (scroll container intercepts pointer events)
      onTouchStart={(e) => {
        e.stopPropagation()
        e.preventDefault()
        onStart()
      }}
      onTouchEnd={(e) => {
        e.stopPropagation()
        e.preventDefault()
        if (!isStop) onStop()
      }}
      onTouchCancel={(e) => {
        e.stopPropagation()
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
      style={{ touchAction: 'none' }}
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
      // Touch fallbacks for iOS Safari
      onTouchStart={(e) => { e.stopPropagation(); e.preventDefault(); onStart() }}
      onTouchEnd={(e) => { e.stopPropagation(); e.preventDefault(); onStop() }}
      onTouchCancel={(e) => { e.stopPropagation(); e.preventDefault(); onStop() }}
      disabled={!connected}
      title={title}
      className={clsx(
        'w-7 h-7 flex items-center justify-center rounded border border-border',
        'text-text-secondary hover:text-text-primary hover:bg-surface-hover',
        'transition-colors disabled:opacity-40 disabled:cursor-not-allowed touch-none select-none',
      )}
      style={{ touchAction: 'none' }}
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

function PtzDiagnosticsPanel({
  ptzMotion, controlMetrics, joystickDragging, joystickVelocity,
  speed, overlays, overlayVisible, diagnosticOverlay, connected,
}: {
  ptzMotion: { state: MotionState; motionId: string; panVelocity: number; tiltVelocity: number; zoomVelocity: number }
  controlMetrics: { ptzLoopCadenceHz: number; stopLatencyMs: number; guardTimeouts: number; lastCommandSentAt: number; coalescedCommands: number }
  joystickDragging: boolean
  joystickVelocity: { pan: number; tilt: number }
  speed: number
  overlays: unknown[]
  overlayVisible: boolean
  diagnosticOverlay: boolean
  connected: boolean
}) {
  const chainHealth = useVisionStore((s) => s.chainHealth)
  const trackerStack = useVisionStore((s) => s.trackerStack)
  const [expanded, setExpanded] = useState(false)

  if (!expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        className="text-[9px] font-mono text-text-quaternary hover:text-text-secondary uppercase tracking-wider border-t border-border pt-2"
      >
        PTZ + Overlay Diagnostics {ptzMotion.state !== 'idle' ? `[${ptzMotion.state}]` : ''} {overlays.length > 0 ? `[${overlays.length} ovr]` : ''}
      </button>
    )
  }

  const enabledTrackers = trackerStack.enabled_trackers.filter((t) => t.enabled)

  return (
    <div className="border-t border-border pt-2 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-[9px] font-mono text-text-tertiary uppercase tracking-wider">PTZ + Overlay Diagnostics</span>
        <button onClick={() => setExpanded(false)} className="text-[9px] font-mono text-text-quaternary hover:text-text-secondary">hide</button>
      </div>

      {/* PTZ state */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[9px] font-mono text-text-quaternary border border-dashed border-border/50 rounded p-2">
        <span>joystick: <span className={joystickDragging ? 'text-cyan' : ''}>{joystickDragging ? 'DRAGGING' : 'idle'}</span></span>
        <span>pointer_captured: {joystickDragging ? 'yes' : 'no'}</span>
        <span>vector: {joystickVelocity.pan.toFixed(2)}, {joystickVelocity.tilt.toFixed(2)}</span>
        <span>speed: {speed.toFixed(1)}x</span>
        <span>motion_id: {ptzMotion.motionId || '—'}</span>
        <span>state: <span className={clsx(
          ptzMotion.state === 'moving' && 'text-warning',
          ptzMotion.state === 'blocked' && 'text-danger',
          ptzMotion.state === 'idle' && 'text-ok',
        )}>{ptzMotion.state}</span></span>
        <span>relay_loop: {controlMetrics.ptzLoopCadenceHz > 0 ? `${controlMetrics.ptzLoopCadenceHz}Hz` : 'off'}</span>
        <span>stop_latency: {controlMetrics.stopLatencyMs > 0 ? `${controlMetrics.stopLatencyMs}ms` : '—'}</span>
        <span>guard_kills: <span className={controlMetrics.guardTimeouts > 0 ? 'text-danger' : ''}>{controlMetrics.guardTimeouts}</span></span>
        <span>coalesced: {controlMetrics.coalescedCommands}</span>
        <span>ws: {connected ? 'connected' : 'DISCONNECTED'}</span>
        <span>update_rate: 50ms</span>
      </div>

      {/* Overlay state */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[9px] font-mono text-text-quaternary border border-dashed border-warning/30 rounded p-2">
        <span>overlay_visible: <span className={overlayVisible ? 'text-ok' : 'text-danger'}>{overlayVisible ? 'ON' : 'OFF'}</span></span>
        <span>diagnostic_mode: <span className={diagnosticOverlay ? 'text-warning' : ''}>{diagnosticOverlay ? 'ON' : 'off'}</span></span>
        <span>overlay_count: <span className={overlays.length > 0 ? 'text-ok' : 'text-text-quaternary'}>{overlays.length}</span></span>
        <span>last_overlay: {chainHealth.lastOverlayAt > 0 ? `${Math.round((Date.now() - chainHealth.lastOverlayAt) / 1000)}s ago` : 'never'}</span>
        <span>tracker_runtime: <span className={chainHealth.trackerRuntimeAvailable ? 'text-ok' : 'text-danger'}>{chainHealth.trackerRuntimeAvailable ? 'available' : 'UNAVAILABLE'}</span></span>
        <span>enabled_trackers: {enabledTrackers.length > 0 ? enabledTrackers.map((t) => t.category).join(', ') : 'none'}</span>
        <span>beast: <span className={chainHealth.beastConnected ? 'text-ok' : 'text-danger'}>{chainHealth.beastConnected ? 'connected' : 'OFFLINE'}</span></span>
        <span>camera: <span className={chainHealth.cameraStreaming ? 'text-ok' : 'text-danger'}>{chainHealth.cameraStreaming ? 'streaming' : chainHealth.cameraAvailable ? 'available' : 'UNAVAILABLE'}</span></span>
      </div>

      {/* Overlay blocker explanation */}
      {overlays.length === 0 && (
        <div className="text-[9px] font-mono text-warning/80 bg-warning/5 rounded p-1.5">
          {!overlayVisible
            ? 'Overlays disabled — click OVR to enable'
            : !diagnosticOverlay && !chainHealth.trackerRuntimeAvailable
            ? 'No tracker runtime available on Beast. Enable DIAG overlay to test rendering, or install CV dependencies on Beast node.'
            : !diagnosticOverlay && enabledTrackers.length === 0
            ? 'No trackers enabled. Enable DIAG overlay to test rendering, or enable trackers in Tracking panel below.'
            : diagnosticOverlay
            ? 'DIAG mode ON but no overlays received — check relay WebSocket connection'
            : 'Trackers enabled but no detections yet. Waiting for tracker output...'}
        </div>
      )}
    </div>
  )
}

// ── Operator HUD — always-visible pipeline health overlay ────────────

function VisionHud({
  connected,
  streaming,
  streamMetrics,
  overlayCount,
  ptzMotion,
  controlMetrics,
  error,
}: {
  connected: boolean
  streaming: boolean
  streamMetrics: StreamMetrics
  overlayCount: number
  ptzMotion: { state: MotionState; motionId: string }
  controlMetrics: ControlMetrics
  error: string | null
}) {
  const chainHealth = useVisionStore((s) => s.chainHealth)
  const [, setTick] = useState(0)

  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1000)
    return () => clearInterval(id)
  }, [])

  const wsColor = connected ? '#22c55e' : '#ef4444'
  const beastOk = chainHealth.beastConnected
  const beastColor = beastOk ? '#22c55e' : '#ef4444'
  const camStreaming = chainHealth.cameraStreaming
  const frameAge = streamMetrics.lastFrameAge
  const frameAgeStr = frameAge <= 0
    ? '—'
    : frameAge < 1000
    ? `${frameAge}ms`
    : `${(frameAge / 1000).toFixed(1)}s`
  const frameFresh = frameAge > 0 && frameAge < 3000
  const frameAgeColor = !streaming ? '#888' : frameFresh ? '#22c55e' : frameAge > 5000 ? '#ef4444' : '#f59e0b'

  const lastCmdAgo = controlMetrics.lastCommandSentAt > 0
    ? Date.now() - controlMetrics.lastCommandSentAt
    : -1
  const lastCmdStr = lastCmdAgo < 0 ? '—' : lastCmdAgo < 2000 ? `${lastCmdAgo}ms ago` : `${(lastCmdAgo / 1000).toFixed(0)}s ago`

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 6,
        left: 6,
        right: 6,
        zIndex: 20,
        pointerEvents: 'none',
        fontFamily: '"JetBrains Mono", "Fira Mono", monospace',
        fontSize: 9,
        lineHeight: '14px',
        letterSpacing: '0.03em',
      }}
    >
      <div style={{
        background: 'rgba(0,0,0,0.82)',
        borderRadius: 4,
        padding: '5px 8px',
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
      }}>
        {/* Row 1: connection chain */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ color: wsColor }}>● {connected ? 'relay' : 'RELAY DOWN'}</span>
          <span style={{ color: beastColor }}>● {beastOk ? 'beast' : 'BEAST OFFLINE'}</span>
          <span style={{ color: camStreaming ? '#22c55e' : '#888' }}>● {camStreaming ? 'camera' : 'cam off'}</span>
          {streaming && frameFresh && (
            <span style={{ color: '#22c55e' }}>● stream</span>
          )}
          {streaming && !frameFresh && (
            <span style={{ color: '#ef4444' }}>● STALE</span>
          )}
        </div>

        {/* Row 2: frame metrics */}
        <div style={{ display: 'flex', gap: 8, color: '#888' }}>
          <span style={{ color: frameAgeColor }}>age: {streaming ? frameAgeStr : '—'}</span>
          <span>fps: <span style={{ color: streamMetrics.actualFps > 0 ? '#22c55e' : '#888' }}>{streaming ? streamMetrics.actualFps.toFixed(1) : '—'}</span>/{streamMetrics.targetFps}</span>
          <span style={{ color: overlayCount > 0 ? '#22c55e' : '#555' }}>{overlayCount} ovr</span>
        </div>

        {/* PTZ motion state */}
        {ptzMotion.state !== 'idle' && ptzMotion.state !== 'disconnected' && (
          <div style={{ color: '#f59e0b' }}>ptz: {ptzMotion.state} [{ptzMotion.motionId.slice(-6)}]</div>
        )}

        {/* Last command */}
        {controlMetrics.lastCommandSentAt > 0 && (
          <div style={{ color: '#555' }}>
            cmd: {lastCmdStr}
            {controlMetrics.stopLatencyMs > 0 && ` | ack: ${controlMetrics.stopLatencyMs}ms`}
          </div>
        )}

        {/* Blocker — most important: why things aren't working */}
        {!beastOk && connected && (
          <div style={{ color: '#ef4444', fontSize: 10 }}>
            ▸ Beast PC not on mesh — camera/PTZ/detection unavailable
          </div>
        )}
        {beastOk && !camStreaming && connected && (
          <div style={{ color: '#f59e0b' }}>
            ▸ Camera not streaming — press START
          </div>
        )}
        {streaming && !frameFresh && frameAge > 5000 && beastOk && (
          <div style={{ color: '#ef4444' }}>
            ▸ Frames stale ({frameAgeStr}) — Beast may have stopped sending
          </div>
        )}

        {/* Error */}
        {error && (
          <div style={{ color: '#ef4444', maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            ! {error}
          </div>
        )}
      </div>
    </div>
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
