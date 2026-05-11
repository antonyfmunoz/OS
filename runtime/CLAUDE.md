# runtime — Runtime Intelligence Layer

## Identity
This is the UMH runtime intelligence layer.
The canonical transport subsystem lives here at
`runtime/transport/`. The shim layer at `eos_ai/substrate/` routes
to transport for backward compatibility.

The `eos_ai/` directory is a shim layer that re-exports from `runtime/`.
All new code should import from `runtime.*` directly.

## Purpose
Core intelligence substrate. All runtime AI lives here:
LLM routing, memory persistence, cognitive loop, agent hierarchy,
voice pipeline, and the canonical transport subsystem.

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
transport/    — canonical transport (sessions, perception, execution)
substrate/    — shim layer (re-exports from transport/)
runtime/      — work_state.py (CONFIRMED_RUNTIME)
interfaces/   — interface contracts (dormant)
platforms/eos/ — EOS platform prototype (dormant)

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
