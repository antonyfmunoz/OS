"""Completeness Engine — 13-slot validation for plans, workflows, and compositions.

No plan, workflow, or composition is complete until every slot is filled.
This is a structural guarantee: the system cannot ship half-built work.

The 13 slots map to the minimum viable requirements for any executable unit:

 1. Input           — what enters the system (signal, data, trigger)
 2. Processing      — what transforms the input (logic, computation)
 3. Output          — what leaves the system (result, side effect)
 4. Feedback        — how the system learns from outcomes
 5. Constraints     — what limits apply (time, cost, risk, scope)
 6. Failure         — what happens when something goes wrong
 7. Optimization    — how the system improves over iterations
 8. Governance      — what approvals / checks are required
 9. Environment     — where execution happens (native, container, etc.)
10. Observability   — what is traced, logged, measured
11. Memory          — how outcomes feed back into the knowledge base
12. Quality         — what benchmark defines "good enough"
13. Proof           — what evidence proves the work was done correctly
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SlotStatus(str, Enum):
    FILLED = "filled"
    EMPTY = "empty"
    PARTIAL = "partial"


class CompletenessSlot(str, Enum):
    INPUT = "input"
    PROCESSING = "processing"
    OUTPUT = "output"
    FEEDBACK = "feedback"
    CONSTRAINTS = "constraints"
    FAILURE = "failure"
    OPTIMIZATION = "optimization"
    GOVERNANCE = "governance"
    ENVIRONMENT = "environment"
    OBSERVABILITY = "observability"
    MEMORY = "memory"
    QUALITY = "quality"
    PROOF = "proof"


@dataclass
class SlotEvaluation:
    slot: CompletenessSlot
    status: SlotStatus
    description: str = ""
    evidence: str = ""


@dataclass
class CompletenessResult:
    """Result of a completeness check across all 13 slots."""

    target_name: str
    target_type: str
    slots: list[SlotEvaluation] = field(default_factory=list)
    score: float = 0.0
    complete: bool = False
    missing: list[str] = field(default_factory=list)
    partial: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_name": self.target_name,
            "target_type": self.target_type,
            "score": round(self.score, 3),
            "complete": self.complete,
            "missing": self.missing,
            "partial": self.partial,
            "slots": [
                {
                    "slot": s.slot.value,
                    "status": s.status.value,
                    "description": s.description,
                }
                for s in self.slots
            ],
        }


_SLOT_KEYWORDS: dict[CompletenessSlot, list[str]] = {
    CompletenessSlot.INPUT: [
        "input", "signal", "trigger", "source", "receives", "accepts",
        "ingests", "takes", "parameter", "argument", "request",
    ],
    CompletenessSlot.PROCESSING: [
        "process", "transform", "compute", "execute", "run",
        "convert", "parse", "analyze", "evaluate", "calculate",
    ],
    CompletenessSlot.OUTPUT: [
        "output", "result", "return", "response", "produce",
        "emit", "yield", "generate", "send", "write",
    ],
    CompletenessSlot.FEEDBACK: [
        "feedback", "learn", "adapt", "improve", "adjust",
        "calibrate", "tune", "correct", "refine",
    ],
    CompletenessSlot.CONSTRAINTS: [
        "constraint", "limit", "timeout", "budget", "max",
        "threshold", "boundary", "cap", "ceiling", "restriction",
    ],
    CompletenessSlot.FAILURE: [
        "fail", "error", "exception", "fallback", "retry",
        "recover", "degrade", "circuit", "timeout", "abort",
    ],
    CompletenessSlot.OPTIMIZATION: [
        "optimize", "improve", "iterate", "refine", "tune",
        "benchmark", "profile", "cache", "batch", "efficiency",
    ],
    CompletenessSlot.GOVERNANCE: [
        "governance", "approve", "policy", "permission", "authorize",
        "risk", "review", "gate", "verdict", "decision",
    ],
    CompletenessSlot.ENVIRONMENT: [
        "environment", "container", "native", "sandbox", "isolation",
        "docker", "vm", "wsl", "runtime", "platform",
    ],
    CompletenessSlot.OBSERVABILITY: [
        "trace", "log", "metric", "monitor", "observe",
        "measure", "instrument", "telemetry", "event", "audit",
    ],
    CompletenessSlot.MEMORY: [
        "memory", "store", "persist", "remember", "candidate",
        "promote", "canonical", "instance", "knowledge", "learn",
    ],
    CompletenessSlot.QUALITY: [
        "quality", "standard", "benchmark", "threshold", "test",
        "verify", "validate", "assert", "check", "criteria",
    ],
    CompletenessSlot.PROOF: [
        "proof", "evidence", "artifact", "hash", "signature",
        "receipt", "attestation", "verification", "certificate",
    ],
}


class CompletenessEngine:
    """Evaluates whether a plan, workflow, or composition fills all 13 slots.

    Two evaluation modes:
    - structural: checks a dict/spec for slot presence (fast, deterministic)
    - textual: scans natural language description for slot keywords (heuristic)
    """

    def evaluate_spec(
        self,
        spec: dict[str, Any],
        target_name: str = "unnamed",
        target_type: str = "plan",
    ) -> CompletenessResult:
        """Evaluate a structured spec dict. Keys map to slot names."""
        result = CompletenessResult(
            target_name=target_name,
            target_type=target_type,
        )

        for slot in CompletenessSlot:
            value = spec.get(slot.value)
            if value is None or value == "" or value == []:
                evaluation = SlotEvaluation(
                    slot=slot,
                    status=SlotStatus.EMPTY,
                    description=f"No {slot.value} defined",
                )
                result.missing.append(slot.value)
            elif isinstance(value, str) and len(value.strip()) < 10:
                evaluation = SlotEvaluation(
                    slot=slot,
                    status=SlotStatus.PARTIAL,
                    description=f"{slot.value} defined but minimal",
                    evidence=value[:100],
                )
                result.partial.append(slot.value)
            else:
                evidence = str(value)[:100] if not isinstance(value, str) else value[:100]
                evaluation = SlotEvaluation(
                    slot=slot,
                    status=SlotStatus.FILLED,
                    description=f"{slot.value} defined",
                    evidence=evidence,
                )
            result.slots.append(evaluation)

        filled = sum(1 for s in result.slots if s.status == SlotStatus.FILLED)
        partial = sum(1 for s in result.slots if s.status == SlotStatus.PARTIAL)
        result.score = (filled + partial * 0.5) / len(CompletenessSlot)
        result.complete = filled == len(CompletenessSlot)

        return result

    def evaluate_text(
        self,
        text: str,
        target_name: str = "unnamed",
        target_type: str = "plan",
    ) -> CompletenessResult:
        """Evaluate natural language text for slot coverage via keyword matching."""
        result = CompletenessResult(
            target_name=target_name,
            target_type=target_type,
        )

        text_lower = text.lower()

        for slot in CompletenessSlot:
            keywords = _SLOT_KEYWORDS[slot]
            matches = [kw for kw in keywords if kw in text_lower]
            match_ratio = len(matches) / len(keywords)

            if match_ratio >= 0.3:
                evaluation = SlotEvaluation(
                    slot=slot,
                    status=SlotStatus.FILLED,
                    description=f"{slot.value} covered ({len(matches)} keywords matched)",
                    evidence=", ".join(matches[:5]),
                )
            elif match_ratio > 0:
                evaluation = SlotEvaluation(
                    slot=slot,
                    status=SlotStatus.PARTIAL,
                    description=f"{slot.value} partially covered ({len(matches)} keywords)",
                    evidence=", ".join(matches),
                )
                result.partial.append(slot.value)
            else:
                evaluation = SlotEvaluation(
                    slot=slot,
                    status=SlotStatus.EMPTY,
                    description=f"No {slot.value} keywords found",
                )
                result.missing.append(slot.value)

            result.slots.append(evaluation)

        filled = sum(1 for s in result.slots if s.status == SlotStatus.FILLED)
        partial = sum(1 for s in result.slots if s.status == SlotStatus.PARTIAL)
        result.score = (filled + partial * 0.5) / len(CompletenessSlot)
        result.complete = filled == len(CompletenessSlot)

        return result

    def evaluate_pipeline_result(
        self,
        pipeline_result: dict[str, Any],
    ) -> CompletenessResult:
        """Evaluate a PipelineResult for slot coverage."""
        spec: dict[str, Any] = {}

        if pipeline_result.get("signal_id"):
            spec["input"] = f"signal:{pipeline_result['signal_id']}"
        if pipeline_result.get("executed"):
            spec["processing"] = "execution completed"
        if pipeline_result.get("outcome_type"):
            spec["output"] = pipeline_result["outcome_type"]
        if pipeline_result.get("memory_promoted"):
            spec["feedback"] = "memory promoted"
            spec["memory"] = "promoted to canonical"
        elif pipeline_result.get("memory_candidate_id"):
            spec["memory"] = f"candidate:{pipeline_result['memory_candidate_id']}"
        if pipeline_result.get("governance_approved") is not None:
            spec["governance"] = pipeline_result["governance_rationale"]
        if pipeline_result.get("proof_id"):
            spec["proof"] = f"proof:{pipeline_result['proof_id']}"
        if pipeline_result.get("trace_id"):
            spec["observability"] = f"trace:{pipeline_result['trace_id']}"
        if pipeline_result.get("mastery_assured") is not None:
            spec["quality"] = f"mastery_assured={pipeline_result['mastery_assured']}"
        if pipeline_result.get("understanding_confidence", 0) > 0:
            spec["constraints"] = f"confidence={pipeline_result['understanding_confidence']}"
        if pipeline_result.get("success") is False:
            spec["failure"] = "execution failed — recorded in trace"

        return self.evaluate_spec(
            spec,
            target_name="pipeline_execution",
            target_type="execution",
        )
