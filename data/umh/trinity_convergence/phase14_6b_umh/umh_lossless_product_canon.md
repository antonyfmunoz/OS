# UMH Lossless Product Canon

Phase: 14.6B-UMH (revised 14.6F)
Status: DRAFT

Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).

## Identity

Universal Meta Harness (UMH) is the integrated AI-native system whose core functional purpose is to build, maintain, and act through a reality-isomorphic approximation of reality (DEC-146C-001). UMH attempts to model reality across physical, digital, cognitive, biological, social, economic, symbolic, operational, software, memory, source-truth, and OS-level layers. Orchestration, governance, execution, memory, adapters, agents, Cockpit, and projections are capabilities and organs serving this reality model; they are not separate identities from UMH. The reality model is the central organizing model through which UMH understands intent, state, constraints, resources, possible actions, consequences, and feedback.

UMH is not a product sold to users -- it is the founder's private reality-modeling intelligence harness that all projections run on.

**Stage 1 Organism Definition (DEC-146C-003):** Stage 1 is one minimum viable UMH organism: Reality Model + Cockpit + Memory + Governed Execution Loop. These four components are indivisible -- they must reach minimum viability as one integrated system. Incremental builds are allowed only if each increment advances the integrated organism across all four components. Stage 1 does not require commercial-grade completeness before use; it requires a partially functional integrated vertical slice sufficient for the operator to actually operate through it.

- **Package**: universal-meta-harness
- **License**: MIT
- **Runtime**: Python 3.11+

## Core Substrate

The `substrate/` package is the innermost layer of UMH. It implements the reality-model infrastructure, governed execution pipeline, memory system, and coordination mechanisms that make UMH a reality-isomorphic intelligence harness rather than a collection of unrelated tools. PHILOSOPHY.md is ratified for rewrite to be UMH-universal, not EOS-specific (DEC-146B-UMH-002).

- **696 files**, **206,602 lines** of code
- Single type system via `substrate/types.py` with 197 registered canonical types
- Public API surface: `substrate/__init__.py` (execute, query, register, status)
- Four pre-commit gates enforce coherence at every commit

## Cockpit

The cockpit is the operator's interface into UMH's reality model at universalmetaharness.tech. Cockpit is part of the indivisible Stage 1 organism (DEC-146C-003) -- it is not a separate product or a passive dashboard. Cockpit without a reality model is only a dashboard; a reality model without Cockpit is inaccessible to the operator.

- **210 API endpoints** across substrate, organism, governance, system, and projection routes
- **27 panels** covering reality-model state, execution traces, governance decisions, intelligence routing, memory, and projection views

## Projections

UMH supports multiple application projections, each a domain-specific view of the substrate:

| Projection | Domain | Status |
|---|---|---|
| EntrepreneurOS (EOS) | Business operations | Active |
| CreatorOS | Creator workflow | Planned |
| LyfeOS | Life management | Planned |

Projections register at runtime via abstract ports in `substrate/sockets/`. The substrate never imports from projections. The ProductConnectionManager upward dependency violation is ratified for resolution via abstract port pattern at substrate/sockets/projection_port.py (DEC-146B-UMH-005).

## Intelligence Routing

All intelligence calls route through `adapters/models/model_router.py`.

- **10-provider routing** with deterministic fallback chain
- Current chain: cc_sdk (Opus 4.6 via subscription) > Gemini 2.5 Flash > Groq > Ollama
- Every LLM call has a deterministic fallback that produces usable output when all providers are down
- CEO/strategic tasks force best-available model via `agent_type='ceo'` or `force_opus=True`

## Governance

Governed execution ensures no autonomous action exceeds its authority.

- **5 risk levels**: NEGLIGIBLE, LOW, MEDIUM, HIGH, CRITICAL
- **4 permission tiers** controlling what agents can do without operator approval
- **Simulation dry-run** mode for cadence operations
- **Deliberation council** for multi-perspective decision evaluation
- **Materialization principle (DEC-146C-002)**: When UMH encounters a gap between imagined outcome and current state, governance classifies the gap type (unavailable, under-resourced, unproven, not-yet-acquired, time-bound) and tracks typed acquisition paths. Only impossible/illegal/unsafe are true boundaries. Missing capability creates typed gaps, not dead ends.

## Memory

Memory is one of the four indivisible Stage 1 organism components (DEC-146C-003). Memory without execution is passive storage; execution without memory is incoherent. Three persistent memory stores backed by Neon Postgres feed the reality model:

- **Conversation memory** -- session history and context continuity
- **Agent memory** -- per-agent learning, preferences, and accumulated knowledge
- **Canonical memory** -- structured knowledge from ingestion pipeline, forming the persistence layer of the reality model

## Execution Pipeline

Governed execution is one of the four indivisible Stage 1 organism components (DEC-146C-003). Execution without memory, governance, and reality model state is unsafe and incoherent. The target architecture is a single unified execution path: Substrate -> SignalRouter -> Spine (DEC-146B-UMH-003). Dead workstation code (26,671 lines) is ratified for extraction and deletion (DEC-146B-UMH-004). The 8-stage execution pipeline in `substrate/execution/spine.py`:

1. **Interpret** -- classify intent from signal
2. **Recall** -- retrieve relevant memory and context
3. **Lookup** -- query knowledge graph and canonical data
4. **Compose** -- assemble execution plan
5. **Route** -- select capability and model
6. **Execute** -- run the action
7. **Trace** -- record execution trace with Neon persistence
8. **Feedback** -- quality scoring and learning loop

## Infrastructure

| Component | Role |
|---|---|
| VPS (Hostinger) | Coordination brain, 4 Docker services (os-discord, os-operator, os-webhook, os-scraper) |
| Beast (Windows) | GPU workhorse, heavy compute, full repo mirror, large models |
| Tailscale mesh | Private network connecting all devices |
| Mobile (iPhone/Termius) | SSH access for commands and quick tasks |
| iPad (code-server) | Full VS Code in browser via VPS |
