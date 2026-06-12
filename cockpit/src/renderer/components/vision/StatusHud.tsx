import { clsx } from 'clsx'
import { useVisionStore } from '../../stores/visionStore'

export function StatusHud() {
  const connected = useVisionStore((s) => s.connected)
  const streaming = useVisionStore((s) => s.streaming)
  const streamMetrics = useVisionStore((s) => s.streamMetrics)
  const chainHealth = useVisionStore((s) => s.chainHealth)
  const overlays = useVisionStore((s) => s.overlays)
  const width = useVisionStore((s) => s.width)
  const height = useVisionStore((s) => s.height)

  const frameAge = streamMetrics.lastFrameAge
  const frameFresh = frameAge > 0 && frameAge < 3000
  const hasRecentOverlays = chainHealth.lastOverlayAt > 0 && (Date.now() - chainHealth.lastOverlayAt) < 10000
  const beastEffective = chainHealth.beastConnected || (streaming && frameFresh) || hasRecentOverlays

  if (!connected) {
    return (
      <div className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-border bg-surface-hover/30">
        <span className="w-1.5 h-1.5 rounded-full bg-danger" />
        <span className="text-[10px] font-mono text-text-tertiary">relay offline</span>
      </div>
    )
  }

  if (!streaming || !frameFresh) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded border border-border bg-surface-hover/30">
        <span className="w-1.5 h-1.5 rounded-full bg-text-quaternary" />
        <span className="text-[10px] font-mono text-text-tertiary">no stream</span>
        {!beastEffective && (
          <>
            <span className="text-text-quaternary">·</span>
            <span className="text-[10px] font-mono text-danger">beast offline</span>
          </>
        )}
      </div>
    )
  }

  const resolutionStr = width > 0 && height > 0 ? `${width}x${height}` : '—'
  const fpsStr = `${streamMetrics.actualFps.toFixed(1)} fps`
  const latencyStr = frameAge < 1000 ? `${frameAge}ms` : `${(frameAge / 1000).toFixed(1)}s`
  const trackedStr = `${overlays.length} obj`

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2 px-3 py-1.5 rounded border border-border bg-surface-hover/30 flex-wrap">
        {/* Resolution */}
        <span className={clsx(
          'text-[10px] font-mono',
          width > 0 ? 'text-text-secondary' : 'text-text-tertiary',
        )}>
          {resolutionStr}
        </span>

        <span className="text-text-quaternary text-[10px]">·</span>

        {/* FPS */}
        <span className={clsx(
          'text-[10px] font-mono',
          streamMetrics.actualFps >= 10 ? 'text-ok' : streamMetrics.actualFps > 0 ? 'text-warning' : 'text-danger',
        )}>
          {fpsStr}
        </span>

        <span className="text-text-quaternary text-[10px]">·</span>

        {/* Latency */}
        <span className={clsx(
          'text-[10px] font-mono',
          frameAge < 500 ? 'text-ok' : frameAge < 2000 ? 'text-warning' : 'text-danger',
        )}>
          {latencyStr}
        </span>

        <span className="text-text-quaternary text-[10px]">·</span>

        {/* Beast */}
        <span className="flex items-center gap-1 text-[10px] font-mono">
          <span className={clsx('w-1.5 h-1.5 rounded-full', beastEffective ? 'bg-ok' : 'bg-danger')} />
          <span className={beastEffective ? 'text-ok' : 'text-danger'}>beast</span>
        </span>

        <span className="text-text-quaternary text-[10px]">·</span>

        {/* Object count */}
        <span className={clsx(
          'text-[10px] font-mono',
          overlays.length > 0 ? 'text-ok' : 'text-text-tertiary',
        )}>
          {trackedStr}
        </span>
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
