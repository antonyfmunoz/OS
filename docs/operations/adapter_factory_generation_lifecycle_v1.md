# Adapter Factory Generation — Lifecycle v1

**Phase**: 96.5  
**Status**: ACTIVE  
**Date**: 2026-05-04

---

## Core Rule

The Adapter Factory generates new adapter packages through an 11-stage lifecycle. Each stage produces tracked artifacts. Tool Mastery generation comes after code generation and before test generation — mastery knowledge informs what to test.

## 11 Generation Stages

| Stage | Name | Input | Output |
|-------|------|-------|--------|
| 1 | DISCOVERY | Tool name, URL, or SDK reference | Raw tool metadata, API surface |
| 2 | CLASSIFICATION | Raw metadata | Tool category, backend type, auth method |
| 3 | CONTRACT_GENERATION | Classification + API surface | Typed interface contracts (inputs, outputs, errors) |
| 4 | CODE_GENERATION | Contracts | Access Adapter + Auth Adapter + Execution Wrapper code |
| 5 | TOOL_MASTERY_GENERATION | Code + API surface + known failure modes | ToolMasteryPack (best practices, workflows, failure modes, edge cases, quality standards) |
| 6 | TEST_GENERATION | Contracts + Code + Mastery Pack | Contract tests, parity tests, smoke tests |
| 7 | SAFETY_POLICY_GENERATION | Classification + Mastery Pack | Rate limits, cost controls, secret handling, blast radius |
| 8 | DOCUMENTATION_GENERATION | All prior artifacts | Capability map, operational notes, configuration reference |
| 9 | QUALITY_GATE | All artifacts | 6-check quality report (pass/fail per check) |
| 10 | REGISTRATION | Quality report (all passed) | Registry entry with metadata, capabilities, status |
| 11 | COMPLETE | Registry entry | Adapter available for backend selection |

## Stage Ordering Rationale

Tool Mastery generation (stage 5) is positioned deliberately:

- **After code generation (stage 4)**: The mastery pack needs to reference actual implementation details — which SDK methods are used, which error types are thrown, which configuration options exist.
- **Before test generation (stage 6)**: Mastery knowledge about failure modes, edge cases, and quality standards directly informs what tests need to exist. Tests written without mastery knowledge only cover happy paths.
- **Before safety policy (stage 7)**: Mastery knowledge about rate limits, cost patterns, and blast radius informs governance constraints.

## Artifact Tracking

Each stage records:

- **stage_name**: enum value from the 11 stages
- **status**: PENDING | IN_PROGRESS | COMPLETED | FAILED
- **artifacts**: list of file paths or data objects produced
- **errors**: any failures encountered during generation
- **timestamp**: when the stage completed

## Stage Transitions

- Stages execute sequentially. No stage starts until its predecessor completes.
- A FAILED stage blocks all subsequent stages. The factory does not skip.
- Retry is allowed on any failed stage without restarting from DISCOVERY.
- QUALITY_GATE failure does not destroy prior artifacts — it identifies what needs repair.

## Hard Rules

- Never skip TOOL_MASTERY_GENERATION. An adapter without mastery is technically connected but operationally ignorant.
- Never generate tests before mastery. Tests informed only by contracts miss edge cases and failure modes.
- Never register an adapter that failed the quality gate. Stage 10 requires all 6 checks passing.
- Never reuse a mastery pack from a different tool. Each adapter gets its own mastery, even if tools are similar.

## References

- `eos_ai/adapter_factory.py` — factory implementation
- `eos_ai/adapter_quality_gate.py` — stage 9 implementation
- `eos_ai/adapter_registry.py` — stage 10 implementation
- `eos_ai/adapter_best_practices_loader.py` — mastery pack generation support
- `docs/operations/adapter_engine_doctrine_v1.md` — 8-layer model
- `docs/operations/adapter_quality_gate_v1.md` — gate policy
