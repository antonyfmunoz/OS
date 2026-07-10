"""EOS projection instance seam — the ONE place EOS reads tenant identity.

Multi-tenancy law: NEVER hardcode a product/venture/ICP/north-star/audience/
brand literal in EOS code. Every seat runs the same code against a different
tenant's BIS. A hardcoded value = one tenant's data leaking into every seat.

All EOS agents and workflows read tenant vocabulary through these accessors,
which resolve from the tenant's Business Instance State (BIS) at runtime and
fall back to neutral, tenant-agnostic wording when BIS is unset (dev / tests /
unconfigured seat) — never to a named default.
"""

from __future__ import annotations

from typing import Any


def load_bis(org_id: str = "", venture_id: str = "") -> Any | None:
    """Load the tenant BIS for this org/venture, or None when unavailable.

    Resolution order for the venture: explicit ``venture_id`` arg → context's
    active venture. Returns None (never raises) so callers degrade to neutral
    defaults.
    """
    try:
        from substrate.state.business.business_instance import BusinessInstanceManager
        from substrate.state.context.context import try_load_context_from_env

        ctx = try_load_context_from_env()
        if not ctx:
            return None
        vid = venture_id or getattr(ctx, "active_venture_id", "")
        if not vid:
            return None
        return BusinessInstanceManager(ctx).get_bis(vid)
    except Exception:
        return None


def _bis_field(bis: Any | None, field: str, default: str) -> str:
    if not bis:
        return default
    value = getattr(bis, field, "") or ""
    return value if value else default


def offer_name(bis: Any | None, default: str = "the offer") -> str:
    """Tenant offer/product name (BIS.offer_name) or a neutral default."""
    return _bis_field(bis, "offer_name", default)


def icp(bis: Any | None, default: str = "the target audience") -> str:
    """Tenant ideal-customer description (BIS.icp_description) or neutral default."""
    return _bis_field(bis, "icp_description", default)


def north_star(bis: Any | None, default: str = "the north-star goal") -> str:
    """Tenant north-star (BIS.north_star) or a neutral default."""
    return _bis_field(bis, "north_star", default)


def brand(bis: Any | None, default: str = "the brand") -> str:
    """Tenant brand/venture name (BIS.name) or a neutral default."""
    return _bis_field(bis, "name", default)


def founder(bis: Any | None, default: str = "the founder") -> str:
    """Tenant founder name (BIS.founder_name) or a neutral default."""
    return _bis_field(bis, "founder_name", default)


def icp_age_ranges(bis: Any | None) -> list[str]:
    """Tenant ICP target age ranges (BIS.icp_demographics['age_ranges']).

    Empty list when unset — callers must treat "no configured ranges" as
    "don't score on age", never as a hardcoded band.
    """
    if not bis:
        return []
    demo = getattr(bis, "icp_demographics", None) or {}
    ranges = demo.get("age_ranges") if isinstance(demo, dict) else None
    if isinstance(ranges, (list, tuple)):
        return [str(r) for r in ranges]
    return []
