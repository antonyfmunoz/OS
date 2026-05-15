# Current-to-Canonical Directory Map

> Phase 96.8BJ — 2026-05-09
> Maps every current directory to its canonical target destination

---

## Legend

| Priority | Meaning |
|----------|---------|
| P0 | This phase (classification, README, docs only) |
| P1 | Stage 1 — safe cleanup, archive moves |
| P2 | Stage 2 — substrate package introduction with compatibility shims |
| P3 | Stage 3+ — full migration, requires runtime testing |

| Risk | Meaning |
|------|---------|
| LOW | No runtime imports, safe to move/classify |
| MEDIUM | Has imports but can be shimmed |
| HIGH | Active runtime entrypoint, breaks services if moved |

---

## Directory Mapping

### services/
| Current | Purpose | Runtime Status | Target | Priority | Risk | Immediate | Deferred |
|---------|---------|----------------|--------|----------|------|-----------|----------|
| `services/discord_bot.py` | Primary runtime entrypoint | CONFIRMED_RUNTIME | `services/discord_bot.py` (stays) | — | HIGH | No change | No change |
| `services/handlers/` | Discord command handlers | CONFIRMED_RUNTIME | `interfaces/discord/handlers/` or stay | P3 | HIGH | No change | Migrate with compatibility shim |
| `services/__pycache__/` | Cache | N/A | Delete on cleanup | P1 | LOW | — | Delete |

### eos_ai/
| Current | Purpose | Runtime Status | Target | Priority | Risk | Immediate | Deferred |
|---------|---------|----------------|--------|----------|------|-----------|----------|
| `eos_ai/*.py` (gateway, context, memory, etc.) | Core runtime modules | CONFIRMED_RUNTIME | `substrate/*` (staged) | P2 | HIGH | Add README_STATUS.md | Staged migration with shims |
| `eos_ai/substrate/` | Substrate subsystem (voice, transport, events) | PARTIALLY_VERIFIED | `substrate/` (merge) | P2 | MEDIUM | Classify | Staged migration |
| `eos_ai/runtime/` | Runtime state (work_state.py) | CONFIRMED_RUNTIME | `substrate/execution/` | P3 | HIGH | No change | Migrate with shim |
| `eos_ai/interfaces/` | Interface contracts | DORMANT | `interfaces/` | P2 | LOW | Classify | Move |
| `eos_ai/platforms/eos/` | EOS platform prototype | DORMANT | `platforms/eos/` | P3 | LOW | Add README_STATUS.md | Move when ready |
| `eos_ai/.substrate_sandbox/` | Sandbox artifacts | DORMANT | `archive/experiments/` | P1 | LOW | — | Archive |
| `eos_ai/.substrate_station/` | Station artifacts | DORMANT | `archive/experiments/` | P1 | LOW | — | Archive |

### core/
| Current | Purpose | Runtime Status | Target | Priority | Risk | Immediate | Deferred |
|---------|---------|----------------|--------|----------|------|-----------|----------|
| `core/adapters/` | Ingestion bridge, decomposer, candidate gen | CANONICAL_SUBSTRATE | `substrate/adapters/` or `substrate/decomposition/` | P2 | MEDIUM | Classify | Staged migration |
| `core/memory/` | Canonical memory store | CANONICAL_SUBSTRATE | `substrate/memory/` | P2 | MEDIUM | Classify | Staged migration |
| `core/ontology/` | Primitive type definitions | CANONICAL_SUBSTRATE | `substrate/ontology/` | P2 | MEDIUM | Classify | Staged migration |
| `core/registry/` | Adapter/capability registry | PARTIALLY_VERIFIED | `substrate/registries/` | P2 | MEDIUM | Classify | Staged migration |
| `core/control_plane_router/` | Control plane routing | PARTIALLY_VERIFIED | `substrate/control_plane/` | P2 | MEDIUM | Classify | Staged migration |
| `core/workstation/` | Workstation relay + constitutional reports | MIXED | `substrate/workstation/` (relay) + reclassify reports | P2 | MEDIUM | Add README_STATUS.md | Split relay vs reports |
| `core/execution/` | Execution contracts | PARTIALLY_VERIFIED | `substrate/execution/` | P2 | MEDIUM | Classify | Staged migration |
| `core/governance/` | Governance contracts | PARTIALLY_VERIFIED | `substrate/governance/` | P2 | MEDIUM | Classify | Staged migration |
| `core/world_model/` | World model candidates | PARTIALLY_VERIFIED | `substrate/world_model/` | P2 | LOW | Classify | Staged migration |
| `core/interpretation/` | Interpretation engine | PARTIALLY_VERIFIED | `substrate/interpretation/` | P2 | LOW | Classify | Staged migration |
| `core/planning/` | Planning modules | PARTIALLY_VERIFIED | `substrate/planning/` | P2 | LOW | Classify | Staged migration |
| `core/state/` | State management | PARTIALLY_VERIFIED | `substrate/execution/` | P2 | LOW | Classify | Staged migration |
| `core/security/` | Security/redaction | PARTIALLY_VERIFIED | `substrate/security/` | P2 | LOW | Classify | Staged migration |
| `core/adapter_engine/` | Adapter generation | FOUNDATION | `substrate/adapters/` | P2 | LOW | Classify | Staged migration |
| `core/adapter_package_manager/` | Adapter package management | FOUNDATION | `substrate/adapters/` | P2 | LOW | Classify | Staged migration |
| `core/environment_bridge/` | Environment bootstrap | PARTIALLY_VERIFIED | `substrate/environments/` | P2 | LOW | Classify | Staged migration |
| `core/action_system/` | Action planning | PARTIALLY_VERIFIED | `substrate/planning/` | P2 | LOW | Classify | Staged migration |
| `core/actuation/` | Physical actuation | PARTIALLY_VERIFIED | `substrate/execution/` | P2 | LOW | Classify | Staged migration |
| `core/coherence/` | Coherence validation | PROOF_ONLY | `substrate/quality/` | P2 | LOW | Classify | Staged migration |
| `core/connectors/` | External connectors | PARTIALLY_VERIFIED | `substrate/adapters/` | P2 | LOW | Classify | Staged migration |
| `core/domain/` | Domain models | PARTIALLY_VERIFIED | `substrate/ontology/` | P2 | LOW | Classify | Staged migration |
| `core/mastery_engine/` | Tool mastery | PARTIALLY_VERIFIED | `substrate/learning/` | P2 | LOW | Classify | Staged migration |
| `core/orchestrator/` | Orchestration | PARTIALLY_VERIFIED | `substrate/control_plane/` | P2 | LOW | Classify | Staged migration |
| `core/runtime/` | Runtime contracts | PARTIALLY_VERIFIED | `substrate/execution/` | P2 | LOW | Classify | Staged migration |
| `core/tool_mastery_*/` | TME agents/managers | PARTIALLY_VERIFIED | `substrate/learning/` | P2 | LOW | Classify | Staged migration |

### umh/
| Current | Purpose | Runtime Status | Target | Priority | Risk | Immediate | Deferred |
|---------|---------|----------------|--------|----------|------|-----------|----------|
| `umh/` (all 870 files) | Prior UMH architecture | DORMANT_REFERENCE | Stay in place with status marker OR `archive/dormant_reference/umh/` | P0 | LOW | Add README_STATUS.md | Archive when substrate is mature |

### Other Directories
| Current | Purpose | Runtime Status | Target | Priority | Risk | Immediate | Deferred |
|---------|---------|----------------|--------|----------|------|-----------|----------|
| `scripts/` | Operator scripts, smoke tests | MIXED | `scripts/` (curate) | P1 | LOW | Consolidation plan | Remove duplicates |
| `tools/` | Duplicate of scripts subset | DUPLICATE | Compare with scripts, archive duplicates | P1 | LOW | Consolidation plan | Archive duplicates |
| `tests/` | Test suite (300+ files) | MIXED | `tests/active/`, `tests/legacy/` | P1 | LOW | Classification plan | Reorganize |
| `data/` | Runtime artifacts, ingestion data | ACTIVE | `data/` (restructure internally) | P1 | LOW | — | Reorganize subdirs |
| `docs/` | System documentation | ACTIVE | `docs/` (add subdirs) | P0 | LOW | Add structure | — |
| `skills/` | CC skill library | ACTIVE | `skills/` (stays) | — | LOW | No change | — |
| `agents/` | Agent soul documents | ACTIVE | `agents/` (stays) | — | LOW | No change | — |
| `config/` | Configuration | ACTIVE | `config/` (stays) | — | LOW | No change | — |
| `10_Wiki/` | Obsidian vault | ACTIVE | `10_Wiki/` (stays) | — | LOW | No change | — |
| `saas/` | SaaS product (TypeScript/React) | SEPARATE_APP | `platforms/eos/saas/` or separate repo | P3 | LOW | Classify | Decision needed |
| `frontend/` | Frontend assets | UNKNOWN | Classify | P1 | LOW | Inspect | Archive if unused |
| `products/` | Product docs | REFERENCE | `docs/products/` or stay | P1 | LOW | Classify | — |
| `ventures/` | Venture docs | REFERENCE | `docs/ventures/` or stay | P1 | LOW | Classify | — |
| `knowledge/` | Domain knowledge | REFERENCE | `10_Wiki/` merge or stay | P1 | LOW | Classify | — |
| `templates/` | Templates | ACTIVE | `templates/` (stays) | — | LOW | No change | — |
| `orchestrator/` | Orchestration scripts | PARTIALLY_VERIFIED | `scripts/` merge | P1 | LOW | Classify | Merge |
| `parsers/` | Parser utilities | UNKNOWN | Classify | P1 | LOW | Inspect | — |
| `runtime/` | Additional runtime | UNKNOWN | Classify | P1 | LOW | Inspect | — |
| `backups/` | Old backups | ARCHIVE_CANDIDATE | `archive/stale_backups/` | P1 | LOW | — | Move |
| `logs/` | Log files | EPHEMERAL | `data/logs/` or stay | P1 | LOW | — | — |
| `vault/` | Obsidian vault mirror | REFERENCE | Merge with `10_Wiki/` or stay | P1 | LOW | Classify | — |

---

## Summary Statistics

| Classification | Count |
|---------------|-------|
| No change needed | 6 (services, skills, agents, config, 10_Wiki, templates) |
| P0 — This phase (docs/README only) | 4 (umh, eos_ai, core, docs) |
| P1 — Safe cleanup | 12 (scripts, tools, tests, data, frontend, etc.) |
| P2 — Substrate introduction | 20+ (eos_ai/*, core/* modules) |
| P3 — Full migration | 5 (services/handlers, eos_ai/runtime, platforms, saas) |
