# Architecture Wording Correction — Post-R8h

> Date: 2026-05-12
> Scope: Canonical directory roles and ownership labels

---

## Problem

Pre-migration documentation described UMH as having a "substrate" containing
a separate "intelligence runtime," implying two nested layers:

```
UMH substrate
└── intelligence runtime (eos_ai/)
```

This was architecturally incorrect. UMH has ONE runtime layer, not a
substrate containing a secondary runtime.

## Correction

The canonical architecture model is:

```
UMH/
├── core/       = substrate contracts, primitives, invariants, governance foundations
├── runtime/    = single live runtime (cognition, execution, memory, transport)
├── services/   = daemons and interfaces that call runtime
├── scripts/    = operator tooling
└── platforms/  = EOS, LyfeOS, CreatorOS projections (not owners)
```

### Role Definitions

| Directory | Role | NOT |
|-----------|------|-----|
| core/ | Contracts, foundations, invariants | Not live execution |
| runtime/ | The single runtime — all live AI | Not a sub-layer of core/ |
| services/ | Daemons that call runtime | Not independent logic |
| scripts/ | Operator tooling | Not runtime code |

### Key Distinctions

- `core/` defines WHAT the system promises (contracts, convergence engines, governance)
- `runtime/` implements HOW those promises are fulfilled (LLM dispatch, memory, cognitive loop)
- `services/` provides WHERE users interact (Discord bot, webhooks, Telegram)
- `scripts/` provides WHEN things run (cron, scheduled tasks, operator utilities)

### What Changed

| File | Old | New |
|------|-----|-----|
| core/convergence/filesystem_integrity_engine_v1.py | `"core": "substrate"`, `"runtime": "intelligence"`, `"services": "runtime"` | `"core": "contracts"`, `"runtime": "execution"`, `"services": "daemons"` |
| runtime/CLAUDE.md | "Runtime Intelligence Layer", "Core intelligence substrate" | "UMH Runtime", "Live cognition and execution machinery" |
| .claude/CLAUDE.md | "canonical substrate + infrastructure contracts", "canonical runtime intelligence layer" | "substrate contracts, primitives, invariants, governance foundations", "single live runtime" |
