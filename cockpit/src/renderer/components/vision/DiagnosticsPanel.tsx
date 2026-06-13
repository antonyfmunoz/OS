import { useState } from 'react'
import { clsx } from 'clsx'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { useVisionStore, type MotionState, type StreamMetrics, type QualityMode } from '../../stores/visionStore'

const QUALITY_DESCRIPTIONS: Record<QualityMode, string> = {
  smooth: '720p 30fps',
  balanced: '720p 15fps',
  high: '1080p 10fps',
  analysis: '1080p 1fps',
}

export function DiagnosticsPanel({
  ptzMotion, controlMetrics, joystickDragging, joystickVelocity,
  speed, overlays, overlayVisible, connected,
  streaming, streamMetrics, frameCount, qualityMode,
}: {
  ptzMotion: { state: MotionState; motionId: string; panVelocity: number; tiltVelocity: number; zoomVelocity: number }
  controlMetrics: { ptzLoopCadenceHz: number; stopLatencyMs: number; guardTimeouts: number; lastCommandSentAt: number; coalescedCommands: number; lastStopSentAt: number }
  joystickDragging: boolean
  joystickVelocity: { pan: number; tilt: number }
  speed: number
  overlays: unknown[]
  overlayVisible: boolean
  connected: boolean
  streaming: boolean
  streamMetrics: StreamMetrics
  frameCount: number
  qualityMode: QualityMode
}) {
  const chainHealth = useVisionStore((s) => s.chainHealth)
  const trackerStack = useVisionStore((s) => s.trackerStack)
  const latencyHistory = useVisionStore((s) => s.latencyHistory)
  const labelCorrections = useVisionStore((s) => s.labelCorrections)
  const authorityLog = useVisionStore((s) => s.authority.log)
  const [expanded, setExpanded] = useState(false)

  const enabledTrackers = trackerStack.enabled_trackers.filter((t) => t.enabled)

  const avgLatency = latencyHistory.length > 0
    ? Math.round(latencyHistory.reduce((sum, m) => sum + m.roundTripMs, 0) / latencyHistory.length)
    : 0
  const maxLatency = latencyHistory.length > 0
    ? Math.max(...latencyHistory.map((m) => m.roundTripMs))
    : 0

  const cmdAge = controlMetrics.lastCommandSentAt > 0
    ? Math.round((Date.now() - controlMetrics.lastCommandSentAt) / 1000)
    : -1

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
        {controlMetrics.stopLatencyMs > 0 ? ` [${controlMetrics.stopLatencyMs}ms]` : ''}
      </button>

      {expanded && (
        <div className="mt-2 flex flex-col gap-2">
          {/* Stream metrics */}
          <div className="grid grid-cols-3 gap-x-4 gap-y-1 text-[10px] font-mono text-text-tertiary">
            <span>FPS: <span className={streamMetrics.actualFps > 0 ? 'text-ok' : 'text-text-secondary'}>{streamMetrics.actualFps.toFixed(1)}</span> / {streamMetrics.targetFps}</span>
            <span>Frame: {Math.round(streamMetrics.avgFrameSize / 1024)} KB</span>
            <span>Age: {streamMetrics.lastFrameAge < 1000 ? `${streamMetrics.lastFrameAge}ms` : `${(streamMetrics.lastFrameAge / 1000).toFixed(1)}s`}</span>
            <span>Bitrate: <span className={streamMetrics.bitrateKbps > 0 ? 'text-ok' : 'text-text-secondary'}>{streamMetrics.bitrateKbps > 1024 ? `${(streamMetrics.bitrateKbps / 1024).toFixed(1)} Mbps` : `${streamMetrics.bitrateKbps} Kbps`}</span></span>
            <span>Frames: {frameCount} <span className={streamMetrics.droppedFrames > 0 ? 'text-warning' : ''}>({streamMetrics.droppedFrames} dropped)</span></span>
            <span>Quality: {QUALITY_DESCRIPTIONS[qualityMode]}</span>
          </div>

          {/* Command latency — prominent */}
          <div className="grid grid-cols-3 gap-x-4 gap-y-0.5 text-[9px] font-mono border border-dashed border-cyan/30 rounded p-2">
            <span className="text-text-quaternary">stop_rtt: <span className={clsx(
              controlMetrics.stopLatencyMs > 150 ? 'text-danger' : controlMetrics.stopLatencyMs > 80 ? 'text-warning' : 'text-ok',
            )}>{controlMetrics.stopLatencyMs > 0 ? `${controlMetrics.stopLatencyMs}ms` : '—'}</span></span>
            <span className="text-text-quaternary">avg_rtt: <span className={clsx(
              avgLatency > 150 ? 'text-danger' : avgLatency > 80 ? 'text-warning' : 'text-ok',
            )}>{avgLatency > 0 ? `${avgLatency}ms` : '—'}</span></span>
            <span className="text-text-quaternary">max_rtt: <span className={clsx(
              maxLatency > 200 ? 'text-danger' : maxLatency > 100 ? 'text-warning' : 'text-ok',
            )}>{maxLatency > 0 ? `${maxLatency}ms` : '—'}</span></span>
            <span className="text-text-quaternary">samples: {latencyHistory.length}</span>
            <span className="text-text-quaternary">update_hz: 30</span>
            <span className="text-text-quaternary">coalesced: {controlMetrics.coalescedCommands}</span>
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
            <span>guard_kills: <span className={controlMetrics.guardTimeouts > 0 ? 'text-danger' : ''}>{controlMetrics.guardTimeouts}</span></span>
            <span>last_cmd: {cmdAge >= 0 ? `${cmdAge}s ago` : '—'}</span>
            <span>ws: {connected ? 'connected' : 'DISCONNECTED'}</span>
            <span>labels_corrected: {Object.keys(labelCorrections).length}</span>
          </div>

          {/* Chain health */}
          <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[9px] font-mono text-text-quaternary border border-dashed border-warning/30 rounded p-2">
            <span>overlay_visible: <span className={overlayVisible ? 'text-ok' : 'text-danger'}>{overlayVisible ? 'ON' : 'OFF'}</span></span>
            <span>overlay_count: <span className={overlays.length > 0 ? 'text-ok' : ''}>{overlays.length}</span></span>
            <span>last_overlay: {chainHealth.lastOverlayAt > 0 ? `${Math.round((Date.now() - chainHealth.lastOverlayAt) / 1000)}s ago` : 'never'}</span>
            <span>tracker_runtime: <span className={chainHealth.trackerRuntimeAvailable ? 'text-ok' : 'text-danger'}>{chainHealth.trackerRuntimeAvailable ? 'available' : 'UNAVAILABLE'}</span></span>
            <span>enabled_trackers: {enabledTrackers.length > 0 ? enabledTrackers.map((t) => t.category).join(', ') : 'none'}</span>
            <span>beast: <span className={chainHealth.beastConnected ? 'text-ok' : 'text-danger'}>{chainHealth.beastConnected ? 'connected' : 'OFFLINE'}</span></span>
            <span>camera: <span className={chainHealth.cameraStreaming ? 'text-ok' : 'text-danger'}>{chainHealth.cameraStreaming ? 'streaming' : chainHealth.cameraAvailable ? 'available' : 'UNAVAILABLE'}</span></span>
            <span>ptz_mode: <span className={chainHealth.ptzMode === 'physical_ptz' ? 'text-ok' : 'text-cyan'}>{chainHealth.ptzMode}</span></span>
            <span>cmd_path: <span className={chainHealth.commandPathReady ? 'text-ok' : 'text-danger'}>{chainHealth.commandPathReady ? 'ready' : 'BLOCKED'}</span></span>
            <span>dispatch_rtt: <span className={clsx(
              chainHealth.lastDispatchRttMs > 500 ? 'text-danger' : chainHealth.lastDispatchRttMs > 100 ? 'text-warning' : 'text-ok',
            )}>{chainHealth.lastDispatchRttMs > 0 ? `${chainHealth.lastDispatchRttMs}ms` : '—'}</span></span>
            <span>last_op: {chainHealth.lastDispatchOperation || '—'}</span>
            <span>dispatch_ok: {chainHealth.lastDispatchOkAt > 0 ? `${Math.round(Date.now() / 1000 - chainHealth.lastDispatchOkAt)}s ago` : 'never'}</span>
            {chainHealth.ptzMode === 'digital_roi' && (
              <>
                <span>roi_x: {chainHealth.roi.x.toFixed(3)}</span>
                <span>roi_y: {chainHealth.roi.y.toFixed(3)}</span>
                <span>roi_zoom: {chainHealth.roi.zoom.toFixed(2)}x</span>
              </>
            )}
          </div>

          {/* Detector status */}
          {chainHealth.detectorStatus && (
            <div className="grid grid-cols-3 gap-x-4 gap-y-0.5 text-[9px] font-mono text-text-quaternary border border-dashed border-border/50 rounded p-2">
              <span>detector: <span className={chainHealth.detectorStatus.loaded ? 'text-ok' : 'text-danger'}>{chainHealth.detectorStatus.loaded ? chainHealth.detectorStatus.model : 'NOT LOADED'}</span></span>
              <span>device: <span className={clsx(
                chainHealth.detectorStatus.device === 'cuda' && 'text-ok',
                chainHealth.detectorStatus.device === 'cuda-infer/cpu-nms' && 'text-warning',
                chainHealth.detectorStatus.device === 'cpu' && 'text-text-secondary',
              )}>{chainHealth.detectorStatus.device || 'unknown'}</span></span>
              <span>infer: {chainHealth.detectorStatus.avg_inference_ms > 0 ? `${chainHealth.detectorStatus.avg_inference_ms.toFixed(0)}ms avg` : '—'}</span>
              <span>frames: {chainHealth.detectorStatus.detection_frames}</span>
              <span>tracks: {chainHealth.detectorStatus.active_tracks}</span>
              {chainHealth.detectorStatus.nms_fallback && <span className="text-warning">NMS: CPU fallback</span>}
            </div>
          )}

          {/* Blockers */}
          {chainHealth.blockers.length > 0 && (
            <div className="text-[9px] font-mono text-danger/80 bg-danger/5 rounded p-1.5">
              {chainHealth.blockers.map((b, i) => <div key={i}>{b}</div>)}
              {chainHealth.recoveryAction && (
                <div className="text-warning/80 mt-0.5">{chainHealth.recoveryAction}</div>
              )}
            </div>
          )}

          {/* Authority audit log */}
          {authorityLog.length > 0 && (
            <div className="text-[9px] font-mono border border-dashed border-border/50 rounded p-2">
              <span className="text-text-quaternary uppercase tracking-wider block mb-1">authority log ({authorityLog.length})</span>
              {authorityLog.slice(-10).reverse().map((entry, i) => (
                <div key={i} className="flex gap-2 text-text-quaternary">
                  <span className="shrink-0">{new Date(entry.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                  <span className={clsx(
                    entry.to === 'ai' && 'text-warning',
                    entry.to === 'operator' && 'text-ok',
                    entry.to === 'voice' && 'text-cyan',
                  )}>{entry.from} → {entry.to}</span>
                  {entry.reason && <span className="text-text-quaternary truncate">{entry.reason}</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
