# Universal Mastery / Competence Layer v1

**Status:** ACTIVE
**Layer:** Governance Layer + Execution Plane prerequisite
**Scope:** Universal — parent doctrine over Tool Mastery Engine

---

## Doctrine

UMH must not execute merely because it has access to a tool, model, environment, data source, human, or adapter.

Before execution, UMH must possess or acquire sufficient **scoped, versioned, testable, proof-backed** mastery of the action, domain, tool/system, adapter boundary, environment, data, model/worker, human approval path, governance constraints, success criteria, and proof requirements.

---

## Relationship to Tool Mastery Engine

**Tool Mastery Engine (TME) is the first implementation slice** of the Universal Mastery / Competence Layer. TME covers the TOOL mastery category. Universal Mastery is the parent concept that encompasses all categories.

TME remains valid, operational, and unchanged. It is not renamed or destroyed — it is contextualized as one slice of the full competence system.

---

## Mastery Categories

| Category | What It Governs |
|----------|----------------|
| TOOL | Expert-level tool usage (TME implementation) |
| ACTION | Understanding of intended state transformation |
| DOMAIN | Business/domain context for the action |
| ENVIRONMENT | Competence in the execution environment |
| DATA | Understanding of data being operated on |
| MODEL | Knowledge of AI model being invoked |
| ADAPTER_BOUNDARY | Understanding of the adapter's constraints |
| HUMAN_APPROVAL | Knowledge of approval path and requirements |
| GOVERNANCE | Understanding of what is allowed/blocked |
| CONTEXT | Situational awareness for this execution |
| PHYSICAL_WORLD | Understanding of physical-world constraints |

---

## Scoped Mastery

Mastery is always scoped. General statements are insufficient.

**Bad:** "master Google Workspace"

**Good:** "master Google Docs tab-aware extraction for W0-001 under read-only OAuth/API constraints, with includeTabsContent=true, child tab recursion, source provenance, and coverage validation."

---

## Mastery Status

| Status | Meaning |
|--------|---------|
| MISSING | No mastery exists |
| PARTIAL | Some knowledge but gaps remain |
| PROVISIONAL | Provisional based on prior proof |
| CURRENT | Full mastery within freshness window |
| STALE | Was current but freshness expired |
| BLOCKED | Cannot acquire mastery (external blocker) |
| VERIFIED | Mastery confirmed by proof artifacts |

---

## Freshness and Staleness

Mastery has a freshness window derived from the tool's speed category:
- fast (14 days) — rapidly changing tools
- medium (45 days) — standard tools
- stable (90 days) — stable tools
- slow (120 days) — very stable tools

Stale mastery blocks high-risk execution. Low-risk execution may proceed with warning.

---

## Proof-Backed Mastery

High-risk execution requires VERIFIED mastery — mastery backed by proof artifacts, not just self-declaration. The proof requirement ensures that UMH can demonstrate competence, not merely claim it.

---

## Risk-Weighted Requirements

| Risk Level | Mastery Requirement |
|------------|-------------------|
| LOW | CURRENT or PROVISIONAL sufficient |
| MEDIUM | CURRENT required |
| HIGH | VERIFIED required |
| CRITICAL | VERIFIED + founder confirmation |

---

## Implementation

- `core/mastery_engine/universal_mastery.py` — parent decision engine
- `core/mastery_engine/mastery_requirement_contracts.py` — scoped requirements
- `core/tool_mastery_manager/mastery_assurance.py` — TME (TOOL category)
