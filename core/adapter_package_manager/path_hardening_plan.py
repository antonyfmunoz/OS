"""Path Hardening Plan for Adapter Packages.

Creates explicit work orders for maturing access paths to 100%.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .full_path_maturity import AdapterPathMaturityDecision, AdapterPathSnapshot


@dataclass
class PathHardeningWorkOrder:
    work_order_id: str = ""
    package_id: str = ""
    path_id: str = ""
    path_name: str = ""
    current_status: str = ""
    target_status: str = "complete"
    required_capability: str = ""
    blockers: list[str] = field(default_factory=list)
    required_approvals: list[str] = field(default_factory=list)
    required_mastery_updates: list[str] = field(default_factory=list)
    required_adapter_work: list[str] = field(default_factory=list)
    required_tests: list[str] = field(default_factory=list)
    required_validation: list[str] = field(default_factory=list)
    estimated_sequence: int = 0
    can_be_done_now: bool = False
    cannot_be_done_now_reason: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_order_id": self.work_order_id,
            "package_id": self.package_id,
            "path_id": self.path_id,
            "path_name": self.path_name,
            "current_status": self.current_status,
            "target_status": self.target_status,
            "required_capability": self.required_capability,
            "blockers": self.blockers,
            "required_approvals": self.required_approvals,
            "required_mastery_updates": self.required_mastery_updates,
            "required_adapter_work": self.required_adapter_work,
            "required_tests": self.required_tests,
            "required_validation": self.required_validation,
            "estimated_sequence": self.estimated_sequence,
            "can_be_done_now": self.can_be_done_now,
            "cannot_be_done_now_reason": self.cannot_be_done_now_reason,
            "notes": self.notes,
        }


_CU_HARDENING_STEPS = [
    "mature visible UI ownership",
    "mature UI tab detection",
    "mature tab navigation",
    "mature body extraction",
    "mature scrolling/end detection",
    "mature per-tab provenance",
    "validate against API parity",
]

_MCP_HARDENING_STEPS = [
    "discover available MCP tools",
    "evaluate Google Docs tab support",
    "build read-only governance",
    "prove includeTabsContent or equivalent",
    "emit canonical source records",
    "run parity tests",
]

_CLI_DIRECT_HARDENING_STEPS = [
    "implement direct REST/curl path or standalone CLI",
    "prove includeTabsContent=true",
    "emit canonical source records",
    "run parity tests",
]

_LOCAL_EXPORT_HARDENING_STEPS = [
    "requires export approval",
    "prove exported format preserves tabs or mark unsupported",
    "build parser",
    "run parity tests",
]

_SDK_HARDENING_STEPS = [
    "implement official SDK path or prove existing path",
    "require includeTabsContent=true",
    "run parity tests against API baseline",
]

_BROWSER_EXT_HARDENING_STEPS = [
    "define extension connector requirements",
    "prove DOM/source extraction coverage",
    "governance/no-secret/no-mutation constraints",
    "run parity tests",
]


def create_hardening_work_order(
    decision: AdapterPathMaturityDecision,
) -> PathHardeningWorkOrder:
    wo = PathHardeningWorkOrder(
        work_order_id=f"WO-{decision.package_id}-{decision.path_id}",
        package_id=decision.package_id,
        path_id=decision.path_id,
        path_name=decision.path_name,
        current_status=decision.current_status,
        target_status="complete",
    )

    if decision.blockers:
        wo.blockers = list(decision.blockers)
        wo.can_be_done_now = False
        wo.cannot_be_done_now_reason = f"blocked: {'; '.join(decision.blockers)}"

    if decision.required_approval:
        wo.required_approvals.append(decision.required_approval)
        wo.can_be_done_now = False
        wo.cannot_be_done_now_reason = "requires approval"

    for gap in decision.gaps_to_100:
        if "tool_mastery" in gap.lower() or "mastery" in gap.lower():
            wo.required_mastery_updates.append(gap)
        elif "test" in gap.lower():
            wo.required_tests.append(gap)
        elif "governance" in gap.lower() or "secret" in gap.lower():
            wo.required_adapter_work.append(gap)
        else:
            wo.required_adapter_work.append(gap)

    path_lower = decision.path_name.lower()
    if "computer use" in path_lower or "cu" in path_lower:
        wo.required_validation = list(_CU_HARDENING_STEPS)
        wo.can_be_done_now = False
        wo.cannot_be_done_now_reason = "requires CU infrastructure"
    elif "mcp" in path_lower:
        wo.required_validation = list(_MCP_HARDENING_STEPS)
        if "discover" in wo.required_validation[0]:
            wo.can_be_done_now = False
            wo.cannot_be_done_now_reason = "requires MCP tool discovery"
    elif "cli direct" in path_lower or "cli_direct" in path_lower:
        wo.required_validation = list(_CLI_DIRECT_HARDENING_STEPS)
        wo.can_be_done_now = True
    elif "export" in path_lower or "archive" in path_lower:
        wo.required_validation = list(_LOCAL_EXPORT_HARDENING_STEPS)
        wo.can_be_done_now = False
        wo.cannot_be_done_now_reason = "requires export approval"
    elif "sdk" in path_lower:
        wo.required_validation = list(_SDK_HARDENING_STEPS)
        wo.can_be_done_now = True
    elif "browser ext" in path_lower or "extension" in path_lower:
        wo.required_validation = list(_BROWSER_EXT_HARDENING_STEPS)
        wo.can_be_done_now = False
        wo.cannot_be_done_now_reason = "requires extension development"
    elif "browser automation" in path_lower:
        wo.can_be_done_now = False
        wo.cannot_be_done_now_reason = "requires separate approval"

    if not wo.blockers and not wo.required_approvals and wo.cannot_be_done_now_reason == "":
        wo.can_be_done_now = True

    return wo


def create_hardening_plan_for_package(
    package_id: str,
    path_decisions: list[AdapterPathMaturityDecision],
) -> list[PathHardeningWorkOrder]:
    work_orders: list[PathHardeningWorkOrder] = []
    seq = 1
    for pd in path_decisions:
        if pd.hardening_required:
            wo = create_hardening_work_order(pd)
            wo.estimated_sequence = seq
            work_orders.append(wo)
            seq += 1
    return work_orders


def prioritize_hardening_work_orders(
    work_orders: list[PathHardeningWorkOrder],
) -> list[PathHardeningWorkOrder]:
    doable_now = [wo for wo in work_orders if wo.can_be_done_now]
    blocked = [wo for wo in work_orders if not wo.can_be_done_now]

    for i, wo in enumerate(doable_now, 1):
        wo.estimated_sequence = i
    for i, wo in enumerate(blocked, len(doable_now) + 1):
        wo.estimated_sequence = i

    return doable_now + blocked


def build_path_hardening_plan_report(
    work_orders: list[PathHardeningWorkOrder],
) -> dict[str, Any]:
    doable = [wo for wo in work_orders if wo.can_be_done_now]
    blocked = [wo for wo in work_orders if not wo.can_be_done_now]

    return {
        "total_work_orders": len(work_orders),
        "doable_now": len(doable),
        "blocked": len(blocked),
        "doable_paths": [wo.path_name for wo in doable],
        "blocked_paths": [
            {"path": wo.path_name, "reason": wo.cannot_be_done_now_reason}
            for wo in blocked
        ],
        "work_orders": [wo.to_dict() for wo in work_orders],
    }
