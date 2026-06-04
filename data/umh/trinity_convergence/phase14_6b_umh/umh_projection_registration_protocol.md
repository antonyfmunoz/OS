# UMH Projection Registration Protocol

**Phase:** 14.6B-UMH
**Status:** DRAFT

## Current Registration Pattern

Projections register with UMH via manifest files. Each projection provides a `manifest.py` module containing:

- **INTEGRATION_ID** -- unique string identifier for the projection (e.g., `"eos"`, `"creatoros"`, `"lyfeos"`)
- **SIGNAL_DESCRIPTORS** -- list of signal types the projection emits and consumes
- **CAPABILITY_DESCRIPTORS** -- list of capabilities the projection exposes to UMH
- **Config loader** -- function that returns projection-specific configuration from env/BIS

### Manifest Locations

| Projection | Manifest Path |
|------------|---------------|
| EOS | `integrations/eos/manifest.py` |
| CreatorOS | `integrations/creatoros/manifest.py` |
| LyfeOS | `integrations/lyfeos/manifest.py` |

### Registration Flow

1. Service startup loads projection manifests
2. Each manifest registers its INTEGRATION_ID with ProductConnectionManager
3. Signal descriptors are registered with the signal routing system
4. Capability descriptors are registered with the capability router

## Future: Abstract Port Pattern

Planned enhancement: `substrate/sockets/projection_port.py`

- Abstract base class defining the projection registration contract
- Projections implement the port interface instead of using manifest conventions
- API endpoint registration for dynamic projection discovery
- Runtime projection health checks and capability negotiation

## Architecture Note

Current manifest-based registration is functional but informal. The abstract port pattern would enforce the registration contract at the type level and enable runtime projection management without restarts.
