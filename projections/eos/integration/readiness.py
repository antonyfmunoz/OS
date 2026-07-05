"""EOS projection activation / readiness — WP-P4-006.

The smallest governed read surface proving EOS is alive as a projection over the
substrate. It COMPOSES existing substrate read surfaces (no new registry, no
schema, no mutation, no domain-model sprawl):

- registered in the canonical seed view  → substrate.sockets.projection_port
      load_umh_projection_seed() (port-backed read of data/umh/projection_registry.json)
- runtime registration status            → get_default_projection_port().get("eos")
      (env-dependent — the daemon seeds a port; reported separately, may be False)
- readiness / boot eligibility           → projections.eos.integration.manifest
      load_eos_config() — CONFIGURED (non-empty) vs DISCONNECTED ({}), read fresh from
      the environment every call (env-disabled-safe: {} when EOS_DATABASE_URL unset)

All imports are downward (projection → substrate), which the dependency-direction
gate permits. This module never mutates state and never raises on the env-disabled
path — it returns a stable, safe readiness dict either way.
"""

from __future__ import annotations

from typing import Any

_PROJECTION_ID = "eos"
_SEED_FIELDS = ("app_name", "health_url", "public_url", "l4_workflow")


def eos_readiness() -> dict[str, Any]:
    """Return a stable EOS activation/readiness view. Never raises; safe when
    EOS_DATABASE_URL is unset (env-disabled → status "disconnected")."""
    from substrate.sockets.projection_port import (
        get_default_projection_port,
        load_umh_projection_seed,
    )

    # 1. Canonical seed view — deterministic proof EOS is a registered projection.
    seed = load_umh_projection_seed()
    eos_seed = seed.get(_PROJECTION_ID, {})
    registered_in_seed = _PROJECTION_ID in seed

    # 2. Runtime registration — env-dependent (daemon-seeded port); reported, not required.
    try:
        runtime_reg = get_default_projection_port().get(_PROJECTION_ID)
    except Exception:
        runtime_reg = None

    # 3. Readiness / boot eligibility — derived from the live EOS config (fresh env
    #    read every call; mirrors product_connections._load_eos CONFIGURED/DISCONNECTED
    #    semantics without a cached process-wide singleton, so readiness reflects the
    #    current environment deterministically).
    status = "disconnected"
    boot_eligible = False
    poll_interval: float | None = None
    try:
        from projections.eos.integration.manifest import load_eos_config

        config = load_eos_config()
        if config:
            status = "configured"
            boot_eligible = True
            poll_interval = config.get("poll_interval")
    except Exception:
        # env-disabled / import-safe: stay disconnected, never raise.
        status = "disconnected"

    return {
        "projection_id": _PROJECTION_ID,
        "registered_in_seed": registered_in_seed,
        "runtime_registered": runtime_reg is not None,
        "seed": {k: eos_seed.get(k) for k in _SEED_FIELDS},
        "connection_status": status,
        "boot_eligible": boot_eligible,
        "poll_interval": poll_interval,
    }
