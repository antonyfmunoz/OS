"""Reality Model — dual Canonical/Instance reality modeling."""

from substrate.reality_model.reality_mutation import (
    MutationSource,
    MutationType,
    RealityMutation,
    RealityMutationReceipt,
)

from substrate.reality_model.canonical_reality_write import (
    CanonicalRealityWritePath,
)

from substrate.reality_model.reality_query import (
    RealityEvidence,
    RealityQuery,
    RealityQueryResult,
    RealityQueryType,
)

from substrate.reality_model.reality_intelligence import (
    RealityIntelligenceEngine,
)

__all__ = [
    "MutationSource",
    "MutationType",
    "RealityMutation",
    "RealityMutationReceipt",
    "CanonicalRealityWritePath",
    "RealityEvidence",
    "RealityQuery",
    "RealityQueryResult",
    "RealityQueryType",
    "RealityIntelligenceEngine",
]
