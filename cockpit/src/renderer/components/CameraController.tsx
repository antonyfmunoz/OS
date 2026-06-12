import { useCallback, useEffect, useRef, useState } from 'react'
import { clsx } from 'clsx'
import {
  ArrowUp, ArrowDown, ArrowLeft, ArrowRight,
  ZoomIn, ZoomOut, Home, Square,
  Camera, CameraOff, Aperture,
  PictureInPicture2, Maximize2, Minimize2, Circle,
  Keyboard, Monitor, BookOpen,
  Trash2, RotateCcw, Pencil, Check, X, Plus,
} from 'lucide-react'
import {
  useVisionStore,
  QUALITY_PROFILES,
  savePresetsToStorage,
  type QualityMode,
  type MotionState,
  type CameraPreset,
} from '../stores/visionStore'
import { getVisionClient } from '../hooks/useVisionConnection'
import { useVisionPopout } from './VisionPopout'
import { TrackingPanel } from './TrackingPanel'
import { VisionOverlay } from './vision'
import { StatusHud } from './vision/StatusHud'
import { CameraModeSelector } from './vision/CameraModeSelector'
import { SceneInventory } from './vision/SceneInventory'
import { DiagnosticsPanel } from './vision/DiagnosticsPanel'
import { ToastContainer } from './vision/ToastContainer'
import { NotificationCenter } from './vision/NotificationCenter'

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

const MOTION_UPDATE_INTERVAL_MS = 33
const JOYSTICK_DEADZONE = 0.12

// Default presets with icons
const DEFAULT_PRESETS = [
  { key: 'home', label: 'Home', icon: <Home size={14} /> },
  { key: 'keyboard', label: 'Keyboard', icon: <Keyboard size={14} /> },
  { key: 'monitor', label: 'Monitor', icon: <Monitor size={14} /> },
  { key: 'desk', label: 'Desk', icon: <BookOpen size={14} /> },
]
const DEFAULT_PRESET_KEYS = new Set(DEFAULT_PRESETS.map((p) => p.key))

export function CameraController({ compact = false }: { compact?: boolean }) {
  const {
    connected, streaming, cameraStatus, latestFrameUrl,
    presets, activePreset, ptzPosition,
    qualityMode, streamMetrics, error, frameCount,
    ptzMotion, controlMetrics,
  } = useVisionStore()
  const overlays = useVisionStore((s) => s.overlays)
  const chainHealth = useVisionStore((s) => s.chainHealth)
  const controlsEnabled = connected && (chainHealth.beastConnected || chainHealth.commandPathReady)
  const overlayVisible = useVisionStore((s) => s.overlayVisible)
  const setOverlayVisible = useVisionStore((s) => s.setOverlayVisible)
  const width = useVisionStore((s) => s.width)
  const height = useVisionStore((s) => s.height)
  const setQualityMode = useVisionStore((s) => s.setQualityMode)
  const setCameraStatus = useVisionStore((s) => s.setCameraStatus)
  const setStreaming = useVisionStore((s) => s.setStreaming)
  const setActivePreset = useVisionStore((s) => s.setActivePreset)
  const setPresets = useVisionStore((s) => s.setPresets)
  const setPtzMoving = useVisionStore((s) => s.setPtzMoving)
  const setPtzMotion = useVisionStore((s) => s.setPtzMotion)
  const updateControlMetrics = useVisionStore((s) => s.updateControlMetrics)
  const addToast = useVisionStore((s) => s.addToast)
  const addNotification = useVisionStore((s) => s.addNotification)

  const { openPopout } = useVisionPopout()
  const [expanded, setExpanded] = useState(false)
  const [savingPreset, setSavingPreset] = useState(false)
  const [newPresetName, setNewPresetName] = useState('')
  const [newPresetLabel, setNewPresetLabel] = useState('')
  const [speed, setSpeed] = useState(1)
  const [qualityOpen, setQualityOpen] = useState(false)
  const [renamingPreset, setRenamingPreset] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)

  const activeMotionIdRef = useRef<string>('')
  const motionUpdateTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const joystickRef = useRef<HTMLDivElement>(null)
  const joystickDragging = useRef(false)
  const joystickVelocity = useRef({ pan: 0, tilt: 0 })
  const [thumbPos, setThumbPos] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)

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
  }, [setActivePreset])

  // ── Realtime PTZ motion — press-and-hold D-pad ─────────────────

  const lastSentVector = useRef({ pan: 0, tilt: 0 })

  const ensureUpdateTimer = useCallback(() => {
    if (motionUpdateTimerRef.current) return
    motionUpdateTimerRef.current = setInterval(() => {
      const client = getVisionClient()
      const mid = activeMotionIdRef.current
      if (!client?.connected || !mid) return
      const v = joystickVelocity.current
      const last = lastSentVector.current
      if (Math.abs(v.pan - last.pan) < 0.02 && Math.abs(v.tilt - last.tilt) < 0.02) return
      lastSentVector.current = { pan: v.pan, tilt: v.tilt }
      client.ptzUpdateMotion({
        motionId: mid,
        panVelocity: v.pan,
        tiltVelocity: v.tilt,
        speed,
      })
      updateControlMetrics({ lastCommandSentAt: Date.now() })
    }, MOTION_UPDATE_INTERVAL_MS)
  }, [speed, updateControlMetrics])

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
    setIsDragging(true)

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
    setIsDragging(false)
    stopDirectionMotion()
  }, [stopDirectionMotion])

  // ── Touch fallback for iOS Safari ─────────────────────────────────

  const handleJoystickTouchStart = useCallback((e: React.TouchEvent) => {
    e.stopPropagation()
    e.preventDefault()
    const t = e.touches[0]
    if (!t) return
    joystickDragging.current = true
    setIsDragging(true)
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
    setIsDragging(false)
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
    addNotification('warn', 'E-stop pressed', 'operator', 'Emergency stop — all PTZ motion halted', 'motion stopped')
  }, [setPtzMoving, stopDirectionMotion, stopZoomMotion, addNotification])

  const handleQualityChange = useCallback((mode: QualityMode) => {
    setQualityMode(mode)
    setQualityOpen(false)
    const client = getVisionClient()
    if (!client?.connected || !streaming) return
    client.switchQuality(QUALITY_PROFILES[mode])
  }, [streaming, setQualityMode])

  const handleSavePreset = useCallback(() => {
    if (!newPresetName.trim()) return
    const client = getVisionClient()
    if (!client?.connected) return
    const slug = newPresetName.trim().toLowerCase().replace(/\s+/g, '_')
    const label = newPresetLabel.trim() || newPresetName.trim()
    const pos = useVisionStore.getState().ptzPosition
    const mode = useVisionStore.getState().chainHealth.ptzMode
    const roi = useVisionStore.getState().chainHealth.roi

    const preset: CameraPreset = {
      label,
      pan: pos.pan,
      tilt: pos.tilt,
      zoom: pos.zoom,
      mode,
      roi: mode === 'digital_roi' ? roi : undefined,
      created_at: Date.now(),
      updated_at: Date.now(),
    }

    client.savePreset(slug, label)

    const updated = { ...useVisionStore.getState().presets, [slug]: preset }
    setPresets(updated)
    savePresetsToStorage(updated)
    setSavingPreset(false)
    setNewPresetName('')
    setNewPresetLabel('')
    addToast(`Preset "${label}" saved`, 'ok')
  }, [newPresetName, newPresetLabel, setPresets, addToast])

  const handleUpdatePreset = useCallback((name: string) => {
    const client = getVisionClient()
    if (!client?.connected) return
    const pos = useVisionStore.getState().ptzPosition
    const mode = useVisionStore.getState().chainHealth.ptzMode
    const roi = useVisionStore.getState().chainHealth.roi
    const existing = useVisionStore.getState().presets[name]

    const preset: CameraPreset = {
      ...existing,
      pan: pos.pan,
      tilt: pos.tilt,
      zoom: pos.zoom,
      mode,
      roi: mode === 'digital_roi' ? roi : undefined,
      updated_at: Date.now(),
    }

    client.savePreset(name, preset.label || name)

    const updated = { ...useVisionStore.getState().presets, [name]: preset }
    setPresets(updated)
    savePresetsToStorage(updated)
    addToast(`Preset "${preset.label || name}" updated`, 'cyan')
  }, [setPresets, addToast])

  const handleDeletePreset = useCallback((name: string) => {
    const current = useVisionStore.getState().presets
    const label = current[name]?.label || name
    const updated = { ...current }
    delete updated[name]
    setPresets(updated)
    savePresetsToStorage(updated)
    getVisionClient()?.deletePresetOnDevice(name)
    if (activePreset === name) setActivePreset('')
    setConfirmDelete(null)
    addToast(`Preset "${label}" deleted`, 'danger')
  }, [setPresets, setActivePreset, activePreset, addToast])

  const handleRenamePreset = useCallback((name: string) => {
    const trimmed = renameValue.trim()
    if (!trimmed) { setRenamingPreset(null); return }
    const current = useVisionStore.getState().presets
    const updated = { ...current, [name]: { ...current[name], label: trimmed, updated_at: Date.now() } }
    setPresets(updated)
    savePresetsToStorage(updated)
    setRenamingPreset(null)
    setRenameValue('')
    addToast(`Preset renamed to "${trimmed}"`, 'cyan')
  }, [renameValue, setPresets, addToast])

  const motionLabel = (state: MotionState): string => {
    const labels: Record<MotionState, string> = {
      idle: 'idle', moving: 'moving', stopping: 'stopping...',
      blocked: 'blocked', disconnected: 'disconnected',
    }
    return labels[state] || state
  }

  // Merged presets: default presets first, then custom presets from store
  const customPresets = Object.entries(presets).filter(([name]) => !DEFAULT_PRESET_KEYS.has(name))

  // Check if current position differs from active preset
  const activePresetData = activePreset ? presets[activePreset] : null
  const isPresetModified = activePresetData && (
    activePresetData.pan !== ptzPosition.pan ||
    activePresetData.tilt !== ptzPosition.tilt ||
    activePresetData.zoom !== ptzPosition.zoom
  )

  // ── Render ─────────────────────────────────────────────────────

  return (
    <div className={clsx('flex flex-col gap-3', expanded && 'fixed inset-0 z-50 bg-surface p-4')}>

      {/* 1. StatusHud — single compact line above camera preview */}
      <StatusHud />

      {/* CAMERA LIVE indicator */}
      {isActive && (
        <div className="flex items-center gap-1.5 px-3 py-2 rounded bg-danger/10 text-danger text-xs font-mono uppercase tracking-wider">
          <span className="w-2 h-2 rounded-full bg-danger animate-pulse" />
          camera live
          {chainHealth.ptzMode === 'physical_ptz' ? ' — physical ptz' : ' — digital roi'}
          {ptzMotion.state === 'moving' && (
            <span className="ml-auto text-warning">{motionLabel(ptzMotion.state)}</span>
          )}
        </div>
      )}

      {/* 2. Camera preview */}
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
              style={chainHealth.ptzMode === 'digital_roi' && chainHealth.roi.zoom > 1 ? {
                transformOrigin: `${(chainHealth.roi.x + (1 / chainHealth.roi.zoom) / 2) * 100}% ${(chainHealth.roi.y + (1 / chainHealth.roi.zoom) / 2) * 100}%`,
                transform: `scale(${chainHealth.roi.zoom})`,
              } : undefined}
            />
            {/* OVR: real AI detections from Beast only */}
            <VisionOverlay
              overlays={overlays}
              width={width || 1280}
              height={height || 720}
              visible={overlayVisible}
            />
            {/* Stream quality badge — bottom-right corner */}
            <div className="absolute bottom-2 right-2">
              <button
                onClick={() => setQualityOpen(!qualityOpen)}
                className="px-2 py-1 rounded-full bg-black/70 text-[10px] font-mono text-text-secondary backdrop-blur-sm hover:text-text-primary transition-colors"
              >
                {QUALITY_LABELS[qualityMode]} · {streamMetrics.actualFps.toFixed(1)}fps · {Math.round(streamMetrics.avgFrameSize / 1024)}KB
              </button>
              {qualityOpen && (
                <div className="absolute bottom-full right-0 mb-1 bg-surface border border-border rounded-lg p-2 shadow-lg flex flex-col gap-1 min-w-[120px]">
                  {(Object.keys(QUALITY_PROFILES) as QualityMode[]).map((mode) => (
                    <button
                      key={mode}
                      onClick={() => handleQualityChange(mode)}
                      className={clsx(
                        'px-3 py-2 rounded text-xs font-mono uppercase tracking-wider transition-colors text-left',
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
              )}
            </div>
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

      {/* 3. CameraModeSelector — below camera preview */}
      <CameraModeSelector />

      {/* 4. Primary action buttons */}
      <div className="flex items-center gap-2">
        {!isActive ? (
          <MobileBtn icon={<Camera size={18} />} label="Start" onClick={handleStart} disabled={!connected} variant="ok" />
        ) : (
          <MobileBtn icon={<CameraOff size={18} />} label="Stop" onClick={handleStop} variant="danger" />
        )}
        <MobileBtn icon={<Aperture size={18} />} label="Snap" onClick={handleSnapshot} disabled={!connected} variant="cyan" />
        <MobileBtn icon={<Square size={18} />} label="E-Stop" onClick={handleEmergencyStop} variant="danger" />
      </div>

      {/* 5. OVR toggle — real detections only */}
      <button
        onClick={() => setOverlayVisible(!overlayVisible)}
        className={clsx(
          'py-2.5 rounded text-xs font-mono text-center transition-colors flex flex-col items-center gap-0.5',
          overlayVisible
            ? 'bg-ok/20 text-ok border border-ok/30'
            : 'bg-surface-hover text-text-tertiary border border-transparent',
        )}
      >
        <span className="uppercase tracking-wider">OVR {overlayVisible ? 'on' : 'off'}</span>
        <span className="text-[9px] opacity-70 normal-case">real detections only</span>
      </button>

      {!compact && (
        <>
          {/* 6. Presets — unified style for all preset buttons */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-text-tertiary uppercase tracking-wider">
                Presets
                {isPresetModified && (
                  <span className="ml-1 text-warning">(modified)</span>
                )}
              </span>
              <div className="flex items-center gap-2">
                {isPresetModified && activePreset && (
                  <button
                    onClick={() => handleUpdatePreset(activePreset)}
                    className="flex items-center gap-1 px-2 py-1 rounded border border-warning/30 bg-warning/10 text-[10px] font-mono text-warning hover:bg-warning/20 uppercase tracking-wider transition-colors"
                    title={`Update ${activePreset} to current position`}
                  >
                    <RotateCcw size={10} />
                    Update
                  </button>
                )}
                <button
                  onClick={() => setSavingPreset(!savingPreset)}
                  className="flex items-center gap-1 px-2 py-1 rounded border border-border bg-surface-hover text-[10px] font-mono text-text-tertiary hover:text-text-primary uppercase tracking-wider transition-colors"
                >
                  <Plus size={12} />
                  New
                </button>
              </div>
            </div>

            {/* All presets — unified grid with identical button treatment */}
            <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-4">
              {DEFAULT_PRESETS.map(({ key, label, icon }) => {
                const isThisActive = activePreset === key
                return (
                  <PresetBtn
                    key={key}
                    label={label}
                    icon={icon}
                    active={isThisActive}
                    modified={isThisActive && !!isPresetModified}
                    disabled={!connected}
                    onClick={() => handlePreset(key)}
                  />
                )
              })}
              {customPresets.map(([name, preset]) => {
                const isThisActive = activePreset === name
                const isRenaming = renamingPreset === name
                const isDeleting = confirmDelete === name

                if (isDeleting) {
                  return (
                    <div key={name} className="flex items-center gap-1 px-3 py-2.5 rounded-lg border border-danger/30 bg-danger/5 min-h-[48px]">
                      <span className="text-[10px] font-mono text-danger truncate flex-1">Delete?</span>
                      <button onClick={() => handleDeletePreset(name)} className="p-1 rounded text-danger hover:bg-danger/10"><Check size={12} /></button>
                      <button onClick={() => setConfirmDelete(null)} className="p-1 rounded text-text-tertiary hover:bg-surface-hover"><X size={12} /></button>
                    </div>
                  )
                }

                if (isRenaming) {
                  return (
                    <div key={name} className="flex items-center gap-1 px-2 py-1.5 rounded-lg border border-cyan/30 bg-surface min-h-[48px]">
                      <input
                        type="text"
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onKeyDown={(e) => { if (e.key === 'Enter') handleRenamePreset(name); if (e.key === 'Escape') setRenamingPreset(null) }}
                        autoFocus
                        className="flex-1 px-1.5 py-0.5 rounded bg-surface-hover border border-border text-xs font-mono text-text-primary focus:outline-none focus:border-cyan/50 min-w-0"
                      />
                      <button onClick={() => handleRenamePreset(name)} className="p-1 rounded text-ok hover:bg-ok/10"><Check size={12} /></button>
                      <button onClick={() => setRenamingPreset(null)} className="p-1 rounded text-text-tertiary hover:bg-surface-hover"><X size={12} /></button>
                    </div>
                  )
                }

                return (
                  <PresetBtn
                    key={name}
                    label={preset.label || name}
                    active={isThisActive}
                    modified={isThisActive && !!isPresetModified}
                    disabled={!connected}
                    onClick={() => handlePreset(name)}
                    onRename={() => { setRenamingPreset(name); setRenameValue(preset.label || name) }}
                    onUpdate={() => handleUpdatePreset(name)}
                    onDelete={() => setConfirmDelete(name)}
                    editable
                  />
                )
              })}
            </div>

            {savingPreset && (
              <div className="flex items-center gap-1.5 p-2 rounded-lg border border-border bg-surface-hover">
                <input
                  type="text"
                  value={newPresetName}
                  onChange={(e) => setNewPresetName(e.target.value)}
                  placeholder="Name (slug)"
                  onKeyDown={(e) => { if (e.key === 'Enter') handleSavePreset() }}
                  className="flex-1 px-2 py-1.5 rounded bg-surface border border-border text-xs font-mono text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-cyan/50"
                />
                <input
                  type="text"
                  value={newPresetLabel}
                  onChange={(e) => setNewPresetLabel(e.target.value)}
                  placeholder="Display label"
                  onKeyDown={(e) => { if (e.key === 'Enter') handleSavePreset() }}
                  className="flex-1 px-2 py-1.5 rounded bg-surface border border-border text-xs font-mono text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-cyan/50"
                />
                <button
                  onClick={handleSavePreset}
                  disabled={!newPresetName.trim()}
                  className="px-3 py-1.5 rounded-lg border border-ok/30 bg-ok/10 text-ok text-xs font-mono uppercase tracking-wider hover:bg-ok/20 disabled:opacity-50 transition-colors"
                >
                  Save
                </button>
                <button
                  onClick={() => { setSavingPreset(false); setNewPresetName(''); setNewPresetLabel('') }}
                  className="px-2 py-1.5 rounded text-text-tertiary hover:text-text-primary text-xs"
                >
                  <X size={14} />
                </button>
              </div>
            )}
          </div>

          {/* 7. PTZ Controls — joystick primary, D-pad secondary */}
          <div className="flex flex-col gap-3">
            <div className="flex items-start gap-4 justify-center">
              {/* D-pad — SECONDARY "Precision Mode" — smaller buttons */}
              <div className="flex flex-col items-center gap-1">
                <span className="text-[9px] font-mono text-text-tertiary uppercase tracking-wider">
                  Precision
                </span>
                <div className="grid grid-cols-3 gap-0.5 w-fit">
                  <div />
                  <DpadBtn direction="up" onStart={() => startDirectionMotion(0, 1)} onStop={stopDirectionMotion} connected={controlsEnabled} size={40} />
                  <div />
                  <DpadBtn direction="left" onStart={() => startDirectionMotion(-1, 0)} onStop={stopDirectionMotion} connected={controlsEnabled} size={40} />
                  <DpadBtn direction="stop" onStart={handleEmergencyStop} onStop={() => {}} connected={controlsEnabled} isStop size={40} />
                  <DpadBtn direction="right" onStart={() => startDirectionMotion(1, 0)} onStop={stopDirectionMotion} connected={controlsEnabled} size={40} />
                  <div />
                  <DpadBtn direction="down" onStart={() => startDirectionMotion(0, -1)} onStop={stopDirectionMotion} connected={controlsEnabled} size={40} />
                  <div />
                </div>
                <button
                  onClick={handlePtzHome}
                  disabled={!controlsEnabled}
                  className={clsx(
                    'mt-0.5 flex items-center gap-1 px-2 py-1.5 rounded text-[10px] font-mono text-text-secondary',
                    'border border-border bg-surface-hover hover:text-text-primary transition-colors',
                    !controlsEnabled && 'opacity-40 cursor-not-allowed',
                  )}
                >
                  <Home size={12} />
                  Home
                </button>
              </div>

              {/* Joystick — PRIMARY — enlarged 192px */}
              <div className="flex flex-col items-center gap-2">
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
                    'w-48 h-48 rounded-full border-2 relative cursor-crosshair select-none transition-shadow',
                    controlsEnabled ? 'border-border bg-surface-hover' : 'border-border/50 bg-surface-hover/50 opacity-50',
                    (isDragging || ptzMotion.state === 'moving') && 'shadow-[0_0_20px_rgba(34,211,238,0.3)] border-cyan/50',
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
                      'absolute w-10 h-10 rounded-full border-2 transition-colors',
                      isDragging || ptzMotion.state === 'moving'
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
                {/* Velocity vector readout */}
                <span className={clsx(
                  'text-[10px] font-mono',
                  isDragging || ptzMotion.state === 'moving' ? 'text-cyan' : 'text-text-quaternary',
                )}>
                  pan: {joystickVelocity.current.pan.toFixed(2)}  tilt: {joystickVelocity.current.tilt.toFixed(2)}
                </span>
              </div>

              {/* Zoom — to the right of joystick */}
              <div className="flex flex-col items-center gap-1">
                <span className="text-[10px] font-mono text-text-tertiary uppercase tracking-wider">Zoom</span>
                <div className="flex flex-col gap-1">
                  <ZoomBtn icon={<ZoomIn size={20} />} onStart={() => startZoomMotion(1)} onStop={stopZoomMotion} connected={controlsEnabled} title="Zoom in" />
                  <ZoomBtn icon={<ZoomOut size={20} />} onStart={() => startZoomMotion(-1)} onStop={stopZoomMotion} connected={controlsEnabled} title="Zoom out" />
                </div>
              </div>
            </div>

            {/* 8. Position readout */}
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

          {/* 9. SceneInventory — replaces TrackerStatus live detections */}
          <SceneInventory />

          {/* 10. DiagnosticsPanel */}
          <DiagnosticsPanel
            ptzMotion={ptzMotion}
            controlMetrics={controlMetrics}
            joystickDragging={isDragging}
            joystickVelocity={joystickVelocity.current}
            speed={speed}
            overlays={overlays}
            overlayVisible={overlayVisible}
            connected={connected}
            streaming={streaming}
            streamMetrics={streamMetrics}
            frameCount={frameCount}
            qualityMode={qualityMode}
          />

          {/* 11. Notification center — security/governance events */}
          <NotificationCenter />

          {/* 12. TrackingPanel */}
          <div className="border-t border-border pt-3">
            <TrackingPanel />
          </div>
        </>
      )}

      {/* 13. Connection status bar */}
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

      <ToastContainer />
    </div>
  )
}

// ── D-pad button — accepts size prop (default 56, pass 40 for precision mode) ──

function DpadBtn({
  direction, onStart, onStop, connected, isStop, size = 56,
}: {
  direction: string
  onStart: () => void
  onStop: () => void
  connected: boolean
  isStop?: boolean
  size?: number
}) {
  const icons: Record<string, React.ReactNode> = {
    up: <ArrowUp size={size <= 40 ? 16 : 20} />,
    down: <ArrowDown size={size <= 40 ? 16 : 20} />,
    left: <ArrowLeft size={size <= 40 ? 16 : 20} />,
    right: <ArrowRight size={size <= 40 ? 16 : 20} />,
    stop: <div className={clsx('rounded-full bg-current', size <= 40 ? 'w-2 h-2' : 'w-3 h-3')} />,
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
        'flex items-center justify-center rounded-lg border border-border',
        'text-text-secondary hover:text-text-primary hover:bg-surface-hover',
        'transition-colors disabled:opacity-40 disabled:cursor-not-allowed touch-none select-none',
        'active:bg-cyan/20 active:border-cyan/50',
        isStop && 'bg-surface-hover',
      )}
      style={{ touchAction: 'none', width: size, height: size }}
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

// ── Unified preset button — same treatment for default + custom ─────

function PresetBtn({
  label, icon, active, modified, disabled, onClick,
  onRename, onUpdate, onDelete, editable,
}: {
  label: string
  icon?: React.ReactNode
  active: boolean
  modified: boolean
  disabled: boolean
  onClick: () => void
  onRename?: () => void
  onUpdate?: () => void
  onDelete?: () => void
  editable?: boolean
}) {
  return (
    <div
      className={clsx(
        'group relative flex items-center gap-1.5 px-3 py-2.5 rounded-lg border text-xs font-mono transition-colors min-h-[48px]',
        active
          ? modified
            ? 'bg-warning/10 text-warning border-warning/30'
            : 'bg-cyan/20 text-cyan border-cyan/30'
          : 'bg-surface-hover text-text-secondary hover:text-text-primary border-border',
        disabled && 'opacity-50 cursor-not-allowed',
      )}
    >
      <button
        onClick={onClick}
        disabled={disabled}
        className="flex items-center gap-1.5 flex-1 text-left truncate uppercase tracking-wider"
      >
        {icon}
        {label}
      </button>
      {editable && (
        <div className="hidden group-hover:flex items-center gap-0.5 shrink-0">
          {onRename && <button onClick={(e) => { e.stopPropagation(); onRename() }} className="p-0.5 rounded text-text-quaternary hover:text-cyan" title="Rename"><Pencil size={10} /></button>}
          {onUpdate && <button onClick={(e) => { e.stopPropagation(); onUpdate() }} className="p-0.5 rounded text-text-quaternary hover:text-warning" title="Update position"><RotateCcw size={10} /></button>}
          {onDelete && <button onClick={(e) => { e.stopPropagation(); onDelete() }} className="p-0.5 rounded text-text-quaternary hover:text-danger" title="Delete"><Trash2 size={10} /></button>}
        </div>
      )}
    </div>
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

