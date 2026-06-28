import { useEffect, useRef, useState, useCallback } from 'react'
import { Monitor } from 'lucide-react'
import { fetchApi } from '../../../api/client'

interface Props {
  monitorId?: string
  paused: boolean
  onResizeHint?: (width: number, height: number) => void
}

const SPECIAL_KEYS = new Set([
  'Enter', 'Backspace', 'Tab', 'Escape', 'Delete',
  'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown',
  'Home', 'End', 'PageUp', 'PageDown',
  'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12',
])

const KEY_MAP: Record<string, string> = {
  Enter: 'enter', Backspace: 'backspace', Tab: 'tab', Escape: 'escape', Delete: 'delete',
  ArrowLeft: 'left', ArrowRight: 'right', ArrowUp: 'up', ArrowDown: 'down',
  Home: 'home', End: 'end', PageUp: 'pageup', PageDown: 'pagedown',
}

function dispatch(capability: string, params: Record<string, unknown>) {
  fetchApi('/mesh/dispatch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      node_id: 'windows-desktop',
      capability,
      params,
      timeout: 5,
    }),
  }).catch(() => {})
}

export function DesktopWindowContent({ monitorId, paused, onResizeHint }: Props) {
  const id = monitorId ?? 'M0'
  const [connected, setConnected] = useState(false)
  const [frameUrl, setFrameUrl] = useState<string | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  const [frameWidth, setFrameWidth] = useState(1920)
  const [frameHeight, setFrameHeight] = useState(1080)
  const wsRef = useRef<WebSocket | null>(null)
  const prevUrlRef = useRef<string | null>(null)
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const imgRef = useRef<HTMLImageElement>(null)
  const interactRef = useRef<HTMLDivElement>(null)
  const mobileInputRef = useRef<HTMLInputElement>(null)
  const isTouchDevice = 'ontouchstart' in window
  const resizeHintFired = useRef(false)

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
      } else if (typeof ev.data === 'string') {
        try {
          const msg = JSON.parse(ev.data)
          if (msg.width) setFrameWidth(msg.width)
          if (msg.height) setFrameHeight(msg.height)
          if (msg.width && msg.height && onResizeHint && !resizeHintFired.current) {
            resizeHintFired.current = true
            onResizeHint(msg.width, msg.height)
          }
        } catch { /* ignore non-JSON */ }
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

  const scaleCoords = useCallback(
    (clientX: number, clientY: number): { x: number; y: number } | null => {
      const img = imgRef.current
      if (!img) return null
      const rect = img.getBoundingClientRect()
      const imgAspect = frameWidth / frameHeight
      const boxAspect = rect.width / rect.height
      let renderW: number, renderH: number, offsetX: number, offsetY: number
      if (imgAspect > boxAspect) {
        renderW = rect.width
        renderH = rect.width / imgAspect
        offsetX = 0
        offsetY = (rect.height - renderH) / 2
      } else {
        renderH = rect.height
        renderW = rect.height * imgAspect
        offsetX = (rect.width - renderW) / 2
        offsetY = 0
      }
      const localX = clientX - rect.left - offsetX
      const localY = clientY - rect.top - offsetY
      if (localX < 0 || localY < 0 || localX > renderW || localY > renderH) return null
      return {
        x: Math.round((localX / renderW) * frameWidth),
        y: Math.round((localY / renderH) * frameHeight),
      }
    },
    [frameWidth, frameHeight]
  )

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      if (isTouchDevice) {
        mobileInputRef.current?.focus()
      } else {
        interactRef.current?.focus()
      }
      const pos = scaleCoords(e.clientX, e.clientY)
      if (!pos) return
      if (e.detail === 2) {
        dispatch('desktop.double_click', { x: pos.x, y: pos.y })
      } else {
        dispatch('desktop.click', { x: pos.x, y: pos.y, button: e.button === 2 ? 'right' : 'left' })
      }
    },
    [scaleCoords, isTouchDevice]
  )

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (e.buttons === 0) return
      const pos = scaleCoords(e.clientX, e.clientY)
      if (pos) dispatch('desktop.move_mouse', { x: pos.x, y: pos.y })
    },
    [scaleCoords]
  )

  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      e.stopPropagation()
      const pos = scaleCoords(e.clientX, e.clientY)
      if (!pos) return
      const clicks = Math.sign(e.deltaY) * -3
      dispatch('desktop.scroll', { x: pos.x, y: pos.y, clicks })
    },
    [scaleCoords]
  )

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    const pos = scaleCoords(e.clientX, e.clientY)
    if (pos) dispatch('desktop.right_click', { x: pos.x, y: pos.y })
  }, [scaleCoords])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      e.stopPropagation()
      e.preventDefault()
      if (e.ctrlKey || e.altKey || e.metaKey) {
        const keys: string[] = []
        if (e.ctrlKey) keys.push('ctrl')
        if (e.altKey) keys.push('alt')
        if (e.metaKey) keys.push('win')
        keys.push(KEY_MAP[e.key] ?? e.key.toLowerCase())
        dispatch('desktop.key_press', { keys })
      } else if (SPECIAL_KEYS.has(e.key)) {
        dispatch('desktop.key_press', { key: KEY_MAP[e.key] ?? e.key.toLowerCase() })
      } else if (e.key.length === 1) {
        dispatch('desktop.type', { text: e.key })
      }
    },
    []
  )

  const handleKeyUp = useCallback((e: React.KeyboardEvent) => {
    e.stopPropagation()
    e.preventDefault()
  }, [])

  const handleMobileInput = useCallback(
    (e: React.FormEvent<HTMLInputElement>) => {
      const value = e.currentTarget.value
      if (value) {
        dispatch('desktop.type', { text: value })
        e.currentTarget.value = ''
      }
    },
    []
  )

  const handleMobileKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      e.stopPropagation()
      if (SPECIAL_KEYS.has(e.key)) {
        e.preventDefault()
        dispatch('desktop.key_press', { key: KEY_MAP[e.key] ?? e.key.toLowerCase() })
      }
    },
    []
  )

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
      <img ref={imgRef} src={frameUrl} alt={`Desktop ${id}`} className="w-full h-full"
        style={{ objectFit: 'contain', pointerEvents: 'none' }} />

      {/* Interactive overlay */}
      <div
        ref={interactRef}
        tabIndex={0}
        className="absolute inset-0"
        style={{ cursor: 'default', outline: 'none' }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={(e) => e.stopPropagation()}
        onWheel={handleWheel}
        onContextMenu={handleContextMenu}
        onKeyDown={handleKeyDown}
        onKeyUp={handleKeyUp}
        onTouchStart={() => {
          if (isTouchDevice && mobileInputRef.current) {
            mobileInputRef.current.focus()
          }
        }}
      >
        {/* Mobile keyboard proxy */}
        <input
          ref={mobileInputRef}
          type="text"
          inputMode="text"
          enterKeyHint="send"
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="off"
          spellCheck={false}
          onInput={handleMobileInput}
          onKeyDown={handleMobileKeyDown}
          style={{
            position: 'absolute',
            top: 0, left: 0,
            width: 16, height: 16,
            opacity: 0,
            zIndex: 10,
          }}
        />
      </div>

      {/* LIVE indicator */}
      <div className="absolute top-1 right-1 flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px]"
        style={{ background: 'rgba(0,0,0,0.6)', color: '#22c55e', pointerEvents: 'none' }}>
        <div className="w-1.5 h-1.5 rounded-full" style={{ background: '#22c55e' }} />
        LIVE
      </div>

      {/* Monitor label */}
      <div className="absolute bottom-1 left-1 px-1.5 py-0.5 rounded text-[9px]"
        style={{ background: 'rgba(0,0,0,0.6)', color: 'var(--color-text-tertiary)', pointerEvents: 'none' }}>
        {id}
      </div>
    </div>
  )
}
