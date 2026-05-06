# Canonical Spine Coherence Gate v1

**Phase:** 96.8G
**Status:** Active
**Layer:** UMH Substrate — Coherence Layer
**Module:** `core/coherence/coherence_gate.py`

## Purpose

Fail-closed execution guard that blocks any work packet from
executing unless it carries a valid CoherenceEnvelope proving
it descended from the canonical UMH spine.

## Why Local Correctness Is Not Global Coherence

A work packet can be locally valid — correct fields, correct
routing, correct governance, correct execution binding — and
still represent an action that was never properly decomposed,
primitive-mapped, or governed through the canonical spine.

Local validation checks: "do these fields look right?"
Coherence validation checks: "did this packet come from the
right place through the right process?"

## The Gate

Before any execution:

```
evaluate_coherence_before_execution(packet)
  → COHERENT → proceed
  → COHERENT_WITH_MVP_STUBS → proceed (controlled W0 testing)
  → anything else → BLOCK_EXECUTION: INCOMPLETE_CANONICAL_SPINE
```

The gate is fail-closed. If validation cannot confirm coherence,
execution is blocked.

## What the Gate Checks

1. Coherence envelope exists in the packet
2. Lineage has all 15 required stages
3. No duplicate stages
4. Stages are in canonical order
5. Every stage has artifact_id, trace_id, schema_version, status
6. MVP stubs are only allowed when explicitly flagged
7. MVP stubs have reasons
8. Governance appears before work_packet
9. Mastery appears before governance

## MVP Stub Lineage

For W0 controlled vertical-slice testing, stages without full
subsystem implementations use explicit MVP stub artifacts.

An MVP stub must have:
- `status: mvp_stub`
- `reason: <why this stage is a stub>`
- `allowed_for: W0 coherence validation only`

This is **not** fake coherence. It is an explicit, traceable
declaration that a subsystem is not yet implemented, with
governance permission to proceed for testing only.

## Integration Points

- **Packet validator:** `validate_w0_packet_dict()` checks coherence
- **Local worker:** `validate_coherence_from_packet()` runs before
  claiming, preflight, or GUI actions
- **W0 packet builder:** `build_w0_001_packet()` emits a coherence
  envelope with explicit MVP stub lineage
