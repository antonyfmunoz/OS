"""Canonical Spine Coherence Validator.

Validates that a CoherenceEnvelope represents valid, complete
lineage through the 15-stage UMH canonical spine.

Fail-closed: if validation cannot confirm coherence, execution
is blocked.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from .spine_lineage_contracts import (
    CANONICAL_STAGE_ORDER,
    REQUIRED_STAGE_NAMES,
    CoherenceEnvelope,
    CoherenceFailureReason,
    CoherenceStatus,
    CoherenceValidationResult,
    SpineLineage,
    SpineStage,
    SpineStageArtifact,
    SpineStageStatus,
)


def validate_coherence_envelope(envelope: CoherenceEnvelope) -> CoherenceValidationResult:
    """Validate a CoherenceEnvelope for spine coherence."""
    result = CoherenceValidationResult()
    lineage = envelope.lineage

    _check_required_stages(lineage, result)
    if result.errors:
        return result

    _check_no_duplicates(lineage, result)
    if result.errors:
        return result

    _check_stage_order(lineage, result)
    if result.errors:
        result.status = CoherenceStatus.INVALID_STAGE_ORDER.value
        return result

    _check_stage_artifacts(lineage, result)
    if result.errors:
        result.status = CoherenceStatus.INVALID_STAGE_ARTIFACT.value
        return result

    _check_mvp_stubs(lineage, result)
    if result.errors:
        return result

    _check_ordering_constraints(lineage, result)
    if result.errors:
        return result

    if result.has_mvp_stubs:
        result.status = CoherenceStatus.COHERENT_WITH_MVP_STUBS.value
        result.coherent = True
    else:
        result.status = CoherenceStatus.COHERENT.value
        result.coherent = True

    return result


def validate_coherence_envelope_dict(
    envelope_dict: dict,
) -> CoherenceValidationResult:
    """Validate a coherence envelope from its dict representation."""
    result = CoherenceValidationResult()

    if not envelope_dict:
        result.errors.append("MISSING_COHERENCE_ENVELOPE: envelope is empty or None")
        result.status = CoherenceStatus.INCOMPLETE_CANONICAL_SPINE.value
        return result

    lineage_dict = envelope_dict.get("lineage")
    if not lineage_dict:
        result.errors.append("MISSING_LINEAGE: lineage required in envelope")
        result.status = CoherenceStatus.INCOMPLETE_CANONICAL_SPINE.value
        return result

    stages_list = lineage_dict.get("stages", [])
    mvp_stub_allowed = lineage_dict.get("mvp_stub_allowed", False)

    stages = []
    for s in stages_list:
        stages.append(
            SpineStageArtifact(
                stage_name=s.get("stage_name", ""),
                artifact_id=s.get("artifact_id", ""),
                artifact_type=s.get("artifact_type", ""),
                source=s.get("source", ""),
                timestamp=s.get("timestamp", ""),
                status=s.get("status", ""),
                confidence=s.get("confidence", 0.0),
                validation_status=s.get("validation_status", ""),
                trace_id=s.get("trace_id", ""),
                schema_version=s.get("schema_version", ""),
                reason=s.get("reason", ""),
                allowed_for=s.get("allowed_for", ""),
            )
        )

    lineage = SpineLineage(stages=stages, mvp_stub_allowed=mvp_stub_allowed)
    envelope = CoherenceEnvelope(
        lineage=lineage,
        coherence_status=envelope_dict.get("coherence_status", ""),
        trace_id=envelope_dict.get("trace_id", ""),
        schema_version=envelope_dict.get("schema_version", "1.0"),
    )

    return validate_coherence_envelope(envelope)


def _check_required_stages(lineage: SpineLineage, result: CoherenceValidationResult) -> None:
    present = set(lineage.stage_names())
    missing = REQUIRED_STAGE_NAMES - present
    if missing:
        result.missing_stages = sorted(missing)
        for m in sorted(missing):
            result.errors.append(f"MISSING_STAGE: {m}")
            result.failure_reasons.append(CoherenceFailureReason.MISSING_STAGE.value)

        if SpineStage.GOVERNANCE_DECISION.value in missing:
            result.status = CoherenceStatus.GOVERNANCE_LINEAGE_MISSING.value
        elif SpineStage.MASTERY_CHECK.value in missing:
            result.status = CoherenceStatus.MASTERY_LINEAGE_MISSING.value
        elif SpineStage.EXECUTION_BINDING.value in missing:
            result.status = CoherenceStatus.EXECUTION_BINDING_LINEAGE_MISSING.value
        elif SpineStage.PROOF_CONTRACT.value in missing:
            result.status = CoherenceStatus.PROOF_CONTRACT_LINEAGE_MISSING.value
        elif SpineStage.TRACE_PATH.value in missing:
            result.status = CoherenceStatus.TRACE_PATH_LINEAGE_MISSING.value


def _check_no_duplicates(lineage: SpineLineage, result: CoherenceValidationResult) -> None:
    seen: set[str] = set()
    for s in lineage.stages:
        if s.stage_name in seen:
            result.errors.append(f"DUPLICATE_STAGE: {s.stage_name}")
            result.failure_reasons.append(CoherenceFailureReason.DUPLICATE_STAGE.value)
            result.status = CoherenceStatus.INVALID_STAGE_ARTIFACT.value
        seen.add(s.stage_name)


def _check_stage_order(lineage: SpineLineage, result: CoherenceValidationResult) -> None:
    last_order = -1
    for s in lineage.stages:
        try:
            stage_enum = SpineStage(s.stage_name)
        except ValueError:
            continue
        order = CANONICAL_STAGE_ORDER.get(stage_enum, -1)
        if order < last_order:
            result.errors.append(f"INVALID_STAGE_ORDER: {s.stage_name} appears after a later stage")
            result.failure_reasons.append(CoherenceFailureReason.INVALID_ORDER.value)
        last_order = order


def _check_stage_artifacts(lineage: SpineLineage, result: CoherenceValidationResult) -> None:
    for s in lineage.stages:
        if not s.artifact_id:
            result.errors.append(f"MISSING_ARTIFACT_ID: stage {s.stage_name}")
            result.failure_reasons.append(CoherenceFailureReason.MISSING_ARTIFACT_ID.value)
        if not s.trace_id:
            result.errors.append(f"MISSING_TRACE_ID: stage {s.stage_name}")
            result.failure_reasons.append(CoherenceFailureReason.MISSING_TRACE_ID.value)
        if not s.schema_version:
            result.errors.append(f"MISSING_SCHEMA_VERSION: stage {s.stage_name}")
            result.failure_reasons.append(CoherenceFailureReason.MISSING_SCHEMA_VERSION.value)
        if not s.status:
            result.errors.append(f"MISSING_STATUS: stage {s.stage_name}")
            result.failure_reasons.append(CoherenceFailureReason.MISSING_STATUS.value)


def _check_mvp_stubs(lineage: SpineLineage, result: CoherenceValidationResult) -> None:
    for s in lineage.stages:
        if s.status == SpineStageStatus.MVP_STUB.value:
            result.has_mvp_stubs = True
            if not lineage.mvp_stub_allowed:
                result.errors.append(
                    f"MVP_STUB_NOT_ALLOWED: stage {s.stage_name} is mvp_stub "
                    f"but mvp_stub_allowed is False"
                )
                result.failure_reasons.append(CoherenceFailureReason.MVP_STUB_NOT_ALLOWED.value)
                result.status = CoherenceStatus.INCOMPLETE_CANONICAL_SPINE.value
            if not s.reason:
                result.errors.append(
                    f"MVP_STUB_MISSING_REASON: stage {s.stage_name} is mvp_stub but has no reason"
                )
                result.failure_reasons.append(CoherenceFailureReason.MVP_STUB_MISSING_REASON.value)
                result.status = CoherenceStatus.INVALID_STAGE_ARTIFACT.value

    result.mvp_stub_allowed = lineage.mvp_stub_allowed


def _check_ordering_constraints(lineage: SpineLineage, result: CoherenceValidationResult) -> None:
    """Check semantic ordering constraints beyond positional order."""
    stage_positions: dict[str, int] = {}
    for i, s in enumerate(lineage.stages):
        stage_positions[s.stage_name] = i

    gov_pos = stage_positions.get(SpineStage.GOVERNANCE_DECISION.value)
    wp_pos = stage_positions.get(SpineStage.WORK_PACKET.value)
    if gov_pos is not None and wp_pos is not None and gov_pos > wp_pos:
        result.errors.append(
            "GOVERNANCE_BEFORE_WORK_PACKET: governance_decision must precede work_packet"
        )
        result.failure_reasons.append(CoherenceFailureReason.GOVERNANCE_BEFORE_WORK_PACKET.value)
        result.status = CoherenceStatus.GOVERNANCE_LINEAGE_MISSING.value

    mastery_pos = stage_positions.get(SpineStage.MASTERY_CHECK.value)
    if mastery_pos is not None and gov_pos is not None and mastery_pos > gov_pos:
        result.errors.append(
            "MASTERY_BEFORE_GOVERNANCE: mastery_check must precede governance_decision"
        )
        result.failure_reasons.append(CoherenceFailureReason.MASTERY_BEFORE_GOVERNANCE.value)
        result.status = CoherenceStatus.MASTERY_LINEAGE_MISSING.value

    proof_pos = stage_positions.get(SpineStage.PROOF_CONTRACT.value)
    if proof_pos is not None and wp_pos is not None and proof_pos < wp_pos:
        pass
    elif proof_pos is not None and wp_pos is not None and proof_pos < wp_pos:
        result.errors.append(
            "PROOF_CONTRACT_BEFORE_EXECUTION: proof_contract must exist "
            "before execution can proceed"
        )
        result.failure_reasons.append(CoherenceFailureReason.PROOF_CONTRACT_BEFORE_EXECUTION.value)
        result.status = CoherenceStatus.PROOF_CONTRACT_LINEAGE_MISSING.value
