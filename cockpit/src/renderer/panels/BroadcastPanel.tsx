import { useEffect, useState } from 'react'
import { Radio, Layers } from 'lucide-react'
import { useViewContextStore } from '../stores/viewContextStore'
import { useBroadcastStore } from '../stores/broadcastStore'
import { useBroadcastConnection } from '../hooks/useBroadcastConnection'
import { fetchApi } from '../api/client'

export function BroadcastPanel() {
  const setViewContext = useViewContextStore((s) => s.setContext)

  useEffect(() => {
    setViewContext({
      active_route: 'broadcast',
      visible_context_summary: 'Broadcast Studio — stream control and health',
    })
  }, [setViewContext])

  useBroadcastConnection()

  const {
    connected, broadcastState, health, pid,
    composite, activeSceneId, scenes, sources,
  } = useBroadcastStore()
  const [outputUrl, setOutputUrl] = useState('rtmp://localhost/live/test')
  const [starting, setStarting] = useState(false)
  const [stopping, setStopping] = useState(false)
  const [switching, setSwitching] = useState<string | null>(null)

  const handleStart = async () => {
    setStarting(true)
    try {
      await fetchApi('/broadcast/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_type: 'test_pattern',
          source_config: {},
          output_url: outputUrl,
        }),
      })
    } catch (err) {
      console.error('[Broadcast] start failed:', err)
    } finally {
      setStarting(false)
    }
  }

  const handleStop = async () => {
    setStopping(true)
    try {
      await fetchApi('/broadcast/stop', { method: 'POST' })
    } catch (err) {
      console.error('[Broadcast] stop failed:', err)
    } finally {
      setStopping(false)
    }
  }

  const handleSwitchScene = async (sceneId: string) => {
    setSwitching(sceneId)
    try {
      await fetchApi('/broadcast/scene/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scene_id: sceneId }),
      })
    } catch (err) {
      console.error('[Broadcast] scene switch failed:', err)
    } finally {
      setSwitching(null)
    }
  }

  const isLive = broadcastState === 'live'
  const statusColor = !connected
    ? 'text-neutral-500'
    : isLive
      ? health.status_tier === 'HEALTHY'
        ? 'text-ok'
        : health.status_tier === 'WARNING'
          ? 'text-warn'
          : 'text-danger'
      : 'text-neutral-400'

  return (
    <div className="p-4 space-y-4 overflow-y-auto h-full text-xs font-mono">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Radio className="w-4 h-4 text-cyan" />
        <span className="text-sm font-bold text-white">Broadcast Studio</span>
        <span className={`ml-auto text-xs ${statusColor}`}>
          {!connected ? 'DISCONNECTED' : broadcastState.toUpperCase()}
        </span>
        {pid && <span className="text-neutral-500">pid:{pid}</span>}
      </div>

      {/* Controls */}
      <div className="space-y-2">
        <label className="block text-neutral-400">
          RTMP Destination
          <input
            type="text"
            value={outputUrl}
            onChange={(e) => setOutputUrl(e.target.value)}
            disabled={isLive}
            className="mt-1 block w-full bg-canvas border border-border rounded px-2 py-1 text-white text-xs font-mono focus:border-cyan focus:outline-none disabled:opacity-50"
          />
        </label>

        <div className="flex gap-2">
          {!isLive ? (
            <button
              onClick={handleStart}
              disabled={starting || !outputUrl}
              className="px-3 py-1.5 bg-cyan/20 text-cyan border border-cyan/30 rounded text-xs hover:bg-cyan/30 disabled:opacity-40"
            >
              {starting ? 'Starting...' : 'Start Stream'}
            </button>
          ) : (
            <button
              onClick={handleStop}
              disabled={stopping}
              className="px-3 py-1.5 bg-danger/20 text-danger border border-danger/30 rounded text-xs hover:bg-danger/30 disabled:opacity-40"
            >
              {stopping ? 'Stopping...' : 'Stop Stream'}
            </button>
          )}
        </div>
      </div>

      {/* Scene Switcher — visible when composite mode + live */}
      {isLive && composite && scenes.length > 0 && (
        <div className="border border-border rounded p-3 space-y-2">
          <div className="flex items-center gap-2">
            <Layers className="w-3 h-3 text-cyan" />
            <span className="text-neutral-400 text-[10px] uppercase tracking-wider">
              Scenes
            </span>
            <span className="ml-auto text-[10px] text-neutral-500">
              {sources.length} source{sources.length !== 1 ? 's' : ''}
            </span>
          </div>
          <div className="flex gap-2 flex-wrap">
            {scenes.map((scene) => {
              const isActive = scene.scene_id === activeSceneId
              const isSwitching = switching === scene.scene_id
              return (
                <button
                  key={scene.scene_id}
                  onClick={() => handleSwitchScene(scene.scene_id)}
                  disabled={isActive || isSwitching}
                  className={`px-3 py-1.5 rounded text-xs border transition-colors ${
                    isActive
                      ? 'bg-cyan/20 text-cyan border-cyan/50'
                      : 'bg-canvas text-neutral-300 border-border hover:border-cyan/30 hover:text-white'
                  } disabled:opacity-60`}
                >
                  {isSwitching ? 'Switching...' : scene.name}
                  {isActive && ' ●'}
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Health Metrics */}
      {isLive && (
        <div className="border border-border rounded p-3 space-y-2">
          <div className="text-neutral-400 text-[10px] uppercase tracking-wider">
            Stream Health
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Metric label="FPS" value={health.fps.toFixed(1)} />
            <Metric label="Bitrate" value={`${health.bitrate_kbps.toFixed(0)} kbps`} />
            <Metric label="Frames" value={health.frame.toString()} />
            <Metric label="Dropped" value={health.drop_frames.toString()} warn={health.drop_frames > 0} />
            <Metric label="Drop %" value={`${health.drop_percentage.toFixed(1)}%`} warn={health.drop_percentage > 1} />
            <Metric label="Uptime" value={formatUptime(health.uptime_s)} />
            <Metric label="Speed" value={health.speed} />
            <Metric label="Size" value={formatBytes(health.total_size_bytes)} />
            <Metric
              label="Status"
              value={health.status_tier}
              warn={health.status_tier !== 'HEALTHY'}
            />
          </div>
        </div>
      )}

      {/* Idle state */}
      {broadcastState === 'idle' && connected && (
        <div className="text-neutral-500 text-center py-8">
          Ready to broadcast. Enter an RTMP URL and click Start Stream.
        </div>
      )}

      {!connected && (
        <div className="text-neutral-500 text-center py-8">
          Broadcast engine not connected. Ensure the API server is running.
        </div>
      )}
    </div>
  )
}

function Metric({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <div>
      <div className="text-[10px] text-neutral-500 uppercase">{label}</div>
      <div className={`text-sm ${warn ? 'text-warn' : 'text-white'}`}>{value}</div>
    </div>
  )
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}
