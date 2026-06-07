import type { ChatMessage } from '../stores/chatStore'
import type { RRIPMessage, RRIPRole, RRIPKind } from '../types/rrip'

const COMMAND_INTENTS = new Set([
  'status_query',
  'command_center_query',
  'council',
  'cc_send',
  'cc_capture',
  'decompose_intent',
  'cockpit_navigation',
  'resume_query',
  'action',
  'work_packet_draft',
  'packet_control',
  'mode_switch',
  'blocked_query',
  'agent_query',
])

function inferRole(msg: ChatMessage): RRIPRole {
  if (msg.role) return msg.role as RRIPRole
  if (msg.sender === 'operator') return 'operator'
  if (msg.intent === 'report') return 'system'
  if (msg.sender === 'system') return 'system'
  return 'dex'
}

function inferKind(msg: ChatMessage): RRIPKind {
  if (msg.kind) return msg.kind as RRIPKind
  if (msg.intent === 'report') return 'work_report'
  if (msg.intent && COMMAND_INTENTS.has(msg.intent)) return 'command_result'
  return 'conversation'
}

export function normalizeLegacyMessage(msg: ChatMessage): RRIPMessage {
  return {
    id: msg.id,
    role: inferRole(msg),
    kind: inferKind(msg),
    content: msg.content,
    timestamp: msg.timestamp,
    title: msg.title,
    source: msg.source,
    origin_channel: msg.origin_channel,
    intent: msg.intent,
    provenance: msg.provenance,
    attachment: msg.attachment,
    suggested_actions: msg.suggested_actions,
    routing: msg.routing as RRIPMessage['routing'],
    metadata: msg.metadata,
  }
}
