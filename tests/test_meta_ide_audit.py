"""Tests for Meta IDE functional audit."""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, "/opt/OS")

from substrate.organism.self_use.meta_ide_audit import (
    AuditMatrix,
    FunctionalStatus,
    SubsystemAudit,
    SubsystemOperation,
)


def test_operation_defaults():
    op = SubsystemOperation(name="Create plan")
    assert op.status == FunctionalStatus.NOT_TESTED
    assert op.tested_at is None


def test_subsystem_compute_status_all_functional():
    audit = SubsystemAudit(
        subsystem="planning",
        operations=[
            SubsystemOperation(name="Create plan", status=FunctionalStatus.FUNCTIONAL),
            SubsystemOperation(name="Approve plan", status=FunctionalStatus.FUNCTIONAL),
        ],
    )
    audit.finalize()
    assert audit.overall_status == FunctionalStatus.FUNCTIONAL


def test_subsystem_compute_status_any_broken():
    audit = SubsystemAudit(
        subsystem="work_packets",
        operations=[
            SubsystemOperation(name="Create packet", status=FunctionalStatus.FUNCTIONAL),
            SubsystemOperation(name="Track packet", status=FunctionalStatus.BROKEN),
        ],
    )
    audit.finalize()
    assert audit.overall_status == FunctionalStatus.BROKEN


def test_subsystem_compute_status_partial():
    audit = SubsystemAudit(
        subsystem="execution",
        operations=[
            SubsystemOperation(name="Submit task", status=FunctionalStatus.FUNCTIONAL),
            SubsystemOperation(name="View telemetry", status=FunctionalStatus.PARTIAL),
        ],
    )
    audit.finalize()
    assert audit.overall_status == FunctionalStatus.PARTIAL


def test_subsystem_compute_status_mixed_not_tested():
    audit = SubsystemAudit(
        subsystem="governance",
        operations=[
            SubsystemOperation(name="Challenge scope", status=FunctionalStatus.FUNCTIONAL),
            SubsystemOperation(name="Block bypass", status=FunctionalStatus.NOT_TESTED),
        ],
    )
    audit.finalize()
    assert audit.overall_status == FunctionalStatus.PARTIAL


def test_audit_matrix_record_operation():
    matrix = AuditMatrix()
    op1 = SubsystemOperation(name="Create plan", status=FunctionalStatus.FUNCTIONAL)
    op2 = SubsystemOperation(name="Approve plan", status=FunctionalStatus.FUNCTIONAL)
    matrix.record_operation("planning", op1)
    matrix.record_operation("planning", op2)

    audit = matrix.get("planning")
    assert audit is not None
    assert len(audit.operations) == 2


def test_audit_matrix_critical_path_broken():
    matrix = AuditMatrix()
    matrix.add_subsystem(
        SubsystemAudit(
            subsystem="planning",
            operations=[
                SubsystemOperation(name="Create plan", status=FunctionalStatus.BROKEN),
            ],
        )
    )
    matrix.finalize_all()
    assert matrix.critical_path_broken()


def test_audit_matrix_critical_path_ok():
    matrix = AuditMatrix()
    matrix.add_subsystem(
        SubsystemAudit(
            subsystem="planning",
            operations=[
                SubsystemOperation(name="Create plan", status=FunctionalStatus.FUNCTIONAL),
            ],
        )
    )
    matrix.add_subsystem(
        SubsystemAudit(
            subsystem="organism_runtime",
            operations=[
                SubsystemOperation(name="View state", status=FunctionalStatus.BROKEN),
            ],
        )
    )
    matrix.finalize_all()
    assert not matrix.critical_path_broken()


def test_audit_matrix_summary():
    matrix = AuditMatrix()
    for name in ["planning", "work_packets", "proof_packages"]:
        matrix.add_subsystem(
            SubsystemAudit(
                subsystem=name,
                operations=[
                    SubsystemOperation(name="test", status=FunctionalStatus.FUNCTIONAL),
                ],
            )
        )
    summary = matrix.summary()
    assert summary["subsystems_tested"] == 3
    assert summary["by_status"]["functional"] == 3
    assert not summary["critical_path_broken"]


def test_audit_matrix_markdown():
    matrix = AuditMatrix()
    matrix.add_subsystem(
        SubsystemAudit(
            subsystem="planning",
            operations=[
                SubsystemOperation(name="Create plan", status=FunctionalStatus.FUNCTIONAL),
            ],
        )
    )
    matrix.add_subsystem(
        SubsystemAudit(
            subsystem="execution",
            operations=[
                SubsystemOperation(
                    name="Submit task",
                    status=FunctionalStatus.BROKEN,
                    evidence="404 on submit endpoint",
                ),
            ],
        )
    )
    md = matrix.to_markdown()
    assert "Meta IDE Functional Audit" in md
    assert "planning" in md
    assert "BROKEN" in md


def test_audit_matrix_json_roundtrip():
    matrix = AuditMatrix()
    matrix.add_subsystem(
        SubsystemAudit(
            subsystem="planning",
            operations=[
                SubsystemOperation(name="Create plan", status=FunctionalStatus.FUNCTIONAL),
                SubsystemOperation(
                    name="Approve plan", status=FunctionalStatus.PARTIAL, evidence="Slow but works"
                ),
            ],
        )
    )
    matrix.finalize_all()

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        matrix.save(path)
        restored = AuditMatrix.load(path)
        assert restored.get("planning") is not None
        assert len(restored.get("planning").operations) == 2
    finally:
        os.unlink(path)


def test_broken_subsystems():
    matrix = AuditMatrix()
    matrix.add_subsystem(
        SubsystemAudit(
            subsystem="governance",
            operations=[
                SubsystemOperation(name="Challenge", status=FunctionalStatus.BROKEN),
            ],
        )
    )
    matrix.add_subsystem(
        SubsystemAudit(
            subsystem="planning",
            operations=[
                SubsystemOperation(name="Create", status=FunctionalStatus.FUNCTIONAL),
            ],
        )
    )
    matrix.finalize_all()
    broken = matrix.broken_subsystems()
    assert len(broken) == 1
    assert broken[0].subsystem == "governance"


def test_operation_to_dict():
    op = SubsystemOperation(
        name="View telemetry",
        status=FunctionalStatus.PARTIAL,
        evidence="Shows data but missing timestamps",
        screenshot_path="/tmp/test.png",
    )
    d = op.to_dict()
    assert d["status"] == "partial"
    assert d["evidence"] == "Shows data but missing timestamps"
