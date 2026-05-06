"""W0-001 packet builder for the Environment Bridge.

Generates the W0-001 CU rerun packet with all required routing fields
so the local worker validates without manual patching.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .work_packet import (
    WorkPacket,
    WorkPacketRiskLevel,
    WorkPacketStatus,
)

W0_001_PACKET_ID = "WP-W0-001-CU-RERUN-001"
W0_001_WORK_ORDER_ID = "WO-LOCAL-PILOT-GDRIVE-GDOCS-001"
W0_001_TARGET_ACCOUNT = "antonyfm@empyreanstudios.co"
W0_001_WORKER_MODE = "auto"
W0_001_APPROVAL_ROUTING = "advisor_relay"
W0_001_PREFERRED_BACKEND = "GUI_COMPUTER_USE"

W0_001_ALLOWED_ACTIONS = [
    "open_google_drive",
    "read_drive_inventory_via_accessibility_tree",
    "open_google_docs",
    "read_docs_tabs_via_accessibility_tree",
    "extract_docs_content_via_foreground",
    "write_result_to_outbox",
    "write_heartbeat",
]

W0_001_BLOCKED_ACTIONS = [
    "credential_capture",
    "token_capture",
    "cookie_capture",
    "account_switching",
    "gmail",
    "edit",
    "delete",
    "move",
    "share",
    "permission_change",
    "export",
    "download",
    "screenshot",
    "ocr",
    "playwright",
    "cdp",
    "memory_promotion",
]

W0_001_PROOF_REQUIREMENTS = [
    "correct_account_visible",
    "drive_visible",
    "drive_inventory_count_26",
    "docs_openability",
    "tab_detection_attempt",
    "content_extraction_attempt",
    "governance_compliance",
    "no_secret_no_mutation_confirmation",
    "founder_confirmation_response",
]

W0_001_EXPECTED_OUTPUTS = [
    "drive_inventory_result.json",
    "docs_tab_detection_result.json",
    "docs_content_extraction_result.json",
    "governance_compliance_report.json",
    "founder_confirmation_response.json",
]

W0_001_REQUIRED_ROUTING_FIELDS = [
    "target_account",
    "worker_mode",
    "approval_routing",
    "preferred_backend",
]


def build_w0_001_packet() -> dict[str, Any]:
    """Build a complete W0-001 packet with all required routing fields."""
    return {
        "packet_id": W0_001_PACKET_ID,
        "work_order_id": W0_001_WORK_ORDER_ID,
        "title": "W0-001 CU Rerun While Founder Present",
        "description": (
            "Re-execute Google Drive and Google Docs Computer Use inventory "
            "on local Windows desktop while founder is physically present. "
            "Founder visually confirms output."
        ),
        "action_type": "cu_rerun_while_present",
        "target_account": W0_001_TARGET_ACCOUNT,
        "worker_mode": W0_001_WORKER_MODE,
        "approval_routing": W0_001_APPROVAL_ROUTING,
        "preferred_backend": W0_001_PREFERRED_BACKEND,
        "target_environment": [
            "local_windows_gui",
            "local_tmux",
            "local_browser",
        ],
        "required_adapter_packages": [
            "W-GWS-CORE-001",
            "W-GDRIVE-CU-001",
            "W-GDOCS-CU-001",
        ],
        "required_tool_mastery_packs": [
            "computer_use_tool_mastery_pack",
            "google_docs_tool_mastery_pack",
        ],
        "required_mastery_categories": ["tool", "environment"],
        "required_worker_runtime": "local-windows-worker",
        "proof_artifact_requirements": [
            "visible_chrome_launch_proof",
            "drive_inventory_json",
            "founder_confirmation",
        ],
        "risk_level": "high",
        "approval_status": "approved",
        "founder_confirmation_required": True,
        "playwright_enabled": False,
        "screenshot_capture": False,
        "cdp_enabled": False,
        "allowed_actions": W0_001_ALLOWED_ACTIONS,
        "blocked_actions": W0_001_BLOCKED_ACTIONS,
        "expected_outputs": W0_001_EXPECTED_OUTPUTS,
        "proof_requirements": W0_001_PROOF_REQUIREMENTS,
        "timeout_seconds": 3600,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": "",
        "status": "approved",
        "required_environment_adapters": ["environment_bridge"],
        "required_human_approval_adapters": ["founder_visual_confirmation"],
        "notes": [
            "Phase 96.8D packet — includes all required routing fields",
            "Direct Chrome executable launch required (not explorer/default-browser)",
            "Visible-window proof required before VERIFY_ACTIVE_GOOGLE_ACCOUNT gate",
            "Primary dispatch: local pull from VPS outbox",
            "Fallback dispatch: manual copy to local inbox",
        ],
    }


def w0_001_packet_has_required_routing(packet: dict[str, Any]) -> list[str]:
    """Return list of missing routing fields."""
    missing: list[str] = []
    if packet.get("target_account") != W0_001_TARGET_ACCOUNT:
        missing.append("target_account")
    if packet.get("worker_mode") != W0_001_WORKER_MODE:
        missing.append("worker_mode")
    if packet.get("approval_routing") != W0_001_APPROVAL_ROUTING:
        missing.append("approval_routing")
    if packet.get("preferred_backend") != W0_001_PREFERRED_BACKEND:
        missing.append("preferred_backend")
    return missing


def w0_001_packet_blocks_playwright(packet: dict[str, Any]) -> bool:
    """Verify playwright/screenshot/cdp are disabled."""
    return (
        not packet.get("playwright_enabled", True)
        and not packet.get("screenshot_capture", True)
        and not packet.get("cdp_enabled", True)
    )
