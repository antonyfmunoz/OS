# runtime — UMH Runtime

## Identity
This is the single UMH runtime layer — live cognition and execution.
All AI machinery lives here: LLM routing, memory, cognitive loop,
agent hierarchy, voice pipeline, transport, and execution fabric.

The `eos_ai/` directory is a dead shim layer that re-exports from
`runtime/`. It has zero active consumers and is pending removal.
All code imports from `runtime.*` directly.

## Purpose
Live cognition and execution machinery. This is NOT a second layer
inside a larger substrate — `core/` holds contracts and foundations,
`runtime/` is the single runtime that implements them.

## Key modules
cognitive_loop.py   — PERCEIVE/GENERATE/ACT
agent_runtime.py    — LLM dispatch + fallback
agent_hierarchy.py  — org chart + routing
gateway.py          — message classification
primitives.py       — PRIMITIVE_LIBRARY (13)
template_library.py — TEMPLATE_LIBRARY (5)
evolution_engine.py — stage-aware gating
knowledge_integrator.py — permanent learning
world_pulse.py      — market monitoring
reality_context.py  — ambient state
voice_engine.py     — STT + TTS
model_router.py     — multi-provider LLM routing

## Subdirectories
transport/    — transport layer (sessions, perception, execution)
substrate/    — internal re-exports (maps to transport/)
runtime/      — work_state.py, provider_state.py
interfaces/   — interface contracts (dormant)

## Conventions
- Import: sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")
- Context: load_context_from_env()
- DB: from runtime.db import get_conn
- Test: python3 -c "from runtime.X import Y"
- LLM: Gemini 2.5 Flash primary, Ollama fallback

## Cognitive loop injection order
1a. principle_engine
1b. domain layer
1c. behavioral context
1d. BIS venture context
1e. ambient reality
1f. primitive context
1g. template + evolution context
1h. hierarchy context (per agent)
