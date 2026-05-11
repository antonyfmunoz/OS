"""Foreground CU Ingestion Execution v1.

VPS-side orchestrator for real foreground Computer Use ingestion
through the Windows workstation relay. Routes:

  Discord !ingest-safe-doc-cu
    → relay transport (SSH/SCP)
      → Windows relay Handle-IngestSafeDocCU
        → real Chrome launch + navigation + DOM extraction
      → VPS polls result
    → classify ingestion evidence
    → generate canonical/instance candidates
    → build foreground CU proof
    → persist proof + candidates

Canonical candidate: reusable structures, abstractions, frameworks,
  invariants, templates, schemas — not identity-bound.
Instance candidate: founder-specific data, conversations, notes,
  business details, environment observations — identity-bound.

UMH substrate subsystem. Phase 96.8AS.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.actuation.actuator_maturity_v1 import (
    MATURITY_LABELS,
    ActuatorMaturityLevel,
)
from runtime.substrate.memory_scope_contracts import MemoryScope
import os
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"



def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


INGESTION_PROOF_DIR = Path("data/runtime/workstation_relay/ingestion_proofs")

CU_INGESTION_MATURITY_REQUIREMENTS: dict[ActuatorMaturityLevel, list[str]] = {
    ActuatorMaturityLevel.L0_SIMULATED: [],
    ActuatorMaturityLevel.L1_PROCESS_STARTED: ["chrome_pid"],
    ActuatorMaturityLevel.L2_WINDOW_OBSERVED: ["chrome_pid", "window_handle"],
    ActuatorMaturityLevel.L3_FOREGROUND_FOCUSED: [
        "chrome_pid",
        "window_handle",
        "foreground_focused",
    ],
    ActuatorMaturityLevel.L4_NAVIGATION_OBSERVED: [
        "chrome_pid",
        "window_handle",
        "foreground_focused",
        "navigation_observed",
    ],
    ActuatorMaturityLevel.L5_SCREENSHOT_VERIFIED: [
        "chrome_pid",
        "window_handle",
        "foreground_focused",
        "navigation_observed",
        "screenshot_captured",
    ],
    ActuatorMaturityLevel.L6_FOUNDER_CONFIRMED: [
        "chrome_pid",
        "window_handle",
        "foreground_focused",
        "navigation_observed",
        "screenshot_captured",
        "founder_confirmed",
    ],
    ActuatorMaturityLevel.L7_REPLAYABLE_ACTUATION: [
        "chrome_pid",
        "window_handle",
        "foreground_focused",
        "navigation_observed",
        "screenshot_captured",
        "founder_confirmed",
        "extraction_completed",
    ],
}

CANDIDATE_TYPE_CANONICAL = "canonical"
CANDIDATE_TYPE_INSTANCE = "instance"

CANONICAL_INDICATORS = frozenset(
    {
        "template",
        "schema",
        "framework",
        "structure",
        "pattern",
        "invariant",
        "protocol",
        "standard",
        "abstract",
        "generic",
        "reusable",
        "universal",
    }
)

INSTANCE_INDICATORS = frozenset(
    {
        "account",
        "personal",
        "specific",
        "credential",
        "identity",
        "private",
        "conversation",
        "meeting",
        "note",
        "business",
        "contact",
        "name",
        "email",
        "address",
        "phone",
        "password",
        "founder",
    }
)


@dataclass
class CUIngestionEvidence:
    """Evidence collected from a real foreground CU ingestion relay execution."""

    chrome_pid: int = 0
    window_handle: int = 0
    window_title: str = ""
    foreground_focused: bool = False
    navigation_observed: bool = False
    navigation_url: str = ""
    screenshot_path: str = ""
    screenshot_hash: str = ""
    extraction_completed: bool = False
    extracted_title: str = ""
    extracted_content_length: int = 0
    extracted_content_preview: str = ""
    extracted_content_hash: str = ""
    desktop_unlocked: bool = False
    desktop_session_active: bool = False
    monitor_detected: bool = False
    founder_confirmed: bool = False
    relay_node_id: str = ""
    relay_machine: str = ""
    is_dry_run: bool = False
    trace_id: str = ""
    request_id: str = ""

    @property
    def has_chrome_pid(self) -> bool:
        return self.chrome_pid > 0

    @property
    def has_window_handle(self) -> bool:
        return self.window_handle != 0

    @property
    def has_screenshot(self) -> bool:
        return bool(self.screenshot_path) and bool(self.screenshot_hash)

    @property
    def has_extraction(self) -> bool:
        return self.extraction_completed and self.extracted_content_length > 0

    @property
    def has_navigation(self) -> bool:
        return self.navigation_observed

    @property
    def missing_evidence(self) -> list[str]:
        missing: list[str] = []
        if not self.has_chrome_pid:
            missing.append("chrome_pid")
        if not self.has_window_handle:
            missing.append("window_handle")
        if not self.foreground_focused:
            missing.append("foreground_focused")
        if not self.has_navigation:
            missing.append("navigation_observed")
        if not self.has_screenshot:
            missing.append("screenshot")
        if not self.has_extraction:
            missing.append("extraction")
        if not self.founder_confirmed:
            missing.append("founder_confirmed")
        return missing

    def to_dict(self) -> dict[str, Any]:
        return {
            "chrome_pid": self.chrome_pid,
            "window_handle": self.window_handle,
            "window_title": self.window_title,
            "foreground_focused": self.foreground_focused,
            "navigation_observed": self.navigation_observed,
            "navigation_url": self.navigation_url,
            "screenshot_path": self.screenshot_path,
            "screenshot_hash": self.screenshot_hash,
            "extraction_completed": self.extraction_completed,
            "extracted_title": self.extracted_title,
            "extracted_content_length": self.extracted_content_length,
            "extracted_content_preview": self.extracted_content_preview,
            "extracted_content_hash": self.extracted_content_hash,
            "desktop_unlocked": self.desktop_unlocked,
            "desktop_session_active": self.desktop_session_active,
            "monitor_detected": self.monitor_detected,
            "founder_confirmed": self.founder_confirmed,
            "relay_node_id": self.relay_node_id,
            "relay_machine": self.relay_machine,
            "is_dry_run": self.is_dry_run,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "missing_evidence": self.missing_evidence,
        }


@dataclass
class IngestionCandidate:
    """A candidate extracted from foreground CU ingestion."""

    candidate_id: str = ""
    candidate_type: str = ""
    label: str = ""
    content_preview: str = ""
    source_url: str = ""
    source_title: str = ""
    memory_scope: str = MemoryScope.INSTANCE_MEMORY.value
    confidence: float = 0.0
    extraction_method: str = "foreground_cu_dom"
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.candidate_id:
            self.candidate_id = f"CAND-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "candidate_type": self.candidate_type,
            "label": self.label,
            "content_preview": self.content_preview[:200] if self.content_preview else "",
            "source_url": self.source_url,
            "source_title": self.source_title,
            "memory_scope": self.memory_scope,
            "confidence": round(self.confidence, 2),
            "extraction_method": self.extraction_method,
            "timestamp": self.timestamp,
        }


@dataclass
class CUIngestionProof:
    """Complete proof of foreground CU ingestion execution."""

    proof_id: str = ""
    trace_id: str = ""
    maturity_level: ActuatorMaturityLevel = ActuatorMaturityLevel.L0_SIMULATED
    maturity_ceiling: ActuatorMaturityLevel = ActuatorMaturityLevel.L7_REPLAYABLE_ACTUATION
    escalation_blocked: bool = False
    escalation_reason: str = ""
    evidence: CUIngestionEvidence | None = None
    candidates: list[IngestionCandidate] = field(default_factory=list)
    canonical_count: int = 0
    instance_count: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.proof_id:
            h = hashlib.sha256(f"{self.trace_id}-{_now_iso()}".encode()).hexdigest()[:8]
            self.proof_id = f"CUIP-{h}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    @property
    def maturity_label(self) -> str:
        return MATURITY_LABELS.get(self.maturity_level, "unknown")

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "proof_type": "foreground_cu_ingestion",
            "trace_id": self.trace_id,
            "maturity_level": self.maturity_level.value,
            "maturity_level_name": self.maturity_level.name,
            "maturity_label": self.maturity_label,
            "maturity_ceiling": self.maturity_ceiling.value,
            "escalation_blocked": self.escalation_blocked,
            "escalation_reason": self.escalation_reason,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "candidates": [c.to_dict() for c in self.candidates],
            "canonical_count": self.canonical_count,
            "instance_count": self.instance_count,
            "timestamp": self.timestamp,
        }


def extract_ingestion_evidence(
    relay_result: dict[str, Any],
    founder_confirmed: bool = False,
) -> CUIngestionEvidence:
    """Extract CU ingestion evidence from a real relay result."""
    obs = relay_result.get("observed_desktop_state", {})
    extraction = relay_result.get("extraction_result", {})

    return CUIngestionEvidence(
        chrome_pid=obs.get("chrome_pid", 0),
        window_handle=obs.get("window_handle", 0),
        window_title=obs.get("window_title", ""),
        foreground_focused=obs.get("focused", False),
        navigation_observed=obs.get("navigation_detected", False),
        navigation_url=obs.get("navigation_url", ""),
        screenshot_path=obs.get("screenshot_path", ""),
        screenshot_hash=obs.get("screenshot_hash", ""),
        extraction_completed=extraction.get("completed", False),
        extracted_title=extraction.get("title", ""),
        extracted_content_length=extraction.get("content_length", 0),
        extracted_content_preview=extraction.get("content_preview", ""),
        extracted_content_hash=extraction.get("content_hash", ""),
        desktop_unlocked=obs.get("desktop_unlocked", False),
        desktop_session_active=obs.get(
            "active_user_session", obs.get("desktop_session_active", False)
        ),
        monitor_detected=obs.get("monitor_detected", False),
        founder_confirmed=founder_confirmed,
        relay_node_id=relay_result.get("node_id", ""),
        relay_machine=relay_result.get("machine_name", ""),
        is_dry_run=relay_result.get("dry_run", False),
        trace_id=relay_result.get("trace_id", ""),
        request_id=relay_result.get("request_id", ""),
    )


def compute_ingestion_maturity(evidence: CUIngestionEvidence) -> ActuatorMaturityLevel:
    """Compute raw maturity level from ingestion evidence."""
    if evidence.is_dry_run:
        return ActuatorMaturityLevel.L0_SIMULATED

    evidence_map = {
        "chrome_pid": evidence.has_chrome_pid,
        "window_handle": evidence.has_window_handle,
        "foreground_focused": evidence.foreground_focused,
        "navigation_observed": evidence.has_navigation,
        "screenshot_captured": evidence.has_screenshot,
        "founder_confirmed": evidence.founder_confirmed,
        "extraction_completed": evidence.has_extraction,
    }

    for level in reversed(ActuatorMaturityLevel):
        reqs = CU_INGESTION_MATURITY_REQUIREMENTS.get(level, [])
        if all(evidence_map.get(r, False) for r in reqs):
            return level

    return ActuatorMaturityLevel.L0_SIMULATED


def ingestion_maturity_ceiling(evidence: CUIngestionEvidence) -> ActuatorMaturityLevel:
    """Compute hard ceiling based on missing evidence."""
    if evidence.is_dry_run:
        return ActuatorMaturityLevel.L0_SIMULATED
    if not evidence.has_window_handle:
        return ActuatorMaturityLevel.L1_PROCESS_STARTED
    if not evidence.has_screenshot:
        return ActuatorMaturityLevel.L4_NAVIGATION_OBSERVED
    if not evidence.has_extraction:
        return ActuatorMaturityLevel.L5_SCREENSHOT_VERIFIED
    if not evidence.founder_confirmed:
        return ActuatorMaturityLevel.L5_SCREENSHOT_VERIFIED
    return ActuatorMaturityLevel.L7_REPLAYABLE_ACTUATION


def classify_candidate_type(label: str, content: str) -> str:
    """Classify whether a candidate is canonical or instance-scoped."""
    text = f"{label} {content}".lower()
    canonical_score = sum(1 for ind in CANONICAL_INDICATORS if ind in text)
    instance_score = sum(1 for ind in INSTANCE_INDICATORS if ind in text)

    if instance_score > canonical_score:
        return CANDIDATE_TYPE_INSTANCE
    if canonical_score > 0:
        return CANDIDATE_TYPE_CANONICAL
    return CANDIDATE_TYPE_INSTANCE


def generate_candidates_from_extraction(
    extraction_result: dict[str, Any],
    source_url: str = "",
    source_title: str = "",
) -> list[IngestionCandidate]:
    """Generate canonical/instance candidates from extraction results."""
    candidates: list[IngestionCandidate] = []

    title = extraction_result.get("title", "")
    if title:
        ctype = classify_candidate_type(title, "")
        candidates.append(
            IngestionCandidate(
                candidate_type=ctype,
                label=f"document_title: {title}",
                content_preview=title,
                source_url=source_url,
                source_title=source_title,
                memory_scope=(
                    MemoryScope.INSTANCE_MEMORY.value
                    if ctype == CANDIDATE_TYPE_INSTANCE
                    else MemoryScope.PROJECT_MEMORY.value
                ),
                confidence=0.9,
            )
        )

    headings = extraction_result.get("headings", [])
    for heading in headings:
        h_text = heading if isinstance(heading, str) else str(heading)
        ctype = classify_candidate_type(h_text, "")
        candidates.append(
            IngestionCandidate(
                candidate_type=ctype,
                label=f"heading: {h_text}",
                content_preview=h_text,
                source_url=source_url,
                source_title=source_title,
                memory_scope=(
                    MemoryScope.INSTANCE_MEMORY.value
                    if ctype == CANDIDATE_TYPE_INSTANCE
                    else MemoryScope.PROJECT_MEMORY.value
                ),
                confidence=0.7,
            )
        )

    content_preview = extraction_result.get("content_preview", "")
    if content_preview:
        ctype = classify_candidate_type("document_content", content_preview)
        candidates.append(
            IngestionCandidate(
                candidate_type=ctype,
                label="document_content",
                content_preview=content_preview[:200],
                source_url=source_url,
                source_title=source_title,
                memory_scope=MemoryScope.INSTANCE_MEMORY.value,
                confidence=0.6,
            )
        )

    links = extraction_result.get("links", [])
    for link in links:
        link_text = link if isinstance(link, str) else str(link)
        ctype = classify_candidate_type("link_reference", link_text)
        candidates.append(
            IngestionCandidate(
                candidate_type=ctype,
                label=f"link: {link_text[:100]}",
                content_preview=link_text[:200],
                source_url=source_url,
                source_title=source_title,
                memory_scope=MemoryScope.INSTANCE_MEMORY.value,
                confidence=0.5,
            )
        )

    return candidates


def classify_cu_ingestion(evidence: CUIngestionEvidence) -> CUIngestionProof:
    """Classify foreground CU ingestion into a maturity-aware proof."""
    if evidence.is_dry_run:
        return CUIngestionProof(
            trace_id=evidence.trace_id,
            maturity_level=ActuatorMaturityLevel.L0_SIMULATED,
            maturity_ceiling=ActuatorMaturityLevel.L0_SIMULATED,
            escalation_blocked=True,
            escalation_reason="dry_run_always_L0",
            evidence=evidence,
        )

    raw_level = compute_ingestion_maturity(evidence)
    ceiling = ingestion_maturity_ceiling(evidence)
    final_level = min(raw_level, ceiling)

    missing = evidence.missing_evidence
    blocked = len(missing) > 0
    reason = ""
    if blocked:
        if not evidence.has_extraction:
            reason = "extraction_not_completed"
        elif not evidence.has_screenshot:
            reason = "screenshot_not_captured"
        elif not evidence.founder_confirmed:
            reason = "founder_confirmation_missing"
        else:
            reason = f"missing: {', '.join(missing)}"

    return CUIngestionProof(
        trace_id=evidence.trace_id,
        maturity_level=final_level,
        maturity_ceiling=ceiling,
        escalation_blocked=blocked,
        escalation_reason=reason,
        evidence=evidence,
    )


def build_full_ingestion_proof(
    relay_result: dict[str, Any],
    founder_confirmed: bool = False,
) -> CUIngestionProof:
    """Build complete ingestion proof from relay result with candidates."""
    evidence = extract_ingestion_evidence(relay_result, founder_confirmed)
    proof = classify_cu_ingestion(evidence)

    extraction = relay_result.get("extraction_result", {})
    if extraction and evidence.has_extraction:
        candidates = generate_candidates_from_extraction(
            extraction,
            source_url=evidence.navigation_url,
            source_title=evidence.extracted_title,
        )
        proof.candidates = candidates
        proof.canonical_count = sum(
            1 for c in candidates if c.candidate_type == CANDIDATE_TYPE_CANONICAL
        )
        proof.instance_count = sum(
            1 for c in candidates if c.candidate_type == CANDIDATE_TYPE_INSTANCE
        )

    return proof


def persist_cu_ingestion_proof(
    proof: CUIngestionProof,
    base_dir: Path = Path(_ROOT),
) -> Path:
    """Persist CU ingestion proof to disk."""
    proof_dir = base_dir / INGESTION_PROOF_DIR
    proof_dir.mkdir(parents=True, exist_ok=True)
    path = proof_dir / f"{proof.proof_id}.json"
    path.write_text(json.dumps(proof.to_dict(), indent=2, default=str))
    return path


def send_ingest_safe_doc_request(
    timeout_seconds: int = 120,
) -> Any:
    """Send real foreground CU ingestion request via relay transport."""
    from core.workstation.relay_execution_transport_v1 import send_and_wait
    from core.environment_bridge.windows_desktop_request_builder import (
        build_w0_real_foreground_cu_ingestion_request,
    )

    config_path = Path(_ROOT) / "config" / "w0_real_foreground_cu_ingestion_v1.json"
    config: dict[str, Any] = {}
    if config_path.exists():
        config = json.loads(config_path.read_text())

    request = build_w0_real_foreground_cu_ingestion_request(
        safe_doc_url=config.get("safe_doc_url_or_id", ""),
        safe_doc_title=config.get("safe_doc_title", "EOS W0 Test Document"),
        google_account_identity=config.get("google_account_identity", ""),
        adapter_instance_id=config.get("adapter_instance_id", ""),
    )
    return send_and_wait(request.to_dict(), timeout_seconds=timeout_seconds)
