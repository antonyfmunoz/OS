# Convergence Law (NON-NEGOTIABLE)

Ratified 2026-07-21 (MVP Wave 1). Governs every concept in UMH at every scale:
global protocols → tenant organisms → projections → projects → conversations
→ Tasks → ExecutionAttempts.

## The law

ONE CONCEPT has exactly one:

1. **Semantic owner** — the module/class that defines what the concept IS
2. **Identity scheme** — one id format, minted in one place
3. **Lifecycle authority** — one state machine, one set of legal transitions
4. **Mutation authority** — one write path (governed_mutation for state changes)
5. **Event vocabulary** — one set of event types on one shared EventSpine
6. **Read contract** — one canonical read surface others project from
7. **Operator term** — one Layer-1 word (docs/LEXICON.md)
8. **Operator surface** — one place the operator sees/acts on it

## What the law does NOT require

One physical file/table. Multiple physical representations are valid ONLY
when explicitly classified as one of:

- canonical current state
- append-only event history
- evidence (EvidenceRef — provenance, never authority)
- execution trace
- immutable version history (e.g. superseded ObjectivePlanRecord versions)
- read projection (e.g. WorkGraph)
- cache
- compatibility representation (legacy adapter, migration pending)

A secondary representation may NEVER independently mutate the concept or
claim current truth. Internal specialization is required; semantic rivalry
is prohibited.

## Wave 1 canonical owners (code-verified adjudication)

| Concept | Owner |
|---|---|
| Objective identity + hierarchy | `substrate/organism/strategic_gap_engine.py` — `Goal` (GoalType.OBJECTIVE) via `GoalRegistry` |
| Plan | `substrate/execution/planning/records.py` — `ObjectivePlanRecord` (versioned; references a canonical Goal) |
| Task | `substrate/organism/work_packet.py` — `WorkPacket` |
| Work graph | `substrate/organism/work_graph.py` — `WorkGraph` (sole read projection) |
| Decision | `substrate/types.py` — `ApprovalRequest` (adapted; 4-part decision_ref) |
| Strategic gap | `strategic_gap_engine.Gap`; planning-time gap artifact = GapAssessmentSnapshot (evidence class, non-authoritative) |
| Events | `substrate/organism/event_spine.py` (one shared instance on the planning path) |
| Intent | `substrate/execution/intent/protocol.py` — `IntentResolution` (wraps legacy IntentSpec) |
| Identity contracts | `substrate/contracts/work_context.py` — PrincipalContext / WorkScope / WorkLineageContext / EvidenceRef / WorkRequirements / SkillRequirementRef |

Legacy machinery (ObjectiveQueue, Coordinator.Objective, WorkUnit, IntentLoop
records, SelfBuild/BuildLoop/Actions stores) = compatibility representations:
zero new writes from new Cockpit work, read adapters only, migration entries
in `docs/cockpit-surface-convergence.md`.

## Before creating ANY new type, store, panel, route, or term

1. Name the concept. Check the table above and `substrate/canonical_types.py`.
2. If an owner exists → extend/reference it. Never mint a rival identity,
   lifecycle, store, or surface.
3. If genuinely new → register the owner (canonical_types, LEXICON, and —
   for surfaces — the panel registry) in the same change.
4. If you find an existing rival → do NOT silently merge or delete; add a
   convergence-ledger entry with owner, rationale, and migration path.

## Enforcement

- Type divergence: `scripts/check_type_divergence.py` (pre-commit)
- Operator language: `scripts/check_operator_language.py` (shrink-only)
- Panel identity: `cockpit/src/renderer/panels/registry.ts` (aliases resolve
  to canonical panels; retired ids never dead-link)
- Adversarial divergence review checklist: authoritative plan §18 (any YES
  blocks unless documented as bounded compatibility debt with a retirement
  path and no current authority)
