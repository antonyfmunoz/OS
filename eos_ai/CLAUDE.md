# eos_ai — Core AI modules

## Purpose
Brain of EOS. All intelligence lives here.

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

## Conventions
- Import: sys.path.insert(0, '/opt/OS')
- Context: load_context_from_env()
- DB: from eos_ai.db import get_conn
- Test: python3 -c "from eos_ai.X import Y"
- LLM: gemma3:4b fallback (Anthropic depleted)

## Cognitive loop injection order
1a. principle_engine
1b. domain layer
1c. behavioral context
1d. BIS venture context
1e. ambient reality
1f. primitive context
1g. template + evolution context
1h. hierarchy context (per agent)
