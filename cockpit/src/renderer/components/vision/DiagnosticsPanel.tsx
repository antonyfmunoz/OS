import { useState } from 'react'
import { clsx } from 'clsx'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { useVisionStore, type MotionState, type StreamMetrics, type QualityMode } from '../../stores/visionStore'

const QUALITY_DESCRIPTIONS: Record<QualityMode, string> = {
  smooth: '720p 30fps',
  balanced: '720p 15fps',
  sharp: '1080p 10fps',
  analysis: '1080p 1fps',
}

export function DiagnosticsPanel({
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
            <span>ptz_mode: <span className={chainHealth.ptzMode === 'physical_ptz' ? 'text-ok' : 'text-cyan'}>{chainHealth.ptzMode}</span></span>
            <span>cmd_path: <span className={chainHealth.commandPathReady ? 'text-ok' : 'text-danger'}>{chainHealth.commandPathReady ? 'ready' : 'BLOCKED'}</span></span>
            {chainHealth.ptzMode === 'digital_roi' && (
              <>
                <span>roi_x: {chainHealth.roi.x.toFixed(3)}</span>
                <span>roi_y: {chainHealth.roi.y.toFixed(3)}</span>
                <span>roi_zoom: {chainHealth.roi.zoom.toFixed(2)}x</span>
              </>
            )}
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
