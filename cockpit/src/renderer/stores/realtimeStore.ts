import { create } from 'zustand'

export interface OrganismEvent {
  event_id: string
  domain: string
  event_type: string
  source: string
  priority: string
  data: Record<string, unknown>
  timestamp: number
  correlation_id: string | null
}

export type RealtimeStatus = 'connected' | 'connecting' | 'disconnected' | 'fallback'

export type EventDomainFilter =
  | 'all'
  | 'governance'
  | 'execution'
  | 'runtime'
  | 'bottleneck'
  | 'leverage'
  | 'mutation'
  | 'supervisor'
  | 'workcell'
  | 'observability'
  | 'objective'
  | 'filesystem'
  | 'docker'
  | 'tmux'
  | 'projection'
  | 'recursion'
  | 'memory'

const MAX_EVENTS = 500
const MAX_EVENT_IDS = 1000

interface RealtimeState {
  status: RealtimeStatus
  events: OrganismEvent[]
  lastEventTimestamp: number | null
  lastPulseTimestamp: number | null
  eventCount: number
  reconnectCount: number
  eventsPerMinute: number
  domainFilter: EventDomainFilter
  seenEventIds: Set<string>

  cpuPercent: number
  memoryPercent: number
  diskPercent: number
  containers: Array<{ name: string; status: string }>

  setStatus: (status: RealtimeStatus) => void
  pushEvents: (events: OrganismEvent[]) => void
  pushPulse: (pulse: {
    cpu_percent: number
    memory_percent: number
    disk_percent: number
    containers: Array<{ name: string; status: string }>
  }) => void
  incrementReconnect: () => void
  setDomainFilter: (filter: EventDomainFilter) => void
  clearEvents: () => void
}

export const useRealtimeStore = create<RealtimeState>((set, get) => ({
  status: 'disconnected',
  events: [],
  lastEventTimestamp: null,
  lastPulseTimestamp: null,
  eventCount: 0,
  reconnectCount: 0,
  eventsPerMinute: 0,
  domainFilter: 'all',
  seenEventIds: new Set<string>(),

  cpuPercent: 0,
  memoryPercent: 0,
  diskPercent: 0,
  containers: [],

  setStatus: (status) => set({ status }),

  pushEvents: (newEvents) => {
    if (newEvents.length === 0) return
    const state = get()
    const seen = new Set(state.seenEventIds)
    const deduped = newEvents.filter((e) => {
      if (seen.has(e.event_id)) return false
      seen.add(e.event_id)
      return true
    })
    if (deduped.length === 0) return

    if (seen.size > MAX_EVENT_IDS) {
      const arr = Array.from(seen)
      const trimmed = new Set(arr.slice(arr.length - MAX_EVENT_IDS))
      set({ seenEventIds: trimmed })
    } else {
      set({ seenEventIds: seen })
    }

    const merged = [...deduped, ...state.events].slice(0, MAX_EVENTS)
    const latest = deduped.reduce((max, e) => Math.max(max, e.timestamp), state.lastEventTimestamp ?? 0)
    const newCount = state.eventCount + deduped.length

    const cutoff = Date.now() / 1000 - 60
    const recentCount = merged.filter((e) => e.timestamp > cutoff).length

    set({
      events: merged,
      lastEventTimestamp: latest,
      eventCount: newCount,
      eventsPerMinute: recentCount,
    })
  },

  pushPulse: (pulse) => {
    set({
      cpuPercent: pulse.cpu_percent,
      memoryPercent: pulse.memory_percent,
      diskPercent: pulse.disk_percent,
      containers: pulse.containers,
      lastPulseTimestamp: Date.now(),
    })
  },

  incrementReconnect: () => set((s) => ({ reconnectCount: s.reconnectCount + 1 })),
  setDomainFilter: (filter) => set({ domainFilter: filter }),
  clearEvents: () => set({ events: [], eventCount: 0, seenEventIds: new Set() }),
}))
