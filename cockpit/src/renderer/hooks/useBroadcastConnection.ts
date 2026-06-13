import { useEffect } from 'react'
import { BroadcastWsClient } from '../api/broadcast-ws'
import { useBroadcastStore } from '../stores/broadcastStore'
import type { BroadcastState } from '../stores/broadcastStore'

let _client: BroadcastWsClient | null = null

export function getBroadcastClient(): BroadcastWsClient | null {
  return _client
}

export function useBroadcastConnection(): void {
  const setConnected = useBroadcastStore((s) => s.setConnected)
  const setBroadcastState = useBroadcastStore((s) => s.setBroadcastState)
  const setHealth = useBroadcastStore((s) => s.setHealth)
  const setPid = useBroadcastStore((s) => s.setPid)
  const setConfig = useBroadcastStore((s) => s.setConfig)
  const reset = useBroadcastStore((s) => s.reset)

  useEffect(() => {
    if (!_client) {
      _client = new BroadcastWsClient()
    }
    const client = _client

    const unsub = client.on((pulse) => {
      setConnected(true)
      setBroadcastState(pulse.state as BroadcastState)
      setPid(pulse.pid)
      setConfig(pulse.config)

      const health = pulse.latest_health ?? pulse.health
      if (health) {
        setHealth(health)
      }
    })

    client.connect()

    return () => {
      unsub()
      client.disconnect()
      _client = null
      reset()
    }
  }, [])
}
