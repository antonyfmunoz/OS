# UMH Projection Integration Architecture

**Phase:** 14.6B-UMH
**Status:** DRAFT

## Socket Pattern

All three projections follow an identical 7-component integration pattern:

```
manifest --> signals --> handlers --> outcomes --> correlation --> tables --> poller
```

### Component Definitions

1. **Manifest** -- INTEGRATION_ID, SIGNAL_DESCRIPTORS, CAPABILITY_DESCRIPTORS, config loader
2. **Signals** -- Signal type definitions the projection emits/consumes
3. **Handlers** -- Signal processing logic for projection-specific events
4. **Outcomes** -- Result types produced by handler execution
5. **Correlation** -- Maps external events to internal signal chains
6. **Tables** -- Database schema for projection-specific persistence
7. **Poller** -- Scheduled polling for external state changes

## Projection Coverage Matrix

| Component | EOS | CreatorOS | LyfeOS |
|-----------|-----|-----------|--------|
| Manifest | Yes | Yes | Yes |
| Signals | Yes | Yes | Yes |
| Handlers | Yes | Yes | No |
| Outcomes | Yes | Yes | No |
| Correlation | Yes | Yes | No |
| Tables | Yes | Yes | No |
| Poller | Yes | No | No |

- **EOS**: All 7 components implemented. Most mature integration.
- **CreatorOS**: 6 of 7 components. No poller (external state managed by separate SaaS).
- **LyfeOS**: 2 of 7 components (manifest + signals only). Minimal integration depth.

## Pattern Consistency

The identical pattern across projections is by design. Any projection integrating with UMH implements the same 7-component socket pattern, enabling uniform lifecycle management and observability.
