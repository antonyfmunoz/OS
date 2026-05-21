"""Intelligence kernel enrichment hook for umh.run stage 4.

Produces an optional enrichment dict that the run loop can attach
to the decision trace.  Never blocks execution — returns empty dict
on any failure.

Enabled by UMH_INTELLIGENCE_ENRICHMENT=1 (default: off).

Pure computation — no I/O, no execution, no subprocess.
"""

from __future__ import annotations

import os
from typing import Any


def is_enabled() -> bool:
    return os.environ.get("UMH_INTELLIGENCE_ENRICHMENT", "") == "1"


def enrich_decision(
    operation: str,
    intent_confidence: float,
    goal_active: bool,
    goal_priority: int = 0,
) -> dict[str, Any]:
    """Return intelligence enrichment for the decision stage.

    Returns empty dict if disabled or if the kernel raises.
    """
    if not is_enabled():
        return {}

    try:
        from umh.runtime.weighted_decision import compute_weighted_influence
        from umh.runtime.regime_aggregation import get_aggregated_regime
        from umh.runtime.dimension_weighting import get_weight_vector

        regime = get_aggregated_regime()
        weights = get_weight_vector()
        influence = compute_weighted_influence(regime, weights)

        return {
            "intelligence_enrichment": {
                "influence_factor": round(influence.factor, 4),
                "confidence": round(influence.confidence, 4),
                "regime_label": regime.label if regime else "unknown",
                "active_dimensions": influence.active_dimensions,
                "gated": influence.confidence_gated,
            }
        }
    except Exception:
        return {}
