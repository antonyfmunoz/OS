# Phase 85 — Deliberation Council System v1

**Date**: 2026-05-03
**Status**: Complete
**Invariants**: INV-641 through INV-680 (40 invariants)
**Hard rules**: 15
**Tests**: 153 passing
**Regression**: 1478 passing (Phase 75B–85)

## Executive Summary

Phase 85 adds UMH's typed advisory council layer — a deliberation system where
specialist roles produce evidence-based perspective reports that are assessed,
gap-analyzed, disagreement-mapped, scored, aggregated, and synthesized into a
single CouncilAdvisory output. The entire layer is advisory-only: no execution,
no mutation, no adapter calls, no LLM calls. v1 uses deterministic stub
perspectives for end-to-end pipeline validation.

## Architecture

### Chair + Specialists Pattern

The council consists of typed roles (Chair, Strategist, Engineer, Risk Analyst,
User Advocate, Ontology Specialist) that each produce a PerspectiveReport
containing position, reasoning, evidence, assumptions, risks, opportunities,
dissents, confidence level, and a score. The Chair has elevated weight (1.5x).

### Pipeline Stages

1. **Request** — typed deliberation input with domain, urgency, constraints
2. **Perspectives** — specialist reports with evidence and assumptions
3. **Evidence Assessment** — strength analysis, gap detection, confidence
4. **Gap Detection** — missing roles, evidence-less perspectives
5. **Disagreement Mapping** — score divergence (>0.4), self-identified dissents
6. **Scoring** — weighted formula: score × role_weight × confidence × evidence
7. **Ontology Bridge** — resolves relevant laws and polarity syntheses
8. **Aggregation** — consensus calculation, recommendation synthesis
9. **Advisory** — final CouncilAdvisory with actionability determination

### Scoring Formula

```
weighted_score = raw_score × role_weight × confidence_factor × (0.5 + 0.5 × evidence_factor)
```

### Consensus Calculation

```
base = 1.0 - min(1.0, score_spread × 2)
penalty = significant_disagreements × 0.15
consensus = 0 if blocking_disagreements > 0
```

## New Files (15)

| File | Purpose |
|------|---------|
| `umh/council/__init__.py` | Package marker |
| `umh/council/contracts.py` | 6 enums, normalization, ID gen, EvidenceItem, Assumption |
| `umh/council/roles.py` | CouncilRoleType enum, CouncilRole dataclass, 6 defaults |
| `umh/council/request.py` | DeliberationRequest, factory, validation |
| `umh/council/perspective.py` | PerspectiveReport, factory, validation |
| `umh/council/evidence.py` | Evidence strength scoring, assessment, gap detection |
| `umh/council/gaps.py` | Coverage gap detection with severity levels |
| `umh/council/disagreement.py` | Conflict mapping by type and severity |
| `umh/council/scoring.py` | Weighted perspective ranking |
| `umh/council/aggregation.py` | Recommendation synthesis, consensus calc |
| `umh/council/advisory.py` | Final CouncilAdvisory wrapper |
| `umh/council/ontology_bridge.py` | Law resolution + polarity synthesis |
| `umh/council/views.py` | UI-safe read models (advisory + health) |
| `umh/council/safety.py` | AST-based import boundary enforcement |
| `umh/council/deliberation.py` | Top-level orchestrator |

## Modified Files (6)

| File | Change |
|------|--------|
| `umh/registry/contracts.py` | Added COUNCIL_ROLE, COUNCIL_ADVISORY to RegistryType |
| `umh/observability/system_status.py` | Added council_status field + check_council_status() |
| `umh/registry/bridges.py` | Added council_roles_to_registry_items() |
| `umh/registry/catalog.py` | Wired council roles bridge into catalog builder |
| `umh/control/api.py` | 4 endpoints: /council/{status,roles,deliberate,safety} |
| `umh/control/cli.py` | 4 commands: council-{status,roles,deliberate,safety} |

## Test Coverage (19 classes, 153 tests)

| Class | Tests | Coverage |
|-------|-------|----------|
| TestContractNormalization | 7 | Enum normalization round-trips |
| TestEnumCompleteness | 7 | All enums have UNKNOWN, complete value sets |
| TestCouncilRoles | 9 | Default roles, weights, types, serialization |
| TestDeliberationRequest | 8 | Factory, validation, constraints, laws |
| TestPerspectiveReports | 9 | Factory, validation, evidence, warnings |
| TestEvidenceAssessment | 8 | Strength scoring, gaps, confidence levels |
| TestGapDetection | 7 | Missing roles, empty perspectives, severity |
| TestDisagreementMapping | 8 | Score divergence, dissents, severity mapping |
| TestScoring | 8 | Weighted formula, role weights, ranking |
| TestAggregation | 8 | Consensus, recommendation synthesis |
| TestAdvisory | 7 | Actionability, status determination |
| TestDeliberationPipeline | 7 | Full pipeline, ontology integration |
| TestOntologyBridge | 5 | Law resolution, polarity pairing |
| TestViews | 8 | Advisory view, health view, serialization |
| TestRegistryIntegration | 5 | Bridge, catalog, new RegistryType values |
| TestObservabilityIntegration | 4 | SystemStatus council field, check function |
| TestAPICLIEndpoints | 8 | All 4 API + 4 CLI endpoints exist |
| TestSafetyLayering | 11 | AST-based forbidden import checking |
| TestRegression | 12 | Phase 75B–85 import smoke tests |

## Key Design Decisions

1. **Advisory-only doctrine** — council modules never execute, mutate, or call
   external services. This maintains UMH's read-only analysis guarantee.

2. **Deterministic v1** — stub perspectives use rule-based logic, not LLM calls.
   This makes the pipeline fully testable and reproducible.

3. **Ontology integration** — deliberations can reference universal laws and
   request polarity synthesis, connecting council reasoning to the ontology kernel.

4. **AST-based safety** — same pattern as Phase 84/84A. Parses all council module
   source files to verify no forbidden imports (subprocess, requests, httpx, etc.).

5. **Lazy imports throughout** — API handlers and bridge functions use deferred
   imports to prevent circular dependency chains.

## Invariant Summary

40 invariants (INV-641–INV-680) covering:
- Contract type integrity (enums, normalization, ID generation)
- Role definitions (types, weights, defaults, serialization)
- Request/perspective validation (required fields, factory contracts)
- Evidence assessment (strength scoring, confidence determination)
- Gap detection (missing roles, empty perspectives, severity levels)
- Disagreement mapping (divergence thresholds, blocking detection)
- Scoring formula correctness (weighted calculation, ranking order)
- Aggregation/consensus (recommendation synthesis, consensus formula)
- Advisory generation (actionability, status determination)
- Ontology bridge (law resolution, polarity synthesis)
- View contracts (UI-safe serialization, health checks)
- Registry integration (new types, bridge, catalog wiring)
- Observability integration (SystemStatus field, check function)
- API/CLI endpoints (4 routes, 4 commands)
- Safety layering (forbidden imports, AST validation)

## Hard Rules (15)

1. Council modules must not import subprocess, requests, httpx, aiohttp, selenium, playwright, smtplib, telegram, or discord
2. All council enums must include an UNKNOWN fallback value
3. Normalization functions must never raise — always return UNKNOWN for bad input
4. Council IDs must be UUID-based with typed prefix
5. Score clamping must enforce [0.0, 1.0] bounds
6. Evidence assessment must return LOW confidence for empty evidence
7. Gap detection must flag missing roles and evidence-less perspectives
8. Disagreement detection threshold is 0.4 for score divergence
9. Scoring formula must include role weight, confidence factor, and evidence factor
10. Consensus must be 0 if any blocking disagreement exists
11. Advisory actionability requires HIGH or MEDIUM confidence + possible consensus
12. Ontology bridge must gracefully degrade if ontology modules unavailable
13. All view models must serialize to dict without raising
14. Registry bridge must convert all default roles to RegistryItems
15. SystemStatus must include council_status field
