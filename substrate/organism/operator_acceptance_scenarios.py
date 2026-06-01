"""Operator acceptance scenarios — predefined end-to-end test scenarios.

Phase 13.4. UMH substrate subsystem. Instance-agnostic.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class AcceptanceScenario:
    """A single predefined acceptance scenario for operator end-to-end validation."""

    scenario_id: str  # "oas-<letter>"
    name: str
    input_text: str
    input_mode: str  # "text"
    expected_intent_type: str
    expected_steps: list[str]
    expected_artifacts: list[str]
    requires_runtime: bool
    requires_permission: bool
    requires_reconciliation: bool
    requires_propagation: bool
    expected_production_mutation: bool  # always False in 13.4D
    expected_external_write: bool  # always False in 13.4D
    success_criteria: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize scenario to a plain dictionary."""
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "input_text": self.input_text,
            "input_mode": self.input_mode,
            "expected_intent_type": self.expected_intent_type,
            "expected_steps": list(self.expected_steps),
            "expected_artifacts": list(self.expected_artifacts),
            "requires_runtime": self.requires_runtime,
            "requires_permission": self.requires_permission,
            "requires_reconciliation": self.requires_reconciliation,
            "requires_propagation": self.requires_propagation,
            "expected_production_mutation": self.expected_production_mutation,
            "expected_external_write": self.expected_external_write,
            "success_criteria": list(self.success_criteria),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

SCENARIO_A = AcceptanceScenario(
    scenario_id="oas-a",
    name="Primary EOS Dashboard Build Intent",
    input_text=(
        "I want to build the first EOS operating dashboard for Empyrean Studios. "
        "Use what UMH knows, inspect the current state, and run a governed "
        "developer workcell to tell me the highest-leverage implementation plan."
    ),
    input_mode="text",
    expected_intent_type="create_work",
    expected_steps=[
        "classify_intent",
        "create_or_load_work_packet",
        "run_context_diagnostic",
        "generate_propagation_preview",
        "generate_workload_placement",
        "generate_runtime_handoff_preview",
        "require_operator_approval",
        "execute_sandbox_runtime",
        "collect_artifacts",
        "produce_implementation_report",
    ],
    expected_artifacts=[
        "work_packet",
        "context_diagnostic",
        "propagation_preview",
        "workload_placement_decision",
        "runtime_handoff_preview",
        "implementation_report",
    ],
    requires_runtime=True,
    requires_permission=False,
    requires_reconciliation=False,
    requires_propagation=True,
    expected_production_mutation=False,
    expected_external_write=False,
    success_criteria=[
        "deterministic intent classification to create_work or runtime_handoff",
        "Work Packet created or loaded",
        "context diagnostic references current known state",
        "propagation preview generated",
        "workload placement decision generated",
        "runtime handoff preview generated with selected runtime and device",
        "Claude Code selected if available, otherwise justified alternative",
        "operator approval required before runtime start",
        "low-risk sandbox runtime produces implementation report artifact",
        "selected runtime and device recorded truthfully",
        "no production mutation",
    ],
)

SCENARIO_B = AcceptanceScenario(
    scenario_id="oas-b",
    name="Roadmap Status + Next Action",
    input_text=(
        "Where are we in the roadmap and what is the highest-leverage next action?"
    ),
    input_mode="text",
    expected_intent_type="query_status",
    expected_steps=[
        "classify_intent",
        "load_roadmap_state",
        "identify_current_phase",
        "identify_blockers",
        "identify_next_action",
        "produce_status_report",
    ],
    expected_artifacts=[
        "status_report",
    ],
    requires_runtime=False,
    requires_permission=False,
    requires_reconciliation=False,
    requires_propagation=False,
    expected_production_mutation=False,
    expected_external_write=False,
    success_criteria=[
        "answer from real roadmap/production truth/operational truth state",
        "current phase identified",
        "standard_multi_runtime mode referenced truthfully",
        "Phase 14 identified as next after 13.4/13.4R completion",
        "next action identified truthfully",
        "no runtime starts",
        "no production mutation",
    ],
)

SCENARIO_C = AcceptanceScenario(
    scenario_id="oas-c",
    name="Reconciliation / Canonical Truth",
    input_text=(
        "Reconcile what UMH understands about EOS handling companies, "
        "entities, and portfolios."
    ),
    input_mode="text",
    expected_intent_type="reconcile",
    expected_steps=[
        "classify_intent",
        "create_reconciliation_session",
        "gather_source_representations",
        "generate_proposals",
        "present_proposals_for_approval",
    ],
    expected_artifacts=[
        "reconciliation_session",
        "reconciliation_proposals",
    ],
    requires_runtime=False,
    requires_permission=False,
    requires_reconciliation=True,
    requires_propagation=False,
    expected_production_mutation=False,
    expected_external_write=False,
    success_criteria=[
        "reconciliation intent classified",
        "ReconciliationSession created",
        "proposals generated if needed",
        "no canonical update auto-applied",
        "approval required for canonization",
    ],
)

SCENARIO_D = AcceptanceScenario(
    scenario_id="oas-d",
    name="Permissioned Cross-Source Diagnostic",
    input_text=(
        "If there is evidence I pay for a tool in email and it appears in "
        "files or workflows, ask me before linking it."
    ),
    input_mode="text",
    expected_intent_type="configure_policy",
    expected_steps=[
        "classify_intent",
        "generate_socratic_permission_request",
        "block_cross_source_linking",
    ],
    expected_artifacts=[
        "permission_request",
    ],
    requires_runtime=False,
    requires_permission=True,
    requires_reconciliation=False,
    requires_propagation=False,
    expected_production_mutation=False,
    expected_external_write=False,
    success_criteria=[
        "Socratic permission request generated",
        "cross-source linking blocked until confirmed",
        "no external account accessed",
        "no canonization",
    ],
)


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

_ALL_SCENARIOS: list[AcceptanceScenario] = [
    SCENARIO_A,
    SCENARIO_B,
    SCENARIO_C,
    SCENARIO_D,
]


def get_all_scenarios() -> list[AcceptanceScenario]:
    """Return all predefined acceptance scenarios."""
    return list(_ALL_SCENARIOS)


def get_scenario(scenario_id: str) -> AcceptanceScenario | None:
    """Return a single scenario by its ID, or None if not found."""
    for scenario in _ALL_SCENARIOS:
        if scenario.scenario_id == scenario_id:
            return scenario
    return None


# ---------------------------------------------------------------------------
# JSON export helper
# ---------------------------------------------------------------------------

def export_scenarios_json() -> str:
    """Serialize all scenarios to a JSON string."""
    payload = {
        "scenarios": [s.to_dict() for s in _ALL_SCENARIOS],
        "count": len(_ALL_SCENARIOS),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps(payload, indent=2)
