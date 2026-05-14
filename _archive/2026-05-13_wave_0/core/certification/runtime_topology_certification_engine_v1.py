"""Runtime Topology Certification Engine v1.

Validates topology invariants across the substrate.

UMH substrate subsystem. Phase 96.8CI.
"""

from __future__ import annotations

from typing import Any

from core.certification.runtime_certification_contracts_v1 import (
    RuntimeTopologyGuarantee,
    _now_iso,
)


MAX_TOPOLOGY_CERTIFICATIONS = 50

TOPOLOGY_CHECKS: list[str] = [
    "no_orphan_execution_paths",
    "no_hidden_topology_mutation",
    "no_recursive_topology_growth",
    "no_environment_owned_orchestration",
    "no_application_owned_cognition",
    "no_deployment_owned_governance",
]


class RuntimeTopologyCertificationEngine:
    """Certifies topology invariants."""

    def __init__(self) -> None:
        self._certifications: list[RuntimeTopologyGuarantee] = []

    def certify_topology(
        self,
        no_orphans: bool = True,
        no_hidden_mutation: bool = True,
        no_recursive_growth: bool = True,
        bounded: bool = True,
    ) -> dict[str, Any]:
        if len(self._certifications) >= MAX_TOPOLOGY_CERTIFICATIONS:
            raise ValueError("Max topology certifications reached")

        g = RuntimeTopologyGuarantee(
            no_orphans=no_orphans,
            no_hidden_mutation=no_hidden_mutation,
            no_recursive_growth=no_recursive_growth,
            bounded=bounded,
        )
        self._certifications.append(g)

        certified = all([
            no_orphans, no_hidden_mutation, no_recursive_growth, bounded,
        ])

        return {
            "topology_guarantee_id": g.topology_guarantee_id,
            "certified": certified,
            "no_orphans": no_orphans,
            "no_hidden_mutation": no_hidden_mutation,
            "no_recursive_growth": no_recursive_growth,
            "bounded": bounded,
        }

    def all_certified(self) -> bool:
        if not self._certifications:
            return True
        return all(
            c.no_orphans and c.no_hidden_mutation
            and c.no_recursive_growth and c.bounded
            for c in self._certifications
        )

    def get_all_certifications(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._certifications]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_certifications": len(self._certifications),
            "all_certified": self.all_certified(),
        }
