"""Governance protocol — canonical contract for governance engines.

Re-exports the GovernanceEngine Protocol from its implementation module.
Import from here for type annotations; implement against the Protocol shape.
"""

from __future__ import annotations

from substrate.control_plane.governance import GovernanceEngine  # noqa: F401

__all__ = ["GovernanceEngine"]
