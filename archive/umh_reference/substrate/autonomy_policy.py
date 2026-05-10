"""
Autonomy policy — bounded autonomy controls for recursive intent chains.

Prevents runaway follow-on intent creation by enforcing:
- Per-source ingress gating (decision/operator/cron/result)
- Maximum chain depth for result-driven follow-on
- Maximum follow-on count from any root intent
- Replay-safe: all decisions derived from persisted intent state

The policy is a frozen dataclass — immutable after construction.
IntentCoordinator accepts it as a dependency and enforces it at
ingress boundaries.

Usage:
    from umh.substrate.autonomy_policy import AutonomyPolicy, IngressSource

    policy = AutonomyPolicy(enabled=True, max_chain_depth=3)
    source = IngressSource.from_event_type("result_intent_requested")
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IngressSource(str, Enum):
    """Classification of ingress event origin.

    Maps 1:1 to the four raw ingress event types in the orchestration
    vocabulary.
    """

    DECISION = "decision"
    OPERATOR = "operator"
    CRON = "cron"
    RESULT = "result"

    @staticmethod
    def from_event_type(event_type: str) -> IngressSource | None:
        """Derive ingress source from raw event type string.

        Returns None if the event type is not a recognized ingress type.
        """
        mapping = {
            "decision_intent_proposed": IngressSource.DECISION,
            "operator_intent_requested": IngressSource.OPERATOR,
            "cron_intent_requested": IngressSource.CRON,
            "result_intent_requested": IngressSource.RESULT,
        }
        return mapping.get(event_type)


@dataclass(frozen=True)
class AutonomyPolicy:
    """Bounded autonomy controls for intent chain creation.

    All fields have safe defaults that preserve existing behavior
    when the policy is disabled (enabled=False).

    Fields:
        enabled:                  Master switch.  When False, no enforcement.
        max_chain_depth:          Maximum depth of result-driven intent chains.
                                  Root intents have depth 0.
        max_follow_on_per_root:   Maximum total follow-on intents from any
                                  single root intent.
        allow_result_follow_on:   Whether result-driven ingress is permitted.
        allow_decision_ingress:   Whether decision engine ingress is permitted.
        allow_cron_ingress:       Whether cron-triggered ingress is permitted.
        allow_operator_ingress:   Whether operator-triggered ingress is permitted.
    """

    enabled: bool = False
    max_chain_depth: int = 3
    max_follow_on_per_root: int = 5
    allow_result_follow_on: bool = True
    allow_decision_ingress: bool = True
    allow_cron_ingress: bool = True
    allow_operator_ingress: bool = True

    def is_source_allowed(self, source: IngressSource) -> bool:
        """Check whether the given ingress source is permitted by policy.

        When policy is disabled, all sources are allowed.
        """
        if not self.enabled:
            return True
        return {
            IngressSource.DECISION: self.allow_decision_ingress,
            IngressSource.OPERATOR: self.allow_operator_ingress,
            IngressSource.CRON: self.allow_cron_ingress,
            IngressSource.RESULT: self.allow_result_follow_on,
        }[source]

    def check_chain_depth(self, proposed_depth: int) -> bool:
        """Return True if the proposed chain depth is within policy limits.

        When policy is disabled, always returns True.
        """
        if not self.enabled:
            return True
        return proposed_depth <= self.max_chain_depth

    def check_follow_on_count(self, proposed_count: int) -> bool:
        """Return True if the proposed follow-on count is within policy limits.

        When policy is disabled, always returns True.
        """
        if not self.enabled:
            return True
        return proposed_count <= self.max_follow_on_per_root
