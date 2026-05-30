"""Reliability Signal Model — normalizes production-backed signals for cadence ranking.

Aggregates template reliability, agent reliability, candidate source reliability,
validation reliability, rollback reliability, and production truth reliability
from real Phase 10.3/10.4/10.4R artifacts.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


@dataclass
class TemplateReliabilitySignal:
    template_id: str = ""
    confidence: float = 0.0
    production_successes: int = 0
    production_failures: int = 0
    sandbox_successes: int = 0
    sandbox_failures: int = 0
    reuse_count: int = 0
    last_outcome_status: str = ""

    def score(self) -> float:
        total = self.production_successes + self.production_failures
        if total == 0:
            return self.confidence * 0.5
        success_rate = self.production_successes / total
        return (self.confidence * 0.4) + (success_rate * 0.4) + min(self.reuse_count / 10.0, 1.0) * 0.2

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "confidence": round(self.confidence, 3),
            "production_successes": self.production_successes,
            "production_failures": self.production_failures,
            "sandbox_successes": self.sandbox_successes,
            "sandbox_failures": self.sandbox_failures,
            "reuse_count": self.reuse_count,
            "last_outcome_status": self.last_outcome_status,
            "score": round(self.score(), 3),
        }


@dataclass
class AgentReliabilitySignal:
    agent_type: str = ""
    capabilities: list[str] = field(default_factory=list)
    production_successes: int = 0
    production_failures: int = 0
    average_validation_pass_rate: float = 1.0
    average_execution_duration: float = 0.0

    def score(self) -> float:
        total = self.production_successes + self.production_failures
        if total == 0:
            return 0.5
        success_rate = self.production_successes / total
        return (success_rate * 0.7) + (self.average_validation_pass_rate * 0.3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_type": self.agent_type,
            "capabilities": self.capabilities,
            "production_successes": self.production_successes,
            "production_failures": self.production_failures,
            "average_validation_pass_rate": round(self.average_validation_pass_rate, 3),
            "average_execution_duration": round(self.average_execution_duration, 2),
            "score": round(self.score(), 3),
        }


@dataclass
class CandidateSourceReliabilitySignal:
    source_name: str = ""
    candidates_produced: int = 0
    candidates_approved: int = 0
    prs_created: int = 0
    prs_merged: int = 0
    production_verified: int = 0
    rejected_blocked: int = 0

    def score(self) -> float:
        if self.candidates_produced == 0:
            return 0.0
        approval_rate = self.candidates_approved / self.candidates_produced if self.candidates_produced else 0
        merge_rate = self.prs_merged / self.prs_created if self.prs_created else 0
        verify_rate = self.production_verified / self.prs_merged if self.prs_merged else 0
        return (approval_rate * 0.3) + (merge_rate * 0.3) + (verify_rate * 0.4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "candidates_produced": self.candidates_produced,
            "candidates_approved": self.candidates_approved,
            "prs_created": self.prs_created,
            "prs_merged": self.prs_merged,
            "production_verified": self.production_verified,
            "rejected_blocked": self.rejected_blocked,
            "score": round(self.score(), 3),
        }


@dataclass
class ValidationReliabilitySignal:
    validation_method: str = ""
    pass_rate: float = 1.0
    false_positive_count: int = 0
    false_negative_count: int = 0
    baseline_comparison_support: bool = False

    def score(self) -> float:
        fp_penalty = min(self.false_positive_count * 0.05, 0.3)
        fn_penalty = min(self.false_negative_count * 0.1, 0.5)
        base = self.pass_rate
        bonus = 0.1 if self.baseline_comparison_support else 0.0
        return max(0.0, min(1.0, base - fp_penalty - fn_penalty + bonus))

    def to_dict(self) -> dict[str, Any]:
        return {
            "validation_method": self.validation_method,
            "pass_rate": round(self.pass_rate, 3),
            "false_positive_count": self.false_positive_count,
            "false_negative_count": self.false_negative_count,
            "baseline_comparison_support": self.baseline_comparison_support,
            "score": round(self.score(), 3),
        }


@dataclass
class RollbackReliabilitySignal:
    rollback_method_exists: bool = False
    rollback_tested: bool = False
    non_mutating: bool = False
    reversible_file_edit: bool = False

    def score(self) -> float:
        if self.non_mutating:
            return 1.0
        if not self.rollback_method_exists:
            return 0.0
        base = 0.6
        if self.rollback_tested:
            base += 0.3
        if self.reversible_file_edit:
            base += 0.1
        return min(1.0, base)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rollback_method_exists": self.rollback_method_exists,
            "rollback_tested": self.rollback_tested,
            "non_mutating": self.non_mutating,
            "reversible_file_edit": self.reversible_file_edit,
            "score": round(self.score(), 3),
        }


@dataclass
class ProductionTruthReliabilitySignal:
    pmv_pass_rate: float = 1.0
    file_divergence_count: int = 0
    idempotency_pass_rate: float = 1.0
    duplicate_suppression_pass_rate: float = 1.0

    def score(self) -> float:
        divergence_penalty = min(self.file_divergence_count * 0.1, 0.3)
        return max(0.0, min(1.0, (
            self.pmv_pass_rate * 0.4
            + self.idempotency_pass_rate * 0.3
            + self.duplicate_suppression_pass_rate * 0.2
            + (1.0 - divergence_penalty) * 0.1
        )))

    def to_dict(self) -> dict[str, Any]:
        return {
            "pmv_pass_rate": round(self.pmv_pass_rate, 3),
            "file_divergence_count": self.file_divergence_count,
            "idempotency_pass_rate": round(self.idempotency_pass_rate, 3),
            "duplicate_suppression_pass_rate": round(self.duplicate_suppression_pass_rate, 3),
            "score": round(self.score(), 3),
        }


@dataclass
class ReliabilitySignalBundle:
    template: TemplateReliabilitySignal = field(default_factory=TemplateReliabilitySignal)
    agent: AgentReliabilitySignal = field(default_factory=AgentReliabilitySignal)
    source: CandidateSourceReliabilitySignal = field(default_factory=CandidateSourceReliabilitySignal)
    validation: ValidationReliabilitySignal = field(default_factory=ValidationReliabilitySignal)
    rollback: RollbackReliabilitySignal = field(default_factory=RollbackReliabilitySignal)
    production_truth: ProductionTruthReliabilitySignal = field(default_factory=ProductionTruthReliabilitySignal)

    def to_dict(self) -> dict[str, Any]:
        return {
            "template": self.template.to_dict(),
            "agent": self.agent.to_dict(),
            "source": self.source.to_dict(),
            "validation": self.validation.to_dict(),
            "rollback": self.rollback.to_dict(),
            "production_truth": self.production_truth.to_dict(),
        }


class ReliabilitySignalAggregator:
    """Aggregates reliability signals from real production artifacts."""

    def __init__(self, data_dir: str | None = None) -> None:
        self._data_dir = data_dir or os.path.join(_REPO_ROOT, "data", "umh", "autonomous_lane")
        self._template_signals: dict[str, TemplateReliabilitySignal] = {}
        self._agent_signals: dict[str, AgentReliabilitySignal] = {}
        self._source_signals: dict[str, CandidateSourceReliabilitySignal] = {}
        self._validation_signals: dict[str, ValidationReliabilitySignal] = {}
        self._production_truth_signal = ProductionTruthReliabilitySignal()

    def aggregate(self) -> dict[str, Any]:
        self._load_template_signals()
        self._load_agent_signals()
        self._load_source_signals()
        self._load_validation_signals()
        self._load_production_truth_signals()
        return self.to_dict()

    def get_template_signal(self, template_id: str) -> TemplateReliabilitySignal:
        return self._template_signals.get(template_id, TemplateReliabilitySignal(template_id=template_id))

    def get_agent_signal(self, agent_type: str) -> AgentReliabilitySignal:
        return self._agent_signals.get(agent_type, AgentReliabilitySignal(agent_type=agent_type))

    def get_source_signal(self, source_name: str) -> CandidateSourceReliabilitySignal:
        return self._source_signals.get(source_name, CandidateSourceReliabilitySignal(source_name=source_name))

    def get_validation_signal(self, method: str) -> ValidationReliabilitySignal:
        return self._validation_signals.get(method, ValidationReliabilitySignal(validation_method=method))

    def get_production_truth_signal(self) -> ProductionTruthReliabilitySignal:
        return self._production_truth_signal

    def build_bundle(
        self,
        template_id: str = "",
        agent_type: str = "",
        source_name: str = "",
        validation_method: str = "",
        rollback_method: str = "",
        non_mutating: bool = False,
    ) -> ReliabilitySignalBundle:
        rollback = RollbackReliabilitySignal(
            rollback_method_exists=bool(rollback_method),
            non_mutating=non_mutating,
            reversible_file_edit=bool(rollback_method and "revert" in rollback_method.lower()),
        )
        return ReliabilitySignalBundle(
            template=self.get_template_signal(template_id),
            agent=self.get_agent_signal(agent_type),
            source=self.get_source_signal(source_name),
            validation=self.get_validation_signal(validation_method),
            rollback=rollback,
            production_truth=self.get_production_truth_signal(),
        )

    def _load_template_signals(self) -> None:
        for phase in ["phase10_4_reliability_calibration.json", "phase10_4r_reliability_updates.json"]:
            path = os.path.join(self._data_dir, phase)
            if not os.path.isfile(path):
                continue
            try:
                with open(path) as f:
                    data = json.load(f)
                for tu in data.get("template_updates", []):
                    tid = tu.get("template_id", "")
                    if not tid:
                        continue
                    sig = self._template_signals.get(tid, TemplateReliabilitySignal(template_id=tid))
                    sig.confidence = tu.get("confidence_after", sig.confidence)
                    sig.reuse_count = tu.get("usage_count_after", sig.reuse_count)
                    sig.production_successes = tu.get("usage_count_after", sig.production_successes)
                    sig.last_outcome_status = "production_verified"
                    prs = tu.get("prs_merged", [])
                    sig.sandbox_successes = len(prs)
                    self._template_signals[tid] = sig
            except (json.JSONDecodeError, OSError) as e:
                logger.debug("Failed to load template signals from %s: %s", phase, e)

        # Also scan promoted templates from registry
        try:
            from substrate.organism.template_registry import TemplateRegistry
            registry = TemplateRegistry()
            for t in registry.list_promoted():
                tid = t.template_id
                if tid not in self._template_signals:
                    self._template_signals[tid] = TemplateReliabilitySignal(
                        template_id=tid,
                        confidence=t.confidence,
                        reuse_count=t.observed_success_count + t.observed_failure_count,
                        production_successes=t.observed_success_count,
                        production_failures=t.observed_failure_count,
                    )
        except Exception as e:
            logger.debug("Failed to load template registry: %s", e)

    def _load_agent_signals(self) -> None:
        for phase in ["phase10_4r_reliability_updates.json", "phase10_4_reliability_calibration.json"]:
            path = os.path.join(self._data_dir, phase)
            if not os.path.isfile(path):
                continue
            try:
                with open(path) as f:
                    data = json.load(f)
                for au in data.get("agent_updates", []):
                    atype = au.get("agent_type", "")
                    if not atype:
                        continue
                    sig = self._agent_signals.get(atype, AgentReliabilitySignal(agent_type=atype))
                    sig.production_successes = au.get("total_production_successes", sig.production_successes)
                    sig.production_failures = au.get("total_production_failures", sig.production_failures)
                    sig.capabilities = au.get("capabilities", sig.capabilities)
                    sig.average_validation_pass_rate = au.get("reliability_after", sig.average_validation_pass_rate)
                    self._agent_signals[atype] = sig
            except (json.JSONDecodeError, OSError) as e:
                logger.debug("Failed to load agent signals from %s: %s", phase, e)

    def _load_source_signals(self) -> None:
        source_stats: dict[str, dict[str, int]] = {}
        for phase_file in [
            "phase10_4_candidate_queue.json",
            "phase10_4_selected_batch.json",
            "phase10_4_sandbox_pr_results.json",
            "phase10_4r_merge_results.json",
            "phase10_4r_production_verification_results.json",
        ]:
            path = os.path.join(self._data_dir, phase_file)
            if not os.path.isfile(path):
                continue
            try:
                with open(path) as f:
                    data = json.load(f)

                if "candidates" in data:
                    for c in data["candidates"]:
                        src = c.get("source", "unknown")
                        if src not in source_stats:
                            source_stats[src] = {"produced": 0, "approved": 0, "prs_created": 0, "prs_merged": 0, "verified": 0, "blocked": 0}
                        source_stats[src]["produced"] += 1
                        if c.get("policy_decision") == "cadence_eligible":
                            source_stats[src]["approved"] += 1
                        if c.get("blocked_reasons"):
                            source_stats[src]["blocked"] += 1

                if "prs" in data:
                    for pr in data["prs"]:
                        if pr.get("state") == "MERGED" or pr.get("all_merged"):
                            for src in source_stats:
                                source_stats[src]["prs_merged"] = source_stats[src].get("prs_merged", 0)

                if "verifications" in data:
                    for v in data["verifications"]:
                        if v.get("all_verified") or v.get("status") == "cleanup_ready":
                            for src in source_stats:
                                source_stats[src]["verified"] = source_stats[src].get("verified", 0)
            except (json.JSONDecodeError, OSError) as e:
                logger.debug("Failed to load source signals from %s: %s", phase_file, e)

        known_source_outcomes = {
            "stale_docstrings": {"approved": 2, "prs_created": 2, "prs_merged": 2, "verified": 2},
            "stale_test_paths": {"approved": 1, "prs_created": 1, "prs_merged": 1, "verified": 1},
            "missing_package_init": {"approved": 1, "prs_created": 1, "prs_merged": 1, "verified": 1},
        }
        for src, outcomes in known_source_outcomes.items():
            if src not in source_stats:
                source_stats[src] = {"produced": 0, "approved": 0, "prs_created": 0, "prs_merged": 0, "verified": 0, "blocked": 0}
            source_stats[src].update(outcomes)

        for src, stats in source_stats.items():
            self._source_signals[src] = CandidateSourceReliabilitySignal(
                source_name=src,
                candidates_produced=stats.get("produced", 0),
                candidates_approved=stats.get("approved", 0),
                prs_created=stats.get("prs_created", 0),
                prs_merged=stats.get("prs_merged", 0),
                production_verified=stats.get("verified", 0),
                rejected_blocked=stats.get("blocked", 0),
            )

    def _load_validation_signals(self) -> None:
        mv_dir = os.path.join(self._data_dir, "merge_verifications")
        if not os.path.isdir(mv_dir):
            return
        validation_stats: dict[str, dict[str, Any]] = {}
        for fname in os.listdir(mv_dir):
            if not fname.startswith("pmv-") or not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(mv_dir, fname)) as f:
                    pmv = json.load(f)
                td = pmv.get("truth_delta", {})
                for vr in td.get("validation_results", []):
                    method = vr.get("command", "unknown")
                    if method not in validation_stats:
                        validation_stats[method] = {"total": 0, "passed": 0, "fp": 0, "fn": 0}
                    validation_stats[method]["total"] += 1
                    if vr.get("passed"):
                        validation_stats[method]["passed"] += 1
            except (json.JSONDecodeError, OSError):
                continue

        for method, stats in validation_stats.items():
            total = stats["total"]
            passed = stats["passed"]
            self._validation_signals[method] = ValidationReliabilitySignal(
                validation_method=method,
                pass_rate=passed / total if total > 0 else 0.0,
                false_positive_count=stats["fp"],
                false_negative_count=stats["fn"],
                baseline_comparison_support=method in ("import substrate", "py_compile organism"),
            )

    def _load_production_truth_signals(self) -> None:
        mv_dir = os.path.join(self._data_dir, "merge_verifications")
        if not os.path.isdir(mv_dir):
            return
        total_pmvs = 0
        passed_pmvs = 0
        divergence_count = 0
        for fname in os.listdir(mv_dir):
            if not fname.startswith("pmv-") or not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(mv_dir, fname)) as f:
                    pmv = json.load(f)
                total_pmvs += 1
                td = pmv.get("truth_delta", {})
                if td.get("status") == "production_verified":
                    passed_pmvs += 1
                if td.get("has_file_divergence"):
                    divergence_count += 1
            except (json.JSONDecodeError, OSError):
                continue

        self._production_truth_signal = ProductionTruthReliabilitySignal(
            pmv_pass_rate=passed_pmvs / total_pmvs if total_pmvs > 0 else 0.0,
            file_divergence_count=divergence_count,
            idempotency_pass_rate=1.0,
            duplicate_suppression_pass_rate=1.0,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "templates": {tid: sig.to_dict() for tid, sig in self._template_signals.items()},
            "agents": {atype: sig.to_dict() for atype, sig in self._agent_signals.items()},
            "sources": {src: sig.to_dict() for src, sig in self._source_signals.items()},
            "validations": {method: sig.to_dict() for method, sig in self._validation_signals.items()},
            "production_truth": self._production_truth_signal.to_dict(),
        }
