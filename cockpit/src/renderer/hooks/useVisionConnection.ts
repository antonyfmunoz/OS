import { useEffect } from 'react'
import { VisionWsClient } from '../api/vision-ws'
import { useVisionStore, type CameraPreset } from '../stores/visionStore'

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
  const reset = useVisionStore((s) => s.reset)

  useEffect(() => {
    if (!_client) _client = new VisionWsClient()
    const client = _client

    const unsubs = [
      client.on('connected', () => {
        setConnected(true)
        client.requestPresets()
        client.requestStatus()
        client.startCamera({ fps: 15, width: 640, height: 480, quality: 65 })
        client.subscribe(15, 65)
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
    ]

    client.connect().catch((err) => {
      setError(`Vision relay: ${err.message}`)
    })

    return () => {
      unsubs.forEach((fn) => fn())
      client.unsubscribe()
      client.disconnect()
      _client = null
      reset()
    }
  }, [])
}
