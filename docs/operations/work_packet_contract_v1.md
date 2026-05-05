# Work Packet Contract v1

**Phase:** 96.8A / 96.8A.1
**Status:** Active
**Layer:** UMH Substrate — `core/environment_bridge/work_packet.py`

## Adapter Boundary Classification

Work packets are **governed external interaction contracts**. Per the
UMH External Boundary Law, every work packet that targets a local GUI,
browser, or founder confirmation crosses the UMH external boundary and
requires adapter boundaries. Packets carry `required_environment_adapters`
and `required_human_approval_adapters` fields to satisfy this requirement.

## Purpose

The WorkPacket is the atomic unit of work in the Environment Bridge.
Every task dispatched from VPS to local worker is a WorkPacket. Every
packet carries its own governance: approval status, risk level,
allowed/blocked actions, and proof requirements.

## Fields

| Field | Type | Purpose |
|-------|------|---------|
| `packet_id` | str | Unique identifier (e.g., `WP-W0-001-CU-RERUN-001`) |
| `work_order_id` | str | Parent work order |
| `title` | str | Human-readable name |
| `description` | str | What this packet does |
| `action_type` | str | Action category (e.g., `cu_rerun_while_present`) |
| `target_environment` | list[str] | Where to execute (e.g., `local_windows_gui`) |
| `required_adapter_packages` | list[str] | Adapter packages needed |
| `required_tool_mastery_packs` | list[str] | TME packs needed |
| `risk_level` | WorkPacketRiskLevel | `low`, `medium`, `high`, `critical` |
| `approval_status` | WorkPacketStatus | Must be `approved` to execute |
| `founder_confirmation_required` | bool | Whether founder must confirm |
| `allowed_actions` | list[str] | Whitelist of permitted actions |
| `blocked_actions` | list[str] | Actions that MUST NOT occur |
| `expected_outputs` | list[str] | Expected result artifacts |
| `proof_requirements` | list[str] | What must be proven post-execution |
| `timeout_seconds` | int | Max execution time (default 3600) |
| `created_at` | str | ISO timestamp |
| `expires_at` | str | ISO timestamp (empty = no expiry) |
| `status` | WorkPacketStatus | Current lifecycle status |
| `external_interaction_id` | str | Link to ExternalInteraction record |
| `adapter_boundary_required` | bool | Whether adapter boundary enforced (default True) |
| `required_environment_adapters` | list[str] | Environment adapter IDs for GUI/tmux |
| `required_human_approval_adapters` | list[str] | Human approval adapter IDs |
| `notes` | list[str] | Additional context |

## Lifecycle States

```
DRAFT → APPROVED → DISPATCHED → CLAIMED → RUNNING → COMPLETED
                                                   → FAILED
         BLOCKED ←──────────────────────────────────┘
         CANCELLED
         EXPIRED
```

## Execution Rules

- `work_packet_is_executable()` returns true only when:
  - `approval_status == APPROVED`
  - `blocked_actions` is non-empty
- `work_packet_requires_approval()` returns true for HIGH and CRITICAL risk
- `work_packet_blocks_if_unapproved()` gates HIGH/CRITICAL packets that lack approval

## CU Governance

Packets targeting `local_windows_gui` or `local_browser` must include
all 17 CU_REQUIRED_BLOCKED_ACTIONS. The packet validator checks this
before execution. Missing even one blocks the packet.

## Example Packet

See `/opt/OS/data/work_queue/outbox/w0_001_cu_rerun_while_present_packet.json`
for a live example — WP-W0-001-CU-RERUN-001, risk HIGH, approval APPROVED,
7 allowed actions, 17 blocked actions, 9 proof requirements.
