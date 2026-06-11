import { useCallback, useEffect, useRef, useState } from 'react'
import { clsx } from 'clsx'
import {
  ArrowUp, ArrowDown, ArrowLeft, ArrowRight,
  ZoomIn, ZoomOut, Home, Square,
  Save, Camera, CameraOff, Aperture,
  PictureInPicture2, Maximize2, Minimize2, Circle,
  ChevronDown, ChevronRight,
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

  const motionLabel = (state: MotionState): string => {
    const labels: Record<MotionState, string> = {
      idle: 'idle', moving: 'moving', stopping: 'stopping...',
      blocked: 'blocked', disconnected: 'disconnected',
    }
    return labels[state] || state
  }

  const realOverlays = overlays.filter(o => !o.track_id?.startsWith('diag_'))

  // ── Render ─────────────────────────────────────────────────────

  return (
    <div className={clsx('flex flex-col gap-3', expanded && 'fixed inset-0 z-50 bg-surface p-4')}>
      {/* CAMERA LIVE indicator */}
      {isActive && (
        <div className="flex items-center gap-1.5 px-3 py-2 rounded bg-danger/10 text-danger text-xs font-mono uppercase tracking-wider">
          <span className="w-2 h-2 rounded-full bg-danger animate-pulse" />
          camera live
          {hasPtzHardware ? ' — physical ptz' : ' — digital roi'}
          {ptzMotion.state === 'moving' && (
            <span className="ml-auto text-warning">{motionLabel(ptzMotion.state)}</span>
          )}
        </div>
      )}

      {/* Preview frame — CLEAN. No HUD, no FPS overlay, no debug text. */}
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
            {/* OVR: only real AI overlays. DIAG synthetic boxes handled by VisionOverlay internally. */}
            <VisionOverlay
              overlays={overlays}
              width={width || 1280}
              height={height || 720}
              visible={overlayVisible}
            />
          </>
        ) : (
          <div className="flex flex-col items-center justify-center w-full h-full text-text-tertiary min-h-[180px] gap-3 px-4">
            {cameraStatus === 'connecting' ? (
              <>
                <Camera size={32} className="opacity-50 animate-pulse" />
                <span className="text-xs font-mono uppercase tracking-wider text-text-quaternary">Connecting to camera...</span>
              </>
            ) : connected ? (
              <>
                <Camera size={32} className="opacity-30" />
                <button
                  onClick={handleStart}
                  className="px-6 py-3 rounded-lg bg-ok/10 text-ok text-sm font-mono uppercase tracking-wider hover:bg-ok/20 active:bg-ok/30 transition-colors"
                >
                  Tap to Start Camera
                </button>
                {!chainHealth.beastConnected && (
                  <span className="text-[11px] font-mono text-danger text-center">Beast offline — camera may not respond.</span>
                )}
              </>
            ) : (
              <>
                <Camera size={32} className="opacity-20" />
                <span className="text-xs font-mono text-text-quaternary text-center">Connecting to vision relay...</span>
              </>
            )}
          </div>
        )}

        {/* Minimal top-left: expand + pop-out only */}
        <div className="absolute top-1 left-1 flex items-center gap-1">
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-1.5 rounded bg-black/60 text-text-secondary hover:text-white"
            title={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
          <button
            onClick={openPopout}
            className="p-1.5 rounded bg-black/60 text-text-secondary hover:text-white"
            title="Pop out"
          >
            <PictureInPicture2 size={14} />
          </button>
        </div>
      </div>

      {/* Primary action buttons — large for mobile */}
      <div className="flex items-center gap-2">
        {!isActive ? (
          <MobileBtn icon={<Camera size={18} />} label="Start" onClick={handleStart} disabled={!connected} variant="ok" />
        ) : (
          <MobileBtn icon={<CameraOff size={18} />} label="Stop" onClick={handleStop} variant="danger" />
        )}
        <MobileBtn icon={<Aperture size={18} />} label="Snap" onClick={handleSnapshot} disabled={!connected} variant="cyan" />
        <MobileBtn icon={<Square size={18} />} label="E-Stop" onClick={handleEmergencyStop} variant="danger" />
      </div>

      {/* OVR / DIAG toggles — below camera, not on it */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setOverlayVisible(!overlayVisible)}
          className={clsx(
            'flex-1 py-2.5 rounded text-xs font-mono text-center transition-colors flex flex-col items-center gap-0.5',
            overlayVisible
              ? 'bg-ok/20 text-ok border border-ok/30'
              : 'bg-surface-hover text-text-tertiary border border-transparent',
          )}
          title="OVR = real AI object detection overlays only"
        >
          <span className="uppercase tracking-wider">OVR {overlayVisible ? 'on' : 'off'}</span>
          <span className="text-[9px] opacity-70 normal-case">real detections only</span>
        </button>
        <button
          onClick={() => {
            const next = !diagnosticOverlay
            setDiagnosticOverlay(next)
            getVisionClient()?.setDiagnosticOverlay(next)
          }}
          className={clsx(
            'flex-1 py-2.5 rounded text-xs font-mono text-center transition-colors flex flex-col items-center gap-0.5',
            diagnosticOverlay
              ? 'bg-warning/20 text-warning border border-warning/30'
              : 'bg-surface-hover text-text-tertiary border border-transparent',
          )}
          title="DIAG = synthetic test boxes for pipeline verification only"
        >
          <span className="uppercase tracking-wider">DIAG {diagnosticOverlay ? 'on' : 'off'}</span>
          <span className="text-[9px] opacity-70 normal-case">synthetic test boxes</span>
        </button>
      </div>

      {/* Pipeline status — below camera, not over it */}
      <PipelineStatus
        connected={connected}
        streaming={streaming}
        streamMetrics={streamMetrics}
        chainHealth={chainHealth}
        error={error}
      />

      {/* Object tracking status */}
      <TrackerStatus
        overlays={realOverlays}
        overlayVisible={overlayVisible}
        diagnosticOverlay={diagnosticOverlay}
        chainHealth={chainHealth}
      />

      {!compact && (
        <>
          {/* PTZ Controls — mobile-sized */}
          <div className="flex flex-col gap-3">
            <div className="flex items-start gap-4 justify-center">
              {/* D-pad — 56px buttons */}
              <div className="flex flex-col items-center gap-1">
                <span className="text-[10px] font-mono text-text-tertiary uppercase tracking-wider">
                  {hasPtzHardware ? 'PTZ' : 'ROI'}
                </span>
                <div className="grid grid-cols-3 gap-1 w-fit">
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
                <MobileBtn icon={<Home size={16} />} label="Home" onClick={handlePtzHome} disabled={!controlsEnabled} variant="cyan" />
              </div>

              {/* Joystick — 160px diameter */}
              <div className="flex flex-col items-center gap-1">
                <span className="text-[10px] font-mono text-text-tertiary uppercase tracking-wider">Joystick</span>
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
                  className={clsx(
                    'w-40 h-40 rounded-full border-2 relative cursor-crosshair select-none',
                    controlsEnabled ? 'border-border bg-surface-hover' : 'border-border/50 bg-surface-hover/50 opacity-50',
                  )}
                  style={{ touchAction: 'none', userSelect: 'none', WebkitUserSelect: 'none' }}
                >
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="absolute w-px h-full bg-border/30" />
                    <div className="absolute h-px w-full bg-border/30" />
                    <Circle size={8} className="text-text-quaternary" />
                  </div>
                  <div
                    className={clsx(
                      'absolute w-8 h-8 rounded-full border-2 transition-colors',
                      joystickDragging.current || ptzMotion.state === 'moving'
                        ? 'bg-cyan/80 border-cyan shadow-[0_0_12px_rgba(34,211,238,0.5)]'
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
                  <span className="text-[10px] font-mono text-cyan">
                    {joystickVelocity.current.pan.toFixed(2)}, {joystickVelocity.current.tilt.toFixed(2)}
                  </span>
                )}
              </div>

              {/* Zoom — tall buttons */}
              <div className="flex flex-col items-center gap-1">
                <span className="text-[10px] font-mono text-text-tertiary uppercase tracking-wider">Zoom</span>
                <div className="flex flex-col gap-1">
                  <ZoomBtn icon={<ZoomIn size={20} />} onStart={() => startZoomMotion(1)} onStop={stopZoomMotion} connected={controlsEnabled} title="Zoom in" />
                  <ZoomBtn icon={<ZoomOut size={20} />} onStart={() => startZoomMotion(-1)} onStop={stopZoomMotion} connected={controlsEnabled} title="Zoom out" />
                </div>
              </div>
            </div>

            {/* Position readout */}
            <div className="flex items-center justify-center gap-4 text-xs font-mono text-text-tertiary">
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
            <span className="text-[10px] font-mono text-text-tertiary uppercase tracking-wider w-12">Speed</span>
            <input
              type="range"
              min={0.2}
              max={3}
              step={0.1}
              value={speed}
              onChange={(e) => setSpeed(parseFloat(e.target.value))}
              className="flex-1 accent-cyan h-2"
            />
            <span className="text-xs font-mono text-text-tertiary w-10 text-right">{speed.toFixed(1)}x</span>
          </div>

          {/* Quality mode selector — larger buttons */}
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] font-mono text-text-tertiary uppercase tracking-wider">Stream Quality</span>
            <div className="flex gap-1">
              {(Object.keys(QUALITY_PROFILES) as QualityMode[]).map((mode) => (
                <button
                  key={mode}
                  onClick={() => handleQualityChange(mode)}
                  className={clsx(
                    'flex-1 px-2 py-2.5 rounded text-xs font-mono uppercase tracking-wider transition-colors text-center',
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

          {/* Presets — larger buttons */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-text-tertiary uppercase tracking-wider">Presets</span>
              <button
                onClick={() => setSavingPreset(!savingPreset)}
                className="flex items-center gap-1 text-[10px] font-mono text-text-tertiary hover:text-text-primary uppercase tracking-wider transition-colors"
              >
                <Save size={12} />
                Save
              </button>
            </div>

            <div className="flex flex-wrap gap-1">
              {Object.entries(presets).map(([name, preset]) => (
                <button
                  key={name}
                  onClick={() => handlePreset(name)}
                  disabled={!connected}
                  className={clsx(
                    'px-3 py-2 rounded text-xs font-mono uppercase tracking-wider transition-colors',
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
                  placeholder="Slug"
                  className="flex-1 px-2 py-1.5 rounded bg-surface border border-border text-xs font-mono text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-cyan/50"
                />
                <input
                  type="text"
                  value={newPresetLabel}
                  onChange={(e) => setNewPresetLabel(e.target.value)}
                  placeholder="Label"
                  className="flex-1 px-2 py-1.5 rounded bg-surface border border-border text-xs font-mono text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-cyan/50"
                />
                <button
                  onClick={handleSavePreset}
                  disabled={!newPresetName.trim()}
                  className="px-3 py-1.5 rounded bg-cyan/10 text-cyan text-xs font-mono uppercase tracking-wider hover:bg-cyan/20 disabled:opacity-50"
                >
                  Save
                </button>
              </div>
            )}
          </div>

          {/* Collapsible diagnostics — NOT on the camera view */}
          <DiagnosticsPanel
            ptzMotion={ptzMotion}
            controlMetrics={controlMetrics}
            joystickDragging={joystickDragging.current}
            joystickVelocity={joystickVelocity.current}
            speed={speed}
            overlays={overlays}
            overlayVisible={overlayVisible}
            diagnosticOverlay={diagnosticOverlay}
            connected={connected}
            streaming={streaming}
            streamMetrics={streamMetrics}
            frameCount={frameCount}
            qualityMode={qualityMode}
          />

          {/* Tracking / Scene Intelligence */}
          <div className="border-t border-border pt-3">
            <TrackingPanel />
          </div>
        </>
      )}

      {/* Connection status bar */}
      <div className="flex items-center gap-2 text-xs font-mono text-text-tertiary">
        <span className={clsx(
          'w-2 h-2 rounded-full',
          connected ? 'bg-ok' : 'bg-danger',
        )} />
        {connected ? 'vision relay connected' : 'vision relay disconnected'}
      </div>

      {error && (
        <div className="px-3 py-2 rounded bg-danger/10 text-danger text-xs font-mono">
          {error}
        </div>
      )}
    </div>
  )
}

// ── Pipeline Status — below camera, NOT over it ───────────────────

function PipelineStatus({
  connected, streaming, streamMetrics, chainHealth, error,
}: {
  connected: boolean
  streaming: boolean
  streamMetrics: StreamMetrics
  chainHealth: ReturnType<typeof useVisionStore.getState>['chainHealth']
  error: string | null
}) {
  const frameAge = streamMetrics.lastFrameAge
  const frameFresh = frameAge > 0 && frameAge < 3000

  return (
    <div className="flex flex-col gap-1 px-3 py-2 rounded border border-border bg-surface-hover/50 text-xs font-mono">
      {/* Status chain as dots */}
      <div className="flex items-center gap-3 flex-wrap">
        <StatusDot ok={connected} label={connected ? 'relay' : 'relay down'} />
        <StatusDot ok={chainHealth.beastConnected} label={chainHealth.beastConnected ? 'beast' : 'beast offline'} />
        <StatusDot ok={chainHealth.cameraStreaming} label={chainHealth.cameraStreaming ? 'camera' : 'cam off'} />
        <StatusDot ok={streaming && frameFresh} label={streaming ? (frameFresh ? 'streaming' : 'stale') : 'no stream'} />
        {streaming && (
          <span className="text-text-tertiary">
            {streamMetrics.actualFps.toFixed(1)} fps
          </span>
        )}
      </div>

      {/* Blocker explanation */}
      {!chainHealth.beastConnected && connected && (
        <span className="text-danger text-[11px]">Beast PC not on mesh — camera, PTZ, and detection unavailable.</span>
      )}
      {chainHealth.beastConnected && !chainHealth.cameraStreaming && connected && (
        <span className="text-warning text-[11px]">Camera not streaming — press Start.</span>
      )}
      {streaming && !frameFresh && frameAge > 5000 && chainHealth.beastConnected && (
        <span className="text-danger text-[11px]">Frames stale ({(frameAge / 1000).toFixed(1)}s) — Beast may have stopped sending.</span>
      )}
    </div>
  )
}

function StatusDot({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={clsx('flex items-center gap-1', ok ? 'text-ok' : 'text-text-quaternary')}>
      <span className={clsx('w-1.5 h-1.5 rounded-full', ok ? 'bg-ok' : 'bg-danger')} />
      {label}
    </span>
  )
}

// ── Detector Inventory — honest about what's actually running ──

function TrackerStatus({
  overlays, overlayVisible, diagnosticOverlay, chainHealth,
}: {
  overlays: import('./vision/VisionOverlay').OverlayMetadata[]
  overlayVisible: boolean
  diagnosticOverlay: boolean
  chainHealth: ReturnType<typeof useVisionStore.getState>['chainHealth']
}) {
  const beastOnline = chainHealth.beastConnected
  const hasRealDetections = overlays.length > 0 && chainHealth.lastOverlayAt > 0
  const uniqueLabels = [...new Set(overlays.map(o => o.label))]

  return (
    <div className="px-3 py-2 rounded border border-border bg-surface-hover/50 text-xs font-mono flex flex-col gap-2">
      <span className="text-text-tertiary uppercase tracking-wider text-[10px]">Detector Status</span>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
        <span className="text-text-quaternary">backend:</span>
        <span className={beastOnline ? 'text-ok' : 'text-danger'}>
          {beastOnline ? 'Beast (connected)' : 'none — Beast offline'}
        </span>

        <span className="text-text-quaternary">ML model:</span>
        <span className={hasRealDetections ? 'text-ok' : 'text-warning'}>
          {hasRealDetections ? 'producing detections' : 'not running'}
        </span>

        <span className="text-text-quaternary">detections:</span>
        <span className={hasRealDetections ? 'text-ok' : 'text-text-quaternary'}>
          {hasRealDetections ? `${overlays.length} objects` : '0'}
        </span>

        <span className="text-text-quaternary">last detection:</span>
        <span className="text-text-secondary">
          {chainHealth.lastOverlayAt > 0
            ? `${Math.round((Date.now() - chainHealth.lastOverlayAt) / 1000)}s ago`
            : 'never'}
        </span>
      </div>

      {/* Live detections from real ML model */}
      {hasRealDetections && (
        <div className="flex flex-col gap-0.5 border-t border-border/50 pt-1.5">
          <span className="text-text-quaternary text-[10px] uppercase tracking-wider">Live Detections</span>
          {overlays.slice(0, 8).map((o) => (
            <div key={o.track_id} className="flex items-center gap-2 text-[11px] text-text-secondary">
              <span className="w-2 h-2 rounded-sm" style={{ background: o.color || '#22c55e' }} />
              <span>{o.label}</span>
              <span className="text-text-quaternary">{(o.confidence * 100).toFixed(0)}%</span>
              <span className="text-text-quaternary text-[9px]">#{o.track_id.slice(-6)}</span>
            </div>
          ))}
          {overlays.length > 8 && (
            <span className="text-text-quaternary text-[10px]">+{overlays.length - 8} more</span>
          )}
          {uniqueLabels.length > 0 && (
            <span className="text-text-quaternary text-[10px]">classes: {uniqueLabels.join(', ')}</span>
          )}
        </div>
      )}

      {/* Honest status — no false claims */}
      {!beastOnline && (
        <div className="text-danger text-[11px] border-t border-border/50 pt-1.5">
          Object detection unavailable — Beast offline.
        </div>
      )}
      {beastOnline && !hasRealDetections && (
        <div className="text-warning text-[11px] border-t border-border/50 pt-1.5">
          No ML detector running. Object detection (keyboard, chair, desk, etc.) requires a model to be loaded on Beast.</div>
      )}
      {hasRealDetections && overlays.length === 0 && (
        <div className="text-text-tertiary text-[11px] border-t border-border/50 pt-1.5">
          Detector active — no objects in current frame.
        </div>
      )}
    </div>
  )
}

// ── D-pad button — 56px for mobile ──────────────────────────────────

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
    up: <ArrowUp size={20} />,
    down: <ArrowDown size={20} />,
    left: <ArrowLeft size={20} />,
    right: <ArrowRight size={20} />,
    stop: <div className="w-3 h-3 rounded-full bg-current" />,
  }
  return (
    <button
      onPointerDown={(e) => { e.preventDefault(); onStart() }}
      onPointerUp={(e) => { e.preventDefault(); if (!isStop) onStop() }}
      onPointerCancel={(e) => { e.preventDefault(); if (!isStop) onStop() }}
      onPointerLeave={(e) => { e.preventDefault(); if (!isStop) onStop() }}
      onTouchStart={(e) => { e.stopPropagation(); e.preventDefault(); onStart() }}
      onTouchEnd={(e) => { e.stopPropagation(); e.preventDefault(); if (!isStop) onStop() }}
      onTouchCancel={(e) => { e.stopPropagation(); e.preventDefault(); if (!isStop) onStop() }}
      disabled={!connected}
      title={`Pan ${direction}`}
      className={clsx(
        'w-14 h-14 flex items-center justify-center rounded-lg border border-border',
        'text-text-secondary hover:text-text-primary hover:bg-surface-hover',
        'transition-colors disabled:opacity-40 disabled:cursor-not-allowed touch-none select-none',
        'active:bg-cyan/20 active:border-cyan/50',
        isStop && 'bg-surface-hover',
      )}
      style={{ touchAction: 'none' }}
    >
      {icons[direction]}
    </button>
  )
}

// ── Zoom button — tall for mobile ───────────────────────────────────

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
      onTouchStart={(e) => { e.stopPropagation(); e.preventDefault(); onStart() }}
      onTouchEnd={(e) => { e.stopPropagation(); e.preventDefault(); onStop() }}
      onTouchCancel={(e) => { e.stopPropagation(); e.preventDefault(); onStop() }}
      disabled={!connected}
      title={title}
      className={clsx(
        'w-14 h-16 flex items-center justify-center rounded-lg border border-border',
        'text-text-secondary hover:text-text-primary hover:bg-surface-hover',
        'transition-colors disabled:opacity-40 disabled:cursor-not-allowed touch-none select-none',
        'active:bg-cyan/20 active:border-cyan/50',
      )}
      style={{ touchAction: 'none' }}
    >
      {icon}
    </button>
  )
}

// ── Mobile-friendly primary button ──────────────────────────────────

function MobileBtn({
  icon, label, onClick, disabled, variant,
}: {
  icon: React.ReactNode
  label: string
  onClick: () => void
  disabled?: boolean
  variant: 'ok' | 'danger' | 'cyan'
}) {
  const colors = {
    ok: 'bg-ok/10 text-ok hover:bg-ok/20 active:bg-ok/30',
    danger: 'bg-danger/10 text-danger hover:bg-danger/20 active:bg-danger/30',
    cyan: 'bg-cyan/10 text-cyan hover:bg-cyan/20 active:bg-cyan/30',
  }
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        'flex items-center justify-center gap-1.5 flex-1 py-3 rounded-lg text-sm font-mono uppercase tracking-wider transition-colors',
        disabled ? 'bg-surface text-text-tertiary cursor-not-allowed' : colors[variant],
      )}
    >
      {icon}
      {label}
    </button>
  )
}

// ── Collapsible diagnostics panel — separate from camera ────────────

function DiagnosticsPanel({
  ptzMotion, controlMetrics, joystickDragging, joystickVelocity,
  speed, overlays, overlayVisible, diagnosticOverlay, connected,
  streaming, streamMetrics, frameCount, qualityMode,
}: {
  ptzMotion: { state: MotionState; motionId: string; panVelocity: number; tiltVelocity: number; zoomVelocity: number }
  controlMetrics: { ptzLoopCadenceHz: number; stopLatencyMs: number; guardTimeouts: number; lastCommandSentAt: number; coalescedCommands: number; lastStopSentAt: number }
  joystickDragging: boolean
  joystickVelocity: { pan: number; tilt: number }
  speed: number
  overlays: unknown[]
  overlayVisible: boolean
  diagnosticOverlay: boolean
  connected: boolean
  streaming: boolean
  streamMetrics: StreamMetrics
  frameCount: number
  qualityMode: QualityMode
}) {
  const chainHealth = useVisionStore((s) => s.chainHealth)
  const trackerStack = useVisionStore((s) => s.trackerStack)
  const [expanded, setExpanded] = useState(false)

  const enabledTrackers = trackerStack.enabled_trackers.filter((t) => t.enabled)

  return (
    <div className="border-t border-border pt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-[10px] font-mono text-text-quaternary hover:text-text-secondary uppercase tracking-wider w-full"
      >
        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        Diagnostics
        {ptzMotion.state !== 'idle' ? ` [${ptzMotion.state}]` : ''}
        {overlays.length > 0 ? ` [${overlays.length} ovr]` : ''}
      </button>

      {expanded && (
        <div className="mt-2 flex flex-col gap-2">
          {/* Stream metrics */}
          <div className="grid grid-cols-3 gap-x-4 gap-y-1 text-[10px] font-mono text-text-tertiary">
            <span>FPS: <span className={streamMetrics.actualFps > 0 ? 'text-ok' : 'text-text-secondary'}>{streamMetrics.actualFps.toFixed(1)}</span> / {streamMetrics.targetFps}</span>
            <span>Frame: {Math.round(streamMetrics.avgFrameSize / 1024)} KB</span>
            <span>Age: {streamMetrics.lastFrameAge < 1000 ? `${streamMetrics.lastFrameAge}ms` : `${(streamMetrics.lastFrameAge / 1000).toFixed(1)}s`}</span>
            <span>Frames: {frameCount}</span>
            <span>Dropped: {streamMetrics.droppedFrames}</span>
            <span>Quality: {QUALITY_DESCRIPTIONS[qualityMode]}</span>
          </div>

          {/* PTZ state */}
          <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[9px] font-mono text-text-quaternary border border-dashed border-border/50 rounded p-2">
            <span>joystick: <span className={joystickDragging ? 'text-cyan' : ''}>{joystickDragging ? 'DRAGGING' : 'idle'}</span></span>
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
            <span>last_cmd: {controlMetrics.lastCommandSentAt > 0
              ? `${Math.round((Date.now() - controlMetrics.lastCommandSentAt) / 1000)}s ago`
              : '—'}</span>
            <span>ws: {connected ? 'connected' : 'DISCONNECTED'}</span>
            <span>update_rate: 50ms</span>
          </div>

          {/* Chain health */}
          <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[9px] font-mono text-text-quaternary border border-dashed border-warning/30 rounded p-2">
            <span>overlay_visible: <span className={overlayVisible ? 'text-ok' : 'text-danger'}>{overlayVisible ? 'ON' : 'OFF'}</span></span>
            <span>diagnostic_mode: <span className={diagnosticOverlay ? 'text-warning' : ''}>{diagnosticOverlay ? 'ON' : 'off'}</span></span>
            <span>overlay_count: <span className={overlays.length > 0 ? 'text-ok' : ''}>{overlays.length}</span></span>
            <span>last_overlay: {chainHealth.lastOverlayAt > 0 ? `${Math.round((Date.now() - chainHealth.lastOverlayAt) / 1000)}s ago` : 'never'}</span>
            <span>tracker_runtime: <span className={chainHealth.trackerRuntimeAvailable ? 'text-ok' : 'text-danger'}>{chainHealth.trackerRuntimeAvailable ? 'available' : 'UNAVAILABLE'}</span></span>
            <span>enabled_trackers: {enabledTrackers.length > 0 ? enabledTrackers.map((t) => t.category).join(', ') : 'none'}</span>
            <span>beast: <span className={chainHealth.beastConnected ? 'text-ok' : 'text-danger'}>{chainHealth.beastConnected ? 'connected' : 'OFFLINE'}</span></span>
            <span>camera: <span className={chainHealth.cameraStreaming ? 'text-ok' : 'text-danger'}>{chainHealth.cameraStreaming ? 'streaming' : chainHealth.cameraAvailable ? 'available' : 'UNAVAILABLE'}</span></span>
          </div>

          {/* Blockers */}
          {chainHealth.blockers.length > 0 && (
            <div className="text-[9px] font-mono text-danger/80 bg-danger/5 rounded p-1.5">
              {chainHealth.blockers.map((b, i) => <div key={i}>{b}</div>)}
              {chainHealth.recoveryAction && (
                <div className="text-warning/80 mt-0.5">{chainHealth.recoveryAction}</div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
