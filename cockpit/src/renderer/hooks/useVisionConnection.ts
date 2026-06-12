import { useEffect, useRef } from 'react'
import { VisionWsClient } from '../api/vision-ws'
import {
  useVisionStore,
  QUALITY_PROFILES,
  shouldAutoStartCamera,
  loadPresetsFromStorage,
  type CameraPreset,
  type TrackedObjectState,
  type WatchItemState,
  type FollowModeState,
  type TrackerConfigState,
  type VisionPresetInfo,
  type TriggerChainInfo,
  type ChainFireInfo,
  type VisionChainStatus,
  type MotionState,
} from '../stores/visionStore'

let _client: VisionWsClient | null = null

export function getVisionClient(): VisionWsClient | null {
  return _client
}

export function useVisionConnection(): void {
  const setConnected = useVisionStore((s) => s.setConnected)
  const setStreaming = useVisionStore((s) => s.setStreaming)
  const setCameraStatus = useVisionStore((s) => s.setCameraStatus)
  const setLatestFrame = useVisionStore((s) => s.setLatestFrame)
  const setError = useVisionStore((s) => s.setError)
  const setPresets = useVisionStore((s) => s.setPresets)
  const incrementFrameCount = useVisionStore((s) => s.incrementFrameCount)
  const setPtzPosition = useVisionStore((s) => s.setPtzPosition)
  const setPtzMoving = useVisionStore((s) => s.setPtzMoving)
  const setHasPtzHardware = useVisionStore((s) => s.setHasPtzHardware)
  const updateStreamMetrics = useVisionStore((s) => s.updateStreamMetrics)
  const setAnalysisResult = useVisionStore((s) => s.setAnalysisResult)
  const setAnalysisStatus = useVisionStore((s) => s.setAnalysisStatus)
  const updateSceneState = useVisionStore((s) => s.updateSceneState)
  const setTrackedObjects = useVisionStore((s) => s.setTrackedObjects)
  const setFollowMode = useVisionStore((s) => s.setFollowMode)
  const updateTrackerStack = useVisionStore((s) => s.updateTrackerStack)
  const setVisionPresets = useVisionStore((s) => s.setVisionPresets)
  const setActiveVisionPresetId = useVisionStore((s) => s.setActiveVisionPresetId)
  const setTriggerChains = useVisionStore((s) => s.setTriggerChains)
  const setRecentFires = useVisionStore((s) => s.setRecentFires)
  const setLastChainExplanation = useVisionStore((s) => s.setLastChainExplanation)
  const setSecurityMode = useVisionStore((s) => s.setSecurityMode)
  const updateChainHealth = useVisionStore((s) => s.updateChainHealth)
  const setDetectedObjects = useVisionStore((s) => s.setDetectedObjects)
  const setOverlays = useVisionStore((s) => s.setOverlays)
  const setPtzMotion = useVisionStore((s) => s.setPtzMotion)
  const updateControlMetrics = useVisionStore((s) => s.updateControlMetrics)
  const setViewerCount = useVisionStore((s) => s.setViewerCount)
  const setCameraSessionActive = useVisionStore((s) => s.setCameraSessionActive)
  const recordLatency = useVisionStore((s) => s.recordLatency)
  const addNotification = useVisionStore((s) => s.addNotification)
  const addToast = useVisionStore((s) => s.addToast)
  const reset = useVisionStore((s) => s.reset)

  const metricsInterval = useRef<ReturnType<typeof setInterval> | null>(null)
  const sceneInterval = useRef<ReturnType<typeof setInterval> | null>(null)
  const healthInterval = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!_client) _client = new VisionWsClient()
    const client = _client

    // Debounce camera_start on reconnects.
    // Without this guard the camera_start + vision_subscribe pair fires on every
    // WS reconnect, producing the loop visible in the console on real devices.
    // Strategy: allow camera_start only if we have been connected for ≥1s
    // (i.e. not a rapid flap) and the camera was not already running.
    let cameraStartedInSession = false
    let connectedAt = 0
    let cameraStartDebounceTimer: ReturnType<typeof setTimeout> | null = null
    let lastBeastConnected: boolean | null = null
    let lastCameraStreaming: boolean | null = null

    const profile = QUALITY_PROFILES[useVisionStore.getState().qualityMode]

    const unsubs = [
      client.on('connected', () => {
        connectedAt = Date.now()
        setConnected(true)
        setCameraSessionActive(true)
        setError(null)
        addNotification('info', 'Vision relay connected', 'relay', 'WebSocket connection established', 'monitoring')
        client.requestPresets()
        client.requestStatus()
        client.requestPosition()
        client.requestHealth()

        const policy = useVisionStore.getState().defaultOnPolicy
        if (shouldAutoStartCamera(policy) && !cameraStartedInSession) {
          // Debounce: wait 800ms before starting camera so rapid reconnect flaps
          // do not each trigger a full camera_start cycle.
          if (cameraStartDebounceTimer) clearTimeout(cameraStartDebounceTimer)
          cameraStartDebounceTimer = setTimeout(() => {
            // Re-check: still connected, still no session started
            if (!client.connected || cameraStartedInSession) return
            cameraStartedInSession = true
            client.startCamera({
              fps: profile.fps,
              width: profile.width,
              height: profile.height,
              quality: profile.quality,
            })
            client.subscribe(profile.fps, profile.quality)
          }, 800)
        }
        client.requestSceneState()
        client.requestLabelCorrections()
        setPtzMotion({ state: 'idle', motionId: '', panVelocity: 0, tiltVelocity: 0, zoomVelocity: 0 })
      }),
      client.on('disconnected', () => {
        if (cameraStartDebounceTimer) {
          clearTimeout(cameraStartDebounceTimer)
          cameraStartDebounceTimer = null
        }
        setConnected(false)
        setCameraStatus('off')
        setStreaming(false)
        setCameraSessionActive(false)
        cameraStartedInSession = false
        connectedAt = 0
        setPtzMotion({ state: 'disconnected', motionId: '', panVelocity: 0, tiltVelocity: 0, zoomVelocity: 0 })
        updateChainHealth({ status: 'relay_offline', relayRunning: false, cockpitConnected: false, blockers: ['WebSocket disconnected from vision relay'], recoveryAction: 'reconnecting automatically' })
        addNotification('warn', 'Vision relay disconnected', 'relay', 'WebSocket connection lost — reconnecting', 'auto-reconnect', true)
      }),
      client.on('vision_frame', (d) => {
        setLatestFrame(d.url as string, d.timestamp as number)
        incrementFrameCount()
      }),
      client.on('vision_status', (d) => {
        const isStreaming = d.streaming as boolean
        setStreaming(isStreaming)
        setCameraStatus(isStreaming ? 'live' : 'off')
      }),
      client.on('camera_presets', (d) => {
        const fromBeast = d.presets as Record<string, CameraPreset>
        const fromStorage = loadPresetsFromStorage()
        setPresets({ ...fromStorage, ...fromBeast })
      }),
      client.on('camera_position', (d) => {
        setPtzPosition({
          pan: d.pan as number,
          tilt: d.tilt as number,
          zoom: d.zoom as number,
        })
        if (d.has_ptz_hardware !== undefined) {
          setHasPtzHardware(d.has_ptz_hardware as boolean)
        }
        setPtzMoving(false)
      }),
      client.on('camera_control_result', (d) => {
        const ok = d.ok as boolean
        if (!ok) {
          setError(d.error as string || 'PTZ command failed')
          setTimeout(() => setError(null), 3000)
        }
        setPtzMoving(false)
        if (d.pan !== undefined) {
          setPtzPosition({
            pan: d.pan as number,
            tilt: d.tilt as number,
            zoom: d.zoom as number,
          })
        }
      }),
      client.on('vision_snapshot', (d) => {
        const b64 = d.image_base64 as string
        if (b64) {
          const binary = atob(b64)
          const bytes = new Uint8Array(binary.length)
          for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
          const blob = new Blob([bytes], { type: 'image/jpeg' })
          const url = URL.createObjectURL(blob)
          setLatestFrame(url, Date.now())
          incrementFrameCount()
        }
      }),
      client.on('vision_error', (d) => {
        const errMsg = d.error as string
        setError(errMsg)
        setTimeout(() => setError(null), 5000)
        addNotification('warn', 'Vision error', 'relay', errMsg, 'check diagnostics')
      }),
      client.on('preset_saved', (d) => {
        client.requestPresets()
        const presetName = d.preset as string
        if (presetName) {
          useVisionStore.getState().addToast(`Preset "${presetName}" saved to device`, 'ok')
        }
      }),
      client.on('preset_deleted', (d) => {
        client.requestPresets()
        const presetName = d.preset as string
        if (presetName) {
          useVisionStore.getState().addToast(`Preset "${presetName}" deleted from device`, 'warning')
        }
      }),
      client.on('label_corrected', (d) => {
        const trackId = d.track_id as string
        const corrected = d.corrected_label as string
        if (trackId && corrected) {
          useVisionStore.getState().addToast(`Label correction synced to detector: "${corrected}"`, 'ok')
        }
      }),
      client.on('label_corrections_list', (d) => {
        const corrections = d.corrections as Record<string, string> | undefined
        if (corrections && Object.keys(corrections).length > 0) {
          useVisionStore.getState().mergeLabelCorrections(corrections)
        }
      }),

      // Scene / tracking events
      client.on('vision_scene_state', (d) => {
        updateSceneState(d)
      }),
      client.on('vision_analysis_result', (d) => {
        setAnalysisResult(d.answer as string)
        setAnalysisStatus(d.confidence === 'none' ? 'error' : 'complete')
        setTimeout(() => setAnalysisStatus('idle'), 10000)
      }),
      client.on('vision_track_result', (d) => {
        if (d.success) client.requestSceneState()
      }),
      client.on('vision_label_result', (d) => {
        if (d.success) client.requestSceneState()
      }),
      client.on('vision_watch_result', (d) => {
        if (d.success) client.requestSceneState()
      }),
      client.on('vision_follow_result', (d) => {
        if (d.success) {
          setFollowMode({
            active: true,
            target: d.target as string || 'operator',
            track_id: '',
          })
        }
        client.requestSceneState()
      }),
      client.on('vision_query_result', (d) => {
        setAnalysisResult(d.answer as string)
        setAnalysisStatus('complete')
        setTimeout(() => setAnalysisStatus('idle'), 10000)
      }),
      client.on('vision_scene_describe_result', (d) => {
        setAnalysisResult(d.description as string || d.answer as string || 'No description')
        setAnalysisStatus('complete')
        setTimeout(() => setAnalysisStatus('idle'), 10000)
      }),
      client.on('vision_active_tracks_result', (d) => {
        const tracks = (d.tracks as TrackedObjectState[]) || []
        setDetectedObjects(tracks)
      }),
      client.on('vision_track_query_result', (d) => {
        if (d.success && d.track) {
          const t = d.track as Record<string, unknown>
          setAnalysisResult(`Found: ${t.label} #${t.track_id} — ${Math.round((t.confidence as number || 0) * 100)}% confidence`)
        } else {
          setAnalysisResult(`Not found: "${d.label}" is not currently visible`)
        }
        setAnalysisStatus('complete')
        setTimeout(() => setAnalysisStatus('idle'), 10000)
      }),
      client.on('vision_look_at_result', (d) => {
        if (d.success) {
          setAnalysisResult(`Centering on ${d.label} #${d.track_id}`)
        } else {
          setAnalysisResult(`Look-at failed: ${d.error || 'target not found'}`)
        }
        setAnalysisStatus('complete')
        setTimeout(() => setAnalysisStatus('idle'), 5000)
      }),

      // Tracker stack events
      client.on('vision_tracker_result', () => {
        client.requestTrackerState()
      }),
      client.on('vision_tracker_state', (d) => {
        updateTrackerStack({
          active_stack_id: d.active_stack_id as string || '',
          enabled_trackers: (d.enabled_trackers as TrackerConfigState[]) || [],
          total_cost: (d.total_cost as { cpu: number; gpu: number }) || { cpu: 0, gpu: 0 },
        })
      }),

      // Vision preset events
      client.on('vision_preset_result', (d) => {
        if (d.success) client.requestPresetState()
      }),
      client.on('vision_preset_state', (d) => {
        setVisionPresets((d.presets as Record<string, VisionPresetInfo>) || {})
        setActiveVisionPresetId(d.active_preset_id as string || '')
      }),

      // Trigger chain events
      client.on('vision_chain_result', (d) => {
        if (d.success) client.requestChainState()
      }),
      client.on('vision_chain_explain', (d) => {
        setLastChainExplanation(d.explanation as string || '')
      }),
      client.on('vision_chain_state', (d) => {
        setTriggerChains((d.chains as Record<string, TriggerChainInfo>) || {})
        setRecentFires((d.recent_fires as ChainFireInfo[]) || [])
      }),

      // Security mode events
      client.on('vision_security_result', (d) => {
        if (d.active !== undefined) {
          setSecurityMode({
            active: d.active as boolean,
            mode: d.mode as string || 'normal',
            risk: d.risk as string || 'low',
            triggered_by: d.triggered_by as string || '',
            actions_taken: (d.actions_taken as string[]) || [],
            requires_review: d.requires_review as boolean || false,
          })
          const isActive = d.active as boolean
          if (isActive) {
            addNotification('critical', 'Security mode activated', d.triggered_by as string || 'system',
              `Mode: ${d.mode || 'unknown'} | Risk: ${d.risk || 'unknown'}`,
              (d.actions_taken as string[] || []).join(', ') || 'monitoring', true)
            addToast(`Security mode: ${d.mode || 'activated'}`, 'danger')
          } else {
            addNotification('info', 'Security mode deactivated', 'operator', 'Security mode returned to normal', 'none')
          }
        }
        client.requestSecurityState()
      }),
      client.on('vision_security_state', (d) => {
        setSecurityMode({
          active: d.active as boolean || false,
          mode: d.mode as string || 'normal',
          risk: d.risk as string || 'low',
          triggered_by: d.triggered_by as string || '',
        })
      }),

      // Realtime PTZ motion events
      client.on('ptz_motion_state', (d) => {
        setPtzMotion({
          state: (d.state as MotionState) || 'idle',
          motionId: d.motion_id as string || '',
          panVelocity: d.pan_velocity as number || 0,
          tiltVelocity: d.tilt_velocity as number || 0,
          zoomVelocity: d.zoom_velocity as number || 0,
        })
        if (d.ptz_mode) {
          updateChainHealth({
            ptzMode: d.ptz_mode as 'physical_ptz' | 'digital_roi',
            roi: d.roi as { x: number; y: number; zoom: number } ?? undefined,
          })
        }
        if (d.loop_cadence_hz !== undefined) {
          updateControlMetrics({ ptzLoopCadenceHz: d.loop_cadence_hz as number })
        }
        if (d.guard_timeout_events !== undefined) {
          updateControlMetrics({ guardTimeouts: d.guard_timeout_events as number })
        }
        if (d.coalesced_commands !== undefined) {
          updateControlMetrics({ coalescedCommands: d.coalesced_commands as number })
        }
        const motionActive = d.state === 'moving'
        setPtzMoving(motionActive)
      }),
      client.on('ptz_motion_ack', (d) => {
        const op = d.operation as string
        const now = Date.now()
        if (op === 'stop_motion' || op === 'zoom_stop') {
          const sentAt = useVisionStore.getState().controlMetrics.lastStopSentAt
          if (sentAt > 0) {
            const rtt = now - sentAt
            updateControlMetrics({ lastStopAckedAt: now, stopLatencyMs: rtt })
            recordLatency({ commandId: d.request_id as string || '', sentAt, ackedAt: now, roundTripMs: rtt, operation: op })
          }
          setPtzMotion({ state: 'idle', motionId: '', panVelocity: 0, tiltVelocity: 0, zoomVelocity: 0 })
          setPtzMoving(false)
        } else if (op === 'start_motion' || op === 'zoom_start') {
          const sentAt = useVisionStore.getState().controlMetrics.lastCommandSentAt
          if (sentAt > 0) {
            const rtt = now - sentAt
            recordLatency({ commandId: d.request_id as string || '', sentAt, ackedAt: now, roundTripMs: rtt, operation: op })
          }
        }
      }),

      // Camera session state
      client.on('camera_session_state', (d) => {
        setCameraSessionActive(d.active as boolean || false)
        setViewerCount(d.viewer_count as number || 0)
      }),

      // Overlay events — normalize flat x/y/w/h to bbox structure
      client.on('vision_overlay', (d) => {
        const raw = (d.overlays as Record<string, unknown>[]) || []
        const overlays: import('../components/vision/VisionOverlay').OverlayMetadata[] = raw.map((o) => ({
          type: (o.type as string) || 'object',
          track_id: (o.track_id as string) || '',
          label: (o.label as string) || '',
          confidence: (o.confidence as number) || 0,
          bbox: o.bbox
            ? (o.bbox as { x: number; y: number; w: number; h: number })
            : { x: (o.x as number) || 0, y: (o.y as number) || 0, w: (o.w as number) || 0, h: (o.h as number) || 0 },
          color: (o.color as string) || undefined,
          source: (o.source as string) || undefined,
          model: (o.model as string) || undefined,
        })) as import('../components/vision/VisionOverlay').OverlayMetadata[]
        setOverlays(overlays)
        const detStatus = d.detector_status as Record<string, unknown> | null
        const healthUpdate: Partial<import('../stores/visionStore').VisionHealthState> = {
          lastOverlayAt: Date.now(), lastOverlayAgeMs: 0,
        }
        if (detStatus) {
          healthUpdate.detectorStatus = {
            source: detStatus.source as string || 'unknown',
            host: detStatus.host as string || 'unknown',
            model: detStatus.model as string || 'unknown',
            loaded: detStatus.loaded as boolean ?? false,
            inference_ms: detStatus.inference_ms as number ?? 0,
            avg_inference_ms: detStatus.avg_inference_ms as number ?? 0,
            detection_frames: detStatus.detection_frames as number ?? 0,
            tracker_active: detStatus.tracker_active as boolean ?? false,
            active_tracks: detStatus.active_tracks as number ?? 0,
            total_tracks: detStatus.total_tracks as number ?? 0,
          }
        }
        updateChainHealth(healthUpdate)
      }),

      // Health chain events — emit notifications on state transitions
      client.on('vision_health', (d) => {
        const beastNow = d.beast_connected as boolean ?? false
        const cameraNow = d.camera_streaming as boolean ?? false
        if (lastBeastConnected !== null && lastBeastConnected !== beastNow) {
          if (beastNow) {
            addNotification('info', 'Beast online', 'mesh', 'Beast node connected to vision relay', 'monitoring')
          } else {
            addNotification('critical', 'Beast offline', 'mesh', 'Beast node disconnected — camera commands unavailable', 'check Beast', true)
            addToast('Beast offline — camera commands unavailable', 'danger')
          }
        }
        if (lastCameraStreaming !== null && lastCameraStreaming !== cameraNow) {
          if (cameraNow) {
            addNotification('info', 'Camera stream started', 'camera', 'Camera is now streaming frames', 'monitoring')
          } else {
            addNotification('warn', 'Camera stream stopped', 'camera', 'Camera is no longer streaming', 'check camera')
          }
        }
        lastBeastConnected = beastNow
        lastCameraStreaming = cameraNow

        const detStatus = d.detector_status as Record<string, unknown> | null
        updateChainHealth({
          status: (d.status as VisionChainStatus) || 'degraded',
          relayRunning: d.relay_running as boolean ?? true,
          cockpitConnected: d.cockpit_connected as boolean ?? false,
          beastConnected: d.beast_connected as boolean ?? false,
          cameraAvailable: d.camera_available as boolean ?? false,
          cameraStreaming: d.camera_streaming as boolean ?? false,
          lastFrameAt: d.last_frame_at as number ?? 0,
          lastFrameAgeMs: d.last_frame_age_ms as number ?? -1,
          frameFps: d.frame_fps as number ?? 0,
          trackerRuntimeAvailable: d.tracker_runtime_available as boolean ?? false,
          activeTrackers: (d.active_trackers as string[]) ?? [],
          lastOverlayAt: d.last_overlay_at as number ?? 0,
          lastOverlayAgeMs: d.last_overlay_age_ms as number ?? -1,
          triggerChainEngineAvailable: d.trigger_chain_engine_available as boolean ?? false,
          activeChains: (d.active_chains as string[]) ?? [],
          securityMode: d.security_mode as string ?? 'normal',
          detectorStatus: detStatus ? {
            source: detStatus.source as string || 'unknown',
            host: detStatus.host as string || 'unknown',
            model: detStatus.model as string || 'unknown',
            loaded: detStatus.loaded as boolean ?? false,
            inference_ms: detStatus.inference_ms as number ?? 0,
            avg_inference_ms: detStatus.avg_inference_ms as number ?? 0,
            detection_frames: detStatus.detection_frames as number ?? 0,
            tracker_active: detStatus.tracker_active as boolean ?? false,
            active_tracks: detStatus.active_tracks as number ?? 0,
            total_tracks: detStatus.total_tracks as number ?? 0,
          } : null,
          blockers: (d.blockers as string[]) ?? [],
          recoveryAction: d.recovery_action as string ?? '',
          ptzMode: (d.ptz_mode as 'physical_ptz' | 'digital_roi') || 'physical_ptz',
          physicalPtzAvailable: d.physical_ptz_available as boolean ?? false,
          digitalRoiAvailable: d.digital_roi_available as boolean ?? true,
          commandPathReady: d.command_path_ready as boolean ?? false,
          roi: d.roi as { x: number; y: number; zoom: number } ?? { x: 0, y: 0, zoom: 1 },
        })
      }),
    ]

    // Metrics polling + stale detection — 1s
    const STALE_FRAME_MS = 15000
    const STALE_OVERLAY_MS = 5000
    let lastMetricFrameCount = 0
    let lastMetricTime = Date.now()
    metricsInterval.current = setInterval(() => {
      if (!client.connected) return
      const state = useVisionStore.getState()
      const lastFrame = state.latestFrameAt
      const frameAge = lastFrame ? Date.now() - lastFrame : 0
      const fps = client.measuredFps
      const avgSize = client.avgFrameSize
      const bitrateKbps = Math.round((fps * avgSize * 8) / 1024)

      const currentFrameCount = client.frameCount
      const now = Date.now()
      const elapsed = (now - lastMetricTime) / 1000
      const targetFps = QUALITY_PROFILES[state.qualityMode].fps
      const expectedFrames = elapsed * targetFps
      const actualFrames = currentFrameCount - lastMetricFrameCount
      const dropped = Math.max(0, Math.round(expectedFrames - actualFrames))
      lastMetricFrameCount = currentFrameCount
      lastMetricTime = now

      updateStreamMetrics({
        actualFps: fps,
        targetFps,
        avgFrameSize: avgSize,
        bitrateKbps,
        lastFrameAge: frameAge,
        droppedFrames: state.streamMetrics.droppedFrames + dropped,
      })
      if (lastFrame && frameAge > STALE_FRAME_MS && state.streaming) {
        setStreaming(false)
        setCameraStatus('error')
        setError('stream stale — no frames received')
      }
      const overlayAge = state.chainHealth.lastOverlayAgeMs
      if (overlayAge > STALE_OVERLAY_MS && state.detectedObjects.length > 0) {
        setDetectedObjects([])
      }
    }, 1000)

    // Scene state polling — 5s
    sceneInterval.current = setInterval(() => {
      if (!client.connected) return
      client.requestSceneState()
    }, 5000)

    // Health chain polling — 5s
    healthInterval.current = setInterval(() => {
      if (!client.connected) return
      client.requestHealth()
    }, 5000)

    client.connect()

    return () => {
      unsubs.forEach((fn) => fn())
      if (cameraStartDebounceTimer) clearTimeout(cameraStartDebounceTimer)
      if (metricsInterval.current) clearInterval(metricsInterval.current)
      if (sceneInterval.current) clearInterval(sceneInterval.current)
      if (healthInterval.current) clearInterval(healthInterval.current)
      client.unsubscribe()
      client.disconnect()
      _client = null
      reset()
    }
  }, [])
}
