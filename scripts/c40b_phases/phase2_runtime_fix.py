"""C40B Phase 2 — Runtime Defect Resolution.

Reads defects from Phase 1's runtime_contract.json, logs diagnoses,
and re-runs browser prerequisite to verify fixes. If no defects found,
this phase is a no-op.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import os
import sys
_PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_PHASE_DIR))
sys.path.insert(0, "/opt/OS")
sys.path.insert(0, _REPO_ROOT)

from scripts.c40b_phases.campaign_context import (
    CampaignContext,
    PhaseResult,
    DATA_DIR,
)
from scripts.c40b_phases.phase1_runtime_audit import (
    _check_browser_prerequisite,
    CONTRACT_PATH,
)

logger = logging.getLogger("c40b")

DEFECT_LOG = DATA_DIR / "defect_log.jsonl"

KNOWN_FIXES = {
    "governed_mutation_to_router": {
        "diagnosis": "MutationRequest construction failed — check import path",
        "fix": "verify substrate.organism.mutation_router imports",
    },
    "router_to_spine": {
        "diagnosis": "GovernedExecutionSpine import or instantiation failed",
        "fix": "verify substrate.organism.governed_spine imports",
    },
    "spine_to_event_spine": {
        "diagnosis": "EventSpine pub/sub not delivering events",
        "fix": "check subscriber registration and thread safety",
    },
    "collector_to_mesh_http": {
        "diagnosis": "Mesh HTTP relay not accepting POST /dispatch",
        "fix": "verify mesh server running on :8095 (host process)",
    },
    "relay_to_jsonrpc": {
        "diagnosis": "JSON-RPC wrapping malformed",
        "fix": "check server._http_dispatch params nesting",
    },
    "client_to_adapter": {
        "diagnosis": "Client params extraction incorrect",
        "fix": "verify client._handle_capability extracts params.params",
    },
    "adapter_to_subprocess": {
        "diagnosis": "ShellAdapter subprocess execution failed",
        "fix": "check shell=True for command strings, CREATE_NO_WINDOW on Windows",
    },
    "trigger_to_evidence": {
        "diagnosis": "Evidence round-trip failed",
        "fix": "check trigger_collection() mesh dispatch and response parsing",
    },
    "browser_prerequisite": {
        "diagnosis": "Beast Session 1 not fully operational",
        "fix": "ensure Beast daemon running (Task Scheduler ONLOGON), "
               "Chrome installed, Playwright installed, pyautogui available",
    },
}


@dataclass
class DefectEntry:
    boundary_id: str
    status: str
    error: str
    diagnosis: str = ""
    recommended_fix: str = ""
    resolved: bool = False
    resolution_notes: str = ""
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        return {
            "boundary_id": self.boundary_id,
            "status": self.status,
            "error": self.error,
            "diagnosis": self.diagnosis,
            "recommended_fix": self.recommended_fix,
            "resolved": self.resolved,
            "resolution_notes": self.resolution_notes,
            "timestamp": self.timestamp,
        }


def _load_defects() -> list[dict]:
    """Load defects from Phase 1 runtime contract."""
    if not CONTRACT_PATH.exists():
        logger.warning("No runtime_contract.json found — Phase 1 not run?")
        return []
    contract = json.loads(CONTRACT_PATH.read_text())
    return contract.get("defects", [])


def _diagnose_defect(defect: dict) -> DefectEntry:
    """Create a diagnosed defect entry."""
    boundary_id = defect.get("boundary_id", "unknown")
    known = KNOWN_FIXES.get(boundary_id, {})

    return DefectEntry(
        boundary_id=boundary_id,
        status=defect.get("status", "unknown"),
        error=defect.get("error", ""),
        diagnosis=known.get("diagnosis", "unknown defect — manual investigation required"),
        recommended_fix=known.get("fix", "manual investigation required"),
        timestamp=time.time(),
    )


def _persist_defect(entry: DefectEntry) -> None:
    """Append defect to JSONL log."""
    DEFECT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(DEFECT_LOG, "a") as f:
        f.write(json.dumps(entry.to_dict()) + "\n")


def run_phase2(ctx: CampaignContext) -> PhaseResult:
    """Phase 2: Runtime Defect Resolution."""
    logger.info("=" * 60)
    logger.info("PHASE 2: Runtime Defect Resolution")
    logger.info("=" * 60)
    pr = PhaseResult(phase=2, name="Runtime Defect Resolution")
    t0 = time.time()

    raw_defects = _load_defects()

    if not raw_defects:
        logger.info("No defects found in Phase 1 — Phase 2 is a no-op")
        pr.gate_passed = True
        pr.notes = "no defects found"
        pr.elapsed_s = round(time.time() - t0, 1)
        ctx.persist_phase(pr)
        return pr

    logger.info("Found %d defects from Phase 1", len(raw_defects))

    diagnosed = []
    for raw in raw_defects:
        entry = _diagnose_defect(raw)
        diagnosed.append(entry)
        _persist_defect(entry)
        logger.warning(
            "DEFECT [%s]: %s — diagnosis: %s — fix: %s",
            entry.boundary_id,
            entry.error[:100],
            entry.diagnosis,
            entry.recommended_fix,
        )

    # Re-run browser prerequisite if not skipping
    recheck_passed = False
    if not ctx.skip_browser:
        logger.info("Re-running browser prerequisite to verify fixes...")
        prereq = _check_browser_prerequisite(ctx)
        recheck_passed = prereq.overall
        logger.info(
            "Browser prerequisite recheck: %s",
            "PASS" if recheck_passed else "FAIL",
        )
        if not recheck_passed:
            for err in prereq.errors:
                logger.warning("  recheck error: %s", err)

        # Update defect resolution status
        for entry in diagnosed:
            if entry.boundary_id == "browser_prerequisite":
                entry.resolved = recheck_passed
                entry.resolution_notes = (
                    "recheck passed" if recheck_passed else "recheck still failing"
                )
                _persist_defect(entry)
    else:
        logger.info("Skipping browser prerequisite recheck (--skip-browser)")

    # Check serialization defects (these are code-level, not runtime)
    ser_defects = [d for d in diagnosed if d.boundary_id != "browser_prerequisite"]
    ser_resolved = all(d.boundary_id == "browser_prerequisite" for d in diagnosed)

    remaining = len([d for d in diagnosed if not d.resolved])
    if ctx.skip_browser:
        # In skip-browser mode, only count serialization defects
        remaining = len(ser_defects)

    pr.total = len(diagnosed)
    pr.successful = pr.total - remaining
    pr.failed = remaining
    pr.elapsed_s = round(time.time() - t0, 1)
    pr.gate_passed = remaining == 0
    pr.notes = "%d defects diagnosed, %d remaining" % (len(diagnosed), remaining)
    ctx.persist_phase(pr)

    if remaining > 0:
        logger.warning(
            "Phase 2 gate FAILED — %d defects remain. "
            "Manual fixes required before Phase 3.",
            remaining,
        )
    else:
        logger.info("Phase 2 gate PASSED — all defects resolved")

    return pr
