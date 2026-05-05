"""
Contract validation tests for Phase 93R.1 work order types.

Tests the work_order_contracts and work_order_factory modules.
Additive-only — does not test or modify any existing substrate module.
"""

import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.work_order_contracts import (
    ALLOWED_TRANSITIONS,
    UNIVERSAL_BLOCKED_ACTIONS,
    AuthorityMode,
    DEFAULT_AUTHORITY,
    SensitivityLevel,
    WorkOrder,
    WorkOrderResult,
    WorkOrderStatus,
    WorkOrderTaskType,
)
from eos_ai.substrate.work_order_factory import (
    create_google_docs_read_export_work_order,
    create_google_workspace_discovery_work_order,
    load_work_order,
    save_work_order,
    validate_work_order,
    work_order_to_bridge_payload,
)


def test_enum_values():
    assert len(WorkOrderStatus) == 11
    assert WorkOrderStatus.CREATED.value == "CREATED"
    assert WorkOrderStatus.CANCELLED.value == "CANCELLED"

    assert len(WorkOrderTaskType) == 9
    assert WorkOrderTaskType.GOOGLE_WORKSPACE_DISCOVERY.value == "GOOGLE_WORKSPACE_DISCOVERY"

    assert len(AuthorityMode) == 4
    assert AuthorityMode.READ_ONLY.value == "READ_ONLY"

    assert len(SensitivityLevel) == 4
    assert SensitivityLevel.MIXED.value == "MIXED"


def test_default_authority_coverage():
    for tt in WorkOrderTaskType:
        assert tt in DEFAULT_AUTHORITY, f"Missing default authority for {tt.value}"


def test_universal_blocked_actions():
    assert len(UNIVERSAL_BLOCKED_ACTIONS) == 16
    assert "capture_credentials" in UNIVERSAL_BLOCKED_ACTIONS
    assert "process_payments" in UNIVERSAL_BLOCKED_ACTIONS
    assert "run_arbitrary_shell_commands" in UNIVERSAL_BLOCKED_ACTIONS


def test_allowed_transitions_coverage():
    for status in WorkOrderStatus:
        assert status in ALLOWED_TRANSITIONS, f"Missing transitions for {status.value}"


def test_terminal_states_have_no_transitions():
    for terminal in (
        WorkOrderStatus.COMPLETE,
        WorkOrderStatus.PARTIAL,
        WorkOrderStatus.BLOCKED,
        WorkOrderStatus.FAILED,
        WorkOrderStatus.CANCELLED,
    ):
        assert ALLOWED_TRANSITIONS[terminal] == set(), (
            f"Terminal state {terminal.value} should have no transitions"
        )


def test_work_order_creation():
    wo = WorkOrder(
        work_order_id="wo_test123",
        created_by_node="vps-orchestrator",
        assigned_to_node="antony-workstation",
        task_type=WorkOrderTaskType.GOOGLE_WORKSPACE_DISCOVERY,
        objective="Test objective",
        source_targets=["Google Drive root"],
        allowed_actions=["navigate", "list"],
        blocked_actions=[],
        authority_mode=AuthorityMode.READ_ONLY,
        sensitivity_level=SensitivityLevel.MIXED,
        evidence_required=True,
        expected_outputs=["folder_tree"],
        timeout_minutes=60,
    )
    assert wo.status == WorkOrderStatus.CREATED
    assert wo.work_order_id == "wo_test123"
    assert len(wo.audit_notes) == 1
    assert "CREATED" in wo.audit_notes[0]
    for blocked in UNIVERSAL_BLOCKED_ACTIONS:
        assert blocked in wo.blocked_actions


def test_work_order_transition_happy_path():
    wo = WorkOrder(
        work_order_id="wo_test_trans",
        created_by_node="vps",
        assigned_to_node="local",
        task_type=WorkOrderTaskType.LOCAL_SOURCE_INVENTORY,
        objective="test",
        source_targets=["~/"],
        allowed_actions=["list"],
        blocked_actions=[],
        authority_mode=AuthorityMode.READ_ONLY,
        sensitivity_level=SensitivityLevel.PUBLIC,
        evidence_required=False,
        expected_outputs=["inventory"],
        timeout_minutes=30,
    )
    wo.transition(WorkOrderStatus.QUEUED, "queued for dispatch")
    assert wo.status == WorkOrderStatus.QUEUED

    wo.transition(WorkOrderStatus.SENT_TO_LOCAL, "bridge healthy")
    assert wo.status == WorkOrderStatus.SENT_TO_LOCAL

    wo.transition(WorkOrderStatus.CLAIMED_BY_LOCAL)
    assert wo.status == WorkOrderStatus.CLAIMED_BY_LOCAL
    assert wo.claimed_at is not None

    wo.transition(WorkOrderStatus.IN_PROGRESS)
    assert wo.status == WorkOrderStatus.IN_PROGRESS

    wo.transition(WorkOrderStatus.COMPLETE, "all outputs produced")
    assert wo.status == WorkOrderStatus.COMPLETE
    assert wo.completed_at is not None
    assert len(wo.audit_notes) >= 6


def test_work_order_transition_approval_loop():
    wo = WorkOrder(
        work_order_id="wo_test_approval",
        created_by_node="vps",
        assigned_to_node="local",
        task_type=WorkOrderTaskType.GOOGLE_DOCS_READ_EXPORT,
        objective="read docs",
        source_targets=["doc1"],
        allowed_actions=["read"],
        blocked_actions=[],
        authority_mode=AuthorityMode.APPROVAL_REQUIRED,
        sensitivity_level=SensitivityLevel.PRIVATE,
        evidence_required=True,
        expected_outputs=["summaries"],
        timeout_minutes=60,
    )
    wo.transition(WorkOrderStatus.QUEUED)
    wo.transition(WorkOrderStatus.SENT_TO_LOCAL)
    wo.transition(WorkOrderStatus.CLAIMED_BY_LOCAL)
    wo.transition(WorkOrderStatus.IN_PROGRESS)
    wo.transition(WorkOrderStatus.WAITING_FOR_USER_APPROVAL, "read doc1?")
    assert wo.status == WorkOrderStatus.WAITING_FOR_USER_APPROVAL

    wo.transition(WorkOrderStatus.IN_PROGRESS, "approved by founder")
    assert wo.status == WorkOrderStatus.IN_PROGRESS

    wo.transition(WorkOrderStatus.PARTIAL, "1 of 2 docs read")
    assert wo.status == WorkOrderStatus.PARTIAL


def test_work_order_invalid_transition():
    wo = WorkOrder(
        work_order_id="wo_test_invalid",
        created_by_node="vps",
        assigned_to_node="local",
        task_type=WorkOrderTaskType.LOCAL_SOURCE_INVENTORY,
        objective="test",
        source_targets=["~/"],
        allowed_actions=["list"],
        blocked_actions=[],
        authority_mode=AuthorityMode.READ_ONLY,
        sensitivity_level=SensitivityLevel.PUBLIC,
        evidence_required=False,
        expected_outputs=["inventory"],
        timeout_minutes=30,
    )
    try:
        wo.transition(WorkOrderStatus.COMPLETE)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Cannot transition" in str(e)


def test_work_order_serialization_roundtrip():
    wo = WorkOrder(
        work_order_id="wo_roundtrip",
        created_by_node="vps-orchestrator",
        assigned_to_node="antony-workstation",
        task_type=WorkOrderTaskType.GOOGLE_WORKSPACE_DISCOVERY,
        objective="Roundtrip test",
        source_targets=["Google Drive"],
        allowed_actions=["navigate"],
        blocked_actions=[],
        authority_mode=AuthorityMode.READ_ONLY,
        sensitivity_level=SensitivityLevel.MIXED,
        evidence_required=True,
        expected_outputs=["folder_tree"],
        timeout_minutes=120,
    )
    d = wo.to_dict()
    assert isinstance(d, dict)
    assert d["work_order_id"] == "wo_roundtrip"
    assert d["task_type"] == "GOOGLE_WORKSPACE_DISCOVERY"

    json_str = json.dumps(d)
    parsed = json.loads(json_str)
    wo2 = WorkOrder.from_dict(parsed)
    assert wo2.work_order_id == wo.work_order_id
    assert wo2.task_type == wo.task_type
    assert wo2.authority_mode == wo.authority_mode


def test_work_order_result_roundtrip():
    result = WorkOrderResult(
        work_order_id="wo_test_result",
        result_id="result_wo_test_result_20260504",
        schema_version="gws_ingestion_result_v1",
        executing_node="antony-workstation",
        execution_start="2026-05-04T10:00:00Z",
        execution_end="2026-05-04T11:00:00Z",
        execution_duration_minutes=60,
        status=WorkOrderStatus.COMPLETE,
        sources_accessed=["Google Drive root", "Initiate Arena folder"],
        safety_confirmation={
            "no_documents_edited": True,
            "no_files_deleted": True,
            "all_actions_logged": True,
        },
        approval_log=[
            {
                "action_requested": "read doc",
                "response": "APPROVED",
                "responded_by": "founder",
            }
        ],
        audit_notes=["2026-05-04T10:00:00Z | started"],
        evidence_paths=["/home/user/evidence/screenshot.png"],
        evidence_transferred=False,
        data={"total_documents": 24},
    )
    d = result.to_dict()
    assert d["status"] == "COMPLETE"
    assert d["execution_duration_minutes"] == 60

    result2 = WorkOrderResult.from_dict(d)
    assert result2.work_order_id == result.work_order_id
    assert result2.status == WorkOrderStatus.COMPLETE


def test_factory_gws_discovery():
    wo = create_google_workspace_discovery_work_order()
    assert wo.task_type == WorkOrderTaskType.GOOGLE_WORKSPACE_DISCOVERY
    assert wo.authority_mode == AuthorityMode.READ_ONLY
    assert wo.sensitivity_level == SensitivityLevel.MIXED
    assert wo.evidence_required is True
    assert wo.timeout_minutes == 120
    assert wo.work_order_id.startswith("wo_")
    assert len(wo.source_targets) >= 10
    assert "Initiate Arena materials" in wo.source_targets

    errors = validate_work_order(wo)
    assert errors == [], f"Factory output should be valid: {errors}"


def test_factory_gws_read_export():
    wo = create_google_docs_read_export_work_order(
        document_titles=["Doc A", "Doc B"],
        folder_path="My Drive/Initiate Arena",
    )
    assert wo.task_type == WorkOrderTaskType.GOOGLE_DOCS_READ_EXPORT
    assert wo.authority_mode == AuthorityMode.APPROVAL_REQUIRED
    assert len(wo.source_targets) == 2

    errors = validate_work_order(wo)
    assert errors == [], f"Factory output should be valid: {errors}"


def test_validate_catches_missing_fields():
    wo = WorkOrder(
        work_order_id="bad_id",
        created_by_node="",
        assigned_to_node="local",
        task_type=WorkOrderTaskType.LOCAL_SOURCE_INVENTORY,
        objective="",
        source_targets=[],
        allowed_actions=[],
        blocked_actions=[],
        authority_mode=AuthorityMode.READ_ONLY,
        sensitivity_level=SensitivityLevel.PUBLIC,
        evidence_required=False,
        expected_outputs=["inventory"],
        timeout_minutes=0,
    )
    errors = validate_work_order(wo)
    assert any("work_order_id must start with 'wo_'" in e for e in errors)
    assert any("created_by_node" in e for e in errors)
    assert any("objective" in e for e in errors)
    assert any("source_targets" in e for e in errors)
    assert any("allowed_actions" in e for e in errors)
    assert any("timeout_minutes" in e for e in errors)


def test_bridge_payload():
    wo = create_google_workspace_discovery_work_order()
    payload = work_order_to_bridge_payload(wo)
    assert isinstance(payload, dict)
    assert "work_order_id" in payload
    assert "task_type" in payload
    assert payload["task_type"] == "GOOGLE_WORKSPACE_DISCOVERY"


def test_save_and_load():
    wo = create_google_workspace_discovery_work_order()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_work_order(wo, tmpdir)
        assert path.exists()
        assert path.name == f"{wo.work_order_id}.json"

        loaded = load_work_order(path)
        assert loaded.work_order_id == wo.work_order_id
        assert loaded.task_type == wo.task_type
        assert loaded.objective == wo.objective


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  PASS  {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed out of {len(tests)} tests")
    sys.exit(1 if failed else 0)
