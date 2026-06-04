# LyfeOS AI Permissions & Approval Model

**Phase:** 14.6B-LyfeOS
**Artifact:** 23 of 30
**operator_approved:** false
**allows_implementation:** false
**Date:** 2026-06-03

---

## Purpose

Documents the current state (and absence) of an AI permissions/approval model in LyfeOS, establishes the professional gap, and proposes a tiered permission architecture for production readiness.

---

## Current State

**Provenance:** INFERRED_PROFESSIONAL_GAP

### No Explicit Permission/Approval Model Exists

The current LyfeOS AI companion implementation has **no explicit permission or approval model**:

- The AI companion can create missions (`batch_create_missions`) without user confirmation
- The AI companion can create vision goals (`create_vision_goal`) without user confirmation
- The AI companion can uncomplete missions (`uncomplete_mission`) without user confirmation
- No audit trail of AI-initiated actions visible to the user
- No mechanism to review and approve AI actions before execution
- No mechanism to undo AI actions after execution (beyond manual deletion)
- No distinction between "AI suggested" and "user confirmed" data

### Implicit Trust Model

The current implementation operates on an implicit trust model:

1. User sends a message to the AI companion
2. AI companion decides to use a tool based on conversation context
3. Tool executes immediately with no confirmation step
4. Result is displayed in the chat stream
5. No audit record persists beyond the conversation

This is appropriate for a single-user MVP but insufficient for production.

---

## Why This Gap Matters

**Provenance:** SYNTHESIZED_CANON

| Risk | Impact | Example |
|------|--------|---------|
| Unintended data creation | User's mission list polluted with unwanted items | AI misinterprets "I should probably do X" as a request to create mission X |
| Unintended data modification | Completed mission reverted without clear user intent | AI uncompletes a mission based on ambiguous context |
| Bulk data damage | Many missions created at once with no easy undo | batch_create_missions generates 20 missions from a casual brainstorming conversation |
| No accountability trail | Cannot determine which actions were AI-initiated vs. user-initiated | User sees data they don't remember creating |
| Trust erosion | User loses confidence in AI companion if it acts without permission | Repeated unwanted actions lead to disabling AI features |

---

## Proposed Permission Tiers

**Provenance:** INFERRED_PROFESSIONAL_GAP

### Tier 1: Auto-Approved (No Confirmation Required)

Actions that are read-only or have zero data impact:

| Action | Justification |
|--------|---------------|
| `web_search` | Read-only, no data mutation |
| `read_webpage` | Read-only, no data mutation |
| `lookup_knowledge_base` | Read-only, no data mutation |
| `navigate_to_page` | Client-side navigation only |
| `generate_affirmation` | Generates text, no data persistence |

### Tier 2: Notify-User (Execute + Show Confirmation)

Actions that create data but are easily reversible:

| Action | Notification Style |
|--------|-------------------|
| `create_vision_goal` | Show created goal in chat with "Undo" button |
| `batch_create_missions` | Show list of created missions with "Undo All" button |
| `update_daily_log` | Show changed fields with "Revert" option |
| `toggle_widget` | Show change with "Undo" option |

### Tier 3: Require-Approval (Confirm Before Execution)

Actions that modify existing data or touch sensitive areas:

| Action | Approval UX |
|--------|-------------|
| `uncomplete_mission` | "Are you sure you want to mark [mission] as incomplete?" confirmation dialog |
| `update_profile` | Show proposed changes, require explicit "Apply" tap |
| Bulk operations (>5 items) | Always require explicit confirmation regardless of tier |
| Access to health/financial profile data for context | Consent banner on first access per session |

### Tier 4: Operator-Only (Never AI-Initiated)

Actions reserved for direct user interaction, never initiated by AI:

| Action | Reason |
|--------|--------|
| Delete mission/goal | Destructive, irreversible |
| Delete conversation | Destructive, irreversible |
| Modify auth settings | Security-critical |
| Export data | Privacy-critical |
| Integration connect/disconnect | OAuth flow requires direct user action |

---

## Rollback Requirements

**Provenance:** INFERRED_PROFESSIONAL_GAP

### Per-Action Rollback

| Action | Rollback Mechanism |
|--------|-------------------|
| `create_vision_goal` | Soft delete the created goal |
| `batch_create_missions` | Soft delete all missions in the batch (track batch_id) |
| `uncomplete_mission` | Re-mark as completed, restore XP |
| `update_profile` | Store previous values, revert on undo |
| `update_daily_log` | Store previous values, revert on undo |
| `toggle_widget` | Toggle back to previous state |

### Batch Rollback

- Every AI action should be tagged with a `batch_id` or `action_id`
- Undo operation targets the batch, not individual items
- Undo window: configurable (e.g., 30 seconds, 5 minutes, or until next user message)

---

## Audit Trail Requirements

**Provenance:** INFERRED_PROFESSIONAL_GAP

### Minimum Audit Record Per AI Action

```json
{
  "action_id": "uuid",
  "user_id": "integer",
  "tool_name": "string",
  "parameters": "object",
  "result": "object",
  "conversation_id": "integer",
  "message_id": "integer",
  "model_used": "haiku|sonnet",
  "tier": "auto_approved|notify_user|require_approval",
  "user_approved": "boolean|null",
  "executed_at": "timestamp",
  "rolled_back_at": "timestamp|null",
  "rolled_back_by": "user|system|timeout"
}
```

### User-Facing Audit View

- Accessible from Settings or Profile page
- Shows all AI-initiated actions with timestamps
- Filterable by action type, date range, and status
- Each entry shows: action, result, whether it was approved/auto, and undo option

---

## UMH Integration Implications

**Provenance:** UMH_INTEGRATION_DEPENDENT_GAP

When UMH integration activates:

1. **Permission tiers map to UMH risk classes**: AUTO_APPROVED = READ_ONLY, NOTIFY_USER = EXTERNAL_COMMUNICATION, REQUIRE_APPROVAL = DATA_MUTATION
2. **UMH governance engine enforces**: LyfeOS UI renders approval dialogs, UMH backend enforces the gate
3. **Audit trail feeds UMH outcome pipeline**: Every AI action produces an `OutcomeEnvelope` that flows through `LyfeOSOutcomeReceiver`
4. **Cross-projection consistency**: Permission model should be consistent across LyfeOS, CreatorOS, EntrepreneurOS

---

## Open Questions

| ID | Question | Classification |
|----|----------|----------------|
| PERM-001 | Should permission tiers be user-configurable (e.g., power users can set all to auto-approve)? | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| PERM-002 | What is the undo window duration? Fixed or configurable? | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| PERM-003 | Should the audit trail be stored in a new LyfeOS table or in the UMH outcomes table? | UMH_INTEGRATION_DEPENDENT_GAP |
| PERM-004 | Should there be rate limits on AI-initiated data creation (e.g., max 10 missions per conversation)? | INFERRED_PROFESSIONAL_GAP |
| PERM-005 | Should AI actions during onboarding have different permission rules (more permissive for setup missions)? | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
