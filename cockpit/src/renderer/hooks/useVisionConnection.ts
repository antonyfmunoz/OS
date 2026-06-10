import { useEffect, useRef } from 'react'
import { VisionWsClient } from '../api/vision-ws'
import {
  useVisionStore,
  QUALITY_PROFILES,
  shouldAutoStartCamera,
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
  const setPtzMotion = useVisionStore((s) => s.setPtzMotion)
  const updateControlMetrics = useVisionStore((s) => s.updateControlMetrics)
  const setViewerCount = useVisionStore((s) => s.setViewerCount)
  const setCameraSessionActive = useVisionStore((s) => s.setCameraSessionActive)
  const reset = useVisionStore((s) => s.reset)

  const metricsInterval = useRef<ReturnType<typeof setInterval> | null>(null)
  const sceneInterval = useRef<ReturnType<typeof setInterval> | null>(null)
  const healthInterval = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!_client) _client = new VisionWsClient()
    const client = _client

    const profile = QUALITY_PROFILES[useVisionStore.getState().qualityMode]

    const unsubs = [
      client.on('connected', () => {
        setConnected(true)
        setCameraSessionActive(true)
        client.requestPresets()
        client.requestStatus()
        client.requestPosition()
        client.requestHealth()

        const policy = useVisionStore.getState().defaultOnPolicy
        if (shouldAutoStartCamera(policy)) {
          client.startCamera({
            fps: profile.fps,
            width: profile.width,
            height: profile.height,
            quality: profile.quality,
          })
          client.subscribe(profile.fps, profile.quality)
        }
        client.requestSceneState()
        setPtzMotion({ state: 'idle', motionId: '', panVelocity: 0, tiltVelocity: 0, zoomVelocity: 0 })
      }),
      client.on('disconnected', () => {
        setConnected(false)
        setCameraStatus('off')
        setStreaming(false)
        setCameraSessionActive(false)
        setPtzMotion({ state: 'disconnected', motionId: '', panVelocity: 0, tiltVelocity: 0, zoomVelocity: 0 })
        updateChainHealth({ status: 'relay_offline', relayRunning: false, cockpitConnected: false, blockers: ['WebSocket disconnected from vision relay'], recoveryAction: 'reconnecting automatically' })
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
        setPresets(d.presets as Record<string, CameraPreset>)
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
        setError(d.error as string)
        setTimeout(() => setError(null), 5000)
      }),
      client.on('preset_saved', () => {
        client.requestPresets()
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
        if (d.loop_cadence_hz !== undefined) {
          updateControlMetrics({ ptzLoopCadenceHz: d.loop_cadence_hz as number })
        }
        if (d.guard_timeout_events !== undefined) {
          updateControlMetrics({ guardTimeouts: d.guard_timeout_events as number })
        }
        const motionActive = d.state === 'moving'
        setPtzMoving(motionActive)
      }),
      client.on('ptz_motion_ack', (d) => {
        const op = d.operation as string
        if (op === 'stop_motion' || op === 'zoom_stop') {
          const sentAt = useVisionStore.getState().controlMetrics.lastStopSentAt
          if (sentAt > 0) {
            updateControlMetrics({ lastStopAckedAt: Date.now(), stopLatencyMs: Date.now() - sentAt })
          }
          setPtzMotion({ state: 'idle', motionId: '', panVelocity: 0, tiltVelocity: 0, zoomVelocity: 0 })
          setPtzMoving(false)
        }
      }),

      // Camera session state
      client.on('camera_session_state', (d) => {
        setCameraSessionActive(d.active as boolean || false)
        setViewerCount(d.viewer_count as number || 0)
      }),

      // Health chain events
      client.on('vision_health', (d) => {
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
          blockers: (d.blockers as string[]) ?? [],
          recoveryAction: d.recovery_action as string ?? '',
        })
      }),
    ]

    // Metrics polling + stale detection — 1s
    const STALE_FRAME_MS = 15000
    const STALE_OVERLAY_MS = 5000
    metricsInterval.current = setInterval(() => {
      if (!client.connected) return
      const state = useVisionStore.getState()
      const lastFrame = state.latestFrameAt
      const frameAge = lastFrame ? Date.now() - lastFrame : 0
      updateStreamMetrics({
        actualFps: client.measuredFps,
        targetFps: QUALITY_PROFILES[state.qualityMode].fps,
        avgFrameSize: client.avgFrameSize,
        lastFrameAge: frameAge,
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

    client.connect().catch((err) => {
      setError(`Vision relay: ${err.message}`)
    })

    return () => {
      unsubs.forEach((fn) => fn())
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
