import { useCallback, useMemo } from 'react'
import { clsx } from 'clsx'
import {
  Camera, RefreshCw, Settings2, Cpu, Zap, Activity,
  X, Monitor, Check, AlertTriangle, Loader2,
  Eye,
} from 'lucide-react'
import {
  useVisionStore,
  QUALITY_PROFILES,
  computeVisionReadiness,
  type QualityMode,
  type CameraDevice,
  type DeviceStatus,
  type VisionReadiness,
} from '../../stores/visionStore'
import { getVisionClient } from '../../hooks/useVisionConnection'

const QUALITY_LABELS: Record<QualityMode, string> = {
  smooth: 'Smooth',
  balanced: 'Balanced',
  high: 'High',
  analysis: 'Analysis',
}

const QUALITY_DESCRIPTIONS: Record<QualityMode, string> = {
  smooth: '30fps 720p — low latency streaming',
  balanced: '15fps 720p — default operator mode',
  high: '10fps 1080p — high detail',
  analysis: '1fps 1080p — AI snapshot, max clarity',
}

const STATUS_LABELS: Record<DeviceStatus, string> = {
  usable: 'Ready',
  busy: 'In Use',
  stale: 'Stale Frames',
  unavailable: 'Unavailable',
  duplicate: 'Duplicate',
  error: 'Error',
  unknown: 'Not Probed',
}

const READINESS_COLORS: Record<VisionReadiness, string> = {
  READY: 'bg-ok',
  DEGRADED: 'bg-warning',
  STALE: 'bg-warning',
  OFFLINE: 'bg-danger',
  BLOCKED: 'bg-danger',
}

const READINESS_TEXT: Record<VisionReadiness, string> = {
  READY: 'text-ok',
  DEGRADED: 'text-warning',
  STALE: 'text-warning',
  OFFLINE: 'text-danger',
  BLOCKED: 'text-danger',
}

function DeviceRow({ device, onSelect, switching }: {
  device: CameraDevice
  onSelect: (idx: number) => void
  switching: boolean
}) {
  const isUsable = device.status === 'usable' || device.status === 'unknown'
  const isBusyElsewhere = device.busy && !device.selected
  const isDisabled = !isUsable && !device.selected
  const statusLabel = isBusyElsewhere
    ? 'In use — may conflict'
    : STATUS_LABELS[device.status] || device.status

  return (
    <button
      onClick={() => onSelect(device.index)}
      disabled={switching || (isDisabled && !device.selected)}
      title={device.last_probe_error || statusLabel}
      className={clsx(
        'w-full flex items-center gap-2 px-3 py-2.5 rounded-lg border text-left transition-colors',
        device.selected
          ? 'border-cyan/50 bg-cyan/5'
          : isDisabled
            ? 'border-border opacity-40 cursor-not-allowed'
            : 'border-border hover:bg-surface-hover cursor-pointer',
        isBusyElsewhere && 'opacity-60 border-warning/30',
      )}
    >
      <Camera size={14} className={device.selected ? 'text-cyan' : 'text-text-tertiary'} />
      <div className="flex-1 min-w-0">
        <div className="text-xs font-mono text-text-primary truncate">{device.name}</div>
        <div className="text-[10px] text-text-tertiary flex items-center gap-1.5 mt-0.5">
          {device.width > 0 && <span>{device.width}x{device.height}</span>}
          {device.fps > 0 && <span>· {device.fps}fps</span>}
          <span className={clsx(
            device.status === 'usable' ? 'text-ok' :
            device.status === 'error' || device.status === 'unavailable' ? 'text-danger' :
            device.status === 'stale' || device.status === 'busy' ? 'text-warning' :
            'text-text-quaternary',
          )}>
            · {statusLabel}
          </span>
          {device.selected && device.busy && <span className="text-cyan">· streaming</span>}
        </div>
      </div>
      {device.selected && <Check size={12} className="text-cyan shrink-0" />}
      <span className={clsx(
        'w-1.5 h-1.5 rounded-full shrink-0',
        device.status === 'usable' ? (device.busy ? (device.selected ? 'bg-cyan' : 'bg-warning') : 'bg-ok')
          : device.status === 'error' || device.status === 'unavailable' ? 'bg-danger'
          : 'bg-text-quaternary',
      )} />
    </button>
  )
}

function ReadinessIndicator() {
  const streaming = useVisionStore((s) => s.streaming)
  const latestFrameAt = useVisionStore((s) => s.latestFrameAt)
  const chainHealth = useVisionStore((s) => s.chainHealth)
  const hasPtzHardware = useVisionStore((s) => s.hasPtzHardware)
  const presetsLoaded = Object.keys(useVisionStore.getState().presets).length > 0

  const fps = useVisionStore((s) => s.streamMetrics.actualFps)
  const readiness = useMemo(
    () => computeVisionReadiness(chainHealth, streaming, latestFrameAt, fps, hasPtzHardware, presetsLoaded),
    [chainHealth, streaming, latestFrameAt, fps, hasPtzHardware, presetsLoaded],
  )

  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-surface-hover/30 border-b border-border">
      <span className={clsx('w-2 h-2 rounded-full', READINESS_COLORS[readiness.readiness])} />
      <span className={clsx('text-xs font-mono font-medium', READINESS_TEXT[readiness.readiness])}>
        {readiness.readiness}
      </span>
      <span className="text-[10px] text-text-tertiary flex-1">{readiness.reason}</span>
    </div>
  )
}

export function VisionSettings() {
  const connected = useVisionStore((s) => s.connected)
  const devices = useVisionStore((s) => s.cameraDevices)
  const selectedDevice = useVisionStore((s) => s.selectedDeviceIndex)
  const scanLoading = useVisionStore((s) => s.deviceScanLoading)
  const switching = useVisionStore((s) => s.deviceSwitching)
  const switchError = useVisionStore((s) => s.deviceSwitchError)
  const qualityMode = useVisionStore((s) => s.qualityMode)
  const setQualityMode = useVisionStore((s) => s.setQualityMode)
  const streamMetrics = useVisionStore((s) => s.streamMetrics)
  const chainHealth = useVisionStore((s) => s.chainHealth)
  const ptzPosition = useVisionStore((s) => s.ptzPosition)
  const hasPtzHardware = useVisionStore((s) => s.hasPtzHardware)
  const setSettingsOpen = useVisionStore((s) => s.setSettingsOpen)
  const latencyHistory = useVisionStore((s) => s.latencyHistory)
  const presetsLoading = useVisionStore((s) => s.presetsLoading)
  const presetsLoadError = useVisionStore((s) => s.presetsLoadError)
  const authority = useVisionStore((s) => s.authority)

  const handleRescan = useCallback(() => {
    const client = getVisionClient()
    if (!client?.connected) return
    useVisionStore.getState().setDeviceScanLoading(true)
    client.listDevices()
    setTimeout(() => {
      if (useVisionStore.getState().deviceScanLoading) {
        useVisionStore.getState().setDeviceScanLoading(false)
      }
    }, 15000)
  }, [])

  const handleSelectDevice = useCallback((idx: number) => {
    const client = getVisionClient()
    if (!client?.connected) return
    if (idx === selectedDevice) return
    const store = useVisionStore.getState()
    store.setDeviceSwitching(true)
    store.setDeviceSwitchError(null)
    store.addToast('Switching camera...', 'cyan')
    const profile = QUALITY_PROFILES[store.qualityMode]
    client.selectDevice(idx)
    // Timeout: if no response in 10s, clear switching state
    setTimeout(() => {
      if (useVisionStore.getState().deviceSwitching) {
        useVisionStore.getState().setDeviceSwitching(false)
        useVisionStore.getState().setDeviceSwitchError('Switch timed out — no response from Beast')
        useVisionStore.getState().addToast('Camera switch timed out', 'danger')
      }
    }, 10000)
  }, [selectedDevice])

  const handleQualityChange = useCallback((mode: QualityMode) => {
    setQualityMode(mode)
    const client = getVisionClient()
    if (client?.connected) {
      client.switchQuality(QUALITY_PROFILES[mode])
    }
  }, [setQualityMode])

  const handleRetryPresets = useCallback(() => {
    const client = getVisionClient()
    if (!client?.connected) return
    useVisionStore.getState().setPresetsLoading(true)
    useVisionStore.getState().setPresetsLoadError(null)
    client.requestPresets()
  }, [])

  const det = chainHealth.detectorStatus
  const avgRtt = latencyHistory.length > 0
    ? Math.round(latencyHistory.reduce((a, m) => a + m.roundTripMs, 0) / latencyHistory.length)
    : null

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
        <Settings2 size={16} className="text-text-secondary" />
        <span className="text-sm font-medium text-text-primary flex-1">Vision Settings</span>
        <button onClick={() => setSettingsOpen(false)} className="p-1 rounded hover:bg-surface-hover">
          <X size={14} className="text-text-tertiary" />
        </button>
      </div>

      {/* Vision Readiness — single source of truth */}
      <ReadinessIndicator />

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Camera Device — OBS/Discord style */}
        <div className="border border-border rounded-lg overflow-hidden">
          <div className="flex items-center gap-2 px-3 py-2 bg-surface-hover/30">
            <Camera size={14} className="text-text-secondary" />
            <span className="text-xs font-medium text-text-secondary flex-1">Camera Device</span>
            <button
              onClick={handleRescan}
              disabled={scanLoading || !connected}
              className={clsx(
                'p-1 rounded transition-colors',
                scanLoading ? 'animate-spin text-cyan' : 'text-text-tertiary hover:text-text-primary hover:bg-surface-hover',
              )}
              title="Rescan devices"
            >
              <RefreshCw size={12} />
            </button>
          </div>
          <div className="p-2 space-y-1.5">
            {!connected ? (
              <div className="text-[10px] text-text-tertiary px-2 py-3 text-center">Connect to relay to scan devices</div>
            ) : devices.length === 0 ? (
              <div className="text-[10px] text-text-tertiary px-2 py-3 text-center">
                {scanLoading ? (
                  <span className="flex items-center justify-center gap-1.5">
                    <Loader2 size={10} className="animate-spin" /> Scanning...
                  </span>
                ) : 'No cameras detected — click refresh'}
              </div>
            ) : (
              <>
                {devices.map((d) => (
                  <DeviceRow key={d.index} device={d} onSelect={handleSelectDevice} switching={switching} />
                ))}
                {switching && (
                  <div className="flex items-center gap-1.5 px-2 py-1 text-[10px] text-cyan">
                    <Loader2 size={10} className="animate-spin" /> Switching camera...
                  </div>
                )}
                {switchError && (
                  <div className="flex items-center gap-1.5 px-2 py-1 text-[10px] text-danger">
                    <AlertTriangle size={10} /> {switchError}
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Stream Quality */}
        <div className="border border-border rounded-lg overflow-hidden">
          <div className="flex items-center gap-2 px-3 py-2 bg-surface-hover/30">
            <Monitor size={14} className="text-text-secondary" />
            <span className="text-xs font-medium text-text-secondary">Stream Quality</span>
          </div>
          <div className="p-2 space-y-1.5">
            {(Object.keys(QUALITY_PROFILES) as QualityMode[]).map((mode) => {
              const p = QUALITY_PROFILES[mode]
              const active = qualityMode === mode
              return (
                <button
                  key={mode}
                  onClick={() => handleQualityChange(mode)}
                  className={clsx(
                    'w-full flex items-center gap-2 px-3 py-2 rounded-lg border text-left transition-colors',
                    active ? 'border-cyan/50 bg-cyan/5' : 'border-border hover:bg-surface-hover',
                  )}
                >
                  <div className="flex-1 min-w-0">
                    <div className={clsx('text-xs font-mono', active ? 'text-cyan' : 'text-text-primary')}>
                      {QUALITY_LABELS[mode]}
                    </div>
                    <div className="text-[10px] text-text-tertiary">{QUALITY_DESCRIPTIONS[mode]}</div>
                  </div>
                  <div className="text-[10px] text-text-quaternary font-mono shrink-0">
                    {p.width}x{p.height} @{p.fps}fps q{p.quality}
                  </div>
                </button>
              )
            })}
            <div className="grid grid-cols-3 gap-1 px-2 pt-1">
              <MetricCell label="Resolution" value={streamMetrics.actualFps > 0 ? `${useVisionStore.getState().width}x${useVisionStore.getState().height}` : '—'} />
              <MetricCell label="Actual FPS" value={streamMetrics.actualFps > 0 ? streamMetrics.actualFps.toFixed(1) : '—'} />
              <MetricCell label="Bitrate" value={streamMetrics.bitrateKbps > 0
                ? streamMetrics.bitrateKbps > 1024 ? `${(streamMetrics.bitrateKbps / 1024).toFixed(1)} Mbps` : `${streamMetrics.bitrateKbps} Kbps`
                : '—'} />
              <MetricCell label="Frame Size" value={streamMetrics.avgFrameSize > 0 ? `${(streamMetrics.avgFrameSize / 1024).toFixed(1)} KB` : '—'} />
              <MetricCell label="Latency" value={streamMetrics.lastFrameAge > 0 ? `${streamMetrics.lastFrameAge}ms` : '—'}
                color={streamMetrics.lastFrameAge < 500 ? 'ok' : streamMetrics.lastFrameAge < 2000 ? 'warn' : 'danger'} />
              <MetricCell label="Dropped" value={String(streamMetrics.droppedFrames)} />
            </div>
          </div>
        </div>

        {/* AI / Detector */}
        <div className="border border-border rounded-lg overflow-hidden">
          <div className="flex items-center gap-2 px-3 py-2 bg-surface-hover/30">
            <Zap size={14} className="text-text-secondary" />
            <span className="text-xs font-medium text-text-secondary">AI / Detector</span>
          </div>
          <div className="p-2">
            {det ? (
              <div className="grid grid-cols-2 gap-1">
                <MetricCell label="Model" value={det.model || 'none'} />
                <MetricCell label="Device" value={det.device || 'cpu'}
                  color={det.device === 'cuda' ? 'ok' : 'warn'} />
                <MetricCell label="Status" value={det.loaded ? 'loaded' : 'not loaded'}
                  color={det.loaded ? 'ok' : 'danger'} />
                <MetricCell label="Inference" value={det.avg_inference_ms > 0 ? `${det.avg_inference_ms.toFixed(0)}ms` : '—'}
                  color={det.avg_inference_ms < 100 ? 'ok' : det.avg_inference_ms < 300 ? 'warn' : 'danger'} />
                <MetricCell label="Det. FPS" value={det.detection_frames > 0 ? `${det.detection_frames} frames` : '0'} />
                <MetricCell label="Tracker" value={det.tracker_active ? `${det.active_tracks} tracks` : 'off'}
                  color={det.tracker_active ? 'ok' : 'off'} />
              </div>
            ) : (
              <div className="text-[10px] text-text-tertiary text-center py-2">
                {connected ? 'Detector not reporting — start stream' : 'Connect to see detector status'}
              </div>
            )}
          </div>
        </div>

        {/* Controls / PTZ — Section 7 */}
        <div className="border border-border rounded-lg overflow-hidden">
          <div className="flex items-center gap-2 px-3 py-2 bg-surface-hover/30">
            <Activity size={14} className="text-text-secondary" />
            <span className="text-xs font-medium text-text-secondary">Controls / PTZ</span>
          </div>
          <div className="p-2">
            <div className="grid grid-cols-2 gap-1">
              <MetricCell label="Mode" value={chainHealth.ptzMode === 'physical_ptz' ? 'Physical PTZ' : 'Digital ROI'} />
              <MetricCell label="Hardware" value={hasPtzHardware ? 'Available' : 'Not detected'}
                color={hasPtzHardware ? 'ok' : 'warn'} />
              <MetricCell label="Pan" value={String(ptzPosition.pan)} />
              <MetricCell label="Tilt" value={String(ptzPosition.tilt)} />
              <MetricCell label="Zoom" value={String(ptzPosition.zoom)} />
              <MetricCell label="Cmd RTT" value={avgRtt !== null ? `${avgRtt}ms` : '—'}
                color={avgRtt !== null ? (avgRtt < 80 ? 'ok' : avgRtt < 150 ? 'warn' : 'danger') : 'off'} />
            </div>
            {!chainHealth.commandPathReady && (
              <div className="flex items-center gap-1.5 px-2 pt-1 text-[10px] text-warning">
                <AlertTriangle size={10} />
                {!chainHealth.beastConnected
                  ? 'Beast offline — controls unavailable'
                  : 'Command path not ready — controls may not respond'}
              </div>
            )}
            {!hasPtzHardware && chainHealth.digitalRoiAvailable && (
              <div className="flex items-center gap-1.5 px-2 pt-1 text-[10px] text-text-tertiary">
                <Eye size={10} /> No PTZ hardware — using Digital ROI fallback
              </div>
            )}
            {!hasPtzHardware && !chainHealth.digitalRoiAvailable && (
              <div className="flex items-center gap-1.5 px-2 pt-1 text-[10px] text-danger">
                <AlertTriangle size={10} /> No PTZ or ROI available — controls disabled
              </div>
            )}
          </div>
        </div>

        {/* Command Path Truth — Section 5 */}
        <div className="border border-border rounded-lg overflow-hidden">
          <div className="flex items-center gap-2 px-3 py-2 bg-surface-hover/30">
            <Activity size={14} className="text-text-secondary" />
            <span className="text-xs font-medium text-text-secondary">Command Path</span>
          </div>
          <div className="p-2">
            <div className="grid grid-cols-2 gap-1">
              <MetricCell label="Path Ready" value={chainHealth.commandPathReady ? 'yes' : 'no'}
                color={chainHealth.commandPathReady ? 'ok' : 'danger'} />
              <MetricCell label="Beast" value={chainHealth.beastConnected ? 'connected' : 'offline'}
                color={chainHealth.beastConnected ? 'ok' : 'danger'} />
              <MetricCell label="Cmd RTT" value={avgRtt !== null ? `${avgRtt}ms` : '—'}
                color={avgRtt !== null ? (avgRtt < 80 ? 'ok' : avgRtt < 150 ? 'warn' : 'danger') : 'off'} />
              <MetricCell label="Authority" value={authority.current}
                color={authority.current === 'operator' ? 'ok' : authority.current === 'ai' ? 'warn' : undefined} />
              <MetricCell label="AI Enabled" value={authority.aiEnabled ? 'yes' : 'no'}
                color={authority.aiEnabled ? 'warn' : undefined} />
              <MetricCell label="Presets" value={
                presetsLoading ? 'loading...'
                  : presetsLoadError ? 'error'
                  : `${Object.keys(useVisionStore.getState().presets).length} loaded`}
                color={presetsLoadError ? 'danger' : presetsLoading ? 'warn' : 'ok'} />
            </div>
            {presetsLoadError && (
              <div className="flex items-center gap-1.5 px-2 pt-1">
                <span className="text-[10px] text-danger flex-1">{presetsLoadError}</span>
                <button onClick={handleRetryPresets} className="text-[10px] text-cyan hover:underline">Retry</button>
              </div>
            )}
          </div>
        </div>

        {/* Subsystem States */}
        <div className="border border-border rounded-lg overflow-hidden">
          <div className="flex items-center gap-2 px-3 py-2 bg-surface-hover/30">
            <Cpu size={14} className="text-text-secondary" />
            <span className="text-xs font-medium text-text-secondary">Subsystem States</span>
          </div>
          <div className="p-2 grid grid-cols-2 gap-1">
            <StatusCell label="Relay" ok={connected} />
            <StatusCell label="Beast" ok={chainHealth.beastConnected} />
            <StatusCell label="Camera" ok={chainHealth.cameraStreaming} />
            <StatusCell label="Detector" ok={det?.loaded ?? false} />
            <StatusCell label="Tracker" ok={det?.tracker_active ?? false} />
            <StatusCell label="PTZ" ok={hasPtzHardware || chainHealth.digitalRoiAvailable}
              warnLabel={!hasPtzHardware && chainHealth.digitalRoiAvailable ? 'ROI mode' : undefined} />
            <StatusCell label="Cmd Path" ok={chainHealth.commandPathReady} />
            <StatusCell label="Presets" ok={!presetsLoadError && Object.keys(useVisionStore.getState().presets).length > 0}
              warnLabel={presetsLoadError || undefined} />
            <StatusCell label="GPU"
              ok={det?.device === 'cuda'}
              warnLabel={det?.device === 'cpu' ? 'CPU fallback' : undefined} />
          </div>
        </div>
      </div>
    </div>
  )
}

function MetricCell({ label, value, color }: { label: string; value: string; color?: 'ok' | 'warn' | 'danger' | 'off' }) {
  const textCls = color === 'ok' ? 'text-ok' : color === 'warn' ? 'text-warning' : color === 'danger' ? 'text-danger' : 'text-text-primary'
  return (
    <div className="px-2 py-1">
      <div className="text-[9px] text-text-quaternary uppercase tracking-wider">{label}</div>
      <div className={clsx('text-[11px] font-mono', textCls)}>{value}</div>
    </div>
  )
}

function StatusCell({ label, ok, warnLabel }: { label: string; ok: boolean; warnLabel?: string }) {
  return (
    <div className="flex items-center gap-1.5 px-2 py-1">
      <span className={clsx('w-1.5 h-1.5 rounded-full shrink-0', ok ? 'bg-ok' : warnLabel ? 'bg-warning' : 'bg-danger')} />
      <span className="text-[10px] font-mono text-text-secondary">{label}</span>
      {warnLabel && <span className="text-[9px] text-warning">{warnLabel}</span>}
    </div>
  )
}
