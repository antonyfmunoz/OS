import { useEffect, useRef, useState, useCallback } from 'react'
import { Monitor } from 'lucide-react'

interface Props {
  monitorId?: string
  paused: boolean
}

export function DesktopWindowContent({ monitorId, paused }: Props) {
  const id = monitorId ?? 'M0'
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
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/umh/desktop/ws`)
    ws.binaryType = 'blob'
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      setRetryCount(0)
      ws.send(JSON.stringify({ type: 'desktop_subscribe', monitor: id }))
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
        const delay = Math.min(5000, 1000 * Math.pow(1.5, retryCount))
        retryTimerRef.current = setTimeout(() => {
          setRetryCount((c) => c + 1)
          connect()
        }, delay)
      }
    }

    ws.onerror = () => ws.close()
  }, [paused, retryCount, id])

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
        <span className="text-[12px]">Desktop paused</span>
      </div>
    )
  }

  if (!connected || !frameUrl) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3"
        style={{ color: 'var(--color-text-tertiary)' }}>
        <Monitor size={24} />
        <span className="text-[12px] font-medium" style={{ color: 'var(--color-text-secondary)' }}>
          Desktop {id}
        </span>
        <span className="text-[10px]">
          {connected ? 'Waiting for frames...' : retryCount > 2 ? 'Reconnecting...' : 'Connecting to desktop relay...'}
        </span>
        {retryCount > 0 && (
          <span className="text-[10px]">Attempt {retryCount + 1}</span>
        )}
        <button className="text-[11px] px-2 py-1 rounded"
          style={{ border: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }}
          onClick={() => { setRetryCount(0); connect() }}>
          Retry
        </button>
        {retryCount > 3 && (
          <span className="text-[9px] px-3 text-center" style={{ maxWidth: 200 }}>
            Requires desktop streaming service on executor node
          </span>
        )}
      </div>
    )
  }

  return (
    <div className="relative w-full h-full overflow-hidden" style={{ background: '#000' }}>
      <img src={frameUrl} alt={`Desktop ${id}`} className="w-full h-full"
        style={{ objectFit: 'contain' }} />
      <div className="absolute top-1 right-1 flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px]"
        style={{ background: 'rgba(0,0,0,0.6)', color: '#22c55e' }}>
        <div className="w-1.5 h-1.5 rounded-full" style={{ background: '#22c55e' }} />
        LIVE
      </div>
      <div className="absolute bottom-1 left-1 px-1.5 py-0.5 rounded text-[9px]"
        style={{ background: 'rgba(0,0,0,0.6)', color: 'var(--color-text-tertiary)' }}>
        {id}
      </div>
    </div>
  )
}
