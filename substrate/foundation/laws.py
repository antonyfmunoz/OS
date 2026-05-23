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

__all__ = ["Law", "LawCategory", "Severity", "LawRegistry", "SUBSTRATE_LAWS"]
