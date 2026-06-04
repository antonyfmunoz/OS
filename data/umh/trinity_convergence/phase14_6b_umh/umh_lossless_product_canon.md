# UMH Lossless Product Canon

Phase: 14.6B-UMH
Status: DRAFT

## Identity

Universal Meta Harness (UMH) is the private universal intelligence substrate, orchestration kernel, governed execution control plane, and operator/Jarvis system. It is not a product sold to users -- it is the founder's personal command infrastructure that all projections run on.

- **Package**: universal-meta-harness
- **License**: MIT
- **Runtime**: Python 3.11+

## Core Substrate

The `substrate/` package is the innermost layer of UMH.

- **696 files**, **206,602 lines** of code
- Single type system via `substrate/types.py` with 197 registered canonical types
- Public API surface: `substrate/__init__.py` (execute, query, register, status)
- Four pre-commit gates enforce coherence at every commit

## Cockpit

The cockpit is the operator command center at universalmetaharness.tech.

- **210 API endpoints** across substrate, organism, governance, system, and projection routes
- **27 panels** covering organism state, execution traces, governance decisions, intelligence routing, memory, and projection views

## Projections

UMH supports multiple application projections, each a domain-specific view of the substrate:

| Projection | Domain | Status |
|---|---|---|
| EntrepreneurOS (EOS) | Business operations | Active |
| CreatorOS | Creator workflow | Planned |
| LyfeOS | Life management | Planned |

Projections register at runtime via abstract ports in `substrate/sockets/`. The substrate never imports from projections.

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

## Memory

Three persistent memory stores backed by Neon Postgres:

- **Conversation memory** -- session history and context continuity
- **Agent memory** -- per-agent learning, preferences, and accumulated knowledge
- **Canonical memory** -- structured knowledge from ingestion pipeline

## Execution Pipeline

The 8-stage execution pipeline in `substrate/execution/spine.py`:

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
