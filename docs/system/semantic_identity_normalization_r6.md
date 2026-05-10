# Semantic Identity Normalization — R6 Report

> Phase: 96.8CO — 2026-05-10
> Commit: root-migration-r6
> Type: Documentation/identity convergence wave

---

## Objective

Normalize project identity from OS/EOS-centric language toward
UMH/substrate language across canonical documentation and status files.

## What Changed

### Identity Normalization

| Document | Change |
|----------|--------|
| `CLAUDE.md` | Developer Agent identity: "for EOS" → "for UMH" |
| `CLAUDE.md` | "EOS protocols" → "UMH protocols" |
| `CLAUDE.md` | "EOS conventions" → "UMH conventions" |
| `CLAUDE.md` | "Never do inside EOS" → "Never do inside UMH" |
| `CLAUDE.md` | "EOS compounds" → "UMH compounds" |
| `CLAUDE.md` | "EOS has a five-layer..." → "UMH has a five-layer..." |
| `CLAUDE.md` | "Boris Cherny (Applied to EOS)" → "(Applied to UMH)" |
| `.claude/CLAUDE.md` | "Developer Agent for EOS" → "for UMH" |
| `.claude/CLAUDE.md` | "EntrepreneurOS is a production AI business OS" → "UMH is a production AI intelligence substrate" |
| `.claude/CLAUDE.md` | Project structure updated with layer labels |
| `README.md` | "EntrepreneurOS" → "UMH — Universal Mastery Hierarchy" |
| `README.md` | Structure section updated with canonical layer names |
| `eos_ai/CLAUDE.md` | Complete rewrite: identity, purpose, subdirectories, rename plan |
| `eos_ai/README_STATUS.md` | Updated with UMH identity, rename recommendation |
| `core/README_STATUS.md` | Updated with canonical substrate identity, relationship to eos_ai/ |
| `services/CLAUDE.md` | Updated: "Live Entrypoints", UMH interface identity |
| `docs/system/current_system_status.md` | Header: system identity block, directory architecture table |

### Clarified Relationships

| Concept | Canonical Definition |
|---------|---------------------|
| **UMH** | The governed intelligence substrate — top-level system identity |
| **substrate** | The runtime implementation layer of UMH |
| **EOS** | EntrepreneurOS — one application projection, not the system owner |
| **core/** | Canonical substrate contracts + infrastructure |
| **eos_ai/** | Runtime intelligence layer (legacy name, pending rename) |
| **eos_ai/transport/** | Canonical transport subsystem |
| **eos_ai/substrate/** | Shim layer → re-exports from transport/ |
| **services/** | Live entrypoints (daemon processes) |
| **scripts/** | Operations layer (cron scripts, utilities) |

## OS/EOS Naming Drift Report

### Remaining EOS-ownership language (intentionally preserved)

| Location | Text | Reason |
|----------|------|--------|
| `ARCHITECTURE.md` header | "AgentOS — Architecture" | Historical document, large rewrite out of scope |
| `PHILOSOPHY.md` | EOS references throughout | Philosophical document, historically authored |
| `PROTOCOLS.md` | EOS protocol layers | Protocol document, tight coupling to existing system |
| `agents/*.md` | "EOS" in agent soul docs | Per R6 scope: agents not targeted |
| Docker container names | `os-discord`, `os-bot` etc. | Deployment identity, changed in R7+ |
| Git branch name | `main` | No change needed |
| Repository path | `/opt/OS` | Physical rename deferred to R7+ |
| `eos_ai/` directory name | Legacy name | Rename blocked on import migration |
| Service env vars | `EOS_ROUTER_*`, `EOS_DISCORD_*` | Env var rename is deployment concern |

### EOS references converted to UMH

| Pattern | Count | Status |
|---------|-------|--------|
| "Developer Agent for EOS" | 2 | Converted |
| "EOS protocols" | 1 | Converted |
| "EOS conventions" | 1 | Converted |
| "EOS compounds" | 1 | Converted |
| "EntrepreneurOS is a production AI..." | 2 | Converted |
| "Inside EOS" | 1 | Converted |
| "Applied to EOS" | 1 | Converted |
| "Brain of EOS" (eos_ai/CLAUDE.md) | 1 | Converted |

## Future Rename Recommendation: eos_ai/

### Target
`umh_runtime/` (preferred) or `substrate/`

### Rationale
The name `eos_ai` conflates an application (EOS) with the substrate (UMH).
`eos_ai/` contains the universal intelligence layer — LLM routing, memory,
cognitive loop, transport — none of which is EOS-specific.

### Strategy
1. Create `umh_runtime/__init__.py` with re-exports from eos_ai
2. Migrate external imports gradually (services/, scripts/, tests/)
3. Keep `eos_ai/__init__.py` as compatibility shim for transition period
4. Remove shim after all imports migrated

### Blockers
- 200+ import sites across the codebase
- Docker PYTHONPATH=/app assumption
- 30 crontab entries referencing eos_ai paths
- Physical rename /opt/OS → /opt/UMH should happen first
- Timeline: post-R7

### Why not `substrate/`
`substrate/` conflicts with the existing `eos_ai/substrate/` shim layer
and the conceptual distinction between "substrate" (the architecture)
and "runtime" (the executing code). `umh_runtime/` is unambiguous.

## Root Migration Readiness Matrix (Updated)

| Wave | Status | Files | Regressions |
|------|--------|-------|-------------|
| R1 — UMH_ROOT env chain | Complete | core/paths.py + env setup | 0 |
| R2 — Runtime bootstrap | Complete | 193 files | 0 |
| R3 — Runtime filesystem refs | Complete | 154 files | 0 |
| R4 — Test topology | Complete | 179 files | 0 |
| R5 — Deployment infrastructure | Complete | 27 files | 0 |
| R6 — Semantic identity (this) | Complete | 8 docs | 0 (no code changes) |
| R7 — Physical rename prep | Not started | — | — |

### Physical Rename Readiness: READY WITH COORDINATION

All code paths use env chain abstraction. Docker compose uses
`${UMH_ROOT:-/opt/OS}` with fallback. Shell scripts use same pattern.
Physical rename requires:
1. Set UMH_ROOT=/opt/UMH in environment
2. Update 30 crontab entries (sed one-liner)
3. Update core/paths.py _FALLBACK
4. Create /opt/OS → /opt/UMH symlink for transition
5. Docker restart (~5 seconds downtime)

## Validation

| Check | Result |
|---|---|
| Code behavior changes | None (docs only) |
| Git diff scope | 8 documentation files only |
| Core imports | Clean |
| Discord bot import | Clean |
| Test suite | Not re-run (no code changes) |

## Rollback

```bash
git revert <R6-commit-hash>
```
