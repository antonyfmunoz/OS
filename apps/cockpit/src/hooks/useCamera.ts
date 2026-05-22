import { useCallback, useEffect, useRef, useState } from 'react'
import { socket } from '../lib/ws-client.ts'

export type CameraState = 'off' | 'starting' | 'live' | 'capturing' | 'error'

interface VisionResult {
  text: string
  provider?: string
  durationMs?: number
}

interface UseCameraReturn {
  state: CameraState
  videoRef: React.RefObject<HTMLVideoElement | null>
  lastVisionResult: VisionResult | null
  supported: boolean
  start: () => void
  stop: () => void
  toggle: () => void
  captureAndAnalyze: (prompt?: string) => void
}

function canvasToJpegBase64(
  video: HTMLVideoElement,
  canvas: HTMLCanvasElement,
): string | null {
  const ctx = canvas.getContext('2d')
  if (!ctx) return null
  canvas.width = Math.min(video.videoWidth, 1280)
  canvas.height = Math.min(video.videoHeight, 720)
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
  const dataUrl = canvas.toDataURL('image/jpeg', 0.8)
  return dataUrl.split(',')[1] ?? null
}

export function useCamera(): UseCameraReturn {
  const [state, setState] = useState<CameraState>('off')
  const [lastVisionResult, setLastVisionResult] = useState<VisionResult | null>(null)

  const videoRef = useRef<HTMLVideoElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  const supported = typeof navigator !== 'undefined'
    && !!navigator.mediaDevices?.getUserMedia

  useEffect(() => {
    if (!canvasRef.current) {
      canvasRef.current = document.createElement('canvas')
    }
  }, [])

  useEffect(() => {
    const checkWs = () => {
      const rawWs = socket.rawWs
      if (!rawWs) return

      const origHandler = rawWs.onmessage

      rawWs.onmessage = (event: MessageEvent) => {
        if (typeof event.data === 'string') {
          try {
            const msg = JSON.parse(event.data) as Record<string, unknown>
            if (msg.type === 'vision_ack') {
              setState('capturing')
            } else if (msg.type === 'vision_response') {
              setLastVisionResult({
                text: (msg.text as string) || '',
                provider: msg.provider as string | undefined,
                durationMs: msg.duration_ms as number | undefined,
              })
              setState('live')
            }
          } catch {
            // not JSON
          }
        }

        if (origHandler) {
          origHandler.call(rawWs, event)
        }
      }
    }

    checkWs()
    const interval = setInterval(checkWs, 2000)
    return () => clearInterval(interval)
  }, [])

  const start = useCallback(async () => {
    if (!supported) {
      setState('error')
      return
    }

    setState('starting')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      setState('live')
    } catch (e) {
      console.error('[useCamera] failed to start:', e)
      setState('error')
      setTimeout(() => setState('off'), 3000)
    }
  }, [supported])

  const stop = useCallback(() => {
    if (streamRef.current) {
      for (const track of streamRef.current.getTracks()) {
        track.stop()
      }
      streamRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setState('off')
  }, [])

  const toggle = useCallback(() => {
    if (state === 'off' || state === 'error') {
      start()
    } else {
      stop()
    }
  }, [state, start, stop])

  const captureAndAnalyze = useCallback((prompt?: string) => {
    if (!videoRef.current || !canvasRef.current || state !== 'live') return

    const b64 = canvasToJpegBase64(videoRef.current, canvasRef.current)
    if (!b64) return

    setState('capturing')
    socket.send('vision_frame', {
      image: b64,
      prompt: prompt || '',
      mime_type: 'image/jpeg',
    })
  }, [state])

  return {
    state,
    videoRef,
    lastVisionResult,
    supported,
    start,
    stop,
    toggle,
    captureAndAnalyze,
  }
}
