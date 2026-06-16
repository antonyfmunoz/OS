"""State Registry — canonical registry of state domain authorities.

Single source of truth for which node is authoritative for each state
domain. Loads seed data from infra/state_authority_registry.json.
State is modeled by domain (memory, governance, runtime), not by file.

Phase 29. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from substrate.organism.state_authority_graph import (
    OrganismStateGraph,
    StateAuthority,
    StateDomainStatus,
)

logger = logging.getLogger(__name__)


def _find_registry_path() -> str:
    """Locate state_authority_registry.json, checking UMH_ROOT and file-relative."""
    root = os.environ.get("UMH_ROOT", "/opt/OS")
    candidate = os.path.join(root, "infra", "state_authority_registry.json")
    if os.path.exists(candidate):
        return candidate
    here = os.path.dirname(os.path.abspath(__file__))
    fallback = os.path.normpath(
        os.path.join(here, "..", "..", "infra", "state_authority_registry.json")
    )
    return fallback


def _load_seed_authorities() -> list[StateAuthority]:
    """Load state authority definitions from infra/state_authority_registry.json."""
    registry_path = _find_registry_path()
    try:
        with open(registry_path) as f:
            entries = json.load(f)
    except Exception:
        logger.debug("Could not load state authority registry from %s", registry_path)
        return []

    authorities: list[StateAuthority] = []
    for entry in entries:
        domain = entry.get("domain", "")
        if not domain:
            continue
        authorities.append(StateAuthority.from_dict(entry))

    return authorities


class StateRegistry:
    """Single source of truth for state domain authority."""

    def __init__(self, seed: bool = True) -> None:
        self._authorities: dict[str, StateAuthority] = {}
        if seed:
            for auth in _load_seed_authorities():
                self._authorities[auth.domain] = auth

    def get_domain(self, domain: str) -> StateAuthority | None:
        return self._authorities.get(domain)

    def authority_node(self, domain: str) -> str:
        auth = self._authorities.get(domain)
        if auth is None:
            return ""
        return auth.node_id

    def domains_for_node(self, node_id: str) -> list[StateAuthority]:
        return [a for a in self._authorities.values() if a.node_id == node_id]

    def all_domains(self) -> list[StateAuthority]:
        return list(self._authorities.values())

    def register_authority(self, authority: StateAuthority) -> None:
        self._authorities[authority.domain] = authority
        logger.info(
            "State authority registered: %s → %s",
            authority.domain,
            authority.node_id,
        )

    def topology(self) -> OrganismStateGraph:
        domain_statuses = []
        for auth in self._authorities.values():
            domain_statuses.append(
                StateDomainStatus(
                    domain=auth.domain,
                    authority_node=auth.node_id,
                )
            )
        return OrganismStateGraph(domains=domain_statuses)

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain_count": len(self._authorities),
            "domains": {
                d: a.to_dict() for d, a in self._authorities.items()
            },
        }
