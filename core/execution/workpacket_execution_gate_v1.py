"""WorkPacket Execution Gate v1 for the UMH substrate layer.

The final structural gate between approved work and real execution.
No worker/runtime may execute directly from planning or authority.
Only validated WorkPackets that pass all gate checks may cross
into runtime actuation.

Gate validation dimensions:
  - workpacket_allowed flag
  - authority decision present
  - environment exists and is ready
  - runtime exists and is ready
  - adapter maturity sufficient
  - capability authority valid
  - proof requirements declared
  - blocked actions present
  - timeout declared
  - governance trace attached
  - execution lineage attached
  - packet not expired
  - no structural hard blocks

UMH substrate subsystem. Phase 96.8AD.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from core.governance.execution_authority_engine_v1 import (
    AuthorityClass,
    AuthorityDecision,
    CapabilityAuthority,
    EnvironmentAuthority,
    RiskClass,
)
from core.state.transformation_state_ledger import (
    StateArtifactReference,
    StateLedgerRecord,
    TransformationStage,
    TransformationStateLedger,
    compute_hash,
    make_state_id,
    make_trace_id,
)


class GateVerdict(str, Enum):
    PASS = "pass"
    DENY = "deny"


class GateDenialCategory(str, Enum):
    MISSING_AUTHORITY = "missing_authority"
    AUTHORITY_DENIED = "authority_denied"
    MISSING_ENVIRONMENT = "missing_environment"
    MISSING_RUNTIME = "missing_runtime"
    MISSING_GOVERNANCE_TRACE = "missing_governance_trace"
    MISSING_PROOF_REQUIREMENTS = "missing_proof_requirements"
    MISSING_BLOCKED_ACTIONS = "missing_blocked_actions"
    MISSING_TIMEOUT = "missing_timeout"
    MISSING_LINEAGE = "missing_lineage"
    ADAPTER_NOT_READY = "adapter_not_ready"
    PACKET_EXPIRED = "packet_expired"
    STRUCTURAL_BLOCK = "structural_block"
    WORKPACKET_NOT_ALLOWED = "workpacket_not_allowed"


GATE_STRUCTURAL_BLOCKS = frozenset(
    {
        "autonomous_financial_execution",
        "wallet_execution",
        "recursive_runtime_spawning",
        "direct_adapter_execution",
        "canonical_mutation_without_governance",
    }
)


@dataclass
class EnvironmentReadiness:
    """Whether the target environment is ready for execution."""

    environment_type: str
    exists: bool = False
    healthy: bool = False
    authority_granted: bool = False
    risk_within_bounds: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return self.exists and self.healthy and self.authority_granted and self.risk_within_bounds

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment_type": self.environment_type,
            "exists": self.exists,
            "healthy": self.healthy,
            "authority_granted": self.authority_granted,
            "risk_within_bounds": self.risk_within_bounds,
            "ready": self.ready,
            "notes": self.notes,
        }


@dataclass
class RuntimeReadiness:
    """Whether the target runtime/worker is ready for execution."""

    runtime_id: str
    exists: bool = False
    healthy: bool = False
    has_capacity: bool = True
    notes: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return self.exists and self.healthy and self.has_capacity

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "exists": self.exists,
            "healthy": self.healthy,
            "has_capacity": self.has_capacity,
            "ready": self.ready,
            "notes": self.notes,
        }


@dataclass
class AdapterReadiness:
    """Whether the required adapter is mature enough for execution."""

    adapter_id: str
    exists: bool = False
    configured: bool = False
    mature: bool = False
    has_required_capability: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return self.exists and self.configured and self.has_required_capability

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "exists": self.exists,
            "configured": self.configured,
            "mature": self.mature,
            "has_required_capability": self.has_required_capability,
            "ready": self.ready,
            "notes": self.notes,
        }


@dataclass
class ProofReadiness:
    """Whether proof requirements are declared and satisfiable."""

    proof_requirements: list[str] = field(default_factory=list)
    all_declared: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return self.all_declared and len(self.proof_requirements) > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_requirements": self.proof_requirements,
            "all_declared": self.all_declared,
            "ready": self.ready,
            "notes": self.notes,
        }


@dataclass
class ExecutionReadiness:
    """Aggregate readiness across all dimensions."""

    environment: EnvironmentReadiness | None = None
    runtime: RuntimeReadiness | None = None
    adapter: AdapterReadiness | None = None
    proof: ProofReadiness | None = None

    @property
    def all_ready(self) -> bool:
        checks = []
        if self.environment:
            checks.append(self.environment.ready)
        if self.runtime:
            checks.append(self.runtime.ready)
        if self.adapter:
            checks.append(self.adapter.ready)
        return all(checks) if checks else False

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment": self.environment.to_dict() if self.environment else None,
            "runtime": self.runtime.to_dict() if self.runtime else None,
            "adapter": self.adapter.to_dict() if self.adapter else None,
            "proof": self.proof.to_dict() if self.proof else None,
            "all_ready": self.all_ready,
        }


@dataclass
class RuntimeExecutionRequest:
    """A validated request to execute a WorkPacket on a specific runtime."""

    request_id: str
    packet_id: str
    authority_decision_id: str
    authority_class: str
    target_environment: str
    target_runtime: str
    action_type: str
    blocked_actions: list[str] = field(default_factory=list)
    proof_requirements: list[str] = field(default_factory=list)
    timeout_seconds: int = 3600
    governance_trace_id: str = ""
    execution_lineage_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.request_id:
            self.request_id = f"EXEC-REQ-{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "packet_id": self.packet_id,
            "authority_decision_id": self.authority_decision_id,
            "authority_class": self.authority_class,
            "target_environment": self.target_environment,
            "target_runtime": self.target_runtime,
            "action_type": self.action_type,
            "blocked_actions": self.blocked_actions,
            "proof_requirements": self.proof_requirements,
            "timeout_seconds": self.timeout_seconds,
            "governance_trace_id": self.governance_trace_id,
            "execution_lineage_id": self.execution_lineage_id,
            "timestamp": self.timestamp,
        }


@dataclass
class ExecutionGateResult:
    """The gate's verdict on whether a WorkPacket may proceed to execution."""

    result_id: str
    packet_id: str
    verdict: GateVerdict
    denial_reasons: list[str] = field(default_factory=list)
    denial_categories: list[str] = field(default_factory=list)
    readiness: ExecutionReadiness | None = None
    runtime_execution_request: RuntimeExecutionRequest | None = None
    gate_hash: str = ""
    trace_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.result_id:
            self.result_id = f"GATE-{uuid.uuid4().hex[:8]}"

    def compute_gate_hash(self) -> str:
        payload = json.dumps(
            {
                "packet_id": self.packet_id,
                "verdict": self.verdict.value,
                "denial_reasons": sorted(self.denial_reasons),
                "denial_categories": sorted(self.denial_categories),
            },
            sort_keys=True,
        )
        self.gate_hash = hashlib.sha256(payload.encode()).hexdigest()
        return self.gate_hash

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "packet_id": self.packet_id,
            "verdict": self.verdict.value,
            "denial_reasons": self.denial_reasons,
            "denial_categories": self.denial_categories,
            "readiness": self.readiness.to_dict() if self.readiness else None,
            "runtime_execution_request": (
                self.runtime_execution_request.to_dict() if self.runtime_execution_request else None
            ),
            "gate_hash": self.gate_hash,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
        }


class WorkPacketExecutionGate:
    """Validates WorkPackets before they may cross into runtime execution.

    Every dimension must pass. A single failure denies the packet.
    Produces deterministic, hash-verified gate results.
    Persists authority_approved / execution_gate_validated /
    execution_gate_denied / runtime_execution_ready ledger states.
    """

    VERSION = "v1"

    def __init__(
        self,
        environment_authorities: dict[str, EnvironmentAuthority] | None = None,
        capability_authorities: dict[str, CapabilityAuthority] | None = None,
        available_runtimes: dict[str, bool] | None = None,
        ledger: TransformationStateLedger | None = None,
        proof_dir: Path | None = None,
    ) -> None:
        self._env_auths = environment_authorities or {}
        self._cap_auths = capability_authorities or {}
        self._runtimes = available_runtimes or {}
        self._ledger = ledger
        self._proof_dir = proof_dir or Path("data/runtime/workpacket_execution_gate_proofs")
        self._proof_dir.mkdir(parents=True, exist_ok=True)

    def validate(
        self,
        packet_id: str,
        action_type: str,
        authority_decision: AuthorityDecision,
        target_environment: str = "",
        target_runtime: str = "",
        required_adapter_id: str = "",
        required_capability: str = "",
        blocked_actions: list[str] | None = None,
        proof_requirements: list[str] | None = None,
        timeout_seconds: int = 0,
        governance_trace_id: str = "",
        execution_lineage_id: str = "",
        expires_at: str = "",
        trace_id: str = "",
    ) -> ExecutionGateResult:
        denial_reasons: list[str] = []
        denial_categories: list[str] = []
        _blocked = blocked_actions or []
        _proofs = proof_requirements or []

        # 1. WorkPacket allowed
        if not authority_decision.workpacket_allowed:
            denial_reasons.append("authority_decision_denies_workpacket")
            denial_categories.append(GateDenialCategory.WORKPACKET_NOT_ALLOWED.value)

        # 2. Authority decision present and valid
        if authority_decision.authority_class == AuthorityClass.DENY:
            denial_reasons.append(f"authority_class_is_deny: {authority_decision.denial_reasons}")
            denial_categories.append(GateDenialCategory.AUTHORITY_DENIED.value)

        # 3. Structural hard blocks
        for block in GATE_STRUCTURAL_BLOCKS:
            if action_type == block:
                denial_reasons.append(f"structural_block: {block}")
                denial_categories.append(GateDenialCategory.STRUCTURAL_BLOCK.value)

        if action_type == "direct_adapter_execution":
            denial_reasons.append("adapters_never_execute_directly")
            denial_categories.append(GateDenialCategory.STRUCTURAL_BLOCK.value)

        # 4. Environment readiness
        env_readiness = self._check_environment(target_environment, authority_decision)
        if not target_environment:
            denial_reasons.append("missing_target_environment")
            denial_categories.append(GateDenialCategory.MISSING_ENVIRONMENT.value)
        elif not env_readiness.ready:
            denial_reasons.append(f"environment_not_ready: {env_readiness.notes}")
            denial_categories.append(GateDenialCategory.MISSING_ENVIRONMENT.value)

        # 5. Runtime readiness
        runtime_readiness = self._check_runtime(target_runtime)
        if not target_runtime:
            denial_reasons.append("missing_target_runtime")
            denial_categories.append(GateDenialCategory.MISSING_RUNTIME.value)
        elif not runtime_readiness.ready:
            denial_reasons.append(f"runtime_not_ready: {runtime_readiness.notes}")
            denial_categories.append(GateDenialCategory.MISSING_RUNTIME.value)

        # 6. Adapter readiness
        adapter_readiness = self._check_adapter(required_adapter_id, required_capability)
        if required_adapter_id and not adapter_readiness.ready:
            denial_reasons.append(f"adapter_not_ready: {adapter_readiness.notes}")
            denial_categories.append(GateDenialCategory.ADAPTER_NOT_READY.value)

        # 7. Proof requirements
        proof_readiness = ProofReadiness(
            proof_requirements=_proofs,
            all_declared=len(_proofs) > 0,
        )
        if not _proofs:
            denial_reasons.append("no_proof_requirements_declared")
            denial_categories.append(GateDenialCategory.MISSING_PROOF_REQUIREMENTS.value)

        # 8. Blocked actions
        if not _blocked:
            denial_reasons.append("no_blocked_actions_declared")
            denial_categories.append(GateDenialCategory.MISSING_BLOCKED_ACTIONS.value)

        # 9. Timeout
        if timeout_seconds <= 0:
            denial_reasons.append("no_timeout_declared")
            denial_categories.append(GateDenialCategory.MISSING_TIMEOUT.value)

        # 10. Governance trace
        if not governance_trace_id:
            denial_reasons.append("no_governance_trace_attached")
            denial_categories.append(GateDenialCategory.MISSING_GOVERNANCE_TRACE.value)

        # 11. Execution lineage
        if not execution_lineage_id:
            denial_reasons.append("no_execution_lineage_attached")
            denial_categories.append(GateDenialCategory.MISSING_LINEAGE.value)

        # 12. Expiration
        if expires_at:
            try:
                exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if exp <= datetime.now(timezone.utc):
                    denial_reasons.append("workpacket_expired")
                    denial_categories.append(GateDenialCategory.PACKET_EXPIRED.value)
            except ValueError:
                denial_reasons.append("invalid_expires_at_format")
                denial_categories.append(GateDenialCategory.PACKET_EXPIRED.value)

        # Build readiness
        readiness = ExecutionReadiness(
            environment=env_readiness,
            runtime=runtime_readiness,
            adapter=adapter_readiness if required_adapter_id else None,
            proof=proof_readiness,
        )

        # Verdict
        if denial_reasons:
            verdict = GateVerdict.DENY
            exec_request = None
        else:
            verdict = GateVerdict.PASS
            exec_request = RuntimeExecutionRequest(
                request_id="",
                packet_id=packet_id,
                authority_decision_id=authority_decision.decision_id,
                authority_class=authority_decision.authority_class.value,
                target_environment=target_environment,
                target_runtime=target_runtime,
                action_type=action_type,
                blocked_actions=_blocked,
                proof_requirements=_proofs,
                timeout_seconds=timeout_seconds,
                governance_trace_id=governance_trace_id,
                execution_lineage_id=execution_lineage_id,
            )

        result = ExecutionGateResult(
            result_id="",
            packet_id=packet_id,
            verdict=verdict,
            denial_reasons=denial_reasons,
            denial_categories=list(set(denial_categories)),
            readiness=readiness,
            runtime_execution_request=exec_request,
            trace_id=trace_id,
        )
        result.compute_gate_hash()

        # Persist ledger states
        if self._ledger:
            self._record_ledger(result, authority_decision, trace_id)

        # Persist proof
        self._persist_proof(result)

        return result

    def _check_environment(
        self,
        env_type: str,
        authority: AuthorityDecision,
    ) -> EnvironmentReadiness:
        if not env_type:
            return EnvironmentReadiness(environment_type="", exists=False)

        env_auth = self._env_auths.get(env_type)
        if not env_auth:
            return EnvironmentReadiness(
                environment_type=env_type,
                exists=False,
                notes=[f"environment_not_registered: {env_type}"],
            )

        return EnvironmentReadiness(
            environment_type=env_type,
            exists=True,
            healthy=True,
            authority_granted=authority.environment_authority_met,
            risk_within_bounds=True,
        )

    def _check_runtime(self, runtime_id: str) -> RuntimeReadiness:
        if not runtime_id:
            return RuntimeReadiness(runtime_id="", exists=False)

        is_available = self._runtimes.get(runtime_id, False)
        return RuntimeReadiness(
            runtime_id=runtime_id,
            exists=is_available,
            healthy=is_available,
            has_capacity=is_available,
            notes=[] if is_available else [f"runtime_not_available: {runtime_id}"],
        )

    def _check_adapter(self, adapter_id: str, required_capability: str) -> AdapterReadiness:
        if not adapter_id:
            return AdapterReadiness(adapter_id="", exists=False)

        cap_auth = self._cap_auths.get(adapter_id)
        if not cap_auth:
            return AdapterReadiness(
                adapter_id=adapter_id,
                exists=False,
                notes=[f"adapter_not_registered: {adapter_id}"],
            )

        has_cap = cap_auth.has_capability(required_capability) if required_capability else True

        return AdapterReadiness(
            adapter_id=adapter_id,
            exists=True,
            configured=cap_auth.is_configured,
            mature=cap_auth.is_mature,
            has_required_capability=has_cap,
            notes=([] if has_cap else [f"missing_capability: {required_capability}"]),
        )

    def _record_ledger(
        self,
        result: ExecutionGateResult,
        authority: AuthorityDecision,
        trace_id: str,
    ) -> None:
        if not self._ledger:
            return

        auth_hash = compute_hash(json.dumps(authority.to_dict(), sort_keys=True))
        gate_hash = result.gate_hash

        auth_record = StateLedgerRecord(
            state_id=make_state_id(),
            trace_id=trace_id or make_trace_id("GATE"),
            parent_state_id="",
            stage=TransformationStage.AUTHORITY_APPROVED,
            input_artifact_ref=StateArtifactReference(
                artifact_id=f"auth-{authority.decision_id}",
                artifact_type="authority_decision",
                content_hash=auth_hash,
            ),
            output_artifact_ref=StateArtifactReference(
                artifact_id=f"auth-out-{authority.decision_id}",
                artifact_type="authority_decision",
                content_hash=auth_hash,
            ),
            transformer_name="workpacket_execution_gate_v1",
            transformer_version="v1",
            runtime_id="gate",
            adapter_id="",
            policy_envelope={"phase": "96.8AD"},
            confidence="high",
            input_hash=auth_hash,
            output_hash=auth_hash,
            allowed_next_actions=["execution_gate_validation"],
            blocked_next_actions=list(GATE_STRUCTURAL_BLOCKS),
        )
        self._ledger.append(auth_record)

        if result.verdict == GateVerdict.PASS:
            gate_stage = TransformationStage.EXECUTION_GATE_VALIDATED
        else:
            gate_stage = TransformationStage.EXECUTION_GATE_DENIED

        gate_record = StateLedgerRecord(
            state_id=make_state_id(),
            trace_id=trace_id or make_trace_id("GATE"),
            parent_state_id=auth_record.state_id,
            stage=gate_stage,
            input_artifact_ref=StateArtifactReference(
                artifact_id=f"gate-in-{result.result_id}",
                artifact_type="gate_input",
                content_hash=auth_hash,
            ),
            output_artifact_ref=StateArtifactReference(
                artifact_id=f"gate-out-{result.result_id}",
                artifact_type="gate_result",
                content_hash=gate_hash,
            ),
            transformer_name="workpacket_execution_gate_v1",
            transformer_version="v1",
            runtime_id="gate",
            adapter_id="",
            policy_envelope={"phase": "96.8AD", "verdict": result.verdict.value},
            confidence="high",
            input_hash=auth_hash,
            output_hash=gate_hash,
            allowed_next_actions=(
                ["runtime_execution"] if result.verdict == GateVerdict.PASS else []
            ),
            blocked_next_actions=list(GATE_STRUCTURAL_BLOCKS),
        )
        self._ledger.append(gate_record)

        if result.verdict == GateVerdict.PASS:
            ready_record = StateLedgerRecord(
                state_id=make_state_id(),
                trace_id=trace_id or make_trace_id("GATE"),
                parent_state_id=gate_record.state_id,
                stage=TransformationStage.RUNTIME_EXECUTION_READY,
                input_artifact_ref=StateArtifactReference(
                    artifact_id=f"ready-in-{result.result_id}",
                    artifact_type="gate_validated",
                    content_hash=gate_hash,
                ),
                output_artifact_ref=StateArtifactReference(
                    artifact_id=f"ready-out-{result.result_id}",
                    artifact_type="runtime_ready",
                    content_hash=gate_hash,
                ),
                transformer_name="workpacket_execution_gate_v1",
                transformer_version="v1",
                runtime_id="gate",
                adapter_id="",
                policy_envelope={"phase": "96.8AD", "status": "runtime_ready"},
                confidence="high",
                input_hash=gate_hash,
                output_hash=gate_hash,
                allowed_next_actions=["execute"],
                blocked_next_actions=list(GATE_STRUCTURAL_BLOCKS),
            )
            self._ledger.append(ready_record)

    def _persist_proof(self, result: ExecutionGateResult) -> None:
        path = self._proof_dir / f"{result.result_id}.json"
        with open(path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
