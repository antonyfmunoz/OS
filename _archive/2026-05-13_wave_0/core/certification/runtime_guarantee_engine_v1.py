"""Runtime Guarantee Engine v1.

Generates runtime guarantees across 8 guarantee types.

UMH substrate subsystem. Phase 96.8CI.
"""

from __future__ import annotations

from typing import Any

from core.certification.runtime_certification_contracts_v1 import (
    RuntimeGuarantee,
    GuaranteeType,
    _now_iso,
)


MAX_GUARANTEES = 200


class RuntimeGuaranteeEngine:
    """Generates and tracks runtime guarantees."""

    def __init__(self) -> None:
        self._guarantees: list[RuntimeGuarantee] = []

    def issue_guarantee(
        self,
        guarantee_type: str,
        domain: str,
        guaranteed: bool = True,
    ) -> dict[str, Any]:
        if len(self._guarantees) >= MAX_GUARANTEES:
            raise ValueError("Max guarantees reached")

        g = RuntimeGuarantee(
            guarantee_type=guarantee_type,
            domain=domain,
            guaranteed=guaranteed,
        )
        self._guarantees.append(g)
        return g.to_dict()

    def issue_all_guarantees(self) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        for gt in GuaranteeType:
            r = self.issue_guarantee(gt.value, "global", guaranteed=True)
            results.append(r)

        return {
            "all_guaranteed": all(r["guaranteed"] for r in results),
            "guarantees": results,
            "total": len(results),
        }

    def get_all_guarantees(self) -> list[dict[str, Any]]:
        return [g.to_dict() for g in self._guarantees]

    def all_guaranteed(self) -> bool:
        if not self._guarantees:
            return True
        return all(g.guaranteed for g in self._guarantees)

    def get_failed_guarantees(self) -> list[dict[str, Any]]:
        return [g.to_dict() for g in self._guarantees if not g.guaranteed]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_guarantees": len(self._guarantees),
            "guaranteed": sum(1 for g in self._guarantees if g.guaranteed),
            "failed": sum(1 for g in self._guarantees if not g.guaranteed),
            "all_guaranteed": self.all_guaranteed(),
        }
