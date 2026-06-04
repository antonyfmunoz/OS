# UMH EOS/CreatorOS/LyfeOS Integration Map

**Phase:** 14.6B-UMH
**Status:** DRAFT

## Projection Maturity

### EOS (EntrepreneurOS)

- **Maturity**: Most mature projection
- **Integration depth**: Full (all 7 socket components)
- **Agents**: 10 department agents with DepartmentAgent base class
- **Runtime**: Primary development and production focus
- **SaaS**: TypeScript/React application in `saas/` directory

### CreatorOS

- **Maturity**: Integration-only
- **Integration depth**: 6 of 7 components (no poller)
- **Agents**: None registered in UMH agent hierarchy
- **Runtime**: Separate SaaS application at `data/repos/creatoros`
- **Deployment**: Standalone SaaS, integrates with UMH via manifest

### LyfeOS

- **Maturity**: Partial integration
- **Integration depth**: 2 of 7 components (manifest + signals only)
- **Agents**: None registered in UMH agent hierarchy
- **Runtime**: Deployed at lyfeos.net (Replit)
- **Deployment**: Standalone web application, minimal UMH integration

## Shared Infrastructure

All three projections share:

- **One intelligence substrate** -- same model router, same fallback chain
- **One type system** -- `substrate/types.py` canonical types
- **One governance engine** -- risk classification and approval lifecycle
- **One observation pipeline** -- perceive/interpret/decompose/bridge/map/persist

## Compounding Model

| Configuration | Value |
|--------------|-------|
| Any one projection standalone | Baseline capability |
| Any two projections connected | Compound -- cross-projection signals and shared intelligence |
| All three projections connected | Multiply -- full trinity convergence, maximum compounding |

Each projection works independently. Any two compound through shared UMH substrate. All three multiply through cross-projection workflows and unified intelligence.

## Integration Dependencies

- EOS depends on UMH substrate (tight coupling, primary projection)
- CreatorOS depends on UMH substrate (loose coupling, manifest-based)
- LyfeOS depends on UMH substrate (minimal coupling, signals only)
- No projection depends on another projection directly
- Cross-projection communication flows through UMH (never peer-to-peer)
