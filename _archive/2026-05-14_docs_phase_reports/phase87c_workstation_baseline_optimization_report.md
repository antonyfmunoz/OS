# Phase 87C — Local Workstation Baseline + Device Literacy + Optimization Readiness v1

**Date**: 2026-05-03
**Status**: Complete
**Phase type**: Advisory/planning only — no real device scanning, no execution, no deletion

---

## Objective

Create the workstation optimization planning layer for UMH onboarding. When a new user instance boots for the first time, EOS needs to understand the local machine's state — storage, apps, startup items, developer environment, thermals, backups — and produce intelligent optimization recommendations with full safety guardrails.

Phase 87C builds the contracts, models, policies, views, and safety enforcement. No real device is scanned. No action is executed. Everything is advisory.

---

## What Was Built

### Module: `umh/workstation_optimization/` (12 files)

| File | Purpose | Lines |
|------|---------|-------|
| `__init__.py` | Package marker | 5 |
| `contracts.py` | 8 enums, 8 normalizers, 6 dataclasses with serialization | ~380 |
| `baseline.py` | 23 default baseline categories, blocked observations, plan builder | ~130 |
| `device_literacy.py` | 11 plain-language explanations across all device areas | ~300 |
| `storage_model.py` | File classification → action/approval/risk mapping (13 classifications) | ~100 |
| `app_process_model.py` | App and process classification using keyword heuristics | ~120 |
| `developer_environment.py` | 13 developer cleanup categories with classification and recommendations | ~110 |
| `performance_tuning.py` | 11 tuning categories with risk/approval/rollback/stability gates | ~180 |
| `recommendations.py` | 7 onboarding optimization recommendations + full report builder | ~100 |
| `approval_policy.py` | Destructive action approval matrix (4 action sets, 5 policy functions) | ~90 |
| `views.py` | 8 UI-safe view dataclasses, 7 converter functions | ~140 |
| `safety.py` | AST-based safety enforcement (forbidden imports, execution patterns, system calls) | ~140 |

### Test file

| File | Tests | Status |
|------|-------|--------|
| `tests/test_phase87c_workstation_baseline_optimization.py` | 138 | All passing |

### Test classes

| Class | Tests | Coverage |
|-------|-------|----------|
| TestContractNormalizers | 9 | All 8 normalizers + UNKNOWN degradation |
| TestContractSerialization | 6 | All 6 dataclass roundtrips |
| TestBaseline | 19 | 16 device areas + planning mode + blocked observations |
| TestDeviceLiteracy | 10 | 11 explanations + required fields |
| TestStorageModel | 10 | All 13 file classifications + action mapping + policy |
| TestAppProcessModel | 9 | Security/system/bloat classification + process + app policies |
| TestDeveloperEnvironment | 12 | 13 categories + classification + recommendations + bloat sources |
| TestPerformanceTuning | 16 | 11 categories + overclocking policy + safe first steps + advisory risk |
| TestRecommendationsApproval | 14 | 7 recommendations + approval matrix + rollback/verification requirements |
| TestViews | 7 | All view converters + dashboard builder |
| TestSafety | 15 | Module safety scan + forbidden import detection + execution pattern detection + secret detection |
| TestDocUpdates | 6 | Strategy doc doctrine presence verification |
| TestRegression | 4 | Phase 86/87/87A/87B import verification |

---

## Contracts Summary

### Enums (8)

| Enum | Values | Purpose |
|------|--------|---------|
| DeviceArea | 24 | Every area of a workstation that can be audited |
| WorkstationAuditMode | 7 | Planning-only, read-only, interactive, full audit, etc. |
| OptimizationActionType | 20 | Every action type from explain to overclock |
| OptimizationRiskLevel | 6 | None through critical + unknown |
| OptimizationApprovalRequirement | 8 | None through expert review + unknown |
| OptimizationReversibility | 6 | Fully reversible through irreversible + unknown |
| FileClassification | 13 | System-critical through unknown |
| PerformanceTuningCategory | 12 | CPU/GPU/memory/thermal/power/BIOS/fan/driver/network/storage/display + unknown |

### Dataclasses (6)

| Dataclass | Key fields |
|-----------|-----------|
| DeviceBaselineCategory | area, audit_mode, default_risk, planning_only_notes |
| WorkstationBaselinePlan | categories, blocked_observations, audit_mode |
| OptimizationCandidate | action_type, risk_level, approval_required, reversibility, rollback_plan_required |
| DeviceLiteracyExplanation | plain_language_summary, why_it_matters, what_good_looks_like, common_failure_modes |
| PerformanceTuningAdvisory | approval_required, stability_testing_required, rollback_plan_available |
| WorkstationOptimizationReport | baseline_plan, device_literacy_items, optimization_candidates, high_risk_items, preserved_items |

---

## Safety Architecture

### 21 Hard Rules (all enforced)

1. No subprocess, shutil.rmtree, pathlib unlink/rmdir
2. No requests, httpx, socket, selenium, playwright
3. No adapter, execution engine, storage mutation, governance mutation
4. No memory promotion
5. No package manager commands
6. No live model calls
7. No credential values
8. No real file scanning
9. No real process listing
10. No real disk usage
11. No actual cleanup/deletion
12. No actual settings changes
13. No actual overclocking/undervolting
14. No network operations
15. No browser automation
16. No Docker commands
17. No system service management
18. No registry/settings modification
19. No BIOS/UEFI changes
20. No fan curve changes
21. No driver installation

### AST Safety Scanner

- **Forbidden imports** (12): subprocess, requests, httpx, aiohttp, socket, selenium, playwright, smtplib, paramiko, scrapy, bs4, shutil
- **Forbidden module prefixes** (5): umh.adapters, umh.execution, umh.governance, umh.memory, umh.storage
- **Execution patterns** (17): execute, run_action, send_message, promote_memory, scrape, ingest, fetch, crawl, download, unlink, rmtree, rmdir, remove, kill, terminate, uninstall
- **System call patterns** (5): subprocess.run, subprocess.call, subprocess.Popen, shutil.rmtree, shutil.move
- **Secret patterns** (1): load_dotenv
- **Vacuous truth guard**: 0 modules scanned = not safe

### Scan result

```
modules_checked: 11
total_violations: 0
all_safe: true
```

---

## Doctrines Added (4)

| Doctrine | Summary |
|----------|---------|
| Local Workstation Onboarding Doctrine | Workstation baseline audit is part of onboarding — not optional later maintenance |
| Device Literacy Doctrine | Users receive plain-language explanations before any optimization is recommended |
| Performance Tuning Safety Doctrine | Overclocking/undervolting/BIOS/fan/driver require explicit approval + expert review + stability testing + rollback plan |
| Destructive Action Approval Doctrine | Unknown = preserve, sensitive = preserve, system-critical = preserve, credential = preserve, user-created = review, generated/cache/temp = cleanup candidate with approval |

---

## Strategy Docs Updated

| Document | Change |
|----------|--------|
| `docs/strategy/current_doctrine_index.md` | Added "Workstation Optimization Doctrines (Phase 87C)" section with 4 doctrines |
| `docs/strategy/source_ingestion_map.md` | Added "Local Workstation Baseline" section with 8 source types + governing doctrines |
| `docs/strategy/war_sprint_context_manifest.md` | Added Phase 87C to phase status, read order #18, 4 doctrines to end-state list |

---

## Regression Status

| Phase | Tests | Status |
|-------|-------|--------|
| 86 — Tomorrow Operating Loop v1 | 81 | Passing |
| 87 — Leverage + Resource/Tool Taxonomy v1 | 118 | Passing |
| 87A — Distributed Node Registry v1 | 146 | Passing |
| 87B — Onboarding Context Ingestion v1 | 164 | Passing |
| 87C — Workstation Baseline Optimization v1 | 138 | Passing |

**Total tests across Phases 86–87C: 647**

---

## What Phase 87C Does NOT Do

- Does not scan any real device
- Does not read disk usage, process lists, or installed apps
- Does not delete, move, or modify any files
- Does not kill any processes
- Does not change any settings
- Does not overclock, undervolt, or modify fan curves
- Does not install or uninstall anything
- Does not access network, browser, or credentials
- Does not connect to any external service
- Does not execute any optimization action

All of the above are future-phase capabilities that will build on Phase 87C contracts and models.

---

## Next Steps (Future Phases)

1. Real device baseline audit using OS APIs (read-only first)
2. Personalized optimization recommendations from real audit data
3. Governed execution for approved cleanup actions
4. Stability testing framework for performance tuning
5. Rollback/backup verification before destructive actions
6. Integration with distributed node registry (Phase 87A) for multi-device baseline
