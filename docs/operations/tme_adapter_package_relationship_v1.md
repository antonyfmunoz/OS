# TME ↔ Adapter Package Relationship

**Version:** 1.0
**Date:** 2026-05-05
**Scope:** UMH substrate — all platform consumers

## Core Relationship

TME and the Adapter Engine are separate UMH substrate subsystems
with a producer-consumer relationship:

- **TME produces** Tool Mastery Packs
- **Adapter Engine consumes** them as Layer 4 of the 8-layer Adapter Package

## The 8 Layers

1. Access Adapter — how UMH connects (API/SDK/CLI/MCP/CU)
2. Auth Adapter — OAuth, API key, service account, browser profile
3. Capability Map — what the tool can do (read/write/search/etc.)
4. **Tool Mastery Pack** — expert-level usage knowledge (TME produces this)
5. Governance Policy — allowed/blocked actions, approval gates, risk levels
6. Execution Wrapper — callable implementation, retries, logging
7. Tests / Validation — adapter, safety, no-secret, parity, coverage
8. Registry Entry — access path class, auth class, independence, status

## Maturity Gate

An adapter package cannot be promoted to AVAILABLE or PREFERRED status
unless its Tool Mastery Pack passes the Mastery Assurance Gate:
- Pack exists
- Pack is fresh (within staleness threshold)
- Pack is complete (all required sections present)
- Pack meets quality tier minimum

## Maturity Score

Each adapter package carries:
- `maturity_score: float` — percentage of quality checks passed (0-100)
- `gaps_to_100: list[str]` — specific checks that failed

These fields exist on both `AdapterQualityReport` and `AdapterPackage`.

## Independence

TME operates independently of the Adapter Engine. A mastery pack can
exist without an adapter package (e.g., for a tool not yet formalized
into an adapter). The reverse — an adapter package without a mastery
pack — is permitted but blocked from promotion.
