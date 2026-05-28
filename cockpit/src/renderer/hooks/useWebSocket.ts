import { useEffect, useRef } from 'react'
import { WsClient } from '../api/websocket'
import { useSystemStore } from '../stores/systemStore'
import { useActivityStore } from '../stores/activityStore'
import { useCockpitStore } from '../stores/cockpitStore'
import { getWsToken } from '../api/client'

export function useWebSocket() {
  const clientRef = useRef<WsClient | null>(null)
  const setConnectionStatus = useCockpitStore((s) => s.setConnectionStatus)

  useEffect(() => {
    const wsUrl = import.meta.env.VITE_WS_URL || `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`
    const token = getWsToken()
    const protocols = token ? [`bearer.${token}`] : undefined
    const client = new WsClient(wsUrl, protocols)
    clientRef.current = client

    const cleanups: (() => void)[] = []

    cleanups.push(client.on('connected', () => {
      setConnectionStatus('ws', 'connected')
    }))

    cleanups.push(client.on('disconnected', () => {
      setConnectionStatus('ws', 'disconnected')
    }))

    cleanups.push(client.on('pulse', (msg) => {
      const d = msg.data as Record<string, unknown> | undefined
      const pulse = d || msg
      useSystemStore.getState().setPulse({
        cpu_percent: (pulse.cpu_percent as number) || 0,
        memory_percent: (pulse.memory_percent as number) || 0,
        disk_percent: (pulse.disk_percent as number) || 0,
        uptime: (pulse.uptime as number) || 0,
        active_agents: (pulse.active_agents as number) || 0,
        pending_tasks: (pulse.pending_tasks as number) || 0,
        pending_approvals: (pulse.pending_approvals as number) || 0,
        trace_rate: (pulse.trace_rate as number) || 0,
      })
    }))

    cleanups.push(client.on('activity', (msg) => {
      const d = msg.data as Record<string, unknown> | undefined
      const event = d || msg
      useActivityStore.getState().addEvent({
        id: (event.id as string) || crypto.randomUUID(),
        timestamp: (event.timestamp as string) || new Date().toISOString(),
        source: (event.source as string) || 'system',
        type: (event.type as string) || 'info',
        severity: (event.severity as 'info' | 'warning' | 'error') || 'info',
        summary: (event.summary as string) || '',
      })
    }))

    cleanups.push(client.on('event', (msg) => {
      const d = msg.data as Record<string, unknown> | undefined
      const event = d || msg
      useActivityStore.getState().addEvent({
        id: (event.id as string) || crypto.randomUUID(),
        timestamp: (event.timestamp as string) || new Date().toISOString(),
        source: (event.source as string) || 'system',
        type: (event.type as string) || 'info',
        severity: (event.severity as 'info' | 'warning' | 'error') || 'info',
        summary: (event.summary as string) || '',
      })
    }))

    client.connect()

    return () => {
      cleanups.forEach((fn) => fn())
      client.disconnect()
      clientRef.current = null
    }
  }, [setConnectionStatus])
}
