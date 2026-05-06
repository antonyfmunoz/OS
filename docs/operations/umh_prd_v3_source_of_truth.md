# UMH PRD v3 — Source of Truth

**Version:** 3.0
**Status:** ACTIVE
**Last Updated:** Phase 96.8A.1

---

## System Definition

The Universal Model of a Hustler (UMH) is a self-improving AI operating system for building and running businesses. It provides intelligence, governance, execution, and learning infrastructure for a founder-led organization.

UMH is a **substrate** — not an application. EOS (EntrepreneurOS) is one platform consumer of UMH substrate capabilities.

---

## Prime Directive

Build a compounding system where every execution makes the next execution better, safer, more capable, and more governed.

---

## What UMH Is

- An intelligence substrate with governed execution
- A system that compounds knowledge through mastery acquisition
- A governed bridge between intention and reality
- A proof-producing system where execution generates evidence
- A self-regulating system that detects and corrects its own gaps

## What UMH Is NOT

- A chatbot with tool access
- An unstructured agent that tries things and hopes
- A system that executes because it can
- An autonomous actor without governance
- A monolithic application

---

## Hard Invariants

1. **External Boundary Law** — No external system accessed directly. All through adapters.
2. **Adapters Connect, Not Execute** — Adapters translate; Execution Plane performs.
3. **Action/Execution Separation** — Intent is separate from performance.
4. **Mastery Before Execution** — UMH must have competence before acting.
5. **Governance Before Execution** — Every action must pass governance.
6. **Proof After Execution** — Every action must produce evidence.
7. **No Immature Adapter Execution** — Immature adapters cannot execute.
8. **Trace Everything** — Complete inspectable records.
9. **Founder Authority** — Critical decisions require human approval.
10. **Compounding Returns** — Every execution improves the system.

---

## Single Runtime Spine

UMH has one runtime spine:

```
Intent → Governance Check → Mastery Check → Execution Binding →
Worker Dispatch → Actuation → Proof Collection → Result Ingestion →
Learning Update → State Update
```

Every action follows this spine. No shortcuts. No bypasses.

---

## Macro Architecture (10 Layers)

1. **Interface Layer** — Human/trigger input translation
2. **Control Plane** — Routing, scheduling, prioritization
3. **Understanding Layer** — Intent/context interpretation
4. **State Layer** — Entity state tracking
5. **Composition Layer** — Plan assembly, dependency resolution
6. **Governance Layer** — Rule/policy enforcement, approval gates
7. **Execution Plane** — Governed worker dispatch and lifecycle
8. **Adapter Boundary Layer** — External system mediation
9. **Observability + Proof Layer** — Trace/evidence collection
10. **Learning + Self-Regulation Layer** — Mastery acquisition, improvement

---

## Corrected Adapter Contract

Adapters are the universal connection and translation boundary.

```
Adapter {
  connect()              — establish connection
  validate_connection()  — confirm live and authorized
  describe_capabilities()— enumerate what system can do
  translate_request()    — convert UMH contract to external call
  validate_operation()   — check if operation is permitted
  normalize_result()     — convert response to UMH artifact
  observe_state()        — monitor without mutating
  disconnect()           — release connection
}
```

Adapters do NOT independently execute. The Execution Plane invokes adapters through governed Work Packets.

---

## Action / Execution Separation

| Concept | Definition |
|---------|-----------|
| Action | Intended state transformation |
| Capability | Abstract ability required |
| Adapter | Connection/translation boundary |
| Environment | Where execution occurs |
| Worker Runtime | What performs execution |
| Actuation | Low-level effect-producing operation |
| Work Packet | Governed executable instruction |
| Proof Artifact | Evidence of correct execution |
| Trace | Complete inspectable record |
| Learning | Governed update process |

---

## Universal Mastery / Competence Layer

TME (Tool Mastery Engine) is the first implementation slice.

Universal Mastery verifies scoped, versioned, testable, proof-backed competence before execution.

**Categories:** TOOL, ACTION, DOMAIN, ENVIRONMENT, DATA, MODEL, ADAPTER_BOUNDARY, HUMAN_APPROVAL, GOVERNANCE, CONTEXT, PHYSICAL_WORLD

**Mastery is scoped** — not "master X" but "master specific capability of X under specific constraints with specific proof requirements."

---

## Memory Discipline

- Memory is governed state, not casual storage
- Memory promotion requires evidence and approval
- Memory never leaks across unauthorized boundaries
- Memory staleness is tracked and acted upon

---

## Trace / Proof Distinction

| Concept | Purpose |
|---------|---------|
| Trace | Complete inspectable record of what happened |
| Proof | Evidence that what happened was correct |

Trace is passive observation. Proof is active validation. Both are required.

---

## W0-001 Mapping

Work Order W0-001 (Google Workspace CU rerun) maps to this architecture:

- **Action:** Read Drive inventory + extract Docs content
- **Adapters:** W-GDRIVE-API-001, W-GDOCS-API-001, W-GDRIVE-CU-001, W-GDOCS-CU-001
- **Environment:** LOCAL_WINDOWS_GUI, LOCAL_BROWSER
- **Worker:** Local Windows worker (tmux session)
- **Bridge:** VPS ↔ Local Worker Bridge (Environment Adapter)
- **Governance:** 17 CU blocked actions, read-only policy
- **Mastery:** Tool (Drive API, Docs API, CU), Environment (Windows GUI), Action (inventory read)
- **Proof:** Inventory count, content hash, coverage validation
- **Human Approval:** Founder confirmation before CU execution

---

## Professional Phase Guardrail

UMH is currently in **pre-revenue single-founder phase**. This means:

- One organization, multiple ventures
- One founder as sole authority
- Economy mode active (cost-constrained model routing)
- No multi-tenant requirements yet
- Proof requirements focus on founder trust
- Human approval is founder confirmation

Phase gates:
1. Pre-revenue → $750 first sale
2. First revenue → $10K/month
3. Scaled → productization as SaaS

Architecture decisions must serve the CURRENT phase while not blocking future phases.
