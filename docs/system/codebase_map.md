# UMH Codebase Map — Phase 75A

> Generated: 2026-05-02 | Total modules: 734 | Packages: 52

---

## Repository Overview

The Universal Meta Harness (UMH) is a domain-independent intelligence substrate
located at `/opt/OS/umh/`. It implements a 9-stage run loop (Signal → Intent →
World → Decision → Compose → Route → Govern → Execute → Feedback) with a
control plane HTTP API, typed protocol contracts, and adapter-based execution.

**Entry point**: `umh.run.run()` — single function, full pipeline.
**Control plane**: `umh.control.api` — FastAPI HTTP surface.
**Gateway**: `umh.gateway.entry` — translates external signals to UMH format.

---

## Package / Layer Overview

### Tier 0 — Core Infrastructure (13 modules)
| Package | Files | Role |
|---------|-------|------|
| `umh.core` | 4 | Clock, config, logging |
| `umh.events` | 2 | Event stream / bus |
| `umh.storage` | 4 | Neon DB adapter, storage backend |
| `umh.gateway` | 2 | Canonical signal entry |
| `umh` (root) | 3 | `run.py`, `__init__`, `__main__` |

### Tier 1 — Perception & Interpretation (36 modules)
| Package | Files | Role |
|---------|-------|------|
| `umh.signal` | 7 | Signal ingestion, hierarchy, routing, sensitivity |
| `umh.intent` | 3 | Intent compilation from signals |
| `umh.context` | 4 | Context assembly, budget, types |
| `umh.decision` | 2 | Decision trace / audit |
| `umh.attention` | 4 | Priority scoring, queue |
| `umh.reasoning` | 16 | Causal attribution, influence scoring, meta control, convergence |

### Tier 2 — World Model & Memory (17 modules)
| Package | Files | Role |
|---------|-------|------|
| `umh.world` | 9 | Two-layer world model, dynamics, simulation, calibration |
| `umh.memory` | 8 | Storage, embedder, hooks, context, metrics |

### Tier 3 — Goals, Strategy & Planning (48 modules)
| Package | Files | Role |
|---------|-------|------|
| `umh.goals` | 17 | Goal engine, state, alignment, arbitration, budget, credit, policy |
| `umh.strategy` | 10 | Decomposer, scoring, refiner, memory, templates, history |
| `umh.planning` | 11 | Planner, hierarchical, directive engine, quality, validator |
| `umh.objectives` | 2 | Objective arbitration |
| `umh.orchestrator` | 8 | Engine, retry, summary, task, timeline, worker |

### Tier 4 — Governance & Security (10 modules)
| Package | Files | Role |
|---------|-------|------|
| `umh.governance` | 4 | Authority levels, governor, capability gating |
| `umh.policy` | 3 | Foresight engine, stability guard |
| `umh.security` | 3 | Access control, execution guard |

### Tier 5 — Execution & Capability (73 modules)
| Package | Files | Role |
|---------|-------|------|
| `umh.execution` | 20 | Engine, contract, stages, approval, harness, pipeline, quality, observability |
| `umh.capability` | 3 | Registry and router |
| `umh.capabilities` | 2 | Capability spec |
| `umh.runtime_loop` | 13 | Live lifecycle loop, session registry, action executor |
| `umh.stages` | 10 | Composable execution stage wrappers |
| `umh.scheduler` | 5 | Policy, runner, store |
| `umh.jobs` | 8 | Job lifecycle, locking, persistence, priority |
| `umh.workflows` | 2 | Workflow executor |
| `umh.actions` | 4 | Action channel, router, schema |

### Tier 6 — Adapters & Environments (40 modules)
| Package | Files | Role |
|---------|-------|------|
| `umh.adapters` | 26 | LLM, browser, discord, notion, voice, workstation, shell adapters |
| `umh.environments` | 10 | Container, sandbox, scheduler, telemetry, system context |
| `umh.tools` | 2 | Tool registry |

### Tier 7 — Protocols (14 modules)
| Package | Files | Role |
|---------|-------|------|
| `umh.protocols` | 14 | Typed contracts for adapters, capabilities, execution, governance, memory, planning, signals, workstation, world |

### Tier 8 — Intelligence Kernel / Reality Mimicry (65 modules)
| Package | Files | Role |
|---------|-------|------|
| `umh.runtime` | 65 | Adaptive learning, regime classification, pattern matching, half-life, weight evolution, trajectory, simulation, identity, hysteresis. Built in phases 30-74. |

### Tier 9 — Profiles & Model (9 modules)
| Package | Files | Role |
|---------|-------|------|
| `umh.model` | 4 | Behavior model, aggregator, traits |
| `umh.brains` | 5 | Brain context, profile, registry, signals |

### Tier 10 — Learning & Prediction (36 modules)
| Package | Files | Role |
|---------|-------|------|
| `umh.learning` | 4 | Learning feedback, metrics, weights |
| `umh.prediction` | 12 | Calibrator, evaluator, predictor, temporal, weights |
| `umh.feedback` | 5 | Outcome evaluator, outcome feedback, dynamics |
| `umh.analytics` | 10 | Exploration, score distribution, strategy synthesis, pattern engine |
| `umh.patterns` | 5 | Abstraction, embedding, registry, similarity |

### Tier 11 — Substrate / Operator Layer (170 modules)
| Package | Files | Role |
|---------|-------|------|
| `umh.substrate` | 170 | Operator sessions, task pipeline, execution workers, voice/meeting intelligence, station runtime, presence, browser agent, discord transport |

### Tier 12 — Legacy Runtime Engine (147 modules)
| Package | Files | Role |
|---------|-------|------|
| `umh.runtime_engine` | 147 | Original eos_ai modules migrated to umh namespace. Contains cognitive_loop, agent_runtime, model_router, gateway, session_runtime, knowledge_domains, knowledge_layers. **42 modules have newer equivalents in clean packages.** |

### Tier 13 — Interfaces (19 modules)
| Package | Files | Role |
|---------|-------|------|
| `umh.interfaces` | 19 | Discord bot, Telegram bot, webhooks (calendly, cc_receiver, higgsfield) |

### Tier 14 — Distributed / Future (22 modules)
| Package | Files | Role |
|---------|-------|------|
| `umh.nodes` | 11 | Distributed runtime, heartbeat, failover, SSH transport |
| `umh.cells` | 9 | Cell runtime, orchestrator, persistence |
| `umh.workflows` | 2 | Workflow executor |

---

## Classification Summary

| Classification | Count | Percentage |
|---------------|-------|------------|
| MVP_CORE | 126 | 17% |
| MVP_SUPPORT | 109 | 15% |
| KEEP | 477 | 65% |
| FUTURE | 22 | 3% |
| DELETE_CANDIDATE | 0 | 0% |

---

## PRD Domain Distribution

| Domain | Count | Top Packages |
|--------|-------|-------------|
| runtime | 223 | runtime_engine (147), runtime (65), nodes (11) |
| presence | 170 | substrate (170) |
| execution | 73 | execution (20), runtime_loop (13), stages (10), jobs (8), scheduler (5) |
| planning | 48 | goals (17), planning (11), strategy (10), orchestrator (8) |
| learning | 36 | prediction (12), analytics (10), patterns (5), feedback (5), learning (4) |
| interpretation | 36 | reasoning (16), signal (7), attention (4), intent (3), context (4) |
| adapters | 30 | adapters (26+4 execution) |
| interface | 19 | interfaces (19) |
| protocols | 14 | protocols (14) |
| core | 13 | core (4), events (2), gateway (2), control (5) |
| capabilities | 11 | capability (3), capabilities (2), agents (4), tools (2) |
| environments | 10 | environments (10) |
| world_model | 9 | world (9) |
| profiles | 9 | model (4), brains (5) |
| memory | 8 | memory (8) |
| governance | 7 | governance (4), policy (3) |
| storage | 7 | storage (4), persistence_layer (3) |

---

## Key Redundancy: runtime_engine vs Clean Packages

The `umh.runtime_engine` package (147 files) is the original EOS runtime migrated
to UMH namespace. **42 of its modules have newer, cleaner equivalents** in
domain-specific packages:

- reasoning: 11 duplicates (causal_*, influence_*, meta_*, convergence, etc.)
- analytics: 7 duplicates (exploration, pattern, score, signal, strategy)
- planning: 3 duplicates (directive_engine, hierarchical_planning, plan_mutation)
- feedback: 2 duplicates (outcome_evaluator, outcome_feedback)
- policy: 2 duplicates (foresight_engine, stability_guard)
- execution: 3 duplicates (system_graph, system_registry, system_selector)
- gateway: 1 duplicate
- goals: 1 duplicate (meta_goal)
- signal: 1 duplicate (event_bus)
- adapters: 1 duplicate (model_router)
- memory: 1 duplicate
- persistence: 1 duplicate (memory_fabric)
- primitives: 1 duplicate

The remaining ~105 runtime_engine modules have no clean equivalent yet and
contain valuable EOS-specific logic (knowledge_domains, skill_registry,
agent_teams, ceo_agent, etc.).

---

## Test Architecture

- 399 test files total
- `tests/unit/` — 147 phase-specific unit tests (phase2c through phase74)
- `tests/substrate/` — 70 substrate integration tests
- `tests/runtime/` — 8 runtime lifecycle tests
- `tests/adapters/` — 5 adapter tests
- `tests/platforms/eos/` — 11 EOS platform tests
- `tests/` (root) — 158 general tests

---

## Data Sources

- Module inventory: `docs/system/module_inventory.json`
- Dependency graph: `docs/system/dependency_data.json`
- Scanner: `scripts/phase75a_dep_scanner.py`
- Classifier: `scripts/phase75a_classifier.py`
