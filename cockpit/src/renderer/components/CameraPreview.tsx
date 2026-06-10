import { useEffect, useRef, useCallback, useState } from 'react'
import { clsx } from 'clsx'
import { Camera, CameraOff, Aperture, Eye, EyeOff, ChevronDown, Maximize2, Minimize2, PictureInPicture2 } from 'lucide-react'
import { useVisionStore, type CameraPreset } from '../stores/visionStore'
import { VisionWsClient } from '../api/vision-ws'
import { useVisionPopout } from './VisionPopout'

let visionClient: VisionWsClient | null = null

function getClient(): VisionWsClient {
  if (!visionClient) visionClient = new VisionWsClient()
  return visionClient
}

export function CameraPreview() {
  const {
    connected, streaming, cameraStatus, activePreset, latestFrameUrl,
    error, presets, analysisStatus, frameCount,
    setConnected, setStreaming, setCameraStatus, setActivePreset,
    setLatestFrame, setError, setPresets, incrementFrameCount, reset,
  } = useVisionStore()

  const poppedOut = useVisionStore((s) => s.poppedOut)
  const { openPopout } = useVisionPopout()
  const [expanded, setExpanded] = useState(false)
  const [presetOpen, setPresetOpen] = useState(false)
  const imgRef = useRef<HTMLImageElement>(null)
  const clientRef = useRef<VisionWsClient | null>(null)

  useEffect(() => {
    const client = getClient()
    clientRef.current = client

    const unsubs = [
      client.on('connected', () => {
        setConnected(true)
        client.requestPresets()
        client.requestStatus()
        client.startCamera({ fps: 2, width: 640, height: 480, quality: 60 })
        client.subscribe(2, 60)
      }),
      client.on('disconnected', () => {
        setConnected(false)
        setCameraStatus('off')
        setStreaming(false)
      }),
      client.on('vision_frame', (d) => {
        const url = d.url as string
        const ts = d.timestamp as number
        setLatestFrame(url, ts)
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
      client.on('preset_saved', (d) => {
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
      reset()
      clientRef.current = null
    }
  }, [])

  const handleStart = useCallback(() => {
    const client = clientRef.current
    if (!client?.connected) return
    setCameraStatus('connecting')
    client.startCamera({ fps: 2, width: 640, height: 480, quality: 60 })
    client.subscribe(2, 60)
  }, [])

  const handleStop = useCallback(() => {
    const client = clientRef.current
    if (!client?.connected) return
    client.stopCamera()
    client.unsubscribe()
    setCameraStatus('off')
    setStreaming(false)
  }, [])

  const handleSnapshot = useCallback(() => {
    clientRef.current?.requestSnapshot()
  }, [])

  const handlePreset = useCallback((name: string) => {
    clientRef.current?.setPreset(name)
    setActivePreset(name)
    setPresetOpen(false)
  }, [])

  const isActive = cameraStatus === 'live' || cameraStatus === 'connecting'

  return (
    <div className={clsx('flex flex-col gap-2', expanded && 'fixed inset-0 z-50 bg-surface p-4')}>
      {/* Privacy indicator */}
      {isActive && (
        <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-danger/10 text-danger text-[10px] font-mono uppercase tracking-wider">
          <span className="w-1.5 h-1.5 rounded-full bg-danger animate-pulse" />
          camera active
        </div>
      )}

      {/* Preview frame */}
      <div className={clsx(
        'relative rounded border overflow-hidden bg-black',
        expanded ? 'flex-1' : 'aspect-video',
        isActive ? 'border-danger/30' : 'border-border',
      )}>
        {latestFrameUrl ? (
          <img
            ref={imgRef}
            src={latestFrameUrl}
            alt="Camera preview"
            className="w-full h-full object-contain"
          />
        ) : (
          <div className="flex items-center justify-center w-full h-full text-text-tertiary">
            <Camera size={24} className="opacity-30" />
          </div>
        )}

        {/* FPS overlay */}
        {streaming && (
          <div className="absolute top-1 right-1 px-1.5 py-0.5 rounded bg-black/60 text-[9px] font-mono text-text-secondary">
            {frameCount} frames
          </div>
        )}

        {/* Expand/collapse + Pop-out */}
        <div className="absolute top-1 left-1 flex items-center gap-1">
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-1 rounded bg-black/60 text-text-secondary hover:text-white"
            title={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
          </button>
          <button
            onClick={openPopout}
            className="p-1 rounded bg-black/60 text-text-secondary hover:text-white"
            title="Pop out"
          >
            <PictureInPicture2 size={12} />
          </button>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-1.5">
        {/* Start / Stop */}
        {!isActive ? (
          <button
            onClick={handleStart}
            disabled={!connected}
            className={clsx(
              'flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono uppercase tracking-wider transition-colors',
              connected
                ? 'bg-ok/10 text-ok hover:bg-ok/20'
                : 'bg-surface text-text-tertiary cursor-not-allowed',
            )}
          >
            <Camera size={12} />
            Start
          </button>
        ) : (
          <button
            onClick={handleStop}
            className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono uppercase tracking-wider bg-danger/10 text-danger hover:bg-danger/20"
          >
            <CameraOff size={12} />
            Stop
          </button>
        )}

        {/* Snapshot */}
        <button
          onClick={handleSnapshot}
          disabled={!connected}
          className={clsx(
            'flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono uppercase tracking-wider transition-colors',
            connected
              ? 'bg-cyan/10 text-cyan hover:bg-cyan/20'
              : 'bg-surface text-text-tertiary cursor-not-allowed',
          )}
        >
          <Aperture size={12} />
          Snap
        </button>

        {/* Preset selector */}
        <div className="relative">
          <button
            onClick={() => setPresetOpen(!presetOpen)}
            disabled={!connected}
            className={clsx(
              'flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono uppercase tracking-wider transition-colors',
              connected
                ? 'bg-surface-hover text-text-secondary hover:text-text-primary'
                : 'bg-surface text-text-tertiary cursor-not-allowed',
            )}
          >
            <Eye size={12} />
            {activePreset || 'Preset'}
            <ChevronDown size={10} />
          </button>

          {presetOpen && (
            <div className="absolute bottom-full left-0 mb-1 w-40 rounded border border-border bg-surface shadow-lg z-10">
              {Object.entries(presets).map(([name, preset]) => (
                <button
                  key={name}
                  onClick={() => handlePreset(name)}
                  className={clsx(
                    'block w-full text-left px-3 py-1.5 text-[11px] font-mono hover:bg-surface-hover transition-colors',
                    activePreset === name ? 'text-cyan' : 'text-text-secondary',
                  )}
                >
                  {preset.label || name}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Connection status */}
      <div className="flex items-center gap-2 text-[10px] font-mono text-text-tertiary">
        <span className={clsx(
          'w-1.5 h-1.5 rounded-full',
          connected ? 'bg-ok' : 'bg-danger',
        )} />
        {connected ? 'vision relay connected' : 'vision relay disconnected'}
        {analysisStatus !== 'idle' && (
          <span className="text-cyan ml-auto">{analysisStatus}</span>
        )}
      </div>

      {/* Error display */}
      {error && (
        <div className="px-2 py-1 rounded bg-danger/10 text-danger text-[10px] font-mono">
          {error}
        </div>
      )}
    </div>
  )
}
