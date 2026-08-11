---
type: codewiki-page
dir: (cross-cutting)
---

# Terminal Fabric + 24/7 Workforce — Why Nothing Works Overnight, and What Closes It

The machinery that keeps the organism **alive** — born once at install,
instantiated at onboarding, ambiently alive thereafter (the Jarvis property).
The system runs on User↔Agent and Agent↔Agent communication **through terminals**
— some ephemeral, some persistent (tmux), across devices — with persistent agents
that **advance work 24/7 with recovery**. The reported symptom *"nothing closes my
reality gap overnight"* is, per [fractal-capability.md](fractal-capability.md),
**the same failure as "it isn't actually alive"**: the organism is born and killed
daily (a session animates it, the session ends, it dies) instead of born once and
living. This page is the code-verified diagnosis and the dependency-ordered fix.
Companions: [fractal-capability.md](fractal-capability.md) — the organism theory;
[role-composition.md](role-composition.md) — *what* runs and *how assembled*. This
page is *how it stays alive*. Every claim file:line-cited at `main` (2026-07-10).

## The org model this serves

The operator is the **coordinator**; agents are **employees**; the system is an
**institution** that keeps running when he sleeps and reports up when he wakes.
The intended chart:

```
   COORDINATOR (human — intent + approvals only)
        │
   SYSTEM ORCHESTRATOR      persistent · whole-system · 1 · never dies
        │
   DEVICE ORCH + EXECUTOR   persistent · 2 nested per device (VPS, Beast, …)
        │
   EPHEMERAL TASK AGENTS    spawn → work → report → die (per task)
```

Three persistent tiers + an ephemeral leaf. The persistent tiers are **standing
Roles** with a permanent reports-to; the leaves are **Roles composed on demand**
([role-composition.md](role-composition.md)).

## Diagnosis — the institution is built but never clocked in

Every row verified against the live checkout.

| # | The break | Evidence | At 2 a.m. |
|---|---|---|---|
| 1 | **Workforce loop never started.** 4 canonical workcells (advisor/executor/reviewer/researcher) are instantiated + heartbeat once, then idle — `WorkcellDaemon.run()` has no production caller. | create: `daemon.py:384-422`; loop: `workcell_daemon.py:117` (only tests call `.run()`) | Employees hired, seated, never told to start |
| 2 | **Loops are session-scoped.** The `start-loops` skill: *"loops run until session closes."* | skill registry `start-loops` | Session ends → whole workforce stops |
| 3 | **No live A2A channel.** Durable inbox/outbox `WorkcellV2` (atomic-rename, exactly-once) runs only in tests; `messages.jsonl` is the operator↔AI **chat log**, not a bus. Delivery is POLL-based; no push. | `workcell_protocol.py:130-397` (dormant); `store.py:74-120` (operator↔AI) | Executor can't hand work to Reviewer |
| 4 | **No state restore on restart.** `daemon_state.json` / `supervisor_state.json` are **write-only** — grep finds no reader that rehydrates. Restart = event **replay**, never working-state **restore**. | writes `daemon.py:992`; `start()` (`daemon.py:873`) never reads it; supervisor `persist_state` has no loader | Crashed agent restarts amnesiac |
| 5 | **Terminal sessions are memory-only.** `TerminalAdapter._sessions` is an in-memory `Popen` dict; `shutdown()` destroys all; nothing serializes. | `nodes/windows/umh_node/adapters/terminal.py:206-211,236-242` | Beast restart orphans every shell |
| 6 | **Mesh dispatch has no ack/redelivery/dedup.** Self-described "MVP placeholder." | `substrate/execution/bridge/station_bus.py` (docstring) | A Tailscale blip drops or double-executes work |

**One sentence:** the org chart, desks, filing cabinets, and phone system all
exist — no one flipped the switch that makes people show up, talk to each other,
and remember what they were doing after a power blink.

## What is already real (the fabric is closer than "nothing works")

- **Governed cross-device dispatch chain.** VPS route →
  `_governed_remote_dispatch` → `governed_mutation` → **signed verdict**
  (`sign_verdict`) → HTTP relay on `:8095` → node WS on `:8094` → node executes.
  `cockpit_workstation_control_routes.py:346-423`,
  `transports/node_mesh/server.py:42`.
- **Real persistent-shell manager (Beast).** Long-lived `Popen` + daemon
  reader-thread + 500-line ring buffer + per-session liveness (`process.poll()`)
  + idle reaping. Multi-shell (`powershell/pwsh/cmd/git-bash/wsl/bash/zsh/sh/python`).
  `nodes/windows/umh_node/adapters/terminal.py:170-428`.
- **`send-keys` inject path works for shells.** `RuntimeManager.inject_message`
  (`runtime_manager.py:293`) → `adapter.inject()` writes to live stdin.
- **Workcell crash-recovery exists.** `recover_stale_inflight()`
  (`workcell_protocol.py:241`) moves stranded inflight messages back to inbox.
- **Composition→execution runs today** (see [role-composition.md](role-composition.md)).

## The keystone stub — a reasoning agent in a terminal

The one adapter meant to put a **reasoning agent** (not a raw shell) into a
terminal — `ClaudeCodeRuntimeAdapter`, `runtime_type="claude_code_pty"`
(`substrate/organism/claude_code_runtime_adapter.py`) — is a **skeleton**:
`inject()` returns `{"injected": False, "reason": "…not yet implemented —
skeleton adapter"}` (≈L151-155); `start`/`status`/`collect_output` are skeletal.
This is *exactly* the operator's "type at a terminal, the agent converses back
in it, and keeps working" loop. Implementing it — with the agent running **inside
a named tmux session** — is the highest-leverage single build, because:

**Real resume falls out of it for free.** The tmux server outlives the daemon.
If the reasoning agent lives in a named tmux pane, "resume after crash" becomes
**re-attach to the pane + replay the event log to reload context** — no separate
heavy state-restore machinery. Persistence stops being a database problem and
becomes a re-attach problem, which tmux already solves.

## The fix — tiers in dependency order

### Tier A — Persistence spine (makes anything survive the night)
- **A1 Service-host the supervisor.** Systemd unit (`Restart=always`,
  `WatchdogSec`) owns the System Orchestrator process — not `/start-loops` inside
  a chat. *This one change turns "runs while watched" into "runs overnight."*
  Home: `infra/systemd/umh-orchestrator.service` + `services/orchestrator_daemon.py`.
- **A2 Leased durable queue.** Promote `ExecutionQueue` (`queue.json`) to
  claim/lease/ack: a worker claims with a TTL lease; crash → lease expires → item
  re-enqueues. Back the lease with Neon advisory locks.
  Home: `substrate/organism/execution_coordinator.py`.
- **A3 Checkpoint read-on-boot.** Make `daemon_state.json` a real checkpoint the
  supervisor **reads** on `start()` and resumes from (today: write-only).
  Home: `daemon.py:start()` + `runtime_supervisor.load_state()` (new).
- **A4 Recovery reconciler.** On boot: replay journal, reconcile checkpoint vs
  reality, expire stale leases, re-enqueue orphans — *act*, don't just report
  (today `ContinuityRuntime` only reports to the operator).
  Home: `substrate/organism/recovery_reconciler.py` (new).

### Tier B — Terminal fabric
- **B0 Implement `claude_code_pty`** (the keystone above), running inside a tmux
  session. Home: `substrate/organism/claude_code_runtime_adapter.py`.
- **B1 Unify tmux → one `TerminalPort`.** Collapse the three implementations
  (`adapters/tool_adapters/tmux.py`,
  `substrate/execution/workers/workstation/tmux_operational_adapter_v1.py`,
  `nodes/environments/tmux_surface.py`) into one canonical port with
  ephemeral / persistent-local / persistent-remote backends (a canonical-home
  fix per the essentialism law). Home: `substrate/sockets/terminal_port.py` (new).
- **B2 Persistent terminal registry + re-attach.** `{session_id → tmux target,
  device, owner_role, cwd, purpose}` persisted; reconcile on boot (list real tmux
  sessions, adopt orphans). This is the bridge from "tmux is persistent" to "the
  agent layer knows about it." Home: `substrate/organism/terminal_registry.py` (new).
- **B3 Streaming I/O over the mesh** (open → send-keys → stream output → close)
  with A-tier ack/dedup so a blip doesn't double-type. Home: extend
  `transports/node_mesh/` with a `terminal_channel` frame.

### Tier C — Chain of command (A2A)
- **C1 Start the workforce loop.** Call `WorkcellDaemon.run()` under the
  supervisor (A1). Smallest highest-leverage A2A change — activates the
  already-built inbox/outbox delivery.
- **C2 A2A contract with guarantees.** Promote `AgentMessage` from chat-log row
  to routed envelope (`from/to_agent, intent, correlation_id, requires_ack,
  deadline`); deliver via workcell inbox, ack via outbox, dedup via
  `correlation_id`. Home: `workcell_protocol.py` + `substrate/sockets/message_port.py`.
- **C3 Delegate / report / escalate** as first-class routed intents, hierarchy-
  aware (executor's boss is device-orch). Home:
  `substrate/organism/orchestration_loop.py` (make its in-process lease-and-ack
  distributed) + a small `hierarchy.py`.

### Tier D — Overnight-safety
- **D1 Async approvals w/ SLA + escalation.** Today Discord buttons expire at
  120s → overnight approval-work stalls forever. Add durable records,
  re-delivery, SLA, and a defined overnight policy (hold / auto-deny / escalate).
  Home: `substrate/organism/approval_store.py` + `approval_sla.py` (new).
- **D2 Spend gate.** Sibling to `cpu_gate.py`, consulted by `model_router` before
  any paid call — the CPU-gate incident's dollar analog (paid-API fallback is
  currently unbounded). Home: `substrate/execution/spend_gate.py` (new).
- **D3 Distributed lease (anti-split-brain).** Two orchestrators (one survived,
  one restarted) must never both act. Neon advisory-lock leadership lease (today:
  local `flock` only). Home: `substrate/organism/leadership.py` (new).
- **D4 Liveness → action.** Heartbeats are written (`heartbeat.json`) but nothing
  acts on a stale one; the supervisor must restart a dead worker.
  Home: `runtime_supervisor.py` reaper.
- **D5 Velocity governor.** Cap per-agent action velocity + quarantine, so a
  persistent agent can't spin all night. Home:
  `substrate/organism/velocity_governor.py` (new).

### Tier E — The coordinator's leverage
- **E1 Morning briefing.** Scheduled overnight-summary push (advanced / blocked
  on you / self-recovered / spend) — the snapshot-diff engine already computes it;
  make it a cron push. Home: cron → `report_dispatcher.py`.
- **E2 Live org view + terminal takeover.** Cockpit instrument bound to the
  hierarchy + attach/takeover into any persistent terminal over the mesh channel
  (B3). Home: `cockpit/src/renderer/` panels.

## The single most important move

**Tier A1 + B0 + C1 + A3-via-tmux.** Service-host the supervisor, start the
workcell loop, implement `claude_code_pty` inside a named tmux session, and
re-attach on boot. That combination makes a reasoning agent survive the night in
a terminal — and it is **mostly wiring plus one real adapter implementation, on
top of machinery that already exists** (the supervisor class, the checkpoint
writer, the workcell delivery, the governed mesh dispatch, the persistent-shell
manager are all built). The difference between "nothing works overnight" and
"the night shift runs" is flipping session-scoped loops to service-scoped and
filling one stub.

## Build order (whole program)

A1+A3+B0+C1 (survive + run overnight) → A2+A4 (crashes don't lose work) →
B1+B2 (terminals survive restart) → D1+D2+D4 (safe unattended) →
C2+C3+B3 (chain of command across devices) → D3+D5 (safe at multi-node scale) →
E1+E2 (coordinator leverage). Number as WP-TF-001…N in the roadmap canon.

## See also

[fractal-capability.md](fractal-capability.md) · [role-composition.md](role-composition.md) ·
[vision-alignment.md](vision-alignment.md) · [build-doctrine.md](build-doctrine.md) ·
[services-runtime.md](services-runtime.md) · [architecture.md](architecture.md)
