import { useMemo } from 'react'
import { clsx } from 'clsx'
import { useVisionStore, computeFrameFreshness, type ControlAuthority } from '../../stores/visionStore'

type StatusColor = 'ok' | 'warn' | 'danger' | 'off'

function Dot({ color }: { color: StatusColor }) {
  const bg = color === 'ok' ? 'bg-ok' : color === 'warn' ? 'bg-warning' : color === 'danger' ? 'bg-danger' : 'bg-text-quaternary'
  return <span className={clsx('w-1.5 h-1.5 rounded-full shrink-0', bg)} />
}

function DomainChip({ label, state, color }: { label: string; state: string; color: StatusColor }) {
  const textCls = color === 'ok' ? 'text-ok' : color === 'warn' ? 'text-warning' : color === 'danger' ? 'text-danger' : 'text-text-quaternary'
  return (
    <span className="flex items-center gap-1.5 text-[10px] font-mono">
      <Dot color={color} />
      <span className="text-text-tertiary uppercase tracking-wider" style={{ fontSize: '9px' }}>{label}</span>
      <span className={textCls}>{state}</span>
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
  const followMode = useVisionStore((s) => s.followMode)
  const latestFrameAt = useVisionStore((s) => s.latestFrameAt)
  const latestFrameUrl = useVisionStore((s) => s.latestFrameUrl)
  const authority = useVisionStore((s) => s.authority)

  const fps = streamMetrics.actualFps
  const frameAge = streamMetrics.lastFrameAge
  const freshness = computeFrameFreshness(frameAge, !!latestFrameUrl)

  // ── 5 independent state domains ──
  // Each derives ONLY from its own source. No cross-contamination.

  // 1. VIDEO — from frame timestamps only
  const videoColor: StatusColor =
    !connected ? 'off'
    : freshness === 'live' || freshness === 'recent' ? 'ok'
    : freshness === 'stale' ? 'warn'
    : freshness === 'dead' ? 'danger'
    : streaming ? 'warn' : 'off'
  const videoState =
    !connected ? 'OFFLINE'
    : freshness === 'live' ? 'LIVE'
    : freshness === 'recent' ? 'LIVE'
    : freshness === 'stale' ? 'STALE'
    : freshness === 'dead' ? 'OFFLINE'
    : streaming ? 'STARTING' : 'OFFLINE'

  // 2. CONTROL — from command path only
  const controlColor: StatusColor =
    !connected ? 'off'
    : chainHealth.commandPathReady ? 'ok'
    : chainHealth.beastConnected ? 'warn'
    : 'danger'
  const controlState =
    !connected ? 'OFFLINE'
    : chainHealth.commandPathReady ? 'READY'
    : chainHealth.beastConnected ? 'DEGRADED'
    : 'OFFLINE'

  // 3. PTZ — from PTZ hardware/ROI flags only
  const ptzColor: StatusColor =
    !connected ? 'off'
    : !chainHealth.commandPathReady ? 'danger'
    : hasPtzHardware ? 'ok'
    : chainHealth.digitalRoiAvailable ? 'warn'
    : 'off'
  const ptzState =
    !connected ? 'OFF'
    : !chainHealth.commandPathReady ? 'BLOCKED'
    : hasPtzHardware ? 'READY'
    : chainHealth.digitalRoiAvailable ? 'ROI'
    : 'UNAVAILABLE'

  // 4. DETECTOR — from detector status reports only
  const det = chainHealth.detectorStatus
  const detectorColor: StatusColor =
    det === null ? 'off'
    : det.loaded ? 'ok'
    : 'warn'
  const detectorState =
    det === null ? 'OFF'
    : det.loaded ? 'ACTIVE'
    : 'LOADING'

  // 5. TRACKER — from tracker reports only
  const trackerColor: StatusColor =
    det === null ? 'off'
    : det.tracker_active ? 'ok'
    : 'off'
  const trackerState =
    det === null ? 'OFF'
    : det.tracker_active ? `ACTIVE ${det.active_tracks}`
    : 'IDLE'

  // Derived display values
  const resolutionStr = width > 0 && height > 0 ? `${width}x${height}` : streaming ? '—' : '—'
  const fpsStr = `${fps.toFixed(1)} fps`
  const latencyStr = frameAge < 1000 ? `${frameAge}ms` : `${(frameAge / 1000).toFixed(1)}s`
  const bitrateStr = streamMetrics.bitrateKbps > 1024
    ? `${(streamMetrics.bitrateKbps / 1024).toFixed(1)} Mbps`
    : `${streamMetrics.bitrateKbps} Kbps`

  // Overall summary — only OFFLINE when both video and control are offline
  const allOffline = videoState === 'OFFLINE' && controlState === 'OFFLINE'
  const allReady = videoState === 'LIVE' && controlState === 'READY'
  const summaryColor = allOffline ? 'danger' : allReady ? 'ok' : 'warn'
  const summaryBg = allOffline
    ? 'bg-danger/10 border-danger/30'
    : allReady
      ? 'bg-ok/10 border-ok/30'
      : 'bg-warning/10 border-warning/30'
  const summaryDot = allOffline ? 'bg-danger' : allReady ? 'bg-ok' : 'bg-warning animate-pulse'
  const summaryText = allOffline
    ? 'text-danger'
    : allReady
      ? 'text-ok'
      : 'text-warning'
  const summaryLabel = allOffline ? 'OFFLINE' : allReady ? 'READY' : 'DEGRADED'
  const summaryReason = useMemo(() => {
    if (allOffline) return !connected ? 'Relay disconnected' : 'No video or control'
    if (allReady) return 'All systems operational'
    const issues: string[] = []
    if (videoState !== 'LIVE') issues.push(`video ${videoState.toLowerCase()}`)
    if (controlState !== 'READY') issues.push(`control ${controlState.toLowerCase()}`)
    if (ptzState === 'BLOCKED') issues.push('ptz blocked')
    return issues.join(' · ') || 'Partial functionality'
  }, [allOffline, allReady, connected, videoState, controlState, ptzState])

  if (!connected) {
    return (
      <div className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-border bg-surface-hover/30">
        <Dot color="danger" />
        <span className="text-[10px] font-mono text-danger">relay offline</span>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-1">
      {/* Summary — OFFLINE only when no video AND no control */}
      <div className={clsx('flex items-center gap-2 px-3 py-1 rounded border', summaryBg)}>
        <span className={clsx('w-2 h-2 rounded-full', summaryDot)} />
        <span className={clsx('text-[11px] font-mono font-bold tracking-wide', summaryText)}>
          {summaryLabel}
        </span>
        <span className="text-[10px] font-mono text-text-tertiary flex-1">{summaryReason}</span>
      </div>

      {/* 5-domain subsystem states */}
      <div className="flex items-center gap-3 px-3 py-1.5 rounded border border-border bg-surface-hover/20 flex-wrap">
        <DomainChip label="video" state={videoState} color={videoColor} />
        <DomainChip label="control" state={controlState} color={controlColor} />
        <DomainChip label="ptz" state={ptzState} color={ptzColor} />
        <DomainChip label="detector" state={detectorState} color={detectorColor} />
        <DomainChip label="tracker" state={trackerState} color={trackerColor} />
        {followMode.active && <DomainChip label="follow" state={followMode.target} color="ok" />}
      </div>

      {/* Metrics row — only when video has frames */}
      {(fps > 0 || freshness === 'live' || freshness === 'recent') && (
        <div className="flex items-center gap-2 px-3 py-1 rounded border border-border bg-surface-hover/30 flex-wrap">
          <span className={clsx('text-[10px] font-mono', width > 0 ? 'text-text-secondary' : 'text-text-tertiary')}>
            {resolutionStr}
          </span>
          <span className="text-text-quaternary text-[10px]">·</span>
          <span className={clsx('text-[10px] font-mono', fps >= 10 ? 'text-ok' : fps > 0 ? 'text-warning' : 'text-danger')}>
            {fpsStr}
          </span>
          <span className="text-text-quaternary text-[10px]">·</span>
          <span className={clsx('text-[10px] font-mono',
            freshness === 'live' ? 'text-ok' : freshness === 'recent' ? 'text-warning' : 'text-danger',
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
          <span className="text-text-quaternary text-[10px]">·</span>
          <span className={clsx('text-[10px] font-mono',
            authority.current === 'operator' ? 'text-text-secondary'
            : authority.current === 'voice' ? 'text-cyan'
            : authority.current === 'ai' ? 'text-warning'
            : 'text-danger',
          )}>
            {AUTHORITY_LABELS[authority.current]}
          </span>
        </div>
      )}

      {/* Stale frame warning — prominent */}
      {(freshness === 'stale' || freshness === 'dead') && latestFrameUrl && (
        <div className={clsx(
          'flex items-center gap-2 px-3 py-1.5 rounded text-[11px] font-mono uppercase tracking-wider',
          freshness === 'stale' ? 'bg-warning/10 text-warning border border-warning/30' : 'bg-danger/10 text-danger border border-danger/30',
        )}>
          <span className={clsx('w-2 h-2 rounded-full', freshness === 'stale' ? 'bg-warning animate-pulse' : 'bg-danger')} />
          {freshness === 'stale' ? `last frame ${(frameAge / 1000).toFixed(1)}s ago — image may not reflect reality` : 'no live stream — showing last captured frame'}
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
