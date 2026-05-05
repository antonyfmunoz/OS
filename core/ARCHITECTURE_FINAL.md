# EOS AI Operating System — Final Architecture

**Status:** consolidation pass, 2026-04-10
**Purpose:** Single source of truth for the unified EOS AI OS after the
"final system pass". Every subsystem listed here has one authoritative
implementation. Nothing in this doc is aspirational — if it isn't in the
code, it isn't in this doc.

---

## 1. Principles

1. **One harness, one execution path.** Every agent call — whether from a
   workflow, a persistent agent, or the Discord gateway — flows through
   `core.agent_harness.AgentHarness.run()`. No bypasses.
2. **Graph-aware permissions.** Capability + risk is evaluated against the
   live codebase graph before any side-effect. Blast radius decides approval.
3. **Everything is logged, everything is replayable.** Every workflow run,
   every action, every agent tick is a JSONL row. Observability reads logs,
   not runtime state.
4. **Optimizer closes the loop.** Failures become improvement proposals
   become action-system-approved edits. The OS *modifies itself*, under the
   same approval gate as any other change.
5. **Never block on the side-channel.** Memory writes, Neon syncs, and
   agent-memory mirrors are fire-and-forget. The execution path never
   waits on them.

---

## 2. Layered architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  L6  CONTROL PLANE              scripts/orchestrator.py          │
│      (scheduler + events + persistent agents + retry)            │
├──────────────────────────────────────────────────────────────────┤
│  L5  FEEDBACK / OPTIMIZER       core/optimizer.py                │
│      (reads logs → proposes improvements → actions under gate)   │
├──────────────────────────────────────────────────────────────────┤
│  L4  PERSISTENT AGENTS          core/persistent_agents.py        │
│      (Observer, Healer, Librarian — stateful, long-running)      │
├──────────────────────────────────────────────────────────────────┤
│  L3  WORKFLOW ENGINE            scripts/workflow_engine.py       │
│      (goal → DAG → execute → log)                                │
├──────────────────────────────────────────────────────────────────┤
│  L2  AGENT HARNESS              core/agent_harness.py            │
│      (tools + memory + graph + capabilities + model routing)     │
├──────────────────────────────────────────────────────────────────┤
│  L1  ACTION SYSTEM              scripts/action_system.py         │
│      (propose → assess → risk → approve → execute → log)         │
├──────────────────────────────────────────────────────────────────┤
│  L0  SUBSTRATE                  eos_ai/*  +  data/codebase_graph │
│      (model router, memory, graph, palace, summaries)            │
└──────────────────────────────────────────────────────────────────┘

Cross-cutting:
  core/capability.py          — capability levels + permission matrix
  core/observability.py       — read-only view over logs + state files
  core/execution_contract.py  — per-message pipeline (user → response)
  scripts/eos_os.py           — unified operator CLI
```

---

## 3. Component inventory

| Layer | Component | File | Status after this pass |
|-------|-----------|------|------------------------|
| L0 | Codebase graph | `data/codebase_graph.json` + `scripts/query_graph.py` | existing — unchanged |
| L0 | Memory palace | `10_Wiki/palace/` + `data/palace.json` | existing — unchanged |
| L0 | Memory | `eos_ai/memory.py` (AgentMemory + ConversationMemory) | existing — harness wraps |
| L0 | Model router | `eos_ai/model_router.py` (`call_with_fallback`) | existing — harness uses |
| L1 | Action system | `scripts/action_system.py` | existing — capability gate added |
| L2 | **Agent harness** | `core/agent_harness.py` | **NEW — this pass** |
| L2 | **Capability/permissions** | `core/capability.py` | **NEW — this pass** |
| L3 | Workflow engine | `scripts/workflow_engine.py` | existing — routes through harness |
| L4 | **Persistent agents** | `core/persistent_agents.py` | **NEW — this pass** |
| L5 | **Optimizer** | `core/optimizer.py` | **NEW — this pass** |
| L6 | Orchestrator | `scripts/orchestrator.py` | existing — manages persistent agents too |
| ✕  | **Observability** | `core/observability.py` | **NEW — this pass** |
| ✕  | Execution contract | `core/execution_contract.py` | existing — unchanged |
| ✕  | **Operator CLI** | `scripts/eos_os.py` | **NEW — this pass** |

---

## 4. Legacy components (kept, fenced, not extended)

These exist and are working but are **not** part of the unified path. They
stay because removing them would break live services. The harness does not
delegate into them, and no new code should either.

| Component | File | Why kept |
|-----------|------|----------|
| Old workflow engine | `eos_ai/workflow_engine.py` | In use by discord_bot intent handler — skill-sequence style |
| Old orchestrator | `eos_ai/orchestrator.py` | 6am cron + morning cycle — production scheduler |
| `core/orchestrator/*` | loop/pipeline/handlers/… | Signal-driven pipeline; different concern (signals not jobs) |
| `core/action_system/*` | control_plane/policy/validator/… | Next-gen control plane for actions — experimental, not wired yet |

**Rule:** when any of these needs extension, the answer is *route through
`AgentHarness`*, not grow the legacy code.

---

## 5. Data surfaces

| Path | Writer | Reader | Format |
|------|--------|--------|--------|
| `data/workflow_log.jsonl` | `WorkflowEngine._emit` | Optimizer, Observability | JSONL |
| `data/workflow_state/<wf_id>.json` | `WorkflowEngine._save_state` | Observability, CLI `show` | JSON |
| `data/orchestrator_log.jsonl` | `ActivityLog.emit` | Optimizer, Observability | JSONL |
| `data/orchestrator_state.json` | `Orchestrator.save_state` | Observability, CLI `status` | JSON |
| `data/action_log.jsonl` | `ActionSystem._emit_log` | Optimizer, Observability | JSONL |
| `data/action_snapshots/<id>/` | `ActionSystem._snapshot` | Rollback | file tree |
| `data/agent_state/<agent>.json` | `PersistentAgent._save_state` | Agent itself, Observability | JSON (NEW) |
| `data/optimizer_proposals.jsonl` | `Optimizer.propose` | Operator review | JSONL (NEW) |

---

## 6. Safety model

### Capability levels (`core/capability.py`)

| Level | Meaning | Examples |
|-------|---------|----------|
| `READ` | Graph queries, memory reads, summaries | `query_graph`, `semantic_search` |
| `WRITE` | New files, memory writes, logs | `write_file` (new), `AgentMemory.log` |
| `EXECUTE` | Running scripts, commands, shell | `run_script`, `run_command` |
| `CRITICAL` | Edits to critical hubs, deletes, infra | `edit_file` on hub, `delete_file` |

### Risk tiers (inherited from `ActionSystem`)

| Tier | Default gate | Override |
|------|--------------|----------|
| `NONE` | auto | — |
| `LOW` | auto | — |
| `MEDIUM` | auto | `require_approval_above=LOW` |
| `HIGH` | **approval required** | `approve=True` or harness policy |
| `CRITICAL` | **approval + reason** | explicit human ack |

### Enforcement

1. Harness asks CapabilityEnforcer before dispatching.
2. Enforcer maps (agent, step-or-action) → required level.
3. If agent lacks level → `PermissionError`, logged, step marked FAILED.
4. ActionSystem still runs its own risk assessment — defense in depth.

---

## 7. Feedback loop

```
    ┌──────────────┐
    │ WorkflowRun  │ writes
    └──────┬───────┘
           │
           ▼
    data/workflow_log.jsonl
    data/action_log.jsonl
           │
           │ reads
           ▼
    ┌──────────────┐
    │  Optimizer   │ (scheduled job, every 6h)
    │  analyze()   │
    └──────┬───────┘
           │
           ▼
    Proposal records
    data/optimizer_proposals.jsonl
           │
           │ propose()
           ▼
    ┌──────────────┐
    │ ActionSystem │  (same gate as any other action)
    └──────┬───────┘
           │
           ▼
    Approved edits applied to:
      - workflow builders
      - orchestrator job definitions
      - agent permissions

    Next WorkflowRun runs the improved version.
```

The optimizer is a **read-first, propose-second, act-last** component.
It never applies changes without going through the same approval gate
the rest of the system uses.

---

## 8. Observability

Single CLI: `python3 scripts/eos_os.py <cmd>`

| Command | Output |
|---------|--------|
| `eos_os status` | Active agents, running workflows, queue depth, recent failures |
| `eos_os agents` | Persistent agent registry + last-tick timestamps |
| `eos_os workflows --recent 10` | Last N workflows + statuses |
| `eos_os actions --recent 10` | Last N actions + risk levels |
| `eos_os optimizer` | Last analysis summary + pending proposals |
| `eos_os start` | Start orchestrator (foreground, handles SIGINT) |
| `eos_os stop` | Signal running orchestrator (via PID file) |

All commands read the JSONL/JSON data files directly. They do **not**
require the orchestrator to be running.

---

## 9. Integration summary

### What changed vs. what was there

- **Added L2 harness** — new single entry point. Workflow engine's
  StepExecutor now calls `AgentHarness.run_llm()` and
  `AgentHarness.run_action()` instead of touching `model_router` and
  `ActionSystem` directly.
- **Added capability enforcer** — action system now asks the enforcer
  before executing; agents declare capabilities; harness checks them.
- **Added persistent agents** — long-running, stateful. Orchestrator
  manages them alongside workflow jobs.
- **Added optimizer + proposals log** — reads workflow/action logs,
  proposes improvements, writes proposals as actions.
- **Added observability CLI** — `scripts/eos_os.py`.
- **Extended orchestrator** — now has `register_agent()` method and
  ticks persistent agents on its scheduler.

### What did NOT change

- `eos_ai/memory.py`, `eos_ai/model_router.py`, `eos_ai/gateway.py` —
  unchanged. The harness wraps them; it does not rewrite them.
- `scripts/action_system.py` — unchanged except for a single
  capability-check hook at the top of `execute()`.
- `scripts/query_graph.py` — unchanged.
- Legacy `eos_ai/orchestrator.py`, `eos_ai/workflow_engine.py`,
  `core/orchestrator/*`, `core/action_system/*` — unchanged, fenced.

---

## 10. Operator quick reference

```bash
# One-shot verification
python3 scripts/session_bootstrap.py --compact
python3 scripts/eos_os_smoke_test.py

# Inspect
python3 scripts/eos_os.py status
python3 scripts/eos_os.py workflows --recent 5
python3 scripts/eos_os.py actions --recent 5
python3 scripts/eos_os.py agents

# Run a workflow ad-hoc
python3 scripts/workflow_engine.py run research --goal "What changed in the graph layer?" --dry-run

# Run the optimizer once
python3 -m core.optimizer --once

# Start the control plane in foreground
python3 scripts/eos_os.py start
```

---

## 11. What is explicitly NOT in this pass

- No new LLM providers.
- No UI layer (intentional — operator CLI only).
- No multi-tenant isolation beyond what Neon already provides.
- No attempt to migrate existing `eos_ai/workflow_engine.py` consumers
  (discord_bot intent handler) onto the new harness. That's a later
  follow-up and a user-facing change.
- No deletion of legacy modules.

This doc is the contract. If code drifts from it, update the doc or fix
the code — not both.
