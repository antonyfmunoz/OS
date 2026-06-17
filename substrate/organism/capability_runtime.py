"""Capability Runtime — emergent capability tracking and maturity lifecycle.

Answers operator question #10: "What capability emerged?"

An EmergentCapability is what the ORGANIZATION has learned to do — distinct
from the job-level Capability enum (CODE_WRITE, WEB_SEARCH) which describes
executor abilities. EmergentCapability tracks organizational learning:
pattern detected → validated → operationalized → institutional.

Composes with (never duplicates):
  - IntentRuntime — lineage from intent to capability
  - OutcomeLearningLoop — pattern detection from outcomes
  - AgentCapabilityModel — reliability data for maturity scoring
  - StrategicGapEngine.GoalRegistry — required_capabilities linkage

Gate 5 — Capability Runtime. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_CAPABILITY_DIR = os.path.join(_REPO_ROOT, "data", "umh", "capabilities")
_CAPABILITIES_PATH = os.path.join(_CAPABILITY_DIR, "capabilities.jsonl")
_EVIDENCE_PATH = os.path.join(_CAPABILITY_DIR, "evidence.jsonl")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class CapabilityMaturity(str, Enum):
    EMERGING = "emerging"
    VALIDATED = "validated"
    OPERATIONAL = "operational"
    INSTITUTIONAL = "institutional"


_MATURITY_ORDER: dict[CapabilityMaturity, int] = {
    CapabilityMaturity.EMERGING: 0,
    CapabilityMaturity.VALIDATED: 1,
    CapabilityMaturity.OPERATIONAL: 2,
    CapabilityMaturity.INSTITUTIONAL: 3,
}


class CapabilityEvidenceType(str, Enum):
    EXECUTION_OUTCOME = "execution_outcome"
    TEMPLATE_MATCH = "template_match"
    MANUAL_ATTESTATION = "manual_attestation"
    RELIABILITY_DATA = "reliability_data"
    GOAL_ALIGNMENT = "goal_alignment"


@dataclass
class CapabilityEvidence:
    evidence_id: str = field(default_factory=lambda: f"cev-{uuid4().hex[:8]}")
    capability_id: str = ""
    evidence_type: CapabilityEvidenceType = CapabilityEvidenceType.MANUAL_ATTESTATION
    source_id: str = ""
    description: str = ""
    quality_score: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["evidence_type"] = self.evidence_type.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CapabilityEvidence:
        d = dict(d)
        et = d.get("evidence_type", "manual_attestation")
        try:
            d["evidence_type"] = CapabilityEvidenceType(et)
        except ValueError:
            d["evidence_type"] = CapabilityEvidenceType.MANUAL_ATTESTATION
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class EmergentCapability:
    capability_id: str = field(default_factory=lambda: f"ecap-{uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    origin_intent_id: str = ""
    understanding_sources: list[str] = field(default_factory=list)
    maturity: CapabilityMaturity = CapabilityMaturity.EMERGING
    evidence_ids: list[str] = field(default_factory=list)
    operationalization_ids: list[str] = field(default_factory=list)
    projections_using: list[str] = field(default_factory=list)
    owner: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["maturity"] = self.maturity.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EmergentCapability:
        d = dict(d)
        mat = d.get("maturity", "emerging")
        try:
            d["maturity"] = CapabilityMaturity(mat)
        except ValueError:
            d["maturity"] = CapabilityMaturity.EMERGING
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Maturity scoring — deterministic, no LLM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_MATURITY_THRESHOLDS = {
    CapabilityMaturity.INSTITUTIONAL: 0.85,
    CapabilityMaturity.OPERATIONAL: 0.60,
    CapabilityMaturity.VALIDATED: 0.30,
}


def compute_maturity_score(evidence: list[CapabilityEvidence]) -> float:
    """Deterministic maturity score from evidence quality, type, and count.

    Score = mean(quality * type_weight) * coverage_factor
    coverage_factor = min(1.0, len(evidence) / 5)

    Higher-value evidence types (execution outcomes, reliability data)
    produce higher scores than manual attestations at the same quality.
    """
    if not evidence:
        return 0.0
    type_weights: dict[CapabilityEvidenceType, float] = {
        CapabilityEvidenceType.EXECUTION_OUTCOME: 1.0,
        CapabilityEvidenceType.RELIABILITY_DATA: 0.9,
        CapabilityEvidenceType.TEMPLATE_MATCH: 0.8,
        CapabilityEvidenceType.GOAL_ALIGNMENT: 0.7,
        CapabilityEvidenceType.MANUAL_ATTESTATION: 0.5,
    }
    composite_sum = 0.0
    for ev in evidence:
        w = type_weights.get(ev.evidence_type, 0.5)
        composite_sum += ev.quality_score * w
    mean_composite = composite_sum / len(evidence)
    coverage = min(1.0, len(evidence) / 5.0)
    return round(mean_composite * coverage, 4)


def maturity_from_score(score: float) -> CapabilityMaturity:
    for maturity, threshold in _MATURITY_THRESHOLDS.items():
        if score >= threshold:
            return maturity
    return CapabilityMaturity.EMERGING


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pattern detection — deterministic from outcomes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def detect_capability_patterns(
    outcomes: list[dict[str, Any]],
    min_occurrences: int = 3,
    min_success_rate: float = 0.6,
) -> list[dict[str, Any]]:
    """Detect repeating successful action patterns from outcome records.

    Groups outcomes by action_type, filters by minimum occurrences and
    success rate. Returns proposed capability descriptions.
    """
    from substrate.organism.outcome_learning import OutcomeStatus

    by_action: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for o in outcomes:
        at = o.get("action_type", "")
        if at:
            by_action[at].append(o)

    proposals: list[dict[str, Any]] = []
    for action_type, records in by_action.items():
        if len(records) < min_occurrences:
            continue
        successes = sum(
            1 for r in records if r.get("status") in (OutcomeStatus.SUCCESS.value, "success")
        )
        rate = successes / len(records)
        if rate < min_success_rate:
            continue
        proposals.append(
            {
                "proposed_name": action_type.replace("_", " ").title(),
                "action_type": action_type,
                "occurrences": len(records),
                "success_rate": round(rate, 3),
                "sample_descriptions": [
                    r.get("description", "") for r in records[:3] if r.get("description")
                ],
            }
        )

    proposals.sort(key=lambda p: (-p["occurrences"], -p["success_rate"]))
    return proposals


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Runtime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class CapabilityRuntime:
    """Registry and lifecycle manager for emergent capabilities."""

    def __init__(
        self,
        capabilities_path: str = _CAPABILITIES_PATH,
        evidence_path: str = _EVIDENCE_PATH,
    ) -> None:
        self._cap_path = capabilities_path
        self._ev_path = evidence_path
        self._lock = threading.Lock()
        self._capabilities: dict[str, EmergentCapability] = {}
        self._evidence: dict[str, CapabilityEvidence] = {}
        self._load()

    # ── Persistence ────────────────────────────────────────────────

    def _load(self) -> None:
        self._capabilities = self._load_jsonl(
            self._cap_path, EmergentCapability.from_dict, "capability_id"
        )
        self._evidence = self._load_jsonl(
            self._ev_path, CapabilityEvidence.from_dict, "evidence_id"
        )

    @staticmethod
    def _load_jsonl(path: str, from_dict_fn: Any, key_field: str) -> dict:
        result: dict = {}
        if not os.path.exists(path):
            return result
        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        obj = from_dict_fn(d)
                        result[getattr(obj, key_field)] = obj
                    except (json.JSONDecodeError, TypeError, KeyError) as e:
                        logger.debug("Skip malformed JSONL line: %s", e)
        except OSError as e:
            logger.debug("Cannot read %s: %s", path, e)
        return result

    def _append_jsonl(self, path: str, data: dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(data, default=str) + "\n")

    def _rewrite_capabilities(self) -> None:
        os.makedirs(os.path.dirname(self._cap_path), exist_ok=True)
        with open(self._cap_path, "w") as f:
            for cap in self._capabilities.values():
                f.write(json.dumps(cap.to_dict(), default=str) + "\n")

    # ── Registry ───────────────────────────────────────────────────

    def register(
        self,
        name: str,
        description: str,
        origin_intent_id: str = "",
        understanding_sources: list[str] | None = None,
        owner: str = "",
        tags: list[str] | None = None,
    ) -> EmergentCapability:
        cap = EmergentCapability(
            name=name,
            description=description,
            origin_intent_id=origin_intent_id,
            understanding_sources=understanding_sources or [],
            owner=owner,
            tags=tags or [],
        )
        with self._lock:
            self._capabilities[cap.capability_id] = cap
            self._append_jsonl(self._cap_path, cap.to_dict())
        logger.info("Registered capability: %s (%s)", cap.name, cap.capability_id)
        return cap

    def get(self, capability_id: str) -> EmergentCapability | None:
        return self._capabilities.get(capability_id)

    def list_capabilities(
        self,
        maturity: CapabilityMaturity | None = None,
        tag: str | None = None,
    ) -> list[EmergentCapability]:
        result = list(self._capabilities.values())
        if maturity is not None:
            result = [c for c in result if c.maturity == maturity]
        if tag is not None:
            result = [c for c in result if tag in c.tags]
        result.sort(key=lambda c: c.created_at, reverse=True)
        return result

    # ── Evidence ───────────────────────────────────────────────────

    def add_evidence(
        self,
        capability_id: str,
        evidence_type: CapabilityEvidenceType,
        source_id: str = "",
        description: str = "",
        quality_score: float = 0.5,
    ) -> CapabilityEvidence | None:
        cap = self._capabilities.get(capability_id)
        if cap is None:
            logger.warning("add_evidence: capability %s not found", capability_id)
            return None

        ev = CapabilityEvidence(
            capability_id=capability_id,
            evidence_type=evidence_type,
            source_id=source_id,
            description=description,
            quality_score=max(0.0, min(1.0, quality_score)),
        )
        with self._lock:
            self._evidence[ev.evidence_id] = ev
            cap.evidence_ids.append(ev.evidence_id)
            cap.updated_at = time.time()
            self._append_jsonl(self._ev_path, ev.to_dict())

            old_maturity = cap.maturity
            new_score = self.maturity_score(capability_id)
            new_maturity = maturity_from_score(new_score)
            if _MATURITY_ORDER.get(new_maturity, 0) > _MATURITY_ORDER.get(old_maturity, 0):
                cap.maturity = new_maturity
                logger.info(
                    "Capability %s maturity: %s → %s (score=%.3f)",
                    cap.name,
                    old_maturity.value,
                    new_maturity.value,
                    new_score,
                )
            self._rewrite_capabilities()
        return ev

    def evidence_for(self, capability_id: str) -> list[CapabilityEvidence]:
        return [ev for ev in self._evidence.values() if ev.capability_id == capability_id]

    def maturity_score(self, capability_id: str) -> float:
        evidence = self.evidence_for(capability_id)
        return compute_maturity_score(evidence)

    # ── Lineage ────────────────────────────────────────────────────

    def lineage(self, capability_id: str) -> dict[str, Any]:
        """Trace capability back to its origin intent and evidence chain."""
        cap = self._capabilities.get(capability_id)
        if cap is None:
            return {"error": f"capability {capability_id} not found"}

        evidence = self.evidence_for(capability_id)
        return {
            "capability_id": cap.capability_id,
            "name": cap.name,
            "maturity": cap.maturity.value,
            "origin_intent_id": cap.origin_intent_id,
            "understanding_sources": cap.understanding_sources,
            "evidence_count": len(evidence),
            "evidence_types": dict(Counter(ev.evidence_type.value for ev in evidence)),
            "evidence_quality_mean": (
                round(sum(e.quality_score for e in evidence) / len(evidence), 3)
                if evidence
                else 0.0
            ),
            "maturity_score": self.maturity_score(capability_id),
            "operationalization_ids": cap.operationalization_ids,
            "projections_using": cap.projections_using,
        }

    def capabilities_from_intent(self, intent_id: str) -> list[EmergentCapability]:
        return [c for c in self._capabilities.values() if c.origin_intent_id == intent_id]

    # ── Discovery ──────────────────────────────────────────────────

    def propose_from_patterns(
        self,
        outcomes: list[dict[str, Any]],
        min_occurrences: int = 3,
        min_success_rate: float = 0.6,
    ) -> list[dict[str, Any]]:
        """Deterministic pattern detection from outcome records.

        Returns proposals — not registered capabilities. Operator must
        approve and register explicitly.
        """
        existing_names = {c.name.lower() for c in self._capabilities.values()}
        proposals = detect_capability_patterns(
            outcomes,
            min_occurrences=min_occurrences,
            min_success_rate=min_success_rate,
        )
        return [p for p in proposals if p["proposed_name"].lower() not in existing_names]

    # ── Health / Summary ───────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        by_maturity = self.capabilities_by_maturity()
        total = len(self._capabilities)
        return {
            "total_capabilities": total,
            "total_evidence": len(self._evidence),
            "by_maturity": {k: len(v) for k, v in by_maturity.items()},
            "tags": dict(Counter(tag for c in self._capabilities.values() for tag in c.tags)),
        }

    def capabilities_by_maturity(self) -> dict[str, list[EmergentCapability]]:
        result: dict[str, list[EmergentCapability]] = {m.value: [] for m in CapabilityMaturity}
        for cap in self._capabilities.values():
            result[cap.maturity.value].append(cap)
        return result

    # ── Linking (for Gate 6 composition) ───────────────────────────

    def link_operationalization(
        self,
        capability_id: str,
        operationalization_id: str,
    ) -> bool:
        cap = self._capabilities.get(capability_id)
        if cap is None:
            return False
        with self._lock:
            if operationalization_id not in cap.operationalization_ids:
                cap.operationalization_ids.append(operationalization_id)
                cap.updated_at = time.time()
                self._rewrite_capabilities()
        return True

    def link_projection(
        self,
        capability_id: str,
        projection_name: str,
    ) -> bool:
        cap = self._capabilities.get(capability_id)
        if cap is None:
            return False
        with self._lock:
            if projection_name not in cap.projections_using:
                cap.projections_using.append(projection_name)
                cap.updated_at = time.time()
                self._rewrite_capabilities()
        return True
