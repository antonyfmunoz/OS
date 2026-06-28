import { useState, useRef, useCallback, useEffect } from 'react'
import {
  ArrowLeft,
  ArrowRight,
  RotateCw,
  Maximize2,
  Minimize2,
  RefreshCw,
  ExternalLink,
  Plus,
  X,
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

// ── Single browser pane ─────────────────────────────────────

export function BrowserPane({ paneId }: { paneId: string }) {
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
  } = useBrowserStream(paneId)

  const [urlInput, setUrlInput] = useState('')
  const [urlFocused, setUrlFocused] = useState(false)
  const [deviceMode, setDeviceMode] = useState<ViewportPreset>('responsive')
  const viewportRef = useRef<HTMLDivElement>(null)
  const interactRef = useRef<HTMLDivElement>(null)
  const mobileInputRef = useRef<HTMLInputElement>(null)
  const isTouchDevice = 'ontouchstart' in window

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
      if (isTouchDevice) {
        mobileInputRef.current?.focus()
      } else {
        interactRef.current?.focus()
      }
      const { x, y } = scaleCoords(e)
      sendMouse('mousePressed', x, y, {
        button: mouseButton(e),
        clickCount: e.detail || 1,
      })
    },
    [scaleCoords, sendMouse, isTouchDevice]
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

  const SPECIAL_KEYS = new Set(['Enter', 'Backspace', 'Tab', 'Escape', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Delete'])

  const handleMobileInput = useCallback(
    (e: React.FormEvent<HTMLInputElement>) => {
      const value = e.currentTarget.value
      if (value) {
        insertText(value)
        e.currentTarget.value = ''
      }
    },
    [insertText]
  )

  const handleMobileKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (SPECIAL_KEYS.has(e.key)) {
        e.preventDefault()
        sendKey('keyDown', e.key, e.code, { modifiers: getModifiers(e) })
        sendKey('keyUp', e.key, e.code, { modifiers: getModifiers(e) })
      }
    },
    [sendKey]
  )

  const handleViewportClick = useCallback(() => {
    if (isTouchDevice) {
      mobileInputRef.current?.focus()
    } else {
      interactRef.current?.focus()
    }
  }, [isTouchDevice])

  const handlePopOut = useCallback(() => {
    if (currentUrl && currentUrl !== 'about:blank') {
      window.open(currentUrl, '_blank')
    }
  }, [currentUrl])

  const btnStyle = {
    color: 'var(--color-text-tertiary)',
  }

  return (
    <div className="flex flex-col h-full">
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

        {/* Pop out */}
        <button
          onClick={handlePopOut}
          className="p-1 rounded hover:opacity-80"
          style={btnStyle}
          title="Open in browser"
        >
          <ExternalLink size={14} />
        </button>

        {/* Reconnect */}
        <button
          onClick={reconnect}
          className="p-1 rounded hover:opacity-80"
          style={btnStyle}
          title="Reconnect"
        >
          <RefreshCw size={14} />
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
          onTouchStart={() => {
            if (isTouchDevice && mobileInputRef.current) {
              mobileInputRef.current.focus()
            }
          }}
        >
          {isTouchDevice && (
            <input
              ref={mobileInputRef}
              inputMode="text"
              enterKeyHint="send"
              autoCapitalize="off"
              autoCorrect="off"
              autoComplete="off"
              onInput={handleMobileInput}
              onKeyDown={handleMobileKeyDown}
              onPaste={handlePaste}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: 16,
                height: 16,
                opacity: 0,
                zIndex: 10,
              }}
            />
          )}
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

// ── Pane manager (outer) ────────────────────────────────────

export function BrowserPanel() {
  const [panes, setPanes] = useState<string[]>(['0'])
  const nextPaneId = useRef(1)
  const [fullscreen, setFullscreen] = useState(false)

  const addPane = useCallback(() => {
    setPanes((prev) => {
      if (prev.length >= 4) return prev
      return [...prev, String(nextPaneId.current++)]
    })
  }, [])

  const removePane = useCallback((index: number) => {
    setPanes((prev) => {
      if (prev.length <= 1) return prev
      return prev.filter((_, i) => i !== index)
    })
  }, [])

  const count = panes.length
  const gridClass =
    count === 1
      ? 'grid-cols-1'
      : count === 2
        ? 'grid-cols-2'
        : 'grid-cols-2 grid-rows-2'

  return (
    <div className={`flex flex-col h-full ${fullscreen ? 'fixed inset-0 z-50 bg-black' : ''}`}>
      {/* Panel header */}
      <div
        className="flex items-center gap-2 px-2 py-1 shrink-0"
        style={{ borderBottom: '1px solid var(--color-border)' }}
      >
        <span className="text-[11px]" style={{ color: 'var(--color-text-tertiary)' }}>
          Browser
        </span>
        {count > 1 && (
          <span
            className="text-[10px] px-1 rounded"
            style={{ color: 'var(--color-text-tertiary)', background: 'var(--color-surface-raised)' }}
          >
            {count}
          </span>
        )}
        <div className="flex-1" />
        <button
          onClick={addPane}
          disabled={count >= 4}
          className="p-1 rounded hover:opacity-80 disabled:opacity-30"
          style={{ color: 'var(--color-text-tertiary)' }}
          title="Add browser pane"
        >
          <Plus size={14} />
        </button>
        <button
          onClick={() => setFullscreen((f) => !f)}
          className="p-1 rounded hover:opacity-80"
          style={{ color: 'var(--color-text-tertiary)' }}
          title={fullscreen ? 'Exit fullscreen' : 'Fullscreen'}
        >
          {fullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
        </button>
      </div>

      {/* Pane grid */}
      <div className={`flex-1 grid ${gridClass} min-h-0`}>
        {panes.map((paneId, i) => (
          <div
            key={paneId}
            className="overflow-hidden relative"
            style={{
              borderRight: count > 1 && i % 2 === 0 ? '1px solid var(--color-border)' : undefined,
              borderBottom: count > 2 && i < 2 ? '1px solid var(--color-border)' : undefined,
              gridColumn: count === 3 && i === 2 ? '1 / -1' : undefined,
            }}
          >
            {count > 1 && (
              <button
                onClick={() => removePane(i)}
                className="absolute top-1.5 right-1.5 z-20 p-0.5 rounded hover:opacity-80"
                style={{ color: 'var(--color-text-tertiary)', background: 'var(--color-surface-raised)' }}
                title="Close pane"
              >
                <X size={10} />
              </button>
            )}
            <BrowserPane paneId={paneId} />
          </div>
        ))}
      </div>
    </div>
  )
}
