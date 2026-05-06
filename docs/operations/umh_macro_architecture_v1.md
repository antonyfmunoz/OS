# UMH Macro Architecture v1

**Status:** ACTIVE
**Scope:** Defines the 10 macro layers of the Universal Model of a Hustler

---

## 10 Macro Layers

### 1. Interface Layer
Where humans and external triggers enter UMH. Discord, Telegram, CLI, web, voice, scheduled cron, webhooks. Translates raw input into UMH-native messages.

### 2. Control Plane
Routes, schedules, prioritizes, and sequences work. Determines what happens next. Orchestrator, scheduler, priority engine, queue management.

### 3. Understanding Layer
Interprets intent, extracts context, classifies requests. NLP, intent classification, entity extraction, context assembly.

### 4. State Layer
Tracks current state of all entities: ventures, projects, tasks, agents, environments, workers, adapters, mastery. Single source of truth.

### 5. Composition Layer
Composes multi-step plans, breaks goals into actions, determines dependencies, assembles execution graphs. Planning, decomposition, dependency resolution.

### 6. Governance Layer
Enforces rules, policies, and constraints. Authority engine, risk classification, approval gates, blocked actions, mastery requirements. Nothing executes without governance clearance.

### 7. Execution Plane
Performs work through governed workers in explicit environments. Binds actions to execution contexts, dispatches work packets, manages worker lifecycles, collects results.

### 8. Adapter Boundary Layer
Mediates all interaction with external systems. Every external system — tool, SaaS, model, environment, human, data source — accessed through adapters. Adapters connect and translate; they do not independently execute.

### 9. Observability + Proof Layer
Records everything. Traces, proof artifacts, audit logs, metrics, health checks. Proves that execution happened correctly. Enables retrospective analysis.

### 10. Learning + Self-Regulation Layer
Governed update process. TME research flows, mastery acquisition, staleness detection, self-improvement loops. Updates competence based on proof and observation.

---

## Phase 96.8A Layer Mapping

The VPS ↔ Local Worker Bridge belongs primarily to:

| Layer | Contribution |
|-------|-------------|
| Execution Plane | Worker dispatch, packet lifecycle |
| Adapter Boundary Layer | Environment Adapter / bridge boundary |
| Governance Layer | Packet validation, blocked actions, approval gates |
| Observability + Proof | Result ingestion, proof artifacts |
| State Layer | Heartbeat, bridge status, worker liveness |

---

## Layer Interaction Rules

- Layers communicate downward (Interface → Control → Understanding → ...)
- Governance Layer has veto power over Execution Plane
- Adapter Boundary Layer is invoked BY Execution Plane (not self-invoking)
- Observability collects from all layers
- Learning feeds back into Governance and State
