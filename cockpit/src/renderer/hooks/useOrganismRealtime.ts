import { useEffect, useRef, useCallback } from 'react'
import { useRealtimeStore, OrganismEvent } from '../stores/realtimeStore'
import { useOrganismStore } from '../stores/organismStore'
import { useSystemStore } from '../stores/systemStore'
import { useCockpitStore } from '../stores/cockpitStore'
import { useActivityStore } from '../stores/activityStore'
import { useConfigStore } from '../stores/configStore'
import { useChatStore } from '../stores/chatStore'
import { useRoomsStore } from '../stores/roomsStore'
import { useBootstrapStore } from '../stores/bootstrapStore'
import { getWsToken, getClerkToken } from '../api/client'

const RECONNECT_BASE_MS = 1000
const RECONNECT_MAX_MS = 30000
const HEARTBEAT_INTERVAL_MS = 25000
const FALLBACK_POLL_MS = 5000

function buildWsUrl(): string {
  const envUrl = import.meta.env.VITE_ORGANISM_WS_URL as string | undefined
  return envUrl || `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/umh/ws`
}

async function getWsProtocols(): Promise<string[] | undefined> {
  const clerkToken = await getClerkToken()
  if (clerkToken) return [`bearer.${clerkToken}`]
  const wsToken = getWsToken()
  return wsToken ? [`bearer.${wsToken}`] : undefined
}

export function useOrganismRealtime(): void {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectDelay = useRef(RECONNECT_BASE_MS)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const heartbeatTimer = useRef<ReturnType<typeof setInterval> | null>(null)
  const fallbackTimer = useRef<ReturnType<typeof setInterval> | null>(null)
  const shouldReconnect = useRef(true)

  const setStatus = useRealtimeStore.getState().setStatus
  const pushEvents = useRealtimeStore.getState().pushEvents
  const pushPulse = useRealtimeStore.getState().pushPulse
  const incrementReconnect = useRealtimeStore.getState().incrementReconnect

  const startFallbackPolling = useCallback(() => {
    if (fallbackTimer.current) return
    useRealtimeStore.getState().setStatus('fallback')

    fallbackTimer.current = setInterval(async () => {
      try {
        await useOrganismStore.getState().fetchAll()
        await useOrganismStore.getState().fetchEvents()
      } catch {
        // polling failure is silent — WS reconnect will take over
      }
    }, FALLBACK_POLL_MS)
  }, [])

  const stopFallbackPolling = useCallback(() => {
    if (fallbackTimer.current) {
      clearInterval(fallbackTimer.current)
      fallbackTimer.current = null
    }
  }, [])

  const connect = useCallback(async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return

    setStatus('connecting')
    const url = buildWsUrl()
    const protocols = await getWsProtocols()

    try {
      const ws = protocols ? new WebSocket(url, protocols) : new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        reconnectDelay.current = RECONNECT_BASE_MS
        setStatus('connected')
        useCockpitStore.getState().setConnectionStatus('ws', 'connected')
        stopFallbackPolling()

        if (useBootstrapStore.getState().loaded) {
          useOrganismStore.getState().fetchAll()
        }

        heartbeatTimer.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }))
          }
        }, HEARTBEAT_INTERVAL_MS)
      }

      ws.onmessage = (event: MessageEvent) => {
        if (typeof event.data !== 'string') return
        try {
          const msg = JSON.parse(event.data) as Record<string, unknown>
          handleMessage(msg)
        } catch {
          // skip unparseable
        }
      }

      ws.onclose = () => {
        cleanup()
        setStatus('disconnected')
        useCockpitStore.getState().setConnectionStatus('ws', 'disconnected')

        if (shouldReconnect.current) {
          startFallbackPolling()
          incrementReconnect()
          reconnectTimer.current = setTimeout(() => {
            connect()
          }, reconnectDelay.current)
          reconnectDelay.current = Math.min(reconnectDelay.current * 2, RECONNECT_MAX_MS)
        }
      }

      ws.onerror = () => {
        ws.close()
      }
    } catch {
      startFallbackPolling()
      if (shouldReconnect.current) {
        reconnectTimer.current = setTimeout(() => connect(), reconnectDelay.current)
        reconnectDelay.current = Math.min(reconnectDelay.current * 2, RECONNECT_MAX_MS)
      }
    }
  }, [setStatus, pushEvents, pushPulse, incrementReconnect, startFallbackPolling, stopFallbackPolling])

  function handleMessage(msg: Record<string, unknown>) {
    const type = msg.type as string

    if (type === 'pulse') {
      pushPulse({
        cpu_percent: (msg.cpu_percent as number) ?? 0,
        memory_percent: (msg.memory_percent as number) ?? 0,
        disk_percent: (msg.disk_percent as number) ?? 0,
        containers: (msg.containers as Array<{ name: string; status: string }>) ?? [],
        node_metrics: msg.node_metrics as Record<string, { name: string; cpu: number | null; memory: number | null; disk: number | null; status: string }> | undefined,
      })

      useSystemStore.getState().setPulse({
        cpu_percent: (msg.cpu_percent as number) ?? 0,
        memory_percent: (msg.memory_percent as number) ?? 0,
        disk_percent: (msg.disk_percent as number) ?? 0,
        uptime: 0,
        active_agents: 0,
        pending_tasks: 0,
        pending_approvals: 0,
        trace_rate: 0,
      })

      const organismEvents = msg.organism_events as Array<Record<string, unknown>> | undefined
      if (organismEvents && organismEvents.length > 0) {
        const roomEvents = organismEvents.filter((e) => e.type === 'room_event')
        for (const re of roomEvents) {
          useRoomsStore.getState().handleWsEvent({
            type: re.event as string,
            payload: re as unknown,
          })
        }

        const nonRoom = organismEvents.filter((e) => e.type !== 'room_event')
        const parsed: OrganismEvent[] = nonRoom.map((e) => ({
          event_id: (e.event_id as string) ?? '',
          domain: (e.domain as string) ?? 'unknown',
          event_type: (e.event_type as string) ?? '',
          source: (e.source as string) ?? '',
          priority: (e.priority as string) ?? 'normal',
          data: (e.data as Record<string, unknown>) ?? {},
          timestamp: (e.timestamp as number) ?? Date.now() / 1000,
          correlation_id: (e.correlation_id as string) ?? null,
        }))
        if (parsed.length > 0) pushEvents(parsed)

        const hasMutationEvents = parsed.some((e) =>
          ['governance', 'execution', 'runtime', 'supervisor'].includes(e.domain)
        )
        if (hasMutationEvents) {
          useOrganismStore.getState().fetchSpine()
          useOrganismStore.getState().fetchPending()
          useOrganismStore.getState().fetchCompleted()
        }
      }
    } else if (type === 'activity' || type === 'event') {
      const d = (msg.data as Record<string, unknown>) || msg
      useActivityStore.getState().addEvent({
        id: (d.id as string) || crypto.randomUUID(),
        timestamp: (d.timestamp as string) || new Date().toISOString(),
        source: (d.source as string) || 'system',
        type: (d.type as string) || 'info',
        severity: (d.severity as 'info' | 'warning' | 'error') || 'info',
        summary: (d.summary as string) || '',
      })
    } else if (type === 'config_changed') {
      const key = msg.key as string
      const value = msg.value
      if (key && value !== undefined) {
        useConfigStore.getState().applyRemoteUpdate(key, value)
      }
    } else if (type === 'chat_message') {
      useChatStore.getState().pushExternalMessage({
        id: (msg.id as string) || `ext-${Date.now()}`,
        sender: (msg.sender as 'operator' | 'assistant' | 'system') || 'system',
        content: (msg.content as string) || '',
        timestamp: (msg.timestamp as string) || new Date().toISOString(),
        origin_channel: (msg.origin_channel as string) || 'unknown',
        role: (msg.role as string) || undefined,
        kind: (msg.kind as string) || undefined,
        intent: (msg.intent as string) || undefined,
        title: (msg.title as string) || undefined,
      })
    } else if (type === 'pong') {
      // heartbeat ack
    }
  }

  function cleanup() {
    if (heartbeatTimer.current) {
      clearInterval(heartbeatTimer.current)
      heartbeatTimer.current = null
    }
  }

  useEffect(() => {
    shouldReconnect.current = true
    connect()

    return () => {
      shouldReconnect.current = false
      cleanup()
      stopFallbackPolling()
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current)
        reconnectTimer.current = null
      }
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [connect, stopFallbackPolling])
}
