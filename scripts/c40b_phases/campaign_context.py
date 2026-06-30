"""C40B Campaign Context — shared state across all phases."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
import urllib.request
import urllib.error
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

import sys
_PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_PHASE_DIR))
sys.path.insert(0, "/opt/OS")
sys.path.insert(0, _REPO_ROOT)

from substrate.organism.daemon import OrganismDaemon
from substrate.organism.execution_journal import ExecutionJournal
from substrate.organism.mutation_registry import MutationRegistry
from substrate.organism.mutation_router import (
    MutationRequest,
    MutationResponse,
    MutationRouter,
)
from substrate.organism.outcome_learning import OutcomeLearningLoop
from substrate.organism.event_spine import EventSpine

logger = logging.getLogger("c40b")

_REPO_ROOT = Path(os.environ.get("UMH_ROOT", "/opt/OS"))
DATA_DIR = _REPO_ROOT / "data" / "umh" / "c40b"
EVIDENCE_DIR = DATA_DIR / "operator_traces"
MUTATION_LOG = DATA_DIR / "mutation_log.jsonl"
PHASE_LOG = DATA_DIR / "phase_results.jsonl"
COCKPIT_URL = "https://universalmetaharness.tech"
_MESH_HTTP_PORT = int(os.environ.get("UMH_MESH_HTTP_PORT", "8095"))

SUCCESS = "success"
GOVERNANCE_CONSTRAINT = "governance_constraint"
IMPLEMENTATION_DEFECT = "implementation_defect"
RUNTIME_INFRASTRUCTURE = "runtime_infrastructure"
MISSING_CAPABILITY = "missing_capability"
OPERATOR_LIMITATION = "operator_limitation"


@dataclass
class MutationResult:
    operation_id: str
    phase: int
    mutation_name: str
    action_type: str
    risk_level: str
    intent: str
    source: str
    envelope_id: str = ""
    status: str = ""
    success: bool = False
    awaiting_approval: bool = False
    rejected_reason: str = ""
    output: str = ""
    classification: str = ""
    error: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    journal_phases: list = field(default_factory=list)
    latency_ms: float = 0.0
    operator_trace: str = ""
    evidence_chain: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class PhaseResult:
    phase: int
    name: str
    total: int = 0
    successful: int = 0
    failed: int = 0
    elapsed_s: float = 0.0
    gate_passed: bool = False
    notes: str = ""
    slo_metrics: dict = field(default_factory=dict)


@dataclass
class DimensionVerdict:
    name: str
    status: str = "UNTESTED"
    evidence: str = ""
    details: dict = field(default_factory=dict)


@dataclass
class SLOTracker:
    mesh_attempts: int = 0
    mesh_successes: int = 0
    session_checks: int = 0
    session_available: int = 0
    dispatch_attempts: int = 0
    dispatch_successes: int = 0
    playwright_checks: int = 0
    playwright_available: int = 0
    chrome_starts: int = 0
    chrome_successes: int = 0
    recovery_attempts: int = 0
    recovery_within_30s: int = 0
    adapter_calls: int = 0
    adapter_failures: int = 0
    latencies_ms: list = field(default_factory=list)
    event_loss: int = 0
    proof_total: int = 0
    proof_complete: int = 0

    def mesh_reliability(self) -> float:
        return self.mesh_successes / max(self.mesh_attempts, 1)

    def session_availability(self) -> float:
        return self.session_available / max(self.session_checks, 1)

    def dispatch_success_rate(self) -> float:
        return self.dispatch_successes / max(self.dispatch_attempts, 1)

    def playwright_availability(self) -> float:
        return self.playwright_available / max(self.playwright_checks, 1)

    def chrome_startup_rate(self) -> float:
        return self.chrome_successes / max(self.chrome_starts, 1)

    def recovery_rate(self) -> float:
        return self.recovery_within_30s / max(self.recovery_attempts, 1)

    def adapter_failure_rate(self) -> float:
        return self.adapter_failures / max(self.adapter_calls, 1)

    def avg_latency_ms(self) -> float:
        return sum(self.latencies_ms) / max(len(self.latencies_ms), 1)

    def p95_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        s = sorted(self.latencies_ms)
        idx = int(len(s) * 0.95)
        return s[min(idx, len(s) - 1)]

    def proof_completeness(self) -> float:
        return self.proof_complete / max(self.proof_total, 1)

    def to_scorecard(self) -> dict:
        return {
            "mesh_reliability": round(self.mesh_reliability(), 4),
            "session_availability": round(self.session_availability(), 4),
            "dispatch_success_rate": round(self.dispatch_success_rate(), 4),
            "playwright_availability": round(self.playwright_availability(), 4),
            "chrome_startup_rate": round(self.chrome_startup_rate(), 4),
            "recovery_rate": round(self.recovery_rate(), 4),
            "adapter_failure_rate": round(self.adapter_failure_rate(), 4),
            "avg_latency_ms": round(self.avg_latency_ms(), 1),
            "p95_latency_ms": round(self.p95_latency_ms(), 1),
            "event_loss": self.event_loss,
            "proof_completeness": round(self.proof_completeness(), 4),
        }

    def all_slos_met(self) -> bool:
        return (
            self.mesh_reliability() >= 0.99
            and self.session_availability() >= 0.95
            and self.dispatch_success_rate() >= 0.95
            and self.playwright_availability() >= 0.95
            and self.chrome_startup_rate() >= 0.95
            and (self.recovery_attempts == 0 or self.recovery_rate() >= 0.80)
            and self.adapter_failure_rate() < 0.05
            and self.avg_latency_ms() < 1000
            and self.p95_latency_ms() < 3000
            and self.event_loss == 0
            and self.proof_completeness() >= 1.0
        )


class CampaignContext:
    def __init__(self, skip_browser: bool = False) -> None:
        self.skip_browser = skip_browser
        self.daemon = OrganismDaemon()
        self.router = MutationRouter(
            spine=self.daemon.governed_spine,
            registry=self.daemon.mutation_registry,
        )
        self.journal = self.daemon.execution_journal
        self.learning = self.daemon.outcome_learning
        self.event_spine = self.daemon.event_spine
        self.registry = self.daemon.mutation_registry
        self.results: list[MutationResult] = []
        self.phase_results: list[PhaseResult] = []
        self._event_log: list[dict] = []
        self.verdicts: dict[str, DimensionVerdict] = {
            "organism": DimensionVerdict(name="Organism"),
            "runtime": DimensionVerdict(name="Runtime"),
            "projection": DimensionVerdict(name="Projection"),
            "operator": DimensionVerdict(name="Operator"),
        }
        self.slo = SLOTracker()

        self.event_spine.subscribe(
            "c40b_monitor",
            lambda evt: self._event_log.append(
                {"domain": evt.domain, "type": evt.event_type, "ts": evt.timestamp}
            ),
        )

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    def submit(
        self,
        phase: int,
        mutation_name: str,
        intent: str,
        execute_fn: Callable[[], tuple],
        source: str = "c40b_campaign",
        verification_fn: Callable[[], bool] | None = None,
        rollback_fn: Callable[[], bool] | None = None,
        metadata: dict | None = None,
    ) -> MutationResult:
        op_id = uuid.uuid4().hex[:12]
        spec = self.registry.lookup(mutation_name)
        risk = spec.risk_level if spec else "unknown"
        atype = spec.action_type if spec else "unknown"

        result = MutationResult(
            operation_id=op_id,
            phase=phase,
            mutation_name=mutation_name,
            action_type=str(atype),
            risk_level=risk,
            intent=intent,
            source=source,
            started_at=time.time(),
        )

        try:
            request = MutationRequest(
                mutation_name=mutation_name,
                intent=intent,
                execute_fn=execute_fn,
                source=source,
                metadata=metadata or {"campaign": "c40b", "op_id": op_id},
                verification_fn=verification_fn,
                rollback_fn=rollback_fn,
            )
            resp = self.router.execute(request)
            result.envelope_id = resp.envelope_id
            result.status = resp.status
            result.success = resp.success
            result.awaiting_approval = resp.awaiting_approval
            result.rejected_reason = resp.rejected_reason
            result.output = resp.output[:500]

            if resp.envelope and resp.envelope.envelope_id:
                journal_entries = self.journal.entries_for(resp.envelope.envelope_id)
                result.journal_phases = [
                    e.phase if isinstance(e.phase, str) else e.phase.value
                    for e in journal_entries
                ]
        except Exception as exc:
            result.error = "%s: %s" % (type(exc).__name__, exc)
            result.status = "error"
            logger.error("mutation %s failed: %s", mutation_name, exc)

        result.completed_at = time.time()
        result.latency_ms = round((result.completed_at - result.started_at) * 1000, 1)
        self._classify(result)
        self.results.append(result)
        self._persist_mutation(result)
        return result

    def _classify(self, r: MutationResult) -> None:
        if r.error:
            r.classification = IMPLEMENTATION_DEFECT
        elif r.status == "rejected":
            r.classification = GOVERNANCE_CONSTRAINT
        elif r.success and r.status in ("completed", "verified"):
            r.classification = SUCCESS
        elif r.awaiting_approval:
            r.classification = GOVERNANCE_CONSTRAINT
        elif r.status in ("failed", "rolled_back"):
            r.classification = IMPLEMENTATION_DEFECT
        else:
            r.classification = IMPLEMENTATION_DEFECT

    def _persist_mutation(self, r: MutationResult) -> None:
        with open(MUTATION_LOG, "a") as f:
            d = {
                "operation_id": r.operation_id,
                "phase": r.phase,
                "mutation_name": r.mutation_name,
                "status": r.status,
                "success": r.success,
                "classification": r.classification,
                "latency_ms": r.latency_ms,
                "source": r.source,
                "error": r.error,
                "ts": r.completed_at,
            }
            f.write(json.dumps(d) + "\n")

    def persist_phase(self, pr: PhaseResult) -> None:
        with open(PHASE_LOG, "a") as f:
            d = {
                "phase": pr.phase,
                "name": pr.name,
                "total": pr.total,
                "successful": pr.successful,
                "failed": pr.failed,
                "elapsed_s": round(pr.elapsed_s, 1),
                "gate_passed": pr.gate_passed,
                "notes": pr.notes,
                "slo_metrics": pr.slo_metrics,
                "ts": time.time(),
            }
            f.write(json.dumps(d) + "\n")
        self.phase_results.append(pr)

    def mesh_health(self) -> dict:
        try:
            req = urllib.request.Request(
                "http://localhost:%d/health" % _MESH_HTTP_PORT, method="GET"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:
            return {"status": "unreachable", "error": str(exc)}

    def mesh_dispatch(self, command: str, timeout: int = 30) -> dict:
        self.slo.dispatch_attempts += 1
        t0 = time.time()
        try:
            payload = json.dumps({
                "node_id": "windows-desktop",
                "capability": "shell",
                "params": {"command": command, "timeout": timeout},
                "timeout": timeout,
            }).encode()
            req = urllib.request.Request(
                "http://localhost:%d/dispatch" % _MESH_HTTP_PORT,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout + 10) as resp:
                result = json.loads(resp.read().decode())
            latency = round((time.time() - t0) * 1000, 1)
            self.slo.latencies_ms.append(latency)
            if result.get("ok") or result.get("result_data", {}).get("success"):
                self.slo.dispatch_successes += 1
            return result
        except Exception as exc:
            logger.error("mesh dispatch failed: %s", exc)
            return {"ok": False, "error": str(exc)}

    def mesh_dispatch_argv(self, argv: list, timeout: int = 30) -> dict:
        self.slo.dispatch_attempts += 1
        t0 = time.time()
        try:
            payload = json.dumps({
                "node_id": "windows-desktop",
                "capability": "shell",
                "params": {"argv": argv, "timeout": timeout},
                "timeout": timeout,
            }).encode()
            req = urllib.request.Request(
                "http://localhost:%d/dispatch" % _MESH_HTTP_PORT,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout + 10) as resp:
                result = json.loads(resp.read().decode())
            latency = round((time.time() - t0) * 1000, 1)
            self.slo.latencies_ms.append(latency)
            if result.get("ok") or result.get("result_data", {}).get("success"):
                self.slo.dispatch_successes += 1
            return result
        except Exception as exc:
            logger.error("mesh dispatch argv failed: %s", exc)
            return {"ok": False, "error": str(exc)}

    def beast_available(self) -> bool:
        self.slo.mesh_attempts += 1
        health = self.mesh_health()
        if health.get("status") == "healthy":
            self.slo.mesh_successes += 1
        node_ids = health.get("node_ids", [])
        available = "windows-desktop" in node_ids
        self.slo.session_checks += 1
        if available:
            self.slo.session_available += 1
        return available

    def noop_execute(self, label: str) -> Callable[[], tuple]:
        def fn() -> tuple:
            return ("c40b simulation: %s" % label, True)
        return fn

    def event_count(self) -> int:
        return len(self._event_log)
