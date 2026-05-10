"""CU Proof Audit.

Audits the evidence chain behind Computer Use maturity claims.
Static contract tests alone cannot establish 100% maturity —
auditable proof of actual GUI execution is required.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import json
import os


class CUProofQualityStatus(str, Enum):
    AUDITABLE_PROOF_CONFIRMED = "auditable_proof_confirmed"
    PROVISIONAL_PROOF = "provisional_proof"
    INSUFFICIENT_PROOF = "insufficient_proof"
    STALE_PROOF = "stale_proof"
    SYNTHETIC_ONLY = "synthetic_only"
    FOUNDER_CONFIRMATION_REQUIRED = "founder_confirmation_required"
    BLOCKED = "blocked"


@dataclass
class CUProofAuditResult:
    package_id: str = ""
    path_id: str = ""
    claimed_maturity_percent: float = 0.0
    audited_maturity_percent: float = 0.0
    proof_status: CUProofQualityStatus = CUProofQualityStatus.INSUFFICIENT_PROOF
    evidence_files: list[str] = field(default_factory=list)
    evidence_files_exist: list[bool] = field(default_factory=list)
    live_gui_execution_confirmed: bool = False
    local_worker_confirmed: bool = False
    founder_visual_confirmation_present: bool = False
    account_verified: bool = False
    inventory_verified: bool = False
    api_parity_verified: bool = False
    governance_verified: bool = False
    no_secret_capture_verified: bool = False
    no_mutation_verified: bool = False
    proof_gaps: list[str] = field(default_factory=list)
    recommended_status: str = ""
    recommended_action: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "path_id": self.path_id,
            "claimed_maturity_percent": self.claimed_maturity_percent,
            "audited_maturity_percent": self.audited_maturity_percent,
            "proof_status": self.proof_status.value,
            "evidence_files": self.evidence_files,
            "evidence_files_exist": self.evidence_files_exist,
            "live_gui_execution_confirmed": self.live_gui_execution_confirmed,
            "local_worker_confirmed": self.local_worker_confirmed,
            "founder_visual_confirmation_present": self.founder_visual_confirmation_present,
            "account_verified": self.account_verified,
            "inventory_verified": self.inventory_verified,
            "api_parity_verified": self.api_parity_verified,
            "governance_verified": self.governance_verified,
            "no_secret_capture_verified": self.no_secret_capture_verified,
            "no_mutation_verified": self.no_mutation_verified,
            "proof_gaps": self.proof_gaps,
            "recommended_status": self.recommended_status,
            "recommended_action": self.recommended_action,
            "notes": self.notes,
        }


_W_GDRIVE_CU_001_EVIDENCE_PATHS = [
    "data/drive_cu_inventory/visible_drive_inventory.json",
    "data/drive_cu_inventory/visible_drive_inventory_phase951.json",
    "data/drive_discovery_inventory.json",
]

_W_GDRIVE_CU_001_DOC_PATHS = [
    "docs/system/phase95_w0_001_computer_use_drive_discovery_report.md",
    "docs/system/phase951_w0_001_cu_scroll_inventory_report.md",
    "docs/system/phase95_w0_001_cu_vs_api_inventory_comparison.md",
    "docs/system/phase951_w0_001_cu_final_comparison_report.md",
]


def _check_evidence_file(path: str, base_dir: str = "/opt/OS") -> bool:
    full = os.path.join(base_dir, path)
    return os.path.isfile(full)


def _load_cu_inventory(
    path: str, base_dir: str = "/opt/OS"
) -> dict[str, Any] | None:
    full = os.path.join(base_dir, path)
    if not os.path.isfile(full):
        return None
    try:
        with open(full) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def audit_w_gdrive_cu_001_proof(
    evidence_paths: list[str] | None = None,
    base_dir: str = "/opt/OS",
) -> CUProofAuditResult:
    if evidence_paths is None:
        evidence_paths = _W_GDRIVE_CU_001_EVIDENCE_PATHS + _W_GDRIVE_CU_001_DOC_PATHS

    result = CUProofAuditResult(
        package_id="W-GDRIVE-CU-001",
        path_id="W-GDRIVE-CU-001",
        claimed_maturity_percent=100.0,
    )
    result.evidence_files = list(evidence_paths)
    result.evidence_files_exist = [
        _check_evidence_file(p, base_dir) for p in evidence_paths
    ]

    gaps: list[str] = []
    notes: list[str] = []

    inventory = _load_cu_inventory(
        "data/drive_cu_inventory/visible_drive_inventory.json", base_dir
    )

    if inventory is None:
        gaps.append("primary_evidence_file_missing")
        notes.append("visible_drive_inventory.json not found or unreadable")
    else:
        method = inventory.get("method", "")
        if method == "COMPUTER_USE_ONLY":
            result.live_gui_execution_confirmed = True
            notes.append(
                f"Evidence method: {method} — confirms GUI path, not API"
            )
        else:
            gaps.append("evidence_method_not_computer_use")

        backend = inventory.get("backend", "")
        if "task_scheduler" in backend.lower() or "ui_automation" in backend.lower():
            result.local_worker_confirmed = True
            notes.append(f"Backend: {backend} — local worker execution")
        else:
            gaps.append("local_worker_backend_not_confirmed")

        account = inventory.get("account", "")
        if account and "@" in account:
            result.account_verified = True
            notes.append(f"Account in evidence: {account}")
        else:
            gaps.append("account_not_in_evidence")

        total_items = inventory.get("total_items", 0)
        items = inventory.get("items", [])
        if total_items >= 26 and len(items) >= 26:
            result.inventory_verified = True
            notes.append(f"Inventory: {total_items} items ({len(items)} in items array)")
        else:
            gaps.append("inventory_count_insufficient")

        comparison = inventory.get("comparison", {})
        if comparison:
            matching = comparison.get("matching_count", 0)
            if matching >= 22:
                result.api_parity_verified = True
                notes.append(f"API parity: {matching} names matched")
            else:
                gaps.append("api_parity_matching_insufficient")
        else:
            gaps.append("no_comparison_data_in_evidence")

        if inventory.get("api_used") is False:
            notes.append("api_used=False confirmed")
        else:
            gaps.append("api_used_not_false")

        if inventory.get("playwright_used") is False:
            notes.append("playwright_used=False confirmed")
        else:
            gaps.append("playwright_used_not_false")

        if inventory.get("cdp_used") is False:
            notes.append("cdp_used=False confirmed")
        else:
            gaps.append("cdp_used_not_false")

        if inventory.get("screenshots_stored") is False:
            notes.append("screenshots_stored=False confirmed")
        else:
            gaps.append("screenshots_stored_not_false")

        gov_clean = (
            inventory.get("api_used") is False
            and inventory.get("playwright_used") is False
            and inventory.get("cdp_used") is False
            and inventory.get("screenshots_stored") is False
        )
        if gov_clean:
            result.governance_verified = True
            result.no_secret_capture_verified = True
            result.no_mutation_verified = True
        else:
            gaps.append("governance_flags_not_clean")

    all_docs_exist = all(
        _check_evidence_file(p, base_dir) for p in _W_GDRIVE_CU_001_DOC_PATHS
    )
    if all_docs_exist:
        notes.append("All 4 Phase 95/95.1 report docs exist")
    else:
        gaps.append("phase_95_report_docs_incomplete")

    result.founder_visual_confirmation_present = False
    gaps.append("founder_visual_confirmation_absent")
    notes.append(
        "Founder was not present during Phase 95 GUI execution. "
        "VPS orchestrator drove Task Scheduler /IT remotely. "
        "No independent visual confirmation that the GUI rendered correctly."
    )

    result.proof_gaps = gaps
    result.notes = notes

    evidence_strong = (
        result.live_gui_execution_confirmed
        and result.local_worker_confirmed
        and result.account_verified
        and result.inventory_verified
        and result.api_parity_verified
        and result.governance_verified
    )

    if evidence_strong and result.founder_visual_confirmation_present:
        result.proof_status = CUProofQualityStatus.AUDITABLE_PROOF_CONFIRMED
        result.audited_maturity_percent = 100.0
        result.recommended_status = "complete"
        result.recommended_action = "none — maturity confirmed"
    elif evidence_strong and not result.founder_visual_confirmation_present:
        result.proof_status = CUProofQualityStatus.FOUNDER_CONFIRMATION_REQUIRED
        result.audited_maturity_percent = 100.0
        result.recommended_status = "provisional_100_pending_confirmation"
        result.recommended_action = (
            "Founder must visually confirm local CU execution on Windows "
            "desktop, or re-run CU inventory while present, to finalize "
            "100% maturity."
        )
    elif result.live_gui_execution_confirmed:
        result.proof_status = CUProofQualityStatus.PROVISIONAL_PROOF
        result.audited_maturity_percent = result.claimed_maturity_percent
        result.recommended_status = "provisional_needs_hardening"
        result.recommended_action = "Fill evidence gaps before final maturity"
    elif inventory is not None:
        result.proof_status = CUProofQualityStatus.INSUFFICIENT_PROOF
        result.audited_maturity_percent = 0.0
        result.recommended_status = "insufficient_evidence"
        result.recommended_action = "Re-run CU inventory with proper method"
    else:
        result.proof_status = CUProofQualityStatus.SYNTHETIC_ONLY
        result.audited_maturity_percent = 0.0
        result.recommended_status = "no_evidence"
        result.recommended_action = "Execute CU inventory on local worker"

    return result


def evidence_supports_100_percent_maturity(
    result: CUProofAuditResult,
) -> bool:
    return result.proof_status == CUProofQualityStatus.AUDITABLE_PROOF_CONFIRMED


def cu_proof_requires_downgrade(result: CUProofAuditResult) -> bool:
    return result.proof_status not in (
        CUProofQualityStatus.AUDITABLE_PROOF_CONFIRMED,
        CUProofQualityStatus.FOUNDER_CONFIRMATION_REQUIRED,
    )


def cu_proof_requires_founder_confirmation(
    result: CUProofAuditResult,
) -> bool:
    return (
        result.proof_status == CUProofQualityStatus.FOUNDER_CONFIRMATION_REQUIRED
    )


def build_cu_proof_audit_report(
    result: CUProofAuditResult,
) -> dict[str, Any]:
    return {
        "package_id": result.package_id,
        "claimed_maturity": result.claimed_maturity_percent,
        "audited_maturity": result.audited_maturity_percent,
        "proof_status": result.proof_status.value,
        "evidence_files_found": sum(result.evidence_files_exist),
        "evidence_files_total": len(result.evidence_files),
        "live_gui_confirmed": result.live_gui_execution_confirmed,
        "founder_confirmed": result.founder_visual_confirmation_present,
        "proof_gap_count": len(result.proof_gaps),
        "proof_gaps": result.proof_gaps,
        "recommended_status": result.recommended_status,
        "recommended_action": result.recommended_action,
    }
