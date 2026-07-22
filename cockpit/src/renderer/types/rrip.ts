export type RRIPRole = 'operator' | 'dex' | 'system' | 'agent' | 'external'

export type RRIPKind =
  | 'conversation'
  | 'command_result'
  | 'work_report'
  | 'audit_report'
  | 'approval_request'
  | 'error'
  | 'status'
  | 'delegation'

export interface RRIPRouting {
  cognitive_mode?: 'fast' | 'deep' | 'council' | 'command' | 'delegation' | 'reporting' | 'approval_review'
  runtime?: 'dex' | 'fast_model' | 'deep_model' | 'council' | 'claude_code' | 'codex' | 'hermes' | 'shell' | 'system'
  context_mode?: string
  routed_by?: string
  confidence?: number
}

export interface RRIPProvenance {
  node?: string
  harness?: string
  session?: string
  phase?: string
  pr?: number | string
  task?: string
}

export interface RRIPAttachment {
  path: string
  filename: string
}

export interface RRIPSuggestedAction {
  label: string
  action: string
  // Optional to stay assignable from chatStore's SuggestedAction — newer rails
  // send a flat `target` instead of a `payload` (e.g. objective-plan navigate).
  payload?: Record<string, unknown>
  target?: string
}

export interface RRIPApprovalData {
  approval_id: string
  description: string
  risk_level: string
  agent: string
  status: string
  created_at: string
}

export interface RRIPMessage {
  id: string
  role: RRIPRole
  kind: RRIPKind
  content: string
  timestamp: string
  title?: string
  source?: 'text' | 'voice'
  origin_channel?: string
  intent?: string
  provenance?: RRIPProvenance
  attachment?: RRIPAttachment
  suggested_actions?: RRIPSuggestedAction[]
  approval_data?: RRIPApprovalData
  routing?: RRIPRouting
  metadata?: Record<string, unknown>
}
