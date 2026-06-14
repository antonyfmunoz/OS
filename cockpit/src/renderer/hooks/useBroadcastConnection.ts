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
  const setComposite = useBroadcastStore((s) => s.setComposite)
  const setActiveSceneId = useBroadcastStore((s) => s.setActiveSceneId)
  const setScenes = useBroadcastStore((s) => s.setScenes)
  const setSources = useBroadcastStore((s) => s.setSources)
  const setActiveNode = useBroadcastStore((s) => s.setActiveNode)
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

      const p = pulse as Record<string, unknown>
      setComposite(Boolean(p.composite))
      setActiveSceneId((p.active_scene_id as string) ?? null)
      setScenes((p.scenes as Array<{ scene_id: string; name: string }>) ?? [])
      setSources((p.sources as Array<{ source_id: string; source_type: string }>) ?? [])
      if (typeof p.active_node === 'string') {
        setActiveNode(p.active_node)
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
