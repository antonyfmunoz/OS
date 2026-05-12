---
type: test-fixture
generated: 2026-05-12
nonce: XQVR7-ZEPHYR-CANARY-9F3K
---

# Ingestion Test Fixture — XQVR7-ZEPHYR-CANARY-9F3K

This document is a deterministic test fixture for the generic ingestion
orchestrator. The nonce string XQVR7-ZEPHYR-CANARY-9F3K appears nowhere
else in the repository and must be retrievable via query-back.

## Purpose

The fixture validates that the full canonical pipeline processes
structured markdown with:
- YAML frontmatter
- Multiple heading levels
- Prescriptive directives (must/never)
- Code blocks
- Wikilinks

## Constraints

Agents must never skip the decomposition phase when processing this
fixture. The pipeline must always produce at least one observation of
each primitive type that appears in the content. Required coverage
includes state, constraint, and resource primitives at minimum.

## Architecture Overview

The generic ingestion orchestrator separates source from pipeline:

```
Source.read() → perceive → interpret → decompose → map → persist → query
```

Each stage produces a typed artifact. The orchestrator never modifies
existing contracts — it sequences them. See [[ingestion_orchestrator_v1_design]]
for the full design rationale.

## Test Data

| Metric | Value |
|--------|-------|
| Word count | ~500 |
| Heading count | 5 |
| Constraints | 2 |
| Code blocks | 1 |
| Wikilinks | 1 |

## Expected Behavior

When processed through `GenericIngestionOrchestrator.ingest()`:

1. Perceive: sha256 computed, signal_id generated
2. Interpret: type = structured_operational_document, domains include architecture
3. Decompose: 4+ observations, 1+ relationships
4. Map: entities and facts written matching observation count
5. Persist: memory entry appended, receipt written
6. Query: nonce XQVR7-ZEPHYR-CANARY-9F3K retrievable at rank 1

## Provenance

This fixture was created on 2026-05-12 for ingestion-orchestrator-1.
It is not real operational content. It exists solely to validate
the pipeline contract shapes in automated tests.

The fixture must remain unchanged after creation. If the orchestrator
cannot process it, the orchestrator needs adjustment — never the fixture.
