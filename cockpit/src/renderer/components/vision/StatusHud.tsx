import { clsx } from 'clsx'
import { useVisionStore, computeFrameFreshness, type ControlAuthority } from '../../stores/visionStore'

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

const AUTHORITY_LABELS: Record<ControlAuthority, string> = {
  operator: 'manual',
  voice: 'voice cmd',
  ai: 'ai control',
  autonomous: 'autonomous',
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
  const latestFrameAt = useVisionStore((s) => s.latestFrameAt)
  const latestFrameUrl = useVisionStore((s) => s.latestFrameUrl)
  const authority = useVisionStore((s) => s.authority)

  const frameAge = streamMetrics.lastFrameAge
  const freshness = computeFrameFreshness(frameAge, !!latestFrameUrl)
  const frameFresh = freshness === 'live'
  const hasRecentOverlays = chainHealth.lastOverlayAt > 0 && (Date.now() - chainHealth.lastOverlayAt) < 10000

  // ── Per-subsystem truth states ──
  const relayColor: StatusColor = connected ? 'ok' : 'danger'
  const relayLabel = connected ? 'relay' : 'relay offline'

  const beastEffective = chainHealth.beastConnected || (streaming && frameFresh) || hasRecentOverlays
  const beastColor: StatusColor = !connected ? 'off' : beastEffective ? 'ok' : 'danger'
  const beastLabel = !connected ? 'beast' : beastEffective ? 'beast' : 'beast offline'

  // Frame freshness truth — the core of Section 1
  const cameraColor: StatusColor =
    !connected ? 'off'
    : freshness === 'live' ? 'ok'
    : freshness === 'recent' ? 'ok'
    : freshness === 'stale' ? 'warn'
    : freshness === 'dead' ? 'danger'
    : 'off'
  const cameraLabel =
    !connected ? 'camera'
    : freshness === 'live' ? 'camera live'
    : freshness === 'recent' ? `camera ${(frameAge / 1000).toFixed(1)}s`
    : freshness === 'stale' ? 'STALE'
    : freshness === 'dead' ? 'NO LIVE STREAM'
    : streaming ? 'camera starting' : 'camera off'

  const detectorStatus = chainHealth.detectorStatus
  const detectorColor: StatusColor = !beastEffective ? 'off' : detectorStatus?.loaded ? 'ok' : 'warn'
  const detectorLabel = !beastEffective ? 'detector' : detectorStatus?.loaded ? `detector ${detectorStatus.avg_inference_ms.toFixed(0)}ms` : 'detector loading'

  const trackerColor: StatusColor = !beastEffective ? 'off' : detectorStatus?.tracker_active ? 'ok' : 'warn'
  const trackerLabel = !beastEffective ? 'tracker' : detectorStatus?.tracker_active
    ? `tracker ${detectorStatus.active_tracks}/${detectorStatus.total_tracks}`
    : 'tracker off'

  const ptzReady = connected && (chainHealth.beastConnected || chainHealth.commandPathReady)
  const ptzColor: StatusColor = !connected ? 'off' : ptzReady ? (hasPtzHardware ? 'ok' : chainHealth.digitalRoiAvailable ? 'warn' : 'off') : 'danger'
  const ptzLabel = !connected ? 'ptz' : !ptzReady ? 'ptz blocked' : hasPtzHardware ? 'ptz hw' : chainHealth.digitalRoiAvailable ? 'ptz digital' : 'ptz unavailable'

  const gpuDevice = detectorStatus?.device
  const gpuColor: StatusColor = !beastEffective ? 'off' : gpuDevice === 'cuda' ? 'ok' : gpuDevice === 'cpu' ? 'warn' : 'off'
  const gpuLabel = !beastEffective ? 'gpu' : gpuDevice === 'cuda' ? 'gpu cuda' : gpuDevice === 'cpu' ? 'gpu → cpu' : 'gpu unknown'

  const secColor: StatusColor = securityMode.active ? 'danger' : 'off'
  const secLabel = securityMode.active ? `security: ${securityMode.mode}` : 'security off'

  // Command path truth — Section 5
  const cmdPathColor: StatusColor = !connected ? 'off' : chainHealth.commandPathReady ? 'ok' : chainHealth.beastConnected ? 'warn' : 'danger'
  const cmdPathLabel = !connected ? 'cmd path' : chainHealth.commandPathReady ? 'cmd ready' : chainHealth.beastConnected ? 'cmd degraded' : 'cmd blocked'

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
        <span className={clsx('text-[10px] font-mono',
          freshness === 'live' ? 'text-ok'
          : freshness === 'recent' ? 'text-warning'
          : freshness === 'stale' ? 'text-danger'
          : 'text-danger'
        )}>
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
        {/* Authority indicator */}
        <span className="text-text-quaternary text-[10px]">·</span>
        <span className={clsx('text-[10px] font-mono',
          authority.current === 'operator' ? 'text-text-secondary'
          : authority.current === 'voice' ? 'text-cyan'
          : authority.current === 'ai' ? 'text-warning'
          : 'text-danger'
        )}>
          {AUTHORITY_LABELS[authority.current]}
        </span>
      </div>

      {/* Subsystem truth states */}
      <div className="flex items-center gap-2 px-3 py-1 rounded border border-border bg-surface-hover/20 flex-wrap">
        <StatusChip label={relayLabel} color={relayColor} />
        <StatusChip label={beastLabel} color={beastColor} />
        <StatusChip label={cameraLabel} color={cameraColor} detail={`Frame age: ${frameAge}ms | Freshness: ${freshness}`} />
        <StatusChip label={detectorLabel} color={detectorColor} />
        <StatusChip label={trackerLabel} color={trackerColor} />
        <StatusChip label={ptzLabel} color={ptzColor} />
        <StatusChip label={cmdPathLabel} color={cmdPathColor} />
        <StatusChip label={gpuLabel} color={gpuColor} />
        <StatusChip label={secLabel} color={secColor} />
        {followMode.active && <StatusChip label={`follow: ${followMode.target}`} color="ok" />}
      </div>

      {/* Stale frame warning banner — prominent */}
      {(freshness === 'stale' || freshness === 'dead') && latestFrameUrl && (
        <div className={clsx(
          'flex items-center gap-2 px-3 py-1.5 rounded text-[11px] font-mono uppercase tracking-wider',
          freshness === 'stale' ? 'bg-warning/10 text-warning border border-warning/30' : 'bg-danger/10 text-danger border border-danger/30',
        )}>
          <span className={clsx('w-2 h-2 rounded-full', freshness === 'stale' ? 'bg-warning animate-pulse' : 'bg-danger')} />
          {freshness === 'stale' ? `last frame ${(frameAge / 1000).toFixed(1)}s ago — image may not reflect reality` : 'no live stream — showing last captured frame'}
          {!chainHealth.beastConnected && ' — beast offline'}
        </div>
      )}

      {/* Command path blocked banner */}
      {connected && !chainHealth.commandPathReady && !chainHealth.beastConnected && (
        <div className="flex items-center gap-2 px-3 py-1 rounded bg-danger/5 text-[10px] font-mono text-danger border border-danger/20">
          controls disabled — Beast offline, no command path available
        </div>
      )}

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
