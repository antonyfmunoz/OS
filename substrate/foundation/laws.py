"""Substrate laws — re-exports from substrate.ontology.laws.

The canonical implementation lives in substrate/ontology/laws.py with
executable check() methods and the full set of 14 substrate laws.
This module re-exports for backward compatibility.
"""

from substrate.ontology.laws import (  # noqa: F401
    Law,
    LawCategory,
    LawRegistry,
    Severity,
)

# Re-export the canonical law instances under their original names
# for any code that imported them from here.
from substrate.ontology.laws import _ALL_LAWS  # noqa: F401

SUBSTRATE_LAWS = _ALL_LAWS

_BY_NAME = {law.name: law for law in _ALL_LAWS}

NO_DIRECT_EXECUTION_LAW = _BY_NAME.get("single_execution_spine", _ALL_LAWS[1])
SIGNAL_INTAKE_LAW = _BY_NAME.get("signal_intake", _ALL_LAWS[12])
TRACEABILITY_LAW = _BY_NAME.get("trace_completeness", _ALL_LAWS[6])
MEMORY_PATHWAY_LAW = _BY_NAME.get("memory_discipline", _ALL_LAWS[4])
ADAPTER_MEDIATION_LAW = _BY_NAME.get("external_boundary", _ALL_LAWS[8])

__all__ = [
    "Law", "LawCategory", "Severity", "LawRegistry", "SUBSTRATE_LAWS",
    "NO_DIRECT_EXECUTION_LAW", "SIGNAL_INTAKE_LAW", "TRACEABILITY_LAW",
    "MEMORY_PATHWAY_LAW", "ADAPTER_MEDIATION_LAW",
]
