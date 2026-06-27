import { useState, useRef, useCallback, useEffect } from 'react'
import {
  ArrowLeft,
  ArrowRight,
  RotateCw,
  Maximize2,
  Minimize2,
  RefreshCw,
} from 'lucide-react'
import { useBrowserStream } from '../hooks/useBrowserStream'
import {
  ViewportSelector,
  VIEWPORT_PRESETS,
  type ViewportPreset,
} from '../components/ViewportSelector'

function getModifiers(e: React.KeyboardEvent | React.MouseEvent): number {
  let m = 0
  if (e.altKey) m |= 1
  if (e.ctrlKey) m |= 2
  if (e.metaKey) m |= 4
  if (e.shiftKey) m |= 8
  return m
}

function mouseButton(e: React.MouseEvent): string {
  switch (e.button) {
    case 0:
      return 'left'
    case 1:
      return 'middle'
    case 2:
      return 'right'
    default:
      return 'left'
  }
}

export function BrowserPanel() {
  const {
    connected,
    currentUrl,
    pageTitle,
    loading,
    frameUrl,
    viewportWidth,
    viewportHeight,
    navigate,
    goBack,
    goForward,
    reload,
    reconnect,
    sendMouse,
    sendKey,
    insertText,
    resize,
  } = useBrowserStream()

  const [urlInput, setUrlInput] = useState('')
  const [urlFocused, setUrlFocused] = useState(false)
  const [fullscreen, setFullscreen] = useState(false)
  const [deviceMode, setDeviceMode] = useState<ViewportPreset>('responsive')
  const viewportRef = useRef<HTMLDivElement>(null)
  const interactRef = useRef<HTMLDivElement>(null)

  const isFixedDevice = deviceMode !== 'responsive'
  const deviceConfig = VIEWPORT_PRESETS[deviceMode]

  useEffect(() => {
    if (!urlFocused) {
      setUrlInput(currentUrl === 'about:blank' ? '' : currentUrl)
    }
  }, [currentUrl, urlFocused])

  useEffect(() => {
    if (!viewportRef.current) return
    if (isFixedDevice) return
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect
        if (width > 0 && height > 0) {
          resize(Math.round(width), Math.round(height))
        }
      }
    })
    observer.observe(viewportRef.current)
    return () => observer.disconnect()
  }, [resize, isFixedDevice])

  const handleDeviceChange = useCallback(
    (preset: ViewportPreset) => {
      setDeviceMode(preset)
      const cfg = VIEWPORT_PRESETS[preset]
      if (preset !== 'responsive' && cfg.width > 0 && cfg.height > 0) {
        resize(cfg.width, cfg.height)
      } else if (preset === 'responsive' && viewportRef.current) {
        const rect = viewportRef.current.getBoundingClientRect()
        if (rect.width > 0 && rect.height > 0) {
          resize(Math.round(rect.width), Math.round(rect.height))
        }
      }
    },
    [resize]
  )

  const scaleCoords = useCallback(
    (e: React.MouseEvent): { x: number; y: number } => {
      const rect = interactRef.current?.getBoundingClientRect()
      if (!rect) return { x: 0, y: 0 }
      return {
        x: Math.round(((e.clientX - rect.left) / rect.width) * viewportWidth),
        y: Math.round(((e.clientY - rect.top) / rect.height) * viewportHeight),
      }
    },
    [viewportWidth, viewportHeight]
  )

  const handleUrlSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()
      if (urlInput.trim()) {
        navigate(urlInput.trim())
        interactRef.current?.focus()
      }
    },
    [urlInput, navigate]
  )

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      const { x, y } = scaleCoords(e)
      sendMouse('mouseMoved', x, y)
    },
    [scaleCoords, sendMouse]
  )

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      interactRef.current?.focus()
      const { x, y } = scaleCoords(e)
      sendMouse('mousePressed', x, y, {
        button: mouseButton(e),
        clickCount: e.detail || 1,
      })
    },
    [scaleCoords, sendMouse]
  )

  const handleMouseUp = useCallback(
    (e: React.MouseEvent) => {
      const { x, y } = scaleCoords(e)
      sendMouse('mouseReleased', x, y, { button: mouseButton(e) })
    },
    [scaleCoords, sendMouse]
  )

  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      const { x, y } = scaleCoords(e)
      sendMouse('mouseWheel', x, y, {
        deltaX: Math.round(e.deltaX),
        deltaY: Math.round(e.deltaY),
      })
    },
    [scaleCoords, sendMouse]
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      e.stopPropagation()
      // Let paste (Ctrl/Cmd+V) through to onPaste handler
      if ((e.ctrlKey || e.metaKey) && e.key === 'v') return
      e.preventDefault()
      sendKey('keyDown', e.key, e.code, {
        text: e.key.length === 1 ? e.key : '',
        modifiers: getModifiers(e),
      })
    },
    [sendKey]
  )

  const handleKeyUp = useCallback(
    (e: React.KeyboardEvent) => {
      e.stopPropagation()
      if ((e.ctrlKey || e.metaKey) && e.key === 'v') return
      e.preventDefault()
      sendKey('keyUp', e.key, e.code, { modifiers: getModifiers(e) })
    },
    [sendKey]
  )

  const handlePaste = useCallback(
    (e: React.ClipboardEvent) => {
      e.preventDefault()
      e.stopPropagation()
      const text = e.clipboardData.getData('text/plain')
      if (text) insertText(text)
    },
    [insertText]
  )

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
  }, [])

  const handleViewportClick = useCallback(() => {
    interactRef.current?.focus()
  }, [])

  const btnStyle = {
    color: 'var(--color-text-tertiary)',
  }

  return (
    <div className={`flex flex-col h-full ${fullscreen ? 'fixed inset-0 z-50 bg-black' : ''}`}>
      {/* Toolbar */}
      <div
        className="flex items-center gap-1 px-2 py-1 shrink-0"
        style={{ borderBottom: '1px solid var(--color-border)' }}
      >
        {/* Connection indicator */}
        <div
          className="w-2 h-2 rounded-full shrink-0"
          style={{ backgroundColor: connected ? '#22c55e' : '#ef4444' }}
          title={connected ? 'Connected' : 'Disconnected'}
        />
        <span
          className="text-[11px] mr-1"
          style={{ color: 'var(--color-text-tertiary)' }}
        >
          Browser
        </span>

        {/* Navigation buttons */}
        <button
          onClick={goBack}
          className="p-1 rounded hover:opacity-80"
          style={btnStyle}
          title="Back"
        >
          <ArrowLeft size={14} />
        </button>
        <button
          onClick={goForward}
          className="p-1 rounded hover:opacity-80"
          style={btnStyle}
          title="Forward"
        >
          <ArrowRight size={14} />
        </button>
        <button
          onClick={reload}
          className="p-1 rounded hover:opacity-80"
          style={btnStyle}
          title="Reload"
        >
          <RotateCw size={14} />
        </button>

        {/* URL bar */}
        <form onSubmit={handleUrlSubmit} className="flex-1 mx-1">
          <input
            type="text"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            onFocus={() => setUrlFocused(true)}
            onBlur={() => setUrlFocused(false)}
            placeholder="Enter URL..."
            className="w-full px-2 py-0.5 text-[12px] rounded"
            style={{
              backgroundColor: 'var(--color-bg-secondary)',
              color: 'var(--color-text-primary)',
              border: '1px solid var(--color-border)',
              outline: 'none',
            }}
            title={pageTitle || currentUrl}
          />
        </form>

        {/* Device viewport selector */}
        <ViewportSelector value={deviceMode} onChange={handleDeviceChange} />

        {/* Reconnect + Fullscreen */}
        <button
          onClick={reconnect}
          className="p-1 rounded hover:opacity-80"
          style={btnStyle}
          title="Reconnect"
        >
          <RefreshCw size={14} />
        </button>
        <button
          onClick={() => setFullscreen((f) => !f)}
          className="p-1 rounded hover:opacity-80"
          style={btnStyle}
          title={fullscreen ? 'Exit fullscreen' : 'Fullscreen'}
        >
          {fullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
        </button>
      </div>

      {/* Loading bar */}
      {loading && (
        <div className="h-[2px] w-full overflow-hidden shrink-0" style={{ backgroundColor: 'var(--color-border)' }}>
          <div
            className="h-full animate-pulse"
            style={{ backgroundColor: '#3b82f6', width: '40%' }}
          />
        </div>
      )}

      {/* Viewport */}
      <div
        ref={viewportRef}
        className="flex-1 relative outline-none overflow-hidden flex items-center justify-center"
        style={{ cursor: connected ? 'default' : 'not-allowed' }}
      >
        <div
          ref={interactRef}
          tabIndex={0}
          className="relative focus:ring-1 focus:ring-blue-500/50 outline-none"
          style={
            isFixedDevice
              ? {
                  width: deviceConfig.width,
                  height: deviceConfig.height,
                  maxWidth: '100%',
                  maxHeight: '100%',
                  border: '1px solid var(--color-border)',
                  borderRadius: deviceMode === 'mobile' ? 16 : deviceMode === 'tablet' ? 8 : 0,
                  overflow: 'hidden',
                  boxShadow: '0 4px 24px rgba(0,0,0,0.3)',
                }
              : { width: '100%', height: '100%' }
          }
          onClick={handleViewportClick}
          onMouseMove={handleMouseMove}
          onMouseDown={handleMouseDown}
          onMouseUp={handleMouseUp}
          onWheel={handleWheel}
          onKeyDown={handleKeyDown}
          onKeyUp={handleKeyUp}
          onPaste={handlePaste}
          onContextMenu={handleContextMenu}
        >
          {frameUrl ? (
            <img
              src={frameUrl}
              alt=""
              className="absolute inset-0 w-full h-full"
              style={{ objectFit: isFixedDevice ? 'fill' : 'contain', pointerEvents: 'none' }}
              draggable={false}
            />
          ) : (
            <div className="flex items-center justify-center h-full">
              <span
                className="text-[13px]"
                style={{ color: 'var(--color-text-tertiary)' }}
              >
                {connected ? 'Waiting for frames...' : 'Connecting...'}
              </span>
            </div>
          )}
        </div>
        {isFixedDevice && (
          <div
            className="absolute bottom-2 text-[10px]"
            style={{ color: 'var(--color-text-tertiary)' }}
          >
            {deviceConfig.width}×{deviceConfig.height}
          </div>
        )}
      </div>
    </div>
  )
}
