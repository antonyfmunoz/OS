"""Model — user behavior modeling, trait computation, and behavioral aggregation."""

from umh.model.aggregator import BehaviorAggregator
from umh.model.behavior import UserBehaviorModel
from umh.model.traits import (
    TRAIT_DEFINITIONS,
    TraitDefinition,
    TraitValue,
    confidence_from_samples,
    default_traits,
)

__all__ = [
    "BehaviorAggregator",
    "TRAIT_DEFINITIONS",
    "TraitDefinition",
    "TraitValue",
    "UserBehaviorModel",
    "confidence_from_samples",
    "default_traits",
]
