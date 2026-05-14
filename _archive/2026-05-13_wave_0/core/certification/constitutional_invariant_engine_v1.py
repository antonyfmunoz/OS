"""Constitutional Invariant Engine v1.

Validates constitutional invariants across 10 domains.
System-wide verification, not module-local correctness.

UMH substrate subsystem. Phase 96.8CI.
"""

from __future__ import annotations

from typing import Any

from core.certification.runtime_certification_contracts_v1 import (
    ConstitutionalInvariantState,
    CrossLayerInvariantState,
    CertificationDomain,
    _now_iso,
)


CONSTITUTIONAL_INVARIANTS: dict[str, list[str]] = {
    CertificationDomain.GOVERNANCE: [
        "operator_approval_required",
        "no_autonomous_execution",
        "no_governance_bypass",
    ],
    CertificationDomain.REPLAY: [
        "deterministic_replay",
        "replay_lineage_preserved",
    ],
    CertificationDomain.CONTINUITY: [
        "checkpoint_determinism",
        "session_lineage_preserved",
    ],
    CertificationDomain.TOPOLOGY: [
        "no_hidden_topology_mutation",
        "self_edge_denied",
        "no_recursive_growth",
    ],
    CertificationDomain.OBSERVABILITY: [
        "all_events_persisted",
        "event_map_matches_enum",
    ],
    CertificationDomain.LIFECYCLE: [
        "terminal_states_enforced",
        "valid_transitions_only",
    ],
    CertificationDomain.ORCHESTRATION: [
        "no_autonomous_orchestration",
        "bounded_fanout",
    ],
    CertificationDomain.APPLICATION: [
        "no_application_owned_cognition",
        "no_substrate_bypass",
    ],
    CertificationDomain.DEPLOYMENT: [
        "no_autonomous_deployment",
        "rollout_operator_only",
    ],
    CertificationDomain.RESILIENCE: [
        "no_autonomous_repair",
        "bounded_cascade_depth",
    ],
}

MAX_INVARIANTS = 200
MAX_CROSS_LAYER = 100


class ConstitutionalInvariantEngine:
    """Validates constitutional invariants across all domains."""

    def __init__(self) -> None:
        self._invariants: list[ConstitutionalInvariantState] = []
        self._cross_layer: list[CrossLayerInvariantState] = []
        self._violations: list[dict[str, Any]] = []

    def verify_invariant(
        self,
        domain: str,
        invariant_name: str,
        enforced: bool = True,
    ) -> dict[str, Any]:
        if len(self._invariants) >= MAX_INVARIANTS:
            raise ValueError("Max invariants reached")

        state = ConstitutionalInvariantState(
            domain=domain,
            invariant_name=invariant_name,
            enforced=enforced,
        )
        self._invariants.append(state)

        if not enforced:
            self._violations.append({
                "domain": domain,
                "invariant_name": invariant_name,
                "timestamp": _now_iso(),
            })

        return state.to_dict()

    def verify_cross_layer(
        self,
        source_domain: str,
        target_domain: str,
        consistent: bool = True,
    ) -> dict[str, Any]:
        if len(self._cross_layer) >= MAX_CROSS_LAYER:
            raise ValueError("Max cross-layer checks reached")

        state = CrossLayerInvariantState(
            source_domain=source_domain,
            target_domain=target_domain,
            consistent=consistent,
        )
        self._cross_layer.append(state)

        if not consistent:
            self._violations.append({
                "type": "cross_layer",
                "source_domain": source_domain,
                "target_domain": target_domain,
                "timestamp": _now_iso(),
            })

        return state.to_dict()

    def verify_all_domains(self) -> dict[str, Any]:
        results: dict[str, dict[str, Any]] = {}
        for domain, invariants in CONSTITUTIONAL_INVARIANTS.items():
            domain_results = []
            for inv in invariants:
                r = self.verify_invariant(domain, inv, enforced=True)
                domain_results.append(r)
            results[domain] = {
                "invariants": len(domain_results),
                "all_enforced": all(
                    d["enforced"] for d in domain_results
                ),
            }

        all_enforced = all(r["all_enforced"] for r in results.values())
        return {
            "all_enforced": all_enforced,
            "domains": results,
            "total_invariants": sum(
                r["invariants"] for r in results.values()
            ),
        }

    def get_violations(self) -> list[dict[str, Any]]:
        return list(self._violations)

    def all_enforced(self) -> bool:
        if not self._invariants:
            return True
        return all(i.enforced for i in self._invariants)

    def all_cross_layer_consistent(self) -> bool:
        if not self._cross_layer:
            return True
        return all(c.consistent for c in self._cross_layer)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_invariants": len(self._invariants),
            "enforced": sum(1 for i in self._invariants if i.enforced),
            "violated": sum(1 for i in self._invariants if not i.enforced),
            "cross_layer_checks": len(self._cross_layer),
            "cross_layer_consistent": sum(
                1 for c in self._cross_layer if c.consistent
            ),
            "all_enforced": self.all_enforced(),
            "all_cross_layer_consistent": self.all_cross_layer_consistent(),
        }
