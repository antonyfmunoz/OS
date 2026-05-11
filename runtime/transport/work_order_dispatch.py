"""
Work order dispatch preparation for Phase 94R.

Additive-only module. Prepares dispatch packages and assesses readiness
without calling network, sending to bridge, or executing local actions.

This module:
- Loads/builds a work order via the factory
- Validates it
- Prepares a bridge payload
- Writes a dispatch package file
- Assesses readiness

This module does NOT:
- Call any network endpoint
- Send anything to the bridge
- Execute any local action
- Modify any existing file
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from eos_ai.transport.work_order_contracts import (
    UNIVERSAL_BLOCKED_ACTIONS,
    WorkOrder,
    WorkOrderStatus,
)
from eos_ai.transport.work_order_factory import (

    create_google_workspace_discovery_work_order,
    validate_work_order,
    work_order_to_bridge_payload,
)

import os
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"



class DispatchReadiness(str, Enum):
    READY_TO_DISPATCH = "READY_TO_DISPATCH"
    READY_AFTER_LOCAL_HEALTHCHECK = "READY_AFTER_LOCAL_HEALTHCHECK"
    BLOCKED = "BLOCKED"
    NEEDS_REPAIR = "NEEDS_REPAIR"


@dataclass
class ReadinessCheck:
    name: str
    passed: bool
    detail: str


@dataclass
class DispatchPackage:
    work_order: WorkOrder
    payload: dict
    validation_errors: list[str]
    readiness: DispatchReadiness
    readiness_checks: list[ReadinessCheck]
    created_at: str

    def to_dict(self) -> dict:
        return {
            "work_order": self.work_order.to_dict(),
            "payload": self.payload,
            "validation_errors": self.validation_errors,
            "readiness": self.readiness.value,
            "readiness_checks": [
                {"name": c.name, "passed": c.passed, "detail": c.detail}
                for c in self.readiness_checks
            ],
            "created_at": self.created_at,
        }


_REQUIRED_VPS_FILES = [
    Path(_ROOT) / "services" / "local_bridge_client.py",
    Path(_ROOT) / "services" / "local_bridge_server.py",
    Path(_ROOT) / "services" / "cc_webhook_receiver.py",
    Path(_ROOT) / "eos_ai" / "substrate" / "work_order_contracts.py",
    Path(_ROOT) / "eos_ai" / "substrate" / "work_order_factory.py",
    Path(_ROOT) / "docs" / "operations" / "local_google_workspace_ingestion_work_order_001.md",
    Path(_ROOT) / "docs" / "operations" / "local_google_workspace_ingestion_result_schema_v1.md",
    Path(_ROOT) / "docs" / "operations" / "existing_bridge_binding_plan_v1.md",
]

_REQUIRED_DOC_FILES = [
    Path(_ROOT) / "docs" / "operations" / "bridge_healthcheck_vps_checklist_v1.md",
    Path(_ROOT) / "docs" / "operations" / "bridge_healthcheck_local_checklist_v1.md",
]


def check_vps_file_readiness() -> list[ReadinessCheck]:
    """Check that all required VPS-side files exist."""
    checks = []
    for path in _REQUIRED_VPS_FILES:
        exists = path.exists()
        checks.append(
            ReadinessCheck(
                name=f"file:{path.name}",
                passed=exists,
                detail=f"{path} {'exists' if exists else 'MISSING'}",
            )
        )
    return checks


def check_contract_readiness() -> list[ReadinessCheck]:
    """Check that work order contracts are importable and functional."""
    checks = []

    try:
        wo = create_google_workspace_discovery_work_order()
        checks.append(
            ReadinessCheck(
                name="factory:build",
                passed=True,
                detail=f"Built {wo.work_order_id} with {len(wo.source_targets)} targets",
            )
        )
    except Exception as e:
        checks.append(
            ReadinessCheck(
                name="factory:build",
                passed=False,
                detail=f"Factory failed: {e}",
            )
        )
        return checks

    errors = validate_work_order(wo)
    checks.append(
        ReadinessCheck(
            name="factory:validate",
            passed=len(errors) == 0,
            detail=f"{len(errors)} errors" if errors else "Valid",
        )
    )

    missing_blocked = UNIVERSAL_BLOCKED_ACTIONS - set(wo.blocked_actions)
    checks.append(
        ReadinessCheck(
            name="safety:blocked_actions",
            passed=len(missing_blocked) == 0,
            detail=f"{len(wo.blocked_actions)} blocked actions enforced"
            if not missing_blocked
            else f"Missing: {sorted(missing_blocked)}",
        )
    )

    try:
        payload = work_order_to_bridge_payload(wo)
        serialized = json.dumps(payload)
        checks.append(
            ReadinessCheck(
                name="serialization:payload",
                passed=True,
                detail=f"Payload serializes to {len(serialized)} bytes",
            )
        )
    except Exception as e:
        checks.append(
            ReadinessCheck(
                name="serialization:payload",
                passed=False,
                detail=f"Serialization failed: {e}",
            )
        )

    return checks


def check_local_healthcheck_status(local_healthcheck_passed: bool = False) -> list[ReadinessCheck]:
    """Check local healthcheck gate. Defaults to not passed."""
    return [
        ReadinessCheck(
            name="local:healthcheck",
            passed=local_healthcheck_passed,
            detail="Local healthcheck passed"
            if local_healthcheck_passed
            else "Local healthcheck not yet run",
        )
    ]


def assess_readiness(checks: list[ReadinessCheck]) -> DispatchReadiness:
    """Determine overall dispatch readiness from checks."""
    failed = [c for c in checks if not c.passed]

    if not failed:
        return DispatchReadiness.READY_TO_DISPATCH

    local_only = all(c.name.startswith("local:") for c in failed)
    if local_only:
        return DispatchReadiness.READY_AFTER_LOCAL_HEALTHCHECK

    file_missing = any(c.name.startswith("file:") and not c.passed for c in failed)
    contract_broken = any(
        c.name.startswith(("factory:", "safety:", "serialization:")) and not c.passed
        for c in failed
    )

    if file_missing or contract_broken:
        return DispatchReadiness.NEEDS_REPAIR

    return DispatchReadiness.BLOCKED


def build_dispatch_package(
    local_healthcheck_passed: bool = False,
) -> DispatchPackage:
    """Build a complete dispatch package for Work Order 001."""
    wo = create_google_workspace_discovery_work_order()
    errors = validate_work_order(wo)
    payload = work_order_to_bridge_payload(wo)

    checks: list[ReadinessCheck] = []
    checks.extend(check_vps_file_readiness())
    checks.extend(check_contract_readiness())
    checks.extend(check_local_healthcheck_status(local_healthcheck_passed))

    readiness = assess_readiness(checks)

    return DispatchPackage(
        work_order=wo,
        payload=payload,
        validation_errors=errors,
        readiness=readiness,
        readiness_checks=checks,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def save_dispatch_package(
    package: DispatchPackage,
    directory: str | Path = f"{_ROOT}/eos_ai/.substrate_station/work_orders",
) -> Path:
    """Write dispatch package to JSON file."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{package.work_order.work_order_id}_dispatch.json"
    path.write_text(json.dumps(package.to_dict(), indent=2))
    return path
