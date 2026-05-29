# Projection Boundary Law

UMH has two layers that must never mix:

- **Substrate** (substrate/) = universal platform. Works for any projection.
- **Projections** (projections/) = applications built ON the substrate (EOS, CreatorOS, LyfeOS).

Before writing ANY identifier in substrate/ code, ask:
"Would this be different for a different projection?"

If yes → it's projection-specific. Move to projections/ or use runtime registration.

Names that are ALWAYS projection-specific:
- `EntrepreneurOS*` class names → use `Gateway`, `SubstrateContext`, `Orchestrator`
- `EOS_ORG_ID` / `EOS_USER_ID` → use `UMH_ORG_ID` / `UMH_USER_ID` (with EOS fallback)
- `eos-*` prefixed identifiers → use projection-agnostic names
- `CreatorOS`, `LyfeOS` → keep in projections/ or registries only

Projections register with UMH at runtime via abstract ports:
- `substrate/sockets/channel_port.py` — channel routing
- `substrate/sockets/projection_port.py` — projection registration (planned)

Pre-commit hook enforces this: `scripts/check_projection_leak.py`
