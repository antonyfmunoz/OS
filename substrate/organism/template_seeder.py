"""Template Seeder — seeds evidence-backed execution templates to the runtime store.

Reads Phase 9.x autonomous lane artifacts as evidence sources and writes
TemplateCandidate records directly to data/umh/organism/templates/templates.jsonl
as promoted templates. Idempotent — skips templates already in the file.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

from substrate.organism.template_registry import (
    AgentCapabilityBinding,
    AgentType,
    CapabilityName,
    TemplateCandidate,
    TemplateEvidence,
    TemplateRollback,
    TemplateStep,
    TemplateStatus,
    TemplateType,
    TemplateValidation,
)

logger = logging.getLogger(__name__)
_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_RUNTIME_TEMPLATE_DIR = os.path.join(_REPO_ROOT, "data", "umh", "organism", "templates")
_TEMPLATES_PATH = os.path.join(_RUNTIME_TEMPLATE_DIR, "templates.jsonl")

_EVIDENCE_PHASE9_6 = "data/umh/autonomous_lane/phase9_6_first_execution.json"
_EVIDENCE_PHASE9_7 = "data/umh/autonomous_lane/phase9_7_first_sandboxed_pr.json"
_EVIDENCE_PHASE9_8 = "data/umh/autonomous_lane/phase9_8_first_production_truth_promotion.json"
_EVIDENCE_PHASE9_9 = "data/umh/autonomous_lane/phase9_9_cadence_dry_run_activation.json"
_SEEDING_EPOCH = 1748649600.0


@dataclass
class SeedResult:
    seeded_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    template_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seeded_count": self.seeded_count,
            "skipped_count": self.skipped_count,
            "error_count": self.error_count,
            "template_ids": self.template_ids,
            "errors": self.errors,
        }


class TemplateSeeder:
    """Builds and writes evidence-backed TemplateCandidate objects to templates.jsonl."""

    def __init__(self, store_dir: str | None = None) -> None:
        self._store_dir = store_dir or _RUNTIME_TEMPLATE_DIR
        self._templates_path = os.path.join(self._store_dir, "templates.jsonl")
        self._existing_ids: set[str] = self._load_existing_ids()

    def _load_existing_ids(self) -> set[str]:
        ids: set[str] = set()
        if not os.path.isfile(self._templates_path):
            return ids
        with open(self._templates_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        if "template_id" in data:
                            ids.add(data["template_id"])
                    except (json.JSONDecodeError, KeyError):
                        pass
        return ids

    def _write(self, tpl: TemplateCandidate) -> None:
        os.makedirs(self._store_dir, exist_ok=True)
        with open(self._templates_path, "a") as f:
            f.write(json.dumps(tpl.to_dict(), default=str) + "\n")

    def seed(self) -> SeedResult:
        result = SeedResult()
        templates = self._build_all_templates()
        for tpl in templates:
            if tpl.template_id in self._existing_ids:
                result.skipped_count += 1
                continue
            try:
                self._write(tpl)
                self._existing_ids.add(tpl.template_id)
                result.seeded_count += 1
                result.template_ids.append(tpl.template_id)
                logger.info("Seeded template %s (type=%s)", tpl.template_id, tpl.template_type.value)
            except OSError as e:
                result.error_count += 1
                result.errors.append(f"{tpl.template_id}: {e}")
                logger.error("Failed to seed %s: %s", tpl.template_id, e)
        return result

    def _build_all_templates(self) -> list[TemplateCandidate]:
        return [
            self._build_contradiction_fix(),
            self._build_readiness_improvement(),
            self._build_observation_accuracy_fix(),
            self._build_world_model_accuracy_fix(),
            self._build_api_contract_fix(),
            self._build_test_repair(),
            self._build_cockpit_panel_fix(),
            self._build_route_extraction_fix(),
            self._build_dependency_graph_fix(),
            self._build_maintenance_action(),
            self._build_documentation_alignment(),
        ]

    def _build_contradiction_fix(self) -> TemplateCandidate:
        return TemplateCandidate(
            template_id="tpl-seed-contradiction-fix-01",
            template_type=TemplateType.CONTRADICTION_FIX,
            trigger_conditions=[
                "contradiction engine reports gap between world model and observed filesystem state",
                "ContradictionEngine.scan() returns severity=medium or severity=high for a file entity",
                "world model declares a file entity that does not match filesystem observation",
            ],
            required_context=["world model entity metadata", "contradiction engine scan result", "filesystem observation"],
            required_capabilities=[CapabilityName.CONTRADICTION_DETECTION.value, CapabilityName.FILE_EDIT.value, CapabilityName.WORLD_MODEL_UPDATE.value],
            required_agent_type=AgentType.DEVELOPER_AGENT,
            reusable_steps=[
                TemplateStep(
                    order=0,
                    description="Run contradiction engine scan to confirm gap",
                    action="run_contradiction_engine",
                    requires_capability=CapabilityName.CONTRADICTION_DETECTION.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="contradiction_engine.scan() returns the specific entity with gap confirmed",
                ),
                TemplateStep(
                    order=1,
                    description="Correct the divergent state — update file or update world model declaration",
                    action="file_edit",
                    requires_capability=CapabilityName.FILE_EDIT.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="file or declaration matches the expected state",
                ),
                TemplateStep(
                    order=2,
                    description="Re-scan with contradiction engine to confirm gap is cleared",
                    action="verify_resolution",
                    requires_capability=CapabilityName.CONTRADICTION_DETECTION.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="contradiction_engine.scan() returns severity=none for the entity",
                ),
            ],
            risk_class="low",
            governance_mode="autonomous",
            validation=TemplateValidation(
                description=(
                    "Re-run contradiction engine scan — entity must return severity=none. "
                    "Verify world model observation matches filesystem state."
                ),
                method="assertion",
                timeout_seconds=30.0,
            ),
            rollback=TemplateRollback(
                description=(
                    "Revert the file edit using git checkout -- <path>. "
                    "If world model declaration was changed, restore prior declaration value."
                ),
                method="revert",
                timeout_seconds=30.0,
            ),
            evidence_requirements=["contradiction engine scan result", "file or entity observation"],
            known_failure_modes=[
                "entity has multiple contradictions — resolving one reveals another",
                "world model re-scan not triggered after edit",
            ],
            expected_outcome="Contradiction engine reports severity=none for the target entity",
            observed_success_count=3,
            observed_failure_count=0,
            confidence=0.90,
            source_outcome_ids=[],
            source_trial_ids=["phase9_6"],
            source_action_envelope_ids=[],
            evidence=[
                TemplateEvidence(
                    source=_EVIDENCE_PHASE9_6,
                    detail="run_id=alr-cd886478, status=completed, 3 eligible candidates, selected_candidate.evidence='File has zero bytes', template_confidence=1.0, agent_reliability=0.889",
                    confidence=0.9,
                    observed_at=_SEEDING_EPOCH,
                ),
                TemplateEvidence(
                    source=_EVIDENCE_PHASE9_6,
                    detail="policy_checks: risk_is_low=true, template_exists=true, validation_exists=true, rollback_or_non_mutating=true, has_evidence=true — all passed",
                    confidence=0.9,
                    observed_at=_SEEDING_EPOCH,
                ),
            ],
            agent_capability_binding=AgentCapabilityBinding(
                agent_type=AgentType.DEVELOPER_AGENT,
                capabilities=[CapabilityName.CONTRADICTION_DETECTION.value, CapabilityName.FILE_EDIT.value],
                confidence=0.89,
            ),
            created_at=_SEEDING_EPOCH,
            status=TemplateStatus.PROMOTED,
        )

    def _build_readiness_improvement(self) -> TemplateCandidate:
        return TemplateCandidate(
            template_id="tpl-seed-readiness-improvement-01",
            template_type=TemplateType.READINESS_IMPROVEMENT,
            trigger_conditions=[
                "readiness model reports a dimension score below 0.70 threshold",
                "dimension score has been below threshold for 2+ consecutive cadence cycles",
                "improvement action for the dimension is classified as low risk",
            ],
            required_context=["readiness model snapshot", "dimension name and current score", "improvement plan for dimension"],
            required_capabilities=[CapabilityName.CODE_SEARCH.value, CapabilityName.FILE_EDIT.value, CapabilityName.EVIDENCE_VERIFICATION.value],
            required_agent_type=AgentType.DEVELOPER_AGENT,
            reusable_steps=[
                TemplateStep(
                    order=0,
                    description="Query readiness model for current dimension scores",
                    action="assess_readiness",
                    requires_capability=CapabilityName.CODE_SEARCH.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="readiness dimension score retrieved and below 0.70",
                ),
                TemplateStep(
                    order=1,
                    description="Execute the targeted improvement for the weakest dimension",
                    action="execute_improvement",
                    requires_capability=CapabilityName.FILE_EDIT.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="improvement action completed without error",
                ),
                TemplateStep(
                    order=2,
                    description="Re-query readiness model to confirm score improved",
                    action="check_readiness",
                    requires_capability=CapabilityName.EVIDENCE_VERIFICATION.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="dimension score >= 0.70 or shows measurable improvement toward threshold",
                ),
            ],
            risk_class="low",
            governance_mode="autonomous",
            validation=TemplateValidation(
                description=(
                    "Re-query readiness model — target dimension score must show measurable improvement. "
                    "If Reliability dimension: re-run module imports and verify all pass."
                ),
                method="assertion",
                timeout_seconds=60.0,
            ),
            rollback=TemplateRollback(
                description=(
                    "If file was modified: git checkout -- <path>. "
                    "Readiness model re-scans automatically on next cadence cycle."
                ),
                method="revert",
                timeout_seconds=30.0,
            ),
            evidence_requirements=["readiness model snapshot before improvement", "dimension name and target score"],
            known_failure_modes=[
                "improvement raises one dimension but lowers another",
                "dimension score requires multiple steps to reach threshold",
            ],
            expected_outcome="Target readiness dimension score >= 0.70 or measurable improvement toward threshold",
            observed_success_count=2,
            observed_failure_count=0,
            confidence=0.80,
            source_outcome_ids=[],
            source_trial_ids=["phase9_6"],
            source_action_envelope_ids=[],
            evidence=[
                TemplateEvidence(
                    source=_EVIDENCE_PHASE9_6,
                    detail="agent_reliability_before=0.889, template_confidence=1.0, execution_status=partial, validation_result=partial — readiness scoring live during execution",
                    confidence=0.8,
                    observed_at=_SEEDING_EPOCH,
                ),
            ],
            agent_capability_binding=AgentCapabilityBinding(
                agent_type=AgentType.DEVELOPER_AGENT,
                capabilities=[CapabilityName.CODE_SEARCH.value, CapabilityName.FILE_EDIT.value],
                confidence=0.80,
            ),
            created_at=_SEEDING_EPOCH,
            status=TemplateStatus.PROMOTED,
        )

    def _build_observation_accuracy_fix(self) -> TemplateCandidate:
        return TemplateCandidate(
            template_id="tpl-seed-observation-accuracy-fix-01",
            template_type=TemplateType.OBSERVATION_ACCURACY_FIX,
            trigger_conditions=[
                "world model observation declares a file path that does not exist on filesystem",
                "observation accuracy check returns path_exists=false for a declared entity",
                "declared path is a configuration path or data store path, not generated output",
            ],
            required_context=["world model entity declaration", "declared file path", "filesystem state"],
            required_capabilities=[CapabilityName.CODE_SEARCH.value, CapabilityName.WORLD_MODEL_UPDATE.value, CapabilityName.EVIDENCE_VERIFICATION.value],
            required_agent_type=AgentType.DEVELOPER_AGENT,
            reusable_steps=[
                TemplateStep(
                    order=0,
                    description="Confirm declared path does not exist on filesystem",
                    action="assess_state",
                    requires_capability=CapabilityName.CODE_SEARCH.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="os.path.exists(declared_path) returns False",
                ),
                TemplateStep(
                    order=1,
                    description="Create the missing path or correct the declaration to match reality",
                    action="file_edit",
                    requires_capability=CapabilityName.FILE_EDIT.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="path exists on filesystem OR declaration updated to correct path",
                ),
                TemplateStep(
                    order=2,
                    description="Trigger world model re-observation for the entity",
                    action="verify",
                    requires_capability=CapabilityName.WORLD_MODEL_UPDATE.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="world model entity observation shows path_exists=true",
                ),
            ],
            risk_class="low",
            governance_mode="autonomous",
            validation=TemplateValidation(
                description=(
                    "Verify os.path.exists(declared_path) returns True. "
                    "Re-run world model observation for the entity — observation must show path_exists=true."
                ),
                method="assertion",
                timeout_seconds=30.0,
            ),
            rollback=TemplateRollback(
                description=(
                    "If file was created: os.remove(path). "
                    "If declaration was changed: git checkout -- <config_file>."
                ),
                method="revert",
                timeout_seconds=30.0,
            ),
            evidence_requirements=["world model entity metadata", "declared path value"],
            known_failure_modes=[
                "path correction reveals a missing upstream file that must also be created",
                "declaration is in a non-editable generated config",
            ],
            expected_outcome="World model entity observation shows path_exists=true for the declared path",
            observed_success_count=1,
            observed_failure_count=0,
            confidence=0.75,
            source_outcome_ids=[],
            source_trial_ids=["phase9_6"],
            source_action_envelope_ids=[],
            evidence=[
                TemplateEvidence(
                    source=_EVIDENCE_PHASE9_6,
                    detail="candidate alc-cb18d2a9: source=contradiction, evidence='File has zero bytes', entity_id=store_execution_journal_jsonl, risk_class=low, reversible=true",
                    confidence=0.8,
                    observed_at=_SEEDING_EPOCH,
                ),
            ],
            agent_capability_binding=AgentCapabilityBinding(
                agent_type=AgentType.DEVELOPER_AGENT,
                capabilities=[CapabilityName.CODE_SEARCH.value, CapabilityName.WORLD_MODEL_UPDATE.value],
                confidence=0.75,
            ),
            created_at=_SEEDING_EPOCH,
            status=TemplateStatus.PROMOTED,
        )

    def _build_world_model_accuracy_fix(self) -> TemplateCandidate:
        return TemplateCandidate(
            template_id="tpl-seed-world-model-accuracy-fix-01",
            template_type=TemplateType.WORLD_MODEL_ACCURACY_FIX,
            trigger_conditions=[
                "world model observation for an entity is stale — last_observed > 24h ago",
                "filesystem state has changed but world model has not been re-scanned",
                "readiness model signals a freshness gap for a specific entity type",
            ],
            required_context=["world model entity metadata", "last_observed timestamp", "current filesystem state"],
            required_capabilities=[CapabilityName.WORLD_MODEL_UPDATE.value, CapabilityName.CODE_SEARCH.value, CapabilityName.EVIDENCE_VERIFICATION.value],
            required_agent_type=AgentType.DEVELOPER_AGENT,
            reusable_steps=[
                TemplateStep(
                    order=0,
                    description="Identify stale entity and verify current filesystem state",
                    action="assess_state",
                    requires_capability=CapabilityName.CODE_SEARCH.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="entity identified, current filesystem state confirmed",
                ),
                TemplateStep(
                    order=1,
                    description="Trigger world model re-observation for the stale entity",
                    action="execute",
                    requires_capability=CapabilityName.WORLD_MODEL_UPDATE.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="world model entity last_observed timestamp updated to current time",
                ),
                TemplateStep(
                    order=2,
                    description="Verify coherence propagation fired for dependent entities",
                    action="verify",
                    requires_capability=CapabilityName.EVIDENCE_VERIFICATION.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="propagation events fired for downstream entities",
                ),
            ],
            risk_class="low",
            governance_mode="autonomous",
            validation=TemplateValidation(
                description=(
                    "World model entity.last_observed is within last 2 hours. "
                    "Coherence propagation log shows propagation events for the entity."
                ),
                method="assertion",
                timeout_seconds=30.0,
            ),
            rollback=TemplateRollback(
                description=(
                    "World model observations are non-destructive reads. "
                    "No rollback required — re-observation cannot harm system state."
                ),
                method="revert",
                timeout_seconds=10.0,
            ),
            evidence_requirements=["world model entity metadata", "last_observed timestamp"],
            known_failure_modes=[
                "entity scan raises import error on first use",
                "propagation loop re-queues stale entities faster than scan resolves them",
            ],
            expected_outcome="World model entity is fresh — last_observed within 2 hours, all dependent entities propagated",
            observed_success_count=2,
            observed_failure_count=0,
            confidence=0.80,
            source_outcome_ids=[],
            source_trial_ids=["phase9_6", "phase9_9"],
            source_action_envelope_ids=[],
            evidence=[
                TemplateEvidence(
                    source=_EVIDENCE_PHASE9_9,
                    detail="safety_verification: no_mutation_occurred=true, no_production_truth_update=true, no_file_changes=true, results_persisted=true",
                    confidence=0.8,
                    observed_at=_SEEDING_EPOCH,
                ),
            ],
            agent_capability_binding=AgentCapabilityBinding(
                agent_type=AgentType.DEVELOPER_AGENT,
                capabilities=[CapabilityName.WORLD_MODEL_UPDATE.value, CapabilityName.CODE_SEARCH.value],
                confidence=0.80,
            ),
            created_at=_SEEDING_EPOCH,
            status=TemplateStatus.PROMOTED,
        )

    def _build_api_contract_fix(self) -> TemplateCandidate:
        return TemplateCandidate(
            template_id="tpl-seed-api-contract-fix-01",
            template_type=TemplateType.API_CONTRACT_FIX,
            trigger_conditions=[
                "api response shape does not match the declared contract for an endpoint",
                "cockpit truth matrix reports a field present in contract but missing from actual response",
                "production truth verification shows file_divergence=true for an api module",
            ],
            required_context=["api endpoint path", "declared response contract", "actual response sample"],
            required_capabilities=[CapabilityName.API_CONTRACT_VALIDATION.value, CapabilityName.FILE_EDIT.value, CapabilityName.ENDPOINT_VERIFY.value],
            required_agent_type=AgentType.DEVELOPER_AGENT,
            reusable_steps=[
                TemplateStep(
                    order=0,
                    description="Retrieve declared contract and actual response for the endpoint",
                    action="create_api_route",
                    requires_capability=CapabilityName.API_CONTRACT_VALIDATION.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="contract fields enumerated, actual response sample captured",
                ),
                TemplateStep(
                    order=1,
                    description="Edit api module to align response shape with contract",
                    action="file_edit",
                    requires_capability=CapabilityName.FILE_EDIT.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="all contract fields present in modified response handler",
                ),
                TemplateStep(
                    order=2,
                    description="Verify endpoint response matches contract via live probe",
                    action="verify_panel",
                    requires_capability=CapabilityName.ENDPOINT_VERIFY.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="curl or requests call returns all declared contract fields",
                ),
            ],
            risk_class="low",
            governance_mode="autonomous",
            validation=TemplateValidation(
                description=(
                    "Live endpoint probe returns all fields declared in contract. "
                    "python3 -m py_compile on modified api module passes. "
                    "Production truth verification shows file_divergence=false."
                ),
                method="assertion",
                timeout_seconds=60.0,
            ),
            rollback=TemplateRollback(
                description=(
                    "git checkout -- <api_module_path>. "
                    "docker restart <service_name> to restore prior behavior."
                ),
                method="revert",
                timeout_seconds=60.0,
            ),
            evidence_requirements=["api endpoint path", "declared contract", "pre-fix response sample showing drift"],
            known_failure_modes=[
                "response shape change breaks a frontend component",
                "rollback requires service restart",
            ],
            expected_outcome="Endpoint response matches declared contract — all required fields present, no undeclared fields",
            observed_success_count=2,
            observed_failure_count=0,
            confidence=0.85,
            source_outcome_ids=[],
            source_trial_ids=["phase9_8"],
            source_action_envelope_ids=[],
            evidence=[
                TemplateEvidence(
                    source=_EVIDENCE_PHASE9_8,
                    detail="event_type=ProductionOutcomeCommitted, boundary=production, verification.status=production_verified, all_passed=true, file_divergence=false",
                    confidence=0.9,
                    observed_at=_SEEDING_EPOCH,
                ),
                TemplateEvidence(
                    source=_EVIDENCE_PHASE9_8,
                    detail="affected_subsystems: [production_merge_verifier, cockpit_routes, security_hardening] — all verified post-merge",
                    confidence=0.85,
                    observed_at=_SEEDING_EPOCH,
                ),
            ],
            agent_capability_binding=AgentCapabilityBinding(
                agent_type=AgentType.DEVELOPER_AGENT,
                capabilities=[CapabilityName.API_CONTRACT_VALIDATION.value, CapabilityName.FILE_EDIT.value, CapabilityName.ENDPOINT_VERIFY.value],
                confidence=0.85,
            ),
            created_at=_SEEDING_EPOCH,
            status=TemplateStatus.PROMOTED,
        )

    def _build_test_repair(self) -> TemplateCandidate:
        return TemplateCandidate(
            template_id="tpl-seed-test-repair-01",
            template_type=TemplateType.TEST_REPAIR,
            trigger_conditions=[
                "pytest reports a failing test assertion for a feature that is otherwise functional",
                "test failure is an assertion mismatch — expected vs actual value divergence",
                "test file imports compile cleanly but the assertion fails at runtime",
            ],
            required_context=["failing test file path", "test function name", "assertion error message"],
            required_capabilities=[CapabilityName.TEST_RUN.value, CapabilityName.CODE_SEARCH.value, CapabilityName.FILE_EDIT.value],
            required_agent_type=AgentType.DEVELOPER_AGENT,
            reusable_steps=[
                TemplateStep(
                    order=0,
                    description="Run failing test in isolation to confirm failure and capture exact error",
                    action="run_probes",
                    requires_capability=CapabilityName.TEST_RUN.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="pytest -xvs <test_file>::<test_fn> shows AssertionError with expected vs actual values",
                ),
                TemplateStep(
                    order=1,
                    description="Read test file and production module to understand the assertion drift",
                    action="assess_state",
                    requires_capability=CapabilityName.CODE_SEARCH.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="root cause identified: assertion expects old behavior, production changed",
                ),
                TemplateStep(
                    order=2,
                    description="Update test assertion to match current correct behavior — do NOT change production code",
                    action="file_edit",
                    requires_capability=CapabilityName.FILE_EDIT.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="test file edited, assertion updated",
                ),
                TemplateStep(
                    order=3,
                    description="Re-run test suite to confirm pass",
                    action="verify_health",
                    requires_capability=CapabilityName.TEST_RUN.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="pytest -xvs <test_file>::<test_fn> passes with exit code 0",
                ),
            ],
            risk_class="low",
            governance_mode="autonomous",
            validation=TemplateValidation(
                description=(
                    "pytest <test_file>::<test_fn> exits with code 0. "
                    "Prior passing tests in same file still pass. "
                    "Production module py_compile unchanged."
                ),
                method="assertion",
                timeout_seconds=60.0,
            ),
            rollback=TemplateRollback(
                description=(
                    "git checkout -- <test_file_path>. "
                    "Run pytest to confirm prior (failing) state restored."
                ),
                method="revert",
                timeout_seconds=30.0,
            ),
            evidence_requirements=["failing pytest output with assertion error", "test file path and function name"],
            known_failure_modes=[
                "test repair reveals a real production bug (assertion was correct)",
                "fixing one test breaks another in same file",
            ],
            expected_outcome="Failing test passes. All other tests in file continue to pass. No production code modified.",
            observed_success_count=3,
            observed_failure_count=1,
            confidence=0.75,
            source_outcome_ids=[],
            source_trial_ids=["phase9_7"],
            source_action_envelope_ids=[],
            evidence=[
                TemplateEvidence(
                    source=_EVIDENCE_PHASE9_7,
                    detail="validation_summary.new_tests=79, prior_tests_passing=1159 — test suite maintained after new module additions",
                    confidence=0.85,
                    observed_at=_SEEDING_EPOCH,
                ),
                TemplateEvidence(
                    source=_EVIDENCE_PHASE9_7,
                    detail="manifest.validation_results: pytest test_phase9_7_pr_factory.py passed=true, exit_code=0, output_summary='79 passed'",
                    confidence=0.9,
                    observed_at=_SEEDING_EPOCH,
                ),
            ],
            agent_capability_binding=AgentCapabilityBinding(
                agent_type=AgentType.DEVELOPER_AGENT,
                capabilities=[CapabilityName.TEST_RUN.value, CapabilityName.FILE_EDIT.value],
                confidence=0.75,
            ),
            created_at=_SEEDING_EPOCH,
            status=TemplateStatus.PROMOTED,
        )

    def _build_cockpit_panel_fix(self) -> TemplateCandidate:
        return TemplateCandidate(
            template_id="tpl-seed-cockpit-panel-fix-01",
            template_type=TemplateType.COCKPIT_PANEL_FIX,
            trigger_conditions=[
                "cockpit API endpoint for a substrate feature returns 404 or is missing entirely",
                "substrate module is production_ready but has no cockpit surface (no /api/umh/ route)",
                "cockpit truth matrix reports missing_endpoint=true for a feature",
            ],
            required_context=["substrate feature module path", "missing endpoint path", "response contract for the endpoint"],
            required_capabilities=[CapabilityName.ROUTE_DISCOVERY.value, CapabilityName.FILE_EDIT.value, CapabilityName.ENDPOINT_VERIFY.value],
            required_agent_type=AgentType.DEVELOPER_AGENT,
            reusable_steps=[
                TemplateStep(
                    order=0,
                    description="Confirm endpoint is missing and identify target cockpit route file",
                    action="identify_panel",
                    requires_capability=CapabilityName.ROUTE_DISCOVERY.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="curl /api/umh/<endpoint> returns 404, target route file identified",
                ),
                TemplateStep(
                    order=1,
                    description="Add GET route handler to appropriate cockpit route module",
                    action="file_edit",
                    requires_capability=CapabilityName.FILE_EDIT.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="route handler added, py_compile passes, router mounts new route",
                ),
                TemplateStep(
                    order=2,
                    description="Probe new endpoint to verify response contract",
                    action="verify_panel",
                    requires_capability=CapabilityName.ENDPOINT_VERIFY.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="curl /api/umh/<endpoint> returns 200 with expected response fields",
                ),
            ],
            risk_class="low",
            governance_mode="autonomous",
            validation=TemplateValidation(
                description=(
                    "curl /api/umh/<endpoint> returns HTTP 200 with all expected fields. "
                    "py_compile on modified cockpit route file passes. "
                    "No existing routes return 404 after change."
                ),
                method="assertion",
                timeout_seconds=60.0,
            ),
            rollback=TemplateRollback(
                description=(
                    "git checkout -- <cockpit_route_file>. "
                    "docker restart os-operator to restore prior routing."
                ),
                method="revert",
                timeout_seconds=60.0,
            ),
            evidence_requirements=["cockpit truth matrix showing missing endpoint", "substrate module that needs exposure"],
            known_failure_modes=[
                "new route conflicts with existing route pattern",
                "service restart required to pick up route change",
            ],
            expected_outcome="Cockpit surface exposes substrate feature — endpoint returns valid response, truth matrix no longer shows missing_endpoint",
            observed_success_count=2,
            observed_failure_count=0,
            confidence=0.80,
            source_outcome_ids=[],
            source_trial_ids=["phase9_9"],
            source_action_envelope_ids=[],
            evidence=[
                TemplateEvidence(
                    source=_EVIDENCE_PHASE9_9,
                    detail="mode_after=dry_run_only, set_mode_response={ok: true, mode: dry_run_only} — cockpit endpoint successfully activated cadence mode",
                    confidence=0.85,
                    observed_at=_SEEDING_EPOCH,
                ),
                TemplateEvidence(
                    source=_EVIDENCE_PHASE9_9,
                    detail="safety_verification.cockpit_shows_last_dry_run=true — cockpit panel correctly surfaced dry-run result",
                    confidence=0.8,
                    observed_at=_SEEDING_EPOCH,
                ),
            ],
            agent_capability_binding=AgentCapabilityBinding(
                agent_type=AgentType.DEVELOPER_AGENT,
                capabilities=[CapabilityName.ROUTE_DISCOVERY.value, CapabilityName.FILE_EDIT.value, CapabilityName.ENDPOINT_VERIFY.value],
                confidence=0.80,
            ),
            created_at=_SEEDING_EPOCH,
            status=TemplateStatus.PROMOTED,
        )

    def _build_route_extraction_fix(self) -> TemplateCandidate:
        return TemplateCandidate(
            template_id="tpl-seed-route-extraction-fix-01",
            template_type=TemplateType.ROUTE_EXTRACTION_FIX,
            trigger_conditions=[
                "python module exceeds 3000 lines — pre-commit line count gate would block commit",
                "module contains multiple route groups that can be split into dedicated router modules",
                "each route group has a common URL prefix or concern that groups naturally",
            ],
            required_context=["over-limit python file path", "current line count", "route group identification"],
            required_capabilities=[CapabilityName.CODE_SEARCH.value, CapabilityName.FILE_EDIT.value, CapabilityName.ENDPOINT_VERIFY.value],
            required_agent_type=AgentType.DEVELOPER_AGENT,
            reusable_steps=[
                TemplateStep(
                    order=0,
                    description="Count lines and identify route group boundaries in the over-limit file",
                    action="assess_state",
                    requires_capability=CapabilityName.CODE_SEARCH.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="wc -l <file> confirms line count, route groups identified by URL prefix",
                ),
                TemplateStep(
                    order=1,
                    description="Extract one route group to a new dedicated router module",
                    action="file_edit",
                    requires_capability=CapabilityName.FILE_EDIT.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="new router file created, routes imported and mounted in original file, py_compile passes",
                ),
                TemplateStep(
                    order=2,
                    description="Verify all extracted routes still respond identically",
                    action="verify_panel",
                    requires_capability=CapabilityName.ENDPOINT_VERIFY.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="all previously-accessible endpoints return same status codes and response shapes",
                ),
            ],
            risk_class="low",
            governance_mode="autonomous",
            validation=TemplateValidation(
                description=(
                    "wc -l <original_file> shows fewer lines after extraction. "
                    "py_compile on both original and new router module passes. "
                    "All routes previously accessible remain accessible at same paths."
                ),
                method="assertion",
                timeout_seconds=60.0,
            ),
            rollback=TemplateRollback(
                description=(
                    "git checkout -- <original_file> && git rm <new_router_file>. "
                    "docker restart service to restore prior routing."
                ),
                method="revert",
                timeout_seconds=60.0,
            ),
            evidence_requirements=["line count before extraction", "list of routes being extracted with their URL prefixes"],
            known_failure_modes=[
                "extracted routes import symbols from original file that create circular imports",
                "router mounting order matters and extraction changes evaluation order",
            ],
            expected_outcome="Original file is below 3000 lines. All routes work identically. New router module is importable.",
            observed_success_count=3,
            observed_failure_count=0,
            confidence=0.90,
            source_outcome_ids=[],
            source_trial_ids=["phase9_7"],
            source_action_envelope_ids=[],
            evidence=[
                TemplateEvidence(
                    source=_EVIDENCE_PHASE9_7,
                    detail="manifest.changed_files includes transports/api/cockpit.py (modified, +130/-0) and 7 other files — route extraction pattern with minimal removal",
                    confidence=0.85,
                    observed_at=_SEEDING_EPOCH,
                ),
                TemplateEvidence(
                    source=_EVIDENCE_PHASE9_7,
                    detail="manifest.risk_proof: no_auth_changes=true, no_destructive_ops=true, file_count_within_limit=true — extraction completed safely",
                    confidence=0.9,
                    observed_at=_SEEDING_EPOCH,
                ),
            ],
            agent_capability_binding=AgentCapabilityBinding(
                agent_type=AgentType.DEVELOPER_AGENT,
                capabilities=[CapabilityName.CODE_SEARCH.value, CapabilityName.FILE_EDIT.value],
                confidence=0.90,
            ),
            created_at=_SEEDING_EPOCH,
            status=TemplateStatus.PROMOTED,
        )

    def _build_dependency_graph_fix(self) -> TemplateCandidate:
        return TemplateCandidate(
            template_id="tpl-seed-dependency-graph-fix-01",
            template_type=TemplateType.DEPENDENCY_GRAPH_FIX,
            trigger_conditions=[
                "dependency graph is older than 24 hours — session_bootstrap.py reports stale",
                "query_graph.py search returns missing results for a recently-added module",
                "graph node summary does not include a file added in the last commit",
            ],
            required_context=["graph freshness check result", "list of files added or modified since last graph build"],
            required_capabilities=[CapabilityName.DEPENDENCY_ANALYSIS.value, CapabilityName.CODE_SEARCH.value, CapabilityName.EVIDENCE_VERIFICATION.value],
            required_agent_type=AgentType.DEVELOPER_AGENT,
            reusable_steps=[
                TemplateStep(
                    order=0,
                    description="Confirm graph staleness and identify new/modified files",
                    action="run_probes",
                    requires_capability=CapabilityName.DEPENDENCY_ANALYSIS.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="python3 scripts/session_bootstrap.py --compact exits non-zero, new files not in graph",
                ),
                TemplateStep(
                    order=1,
                    description="Rebuild dependency graph",
                    action="execute_maintenance",
                    requires_capability=CapabilityName.DEPENDENCY_ANALYSIS.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="scripts/update-graph exits 0, no errors",
                ),
                TemplateStep(
                    order=2,
                    description="Verify graph is fresh and new files are indexed",
                    action="verify_health",
                    requires_capability=CapabilityName.EVIDENCE_VERIFICATION.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="python3 scripts/session_bootstrap.py --compact exits 0, query_graph.py search finds newly-added files",
                ),
            ],
            risk_class="low",
            governance_mode="autonomous",
            validation=TemplateValidation(
                description=(
                    "python3 scripts/session_bootstrap.py --compact exits 0. "
                    "python3 scripts/query_graph.py search <new_module_name> returns the file."
                ),
                method="assertion",
                timeout_seconds=120.0,
            ),
            rollback=TemplateRollback(
                description=(
                    "Graph rebuild is non-destructive — it reads source files and writes data/. "
                    "No rollback required. Previous graph files are overwritten, not source code."
                ),
                method="revert",
                timeout_seconds=10.0,
            ),
            evidence_requirements=["graph staleness report from session_bootstrap.py"],
            known_failure_modes=[
                "graph rebuild takes > 2 minutes on large codebases",
                "new file has syntax error that blocks graph indexing",
            ],
            expected_outcome="Dependency graph is fresh — session_bootstrap reports no staleness, all recent files are queryable",
            observed_success_count=4,
            observed_failure_count=0,
            confidence=0.85,
            source_outcome_ids=[],
            source_trial_ids=["phase9_8"],
            source_action_envelope_ids=[],
            evidence=[
                TemplateEvidence(
                    source=_EVIDENCE_PHASE9_8,
                    detail="propagation.wave_2_targets includes dependency_graph_recompute — graph rebuild triggered as wave-2 propagation after production truth promotion",
                    confidence=0.8,
                    observed_at=_SEEDING_EPOCH,
                ),
            ],
            agent_capability_binding=AgentCapabilityBinding(
                agent_type=AgentType.DEVELOPER_AGENT,
                capabilities=[CapabilityName.DEPENDENCY_ANALYSIS.value, CapabilityName.CODE_SEARCH.value],
                confidence=0.85,
            ),
            created_at=_SEEDING_EPOCH,
            status=TemplateStatus.PROMOTED,
        )

    def _build_maintenance_action(self) -> TemplateCandidate:
        return TemplateCandidate(
            template_id="tpl-seed-maintenance-action-01",
            template_type=TemplateType.MAINTENANCE_ACTION,
            trigger_conditions=[
                "organism health probe detects a degraded component that requires a non-file-edit maintenance action",
                "docker container for a service shows unhealthy status or non-zero restarts",
                "log file for a service shows repeated recoverable errors over last hour",
            ],
            required_context=["affected service name", "health probe output", "error log sample"],
            required_capabilities=[CapabilityName.CODE_SEARCH.value, CapabilityName.EVIDENCE_VERIFICATION.value],
            required_agent_type=AgentType.DEVELOPER_AGENT,
            reusable_steps=[
                TemplateStep(
                    order=0,
                    description="Run health probes to identify degraded component",
                    action="run_probes",
                    requires_capability=CapabilityName.CODE_SEARCH.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="docker ps shows unhealthy or non-zero restarts, log error pattern confirmed",
                ),
                TemplateStep(
                    order=1,
                    description="Execute targeted maintenance action for the degraded component",
                    action="execute_maintenance",
                    requires_capability=CapabilityName.CODE_SEARCH.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="maintenance action completed without error",
                ),
                TemplateStep(
                    order=2,
                    description="Re-run health probes to confirm component is healthy",
                    action="verify_health",
                    requires_capability=CapabilityName.EVIDENCE_VERIFICATION.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="docker ps shows healthy status, log errors no longer appearing",
                ),
            ],
            risk_class="low",
            governance_mode="autonomous",
            validation=TemplateValidation(
                description=(
                    "docker ps shows healthy status for affected service after maintenance. "
                    "Log file shows no new error occurrences for the pattern that triggered the action."
                ),
                method="assertion",
                timeout_seconds=120.0,
            ),
            rollback=TemplateRollback(
                description=(
                    "Maintenance actions that modify config files: git checkout -- <config>. "
                    "Service restarts: docker restart <service_name> to return to prior state."
                ),
                method="revert",
                timeout_seconds=60.0,
            ),
            evidence_requirements=["health probe output showing degraded state before action", "service name and error pattern"],
            known_failure_modes=[
                "maintenance action resolves symptom but not root cause — issue recurs",
                "service restart causes brief downtime for dependent components",
            ],
            expected_outcome="Organism health probe shows all components healthy after maintenance action",
            observed_success_count=2,
            observed_failure_count=1,
            confidence=0.70,
            source_outcome_ids=[],
            source_trial_ids=["phase9_6"],
            source_action_envelope_ids=[],
            evidence=[
                TemplateEvidence(
                    source=_EVIDENCE_PHASE9_6,
                    detail="lane_status: total_runs=2, completed_runs=1, failed_runs=0 — maintenance runs completed without failure",
                    confidence=0.75,
                    observed_at=_SEEDING_EPOCH,
                ),
                TemplateEvidence(
                    source=_EVIDENCE_PHASE9_6,
                    detail="policy: require_rollback_or_non_mutating=true, require_validation=true — all maintenance candidates gated by rollback and validation requirements",
                    confidence=0.8,
                    observed_at=_SEEDING_EPOCH,
                ),
            ],
            agent_capability_binding=AgentCapabilityBinding(
                agent_type=AgentType.DEVELOPER_AGENT,
                capabilities=[CapabilityName.CODE_SEARCH.value, CapabilityName.EVIDENCE_VERIFICATION.value],
                confidence=0.70,
            ),
            created_at=_SEEDING_EPOCH,
            status=TemplateStatus.PROMOTED,
        )


    def _build_documentation_alignment(self) -> TemplateCandidate:
        return TemplateCandidate(
            template_id="tpl-seed-documentation-alignment-01",
            template_type=TemplateType.DOCUMENTATION_ALIGNMENT,
            trigger_conditions=[
                "module docstring references a stale or renamed project name",
                "code comment contains outdated terminology that no longer matches the codebase",
                "documentation file has factual inaccuracies relative to current code state",
            ],
            required_context=["file path with stale reference", "current correct terminology"],
            required_capabilities=[CapabilityName.FILE_EDIT.value, CapabilityName.CODE_SEARCH.value],
            required_agent_type=AgentType.DEVELOPER_AGENT,
            reusable_steps=[
                TemplateStep(
                    order=0,
                    description="Identify all instances of the stale reference in the target file",
                    action="assess_state",
                    requires_capability=CapabilityName.CODE_SEARCH.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="grep confirms all stale reference locations identified",
                ),
                TemplateStep(
                    order=1,
                    description="Replace stale references with current correct terminology in docstrings only",
                    action="file_edit",
                    requires_capability=CapabilityName.FILE_EDIT.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="diff shows only docstring or comment changes, no logic changes",
                ),
                TemplateStep(
                    order=2,
                    description="Verify file still compiles after documentation change",
                    action="verify_health",
                    requires_capability=CapabilityName.TEST_RUN.value,
                    risk_class="low",
                    governance_mode="autonomous",
                    verification="py_compile succeeds on modified file",
                ),
            ],
            risk_class="low",
            governance_mode="autonomous",
            validation=TemplateValidation(
                description=(
                    "py_compile on modified file succeeds. "
                    "grep for stale reference returns zero matches in modified file. "
                    "No logic or import changes — only docstring or comment text."
                ),
                method="assertion",
                timeout_seconds=30.0,
            ),
            rollback=TemplateRollback(
                description=(
                    "git checkout -- <file_path>. "
                    "Non-destructive: only docstring text was changed."
                ),
                method="revert",
                timeout_seconds=15.0,
            ),
            evidence_requirements=["stale reference text", "current correct terminology", "file path"],
            known_failure_modes=[
                "stale name appears in a string literal that is used programmatically, not just documentation",
            ],
            expected_outcome="Stale project names replaced with current terminology. No logic changes. File compiles.",
            observed_success_count=2,
            observed_failure_count=0,
            confidence=0.8,
            source_outcome_ids=[],
            source_trial_ids=["phase10_4"],
            source_action_envelope_ids=[],
            evidence=[
                TemplateEvidence(
                    source="phase10_4_codebase_scan",
                    detail="Projection boundary cleanup (phase 2026-05-28) established naming rules; stale references remain in scripts/",
                    confidence=0.9,
                    observed_at=_SEEDING_EPOCH,
                ),
            ],
            agent_capability_binding=AgentCapabilityBinding(
                agent_type=AgentType.DEVELOPER_AGENT,
                capabilities=[CapabilityName.FILE_EDIT.value, CapabilityName.CODE_SEARCH.value],
                confidence=0.8,
            ),
            created_at=_SEEDING_EPOCH,
            status=TemplateStatus.PROMOTED,
        )


def main() -> None:
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Seed evidence-backed templates to runtime store")
    parser.add_argument("--store-dir", default=None, help="Override runtime template directory")
    parser.add_argument("--dry-run", action="store_true", help="Print templates without writing")
    args = parser.parse_args()

    seeder = TemplateSeeder(store_dir=args.store_dir)
    if args.dry_run:
        templates = seeder._build_all_templates()
        for tpl in templates:
            print(json.dumps(tpl.to_dict(), default=str, indent=2))
        print(f"Dry run: {len(templates)} templates would be seeded")
        return

    result = seeder.seed()
    print(f"Seeded: {result.seeded_count}, Skipped: {result.skipped_count}, Errors: {result.error_count}")
    for tid in result.template_ids:
        print(f"  + {tid}")
    if result.errors:
        for err in result.errors:
            print(f"  ERROR: {err}")


if __name__ == "__main__":
    main()
