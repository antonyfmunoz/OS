# Phase 1 — LLM Canary (Strict cc_sdk-only)

> Date: 2026-05-13
> Verdict: **PASS — STRUCTURED via cc_sdk (Opus 4.6)**

## Test Configuration

- Fixture: `tests/fixtures/ingestion_fixture.md`
- Source: `LocalFileSource(authority_tier=T8_SCRATCH)`
- Orchestrator: `GenericIngestionOrchestrator`
- cc_sdk timeout: 120s (default)

## Result

```
verdict: COMPLETE_CYCLE
wall-clock: 72.1s
provider: cc_sdk (confirmed by log: "[cc_sdk] returning output (6940 chars)")
model: Opus 4.6 (via Max subscription, no API cost)
observations: 10 (all with semantic labels, not raw text)
relationships: 6 (typed: produces, constrains, enables, measures)
projections: 0 (expected — test fixture lacks business domain keywords)
persisted: 10 entries
query_back: rank=3
```

## Provider Attribution

- `[cc_sdk] called with task_type=analysis agent_id=eos_default nested=False`
- `[cc_sdk] output_parts=1`
- `[cc_sdk] returning output (6940 chars)`
- No fallthrough log lines (no `[Router] cc_sdk failed` messages)
- "Fatal error in message reader" = known MCP shutdown artifact, NOT a failure

**cc_sdk served directly. No fallthrough.**

## Observation Quality

| # | Type | Label | Quality |
|---|------|-------|---------|
| 0 | resource | Deterministic ingestion test fixture document | SEMANTIC |
| 1 | constraint | Decomposition phase must never be skipped | SEMANTIC |
| 2 | constraint | Minimum primitive type coverage required | SEMANTIC |
| 3 | state | Ingestion orchestrator separates source from pipeline | SEMANTIC |
| 4 | action | Six-stage canonical ingestion pipeline execution | SEMANTIC |
| 5 | constraint | Orchestrator must not modify existing contracts | SEMANTIC |
| 6 | outcome | Nonce retrievable at rank 1 after query-back | SEMANTIC |
| 7 | constraint | Fixture immutability requirement | SEMANTIC |
| 8 | time | Fixture creation date 2026-05-12 | SEMANTIC |
| 9 | state | Fixture document structure metrics | SEMANTIC |

6 distinct primitive types (resource, constraint, state, action, outcome, time).
All labels are semantic abstractions, not raw text copies.

## Relationship Quality

| # | From → To | Type | Semantic? |
|---|-----------|------|-----------|
| 0 | obs-71f41023 → obs-fa072b75 | produces | YES |
| 1 | obs-daa7f313 → obs-71f41023 | constrains | YES |
| 2 | obs-2253993d → obs-2d13ab62 | constrains | YES |
| 3 | obs-de710b21 → obs-71f41023 | enables | YES |
| 4 | obs-89899acc → obs-de710b21 | constrains | YES |
| 5 | obs-77bc9aa3 → obs-fa072b75 | measures | YES |

6 relationships with 4 distinct types. vs old heuristic's 1 hardcoded "enables".

## STOP Condition Check

- Provider = cc_sdk ✓ (not fallthrough)
- cc_sdk completed in 72.1s < 120s ✓ (no timeout)
- Output = STRUCTURED ✓ (10 semantic observations, 6 typed relationships)
- No STOP conditions triggered → PROCEED to Phase 2
