"""
Agent role abstraction — clean contract for multi-agent orchestration.

EOS already has agent_hierarchy.py, which encodes the org chart for prompt
injection. This module does NOT replace it. It adds a complementary,
routing-friendly `AgentRole` abstraction that captures:

  - identity slug (used by substrate messages + SafeAction.issued_by)
  - scope (what the role is allowed to touch)
  - handoff targets (which roles it may escalate to)

The goal is preparing for live async + voice sessions where multiple agents
need to coexist without becoming disconnected systems. A role here is the
*substrate-facing* view of what agent_hierarchy already describes
operationally.

Usage:
    from runtime.transport import RoleRegistry, AgentRole, RoleScope

    reg = RoleRegistry.default()
    ea = reg.get("ea_orchestrator")
    assert RoleScope.ROUTE_ALL in ea.scopes
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RoleScope(str, Enum):
    """
    Coarse permission tags. Not a full ACL — just enough to make handoff
    and escalation decisions legible at the substrate level. Finer-grained
    authority lives in runtime/authority_engine.py and is NOT duplicated here.
    """

    ROUTE_ALL = "route_all"                  # can receive any founder message
    READ_PORTFOLIO = "read_portfolio"        # can read cross-company state
    DECIDE_COMPANY = "decide_company"        # can make decisions for one company
    ADVISE_ONLY = "advise_only"              # no decisions, intelligence only
    DISPATCH_ACTIONS = "dispatch_actions"    # may emit SafeActions to a station
    INITIATE_RITUAL = "initiate_ritual"      # may start open_day/close_day


@dataclass
class AgentRole:
    """
    A role a running agent instance can adopt.

    `slug` is the stable identifier used across the substrate (appears in
    SafeAction.issued_by, StationEvent.payload, ritual inputs, etc.).
    """

    slug: str
    title: str
    description: str
    scopes: list[RoleScope] = field(default_factory=list)
    handoff_to: list[str] = field(default_factory=list)  # other role slugs
    escalate_to: Optional[str] = None  # single upward role, if any
    metadata: dict = field(default_factory=dict)

    def has_scope(self, scope: RoleScope) -> bool:
        return scope in self.scopes

    def can_handoff_to(self, other_slug: str) -> bool:
        return other_slug in self.handoff_to


class RoleRegistry:
    """
    Minimal in-memory role registry, seeded with the three initial roles.

    These mirror agent_hierarchy.py at a higher level of abstraction:
      - ea_orchestrator  ≈ executive_assistant (DEX), the primary interface
      - ceo              ≈ a generic CEO slot; per-company CEOs are instances
      - portfolio_advisor ≈ pure intelligence, no command authority
    """

    _default: Optional["RoleRegistry"] = None

    def __init__(self) -> None:
        self._roles: dict[str, AgentRole] = {}

    def register(self, role: AgentRole) -> AgentRole:
        self._roles[role.slug] = role
        return role

    def get(self, slug: str) -> Optional[AgentRole]:
        return self._roles.get(slug)

    def all(self) -> list[AgentRole]:
        return list(self._roles.values())

    @classmethod
    def default(cls) -> "RoleRegistry":
        if cls._default is not None:
            return cls._default

        reg = cls()
        reg.register(
            AgentRole(
                slug="ea_orchestrator",
                title="Executive Assistant / Orchestrator",
                description=(
                    "Primary founder interface. Routes communication, "
                    "initiates rituals, dispatches actions to stations on "
                    "the founder's behalf. Does not own company decisions."
                ),
                scopes=[
                    RoleScope.ROUTE_ALL,
                    RoleScope.READ_PORTFOLIO,
                    RoleScope.DISPATCH_ACTIONS,
                    RoleScope.INITIATE_RITUAL,
                ],
                handoff_to=["ceo", "portfolio_advisor"],
                escalate_to=None,  # EA is the top interface layer
            )
        )
        reg.register(
            AgentRole(
                slug="ceo",
                title="Company CEO",
                description=(
                    "Owns decisions and execution for a single company. "
                    "Generic slot; concrete instances are per-company "
                    "(e.g. lyfe_institute_ceo, empyrean_ceo)."
                ),
                scopes=[
                    RoleScope.DECIDE_COMPANY,
                    RoleScope.DISPATCH_ACTIONS,
                ],
                handoff_to=["ea_orchestrator"],
                escalate_to="ea_orchestrator",
            )
        )
        reg.register(
            AgentRole(
                slug="portfolio_advisor",
                title="Portfolio Advisor",
                description=(
                    "Cross-company intelligence. Reads everything, decides "
                    "nothing. Informs CEOs and the EA without commanding."
                ),
                scopes=[
                    RoleScope.READ_PORTFOLIO,
                    RoleScope.ADVISE_ONLY,
                ],
                handoff_to=["ea_orchestrator"],
                escalate_to="ea_orchestrator",
            )
        )
        cls._default = reg
        return reg
