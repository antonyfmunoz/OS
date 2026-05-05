# Existing Bridge Work Order Contract v1

**Date**: 2026-05-04
**Phase**: 93R.1 — Bind Existing Local Bridge to Work Order Contract v1
**Purpose**: Formal work-order schema compatible with the existing local bridge, station bus, and control command patterns.

---

## Design Principles

1. **Compatible, not competing.** This contract sits alongside SafeAction and ControlCommand. It does not replace them. WorkOrders are higher-level orchestration envelopes that may decompose into SafeActions or bridge payloads at dispatch time.
2. **JSON-serializable.** Transport-agnostic. Can flow through StationBus file bus, HTTP local bridge, or future WebSocket.
3. **Read-only by default.** Every work order declares `authority_mode`. No work order may mutate external state without explicit `APPROVAL_REQUIRED` and founder sign-off.
4. **Auditable.** Every status transition is timestamped. Every blocked action is logged. Every result includes a safety confirmation.

---

## Work Order Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `work_order_id` | str | YES | Unique identifier. Format: `wo_{uuid12}` |
| `created_by_node` | str | YES | Node that created the work order (e.g., `vps-orchestrator`) |
| `assigned_to_node` | str | YES | Node that should execute (e.g., `antony-workstation`) |
| `task_type` | WorkOrderTaskType | YES | Enum — see Task Types below |
| `objective` | str | YES | Human-readable description of what this work order accomplishes |
| `source_targets` | list[str] | YES | URLs, file paths, folder names, or platform identifiers to access |
| `allowed_actions` | list[str] | YES | Explicit list of permitted actions during execution |
| `blocked_actions` | list[str] | YES | Explicit list of forbidden actions — safety boundary |
| `required_approvals` | list[str] | NO | Actions that need founder sign-off before execution |
| `authority_mode` | AuthorityMode | YES | READ_ONLY / APPROVAL_REQUIRED / BLOCKED / FUTURE_ONLY |
| `sensitivity_level` | SensitivityLevel | YES | PUBLIC / PRIVATE / SENSITIVE / MIXED |
| `evidence_required` | bool | YES | Whether screenshots/logs must accompany the result |
| `expected_outputs` | list[str] | YES | What the result should contain |
| `result_schema` | str | NO | Reference to the result schema document/version |
| `timeout_minutes` | int | YES | Maximum allowed execution time |
| `status` | WorkOrderStatus | YES | Current lifecycle state — see Statuses below |
| `created_at` | str (ISO 8601) | YES | When the work order was created |
| `claimed_at` | str (ISO 8601) | NO | When the local worker claimed the order |
| `completed_at` | str (ISO 8601) | NO | When execution finished |
| `result_path` | str | NO | File path or URL where the result is stored |
| `audit_notes` | list[str] | NO | Timestamped log of status transitions and decisions |

---

## Work Order Statuses

| Status | Meaning |
|--------|---------|
| `CREATED` | Work order defined but not yet queued |
| `QUEUED` | Placed in outbox / queue for local worker |
| `SENT_TO_LOCAL` | Dispatched to local machine (health check passed) |
| `CLAIMED_BY_LOCAL` | Local worker acknowledged receipt |
| `IN_PROGRESS` | Local worker is executing |
| `WAITING_FOR_USER_APPROVAL` | Execution paused — needs founder approval for a specific action |
| `COMPLETE` | All expected outputs produced, safety confirmed |
| `PARTIAL` | Some outputs produced, others blocked or failed |
| `BLOCKED` | Cannot proceed — external dependency or policy violation |
| `FAILED` | Execution error, no usable outputs |
| `CANCELLED` | Manually cancelled by founder or VPS orchestrator |

### Status Transitions (allowed)

```
CREATED → QUEUED → SENT_TO_LOCAL → CLAIMED_BY_LOCAL → IN_PROGRESS
IN_PROGRESS → WAITING_FOR_USER_APPROVAL → IN_PROGRESS (after approval)
IN_PROGRESS → COMPLETE | PARTIAL | BLOCKED | FAILED
Any status → CANCELLED (founder override)
```

---

## Task Types

| Task Type | Description | Default Authority |
|-----------|-------------|-------------------|
| `LOCAL_SOURCE_INVENTORY` | List files/folders on local machine by type and location | READ_ONLY |
| `GOOGLE_WORKSPACE_DISCOVERY` | Navigate Google Drive, list docs/folders/sheets without reading content | READ_ONLY |
| `GOOGLE_DOCS_READ_EXPORT` | Open and read/export specific Google Docs content | APPROVAL_REQUIRED |
| `AI_CHAT_EXPORT` | Export conversation history from ChatGPT, Claude, Gemini | APPROVAL_REQUIRED |
| `CUSTOM_GPT_CONFIG_CAPTURE` | Read Custom GPT configuration and instructions | APPROVAL_REQUIRED |
| `OBSIDIAN_VAULT_READ` | Read Obsidian vault structure and note content | READ_ONLY |
| `BROWSER_READ_ONLY_NAVIGATION` | Navigate to URLs in browser, read page content | READ_ONLY |
| `SCREENSHOT_EVIDENCE_CAPTURE` | Take screenshots as evidence of what was seen | APPROVAL_REQUIRED |
| `RESULT_WRITEBACK` | Write results back to VPS via bridge | READ_ONLY |

---

## Authority Modes

| Mode | Meaning | What local worker may do |
|------|---------|------------------------|
| `READ_ONLY` | No modification of any external system | Navigate, read, list, extract text. No writes, no clicks on buttons that change state. |
| `APPROVAL_REQUIRED` | Must pause and get founder approval before each action | Present the action to founder, wait for explicit "yes", then execute. Log the approval. |
| `BLOCKED` | This action type is not permitted in this work order | Worker must skip and log as blocked. Never attempt. |
| `FUTURE_ONLY` | Planned for a future phase, not executable now | Worker must skip and log as future_only. Never attempt. |

---

## Sensitivity Levels

| Level | Meaning | Handling |
|-------|---------|---------|
| `PUBLIC` | Content already visible to the world | Standard handling. No redaction needed. |
| `PRIVATE` | Personal/business data not publicly visible | Do not log full content in audit notes. Summarize. |
| `SENSITIVE` | Contains credentials, financials, personal details | Never capture passwords/tokens. Redact in results. Flag for founder review. |
| `MIXED` | Contains both public and private data | Treat as PRIVATE for handling rules. |

---

## Blocked Actions (Universal — applies to ALL work orders)

These actions are NEVER permitted in any ingestion work order:

| # | Blocked Action | Why |
|---|---------------|-----|
| 1 | Edit/modify documents | Read-only ingestion |
| 2 | Delete files or documents | Destructive |
| 3 | Change sharing/permissions | Modifies access state |
| 4 | Send emails | Outbound communication |
| 5 | Send DMs | Outbound communication |
| 6 | Post content (any platform) | Public-facing action |
| 7 | Change account settings | Account state modification |
| 8 | Capture passwords/tokens/API keys | Credential capture forbidden |
| 9 | Process payments | Financial action |
| 10 | Subscribe/unsubscribe | Account state modification |
| 11 | Click "buy" or "purchase" | Financial action |
| 12 | Install software | System modification |
| 13 | Modify system settings | System modification |
| 14 | Autonomous social actions | Requires founder approval |
| 15 | Promote memory without governance | Memory governance required |
| 16 | Run arbitrary shell commands | Safety boundary violation |

---

## Transport Mapping

### Via Local Bridge (HTTP)

```json
POST http://100.74.199.102:8766/work-order
{
    "work_order_id": "wo_abc123def456",
    "task_type": "GOOGLE_WORKSPACE_DISCOVERY",
    "objective": "List all Google Drive folders and documents",
    "source_targets": ["Google Drive root"],
    "allowed_actions": ["navigate", "list", "read_metadata"],
    "blocked_actions": ["edit", "delete", "share"],
    "authority_mode": "READ_ONLY",
    "sensitivity_level": "MIXED",
    ...
}
```

### Via Station Bus (File)

```
eos_ai/.substrate_station/antony-workstation.outbox.json
[
    {
        "type": "work_order",
        "payload": { ... work order fields ... }
    }
]
```

### Via Control Bridge (Command Envelope)

```python
ControlCommand(
    action="execute_work_order",
    payload={"work_order": { ... work order fields ... }},
    issued_by="vps-orchestrator",
    node_id="antony-workstation",
)
```

All three transports are viable. The binding plan (Part 2) determines which to use.

---

## Result Contract

Every completed work order must produce a result containing:

| Field | Required |
|-------|----------|
| `work_order_id` | YES — links result to work order |
| `executing_node` | YES — which node ran it |
| `execution_start` | YES |
| `execution_end` | YES |
| `status` | YES — COMPLETE / PARTIAL / FAILED |
| `sources_accessed` | YES — what was actually accessed |
| `evidence_paths` | If evidence_required=True |
| `safety_confirmation` | YES — explicit attestation |

Full result schema: `local_google_workspace_ingestion_result_schema_v1.md`
