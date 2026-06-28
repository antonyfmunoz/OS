import { useEffect, useRef, useState, useCallback } from 'react'
import { Camera } from 'lucide-react'

interface Props {
  paused: boolean
}

export function VisionWindowContent({ paused }: Props) {
  const [connected, setConnected] = useState(false)
  const [frameUrl, setFrameUrl] = useState<string | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  const wsRef = useRef<WebSocket | null>(null)
  const prevUrlRef = useRef<string | null>(null)
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const connect = useCallback(() => {
    if (paused || wsRef.current?.readyState === WebSocket.OPEN) return
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/umh/vision/ws`)
    ws.binaryType = 'blob'
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      setRetryCount(0)
    }

    ws.onmessage = (ev) => {
      if (ev.data instanceof Blob) {
        const url = URL.createObjectURL(ev.data)
        setFrameUrl(url)
        if (prevUrlRef.current) URL.revokeObjectURL(prevUrlRef.current)
        prevUrlRef.current = url
      }
    }

    ws.onclose = () => {
      setConnected(false)
      setFrameUrl(null)
      wsRef.current = null
      if (!paused) {
        const delay = Math.min(3000, 1000 * Math.pow(1.5, retryCount))
        retryTimerRef.current = setTimeout(() => {
          setRetryCount((c) => c + 1)
          connect()
        }, delay)
      }
    }

    ws.onerror = () => ws.close()
  }, [paused, retryCount])

  useEffect(() => {
    connect()
    return () => {
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current)
      wsRef.current?.close()
      wsRef.current = null
      if (prevUrlRef.current) URL.revokeObjectURL(prevUrlRef.current)
    }
  }, [connect])

  if (paused) {
    return (
      <div className="flex items-center justify-center h-full"
        style={{ color: 'var(--color-text-tertiary)' }}>
        <span className="text-[12px]">Vision paused</span>
      </div>
    )
  }

  if (!connected || !frameUrl) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3"
        style={{ color: 'var(--color-text-tertiary)' }}>
        <Camera size={24} />
        <span className="text-[12px]">
          {connected ? 'Waiting for frames...' : retryCount > 2 ? 'Reconnecting to vision relay...' : 'Connecting to vision relay...'}
        </span>
        {retryCount > 0 && (
          <span className="text-[10px]">Attempt {retryCount + 1}</span>
        )}
        <button className="text-[11px] px-2 py-1 rounded"
          style={{ border: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }}
          onClick={() => { setRetryCount(0); connect() }}>
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="relative w-full h-full overflow-hidden" style={{ background: '#000' }}>
      <img src={frameUrl} alt="Vision feed" className="w-full h-full"
        style={{ objectFit: 'contain' }} />
      <div className="absolute top-1 right-1 flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px]"
        style={{ background: 'rgba(0,0,0,0.6)', color: '#22c55e' }}>
        <div className="w-1.5 h-1.5 rounded-full" style={{ background: '#22c55e' }} />
        LIVE
      </div>
    </div>
  )
}
