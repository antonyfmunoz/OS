"""LyfeOS projection activation / readiness — P4S-10.

Mirrors the EOS reference shape (projections/eos/integration/readiness.py,
rules/projection-read-surfaces.md) for the second projection to ship a governed
read surface. COMPOSES existing substrate read surfaces only (no new registry,
no schema, no mutation, no domain-model sprawl):

- registered in the canonical seed view  → substrate.sockets.projection_port
      load_umh_projection_seed() (port-backed read of data/umh/projection_registry.json)
- runtime registration status            → get_default_projection_port().get("lyfeos")
      (env-dependent — the daemon seeds a port; reported separately, may be False)
- readiness / boot eligibility           → projections.lyfeos.integration.manifest
      load_lyfeos_config() — CONFIGURED (non-empty) vs DISCONNECTED ({}), read fresh
      from the environment every call (env-disabled-safe: {} when
      LYFEOS_DATABASE_URL unset)

All imports are downward (projection → substrate), which the dependency-direction
gate permits. This module never mutates state and never raises on the env-disabled
path — it returns a stable, safe readiness dict either way.

LyfeOS is an integration-shell projection today (no Beast-backed source-truth row
like EOS) — the readiness shape intentionally omits the beast_* fields until
LyfeOS ships a real Beast-tracked build (see WP-P4-EOS-BEAST-BACKED-BUILD-001 for
that follow-on shape when/if it applies here).
"""

from __future__ import annotations

from typing import Any

_PROJECTION_ID = "lyfeos"
_SEED_FIELDS = ("app_name", "health_url", "public_url", "l4_workflow")


def lyfeos_readiness() -> dict[str, Any]:
    """Return a stable LyfeOS activation/readiness view. Never raises; safe when
    LYFEOS_DATABASE_URL is unset (env-disabled -> status "disconnected")."""
    from substrate.sockets.projection_port import (
        get_default_projection_port,
        load_umh_projection_seed,
    )

    # 1. Canonical seed view — deterministic proof LyfeOS is a registered projection.
    seed = load_umh_projection_seed()
    lyfeos_seed = seed.get(_PROJECTION_ID, {})
    registered_in_seed = _PROJECTION_ID in seed

    # 2. Runtime registration — env-dependent (daemon-seeded port); reported, not required.
    try:
        runtime_reg = get_default_projection_port().get(_PROJECTION_ID)
    except Exception:
        runtime_reg = None

    # 3. Readiness / boot eligibility — derived from the live LyfeOS config (fresh env
    #    read every call; env-disabled-safe).
    status = "disconnected"
    boot_eligible = False
    poll_interval: float | None = None
    try:
        from projections.lyfeos.integration.manifest import load_lyfeos_config

        config = load_lyfeos_config()
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
        "seed": {k: lyfeos_seed.get(k) for k in _SEED_FIELDS},
        "connection_status": status,
        "boot_eligible": boot_eligible,
        "poll_interval": poll_interval,
    }
