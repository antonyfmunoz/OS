"""
Work order factory for Phase 93R.1.

Additive-only module. Creates pre-configured WorkOrder instances
for known task types. Does not import from or modify any existing
substrate module.
"""

from __future__ import annotations

import json
from pathlib import Path

from runtime.transport.work_order_contracts import (
    UNIVERSAL_BLOCKED_ACTIONS,
    AuthorityMode,
    SensitivityLevel,
    WorkOrder,
    WorkOrderStatus,
    WorkOrderTaskType,
    _generate_work_order_id,
    _now_iso,
)


def create_google_workspace_discovery_work_order(
    source_targets: list[str] | None = None,
    timeout_minutes: int = 120,
    assigned_to_node: str = "antony-workstation",
) -> WorkOrder:
    targets = source_targets or [
        "Initiate Arena materials",
        "Lyfe Institute documents",
        "Game of Lyfe documents",
        "UMH materials",
        "EntrepreneurOS / EOS documents",
        "AI Agents documentation",
        "Coaching Frameworks",
        "Antony Munoz Email Sequences",
        "Content strategy / content calendar",
        "Business templates",
        "Automations documentation",
        "Whop / course references",
        "Empyrean Studio documents",
        "Lyfe Spectrum materials",
    ]

    return WorkOrder(
        work_order_id=_generate_work_order_id(),
        created_by_node="vps-orchestrator",
        assigned_to_node=assigned_to_node,
        task_type=WorkOrderTaskType.GOOGLE_WORKSPACE_DISCOVERY,
        objective=(
            "Discover all Google Drive folders and documents relevant to "
            "Munoz Conglomerate ventures. Produce folder tree, document "
            "inventory, sensitivity flags, and venture relevance tags."
        ),
        source_targets=targets,
        allowed_actions=[
            "navigate_google_drive",
            "list_folders",
            "open_folders",
            "read_folder_names",
            "read_document_titles",
            "read_document_metadata",
            "count_documents",
            "take_folder_screenshots",
            "record_folder_hierarchy",
        ],
        blocked_actions=list(UNIVERSAL_BLOCKED_ACTIONS),
        required_approvals=[
            "read_document_content",
            "export_document",
            "access_sensitive_folder",
            "screenshot_document_content",
        ],
        authority_mode=AuthorityMode.READ_ONLY,
        sensitivity_level=SensitivityLevel.MIXED,
        evidence_required=True,
        expected_outputs=[
            "folder_tree_json",
            "document_inventory_json",
            "folder_screenshots",
            "sensitivity_flags",
            "venture_relevance_tags",
            "safety_confirmation",
            "approval_log",
        ],
        result_schema="gws_ingestion_result_v1",
        timeout_minutes=timeout_minutes,
    )


def create_google_docs_read_export_work_order(
    document_titles: list[str],
    folder_path: str,
    timeout_minutes: int = 60,
    assigned_to_node: str = "antony-workstation",
) -> WorkOrder:
    return WorkOrder(
        work_order_id=_generate_work_order_id(),
        created_by_node="vps-orchestrator",
        assigned_to_node=assigned_to_node,
        task_type=WorkOrderTaskType.GOOGLE_DOCS_READ_EXPORT,
        objective=(
            f"Read and optionally export {len(document_titles)} documents "
            f"from '{folder_path}' with founder approval per document."
        ),
        source_targets=document_titles,
        allowed_actions=[
            "open_document",
            "read_document_content",
            "export_document_pdf",
            "export_document_txt",
            "copy_text_content",
            "screenshot_document_content",
        ],
        blocked_actions=list(UNIVERSAL_BLOCKED_ACTIONS),
        required_approvals=[
            "read_document_content",
            "export_document",
            "screenshot_document_content",
        ],
        authority_mode=AuthorityMode.APPROVAL_REQUIRED,
        sensitivity_level=SensitivityLevel.MIXED,
        evidence_required=True,
        expected_outputs=[
            "document_read_summaries",
            "exported_document_files",
            "document_screenshots",
            "safety_confirmation",
            "approval_log",
        ],
        result_schema="gws_ingestion_result_v1",
        timeout_minutes=timeout_minutes,
    )


def validate_work_order(wo: WorkOrder) -> list[str]:
    """Return list of validation errors. Empty list means valid."""
    errors: list[str] = []

    if not wo.work_order_id.startswith("wo_"):
        errors.append(f"work_order_id must start with 'wo_', got '{wo.work_order_id}'")

    if not wo.created_by_node:
        errors.append("created_by_node is required")

    if not wo.assigned_to_node:
        errors.append("assigned_to_node is required")

    if not wo.objective:
        errors.append("objective is required")

    if not wo.source_targets:
        errors.append("source_targets must not be empty")

    if not wo.allowed_actions:
        errors.append("allowed_actions must not be empty")

    if wo.timeout_minutes <= 0:
        errors.append(f"timeout_minutes must be positive, got {wo.timeout_minutes}")

    missing_blocked = UNIVERSAL_BLOCKED_ACTIONS - set(wo.blocked_actions)
    if missing_blocked:
        errors.append(f"blocked_actions missing universal items: {sorted(missing_blocked)}")

    overlap = set(wo.allowed_actions) & set(wo.blocked_actions)
    if overlap:
        errors.append(f"Actions cannot be both allowed and blocked: {sorted(overlap)}")

    return errors


def work_order_to_bridge_payload(wo: WorkOrder) -> dict:
    """Convert work order to the JSON payload for POST /work-order."""
    return wo.to_dict()


def save_work_order(wo: WorkOrder, directory: str | Path) -> Path:
    """Write work order JSON to directory. Returns the file path."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{wo.work_order_id}.json"
    path.write_text(json.dumps(wo.to_dict(), indent=2))
    return path


def load_work_order(path: str | Path) -> WorkOrder:
    """Load a work order from a JSON file."""
    data = json.loads(Path(path).read_text())
    return WorkOrder.from_dict(data)
