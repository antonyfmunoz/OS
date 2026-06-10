import { useEffect, useRef } from 'react'
import { VisionWsClient } from '../api/vision-ws'
import {
  useVisionStore,
  QUALITY_PROFILES,
  type CameraPreset,
  type TrackedObjectState,
  type WatchItemState,
  type FollowModeState,
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
  const reset = useVisionStore((s) => s.reset)

  const metricsInterval = useRef<ReturnType<typeof setInterval> | null>(null)
  const sceneInterval = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!_client) _client = new VisionWsClient()
    const client = _client

    const profile = QUALITY_PROFILES[useVisionStore.getState().qualityMode]

    const unsubs = [
      client.on('connected', () => {
        setConnected(true)
        client.requestPresets()
        client.requestStatus()
        client.requestPosition()
        client.startCamera({
          fps: profile.fps,
          width: profile.width,
          height: profile.height,
          quality: profile.quality,
        })
        client.subscribe(profile.fps, profile.quality)
        client.requestSceneState()
      }),
      client.on('disconnected', () => {
        setConnected(false)
        setCameraStatus('off')
        setStreaming(false)
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
    ]

    // Metrics polling — 1s
    metricsInterval.current = setInterval(() => {
      if (!client.connected) return
      const lastFrame = useVisionStore.getState().latestFrameAt
      updateStreamMetrics({
        actualFps: client.measuredFps,
        targetFps: QUALITY_PROFILES[useVisionStore.getState().qualityMode].fps,
        avgFrameSize: client.avgFrameSize,
        lastFrameAge: lastFrame ? Date.now() - lastFrame : 0,
      })
    }, 1000)

    // Scene state polling — 5s
    sceneInterval.current = setInterval(() => {
      if (!client.connected) return
      client.requestSceneState()
    }, 5000)

    client.connect().catch((err) => {
      setError(`Vision relay: ${err.message}`)
    })

    return () => {
      unsubs.forEach((fn) => fn())
      if (metricsInterval.current) clearInterval(metricsInterval.current)
      if (sceneInterval.current) clearInterval(sceneInterval.current)
      client.unsubscribe()
      client.disconnect()
      _client = null
      reset()
    }
  }, [])
}
