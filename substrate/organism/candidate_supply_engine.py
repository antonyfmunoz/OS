"""Candidate Supply Engine — discovers improvement candidates from real organism sources.

Scans ContradictionEngine, WorldModel, DependencyGraph, ReadinessModel,
BottleneckEngine, and template audit gaps. Each candidate gets evidence,
template matching, governance scoring, and a policy decision.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from substrate.organism.template_governance import (
    GovernanceDecision,
    TemplateGovernance,
)
from substrate.organism.template_registry import (
    TemplateCandidate,
    TemplateRegistry,
)

logger = logging.getLogger(__name__)
_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


@dataclass
class SupplyCandidate:
    candidate_id: str = field(default_factory=lambda: f"cse-{uuid4().hex[:8]}")
    source: str = ""
    title: str = ""
    description: str = ""
    evidence: list[dict[str, Any]] = field(default_factory=list)
    affected_files: list[str] = field(default_factory=list)
    risk_class: str = "low"
    matching_templates: list[str] = field(default_factory=list)
    policy_decision: str = "pending"
    blocked_reasons: list[str] = field(default_factory=list)
    expected_delta: str = ""
    recommended_next_step: str = ""
    template_confidence: float = 0.0
    agent_reliability: float = 0.0
    validation_method: str = ""
    rollback_method: str = ""
    non_mutating: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source": self.source,
            "title": self.title,
            "description": self.description,
            "evidence": self.evidence,
            "affected_files": self.affected_files,
            "risk_class": self.risk_class,
            "matching_templates": self.matching_templates,
            "policy_decision": self.policy_decision,
            "blocked_reasons": self.blocked_reasons,
            "expected_delta": self.expected_delta,
            "recommended_next_step": self.recommended_next_step,
            "template_confidence": round(self.template_confidence, 3),
            "agent_reliability": round(self.agent_reliability, 3),
            "validation_method": self.validation_method,
            "rollback_method": self.rollback_method,
            "non_mutating": self.non_mutating,
            "created_at": self.created_at,
        }

    def to_cadence_dict(self) -> dict[str, Any]:
        """Format for AutonomousCadence._filter_candidates() compatibility."""
        return {
            "candidate_id": self.candidate_id,
            "source": self.source,
            "title": self.title,
            "description": self.description,
            "evidence": self.evidence,
            "risk_class": self.risk_class,
            "template_id": self.matching_templates[0] if self.matching_templates else "",
            "template_confidence": self.template_confidence,
            "agent_reliability": self.agent_reliability,
            "validation_method": self.validation_method,
            "rollback_method": self.rollback_method,
            "non_mutating": self.non_mutating,
            "policy_decision": self.policy_decision,
            "blocked_reasons": self.blocked_reasons,
            "affected_files": self.affected_files,
            "expected_delta": self.expected_delta,
            "recommended_next_step": self.recommended_next_step,
        }


@dataclass
class SupplyResult:
    candidates: list[SupplyCandidate] = field(default_factory=list)
    source_scan_proof: dict[str, Any] = field(default_factory=dict)
    scan_duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_count": len(self.candidates),
            "candidates": [c.to_dict() for c in self.candidates],
            "source_scan_proof": self.source_scan_proof,
            "scan_duration_seconds": round(self.scan_duration_seconds, 3),
        }


class CandidateSupplyEngine:
    """Discovers candidates from real organism sources, matches templates, applies governance."""

    def __init__(
        self,
        template_registry: TemplateRegistry | None = None,
        governance: TemplateGovernance | None = None,
        state_dir: str | None = None,
    ) -> None:
        template_store = state_dir or os.path.join(_REPO_ROOT, "data", "umh", "organism", "templates")
        self._registry = template_registry or TemplateRegistry(store_dir=template_store)
        self._governance = governance or TemplateGovernance()
        self._state_dir = state_dir or os.path.join(_REPO_ROOT, "data", "umh", "organism")
        self._sources: dict[str, bool] = {}

    def discover(self) -> SupplyResult:
        start = time.time()
        all_candidates: list[SupplyCandidate] = []
        scan_proof: dict[str, Any] = {}

        source_methods = [
            ("contradiction_engine", self._scan_contradictions),
            ("world_model", self._scan_world_model),
            ("dependency_graph", self._scan_dependency_graph),
            ("readiness_model", self._scan_readiness),
            ("bottleneck_engine", self._scan_bottlenecks),
            ("template_audit_gaps", self._scan_template_audit_gaps),
        ]

        for source_name, scan_fn in source_methods:
            try:
                candidates = scan_fn()
                scan_proof[source_name] = {
                    "scanned": True,
                    "candidates_found": len(candidates),
                    "error": None,
                }
                all_candidates.extend(candidates)
                self._sources[source_name] = True
            except Exception as e:
                scan_proof[source_name] = {
                    "scanned": False,
                    "candidates_found": 0,
                    "error": str(e),
                }
                self._sources[source_name] = False
                logger.warning("Source %s scan failed: %s", source_name, e)

        for c in all_candidates:
            self._match_template(c)
            self._apply_governance(c)

        all_candidates.sort(
            key=lambda c: (c.template_confidence, c.agent_reliability),
            reverse=True,
        )

        for c in all_candidates:
            if c.blocked_reasons:
                c.policy_decision = "blocked"

        duration = time.time() - start
        return SupplyResult(
            candidates=all_candidates,
            source_scan_proof=scan_proof,
            scan_duration_seconds=duration,
        )

    def discover_for_cadence(self) -> list[dict[str, Any]]:
        """Callback-compatible method for AutonomousCadence._candidate_discovery_fn."""
        result = self.discover()
        return [c.to_cadence_dict() for c in result.candidates]

    def _match_template(self, candidate: SupplyCandidate) -> None:
        action_type = self._infer_action_type(candidate)
        matches = self._registry.find_matching(action_type, candidate.description)
        if matches:
            best = matches[0]
            candidate.matching_templates = [m.template_id for m in matches[:3]]
            candidate.template_confidence = best.confidence
            if best.agent_capability_binding:
                candidate.agent_reliability = best.agent_capability_binding.confidence
            if best.validation:
                candidate.validation_method = best.validation.method
            if best.rollback:
                candidate.rollback_method = best.rollback.method
                desc = best.rollback.description.lower()
                if "non-destructive" in desc or "no rollback required" in desc:
                    candidate.non_mutating = True

    def _apply_governance(self, candidate: SupplyCandidate) -> None:
        if not candidate.matching_templates:
            candidate.policy_decision = "no_template_match"
            candidate.blocked_reasons.append("no_matching_template")
            return

        template = self._registry.get_template(candidate.matching_templates[0])
        if not template:
            candidate.policy_decision = "template_not_found"
            candidate.blocked_reasons.append("template_not_found")
            return

        score = self._governance.evaluate(template)
        candidate.policy_decision = score.decision.value
        if score.decision == GovernanceDecision.BLOCKED:
            candidate.blocked_reasons.extend(score.reason_codes)

    def _infer_action_type(self, candidate: SupplyCandidate) -> str:
        source_to_action = {
            "contradiction_engine": "run_contradiction_engine",
            "world_model": "assess_state",
            "dependency_graph": "execute_maintenance",
            "readiness_model": "check_readiness",
            "bottleneck_engine": "run_probes",
            "template_audit_gaps": "identify_panel",
        }
        return source_to_action.get(candidate.source, "assess_state")

    def _scan_contradictions(self) -> list[SupplyCandidate]:
        candidates: list[SupplyCandidate] = []
        try:
            from substrate.organism.contradiction_engine import ContradictionEngine
            engine = ContradictionEngine(state_dir=self._state_dir)
            report = engine.scan()
            for c in report.contradictions:
                if c.severity.value in ("medium", "high"):
                    candidates.append(SupplyCandidate(
                        source="contradiction_engine",
                        title=f"Contradiction: {c.entity_id}",
                        description=c.description,
                        evidence=[{
                            "source": "contradiction_engine",
                            "detail": f"severity={c.severity.value}, type={c.contradiction_type.value}, entity={c.entity_id}",
                            "confidence": 0.8,
                        }],
                        affected_files=[c.entity_id] if c.entity_id else [],
                        risk_class="low",
                        expected_delta=f"Resolve {c.severity.value} contradiction for {c.entity_id}",
                        recommended_next_step="Run contradiction fix template",
                    ))
        except Exception as e:
            logger.debug("ContradictionEngine scan: %s", e)
        return candidates

    def _scan_world_model(self) -> list[SupplyCandidate]:
        candidates: list[SupplyCandidate] = []
        try:
            from substrate.organism.world_model import WorldModel
            wm = WorldModel(state_dir=self._state_dir)
            entities = wm.list_entities() if hasattr(wm, "list_entities") else []
            for entity in entities[:50]:
                if isinstance(entity, dict):
                    entity_id = entity.get("entity_id", "")
                    path = entity.get("declared_path", entity.get("path", ""))
                    last_obs = entity.get("last_observed", 0)
                    age_hours = (time.time() - last_obs) / 3600 if last_obs else 999
                    if path and not os.path.exists(os.path.join(_REPO_ROOT, path)):
                        candidates.append(SupplyCandidate(
                            source="world_model",
                            title=f"Missing path: {path}",
                            description=f"World model declares {entity_id} at path {path} but file does not exist",
                            evidence=[{
                                "source": "world_model",
                                "detail": f"entity_id={entity_id}, declared_path={path}, path_exists=false",
                                "confidence": 0.9,
                            }],
                            affected_files=[path],
                            risk_class="low",
                            expected_delta=f"Create missing path or correct declaration for {entity_id}",
                            recommended_next_step="Run observation accuracy fix template",
                        ))
                    elif age_hours > 24:
                        candidates.append(SupplyCandidate(
                            source="world_model",
                            title=f"Stale entity: {entity_id}",
                            description=f"World model entity {entity_id} last observed {age_hours:.0f}h ago",
                            evidence=[{
                                "source": "world_model",
                                "detail": f"entity_id={entity_id}, last_observed={last_obs}, age_hours={age_hours:.0f}",
                                "confidence": 0.7,
                            }],
                            affected_files=[path] if path else [],
                            risk_class="low",
                            non_mutating=True,
                            expected_delta=f"Refresh world model observation for {entity_id}",
                            recommended_next_step="Run world model accuracy fix template",
                        ))
        except Exception as e:
            logger.debug("WorldModel scan: %s", e)
        return candidates

    def _scan_dependency_graph(self) -> list[SupplyCandidate]:
        candidates: list[SupplyCandidate] = []
        try:
            from substrate.organism.dependency_graph import DependencyGraph
            dg = DependencyGraph(state_dir=self._state_dir)
            if hasattr(dg, "staleness_check"):
                staleness = dg.staleness_check()
                if isinstance(staleness, dict) and staleness.get("stale"):
                    candidates.append(SupplyCandidate(
                        source="dependency_graph",
                        title="Dependency graph stale",
                        description=f"Graph last built {staleness.get('age_hours', '?')}h ago",
                        evidence=[{
                            "source": "dependency_graph",
                            "detail": f"stale={staleness.get('stale')}, age_hours={staleness.get('age_hours', '?')}",
                            "confidence": 0.8,
                        }],
                        risk_class="low",
                        non_mutating=True,
                        expected_delta="Rebuild dependency graph to include recent files",
                        recommended_next_step="Run dependency graph fix template",
                    ))
            if hasattr(dg, "find_missing_edges"):
                missing = dg.find_missing_edges()
                if isinstance(missing, list):
                    for edge in missing[:5]:
                        candidates.append(SupplyCandidate(
                            source="dependency_graph",
                            title=f"Missing edge: {edge.get('from', '?')} -> {edge.get('to', '?')}",
                            description=f"Dependency graph missing edge from {edge.get('from', '?')} to {edge.get('to', '?')}",
                            evidence=[{
                                "source": "dependency_graph",
                                "detail": str(edge),
                                "confidence": 0.7,
                            }],
                            risk_class="low",
                            expected_delta="Add missing dependency edge",
                            recommended_next_step="Run dependency graph fix template",
                        ))
        except Exception as e:
            logger.debug("DependencyGraph scan: %s", e)
        return candidates

    def _scan_readiness(self) -> list[SupplyCandidate]:
        candidates: list[SupplyCandidate] = []
        try:
            from substrate.organism.readiness_model import ReadinessModel
            rm = ReadinessModel(state_dir=self._state_dir)
            snapshot = rm.snapshot() if hasattr(rm, "snapshot") else {}
            dimensions = snapshot.get("dimensions", {}) if isinstance(snapshot, dict) else {}
            for dim_name, dim_data in dimensions.items():
                if isinstance(dim_data, dict):
                    score = dim_data.get("score", 1.0)
                    if score < 0.70:
                        candidates.append(SupplyCandidate(
                            source="readiness_model",
                            title=f"Low readiness: {dim_name} ({score:.2f})",
                            description=f"Readiness dimension {dim_name} is at {score:.2f}, below 0.70 threshold",
                            evidence=[{
                                "source": "readiness_model",
                                "detail": f"dimension={dim_name}, score={score:.2f}, threshold=0.70",
                                "confidence": 0.85,
                            }],
                            risk_class="low",
                            expected_delta=f"Improve {dim_name} readiness score to >= 0.70",
                            recommended_next_step="Run readiness improvement template",
                        ))
        except Exception as e:
            logger.debug("ReadinessModel scan: %s", e)
        return candidates

    def _scan_bottlenecks(self) -> list[SupplyCandidate]:
        candidates: list[SupplyCandidate] = []
        try:
            from substrate.organism.bottleneck_engine import BottleneckEngine
            be = BottleneckEngine(state_dir=self._state_dir)
            report = be.analyze() if hasattr(be, "analyze") else None
            if report and hasattr(report, "bottlenecks"):
                for b in report.bottlenecks[:5]:
                    if isinstance(b, dict):
                        severity = b.get("severity", "low")
                        if severity in ("medium", "high"):
                            candidates.append(SupplyCandidate(
                                source="bottleneck_engine",
                                title=f"Bottleneck: {b.get('component', '?')}",
                                description=b.get("description", ""),
                                evidence=[{
                                    "source": "bottleneck_engine",
                                    "detail": str(b),
                                    "confidence": 0.75,
                                }],
                                risk_class="low",
                                expected_delta=f"Resolve bottleneck in {b.get('component', '?')}",
                                recommended_next_step="Run maintenance action template",
                            ))
        except Exception as e:
            logger.debug("BottleneckEngine scan: %s", e)
        return candidates

    def _scan_template_audit_gaps(self) -> list[SupplyCandidate]:
        candidates: list[SupplyCandidate] = []
        audit_path = os.path.join(_REPO_ROOT, "data", "umh", "templates", "phase10_0_template_audit.json")
        if not os.path.isfile(audit_path):
            return candidates
        try:
            import json
            with open(audit_path) as f:
                audit = json.load(f)
            gaps = audit.get("candidate_discovery_gaps", audit.get("discovery_gaps", []))
            for gap in gaps:
                if isinstance(gap, dict):
                    gap_title = gap.get("title", gap.get("gap", ""))
                    gap_desc = gap.get("description", gap.get("impact", ""))
                    gap_severity = gap.get("severity", "medium")
                    if gap_severity in ("critical", "high"):
                        candidates.append(SupplyCandidate(
                            source="template_audit_gaps",
                            title=f"Audit gap: {gap_title}",
                            description=f"Template audit identified gap: {gap_title}. {gap_desc}",
                            evidence=[{
                                "source": "template_audit",
                                "detail": f"gap_id={gap.get('gap_id', '?')}, severity={gap_severity}, title={gap_title}",
                                "confidence": 0.7,
                            }],
                            risk_class="low",
                            expected_delta=f"Close audit gap: {gap_title}",
                            recommended_next_step=gap.get("fix_in_phase", "Review template audit"),
                        ))
        except Exception as e:
            logger.debug("Template audit gap scan: %s", e)
        return candidates

    def summary(self) -> dict[str, Any]:
        return {
            "sources_scanned": self._sources,
            "sources_active": sum(1 for v in self._sources.values() if v),
            "sources_failed": sum(1 for v in self._sources.values() if not v),
        }
