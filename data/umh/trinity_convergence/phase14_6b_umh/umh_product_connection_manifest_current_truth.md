# UMH Product Connection Manifest -- Current Truth

**Phase:** 14.6B-UMH (revised 14.6F)
**Status:** DRAFT

Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).

## Location

`substrate/integrations/product_connections.py`

## Core Components

### Product Enum

Defines the three UMH projections:

- `EOS` -- EntrepreneurOS
- `CREATOROS` -- CreatorOS
- `LYFEOS` -- LyfeOS

### ConnectionStatus Enum

- `CONNECTED` -- projection is active and registered
- `DISCONNECTED` -- projection is not active
- `DEGRADED` -- projection is active but not fully functional

### ProductConnection Dataclass

Fields:

- `product: Product`
- `status: ConnectionStatus`
- `capabilities: list` -- registered capabilities
- `signals: list` -- registered signal types
- `integration_id: str` -- unique identifier from manifest

## cross_product_summary()

Returns a dictionary:

```python
{
    "connected_count": int,       # projections with CONNECTED status
    "total_capabilities": int,    # sum across all connected projections
    "total_signals": int,         # sum across all connected projections
    "compounding_flag": bool      # True if 2+ projections connected
}
```

## Architecture Violation

**Problem**: `ProductConnectionManager` lives in `substrate/integrations/` but imports from projection-specific modules to load manifests.

This violates the architecture layer law: substrate must never import from projections or transports.

**Ratified fix (DEC-146B-UMH-005, 2026-06-04)**: Projections register their manifests via an abstract port (`substrate/sockets/projection_port.py`). ProductConnectionManager queries the port registry instead of importing projection code. Decision ratified; implementation not yet started.
