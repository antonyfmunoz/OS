"""Mutation Equivalence Scorer — Benchmark H for C33.

Verifies that every surface produces the same canonical mutation.
No surface bypasses the GovernedExecutionSpine. No private control
paths. Agent mutations and human mutations are structurally identical.

Method: For each core mutation type, compare human-initiated (Run A)
vs agent-initiated (Run B). Both must produce identical ActionEnvelope
shapes, governance classifications, journal entries, and proof packages.

All scoring is deterministic. No LLM calls.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_STORE_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "c33", "mutation_equivalence.jsonl"
)

CORE_MUTATIONS = [
    "create_work_packet",
    "approve_action",
    "reject_action",
    "launch_cc_session",
    "complete_dev_session",
    "register_projection_event",
    "update_adapter_status",
    "attach_proof",
    "create_decision",
    "mark_blocker",
]

_CHECK_NAMES = [
    "envelope_shape",
    "governance_classification",
    "approval_behavior",
    "journal_entry",
    "proof_package",
    "resulting_state",
    "realtime_event",
    "rollback_path",
]


@dataclass
class MutationPair:
    pair_id: str = field(default_factory=lambda: f"mp-{uuid4().hex[:8]}")
    mutation_type: str = ""
    timestamp: float = field(default_factory=time.time)

    human_envelope_id: str = ""
    human_surface: str = ""
    human_source: str = ""

    agent_envelope_id: str = ""
    agent_surface: str = ""
    agent_source: str = ""

    envelope_shape_match: bool = False
    governance_match: bool = False
    approval_match: bool = False
    journal_match: bool = False
    proof_match: bool = False
    state_match: bool = False
    realtime_event_match: bool = False
    rollback_match: bool = False

    human_bypassed_spine: bool = False
    agent_bypassed_spine: bool = False

    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MutationPair:
        fields = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**fields)

    @property
    def checks_passed(self) -> int:
        return sum([
            self.envelope_shape_match,
            self.governance_match,
            self.approval_match,
            self.journal_match,
            self.proof_match,
            self.state_match,
            self.realtime_event_match,
            self.rollback_match,
        ])

    @property
    def spine_bypassed(self) -> bool:
        return self.human_bypassed_spine or self.agent_bypassed_spine


@dataclass
class MutationEquivalenceScore:
    pair_id: str = ""
    mutation_type: str = ""
    checks_total: int = 8
    checks_passed: int = 0
    score: float = 0.0
    spine_bypass: bool = False
    failed_checks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MutationEquivalenceScorer:
    """Scores mutation equivalence across human and agent execution paths."""

    def __init__(self, store_path: str = _STORE_PATH) -> None:
        self._path = store_path
        self._pairs: list[MutationPair] = []
        self._scores: list[MutationEquivalenceScore] = []
        self._load()

    def _load(self) -> None:
        if not os.path.isfile(self._path):
            return
        try:
            with open(self._path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        self._pairs.append(MutationPair.from_dict(d))
                    except (json.JSONDecodeError, TypeError) as exc:
                        logger.debug("Skip malformed mutation pair: %s", exc)
        except OSError as exc:
            logger.debug("Cannot read %s: %s", self._path, exc)

    def _persist(self, pair: MutationPair) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "a") as f:
            f.write(json.dumps(pair.to_dict(), default=str) + "\n")

    def record_pair(self, pair: MutationPair) -> MutationEquivalenceScore:
        self._pairs.append(pair)
        self._persist(pair)
        score = self.score_pair(pair)
        self._scores.append(score)
        return score

    def score_pair(self, pair: MutationPair) -> MutationEquivalenceScore:
        checks = [
            ("envelope_shape", pair.envelope_shape_match),
            ("governance_classification", pair.governance_match),
            ("approval_behavior", pair.approval_match),
            ("journal_entry", pair.journal_match),
            ("proof_package", pair.proof_match),
            ("resulting_state", pair.state_match),
            ("realtime_event", pair.realtime_event_match),
            ("rollback_path", pair.rollback_match),
        ]

        passed = sum(1 for _, v in checks if v)
        failed = [name for name, v in checks if not v]

        return MutationEquivalenceScore(
            pair_id=pair.pair_id,
            mutation_type=pair.mutation_type,
            checks_total=len(checks),
            checks_passed=passed,
            score=round(passed / len(checks), 4) if checks else 0.0,
            spine_bypass=pair.spine_bypassed,
            failed_checks=failed,
        )

    def score_all(self) -> dict[str, Any]:
        if not self._pairs:
            return {
                "count": 0,
                "composite": 0.0,
                "pass": False,
                "coverage": 0,
                "required_mutations": len(CORE_MUTATIONS),
            }

        scores = [self.score_pair(p) for p in self._pairs]
        n = len(scores)

        composite = round(sum(s.score for s in scores) / n, 4)
        any_bypass = any(s.spine_bypass for s in scores)

        covered = {p.mutation_type for p in self._pairs}
        uncovered = [m for m in CORE_MUTATIONS if m not in covered]

        all_envelope_match = all(p.envelope_shape_match for p in self._pairs)
        all_governance_match = all(p.governance_match for p in self._pairs)
        journals_indistinguishable = all(p.journal_match for p in self._pairs)

        per_mutation: dict[str, dict[str, Any]] = {}
        for pair in self._pairs:
            score = self.score_pair(pair)
            per_mutation[pair.mutation_type] = {
                "pair_id": pair.pair_id,
                "score": score.score,
                "checks_passed": score.checks_passed,
                "spine_bypass": score.spine_bypass,
                "failed_checks": score.failed_checks,
            }

        passes = (
            composite >= 0.9
            and not any_bypass
            and all_envelope_match
            and all_governance_match
            and journals_indistinguishable
            and len(covered) >= len(CORE_MUTATIONS)
        )

        return {
            "count": n,
            "composite": composite,
            "pass": passes,
            "any_spine_bypass": any_bypass,
            "all_envelope_match": all_envelope_match,
            "all_governance_match": all_governance_match,
            "journals_indistinguishable": journals_indistinguishable,
            "coverage": len(covered),
            "required_mutations": len(CORE_MUTATIONS),
            "uncovered_mutations": uncovered,
            "per_mutation": per_mutation,
            "scores": [s.to_dict() for s in scores],
        }

    def structural_audit(self) -> dict[str, Any]:
        """Audit the codebase for spine bypass indicators.

        Classifies route files as MUTATION, QUERY, or ADMIN.
        Only flags MUTATION routes that bypass the spine.
        """
        import re

        routes_dir = os.path.join(_REPO_ROOT, "transports", "api")
        if not os.path.isdir(routes_dir):
            return {"error": "transports/api not found", "bypasses": []}

        mutation_indicators = re.compile(
            r"def\s+(?:create|update|delete|approve|reject|launch|"
            r"dispatch|submit|save|persist|write|send|execute|"
            r"mark|attach|register|assign|complete|resolve|claim)",
            re.IGNORECASE,
        )

        bypasses: list[dict[str, str]] = []
        spine_imports: list[str] = []
        mutation_files: list[str] = []
        query_files: list[str] = []
        admin_files: list[str] = []
        total_routes = 0

        for fname in sorted(os.listdir(routes_dir)):
            if not fname.endswith(".py") or fname.startswith("__"):
                continue
            fpath = os.path.join(routes_dir, fname)
            try:
                with open(fpath) as f:
                    content = f.read()
            except OSError:
                continue

            has_spine = any(kw in content for kw in (
                "governed_spine", "GovernedExecutionSpine",
                "approval_gate", "governed_execution",
                "spine_router", "organism_bridge",
            ))
            has_envelope = "ActionEnvelope" in content or "action_envelope" in content
            has_post_put = bool(re.search(r'@router\.(post|put|delete|patch)', content, re.IGNORECASE))
            has_mutation_fn = bool(mutation_indicators.search(content))
            is_admin = "health" in fname or "metrics" in fname or "debug" in fname

            if is_admin:
                admin_files.append(fname)
                continue

            is_mutation = has_post_put and has_mutation_fn

            if is_mutation:
                total_routes += 1
                mutation_files.append(fname)
                if has_spine or has_envelope:
                    spine_imports.append(fname)
                else:
                    bypasses.append({
                        "file": fname,
                        "reason": "mutation route without spine/envelope import",
                    })
            elif has_post_put:
                total_routes += 1
                query_files.append(fname)
            else:
                query_files.append(fname)

        return {
            "total_route_files": len(mutation_files) + len(query_files) + len(admin_files),
            "mutation_route_files": len(mutation_files),
            "query_route_files": len(query_files),
            "admin_route_files": len(admin_files),
            "spine_connected": len(spine_imports),
            "potential_bypasses": len(bypasses),
            "bypasses": bypasses,
            "spine_files": spine_imports,
            "mutation_files": mutation_files,
        }

    def summary(self) -> dict[str, Any]:
        result = self.score_all()
        result.pop("scores", None)
        result.pop("per_mutation", None)
        audit = self.structural_audit()
        result["structural_audit"] = {
            "total_routes": audit["total_route_files"],
            "mutation_routes": audit["mutation_route_files"],
            "query_routes": audit["query_route_files"],
            "spine_connected": audit["spine_connected"],
            "potential_bypasses": audit["potential_bypasses"],
        }
        return result
