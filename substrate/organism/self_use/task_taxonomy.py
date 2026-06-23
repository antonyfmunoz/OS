"""Task taxonomy — domain classification for self-use certification.

Defines the streams, domains, and coherence attack types that
C27 tasks are classified under. Data-driven, no hardcoded tasks.
"""

from __future__ import annotations

from enum import Enum


class StreamType(str, Enum):
    """Top-level C27 streams."""

    PRODUCTION = "production"
    COHERENCE = "coherence"
    REALITY = "reality"
    META_IDE_AUDIT = "meta_ide_audit"


class TaskDomain(str, Enum):
    """Production task domains — what the task exercises."""

    DESIRED_STATE = "desired_state"
    DESIGN_TO_IMPL = "design_to_impl"
    IMPLEMENTATION = "implementation"
    DEPLOY_CERTIFY = "deploy_certify"
    UMH_SUPPORT = "umh_support"


class CoherenceDomain(str, Enum):
    """Coherence attack domains — what the attack tests."""

    CONTINUITY = "continuity"
    DISTRACTION = "distraction"
    GOVERNANCE = "governance"
    REALITY_DRIFT = "reality_drift"


STREAM_TASK_RANGES: dict[StreamType, tuple[int, int]] = {
    StreamType.PRODUCTION: (40, 50),
    StreamType.COHERENCE: (15, 25),
    StreamType.REALITY: (5, 10),
    StreamType.META_IDE_AUDIT: (20, 30),
}

COHERENCE_DOMAIN_RANGES: dict[CoherenceDomain, tuple[int, int]] = {
    CoherenceDomain.CONTINUITY: (5, 8),
    CoherenceDomain.DISTRACTION: (4, 6),
    CoherenceDomain.GOVERNANCE: (3, 5),
    CoherenceDomain.REALITY_DRIFT: (3, 6),
}
