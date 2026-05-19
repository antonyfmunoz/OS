# UMH/EOS Boundary Doctrine v1

**Phase**: 94D.4 — Auto Worker Runtime + Topology Boundary
**Status**: ACTIVE
**Date**: 2026-05-04

---

## Doctrine

UMH (Universal Meta Harness) is the substrate. EOS (EntrepreneurOS) is
a projection. They are not the same thing. EOS does not contain UMH.
UMH powers EOS. This distinction must never collapse.

## What is UMH (Substrate)?

Everything below the application layer:
- Execution spine, cognitive loop, primitives, laws
- Governance engine, authority engine
- Message bus, advisor session
- Topology, capability routing
- Worker runtime, node registry
- Station daemon, station bus
- Control plane, execution fabric

UMH is domain-agnostic. It can power any business OS, not just EOS.

## What is EOS (Projection)?

A business execution surface powered by UMH:
- EntrepreneurOS — the flagship SaaS
- Initiate Arena, Game of Lyfe — product projections
- Portfolio Advisor, Morning Brief — feature projections
- CRM, Content Calendar, Lead Pipeline — domain projections

## What are Other Projections?

- LYFEOS — personal optimization projection
- CreatorOS — content creator projection
- Distribution platforms, audience platforms

All projections sit on top of UMH. None of them are the substrate.

## Confusion Patterns (INVALID)

| Statement | Why It's Wrong |
|-----------|---------------|
| "EOS is the substrate" | EOS is a projection, not the substrate |
| "EOS is substrate" | Same error |
| "EOS powers UMH" | UMH powers EOS, not the reverse |
| "EOS substrate layer" | The substrate layer is UMH |

## Valid Statements

- "EOS is powered by UMH"
- "EOS is a projection"
- "EOS is a domain projection"
- "UMH is the substrate"
- "UMH powers EOS"
- "LYFEOS is a projection"
- "CreatorOS is a projection"

## Classification Logic

`classify_component_boundary()` classifies any component as:
- `UMH_SUBSTRATE` — lives in substrate package or matches substrate terms
- `PROJECTION` — lives in saas/services or matches projection terms
- `AMBIGUOUS` — cannot classify, needs human review

## Detection Logic

`detect_umh_eos_confusion()` scans text for statements that collapse
EOS into UMH or reverse the power relationship. Returns warnings.

`validate_boundary_statement()` returns True/False for a given statement.

## Files

`eos_ai/substrate/substrate_projection_boundaries.py`
