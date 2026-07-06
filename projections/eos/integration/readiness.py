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
# The VERIFIED Beast source-state fields surfaced in the readiness view, mapped to the
# flat readiness key they appear under. Kept to a small, stable set (source classification
# + build-safety inputs + provenance) — not the full harness row — so the accessor stays
# flat and its shape is stable. Keys are pre-namespaced to avoid a double "beast_" prefix.
_BEAST_SOURCE_FIELDS = {
    "source_risk": "beast_source_risk",
    "runtime_ready": "beast_runtime_ready",
    "backed_up": "beast_backed_up",
    "mirror_fidelity": "beast_mirror_fidelity",
    "operating_branch": "beast_operating_branch",
    "head": "beast_head",
    "beast_verification": "beast_verification",
    "beast_probe_at": "beast_probe_at",
}


def eos_readiness() -> dict[str, Any]:
    """Return a stable EOS activation/readiness view. Never raises; safe when
    EOS_DATABASE_URL is unset (env-disabled → status "disconnected")."""
    from substrate.sockets.projection_port import (
        get_beast_source_row,
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

    # 4. Beast source truth — VERIFIED source-readiness row for EOS, composed through
    #    the canonical port (never opens the reconciliation file here; read-surface
    #    invariant #6). The real EOS app body lives on the Beast, not in this shell or
    #    the /opt/OS mirror — this ties EOS readiness to that verified source state.
    #    `beast_source` is {} when the last probe was UNREACHABLE/UNKNOWN or the row is
    #    unverified (never surfaces a stale/false-current state). `source_build_safe` is
    #    the single boolean a build orchestrator checks before a Beast-backed EOS slice.
    #    Fields are flattened into `beast_*` top-level keys (not a nested dict) to honor
    #    the read-surface flat-shape invariant, which sanctions only the single `seed`
    #    summary dict. Absent/unverified → all beast_* keys None and source_build_safe False.
    beast_fields: dict[str, Any] = {key: None for key in _BEAST_SOURCE_FIELDS.values()}
    source_build_safe = False
    try:
        row = get_beast_source_row(_PROJECTION_ID)
        if row:
            beast_fields = {key: row.get(src) for src, key in _BEAST_SOURCE_FIELDS.items()}
            source_build_safe = (
                row.get("source_risk") == "source_current"
                and row.get("runtime_ready") == "yes"
                and row.get("backed_up") == "yes"
                and row.get("mirror_fidelity") == "full"
                and row.get("beast_verification") == "VERIFIED"
            )
    except Exception:
        # port-safe: no Beast record → None beast_* fields, not build-safe, never raise.
        beast_fields = {key: None for key in _BEAST_SOURCE_FIELDS.values()}
        source_build_safe = False

    return {
        "projection_id": _PROJECTION_ID,
        "registered_in_seed": registered_in_seed,
        "runtime_registered": runtime_reg is not None,
        "seed": {k: eos_seed.get(k) for k in _SEED_FIELDS},
        "connection_status": status,
        "boot_eligible": boot_eligible,
        "poll_interval": poll_interval,
        **beast_fields,
        "source_build_safe": source_build_safe,
    }
