# Central Advisor Session Model v1

**Date**: 2026-05-04
**Phase**: 94D.3 — Central Advisor Session + Interface-Agnostic Communication Bus Correction v1

---

## 1. What the Central Advisor Session Is

The central advisor session is the founder's primary command and intelligence layer. It is not a queue, not a bot, and not a single CLI window. It is the persistent session through which the founder communicates intent, receives intelligence, approves actions, and observes execution — regardless of which interface is currently active.

The advisor session is the EOS brain from the founder's perspective.

---

## 2. Core Responsibilities

| # | Responsibility | Description |
|---|---------------|-------------|
| 1 | Receive founder intent | Accept commands, questions, approvals from any connected interface |
| 2 | Maintain conversational continuity | Session state persists across interface switches and time gaps |
| 3 | Track active work | Know all active work orders, projects, pending approvals, blocked items |
| 4 | Route tasks to execution nodes | Dispatch work to VPS agents, local PC workers, external APIs |
| 5 | Ask questions when context is missing | Surface clarification requests before acting on ambiguity |
| 6 | Surface approvals/interventions/status/errors | Push relevant events to whichever interface is active |
| 7 | Receive results from nodes | Collect completion reports, evidence, errors from execution nodes |
| 8 | Summarize progress | Provide concise updates on request or on significant state changes |
| 9 | Preserve audit trail | Every message, decision, approval logged with timestamps |
| 10 | Support multiple interface projections | Same session accessible from CLI, Discord, mobile, voice, etc. |

---

## 3. What the Advisor Session Is NOT

| It is NOT | Why |
|-----------|-----|
| An approval queue | Approvals are one message type among many |
| A CLI session | CLI is one interface projection |
| A Discord bot | Discord is one interface projection |
| A local terminal | Local terminal is a separate execution node |
| A work order executor | It dispatches and monitors — it does not execute |
| A stateless API | It maintains conversational context and session state |

---

## 4. Session State Model

```
AdvisorSession:
  session_id: str
  founder_id: str
  state: ACTIVE | IDLE | SLEEPING | PAUSED
  active_interfaces: list[InterfaceProjection]
  active_work_orders: list[WorkOrderReference]
  pending_approvals: list[ApprovalRequest]
  pending_questions: list[ClarificationRequest]
  conversation_history: list[MessageEnvelope]
  last_activity: datetime
  created_at: datetime
```

---

## 5. Message Categories the Session Handles

### Founder → Advisor

| Category | Purpose |
|----------|---------|
| INTENT | "I want X to happen" — high-level direction |
| COMMAND | "Do X now" — specific executable instruction |
| APPROVAL_RESPONSE | APPROVE / DENY / MODIFY / DEFER response to a pending approval |
| CLARIFICATION_RESPONSE | Answer to a question the advisor asked |
| STOP | Halt all active work immediately |
| PAUSE | Pause specific work order or all work |
| RESUME | Resume paused work |
| MODIFY_CONSTRAINTS | Change safety rules, scope, or backend for active work |
| SWITCH_INTERFACE | Signal that founder is moving to a different interface |

### Advisor → Founder

| Category | Purpose |
|----------|---------|
| ADVISORY | Proactive intelligence, recommendations, summaries |
| PLAN | Proposed execution plan before starting work |
| QUESTION | "I need clarification on X before proceeding" |
| APPROVAL_REQUEST | "Node X wants to do Y — approve/deny?" |
| STATUS_SUMMARY | "Here's where things stand" |
| RISK_WARNING | "This looks risky because..." |
| RECOMMENDED_ACTION | "I recommend doing X next" |
| MEMORY_CANDIDATE_REVIEW | "This seems worth persisting — confirm?" |

### Node → Advisor

| Category | Purpose |
|----------|---------|
| NODE_HEALTH | Heartbeat, status, resource state |
| WORK_ORDER_CLAIMED | "I've picked up WO-XXX" |
| WORK_ORDER_STATUS | Progress update, phase transition |
| APPROVAL_NEEDED | "I need approval before I can do X" |
| ERROR | Something failed |
| BLOCKED | Cannot proceed without intervention |
| RESULT | Work complete, here's the output |
| EVIDENCE_AVAILABLE | Screenshot, export, file ready for review |
| COMPLETION_REPORT | Final summary of work order execution |

### System → Advisor

| Category | Purpose |
|----------|---------|
| AUDIT_EVENT | Logged state change for governance |
| POLICY_BLOCK | Safety policy prevented an action |
| GOVERNANCE_WARNING | Something is approaching a boundary |
| ROUTING_DECISION | Record of how a message was routed |
| HEARTBEAT | System liveness signal |

---

## 6. Approval Flow (as One Message Type)

Approvals are NOT the architecture. They are one event type flowing through the central session.

```
Node sends: APPROVAL_NEEDED {action: "open_folder", target: "Coaching Frameworks"}
  → Advisor routes to active interface
  → Founder sees: "Local worker wants to open 'Coaching Frameworks' — approve?"
  → Founder responds: APPROVAL_RESPONSE {decision: "APPROVE"}
  → Advisor routes back to node
  → Node continues execution
```

The same flow handles:
- Work order approval gates
- Memory promotion approval
- Risk boundary approval
- Configuration change approval
- Backend switch approval

---

## 7. Continuity Across Interfaces

The advisor session maintains state independent of interface. When the founder switches:

```
CLI session (VPS) → founder walks to phone
  → Session state persists
  → Pending approvals still visible on any connected interface
  → Phone (Termius SSH) connects → same session, same context
  → Founder approves from phone
  → Approval routes to local PC worker
  → Local PC continues
```

No interface is "primary." The session is primary. Interfaces are projections.

---

## 8. Execution Node Relationship

The advisor session does NOT execute work. It:
- Creates and dispatches work orders
- Monitors execution progress
- Relays approvals between founder and nodes
- Escalates errors and blocks
- Collects results

Execution happens on:
- Local PC (GUI computer use, browser automation, manual)
- VPS agents (orchestration, LLM tasks, API calls)
- External services (APIs, webhooks)

---

## 9. Session Persistence

| Layer | Storage |
|-------|---------|
| Message history | Neon DB (append-only, indexed by session_id) |
| Active state | In-memory + periodic checkpoint to Neon |
| Work order tracking | Linked via work_order_id in messages |
| Interface registry | In-memory, updated on connect/disconnect |
| Audit log | Append-only JSONL (local) + Neon (durable) |

---

## 10. Relationship to Existing EOS Components

| Component | Relationship |
|-----------|-------------|
| `cognitive_loop.py` | Advisor session MAY invoke the cognitive loop for complex reasoning |
| `agent_runtime.py` | Advisor session uses agent runtime for LLM-backed responses |
| `local_bridge_client.py` | Transport layer — advisor uses bridge for VPS→local communication |
| `station_bus.py` | Alternative transport — advisor can dispatch via file bus |
| `work_order_contracts.py` | Work orders are one object type the session manages |
| `discord_bot.py` | Discord is one interface projection into the advisor session |
| `local_listener.py` | Local activation events feed into the advisor session |

The advisor session sits ABOVE all of these. It is the coordination layer, not a replacement for any transport.
