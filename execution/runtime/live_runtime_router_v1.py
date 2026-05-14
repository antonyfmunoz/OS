"""Live Runtime Router v1.

Resolves routing decisions for the live runtime spine:
  - capability resolution (what can handle this command)
  - environment resolution (where should it execute)
  - embodiment path resolution (workstation, browser, GUI, runtime)
  - governance path resolution (what governance rules apply)
  - observability path resolution (what telemetry to capture)

All routing decisions emit lineage receipts.
All routing is deterministic and replay-safe.

UMH substrate subsystem. Phase 96.8BR.
"""

from __future__ import annotations

from typing import Any

from .live_runtime_contracts_v1 import (
    RuntimeContext,
    RuntimeDecision,
    RuntimeDecisionType,
    RuntimeLineageReceipt,
    RuntimePhase,
    RuntimeSignal,
    _content_hash,
    _new_id,
)


CAPABILITY_MAP: dict[str, str] = {
    "workstation-status": "workstation_inspection",
    "tmux-status": "workstation_inspection",
    "runtime-sessions": "workstation_inspection",
    "resume-work": "continuity_generation",
    "operational-state": "workstation_inspection",
    "environment-health": "workstation_inspection",
    "replay-validate": "replay_verification",
    "execution-history": "observability_query",
    "mode-info": "workstation_inspection",
    "browser-status": "browser_inspection",
    "browser-tabs": "browser_inspection",
    "browser-inspect": "browser_inspection",
    "browser-summary": "browser_inspection",
    "gui-state": "gui_inspection",
    "visible-actuation-log": "observability_query",
    "runtime-status": "runtime_inspection",
    "runtime-lineage": "observability_query",
    "runtime-open-loops": "continuity_query",
    "runtime-resume": "continuity_generation",
    "runtime-observe": "observability_query",
    "runtime-replay": "replay_verification",
    "runtime-governance": "governance_query",
    "runtime-context": "runtime_inspection",
}

ENVIRONMENT_MAP: dict[str, str] = {
    "workstation_inspection": "vps_local",
    "browser_inspection": "vps_local",
    "gui_inspection": "vps_local",
    "runtime_inspection": "vps_local",
    "continuity_query": "vps_local",
    "continuity_generation": "vps_local",
    "observability_query": "vps_local",
    "replay_verification": "vps_local",
    "governance_query": "vps_local",
    "shell_execution": "vps_local",
    "tmux_execution": "vps_local",
}

EMBODIMENT_MAP: dict[str, str] = {
    "workstation_inspection": "workstation",
    "browser_inspection": "browser",
    "gui_inspection": "browser",
    "runtime_inspection": "runtime",
    "continuity_query": "runtime",
    "continuity_generation": "runtime",
    "observability_query": "runtime",
    "replay_verification": "runtime",
    "governance_query": "runtime",
    "shell_execution": "workstation",
    "tmux_execution": "workstation",
}

RISK_MAP: dict[str, str] = {
    "workstation_inspection": "safe",
    "browser_inspection": "safe",
    "gui_inspection": "safe",
    "runtime_inspection": "safe",
    "continuity_query": "safe",
    "continuity_generation": "safe",
    "observability_query": "safe",
    "replay_verification": "safe",
    "governance_query": "safe",
    "shell_execution": "medium",
    "tmux_execution": "medium",
}


class LiveRuntimeRouter:
    """Resolves capability, environment, embodiment, governance, and observability paths.

    All routing decisions are deterministic and emit lineage receipts.
    """

    def __init__(self) -> None:
        self._routes_resolved: int = 0
        self._decisions: list[RuntimeDecision] = []

    def resolve(
        self,
        signal: RuntimeSignal,
        context: RuntimeContext,
    ) -> RuntimeContext:
        """Resolve all routing dimensions for a runtime context."""
        context.current_phase = RuntimePhase.ROUTING

        capability = self._resolve_capability(context.command_name)
        context.capability_resolved = capability

        environment = self._resolve_environment(capability)
        context.environment_resolved = environment

        embodiment = self._resolve_embodiment(capability)
        context.embodiment_path = embodiment

        risk = self._resolve_risk(capability)
        context.risk_class = risk

        governance_rules = self._resolve_governance_rules(capability, risk)
        context.governance_rules = governance_rules

        decision = RuntimeDecision(
            decision_type=RuntimeDecisionType.ROUTE,
            phase=RuntimePhase.ROUTING,
            input_summary=f"command:{context.command_name}",
            output_summary=(
                f"cap:{capability} env:{environment} embodiment:{embodiment} risk:{risk}"
            ),
            rules_applied=["capability_map", "environment_map", "embodiment_map", "risk_map"],
            approved=True,
            correlation_id=context.correlation_id,
        )
        context.add_decision(decision)
        self._decisions.append(decision)

        receipt = RuntimeLineageReceipt(
            signal_id=signal.signal_id,
            correlation_id=context.correlation_id,
            phase=RuntimePhase.ROUTING,
            action="resolve_routing",
            component="runtime_router",
            input_hash=_content_hash({"command": context.command_name}),
            output_hash=_content_hash(
                {
                    "capability": capability,
                    "environment": environment,
                    "embodiment": embodiment,
                    "risk": risk,
                }
            ),
        )
        context.add_lineage_receipt(receipt.receipt_id)

        self._routes_resolved += 1
        return context

    def resolve_capability(self, command_name: str) -> str:
        return self._resolve_capability(command_name)

    def resolve_embodiment(self, command_name: str) -> str:
        capability = self._resolve_capability(command_name)
        return self._resolve_embodiment(capability)

    def get_stats(self) -> dict[str, Any]:
        return {
            "routes_resolved": self._routes_resolved,
            "decisions_count": len(self._decisions),
            "known_commands": len(CAPABILITY_MAP),
        }

    def _resolve_capability(self, command_name: str) -> str:
        return CAPABILITY_MAP.get(command_name, "general_execution")

    def _resolve_environment(self, capability: str) -> str:
        return ENVIRONMENT_MAP.get(capability, "vps_local")

    def _resolve_embodiment(self, capability: str) -> str:
        return EMBODIMENT_MAP.get(capability, "spine")

    def _resolve_risk(self, capability: str) -> str:
        return RISK_MAP.get(capability, "medium")

    def _resolve_governance_rules(self, capability: str, risk: str) -> list[str]:
        rules = ["CAPABILITY_AUTHORIZED"]
        if risk in ("medium", "high", "critical"):
            rules.append("RISK_ELEVATED")
        if capability.endswith("_execution"):
            rules.append("EXECUTION_GOVERNANCE")
        return rules
