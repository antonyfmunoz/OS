---
type: codewiki-page
dir: (cross-cutting)
---

# Vision ↔ Reality Alignment — What UMH Is and Where It Stands

Synthesis of the full "UMH — Architecture — Master Document" (14 tabs, 318,643
chars) and the "Jarvis Master Handoff" (3 handoff docs), read 100% on
2026-07-10 and cross-checked against the audited codebase at `c806e75e2`
(see [audit-2026-07-10.md](audit-2026-07-10.md)). Written per the master doc's
own rules: infer the invariant behind the metaphor, and let observed reality
supersede declared intent.

## What is being built (industry terms)

**An Operator OS: a policy-governed, provenance-complete agentic orchestration
platform — Kubernetes' architecture applied to work instead of containers.**
`governed_mutation()` (transports/api/governed.py) is the admission
controller; WorkPackets are the pod specs; the IntentContract/EndStateVerifier
loop is the reconciler; adapters are the CRI/CNI-style plugin boundary; the
VPS/Beast mesh is the node pool; the 14 pre-commit gates are policy-as-code
for the codebase itself.

Four subsystems the industry ships as separate companies, unified here:

1. **Model gateway with purpose-role routing** — `model_router.call_with_fallback`
   with a deterministic floor: the system degrades to rules, never to silence.
2. **Agent observability + audit layer** — traces, proof artifacts, approval
   intercepts, replayable journals; OpenTelemetry-for-agents plus a SOC2-grade
   evidence trail. This is the layer enterprise agent adoption is blocked on.
3. **Internal developer platform for capability** — Tool Mastery Engine +
   skills + templates: competence as versioned, testable packages
   ("npm-for-work"; Backstage golden paths generalized).
4. **Ontology-grounded operational data layer** — canonical types, reality
   model, provenance-scored entities; the Palantir Foundry pattern with
   projections (EOS/CreatorOS/LyfeOS) as thin operational apps over one ontology.

The category the synthesis lands on: **governed execution infrastructure** —
the layer between frontier models (commoditizing) and business outcomes.
The deeper intent invariant across all 14 tabs: an **organization-in-software**
— every function a company gets from headcount (memory, coordination, QA,
compliance, institutional knowledge) reimplemented as substrate primitives,
enabling the one-person holdco. EOS is this machine pointed at the
SMB-acquisition playbook: acquire operationally weak cash flow, install the
OS, capture the margin delta.

## The defensibility flywheel

Governed execution is a data-generation machine. Every spine run emits a
labeled trajectory: state → interpretation → plan → **human approval/rejection**
→ action → outcome → proof. That tuple is process-supervision /
imitation-learning data — the scarcest training data in the industry —
produced as a byproduct of real operations (the Tesla FSD transposition: own
the loop, harvest trajectories, eventually train the proprietary operator
model). Models commoditize; audited trajectories of real economic work with
human preference labels do not. Instance Context Law + trace completeness
means the corpus accrues tenant-clean and provenance-complete from day one.

## Alignment verdict (2026-07-10)

The codebase is a faithful implementation of the doc's invariants — more
faithful than the doc records. All ten non-negotiable laws are built, and most
are mechanically enforced by pre-commit gates (the enforced dependency rule is
stricter than the documented one). On the doc's own Tier 1–6 maturity ladder:

| Tier | Status |
|---|---|
| 1 MVP (spine, governance, trace) | DONE — frozen as PLATFORM_SPEC v1.0.0 |
| 2 Operational (adapters, real tasks, continuity) | DONE-ish — vision-cockpit field NO-GO is the open wound |
| 3 Learning (routing/template updates from outcomes) | RECORDED, not COMPOUNDING |
| 4 World Model (simulation, counterfactuals) | seed only (`substrate/understanding/world_model/`) |
| 5 Organism (homeostasis, signaling) | CPU-gate stack is real homeostasis; signaling ad-hoc |
| 6 AI OS (installable, proprietary intelligence) | groundwork only |

**The critical missing organ is the Composition Engine** (master doc's 15-step
standard: intent binding → template selection → slot filling → capability
selection → completeness → governance → ExecutableComposition). The doc, the
Claude-chat synthesis, and the code audit all converge on the same "composition
gap": interpretation flows, but is not composed into runnable, adapter-bound
execution graphs. `substrate/templates/` is 3 files; completeness exists
(`substrate/governance/validation/completeness_engine.py`) but is not a
mandatory spine stage. This is the highest-leverage build in the system.

Where reality is AHEAD of the doc: the 14-gate enforcement stack, multi-tenant
instance hygiene, embodiment plumbing (5-dimensional voice routing, Beast work
lanes, vision relay), and the knowledge stack (graph/palace/this CodeWiki —
which operationalizes the doc's own "Current Reality truth layer" prescription).

Known canon-rot items: `.claude/CLAUDE.md` still expands UMH as "Universal
Mastery Hierarchy" (the expansion `substrate/organism/system_identity.py`
deterministically bans — correct is Universal **Meta Harness**); three
unreconciled roadmap numbering schemes (Tab 5, Tab 6, handoff P-phases) vs the
repo's actual P1–P3; two same-name councils
(`substrate/organism/council.py` and `substrate/understanding/deliberation/council.py`).

## Bridge (NOW / NEXT / LATER)

- **NOW** — fix the CLAUDE.md name rot; declare this CodeWiki the
  Current-Reality layer; close the vision-cockpit NO-GO (continuous PTZ,
  visible overlays, WebRTC decision); reconcile the roadmap numbering into one
  NOW/NEXT/LATER/END-STATE list.
- **NEXT** — close the composition gap: Template contract + registry-driven
  capability selection + completeness as a mandatory spine stage, proven by
  one intent → composed → governed → executed → traced → learned loop.
- **LATER** — learning that mutates routing/template scores (Tier 3 for real)
  → world model + simulation (Tier 4) → installability/UserInstance
  (productization), with EOS as the wedge monetizing each rung.

## Extrapolation (grounded)

0–6 mo: governed operator console — headcount-equivalent hours executed
without rescue as the metric. 6–24 mo: EOS as AI-native ERP/agentic-BPO for
founder-led SMBs (governance is the go-to-market), and/or the governance layer
itself sold as infrastructure for other people's agents. 2–5 yr: capability
registry as a signed-package marketplace; trajectory corpus reaches
training-viable scale; fine-tuned operator models collapse unit costs. 5+ yr:
the WorkPacket contract is actuator-agnostic — physical actuation is an
adapter swap, because governance-before-actuation was built first.

Honest constraints: single-tenant data gravity (the flywheel needs the EOS
wedge), eval scarcity for cognitive quality, and the substrate outrunning the
operator surface — cockpit-grade UX is the product, not polish.

## See also

[index.md](index.md) · [architecture.md](architecture.md) ·
[audit-2026-07-10.md](audit-2026-07-10.md) ·
[health-findings.md](health-findings.md) · [conventions.md](conventions.md)
