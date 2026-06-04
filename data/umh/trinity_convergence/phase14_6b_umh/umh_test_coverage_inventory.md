# UMH Test Coverage Inventory

**Phase:** 14.6B-UMH
**Status:** DRAFT

## Summary

- **86 test files** across the repository
- **2,832 test functions** total
- **929 test functions** from Phase 14 alone
- **No CI pipeline** -- tests run manually
- **No E2E tests** -- all tests are unit/integration level

## Key Test Areas

| Area | Coverage Focus |
|------|---------------|
| Substrate types | Pydantic model validation, enum completeness, type coherence |
| Entity store | CRUD operations, tenant isolation, query patterns |
| Memory | Memory persistence, retrieval, context assembly |
| Feedback | Quality scoring, learning loop, feedback persistence |
| Trace | Trace recording, Neon persistence, trace correlation |
| Spine | 8-stage execution pipeline, stage transitions, error handling |
| Convergence | Phase convergence validation, artifact integrity |
| Products | Product connection, cross-product summary, manifest loading |
| Organism | Runtime graph, coordinator, workcell protocol, daemon state |
| Daemon | Daemon lifecycle, heartbeat, state transitions |
| Cockpit endpoints | Route handlers, response format, auth middleware |
| Domain bridge | Domain-typed projections, ontology observations |
| TME | Tool mastery engine, skill loading, tool skill management |

## Test Distribution

Phase 14 tests account for approximately 33% of all test functions (929/2832), reflecting the intensive build and convergence work in recent phases.

## Gaps

- No continuous integration -- tests are not run automatically on commit or PR
- No end-to-end tests that exercise the full signal-to-outcome pipeline
- No load/performance tests for Docker services
- No browser-based tests for cockpit UI
- No cross-projection integration tests
