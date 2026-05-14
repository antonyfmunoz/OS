# Phase 96.8BP — Workstation Operational Embodiment

> Date: 2026-05-09
> Status: COMPLETE
> Tests: 93/93 pass
> Modules: 10 created

---

## What This Phase Built

Operationalized the substrate into the real workstation environment.
10 modules that embody governed execution on an actual VPS —
shell commands, tmux sessions, operational modes, and continuity tracking.

---

## Architecture

```
WorkstationOperationalEmbodimentEngine (apex)
  ├── WorkstationExecutionOrchestrator (pipeline)
  │     ├── GovernedShellAdapter (allowlist shell)
  │     ├── TmuxOperationalAdapter (governed tmux)
  │     ├── WorkstationObservabilityPipeline (telemetry)
  │     └── WorkstationContinuityBridge (lineage)
  ├── WorkstationStateRegistry (live state)
  ├── WorkstationReplayValidator (determinism)
  └── OperationalModeSystem (4 modes)
```

---

## Module Table

| Module | File | Purpose |
|--------|------|---------|
| Workstation Contracts | `core/workstation/workstation_contracts_v1.py` | 8 data shapes with deterministic IDs |
| Operational Modes | `core/workstation/workstation_operational_modes_v1.py` | 4 modes constraining all execution |
| Governed Shell Adapter | `core/workstation/governed_shell_adapter_v1.py` | Allowlist shell execution |
| Tmux Operational Adapter | `core/workstation/tmux_operational_adapter_v1.py` | Governed tmux interaction |
| Workstation State Registry | `core/workstation/workstation_state_registry_v1.py` | Live state capture |
| Workstation Execution Orchestrator | `core/workstation/workstation_execution_orchestrator_v1.py` | Pipeline coordination |
| Workstation Observability Pipeline | `core/workstation/workstation_observability_pipeline_v1.py` | Execution telemetry |
| Workstation Replay Validator | `core/workstation/workstation_replay_validator_v1.py` | Decision path replay |
| Workstation Continuity Bridge | `core/workstation/workstation_continuity_bridge_v1.py` | Session lineage |
| Workstation Embodiment Engine | `core/workstation/workstation_operational_embodiment_engine_v1.py` | Central orchestrator |

---

## Contracts (8)

| Contract | ID Prefix | Purpose |
|----------|-----------|---------|
| WorkstationState | wstate- | Current operational state |
| WorkstationSession | wsess- | Tmux/shell session descriptor |
| WorkstationEnvironment | wenv- | Environment capabilities |
| WorkstationExecutionRequest | wexreq- | Execution request |
| WorkstationExecutionResult | wexres- | Execution result |
| WorkstationContinuityState | wcont- | Continuity snapshot |
| WorkstationResumeState | wresume- | Session resumption |
| WorkstationOperationalSnapshot | wsnap- | Complete operational snapshot |

---

## Operational Modes (4)

| Mode | Shell Commands | Tmux Ops | Adapters | Timeout |
|------|---------------|----------|----------|---------|
| Developer | All safe + git + test + ruff | Full (inspect + control) | shell, tmux, filesystem | 60s |
| Research | Inspection + git | Inspect only | shell, tmux | 30s |
| Audit | pwd, whoami, hostname, date, uptime | list-sessions only | None | 10s |
| Overnight Safe | Inspection + docker | Inspect only | shell | 15s |

---

## Governance Rules

### Shell Governance (4 rules, evaluated in order)
1. **STRUCTURAL_BLOCK** — 33+ prefixes + 11 exact matches. Never execute regardless of mode.
2. **DANGEROUS_CHAIN** — Detects: `; rm`, `&& rm`, `|| rm`, `| sudo`, backticks, `$()`, pipe count > 2.
3. **MODE_ALLOWLIST** — Command prefix must be in the mode's allowed set.
4. **RISK_CLASSIFICATION** — Read-only = safe, everything else = low.

### Tmux Governance (double governance)
- Tmux operation must be in mode's allowed tmux operations.
- Command content sent via send-keys must pass full shell governance.

### Structural Blocklist (never configurable)
`rm`, `sudo`, `chmod`, `chown`, `kill`, `pkill`, `killall`, `apt`, `dpkg`,
`pip install`, `pip uninstall`, `npm install`, `npm uninstall`, `curl -X`,
`wget`, `mkfs`, `dd`, `shutdown`, `reboot`, `systemctl`, `bash -c`, `sh -c`,
`eval`, `exec`, `> /`, `>> /`, `| sudo`, `; rm`, `&& rm`, `|| rm`

---

## Workstation Commands (9)

| Command | Description |
|---------|-------------|
| workstation-status | Full workstation operational status |
| tmux-status | Active tmux sessions and panes |
| runtime-sessions | Running services and containers |
| resume-work | Generate resume state for session continuation |
| operational-state | Current operational mode and constraints |
| environment-health | Workstation environment health check |
| replay-validate | Replay recent executions for determinism |
| execution-history | Recent execution history with outcomes |
| mode-info | Operational mode details and constraints |

---

## Test Results

```
93 passed in 1.29s

TestContracts ............... 13 passed
TestOperationalModes ........ 12 passed
TestGovernedShellAdapter .... 18 passed
TestTmuxAdapter ............. 6 passed
TestStateRegistry ........... 5 passed
TestObservabilityPipeline ... 4 passed
TestReplayValidator ......... 6 passed
TestContinuityBridge ........ 9 passed
TestExecutionOrchestrator ... 5 passed
TestEmbodimentEngine ........ 15 passed
```

---

## Constraints Met

| Constraint | How Met |
|-----------|---------|
| No unrestricted desktop control | All execution gated by allowlist + mode |
| No arbitrary shell execution | Structural blocklist + mode allowlist = only approved prefixes run |
| No governance bypass | Governance evaluates before every execution, no exceptions |
| No hidden workstation state | All state captured to JSONL, all decisions persisted |
| No autonomous recursive behavior | Engine executes on request only, no background loops |
| No weakened replay determinism | Same input → same governance verdict, risk class, adapter routing |
| No adapter execution outside pipeline | Orchestrator is the single execution entry point |

---

## What Became Real

- **Governed shell execution** — Real subprocess.run behind a 4-rule governance gate.
- **Governed tmux interaction** — Real tmux commands behind double governance.
- **Live state capture** — Real tmux sessions, docker containers, git info detected from live environment.
- **Operational mode enforcement** — Mode constrains every command, every tmux op, every adapter.
- **Execution lineage** — Every command's governance decision, outcome, and adapter routing persisted.
- **Deterministic replay** — Decision path replays produce identical verdicts.

---

## What Remains Partial

- **Tmux send-keys execution** — Governance works, but actual tmux send-keys was tested in governance-denial path only (no live tmux target in test environment).
- **Workstation commands wiring** — Commands defined and dispatchable, but not yet wired into the canonical runtime spine from 96.8BO.
- **Continuity engine integration** — Bridge produces events, but not yet feeding into SubstrateContinuityEngine from 96.8BN.
