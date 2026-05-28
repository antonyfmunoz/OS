import { useRealtimeStore } from '../stores/realtimeStore'

export function ConnectionBanner() {
  const status = useRealtimeStore((s) => s.status)
  const reconnectCount = useRealtimeStore((s) => s.reconnectCount)
  const eventsPerMinute = useRealtimeStore((s) => s.eventsPerMinute)
  const lastPulseTimestamp = useRealtimeStore((s) => s.lastPulseTimestamp)

  if (status === 'connected') {
    const stalePulse = lastPulseTimestamp && Date.now() - lastPulseTimestamp > 10000
    if (stalePulse) {
      return (
        <div className="flex items-center gap-2 px-3 py-1 bg-warn/10 border-b border-warn/20">
          <span className="w-2 h-2 rounded-full bg-warn animate-pulse" />
          <span className="text-[10px] text-warn font-mono">WS connected but no pulse in 10s — possible backend stall</span>
        </div>
      )
    }
    return null
  }

  const bgClass = status === 'fallback' ? 'bg-amber/10 border-amber/20' :
    status === 'connecting' ? 'bg-warn/10 border-warn/20' :
    'bg-danger/10 border-danger/20'

  const textClass = status === 'fallback' ? 'text-amber' :
    status === 'connecting' ? 'text-warn' :
    'text-danger'

  const dotClass = status === 'connecting' ? 'bg-warn animate-pulse' :
    status === 'fallback' ? 'bg-amber' :
    'bg-danger'

  const label = status === 'fallback' ? 'Polling fallback active — WebSocket reconnecting' :
    status === 'connecting' ? 'Connecting to organism WebSocket...' :
    'Disconnected from organism — data may be stale'

  return (
    <div className={`flex items-center gap-2 px-3 py-1 border-b ${bgClass}`}>
      <span className={`w-2 h-2 rounded-full ${dotClass}`} />
      <span className={`text-[10px] font-mono flex-1 ${textClass}`}>{label}</span>
      {reconnectCount > 0 && (
        <span className="text-[9px] text-text-tertiary font-mono">×{reconnectCount} reconnects</span>
      )}
      {status === 'fallback' && (
        <span className="text-[9px] text-text-tertiary font-mono">{eventsPerMinute}/min via poll</span>
      )}
    </div>
  )
}
