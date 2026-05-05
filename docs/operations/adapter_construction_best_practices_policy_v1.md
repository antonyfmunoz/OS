# Adapter Construction Best Practices — Policy v1

**Phase**: 96.5  
**Status**: ACTIVE  
**Date**: 2026-05-04

---

## Core Rule

Every adapter package must satisfy 6 quality checks before promotion. No adapter ships without a contract, tests, safety policy, no-secret policy, documentation, and a Tool Mastery Pack. These are non-negotiable construction standards, not aspirational guidelines.

## Mandatory Components

1. **Contract** — typed interface defining inputs, outputs, errors, and invariants for every capability the adapter exposes. No implicit behavior.
2. **Tests** — contract tests proving the adapter meets its interface, parity tests against reference backends, smoke tests for basic reachability.
3. **Safety Policy** — rate limits, cost ceilings, blast radius constraints, rollback procedures. Every adapter must declare what it can break and how to contain it.
4. **No-Secret Policy** — secrets never hardcoded, never logged, never passed in URLs. All credentials flow through the Auth Adapter layer via environment variables or secret broker.
5. **Documentation** — capability map, failure modes, configuration reference, and operational notes. Written for the operator who will debug this at 2am.
6. **Tool Mastery Pack** — best practices, workflows, failure modes, edge cases, quality standards. The difference between "connected" and "usable like a master."

## Pre-Change Checks

- Read the adapter module you are modifying before touching it.
- Check if the capability you are adding already exists in the Capability Map.
- Verify the adapter's current quality gate status — do not regress a passing adapter.

## Pre-Done Checks

- All 6 quality gate checks pass.
- Import check: `python3 -c "from eos_ai.adapter_engine import AdapterEngine; print('ok')"`.
- Parity validation against reference backend (if applicable).
- No secrets in any committed file.

## Pre-Deploy Checks

- Quality gate report generated and reviewed.
- Registry entry updated with current capability set.
- Existing consumers of the adapter are not broken by the change.

## Risk Classes

| Risk | Description | Example |
|------|-------------|---------|
| LOW | New adapter, new capability | Adding a new tool adapter |
| MEDIUM | Modifying existing capability | Changing retry logic in execution wrapper |
| HIGH | Changing auth flow or governance | Rotating credential strategy |
| CRITICAL | Schema migration, removing capability | Dropping a registered adapter |

## Hard Rules

- Never hardcode secrets — always `os.getenv()`.
- Never skip parity validation when a reference backend exists.
- Never promote an adapter that fails any quality gate check.
- Never build a new adapter pattern when the Adapter Factory can generate one.
- Never ship a mastery pack that is a copy of the tool's README — mastery encodes operational expertise, not vendor docs.

## References

- `eos_ai/adapter_engine.py` — core engine
- `eos_ai/adapter_quality_gate.py` — 6-check gate
- `eos_ai/adapter_factory.py` — generation lifecycle
- `docs/operations/adapter_quality_gate_v1.md` — gate policy details
- `docs/operations/adapter_engine_doctrine_v1.md` — 8-layer model
