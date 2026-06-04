# UMH Cross-Product Integration Architecture

**Phase:** 14.6B-UMH (revised 14.6F)
**Status:** DRAFT

Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).

## Current State

Cross-projection integration is managed by `ProductConnectionManager` at `substrate/integrations/product_connections.py`.

### cross_product_summary()

Returns a dictionary with:

| Field | Description |
|-------|-------------|
| `connected_count` | Number of projections with CONNECTED status |
| `total_capabilities` | Sum of capabilities across all connected projections |
| `total_signals` | Sum of signal types across all connected projections |
| `compounding_flag` | Boolean indicating whether multi-projection compounding is active |

### Current Capability

- Read-only summary of projection connection state
- No cross-projection data flow
- No cross-projection workflow orchestration
- Compounding flag is informational only (no runtime effect)

## Future Architecture

### Cross-Projection Workflows

- Projection A emits signal that triggers handler in Projection B
- Workflow chains that span multiple projections with correlation tracking
- Example: EOS client signs up --> LyfeOS creates wellness profile --> CreatorOS generates content plan

### Data Sharing Policies

- Per-projection data boundary enforcement (currently documented in `umh_projection_data_boundary_privacy_model.md`)
- Explicit opt-in data sharing between projections via governance approval
- Tenant-scoped sharing (no cross-tenant leakage)

### Combined Analytics

- Unified metrics across projections for a single user/org
- Cross-projection funnel analysis
- Compounding value measurement (the whole exceeding the sum of parts)

## Architecture Violation Note

ProductConnectionManager currently lives in `substrate/integrations/` but imports from projection-specific modules. This violates the architecture layer law (substrate must not import from projections). Ratified fix (DEC-146B-UMH-005, 2026-06-04): projections register capabilities via abstract port (`substrate/sockets/projection_port.py`), ProductConnectionManager queries the port registry. Decision ratified; implementation not yet started.
