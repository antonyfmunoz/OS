"""Invariant Consolidation Engine v1.

Consolidates governance, replay, continuity, lifecycle, topology,
observability, scaling, and resilience invariants into a unified set.

UMH substrate subsystem. Phase 96.8CG.
"""

from __future__ import annotations

from typing import Any

from core.constitutional.constitutional_runtime_contracts_v1 import (
    ConstitutionalInvariant,
    InvariantDomain,
    _now_iso,
)

CONSOLIDATED_INVARIANTS: list[dict[str, str]] = [
    {"domain": "governance", "name": "operator_approval_required",
     "description": "All mutations require operator approval"},
    {"domain": "governance", "name": "no_autonomous_execution",
     "description": "Substrate never executes autonomously"},
    {"domain": "governance", "name": "no_governance_bypass",
     "description": "No subsystem may bypass governance"},
    {"domain": "replay", "name": "deterministic_replay",
     "description": "Same input + same state → same output across all layers"},
    {"domain": "replay", "name": "replay_lineage_preserved",
     "description": "All replay decisions traceable to source"},
    {"domain": "continuity", "name": "checkpoint_determinism",
     "description": "Checkpoints restore identically"},
    {"domain": "continuity", "name": "session_lineage_preserved",
     "description": "Session chains unbroken across layers"},
    {"domain": "lifecycle", "name": "terminal_states_enforced",
     "description": "Terminal states are absorbing — no exit"},
    {"domain": "lifecycle", "name": "valid_transitions_only",
     "description": "Only declared transitions permitted"},
    {"domain": "topology", "name": "no_hidden_topology_mutation",
     "description": "Topology changes are explicit and governed"},
    {"domain": "topology", "name": "self_edge_denied",
     "description": "No node may connect to itself"},
    {"domain": "topology", "name": "cycle_prevention",
     "description": "No cycles in execution/dependency graphs"},
    {"domain": "observability", "name": "all_events_persisted",
     "description": "Every event type has JSONL persistence"},
    {"domain": "observability", "name": "event_map_matches_enum",
     "description": "EVENT_FILE_MAP generated from enum values"},
    {"domain": "scaling", "name": "no_autonomous_scaling",
     "description": "Infrastructure scaling requires operator"},
    {"domain": "scaling", "name": "override_capping",
     "description": "min(override, default) always applied"},
    {"domain": "resilience", "name": "no_autonomous_repair",
     "description": "Recovery recommends, never auto-executes"},
    {"domain": "resilience", "name": "bounded_cascade_depth",
     "description": "Cascading failures bounded to max depth"},
]

MAX_INVARIANTS = 100


class InvariantConsolidationEngine:
    """Consolidates and validates constitutional invariants."""

    def __init__(self) -> None:
        self._invariants: list[ConstitutionalInvariant] = []
        self._load_consolidated()

    def _load_consolidated(self) -> None:
        for entry in CONSOLIDATED_INVARIANTS:
            inv = ConstitutionalInvariant(
                domain=entry["domain"],
                name=entry["name"],
                description=entry["description"],
            )
            self._invariants.append(inv)

    def register_invariant(
        self,
        domain: str,
        name: str,
        description: str = "",
    ) -> ConstitutionalInvariant | None:
        known_domains = {d.value for d in InvariantDomain}
        if domain not in known_domains:
            return None
        if len(self._invariants) >= MAX_INVARIANTS:
            return None

        for inv in self._invariants:
            if inv.domain == domain and inv.name == name:
                return inv

        inv = ConstitutionalInvariant(
            domain=domain, name=name, description=description,
        )
        self._invariants.append(inv)
        return inv

    def validate_domain(self, domain: str) -> dict[str, Any]:
        domain_invs = [i for i in self._invariants if i.domain == domain]
        return {
            "domain": domain,
            "invariant_count": len(domain_invs),
            "all_enforced": all(i.enforced for i in domain_invs),
            "invariants": [i.to_dict() for i in domain_invs],
        }

    def validate_all(self) -> dict[str, Any]:
        domains = {d.value for d in InvariantDomain}
        results: dict[str, Any] = {}
        for domain in sorted(domains):
            results[domain] = self.validate_domain(domain)
        return {
            "total_invariants": len(self._invariants),
            "all_enforced": all(i.enforced for i in self._invariants),
            "domains": results,
        }

    def get_invariants_for_domain(self, domain: str) -> list[dict[str, Any]]:
        return [i.to_dict() for i in self._invariants if i.domain == domain]

    def get_all_invariants(self) -> list[dict[str, Any]]:
        return [i.to_dict() for i in self._invariants]

    def get_stats(self) -> dict[str, object]:
        return {
            "total_invariants": len(self._invariants),
            "domains_covered": len({i.domain for i in self._invariants}),
            "all_enforced": all(i.enforced for i in self._invariants),
        }
