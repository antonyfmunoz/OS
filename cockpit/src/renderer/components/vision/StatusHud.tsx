import { clsx } from 'clsx'
import { useVisionStore } from '../../stores/visionStore'

type StatusColor = 'ok' | 'warn' | 'danger' | 'off'

function Dot({ color }: { color: StatusColor }) {
  const bg = color === 'ok' ? 'bg-ok' : color === 'warn' ? 'bg-warning' : color === 'danger' ? 'bg-danger' : 'bg-text-quaternary'
  return <span className={clsx('w-1.5 h-1.5 rounded-full shrink-0', bg)} />
}

function StatusChip({ label, color, detail }: { label: string; color: StatusColor; detail?: string }) {
  const textCls = color === 'ok' ? 'text-ok' : color === 'warn' ? 'text-warning' : color === 'danger' ? 'text-danger' : 'text-text-quaternary'
  return (
    <span className="flex items-center gap-1 text-[10px] font-mono" title={detail}>
      <Dot color={color} />
      <span className={textCls}>{label}</span>
    </span>
  )
}

export function StatusHud() {
  const connected = useVisionStore((s) => s.connected)
  const streaming = useVisionStore((s) => s.streaming)
  const streamMetrics = useVisionStore((s) => s.streamMetrics)
  const chainHealth = useVisionStore((s) => s.chainHealth)
  const overlays = useVisionStore((s) => s.overlays)
  const width = useVisionStore((s) => s.width)
  const height = useVisionStore((s) => s.height)
  const hasPtzHardware = useVisionStore((s) => s.hasPtzHardware)
  const securityMode = useVisionStore((s) => s.securityMode)
  const followMode = useVisionStore((s) => s.followMode)

  const frameAge = streamMetrics.lastFrameAge
  const frameFresh = frameAge > 0 && frameAge < 3000
  const hasRecentOverlays = chainHealth.lastOverlayAt > 0 && (Date.now() - chainHealth.lastOverlayAt) < 10000

  // ── Per-subsystem truth states ──
  const relayColor: StatusColor = connected ? 'ok' : 'danger'
  const relayLabel = connected ? 'relay' : 'relay offline'

  const beastEffective = chainHealth.beastConnected || (streaming && frameFresh) || hasRecentOverlays
  const beastColor: StatusColor = !connected ? 'off' : beastEffective ? 'ok' : 'danger'
  const beastLabel = !connected ? 'beast' : beastEffective ? 'beast' : 'beast offline'

  const cameraColor: StatusColor = !connected ? 'off' : streaming && frameFresh ? 'ok' : streaming ? 'warn' : 'off'
  const cameraLabel = !connected ? 'camera' : streaming && frameFresh ? 'camera live' : streaming ? 'camera stale' : 'camera off'

  const detectorStatus = chainHealth.detectorStatus
  const detectorColor: StatusColor = !beastEffective ? 'off' : detectorStatus?.loaded ? 'ok' : 'warn'
  const detectorLabel = !beastEffective ? 'detector' : detectorStatus?.loaded ? `detector ${detectorStatus.avg_inference_ms.toFixed(0)}ms` : 'detector loading'

  const trackerColor: StatusColor = !beastEffective ? 'off' : detectorStatus?.tracker_active ? 'ok' : 'warn'
  const trackerLabel = !beastEffective ? 'tracker' : detectorStatus?.tracker_active
    ? `tracker ${detectorStatus.active_tracks}/${detectorStatus.total_tracks}`
    : 'tracker off'

  const ptzColor: StatusColor = !connected ? 'off' : hasPtzHardware ? 'ok' : chainHealth.digitalRoiAvailable ? 'warn' : 'off'
  const ptzLabel = !connected ? 'ptz' : hasPtzHardware ? 'ptz hw' : chainHealth.digitalRoiAvailable ? 'ptz digital' : 'ptz unavailable'

  const secColor: StatusColor = securityMode.active ? 'danger' : 'off'
  const secLabel = securityMode.active ? `security: ${securityMode.mode}` : 'security off'

  if (!connected) {
    return (
      <div className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-border bg-surface-hover/30">
        <StatusChip label={relayLabel} color={relayColor} />
      </div>
    )
  }

  const resolutionStr = width > 0 && height > 0 ? `${width}x${height}` : '—'
  const fpsStr = `${streamMetrics.actualFps.toFixed(1)} fps`
  const latencyStr = frameAge < 1000 ? `${frameAge}ms` : `${(frameAge / 1000).toFixed(1)}s`
  const bitrateStr = streamMetrics.bitrateKbps > 1024
    ? `${(streamMetrics.bitrateKbps / 1024).toFixed(1)} Mbps`
    : `${streamMetrics.bitrateKbps} Kbps`

  return (
    <div className="flex flex-col gap-1">
      {/* Metrics row */}
      <div className="flex items-center gap-2 px-3 py-1.5 rounded border border-border bg-surface-hover/30 flex-wrap">
        <span className={clsx('text-[10px] font-mono', width > 0 ? 'text-text-secondary' : 'text-text-tertiary')}>
          {resolutionStr}
        </span>
        <span className="text-text-quaternary text-[10px]">·</span>
        <span className={clsx('text-[10px] font-mono', streamMetrics.actualFps >= 10 ? 'text-ok' : streamMetrics.actualFps > 0 ? 'text-warning' : 'text-danger')}>
          {fpsStr}
        </span>
        <span className="text-text-quaternary text-[10px]">·</span>
        <span className={clsx('text-[10px] font-mono', frameAge < 500 ? 'text-ok' : frameAge < 2000 ? 'text-warning' : 'text-danger')}>
          {latencyStr}
        </span>
        <span className="text-text-quaternary text-[10px]">·</span>
        <span className={clsx('text-[10px] font-mono', streamMetrics.bitrateKbps > 0 ? 'text-text-secondary' : 'text-text-tertiary')}>
          {bitrateStr}
        </span>
        <span className="text-text-quaternary text-[10px]">·</span>
        <span className={clsx('text-[10px] font-mono', overlays.length > 0 ? 'text-ok' : 'text-text-tertiary')}>
          {overlays.length} obj
        </span>
      </div>

      {/* Subsystem truth states */}
      <div className="flex items-center gap-2 px-3 py-1 rounded border border-border bg-surface-hover/20 flex-wrap">
        <StatusChip label={relayLabel} color={relayColor} />
        <StatusChip label={beastLabel} color={beastColor} />
        <StatusChip label={cameraLabel} color={cameraColor} />
        <StatusChip label={detectorLabel} color={detectorColor} />
        <StatusChip label={trackerLabel} color={trackerColor} />
        <StatusChip label={ptzLabel} color={ptzColor} />
        <StatusChip label={secLabel} color={secColor} />
        {followMode.active && <StatusChip label={`follow: ${followMode.target}`} color="ok" />}
      </div>

      {/* Blocker messages */}
      {chainHealth.blockers.length > 0 && (
        <div className="flex flex-col gap-0.5">
          {chainHealth.blockers.map((blocker, i) => (
            <span key={i} className="text-[10px] font-mono text-warning px-3">
              {blocker}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
