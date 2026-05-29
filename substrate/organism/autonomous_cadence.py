"""Autonomous Cadence — scheduled autonomous improvement discovery.

Runs autonomous improvement discovery on a configurable schedule.
Default mode is OFF — no production mutation without explicit
operator policy enabling PR creation.

Doctrine:
  - Default does not mutate production.
  - PR creation requires explicit operator policy.
  - No auto-merge ever.
  - Every scheduled decision visible in cockpit.
  - Every production truth update journaled.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


class CadenceMode(str, Enum):
    OFF = "off"
    DRY_RUN_ONLY = "dry_run_only"
    PROPOSE_PR = "propose_pr"
    CREATE_PR_WITH_OPERATOR_POLICY = "create_pr_with_operator_policy"
    PRODUCTION_VERIFY_ONLY = "production_verify_only"


@dataclass
class CadencePolicy:
    mode: CadenceMode = CadenceMode.OFF
    max_dry_runs_per_day: int = 24
    max_prs_per_day: int = 1
    max_active_sandboxes: int = 2
    max_active_prs: int = 3
    allowed_risk: str = "low"
    require_template: bool = True
    require_agent_reliability: bool = True
    require_validation: bool = True
    require_rollback_or_non_mutating: bool = True
    require_operator_enable_for_pr_creation: bool = True
    no_auto_merge: bool = True
    interval_seconds: int = 3600

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "max_dry_runs_per_day": self.max_dry_runs_per_day,
            "max_prs_per_day": self.max_prs_per_day,
            "max_active_sandboxes": self.max_active_sandboxes,
            "max_active_prs": self.max_active_prs,
            "allowed_risk": self.allowed_risk,
            "require_template": self.require_template,
            "require_agent_reliability": self.require_agent_reliability,
            "require_validation": self.require_validation,
            "require_rollback_or_non_mutating": self.require_rollback_or_non_mutating,
            "require_operator_enable_for_pr_creation": self.require_operator_enable_for_pr_creation,
            "no_auto_merge": self.no_auto_merge,
            "interval_seconds": self.interval_seconds,
        }


@dataclass
class CadenceRunResult:
    run_id: str = field(default_factory=lambda: f"cdr-{uuid4().hex[:8]}")
    mode: CadenceMode = CadenceMode.OFF
    candidates_found: int = 0
    candidates_blocked: int = 0
    candidates_eligible: int = 0
    dry_run_results: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    pr_queued: bool = False
    pr_created: bool = False
    error: str = ""
    started_at: float = field(default_factory=time.time)
    completed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "mode": self.mode.value,
            "candidates_found": self.candidates_found,
            "candidates_blocked": self.candidates_blocked,
            "candidates_eligible": self.candidates_eligible,
            "dry_run_results": self.dry_run_results,
            "recommendations": self.recommendations,
            "pr_queued": self.pr_queued,
            "pr_created": self.pr_created,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class AutonomousCadence:
    """Scheduled autonomous improvement discovery and management."""

    def __init__(
        self,
        policy: CadencePolicy | None = None,
        candidate_discovery_fn: Callable[[], list[dict[str, Any]]] | None = None,
        dry_run_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        pr_creation_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        merge_verification_fn: Callable[[], list[dict[str, Any]]] | None = None,
    ) -> None:
        self._policy = policy or CadencePolicy()
        self._candidate_discovery_fn = candidate_discovery_fn
        self._dry_run_fn = dry_run_fn
        self._pr_creation_fn = pr_creation_fn
        self._merge_verification_fn = merge_verification_fn

        self._run_history: list[CadenceRunResult] = []
        self._dry_runs_today: int = 0
        self._prs_today: int = 0
        self._last_run_at: float = 0.0
        self._last_day_reset: float = time.time()
        self._pending_recommendations: list[dict[str, Any]] = []

    @property
    def policy(self) -> CadencePolicy:
        return self._policy

    @policy.setter
    def policy(self, value: CadencePolicy) -> None:
        self._policy = value

    @property
    def mode(self) -> CadenceMode:
        return self._policy.mode

    @mode.setter
    def mode(self, value: CadenceMode) -> None:
        self._policy.mode = value

    def _reset_daily_counters_if_needed(self) -> None:
        now = time.time()
        if now - self._last_day_reset > 86400:
            self._dry_runs_today = 0
            self._prs_today = 0
            self._last_day_reset = now

    def should_run(self) -> bool:
        if self._policy.mode == CadenceMode.OFF:
            return False
        now = time.time()
        elapsed = now - self._last_run_at
        return elapsed >= self._policy.interval_seconds

    def tick(self) -> dict[str, Any]:
        if self._policy.mode == CadenceMode.OFF:
            return {"action": "off", "skipped": True}

        if not self.should_run():
            return {"action": "not_due", "skipped": True}

        self._reset_daily_counters_if_needed()

        if self._policy.mode == CadenceMode.PRODUCTION_VERIFY_ONLY:
            return self._production_verify_tick()

        result = self.run_cycle()
        return result.to_dict()

    def run_cycle(self) -> CadenceRunResult:
        self._reset_daily_counters_if_needed()
        result = CadenceRunResult(mode=self._policy.mode)

        try:
            candidates = self._discover_candidates()
            result.candidates_found = len(candidates)

            eligible, blocked = self._filter_candidates(candidates)
            result.candidates_eligible = len(eligible)
            result.candidates_blocked = len(blocked)

            if self._policy.mode in (
                CadenceMode.DRY_RUN_ONLY,
                CadenceMode.PROPOSE_PR,
                CadenceMode.CREATE_PR_WITH_OPERATOR_POLICY,
            ):
                if self._dry_runs_today < self._policy.max_dry_runs_per_day:
                    dry_results = self._run_dry_runs(eligible)
                    result.dry_run_results = dry_results
                    self._dry_runs_today += 1

            if self._policy.mode == CadenceMode.PROPOSE_PR:
                recs = self._build_recommendations(eligible)
                result.recommendations = recs
                self._pending_recommendations.extend(recs)

            if self._policy.mode == CadenceMode.CREATE_PR_WITH_OPERATOR_POLICY:
                if (
                    not self._policy.require_operator_enable_for_pr_creation
                    and self._prs_today < self._policy.max_prs_per_day
                    and eligible
                ):
                    pr_result = self._create_pr(eligible[0])
                    result.pr_created = bool(pr_result)
                    self._prs_today += 1
                else:
                    recs = self._build_recommendations(eligible)
                    result.recommendations = recs
                    result.pr_queued = bool(recs)

        except Exception as exc:
            result.error = str(exc)[:500]
            logger.exception("Cadence cycle failed")

        result.completed_at = time.time()
        self._last_run_at = time.time()
        self._run_history.append(result)
        if len(self._run_history) > 100:
            self._run_history = self._run_history[-100:]
        return result

    def _production_verify_tick(self) -> dict[str, Any]:
        if self._merge_verification_fn:
            pending = self._merge_verification_fn()
            self._last_run_at = time.time()
            return {
                "action": "production_verify",
                "pending_verifications": len(pending),
                "results": pending,
            }
        self._last_run_at = time.time()
        return {"action": "production_verify", "pending_verifications": 0}

    def _discover_candidates(self) -> list[dict[str, Any]]:
        if self._candidate_discovery_fn:
            return self._candidate_discovery_fn()
        return []

    def _filter_candidates(
        self, candidates: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        eligible: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []

        for c in candidates:
            reasons: list[str] = []
            risk = c.get("risk_class", "unknown")
            if risk != self._policy.allowed_risk:
                reasons.append(f"risk={risk}")
            if self._policy.require_template and not c.get("template_id"):
                reasons.append("no_template")
            if self._policy.require_agent_reliability and not c.get(
                "agent_reliability", 0
            ):
                reasons.append("no_agent_reliability")
            if self._policy.require_validation and not c.get("validation_method"):
                reasons.append("no_validation")
            if self._policy.require_rollback_or_non_mutating:
                if not c.get("rollback_method") and not c.get("non_mutating"):
                    reasons.append("no_rollback_or_non_mutating")

            if reasons:
                c["block_reasons"] = reasons
                blocked.append(c)
            else:
                eligible.append(c)

        return eligible, blocked

    def _run_dry_runs(
        self, candidates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        results = []
        for c in candidates[:5]:
            if self._dry_run_fn:
                dr = self._dry_run_fn(c)
            else:
                dr = {
                    "candidate_id": c.get("candidate_id", ""),
                    "dry_run": True,
                    "would_proceed": True,
                    "risk_class": c.get("risk_class", "low"),
                }
            results.append(dr)
        return results

    def _build_recommendations(
        self, candidates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        recs = []
        for c in candidates[:3]:
            recs.append({
                "candidate_id": c.get("candidate_id", ""),
                "description": c.get("description", ""),
                "risk_class": c.get("risk_class", "low"),
                "recommended": True,
                "reason": "eligible after filtering",
            })
        return recs

    def _create_pr(self, candidate: dict[str, Any]) -> dict[str, Any]:
        if self._pr_creation_fn:
            return self._pr_creation_fn(candidate)
        return {}

    def status(self) -> dict[str, Any]:
        self._reset_daily_counters_if_needed()
        last_run = self._run_history[-1] if self._run_history else None
        return {
            "mode": self._policy.mode.value,
            "interval_seconds": self._policy.interval_seconds,
            "last_run_at": self._last_run_at,
            "dry_runs_today": self._dry_runs_today,
            "prs_today": self._prs_today,
            "total_runs": len(self._run_history),
            "pending_recommendations": len(self._pending_recommendations),
            "should_run": self.should_run(),
            "last_run": last_run.to_dict() if last_run else None,
            "policy": self._policy.to_dict(),
        }

    def to_dict(self) -> dict[str, Any]:
        return self.status()
