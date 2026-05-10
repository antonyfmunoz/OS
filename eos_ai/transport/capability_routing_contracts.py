"""
Capability-based routing contracts for Phase 94D.4.

Routes tasks to nodes based on capabilities, not node names.
A GUI computer-use task routes to a GUI-capable node.
Missing capability produces SETUP_REQUIRED, not hallucinated execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from eos_ai.substrate.topology_contracts import NodeProfile, TopologyProfile


class Capability(str, Enum):
    GUI_COMPUTER_USE = "gui_computer_use"
    BROWSER_SESSION = "browser_session"
    LOCAL_FILES = "local_files"
    SCREEN_CONTROL = "screen_control"
    AUDIO = "audio"
    LLM_INFERENCE = "llm_inference"
    ORCHESTRATION = "orchestration"
    SCHEDULING = "scheduling"
    API_ACCESS = "api_access"
    FILE_STORAGE = "file_storage"
    DOCKER = "docker"
    GPU_COMPUTE = "gpu_compute"


class RoutingOutcome(str, Enum):
    ROUTED = "routed"
    NO_CAPABLE_NODE = "no_capable_node"
    SETUP_REQUIRED = "setup_required"
    MULTIPLE_CANDIDATES = "multiple_candidates"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RoutingRequirement:
    required_capabilities: list[str]
    preferred_capabilities: list[str] = field(default_factory=list)
    required_roles: list[str] = field(default_factory=list)
    prefer_online: bool = True
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "required_capabilities": self.required_capabilities,
            "preferred_capabilities": self.preferred_capabilities,
            "required_roles": self.required_roles,
            "prefer_online": self.prefer_online,
            "description": self.description,
        }


@dataclass
class RoutingDecision:
    outcome: RoutingOutcome
    selected_node_id: str | None
    score: float
    reason: str
    candidates_evaluated: int
    missing_capabilities: list[str] = field(default_factory=list)
    decided_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "selected_node_id": self.selected_node_id,
            "score": self.score,
            "reason": self.reason,
            "candidates_evaluated": self.candidates_evaluated,
            "missing_capabilities": self.missing_capabilities,
            "decided_at": self.decided_at,
        }


def score_node_for_requirement(
    node: NodeProfile, requirement: RoutingRequirement
) -> tuple[float, list[str]]:
    """Score a node against a routing requirement.

    Returns (score, missing_capabilities).
    Score range: 0.0 (unusable) to 1.0 (perfect match).
    A node missing any required capability scores 0.0.
    """
    missing = [cap for cap in requirement.required_capabilities if not node.has_capability(cap)]
    if missing:
        return 0.0, missing

    required_roles_met = all(
        any(r.value == role for r in node.roles) for role in requirement.required_roles
    )
    if requirement.required_roles and not required_roles_met:
        return 0.0, [f"role:{r}" for r in requirement.required_roles]

    score = 0.5
    if requirement.preferred_capabilities:
        preferred_count = sum(
            1 for cap in requirement.preferred_capabilities if node.has_capability(cap)
        )
        score += 0.3 * (preferred_count / len(requirement.preferred_capabilities))

    if requirement.prefer_online and node.online:
        score += 0.2
    elif requirement.prefer_online and not node.online:
        score -= 0.2

    return min(max(score, 0.0), 1.0), []


def choose_best_node(topology: TopologyProfile, requirement: RoutingRequirement) -> RoutingDecision:
    """Choose the best node for a routing requirement from a topology.

    Returns SETUP_REQUIRED if no node has the required capabilities.
    """
    if not topology.nodes:
        return RoutingDecision(
            outcome=RoutingOutcome.NO_CAPABLE_NODE,
            selected_node_id=None,
            score=0.0,
            reason="Topology has no nodes",
            candidates_evaluated=0,
        )

    scored: list[tuple[NodeProfile, float, list[str]]] = []
    for node in topology.nodes:
        s, missing = score_node_for_requirement(node, requirement)
        scored.append((node, s, missing))

    viable = [(n, s, m) for n, s, m in scored if s > 0.0]

    if not viable:
        all_missing: list[str] = []
        for _, _, m in scored:
            all_missing.extend(m)
        unique_missing = sorted(set(all_missing))
        return RoutingDecision(
            outcome=RoutingOutcome.SETUP_REQUIRED,
            selected_node_id=None,
            score=0.0,
            reason=f"No node has required capabilities: {unique_missing}",
            candidates_evaluated=len(scored),
            missing_capabilities=unique_missing,
        )

    viable.sort(key=lambda x: x[1], reverse=True)
    best_node, best_score, _ = viable[0]

    outcome = RoutingOutcome.MULTIPLE_CANDIDATES if len(viable) > 1 else RoutingOutcome.ROUTED

    return RoutingDecision(
        outcome=outcome,
        selected_node_id=best_node.node_id,
        score=best_score,
        reason=f"Selected {best_node.node_id} (score={best_score:.2f})",
        candidates_evaluated=len(scored),
    )
