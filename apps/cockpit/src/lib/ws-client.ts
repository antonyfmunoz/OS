/**
 * WebSocket client that connects to the UMH View socket endpoint
 * and dispatches ViewFrame events to the cockpit store.
 *
 * Import this module from App.tsx to activate the connection.
 * The connection auto-reconnects on close (3s delay, handled by CockpitSocket).
 */

import { CockpitSocket } from './websocket.ts'
import { useCockpitStore } from '../stores/cockpitStore.ts'
import type { TraceEvent } from '../types/domain.ts'

interface ViewFrame {
  frame_id: string
  timestamp: string
  event_type: string
  stage: number
  data: Record<string, unknown>
  trace_id?: string | null
  signal_id?: string | null
  integration_id?: string | null
}

const STAGE_LABELS: Record<number, string> = {
  1: 'signal',
  2: 'governance',
  3: 'work_packet',
  4: 'execution',
  5: 'proof',
  6: 'outcome',
  7: 'trace',
  8: 'memory_candidate',
  9: 'memory_promotion',
  10: 'resume_state',
}

function viewFrameToTrace(frame: ViewFrame): TraceEvent {
  const stageLabel = STAGE_LABELS[frame.stage] ?? `stage_${frame.stage}`
  const approved = frame.data.approved as boolean | undefined
  const success = frame.data.success as boolean | undefined

  let status: TraceEvent['status'] = 'completed'
  if (frame.event_type === 'signal') status = 'running'
  else if (approved === false) status = 'failed'
  else if (success === false) status = 'failed'

  const action = summarizeAction(frame)
  const durationMs = (frame.data.duration_ms as number) ?? undefined

  return {
    id: frame.frame_id,
    timestamp: frame.timestamp,
    agent: stageLabel,
    action,
    status,
    durationMs,
    detail: frame.trace_id ?? undefined,
  }
}

function summarizeAction(frame: ViewFrame): string {
  switch (frame.event_type) {
    case 'signal': {
      const content = frame.data.content as string | undefined
      return content ? `signal: ${content}` : 'signal received'
    }
    case 'governance': {
      const decision = frame.data.decision as string | undefined
      return decision ? `governance: ${decision}` : 'governance evaluated'
    }
    case 'execution': {
      const adapter = frame.data.adapter_name as string | undefined
      return adapter ? `execute via ${adapter}` : 'execution'
    }
    case 'proof':
      return `proof: ${(frame.data.status as string) ?? 'generated'}`
    case 'outcome':
      return `outcome: ${(frame.data.outcome_type as string) ?? 'classified'}`
    case 'trace':
      return 'trace stored'
    case 'memory_candidate':
      return 'memory candidate generated'
    case 'memory_promotion':
      return 'memory promoted'
    default:
      return frame.event_type
  }
}

function handleMessage(_type: string, data: unknown): void {
  const store = useCockpitStore.getState()
  const frame = data as ViewFrame
  if (!frame?.frame_id) return

  const trace = viewFrameToTrace(frame)
  store.addTrace(trace)
}

function handleStatus(connected: boolean): void {
  useCockpitStore.getState().setWsConnected(connected)
}

export const socket = new CockpitSocket(handleMessage, handleStatus)

export function connectWebSocket(): void {
  socket.connect()
}

export function disconnectWebSocket(): void {
  socket.disconnect()
}
