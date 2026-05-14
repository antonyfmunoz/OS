# Phase 96.8BJ — Canonical Repo Convergence and Drift Elimination

> Generated: 2026-05-09
> Executor: Developer Agent (Claude Code)
> Baseline commit: 10b441ed702837b16d52971161faa9a3a82d6f95

---

## Executive Summary

Phase 96.8BJ establishes conceptual coherence across the /opt/OS repository.
Before this phase, the repo had three parallel architectures (`umh/`, `eos_ai/`, `core/`),
inconsistent terminology, 140+ duplicate files between `scripts/` and `tools/`,
12 report generators misclassified as "engines," and no documented migration path.

This phase:
- Locked canonical terminology (32 terms with allowed/disallowed usage)
- Defined canonical directory architecture (target state)
- Mapped every current directory to its canonical destination
- Built a machine-readable classification index (44 entries, JSON-validated)
- Documented the actual runtime spine vs target runtime spine
- Classified all constitutional modules as REPORT_GENERATORS
- Created README_STATUS.md for 6 key directories
- Established anti-drift governance rules (10 mandatory rules)
- Created a 7-stage migration plan

**No code was moved. No runtime was affected. No imports changed.**
This phase is pure truth-establishment and classification.

---

## Current Drift Diagnosis

### Three parallel architectures
| Directory | Files | Runtime Imports | Status |
|-----------|-------|----------------|--------|
| `eos_ai/` | 292 .py | YES (Discord bot) | ACTIVE_RUNTIME_LEGACY_NAME |
| `core/` | 238 .py | PARTIAL (handlers) | PARTIAL_CANONICAL_SUBSTRATE |
| `umh/` | 870 .py | ZERO | DORMANT_REFERENCE |

### scripts/ vs tools/ duplication
- 140+ Python files exist in both directories with identical filenames
- Only 16 files unique to `tools/`
- Root cause: multi-chat drift — different sessions created files in different locations

### Report generator misclassification
- 12 modules in `core/workstation/` named `*_engine_v1.py`
- All generate reports/analysis — none gate runtime execution
- Previously classified as "governance engines" — now reclassified as REPORT_GENERATORS

### Ingestion fragmentation
- `eos_ai/gws_scanner.py` writes directly to `data/` (bypasses substrate)
- `core/adapters/` bridge pipeline works but not wired to bot commands
- Memory split: `eos_ai.memory` (Neon) vs `canonical_memory_store` (JSONL)

---

## Canonical Terminology

See `docs/system/canonical_terminology.md` for full definitions.

Key terms locked:
- **substrate** = runtime implementation of UMH
- **report generator** = analysis module that does NOT enforce (not "engine")
- **bridge** = temporary translation layer (must have migration destination)
- **canonical** = governance-approved version of truth
- **dormant reference** = architecturally valuable code not in active runtime
- **adapter** = typed bridge to external system (not "capability")
- **capability** = tool-independent abstract action
- **proof artifact** = structured evidence from real execution (not example data)

---

## Canonical Directory Architecture

See `docs/system/canonical_directory_architecture.md` for full target.

Target top-level:
```
services/       — daemon entrypoints only
substrate/      — canonical UMH substrate runtime
interfaces/     — user-facing surfaces (Discord, CLI, voice)
platforms/      — product layers (EOS, CreatorOS)
data/           — runtime artifacts, memory, proofs
docs/           — system documentation
skills/         — CC skill library
scripts/        — operator scripts
tests/          — test suite
archive/        — dormant/deprecated code
```

---

## Deliverables Created

### Terminology & Architecture
| File | Task |
|------|------|
| `docs/system/canonical_terminology.md` | 32 terms with usage rules |
| `docs/system/canonical_directory_architecture.md` | Target directory structure |
| `docs/system/naming_conventions.md` | File/package naming rules |

### Mapping & Classification
| File | Task |
|------|------|
| `docs/system/current_to_canonical_directory_map.md` | Every directory mapped |
| `data/system/canonical_repo_classification_index.json` | 44 entries, JSON-validated |
| `docs/system/current_canonical_runtime_spine.md` | Actual vs target runtime |

### Status Classification
| File | Task |
|------|------|
| `umh/README_STATUS.md` | DORMANT_REFERENCE_ARCHITECTURE |
| `docs/system/umh_dormant_reference_status.md` | Detailed /umh status |
| `eos_ai/README_STATUS.md` | ACTIVE_RUNTIME_LEGACY_NAME |
| `core/README_STATUS.md` | PARTIAL_CANONICAL_SUBSTRATE_AND_PROOF_LAYER |
| `core/workstation/README_STATUS.md` | MIXED (relay + report generators) |
| `eos_ai/platforms/eos/README_STATUS.md` | DORMANT_PLATFORM_PROTOTYPE |

### Strategy & Convergence
| File | Task |
|------|------|
| `docs/system/canonical_ingestion_convergence_path.md` | Ingestion pipeline path |
| `docs/system/adapter_maturity_compounding_strategy.md` | Adapter maturity loop |
| `docs/system/staged_convergence_migration_plan.md` | 7-stage migration plan |

### Plans & Rules
| File | Task |
|------|------|
| `docs/system/scripts_tools_consolidation_plan.md` | 140+ duplicates mapped |
| `docs/system/test_suite_classification_plan.md` | 300+ tests classified |
| `docs/system/anti_drift_governance_rules.md` | 10 mandatory rules |
| `docs/system/current_system_status.md` | What's proven/partial/dormant/next |

### Safe Moves Performed
| Action | Risk |
|--------|------|
| `backups/eos_backup_20260326.tar.gz` → `archive/stale_backups/` | LOW |
| Created `docs/migrations/` directory | LOW |
| Created `data/system/` directory | LOW |

---

## Runtime Compatibility

| Check | Result |
|-------|--------|
| Discord bot imports unchanged | YES |
| eos_ai/ modules unchanged | YES |
| core/ modules unchanged | YES |
| handlers/ unchanged | YES |
| No Python files modified | YES (only new files created) |
| No imports changed | YES |
| No services restarted | YES |

---

## Ingestion Convergence Implications

This phase clarifies that the ingestion pipeline from Phase 96.8BJ-prior
(bridge → decomposer → candidate gen → memory store) is the canonical path.

Rules established:
1. No new ingestion framework — extend the existing pipeline
2. All ingestion targets canonical memory store
3. Scanner remains at `eos_ai/gws_scanner.py` until `substrate/adapters/` exists
4. Adapter maturity loop incorporated after batch ingestion

---

## Anti-Drift Enforcement

10 rules established in `docs/system/anti_drift_governance_rules.md`:
1. Every new module must declare canonical layer
2. Every new adapter must have capability contract
3. Every proof must specify source and whether simulated/real
4. Every report generator must say it does not enforce
5. Every bridge must have a migration destination
6. No new parallel architecture without explicit approval
7. All ingestion must target canonical memory
8. Platforms cannot own substrate intelligence
9. Current reality docs updated after every major phase
10. All new names must follow naming conventions

---

## Next Three Phases

### 96.8BK — SAFE_DIRECTORY_CLEANUP_AND_COMPATIBILITY_SHIMS
- Consolidate scripts/tools (eliminate 140+ duplicates)
- Classify test suite (300+ files)
- Archive stale/deprecated code
- Organize data/ structure

### 96.8BL — CONNECT_GWS_SCANNER_TO_CANONICAL_SUBSTRATE_INGESTION
- Batch process all 22+ real documents
- Wire !ingest-real-doc into bot commands
- Add query commands

### 96.8BM — CANONICAL_MEMORY_STORE_AND_NEON_MIGRATION
- JSONL → Neon migration
- Cross-session queryability
- Memory reconciliation
