export type VoiceCommandState =
  | 'idle'
  | 'listening'
  | 'processing'
  | 'transcribed'
  | 'submitting'
  | 'responded'
  | 'error'
  | 'unsupported'

export type VoiceInputMode = 'voice' | 'text' | 'fallback_text'

export interface VoiceTranscript {
  transcript_id: string
  session_id: string
  text: string
  confidence: number
  source: 'browser_speech' | 'typed_text' | 'test_adapter'
  interim: boolean
  final: boolean
  started_at: string
  completed_at: string | null
  error: string | null
}

export interface VoiceCommandRequest {
  session_id: string
  input_text: string
  input_mode: VoiceInputMode
  transcript_id: string | null
  operator_context: Record<string, unknown> | null
  request_preview_only: boolean
  created_at: string
}

export interface VoiceCommandResult {
  request_id: string
  session_id: string
  transcript: VoiceTranscript | null
  dex_response: DexResponse | null
  execution_occurred: boolean
  created_packet_id: string | null
  linked_propagation_plan_id: string | null
  approval_required: boolean
  human_required: boolean
  error: string | null
}

export interface DexResponse {
  session_id: string
  intent: string
  summary: string
  current_state: string | null
  recommended_next_action: string | null
  confidence: number
  safety_state: string
  packet_preview: PacketPreview | null
  topology_preview: TopologyPreview | null
  human_actions: HumanAction[]
  approval_gates: ApprovalGate[]
  propagation_preview: PropagationPreview | null
  execution_occurred: boolean
}

export interface PacketPreview {
  packet_id: string | null
  title: string
  desired_end_state: string
  domain: string | null
  project: string | null
  company: string | null
  product: string | null
  status: string
  risk_class: string
  leverage: number | null
  effectiveness: number | null
  efficiency: number | null
}

export interface TopologyPreview {
  topology_type: string
  lead_role_contract: string | null
  workcells: WorkcellPreview[]
  advisor_branches: string[]
  reconvergence_point: string | null
}

export interface WorkcellPreview {
  role: string
  agent: string | null
  status: string
}

export interface HumanAction {
  action: string
  reason: string
  blocking: boolean
}

export interface ApprovalGate {
  gate_id: string
  description: string
  status: 'pending' | 'approved' | 'rejected'
  required: boolean
}

export interface PropagationPreview {
  affected_nodes: PropagationNode[]
  waves: number
  validation_required: boolean
  approval_required: boolean
  noop_actions: string[]
  blocked_actions: string[]
}

export interface PropagationNode {
  node_id: string
  label: string
  wave: number
  impact: string
}

export interface OperatorSession {
  session_id: string
  created_at: string
  last_activity: string
  turn_count: number
  turns: SessionTurn[]
}

export interface SessionTurn {
  turn_id: string
  input: string
  input_mode: VoiceInputMode
  response: DexResponse | null
  timestamp: string
}
