"""Runtime Pressure Engine v1.

Simulates runtime pressure across multiple domains.
All pressure must remain bounded.

UMH substrate subsystem. Phase 96.8CJ.
"""

from __future__ import annotations

from typing import Any

from core.validation.sovereign_operational_validation_contracts_v1 import (
    RuntimePressureState,
    PressureDomain,
    _now_iso,
)

MAX_PRESSURE_SIMULATIONS = 100

PRESSURE_DOMAINS: list[str] = [d.value for d in PressureDomain]


class RuntimePressureEngine:
    def __init__(self) -> None:
        self._pressures: list[RuntimePressureState] = []

    def apply_pressure(self, domain: str, pressure_level: int = 50, bounded: bool = True) -> dict[str, Any]:
        if len(self._pressures) >= MAX_PRESSURE_SIMULATIONS:
            raise ValueError("Max pressure simulations reached")
        state = RuntimePressureState(domain=domain, pressure_level=pressure_level, bounded=bounded)
        self._pressures.append(state)
        return state.to_dict()

    def apply_all_pressures(self, pressure_level: int = 50) -> dict[str, Any]:
        results = []
        for domain in PRESSURE_DOMAINS:
            r = self.apply_pressure(domain, pressure_level=pressure_level, bounded=True)
            results.append(r)
        return {"all_bounded": all(r["bounded"] for r in results), "pressures": results, "total": len(results)}

    def all_bounded(self) -> bool:
        if not self._pressures:
            return True
        return all(p.bounded for p in self._pressures)

    def get_unbounded(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self._pressures if not p.bounded]

    def get_stats(self) -> dict[str, Any]:
        levels = [p.pressure_level for p in self._pressures]
        return {
            "total_pressures": len(self._pressures),
            "bounded": sum(1 for p in self._pressures if p.bounded),
            "unbounded": sum(1 for p in self._pressures if not p.bounded),
            "all_bounded": self.all_bounded(),
            "max_pressure": max(levels) if levels else 0,
            "avg_pressure": sum(levels) / len(levels) if levels else 0,
        }
