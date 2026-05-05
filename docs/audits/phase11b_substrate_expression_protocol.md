# Phase 11B — Substrate-Expression Protocol v1

**Date**: 2026-04-29
**Status**: Complete
**Test Results**: 36/36 pass (11B) + 14/14 pass (11C, fixed)

## What was built

The brain system — identity, expression, and coordination layer over
the shared UMH substrate. Brains are views/profiles, not databases.
Expression state (epigenetic config) shapes interpretation and planning
WITHOUT touching execution.

## Architecture

```
BrainProfile (frozen)     — identity, authority, primitives, scope
ExpressionState (mutable) — amplified/silenced concepts, pattern bias,
                            corrections, checkpoint versioning
BrainSignal (frozen)      — append-only inter-brain coordination
BrainContext (frozen)     — injection interface to intent/planning/decomposition
BrainRegistry             — in-memory store with thread safety
```

## Files created

| File | Purpose |
|---|---|
| `umh/brains/__init__.py` | Package exports |
| `umh/brains/profile.py` | BrainProfile + ExpressionState dataclasses |
| `umh/brains/registry.py` | Registry: CRUD, inheritance, default brains, singleton |
| `umh/brains/signals.py` | Append-only BrainSignal store |
| `umh/brains/context.py` | BrainContext builder + injection interface |
| `tests/unit/test_phase11b_brains.py` | 36 tests: profile, expression, registry, signals, boundary |
| `tests/unit/test_phase11c_brain_context.py` | 14 tests: context injection into intent/decomposition/planning |

## Files modified

| File | Change |
|---|---|
| `umh/control/api.py` | Added 6 brain endpoints |
| `umh/control/cli.py` | Added 5 brain CLI commands |
| `umh/intent/compiler.py` | Brain-weighted concept scoring |
| `umh/substrate/task_decomposition.py` | Brain pattern bias in role inference |
| `umh/planning/planner.py` | Brain context injection into plan objectives |

## Key design decisions

1. **Brains are views, not databases** — BrainProfile is frozen, ExpressionState is mutable.
   Corrections apply to expression state ONLY, never to canonical substrate.

2. **Weight clamping [0.0, 1.0]** — All concept/pattern weights are clamped to prevent
   runaway amplification/suppression.

3. **Checkpoint versioning** — ExpressionState.checkpoint_version increments on every
   mutation, enabling conflict detection and replay safety.

4. **Inheritance** — Child brains inherit parent expression state. resolve_with_inheritance
   merges parent+child: amplified/silenced concepts union, retrieval weights merge
   (child wins), primitives/patterns concatenate with dedup.

5. **Append-only signals** — BrainSignal is frozen. Once emitted, cannot be modified.
   Per-brain deques capped at 500, global at 5000.

6. **No execution coupling** — Brain modules import NOTHING from execution, adapters,
   or runtime. Boundary tests enforce this at the file level.

7. **Best-effort event publishing** — _publish() wraps event emission in try/except.
   Event bus failures never break core brain operations.

8. **AuthorityLevel enum** — Six levels: OBSERVE < ADVISE < PROPOSE < APPROVE < EXECUTE < ADMIN.
   Compatibility aliases map old names (GOVERNOR→ADMIN, EXECUTOR→EXECUTE, etc.).

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/brains` | List all registered brains |
| GET | `/brains/{id}` | Show profile + resolved (with inheritance) |
| GET | `/brains/{id}/expression` | Show expression state |
| GET | `/brains/{id}/children` | List direct children |
| GET | `/brain-signals` | List signals (optional brain_id, type filter) |
| POST | `/brains/{id}/correct` | Apply epigenetic correction |

## CLI commands

| Command | Description |
|---|---|
| `brains` | List all registered brains |
| `brain-show <id>` | Show brain profile with inheritance |
| `brain-expression <id>` | Show expression state |
| `brain-children <id>` | List children |
| `brain-signals` | List signals (--brain-id, --type filters) |

## Default brains

`ensure_default_brains()` creates four standard brains:
- **system** (ADMIN) — root brain
- **user** (APPROVE) — human operator
- **claude_code** (EXECUTE, parent: system) — developer agent
- **workstation** (OBSERVE, parent: system) — environment observer
- **project** (PROPOSE, parent: system) — optional, from project metadata

## Regression verification

- 36/36 Phase 11B tests pass
- 14/14 Phase 11C tests pass (fixed Signal/SignalBundle constructors + AuthorityLevel compat)
- 34/34 task decomposition tests pass
- 10/10 work_state tests pass
- All module imports clean
- No execution imports in brain modules (boundary test enforced)
