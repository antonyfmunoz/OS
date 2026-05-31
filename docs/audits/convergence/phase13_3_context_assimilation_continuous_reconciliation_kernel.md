# Phase 13.3 — Context Assimilation + Continuous Reconciliation Kernel

**Date:** 2026-05-30
**Phase:** 13.3
**Prerequisite:** Phase 13.2R (Native Agent Runtime Surface — Production Truth)
**Status:** COMPLETE

---

## Overview

Phase 13.3 builds UMH's ability to ingest fragmented context, diagnose what is canonical/outdated/contradictory/missing, propose canonical updates, and continuously reconcile new operator collaboration into the system without silently rewriting truth.

Three additional subsystems were added mid-build per operator correction:
1. **Device/Application Discovery Model** — UMH discovers operating environment
2. **Socratic Permission Engine** — asks before accessing/linking/reconciling
3. **Cross-Source Reconciliation Graph** — detects relationships across sources with confirmation

---

## Deliverables

### Models (13 modules)

| Module | Lines | Purpose |
|--------|-------|---------|
| `source_registry.py` | 231 | ContextSource, SourceType, SyncPolicy, Canonicality enums, SourceRegistry with JSONL dedup |
| `ingestion_job.py` | 259 | IngestionJob/IngestedItem, JobType/JobStatus enums, dual JSONL persistence |
| `context_diagnostic.py` | 227 | DiagnosticReport, CanonicalClaim, ContextContradiction, ContradictionType enum |
| `canonical_update.py` | 191 | CanonicalUpdateProposal (approval_required=True default), ProposalType/ProposalStatus enums |
| `reconciliation_session.py` | 234 | ReconciliationSession/Decision, SessionStatus/ReconciliationMode enums |
| `sync_policy.py` | 173 | ExternalSyncPolicy with evaluate_operation() dry-run, 5 policy enums |
| `environment_discovery.py` | 346 | DeviceEnvironment, FilesystemScope, ApplicationInventoryItem, triple JSONL |
| `permission_dialogue.py` | 394 | PermissionRequest/Preference, SocraticPermissionEngine with remember/revoke |
| `cross_source_reconciler.py` | 345 | CrossSourceSignal, detect/confirm/canonize pipeline, cleanup candidates |
| `context_ingestion_engine.py` | 450 | Seed sources, local audit/artifact ingestion, secret redaction, claim extraction |
| `diagnostic_engine.py` | 332 | Build diagnostic reports, detect contradictions/outdated/missing, entity map |
| `reconciliation_engine.py` | 265 | Full session lifecycle: start→attach→diagnose→propose→decide→approve→propagate |
| `dex_reconciliation.py` | 227 | Intent classifier (regex), operator input dispatch to reconciliation engine |

### API Surface

| File | Lines | Routes |
|------|-------|--------|
| `cockpit_context_assimilation_routes.py` | 551 | 15 GET (read-only) + 9 POST (operator auth) = 24 routes |
| `cockpit.py` | 2304 | Router mounted via `_mount_context_assimilation_router()` |
| `organism_bridge.py` | 2134 | 17 bridge action handlers in `_ACTIONS` dict |

### Data Files

| File | Purpose |
|------|---------|
| `entity_knowledge.json` | Instance-specific entity knowledge (loaded at runtime, not hardcoded) |
| `phase13_3_preflight.json` | 9/9 preflight checks pass |
| `phase13_3_test_gate_results.json` | 106 tests pass, 13 gates pass, 172 prior tests pass |
| 12 proof JSONs | Source registry, ingestion, diagnostic, reconciliation, sync policy, API, cockpit, lifecycle |

---

## Architecture Decisions

### Instance Context Law Compliance

The initial build hardcoded entity names (UMH, EOS, DEX, etc.) in substrate/ modules. The instance leak gate correctly flagged this. Fixed by:
- Extracting entity knowledge to `data/umh/context_assimilation/entity_knowledge.json`
- Engines load entity patterns, known entities, expected products/companies from data file at runtime
- Fallback to empty dicts when file missing (graceful degradation)
- No instance-specific strings remain in substrate/ code

### Reconciliation Mode Boundaries

- **Exploration mode**: No canonical changes possible. Safe for brainstorming.
- **Reconciliation mode**: Generates proposals. No auto-apply. Approval required.
- **Decision mode**: Operator explicitly approves/rejects proposals.
- **Query mode**: Read-only view of current understanding.

### Socratic Permission Model

- All filesystem scopes default to `permission_required=True, allowed=False`
- Blocked patterns: `.env`, `credentials`, `secret`, `private_key`, `token`
- Financial/personal sensitivity auto-requires permission for cross-source linking
- `to_dialogue()` renders Socratic questions for operator review
- `remember` feature saves preferences but `revoke` always works

### Data-Driven Entity Extraction

Entity patterns and claim patterns are loaded from `entity_knowledge.json` rather than compiled into substrate code. This means:
- Different UMH instances can have different entity knowledge
- Entity knowledge can be updated without code changes
- The diagnostic engine adapts to whatever entities are configured

---

## Safety Invariants Verified

| # | Invariant | Status |
|---|-----------|--------|
| 1 | No auto-apply — all proposals require approval | PASS |
| 2 | No external writes — sync policy enforces | PASS |
| 3 | Exploration creates no proposals | PASS |
| 4 | No silent canon mutation | PASS |
| 5 | Filesystem permission required by default | PASS |
| 6 | Sensitive cross-linking requires confirmation | PASS |
| 7 | Cadence remains dry_run_only | PASS |
| 8 | No raw secrets in diagnostic artifacts | PASS |
| 9 | No fake data in proofs | PASS |
| 10 | POST routes require operator auth | PASS |
| 11 | Path traversal blocked | PASS |
| 12 | Medium-risk execution blocked | PASS |

---

## Test Results

### Phase 13.3 Tests: 106/106 PASS

15 test classes across all models, engines, routes, security invariants:
- TestSourceRegistry (10), TestIngestionJob (6), TestContextIngestionEngine (7)
- TestContextDiagnostic (5), TestDiagnosticEngine (2), TestCanonicalUpdate (6)
- TestReconciliationSession (5), TestReconciliationEngine (8), TestDexReconciliation (8)
- TestEnvironmentDiscovery (8), TestPermissionDialogue (8), TestCrossSourceReconciler (6)
- TestSyncPolicy (7), TestAPIRoutes (6), TestCockpitShape (8), TestInvariants (6)

### Prior Phase Regression: 172/172 PASS

Phases 10.2, 10.3, 10.4, 10.5 — zero regressions.

### Gate Checks: 13/13 PASS

py_compile, type divergence, instance leak, dependency direction, line count, route auth, path traversal, no fake data, no raw secrets, cadence dry-run, no external write.

---

## Proof Artifacts

All proofs in `data/umh/context_assimilation/`:
- `phase13_3_preflight.json` — 13.2R prerequisite verified
- `phase13_3_source_registry_proof.json` — 6 sources, 330 claims, 9 entities
- `phase13_3_ingestion_engine_proof.json` — real ingestion against audit docs
- `phase13_3_instantiation_diagnostic_proof.json` — 88 items, 328 claims, 13 entities, 4 missing
- `phase13_3_diagnostic_report_proofs.json` — contradiction/outdated/missing detection
- `phase13_3_canonical_update_proof.json` — proposal lifecycle
- `phase13_3_reconciliation_engine_proof.json` — session lifecycle
- `phase13_3_main_lifecycle_proof.json` — full end-to-end, 319 proposals, dry_run=true
- `phase13_3_continuous_reconciliation_proofs.json` — 8 reconciliation scenarios
- `phase13_3_dex_reconciliation_integration.json` — intent classification
- `phase13_3_sync_policy_proof.json` — policy enforcement
- `phase13_3_api_verification.json` — route structure + auth
- `phase13_3_cockpit_verification.json` — cockpit mounting
- `phase13_3_test_gate_results.json` — final test/gate summary

---

## Conclusion

Phase 13.3 delivers a complete Context Assimilation + Continuous Reconciliation Kernel. UMH can now ingest fragmented context, diagnose its canonical truth state, propose updates requiring operator approval, discover operating environments with Socratic permission, and reconcile cross-source relationships — all without silently mutating canonical truth.

**Proof:** `data/umh/context_assimilation/phase13_3_test_gate_results.json`
