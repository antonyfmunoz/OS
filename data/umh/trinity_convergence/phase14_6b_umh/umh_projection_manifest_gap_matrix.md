# UMH Projection Manifest Gap Matrix

**Phase:** 14.6B-UMH
**Status:** DRAFT

## Problem

All three projection manifests are shallow current slices that do not reflect the full capability of each product. Manifests undercount both signals and capabilities relative to actual product scope.

## Gap Matrix

### EOS (EntrepreneurOS)

| Dimension | Manifest | Actual Scope | Gap |
|-----------|----------|-------------|-----|
| Signals | 3 | 10+ (one per department minimum) | ~70% undeclared |
| Capabilities | 5 | 10 departments, 10 workflows, full entity hierarchy | ~80% undeclared |

Missing from manifest: department-level signal types, workflow capabilities, entity CRUD operations, analytics signals, governance actions.

### CreatorOS

| Dimension | Manifest | Actual Scope | Gap |
|-----------|----------|-------------|-----|
| Signals | 3 | Per corrected 14.6B CreatorOS canon | Significant |
| Capabilities | 4 | Per corrected 14.6B CreatorOS canon | Significant |

Missing from manifest: content pipeline signals, audience analytics, platform distribution capabilities, collaboration workflows.

### LyfeOS

| Dimension | Manifest | Actual Scope | Gap |
|-----------|----------|-------------|-----|
| Signals | 3 | Per corrected 14.6B LyfeOS canon (35 tables) | Major |
| Capabilities | 4 | Per corrected 14.6B LyfeOS canon (35 tables) | Major |

Missing from manifest: wellness tracking, habit loops, social features, gamification signals, profile management, community capabilities.

## Impact

- `cross_product_summary()` underreports total capabilities and signals
- Compounding value calculation is based on incomplete data
- UMH cannot route signals to capabilities that are not declared in manifests
- Capability-aware agent dispatch misses undeclared projection features

## Recommended Action

Each manifest should be expanded to declare the full signal and capability surface of its projection, derived from the corrected 14.6B canon documents.
