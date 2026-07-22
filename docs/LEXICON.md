# UMH Operator Lexicon — Two-Layer Language Standard

Ratified 2026-07-21 (MVP Wave 1). Word slate provisional pending final owner
swaps; structure and mapping are binding.

UMH speaks TWO layers. **Layer 1** is what the operator reads on every
surface. **Layer 2** is the canonical internal type each word resolves to.
New and touched surfaces use Layer 1 words ONLY; internals never leak into
operator-facing labels. Enforced shrink-only by
`scripts/check_operator_language.py`.

## Layer 1 → Layer 2 mapping

| Operator word | Canonical internal (Layer 2) | Notes |
|---|---|---|
| **Goal** | `strategic_gap_engine.Goal` (non-OBJECTIVE types) | Long-horizon direction (vision/outcome/roadmap) |
| **Objective** | `strategic_gap_engine.Goal` with `GoalType.OBJECTIVE`, owned by `GoalRegistry` | One canonical identity per tenant + objective key + scope |
| **Plan** | `ObjectivePlanRecord` (versioned) + `WorkGraph` read projection | A Plan pursues exactly one Objective |
| **Task** | `WorkPacket` | The unit of work; kanban card |
| **Decision** | `ApprovalRequest` (adapted; 4-part `decision_ref`) via UnifiedApprovalRuntime | Surfaces ONLY in the Top HUD ControlPanel |
| **Execution** | ExecutionAttempt (Wave 2+; ZERO in Wave 1) | Plan acceptance never authorizes execution |
| **Outcome** | outcome records (continuity runtime) | |
| **Proof** | evidence packages / `EvidenceRef` provenance | Evidence is never mutation authority |
| **Agent** | Role-bound worker (RoleContract; scheduling = Wave 2) | |
| **Memory** | canonical memory subsystems | |
| *(assistant name)* | `get_ai_name()` / SelfModel.ai_name; neutral fallback "Assistant" | NEVER a hardcoded persona name in surfaces |

## Surface vocabulary rules

- "Intent", "IntentSpec", "IntentLoop", "WorkPacket", "packet",
  "ObjectivePlanRecord", "ApprovalRequest", "mutation", "spine" are Layer 2 —
  they never appear as operator-facing labels on new/touched surfaces.
- "Approval" as a label is legacy for **Decision** on touched surfaces
  (compatibility ids like the `approvals` panel alias remain valid ids).
- Synonyms are banned only where they stand in for the canonical work object
  ("job", "ticket", "todo" for Task; "blueprint", "roadmap" for Plan when it
  means an ObjectivePlanRecord). Domain prose in user text, model output,
  logs, and payload data is untouched.
- Status line after plan approval reads exactly:
  `PLAN APPROVED — EXECUTION NOT STARTED`.

## Change control

The Layer-1 slate changes only by owner ruling (final word swaps remain an
open owner item). The gate baseline may only shrink — no new Layer-2 leakage
in operator surfaces.
