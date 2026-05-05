# Central Command Message Types v1

**Date**: 2026-05-04
**Phase**: 94D.3 — Central Advisor Session + Interface-Agnostic Communication Bus Correction v1

---

## 1. Message Type Registry

All message types are enumerated. No freeform types. New types require registration.

---

## 2. Founder-Originated Messages

Messages sent by the founder to the advisor session or directly to nodes.

### INTENT
**Purpose**: High-level direction. "I want X to happen."
```
payload:
  description: str       — what the founder wants
  scope: str | None      — which project/venture/area
  urgency: str | None    — how soon
  constraints: list[str] — any boundaries
```

### COMMAND
**Purpose**: Specific executable instruction. "Do X now."
```
payload:
  action: str            — what to do
  target: str | None     — what to act on
  parameters: dict       — action-specific parameters
```

### APPROVAL_RESPONSE
**Purpose**: Response to a pending approval request.
```
payload:
  approval_request_id: str   — which request this responds to
  decision: str              — APPROVE | DENY | MODIFY | DEFER
  modifications: dict | None — if MODIFY, what changed
  reason: str | None         — why (optional)
```

### CLARIFICATION_RESPONSE
**Purpose**: Answer to a question the advisor asked.
```
payload:
  question_id: str       — which question this answers
  answer: str            — the response
  additional_context: str | None
```

### STOP
**Purpose**: Halt all active work immediately.
```
payload:
  scope: str             — "all" | work_order_id | node_id
  reason: str | None
```

### PAUSE
**Purpose**: Pause specific work or all work.
```
payload:
  scope: str             — "all" | work_order_id | node_id
  reason: str | None
```

### RESUME
**Purpose**: Resume paused work.
```
payload:
  scope: str             — "all" | work_order_id | node_id
```

### MODIFY_CONSTRAINTS
**Purpose**: Change safety rules, scope, or backend for active work.
```
payload:
  work_order_id: str     — which work order
  changes: dict          — what to change (backend, scope, authority, etc.)
  reason: str
```

### SWITCH_INTERFACE
**Purpose**: Signal that the founder is moving to a different interface.
```
payload:
  from_interface: str    — current interface_id
  to_interface: str      — new interface_id
  transfer_context: bool — whether to push recent messages to new interface
```

---

## 3. Advisor-Originated Messages

Messages the advisor session sends to the founder or to nodes.

### ADVISORY
**Purpose**: Proactive intelligence, recommendations, summaries.
```
payload:
  topic: str
  content: str
  relevance: str         — why this matters now
  suggested_action: str | None
```

### PLAN
**Purpose**: Proposed execution plan before starting work.
```
payload:
  plan_id: str
  work_order_id: str | None
  steps: list[dict]      — ordered steps with descriptions
  estimated_duration: str | None
  risks: list[str]
  requires_approval: bool
```

### QUESTION
**Purpose**: "I need clarification on X before proceeding."
```
payload:
  question_id: str
  question: str
  context: str           — why this question matters
  options: list[str] | None  — suggested answers if applicable
  blocking: bool         — is this blocking work?
```

### APPROVAL_REQUEST
**Purpose**: Node wants to do something that requires founder sign-off.
```
payload:
  approval_request_id: str
  work_order_id: str
  node_id: str
  action_description: str
  action_type: str       — what kind of action (browse, read, export, etc.)
  risk_level: str        — LOW | MEDIUM | HIGH
  context: str           — what the node is doing and why
  timeout_seconds: int | None  — auto-deny after timeout (safety)
```

### STATUS_SUMMARY
**Purpose**: "Here's where things stand."
```
payload:
  summary: str
  active_work_orders: list[dict]
  pending_approvals: int
  blocked_items: int
  completed_since_last: int
```

### RISK_WARNING
**Purpose**: Something looks risky.
```
payload:
  risk_id: str
  description: str
  severity: str          — LOW | MEDIUM | HIGH | CRITICAL
  affected_work_order: str | None
  recommended_action: str
```

### RECOMMENDED_ACTION
**Purpose**: Proactive recommendation.
```
payload:
  recommendation: str
  rationale: str
  priority: str
```

### MEMORY_CANDIDATE_REVIEW
**Purpose**: Something seems worth persisting — confirm?
```
payload:
  candidate_id: str
  content: str
  memory_type: str       — user | feedback | project | reference
  source: str            — where this was learned
  requires_approval: bool
```

---

## 4. Node-Originated Messages

Messages from execution nodes to the advisor session.

### NODE_HEALTH
**Purpose**: Heartbeat and status.
```
payload:
  node_id: str
  status: str            — ONLINE | DEGRADED | OFFLINE | BUSY
  uptime_seconds: int
  active_work_orders: list[str]
  resource_usage: dict | None
```

### WORK_ORDER_CLAIMED
**Purpose**: Node has picked up a work order.
```
payload:
  work_order_id: str
  node_id: str
  estimated_duration: str | None
  execution_backend: str — GUI_COMPUTER_USE | BROWSER_AUTOMATION | API_CONNECTOR | MANUAL_FALLBACK
```

### WORK_ORDER_STATUS
**Purpose**: Progress update.
```
payload:
  work_order_id: str
  node_id: str
  phase: str             — current execution phase
  progress_pct: int | None
  detail: str
  items_completed: int
  items_remaining: int
```

### APPROVAL_NEEDED
**Purpose**: Node cannot proceed without founder approval.
```
payload:
  approval_request_id: str
  work_order_id: str
  node_id: str
  action: str            — what the node wants to do
  target: str            — what it wants to act on
  context: str           — why
  risk_level: str
  blocked_until_approved: bool
```

### ERROR
**Purpose**: Something failed.
```
payload:
  error_id: str
  work_order_id: str | None
  node_id: str
  error_type: str        — RUNTIME | NETWORK | AUTH | POLICY | TIMEOUT | UNKNOWN
  description: str
  recoverable: bool
  suggested_action: str | None
```

### BLOCKED
**Purpose**: Cannot proceed without intervention.
```
payload:
  work_order_id: str
  node_id: str
  reason: str
  blocker_type: str      — APPROVAL | ERROR | RESOURCE | POLICY | MISSING_CONTEXT
  requires: str          — what's needed to unblock
```

### RESULT
**Purpose**: Work complete, here's the output.
```
payload:
  work_order_id: str
  node_id: str
  status: str            — COMPLETE | PARTIAL | FAILED
  result_path: str | None
  summary: str
  items_processed: int
  evidence_count: int
```

### EVIDENCE_AVAILABLE
**Purpose**: Screenshot, export, file ready for review.
```
payload:
  work_order_id: str
  evidence_id: str
  evidence_type: str     — SCREENSHOT | EXPORT | LOG | FILE
  path: str
  size_bytes: int
  description: str
```

### COMPLETION_REPORT
**Purpose**: Final summary of work order execution.
```
payload:
  work_order_id: str
  node_id: str
  status: str
  duration_minutes: int
  actions_taken: int
  approvals_requested: int
  approvals_granted: int
  approvals_denied: int
  errors_encountered: int
  safety_attestation: dict
  result_path: str
```

---

## 5. System-Originated Messages

Messages from the system layer (governance, audit, routing).

### AUDIT_EVENT
```
payload:
  event_id: str
  event_type: str
  description: str
  actor: str
  affected_resource: str | None
```

### POLICY_BLOCK
```
payload:
  policy_id: str
  blocked_action: str
  reason: str
  work_order_id: str | None
  node_id: str | None
```

### GOVERNANCE_WARNING
```
payload:
  warning_id: str
  boundary: str
  current_state: str
  threshold: str
  recommended_action: str
```

### ROUTING_DECISION
```
payload:
  message_id: str
  routed_from: str
  routed_to: str
  transport: str
  reason: str
```

### HEARTBEAT
```
payload:
  source: str
  timestamp: str
  sequence: int
```

---

## 6. Message Type Summary

| Origin | Count | Types |
|--------|-------|-------|
| Founder | 9 | INTENT, COMMAND, APPROVAL_RESPONSE, CLARIFICATION_RESPONSE, STOP, PAUSE, RESUME, MODIFY_CONSTRAINTS, SWITCH_INTERFACE |
| Advisor | 8 | ADVISORY, PLAN, QUESTION, APPROVAL_REQUEST, STATUS_SUMMARY, RISK_WARNING, RECOMMENDED_ACTION, MEMORY_CANDIDATE_REVIEW |
| Node | 9 | NODE_HEALTH, WORK_ORDER_CLAIMED, WORK_ORDER_STATUS, APPROVAL_NEEDED, ERROR, BLOCKED, RESULT, EVIDENCE_AVAILABLE, COMPLETION_REPORT |
| System | 5 | AUDIT_EVENT, POLICY_BLOCK, GOVERNANCE_WARNING, ROUTING_DECISION, HEARTBEAT |
| **Total** | **31** | |
