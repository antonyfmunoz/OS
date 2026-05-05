"""
Tests for Phase 11C — Cell Runtime + Control Plane Bridge v1.

Verifies:
  - Cell model serialization/roundtrip
  - Cell lifecycle: spawn → hydrate → activate → checkpoint → terminate
  - Invalid transitions are rejected
  - Execution requests do NOT execute directly
  - Execution requests emit append-only signals
  - Bridge delegates to control plane, not adapters
  - No subprocess/docker/tmux/shell imports in umh/cells
  - No adapter imports in umh/cells
  - Cell registry type definitions
  - Phase 11B regression
"""

import sys

sys.path.insert(0, "/opt/OS")

import json
import os
import re

from umh.brains.profile import AuthorityLevel
from umh.cells.models import (
    CellCheckpoint,
    CellContext,
    CellExecutionRequest,
    CellIdentity,
    CellResult,
    CellStatus,
    CellType,
    InvalidTransitionError,
    RequestStatus,
    validate_transition,
)
from umh.cells.runtime import (
    activate_cell,
    checkpoint_cell,
    clear as clear_cells,
    fail_cell,
    get_cell,
    get_cell_status,
    get_checkpoints,
    hydrate_cell,
    list_cells,
    list_execution_requests,
    request_execution,
    spawn_cell,
    terminate_cell,
)
from umh.cells.registry import (
    CellTypeDefinition,
    clear as clear_registry,
    ensure_default_types,
    get_cell_type,
    list_cell_types,
    register_cell_type,
)
from umh.cells.bridge import submit_request


# ─── Model serialization ──────────────────────────────────────────


def test_cell_identity_creation():
    ci = CellIdentity(cell_id="c1", cell_type=CellType.PLANNING)
    assert ci.cell_id == "c1"
    assert ci.cell_type == CellType.PLANNING
    assert ci.created_at != ""
    assert ci.parent_cell_id is None
    print("  PASS: cell_identity_creation")


def test_cell_identity_validation():
    try:
        CellIdentity(cell_id="", cell_type=CellType.PLANNING)
        assert False, "Should have raised"
    except ValueError:
        pass
    print("  PASS: cell_identity_validation")


def test_cell_identity_frozen():
    ci = CellIdentity(cell_id="c1", cell_type=CellType.PLANNING)
    try:
        ci.cell_id = "c2"
        assert False, "Should have raised"
    except AttributeError:
        pass
    print("  PASS: cell_identity_frozen")


def test_cell_identity_serialization():
    ci = CellIdentity(
        cell_id="c1",
        cell_type=CellType.PLANNING,
        parent_cell_id="p1",
        profile_id="brain_1",
        lineage=("root", "p1"),
        metadata={"key": "val"},
    )
    d = ci.to_dict()
    assert d["cell_id"] == "c1"
    assert d["cell_type"] == "planning"
    assert d["parent_cell_id"] == "p1"
    assert d["lineage"] == ["root", "p1"]

    serialized = json.dumps(d)
    assert '"cell_id"' in serialized

    ci2 = CellIdentity.from_dict(d)
    assert ci2.cell_id == ci.cell_id
    assert ci2.cell_type == CellType.PLANNING
    assert ci2.lineage == ("root", "p1")
    print("  PASS: cell_identity_serialization")


def test_cell_context_serialization():
    ctx = CellContext(
        cell_id="c1",
        objective="analyze market",
        active_primitives=("goal", "action"),
        authority_level=AuthorityLevel.EXECUTE,
    )
    d = ctx.to_dict()
    assert d["authority_level"] == "execute"
    assert d["objective"] == "analyze market"

    ctx2 = CellContext.from_dict(d)
    assert ctx2.authority_level == AuthorityLevel.EXECUTE
    assert ctx2.objective == "analyze market"
    print("  PASS: cell_context_serialization")


def test_execution_request_serialization():
    req = CellExecutionRequest(
        request_id="r1",
        cell_id="c1",
        objective="deploy changes",
        operation="shell_command",
        inputs={"cmd": "git push"},
        constraints=("no_force_push",),
        required_capabilities=("git",),
        authority_level=AuthorityLevel.PROPOSE,
    )
    d = req.to_dict()
    assert d["operation"] == "shell_command"
    assert d["constraints"] == ["no_force_push"]

    serialized = json.dumps(d)
    assert '"request_id"' in serialized

    req2 = CellExecutionRequest.from_dict(d)
    assert req2.request_id == "r1"
    assert req2.constraints == ("no_force_push",)
    print("  PASS: execution_request_serialization")


def test_execution_request_validation():
    try:
        CellExecutionRequest(request_id="", cell_id="c1", objective="x", operation="y")
        assert False, "Should have raised"
    except ValueError:
        pass
    try:
        CellExecutionRequest(request_id="r1", cell_id="", objective="x", operation="y")
        assert False, "Should have raised"
    except ValueError:
        pass
    try:
        CellExecutionRequest(request_id="r1", cell_id="c1", objective="", operation="y")
        assert False, "Should have raised"
    except ValueError:
        pass
    print("  PASS: execution_request_validation")


def test_cell_result_serialization():
    res = CellResult(
        request_id="r1",
        cell_id="c1",
        status=RequestStatus.DELEGATED,
        plan_id="plan_abc",
        outputs={"plan_status": "validated"},
    )
    d = res.to_dict()
    assert d["status"] == "delegated"
    assert d["plan_id"] == "plan_abc"

    serialized = json.dumps(d)
    assert '"request_id"' in serialized
    print("  PASS: cell_result_serialization")


def test_checkpoint_serialization():
    ckpt = CellCheckpoint(
        checkpoint_id="ckpt_1",
        cell_id="c1",
        status=CellStatus.CHECKPOINTED,
        context={"objective": "test"},
        version=3,
    )
    d = ckpt.to_dict()
    assert d["version"] == 3
    assert d["status"] == "checkpointed"
    print("  PASS: checkpoint_serialization")


# ─── Lifecycle ─────────────────────────────────────────────────────


def test_spawn_cell():
    clear_cells()
    identity = spawn_cell(CellType.PLANNING)
    assert identity.cell_id.startswith("cell_")
    assert identity.cell_type == CellType.PLANNING

    state = get_cell(identity.cell_id)
    assert state is not None
    assert state["status"] == "created"
    print("  PASS: spawn_cell")


def test_hydrate_cell():
    clear_cells()
    identity = spawn_cell(CellType.INTERPRETATION)
    ctx = CellContext(
        cell_id=identity.cell_id,
        objective="interpret market signals",
        active_primitives=("signal", "state"),
    )
    hydrate_cell(identity.cell_id, ctx)

    state = get_cell(identity.cell_id)
    assert state["status"] == "hydrated"
    assert state["context"]["objective"] == "interpret market signals"
    print("  PASS: hydrate_cell")


def test_activate_cell():
    clear_cells()
    identity = spawn_cell(CellType.REVIEW)
    ctx = CellContext(cell_id=identity.cell_id, objective="review plan")
    hydrate_cell(identity.cell_id, ctx)
    activate_cell(identity.cell_id)

    assert get_cell_status(identity.cell_id) == CellStatus.ACTIVE
    print("  PASS: activate_cell")


def test_checkpoint_cell():
    clear_cells()
    identity = spawn_cell(CellType.PLANNING)
    ctx = CellContext(cell_id=identity.cell_id, objective="plan execution")
    hydrate_cell(identity.cell_id, ctx)
    activate_cell(identity.cell_id)

    ckpt = checkpoint_cell(identity.cell_id)
    assert ckpt.checkpoint_id.startswith("ckpt_")
    assert ckpt.version > 0
    assert get_cell_status(identity.cell_id) == CellStatus.CHECKPOINTED

    checkpoints = get_checkpoints(identity.cell_id)
    assert len(checkpoints) == 1
    print("  PASS: checkpoint_cell")


def test_terminate_cell():
    clear_cells()
    identity = spawn_cell(CellType.MONITOR)
    terminate_cell(identity.cell_id, reason="test cleanup")

    assert get_cell_status(identity.cell_id) == CellStatus.TERMINATED
    print("  PASS: terminate_cell")


def test_fail_cell():
    clear_cells()
    identity = spawn_cell(CellType.DEBUG)
    ctx = CellContext(cell_id=identity.cell_id, objective="debug failure")
    hydrate_cell(identity.cell_id, ctx)
    fail_cell(identity.cell_id, error="unrecoverable")

    assert get_cell_status(identity.cell_id) == CellStatus.FAILED
    print("  PASS: fail_cell")


def test_full_lifecycle():
    """Test complete lifecycle: spawn → hydrate → activate → checkpoint → rehydrate → activate → terminate."""
    clear_cells()
    identity = spawn_cell(CellType.EXECUTION_REQUESTER, profile_id="system")
    assert get_cell_status(identity.cell_id) == CellStatus.CREATED

    ctx = CellContext(cell_id=identity.cell_id, objective="full lifecycle test")
    hydrate_cell(identity.cell_id, ctx)
    assert get_cell_status(identity.cell_id) == CellStatus.HYDRATED

    activate_cell(identity.cell_id)
    assert get_cell_status(identity.cell_id) == CellStatus.ACTIVE

    ckpt = checkpoint_cell(identity.cell_id)
    assert get_cell_status(identity.cell_id) == CellStatus.CHECKPOINTED

    hydrate_cell(identity.cell_id, ctx)
    assert get_cell_status(identity.cell_id) == CellStatus.HYDRATED

    activate_cell(identity.cell_id)
    assert get_cell_status(identity.cell_id) == CellStatus.ACTIVE

    terminate_cell(identity.cell_id)
    assert get_cell_status(identity.cell_id) == CellStatus.TERMINATED
    print("  PASS: full_lifecycle")


def test_parent_lineage():
    clear_cells()
    parent = spawn_cell(CellType.PLANNING)
    child = spawn_cell(CellType.DECOMPOSITION, parent_cell_id=parent.cell_id)
    grandchild = spawn_cell(CellType.REVIEW, parent_cell_id=child.cell_id)

    assert child.parent_cell_id == parent.cell_id
    assert child.lineage == (parent.cell_id,)
    assert grandchild.lineage == (parent.cell_id, child.cell_id)
    print("  PASS: parent_lineage")


# ─── Invalid transitions ──────────────────────────────────────────


def test_invalid_transition_created_to_active():
    """Cannot go directly from CREATED to ACTIVE."""
    try:
        validate_transition("test", CellStatus.CREATED, CellStatus.ACTIVE)
        assert False, "Should have raised"
    except InvalidTransitionError as e:
        assert "created" in str(e)
        assert "active" in str(e)
    print("  PASS: invalid_transition_created_to_active")


def test_invalid_transition_terminated():
    """Cannot transition from TERMINATED."""
    for target in CellStatus:
        if target == CellStatus.TERMINATED:
            continue
        try:
            validate_transition("test", CellStatus.TERMINATED, target)
            assert False, f"Should have raised for TERMINATED → {target.value}"
        except InvalidTransitionError:
            pass
    print("  PASS: invalid_transition_terminated")


def test_invalid_transition_failed():
    """Cannot transition from FAILED."""
    for target in CellStatus:
        if target == CellStatus.FAILED:
            continue
        try:
            validate_transition("test", CellStatus.FAILED, target)
            assert False, f"Should have raised for FAILED → {target.value}"
        except InvalidTransitionError:
            pass
    print("  PASS: invalid_transition_failed")


def test_double_terminate():
    clear_cells()
    identity = spawn_cell(CellType.MONITOR)
    terminate_cell(identity.cell_id)

    try:
        terminate_cell(identity.cell_id)
        assert False, "Should have raised"
    except (InvalidTransitionError, ValueError):
        pass
    print("  PASS: double_terminate")


# ─── Execution requests ───────────────────────────────────────────


def test_execution_request_does_not_execute():
    """Execution request creates a request object but does NOT execute."""
    clear_cells()
    identity = spawn_cell(CellType.EXECUTION_REQUESTER)
    ctx = CellContext(cell_id=identity.cell_id, objective="test execution boundary")
    hydrate_cell(identity.cell_id, ctx)
    activate_cell(identity.cell_id)

    req = request_execution(
        identity.cell_id,
        objective="run git status",
        operation="shell_command",
        inputs={"cmd": "git status"},
    )

    assert req.request_id.startswith("creq_")
    assert req.cell_id == identity.cell_id
    assert req.objective == "run git status"
    assert req.operation == "shell_command"

    assert get_cell_status(identity.cell_id) == CellStatus.WAITING

    requests = list_execution_requests(identity.cell_id)
    assert len(requests) == 1
    assert requests[0].request_id == req.request_id
    print("  PASS: execution_request_does_not_execute")


def test_execution_request_emits_signal():
    """Execution request emits an append-only signal."""
    from umh.brains.signals import clear as clear_signals, list_signals

    clear_cells()
    clear_signals()

    identity = spawn_cell(CellType.EXECUTION_REQUESTER)
    ctx = CellContext(cell_id=identity.cell_id, objective="signal test")
    hydrate_cell(identity.cell_id, ctx)
    activate_cell(identity.cell_id)

    request_execution(identity.cell_id, objective="test op", operation="test")

    signals = list_signals("cell_runtime", signal_type="cell.execution_requested")
    assert len(signals) >= 1
    latest = signals[0]
    assert latest.payload["cell_id"] == identity.cell_id
    print("  PASS: execution_request_emits_signal")


def test_execution_request_requires_active():
    """Only ACTIVE cells can request execution."""
    clear_cells()
    identity = spawn_cell(CellType.EXECUTION_REQUESTER)

    try:
        request_execution(identity.cell_id, objective="fail", operation="test")
        assert False, "Should have raised"
    except ValueError as e:
        assert "ACTIVE" in str(e)
    print("  PASS: execution_request_requires_active")


# ─── Bridge ────────────────────────────────────────────────────────


def test_bridge_returns_result():
    """Bridge returns a CellResult with appropriate status."""
    req = CellExecutionRequest(
        request_id="br_1",
        cell_id="c1",
        objective="test bridge",
        operation="classify_intent",
    )

    result = submit_request(req)

    assert result.request_id == "br_1"
    assert result.cell_id == "c1"
    assert result.status in (RequestStatus.DELEGATED, RequestStatus.REJECTED, RequestStatus.PENDING)
    print("  PASS: bridge_returns_result")


def test_bridge_does_not_execute():
    """Bridge delegates to planner — it does not execute directly."""
    req = CellExecutionRequest(
        request_id="br_2",
        cell_id="c2",
        objective="run shell command",
        operation="shell_command",
        inputs={"cmd": "echo hello"},
    )

    result = submit_request(req)

    assert result.status != RequestStatus.COMPLETED
    print("  PASS: bridge_does_not_execute")


# ─── Registry ─────────────────────────────────────────────────────


def test_registry_default_types():
    clear_registry()
    created = ensure_default_types()
    assert CellType.PLANNING in created
    assert CellType.INTERPRETATION in created
    assert CellType.MONITOR in created

    types = list_cell_types()
    assert len(types) >= 9

    planning = get_cell_type(CellType.PLANNING)
    assert planning is not None
    assert planning.description != ""
    print("  PASS: registry_default_types")


def test_registry_idempotent():
    clear_registry()
    first = ensure_default_types()
    second = ensure_default_types()
    assert len(second) == 0
    print("  PASS: registry_idempotent")


def test_registry_custom_type():
    clear_registry()
    defn = CellTypeDefinition(
        cell_type=CellType.CUSTOM,
        description="Custom cell for testing",
        default_authority="execute",
        required_capabilities=("special_tool",),
    )
    register_cell_type(defn)

    retrieved = get_cell_type(CellType.CUSTOM)
    assert retrieved is not None
    assert retrieved.description == "Custom cell for testing"
    assert retrieved.required_capabilities == ("special_tool",)
    print("  PASS: registry_custom_type")


def test_registry_definition_serialization():
    defn = CellTypeDefinition(
        cell_type=CellType.REVIEW,
        description="Review cell",
        default_primitives=("feedback",),
    )
    d = defn.to_dict()
    assert d["cell_type"] == "review"
    assert d["default_primitives"] == ["feedback"]

    serialized = json.dumps(d)
    assert '"cell_type"' in serialized
    print("  PASS: registry_definition_serialization")


# ─── List/query ────────────────────────────────────────────────────


def test_list_cells():
    clear_cells()
    spawn_cell(CellType.PLANNING)
    spawn_cell(CellType.MONITOR)
    spawn_cell(CellType.PLANNING)

    all_cells = list_cells()
    assert len(all_cells) == 3

    planning_cells = list_cells(cell_type=CellType.PLANNING)
    assert len(planning_cells) == 2

    monitor_cells = list_cells(cell_type=CellType.MONITOR)
    assert len(monitor_cells) == 1
    print("  PASS: list_cells")


def test_list_cells_by_status():
    clear_cells()
    id1 = spawn_cell(CellType.PLANNING)
    id2 = spawn_cell(CellType.MONITOR)
    terminate_cell(id2.cell_id)

    created = list_cells(status=CellStatus.CREATED)
    assert len(created) == 1
    terminated = list_cells(status=CellStatus.TERMINATED)
    assert len(terminated) == 1
    print("  PASS: list_cells_by_status")


def test_get_nonexistent_cell():
    clear_cells()
    assert get_cell("nonexistent") is None
    assert get_cell_status("nonexistent") is None
    print("  PASS: get_nonexistent_cell")


# ─── Boundary safety ──────────────────────────────────────────────


def test_no_subprocess_imports():
    """Cell modules must not import subprocess."""
    cells_dir = "/opt/OS/umh/cells/"
    forbidden = re.compile(
        r"^\s*(?:from|import)\s+(?:subprocess|docker|os\.system|os\.popen)"
    )

    for fname in os.listdir(cells_dir):
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(cells_dir, fname)
        with open(fpath) as f:
            for i, line in enumerate(f, 1):
                assert not forbidden.match(line), f"Forbidden import in {fpath}:{i}: {line.strip()}"
    print("  PASS: no_subprocess_imports")


def test_no_adapter_imports():
    """Cell modules must not import from adapters."""
    cells_dir = "/opt/OS/umh/cells/"
    forbidden = re.compile(r"^\s*(?:from|import)\s+umh\.adapters")

    for fname in os.listdir(cells_dir):
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(cells_dir, fname)
        with open(fpath) as f:
            for i, line in enumerate(f, 1):
                assert not forbidden.match(line), f"Adapter import in {fpath}:{i}: {line.strip()}"
    print("  PASS: no_adapter_imports")


def test_no_execution_imports():
    """Cell modules must not import from execution engine directly."""
    cells_dir = "/opt/OS/umh/cells/"
    forbidden = re.compile(r"^\s*from\s+umh\.execution")

    for fname in os.listdir(cells_dir):
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(cells_dir, fname)
        with open(fpath) as f:
            for i, line in enumerate(f, 1):
                if "TYPE_CHECKING" in line:
                    continue
                assert not forbidden.match(line), f"Execution import in {fpath}:{i}: {line.strip()}"
    print("  PASS: no_execution_imports")


def test_no_shell_true():
    """Cell modules must not use shell=True."""
    cells_dir = "/opt/OS/umh/cells/"
    for fname in os.listdir(cells_dir):
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(cells_dir, fname)
        with open(fpath) as f:
            content = f.read()
            assert "shell=True" not in content, f"shell=True found in {fpath}"
    print("  PASS: no_shell_true")


def test_brain_modules_still_execution_free():
    """Brain modules remain free of execution imports (Phase 11B invariant)."""
    brain_dir = "/opt/OS/umh/brains/"
    forbidden = re.compile(r"^\s*(?:from|import)\s+(?:umh\.execution|umh\.adapters|umh\.runtime)")

    for fname in os.listdir(brain_dir):
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(brain_dir, fname)
        with open(fpath) as f:
            for i, line in enumerate(f, 1):
                assert not forbidden.match(line), f"Forbidden import in {fpath}:{i}: {line.strip()}"
    print("  PASS: brain_modules_still_execution_free")


# ─── Phase 11B regression ─────────────────────────────────────────


def test_phase11b_imports():
    """Phase 11B brain system still imports cleanly."""
    from umh.brains import (
        BrainProfile,
        ExpressionState,
        get_brain_registry,
        BrainSignal,
        emit_signal,
    )
    from umh.brains.context import build_brain_context, empty_context
    from umh.brains.registry import ensure_default_brains, resolve_with_inheritance

    assert BrainProfile is not None
    assert ExpressionState is not None
    assert empty_context().brain_id == ""
    print("  PASS: phase11b_imports")


def test_phase11b_brain_registry_works():
    """Phase 11B brain registry operations still work."""
    from umh.brains.registry import clear as clear_brains, register, get, list_brains
    from umh.brains.profile import BrainProfile, AuthorityLevel

    clear_brains()
    p = BrainProfile(brain_id="11c_compat", name="Compat Check", authority=AuthorityLevel.ADMIN)
    register(p)
    assert get("11c_compat") is not None
    assert "11c_compat" in list_brains()
    clear_brains()
    print("  PASS: phase11b_brain_registry_works")


# ─── Runner ───────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing Phase 11C — Cell Runtime + Control Plane Bridge...")
    print()

    print("Model serialization:")
    test_cell_identity_creation()
    test_cell_identity_validation()
    test_cell_identity_frozen()
    test_cell_identity_serialization()
    test_cell_context_serialization()
    test_execution_request_serialization()
    test_execution_request_validation()
    test_cell_result_serialization()
    test_checkpoint_serialization()

    print()
    print("Lifecycle:")
    test_spawn_cell()
    test_hydrate_cell()
    test_activate_cell()
    test_checkpoint_cell()
    test_terminate_cell()
    test_fail_cell()
    test_full_lifecycle()
    test_parent_lineage()

    print()
    print("Invalid transitions:")
    test_invalid_transition_created_to_active()
    test_invalid_transition_terminated()
    test_invalid_transition_failed()
    test_double_terminate()

    print()
    print("Execution requests:")
    test_execution_request_does_not_execute()
    test_execution_request_emits_signal()
    test_execution_request_requires_active()

    print()
    print("Bridge:")
    test_bridge_returns_result()
    test_bridge_does_not_execute()

    print()
    print("Registry:")
    test_registry_default_types()
    test_registry_idempotent()
    test_registry_custom_type()
    test_registry_definition_serialization()

    print()
    print("List/query:")
    test_list_cells()
    test_list_cells_by_status()
    test_get_nonexistent_cell()

    print()
    print("Boundary safety:")
    test_no_subprocess_imports()
    test_no_adapter_imports()
    test_no_execution_imports()
    test_no_shell_true()
    test_brain_modules_still_execution_free()

    print()
    print("Phase 11B regression:")
    test_phase11b_imports()
    test_phase11b_brain_registry_works()

    print()
    print("All Phase 11C tests passed.")
