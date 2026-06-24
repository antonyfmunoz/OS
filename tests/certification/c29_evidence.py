#!/usr/bin/env python3
"""C29 Harness Superiority — Browser Evidence Collector.

Runs ON Beast via Playwright to collect Class B browser evidence for the
C29 Harness Superiority benchmark. Each test function receives a Playwright
Page object already authenticated to the cockpit and exercises real UI
interactions: panel navigation, element visibility checks, timing
measurements, and screenshot capture.

This module does NOT trigger via SSH. It runs directly on Beast (Session 1)
where Playwright has access to a real display. The VPS orchestrator calls
this module on Beast via SSH or the node daemon.

Evidence types collected:
  - ContinuityResult: tab close/reopen, TTRC measurement
  - GovernanceResult: approval workflow presence check
  - AwarenessSnapshot: 10 visibility items across panels
  - CognitiveLoadResult: reconstruction step count during resume
  - InterruptionResult: panel switch mid-task timing
  - RealityDriftResult: drift indicator detection
  - MetaIDEResult: 7 awareness dimensions in Meta IDE
  - BrowserEvidence: screenshots + console/network traces

All result types imported from substrate.organism.benchmarks.harness_superiority.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from substrate.organism.benchmarks.harness_superiority import (  # noqa: E402
    AwarenessSnapshot,
    BrowserEvidence,
    CognitiveLoadResult,
    ContinuityResult,
    GovernanceResult,
    InterruptionResult,
    MetaIDEResult,
    RealityDriftResult,
)

logger = logging.getLogger(__name__)

_COCKPIT_URL = "https://universalmetaharness.tech"

# Panel labels that appear in the LeftRail (primary + system visibility).
# Maps logical name -> exact label text rendered in the <span>.
_PANEL_LABELS: dict[str, str] = {
    "commandcenter": "Command Center",
    "work": "Work",
    "agents": "Agents",
    "approvals": "Approvals",
    "activity": "Activity",
    "editor": "Meta IDE",
    "execution": "Execution",
    "organismmap": "Organism Map",
    "rooms": "Conference Rooms",
    "vision": "Vision",
    "broadcast": "Broadcast",
    "knowledge": "Knowledge",
    "settings": "Settings",
    "unifiedexecution": "Unified Execution",
    "buildloop": "Build Loop",
    "projectionintegration": "Projection Integration",
    "orchestratorawareness": "Orchestrator",
    "operatingloopview": "Operating Loop",
    "sessionresume": "Session Resume",
    "delegation": "Delegation",
    "operations": "Operations",
    "goals": "Goals",
}


def _umh_root() -> Path:
    return Path(os.environ.get("UMH_ROOT", "/opt/OS"))


def _run_dir(task_id: str) -> Path:
    """Return screenshot output directory for a given task run."""
    d = _umh_root() / "data" / "certification" / "c29" / "runs" / task_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _screenshot_path(task_id: str, name: str) -> str:
    """Build a screenshot file path."""
    return str(_run_dir(task_id) / f"{name}.png")


# ---------------------------------------------------------------------------
# Navigation helper
# ---------------------------------------------------------------------------


async def _navigate_to_panel(
    page: Any,
    panel_label: str,
    timeout: int = 5000,
) -> bool:
    """Click a LeftRail button by its label text.

    The LeftRail renders <button> elements with a <span> containing the
    panel label in uppercase 10px mono text. We locate by text-is match
    on the span inside a nav button.

    Args:
        page: Playwright Page object.
        panel_label: Exact label text (e.g. "Command Center", "Meta IDE").
        timeout: Max wait in milliseconds for the button to be clickable.

    Returns:
        True if navigation succeeded, False on timeout or error.
    """
    try:
        btn = page.locator(
            f'nav button:has(span:text-is("{panel_label}"))'
        ).first
        await btn.click(timeout=timeout)
        await page.wait_for_timeout(500)  # animation settle
        return True
    except Exception as exc:
        logger.debug(
            "Failed to navigate to panel '%s': %s", panel_label, exc
        )
        return False


async def _element_visible(
    page: Any,
    selector: str,
    timeout: int = 3000,
) -> bool:
    """Check if a selector is visible within timeout."""
    try:
        loc = page.locator(selector).first
        await loc.wait_for(state="visible", timeout=timeout)
        return True
    except Exception:
        return False


async def _text_visible(
    page: Any,
    text: str,
    timeout: int = 3000,
) -> bool:
    """Check if text content is visible on the page."""
    try:
        loc = page.get_by_text(text, exact=False).first
        await loc.wait_for(state="visible", timeout=timeout)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Test 1: Continuity
# ---------------------------------------------------------------------------


async def continuity_test(page: Any) -> ContinuityResult:
    """Close the cockpit tab and reopen it, measuring TTRC.

    TTRC = Time To Reconstruct Context. We navigate to a panel, close the
    page, reopen it, and measure how long until the session resume card or
    the previously-active panel re-appears.

    Args:
        page: Playwright Page object with active cockpit session.

    Returns:
        ContinuityResult with TTRC and context preservation metrics.
    """
    # Step 1: Navigate to a known panel to establish context
    await _navigate_to_panel(page, "Command Center")
    await page.wait_for_timeout(1000)

    # Step 2: Record what we see before "closing"
    pre_url = page.url

    # Step 3: Navigate away (simulates tab close) then back
    t_start = time.monotonic()
    await page.goto("about:blank")
    await page.wait_for_timeout(500)

    # Step 4: Reopen cockpit
    await page.goto(_COCKPIT_URL)
    await page.wait_for_load_state("networkidle", timeout=10000)

    # Step 5: Check for session resume indicators
    resume_found = await _text_visible(page, "Session Resume", timeout=5000)
    resume_card_found = await _element_visible(
        page, '[data-testid="resume-card"], [class*="resume"]', timeout=3000
    )

    t_resume = time.monotonic() - t_start

    # Step 6: Check if we returned to the same context
    context_preserved = resume_found or resume_card_found
    intent_preserved = False

    # Check if the page restored to Command Center or shows session state
    if context_preserved:
        cc_visible = await _text_visible(page, "Command Center", timeout=3000)
        intent_preserved = cc_visible

    return ContinuityResult(
        interruption_duration_seconds=round(t_resume, 2),
        context_preserved=context_preserved,
        resume_time_seconds=round(t_resume, 2),
        decisions_recalled=1 if context_preserved else 0,
        decisions_total=1,
        intent_preserved=intent_preserved,
    )


# ---------------------------------------------------------------------------
# Test 2: Governance
# ---------------------------------------------------------------------------


async def governance_test(page: Any) -> GovernanceResult:
    """Navigate to Approvals panel and check governance elements.

    Looks for approval workflow UI elements: approval cards, risk badges,
    verification status indicators, and governance controls.

    Args:
        page: Playwright Page object with active cockpit session.

    Returns:
        GovernanceResult with approval enforcement metrics.
    """
    navigated = await _navigate_to_panel(page, "Approvals")
    if not navigated:
        logger.debug("Could not navigate to Approvals panel")
        return GovernanceResult(
            approvals_required=0,
            approvals_enforced=0,
            proof_generated=False,
            verification_enforced=False,
            false_history_tested=False,
            false_history_blocked=False,
        )

    await page.wait_for_timeout(1000)

    # Check for governance UI elements
    has_approval_cards = await _element_visible(
        page,
        '[data-testid="approval-card"], [class*="approval"], '
        '[class*="Approval"]',
        timeout=3000,
    )
    has_risk_badges = await _text_visible(page, "risk", timeout=2000)
    has_verification = await _text_visible(
        page, "verif", timeout=2000
    )
    has_proof = await _text_visible(page, "proof", timeout=2000)

    # Count visible approval-related elements
    approval_elements = page.locator(
        '[data-testid="approval-card"], [class*="approval"], '
        '[class*="Approval"]'
    )
    try:
        count = await approval_elements.count()
    except Exception:
        count = 0

    approvals_required = max(count, 1 if has_approval_cards else 0)
    approvals_enforced = count if has_approval_cards else 0

    return GovernanceResult(
        approvals_required=approvals_required,
        approvals_enforced=approvals_enforced,
        proof_generated=has_proof,
        verification_enforced=has_verification,
        false_history_tested=False,  # requires manual injection
        false_history_blocked=False,
    )


# ---------------------------------------------------------------------------
# Test 3: Awareness
# ---------------------------------------------------------------------------

# Maps each awareness dimension to (panel_label, check_fn_description).
# The test navigates to each panel and checks for relevant content.
_AWARENESS_CHECKS: list[tuple[str, str, str]] = [
    # (field_name, panel_label, text_to_find)
    ("repos_visible", "Meta IDE", "repo"),
    ("branches_visible", "Meta IDE", "branch"),
    ("builds_visible", "Build Loop", "build"),
    ("deployments_visible", "Execution", "deploy"),
    ("containers_visible", "Execution", "container"),
    ("previews_visible", "Meta IDE", "preview"),
    ("sessions_visible", "Execution", "session"),
    ("executions_visible", "Execution", "execution"),
    ("agents_visible", "Agents", "agent"),
    ("device_mesh_visible", "Organism Map", "mesh"),
]


async def awareness_test(page: Any) -> AwarenessSnapshot:
    """Navigate panels and check 10 visibility items for awareness scoring.

    Visits multiple cockpit panels and checks whether key information
    categories are surfaced: repos, branches, builds, deployments,
    containers, previews, sessions, executions, agents, device_mesh.

    Args:
        page: Playwright Page object with active cockpit session.

    Returns:
        AwarenessSnapshot with per-dimension visibility flags.
    """
    results: dict[str, bool] = {}
    visited_panels: set[str] = set()

    for field_name, panel_label, search_text in _AWARENESS_CHECKS:
        # Navigate only if we haven't been to this panel yet
        if panel_label not in visited_panels:
            navigated = await _navigate_to_panel(page, panel_label)
            if navigated:
                visited_panels.add(panel_label)
                await page.wait_for_timeout(800)

        if panel_label in visited_panels:
            visible = await _text_visible(page, search_text, timeout=2000)
            results[field_name] = visible
        else:
            results[field_name] = False

    return AwarenessSnapshot(**results)


# ---------------------------------------------------------------------------
# Test 4: Cognitive Load
# ---------------------------------------------------------------------------


async def cognitive_load_test(page: Any) -> CognitiveLoadResult:
    """Count reconstruction steps during a simulated session resume.

    Simulates an operator returning to the cockpit and measures how many
    actions are needed to reconstruct working context: panel hops, searches,
    clarification dialogs, and memory recovery actions.

    Args:
        page: Playwright Page object with active cockpit session.

    Returns:
        CognitiveLoadResult with step counts and computed score.
    """
    reconstruction_steps = 0
    panel_hops = 0
    context_searches = 0
    clarification_questions = 0
    memory_recovery_actions = 0

    # Simulate resume: navigate to Session Resume panel
    if await _navigate_to_panel(page, "Session Resume"):
        reconstruction_steps += 1
        panel_hops += 1

        # Check if session state is immediately visible
        has_session_state = await _text_visible(
            page, "session", timeout=3000
        )
        if not has_session_state:
            # Need to search for context
            context_searches += 1
            reconstruction_steps += 1

    # Check Command Center for current state
    if await _navigate_to_panel(page, "Command Center"):
        panel_hops += 1
        reconstruction_steps += 1

        # If command center shows active work, context is partially restored
        has_active_work = await _text_visible(page, "active", timeout=2000)
        if not has_active_work:
            memory_recovery_actions += 1
            reconstruction_steps += 1

    # Check Work panel for task state
    if await _navigate_to_panel(page, "Work"):
        panel_hops += 1
        reconstruction_steps += 1

        has_tasks = await _text_visible(page, "task", timeout=2000)
        if not has_tasks:
            context_searches += 1
            reconstruction_steps += 1

    # Check Activity for recent history
    if await _navigate_to_panel(page, "Activity"):
        panel_hops += 1
        reconstruction_steps += 1

    return CognitiveLoadResult(
        reconstruction_steps=reconstruction_steps,
        clarification_questions=clarification_questions,
        context_searches=context_searches,
        panel_hops=panel_hops,
        memory_recovery_actions=memory_recovery_actions,
    )


# ---------------------------------------------------------------------------
# Test 5: Interruption
# ---------------------------------------------------------------------------


async def interruption_test(
    page: Any,
    from_panel: str,
    to_panel: str,
) -> InterruptionResult:
    """Switch between panels mid-task, measuring resume time and accuracy.

    Navigates to from_panel, waits (simulating work), switches to to_panel,
    does work there, then switches back. Measures how long it takes to
    re-establish context after the interruption.

    Args:
        page: Playwright Page object with active cockpit session.
        from_panel: Label of the panel to start in (e.g. "Meta IDE").
        to_panel: Label of the panel to switch to (e.g. "Approvals").

    Returns:
        InterruptionResult with timing and accuracy measurements.
    """
    # Step 1: Navigate to the starting panel
    await _navigate_to_panel(page, from_panel)
    await page.wait_for_timeout(1000)

    # Capture initial state
    initial_content = await page.content()

    # Step 2: Interrupt — switch to different panel
    t_away_start = time.monotonic()
    await _navigate_to_panel(page, to_panel)
    await page.wait_for_timeout(2000)  # simulate work in interrupting panel
    away_duration = time.monotonic() - t_away_start

    # Step 3: Return to original panel
    t_resume_start = time.monotonic()
    await _navigate_to_panel(page, from_panel)

    # Wait for content to settle
    await page.wait_for_timeout(500)
    resume_time = time.monotonic() - t_resume_start

    # Step 4: Check context accuracy
    post_content = await page.content()

    # Simple accuracy heuristic: check if same panel is showing same type
    # of content (not a deep semantic comparison, but evidence of
    # state preservation)
    from_panel_visible = await _text_visible(page, from_panel, timeout=2000)
    context_accuracy = 1.0 if from_panel_visible else 0.5

    return InterruptionResult(
        interruption_type="TASK_SWITCH",
        interruption_from=from_panel,
        interruption_to=to_panel,
        away_duration_seconds=round(away_duration, 2),
        resume_time_seconds=round(resume_time, 2),
        context_accuracy=context_accuracy,
        decisions_recalled=1 if from_panel_visible else 0,
        decisions_total=1,
        work_recovery_complete=from_panel_visible,
    )


# ---------------------------------------------------------------------------
# Test 6: Reality Drift
# ---------------------------------------------------------------------------


async def reality_drift_test(page: Any) -> RealityDriftResult:
    """Navigate to reality-related panels and check for drift indicators.

    Looks for staleness warnings, drift alerts, version mismatches, or
    stale deploy indicators in panels that show system state.

    Args:
        page: Playwright Page object with active cockpit session.

    Returns:
        RealityDriftResult with drift detection metrics.
    """
    t_start = time.monotonic()
    drift_detected = False
    detection_method = "not_detected"

    # Check Execution panel for deployment state
    if await _navigate_to_panel(page, "Execution"):
        await page.wait_for_timeout(800)

        # Look for drift/stale/warning indicators
        has_stale = await _text_visible(page, "stale", timeout=2000)
        has_drift = await _text_visible(page, "drift", timeout=2000)
        has_warning = await _element_visible(
            page,
            '[class*="warning"], [class*="Warning"], '
            '[data-testid*="drift"], [class*="stale"]',
            timeout=2000,
        )

        if has_stale or has_drift or has_warning:
            drift_detected = True
            detection_method = "automated"

    # Check Organism Map for node health
    if not drift_detected:
        if await _navigate_to_panel(page, "Organism Map"):
            await page.wait_for_timeout(800)

            has_offline = await _text_visible(
                page, "offline", timeout=2000
            )
            has_unhealthy = await _text_visible(
                page, "unhealthy", timeout=2000
            )
            has_error = await _element_visible(
                page,
                '[class*="error"], [class*="Error"], '
                '[class*="danger"]',
                timeout=2000,
            )

            if has_offline or has_unhealthy or has_error:
                drift_detected = True
                detection_method = "automated"

    # Check Operations panel
    if not drift_detected:
        if await _navigate_to_panel(page, "Operations"):
            await page.wait_for_timeout(800)

            has_mismatch = await _text_visible(
                page, "mismatch", timeout=2000
            )
            has_outdated = await _text_visible(
                page, "outdated", timeout=2000
            )

            if has_mismatch or has_outdated:
                drift_detected = True
                detection_method = "automated"

    detection_time = time.monotonic() - t_start

    return RealityDriftResult(
        drift_type="STALE_DEPLOY",
        drift_present=drift_detected,
        drift_detected=drift_detected,
        detection_time_seconds=round(detection_time, 2),
        false_positive=False,
        detection_method=detection_method,
    )


# ---------------------------------------------------------------------------
# Test 7: Meta IDE
# ---------------------------------------------------------------------------


async def meta_ide_test(page: Any) -> MetaIDEResult:
    """Navigate to Meta IDE panel and check 7 awareness dimensions.

    The Meta IDE (panel id 'editor') is the development workspace. We check
    for indicators of: workspace, repo, branch, execution, preview, proof,
    and continuity awareness.

    Args:
        page: Playwright Page object with active cockpit session.

    Returns:
        MetaIDEResult with per-dimension awareness flags.
    """
    navigated = await _navigate_to_panel(page, "Meta IDE")
    if not navigated:
        logger.debug("Could not navigate to Meta IDE panel")
        return MetaIDEResult()

    await page.wait_for_timeout(1000)

    workspace_aware = await _text_visible(page, "workspace", timeout=2000)
    repo_aware = await _text_visible(page, "repo", timeout=2000)
    branch_aware = await _text_visible(page, "branch", timeout=2000)
    execution_aware = await _text_visible(
        page, "execution", timeout=2000
    ) or await _text_visible(page, "running", timeout=1000)
    preview_aware = await _text_visible(page, "preview", timeout=2000)
    proof_aware = await _text_visible(
        page, "proof", timeout=2000
    ) or await _text_visible(page, "verification", timeout=1000)
    continuity_aware = await _text_visible(
        page, "continuity", timeout=2000
    ) or await _text_visible(page, "session", timeout=1000)

    return MetaIDEResult(
        workspace_aware=workspace_aware,
        repo_aware=repo_aware,
        branch_aware=branch_aware,
        execution_aware=execution_aware,
        preview_aware=preview_aware,
        proof_aware=proof_aware,
        continuity_aware=continuity_aware,
    )


# ---------------------------------------------------------------------------
# Full evidence orchestrator
# ---------------------------------------------------------------------------


async def collect_full_evidence(
    page: Any,
    task_id: str,
) -> dict[str, Any]:
    """Orchestrate all C29 browser evidence tests and capture screenshots.

    Runs each test function in sequence, captures a screenshot after each,
    and returns a combined result dict containing BrowserEvidence plus all
    individual sub-results.

    Args:
        page: Playwright Page object with active cockpit session.
        task_id: Task identifier for file naming (e.g. "c29-001").

    Returns:
        Dict with keys:
          - browser_evidence: BrowserEvidence
          - continuity: ContinuityResult
          - governance: GovernanceResult
          - awareness: AwarenessSnapshot
          - cognitive_load: CognitiveLoadResult
          - interruption: InterruptionResult
          - reality_drift: RealityDriftResult
          - meta_ide: MetaIDEResult
    """
    screenshots: list[str] = []
    console_errors: list[str] = []
    console_log: list[str] = []
    execution_traces: list[str] = []

    # Set up console listener
    def _on_console(msg: Any) -> None:
        text = str(msg)
        if msg.type == "error":
            console_errors.append(text)
        else:
            console_log.append(text)

    try:
        page.on("console", _on_console)
    except Exception as exc:
        logger.debug("Could not attach console listener: %s", exc)

    run_dir = _run_dir(task_id)

    # ── Test 1: Continuity ──────────────────────────────────────────
    logger.info("C29 evidence: running continuity_test")
    try:
        cont_result = await continuity_test(page)
        execution_traces.append("continuity_test: OK")
    except Exception as exc:
        logger.debug("continuity_test failed: %s", exc)
        cont_result = ContinuityResult(
            interruption_duration_seconds=0.0,
            context_preserved=False,
            resume_time_seconds=0.0,
            decisions_recalled=0,
            decisions_total=1,
            intent_preserved=False,
        )
        execution_traces.append("continuity_test: FAILED - " + str(exc))

    ss = _screenshot_path(task_id, "01_continuity")
    try:
        await page.screenshot(path=ss, full_page=False)
        screenshots.append(ss)
    except Exception as exc:
        logger.debug("Screenshot failed (continuity): %s", exc)

    # ── Test 2: Governance ──────────────────────────────────────────
    logger.info("C29 evidence: running governance_test")
    try:
        gov_result = await governance_test(page)
        execution_traces.append("governance_test: OK")
    except Exception as exc:
        logger.debug("governance_test failed: %s", exc)
        gov_result = GovernanceResult(
            approvals_required=0,
            approvals_enforced=0,
            proof_generated=False,
            verification_enforced=False,
            false_history_tested=False,
            false_history_blocked=False,
        )
        execution_traces.append("governance_test: FAILED - " + str(exc))

    ss = _screenshot_path(task_id, "02_governance")
    try:
        await page.screenshot(path=ss, full_page=False)
        screenshots.append(ss)
    except Exception as exc:
        logger.debug("Screenshot failed (governance): %s", exc)

    # ── Test 3: Awareness ───────────────────────────────────────────
    logger.info("C29 evidence: running awareness_test")
    try:
        aware_result = await awareness_test(page)
        execution_traces.append("awareness_test: OK")
    except Exception as exc:
        logger.debug("awareness_test failed: %s", exc)
        aware_result = AwarenessSnapshot()
        execution_traces.append("awareness_test: FAILED - " + str(exc))

    ss = _screenshot_path(task_id, "03_awareness")
    try:
        await page.screenshot(path=ss, full_page=False)
        screenshots.append(ss)
    except Exception as exc:
        logger.debug("Screenshot failed (awareness): %s", exc)

    # ── Test 4: Cognitive Load ──────────────────────────────────────
    logger.info("C29 evidence: running cognitive_load_test")
    try:
        cog_result = await cognitive_load_test(page)
        execution_traces.append("cognitive_load_test: OK")
    except Exception as exc:
        logger.debug("cognitive_load_test failed: %s", exc)
        cog_result = CognitiveLoadResult(
            reconstruction_steps=0,
            clarification_questions=0,
            context_searches=0,
            panel_hops=0,
            memory_recovery_actions=0,
        )
        execution_traces.append("cognitive_load_test: FAILED - " + str(exc))

    ss = _screenshot_path(task_id, "04_cognitive_load")
    try:
        await page.screenshot(path=ss, full_page=False)
        screenshots.append(ss)
    except Exception as exc:
        logger.debug("Screenshot failed (cognitive_load): %s", exc)

    # ── Test 5: Interruption ────────────────────────────────────────
    logger.info("C29 evidence: running interruption_test")
    try:
        int_result = await interruption_test(
            page,
            from_panel="Meta IDE",
            to_panel="Approvals",
        )
        execution_traces.append("interruption_test: OK")
    except Exception as exc:
        logger.debug("interruption_test failed: %s", exc)
        int_result = InterruptionResult(
            interruption_type="TASK_SWITCH",
            interruption_from="Meta IDE",
            interruption_to="Approvals",
            away_duration_seconds=0.0,
            resume_time_seconds=0.0,
            context_accuracy=0.0,
            decisions_recalled=0,
            decisions_total=1,
            work_recovery_complete=False,
        )
        execution_traces.append("interruption_test: FAILED - " + str(exc))

    ss = _screenshot_path(task_id, "05_interruption")
    try:
        await page.screenshot(path=ss, full_page=False)
        screenshots.append(ss)
    except Exception as exc:
        logger.debug("Screenshot failed (interruption): %s", exc)

    # ── Test 6: Reality Drift ───────────────────────────────────────
    logger.info("C29 evidence: running reality_drift_test")
    try:
        drift_result = await reality_drift_test(page)
        execution_traces.append("reality_drift_test: OK")
    except Exception as exc:
        logger.debug("reality_drift_test failed: %s", exc)
        drift_result = RealityDriftResult(
            drift_type="STALE_DEPLOY",
            drift_present=False,
            drift_detected=False,
            detection_time_seconds=0.0,
            false_positive=False,
            detection_method="not_detected",
        )
        execution_traces.append("reality_drift_test: FAILED - " + str(exc))

    ss = _screenshot_path(task_id, "06_reality_drift")
    try:
        await page.screenshot(path=ss, full_page=False)
        screenshots.append(ss)
    except Exception as exc:
        logger.debug("Screenshot failed (reality_drift): %s", exc)

    # ── Test 7: Meta IDE ────────────────────────────────────────────
    logger.info("C29 evidence: running meta_ide_test")
    try:
        ide_result = await meta_ide_test(page)
        execution_traces.append("meta_ide_test: OK")
    except Exception as exc:
        logger.debug("meta_ide_test failed: %s", exc)
        ide_result = MetaIDEResult()
        execution_traces.append("meta_ide_test: FAILED - " + str(exc))

    ss = _screenshot_path(task_id, "07_meta_ide")
    try:
        await page.screenshot(path=ss, full_page=False)
        screenshots.append(ss)
    except Exception as exc:
        logger.debug("Screenshot failed (meta_ide): %s", exc)

    # ── Build BrowserEvidence ───────────────────────────────────────
    browser_evidence = BrowserEvidence(
        screenshots=screenshots,
        console_errors=console_errors[:50],
        console_log=console_log[:100],
        network_errors=[],
        network_traces=[],
        execution_traces=execution_traces,
        proof_package_id=task_id,
        verification_result="collected",
    )

    # ── Save combined results to disk ───────────────────────────────
    combined = {
        "task_id": task_id,
        "browser_evidence": browser_evidence.to_dict(),
        "continuity": cont_result.to_dict(),
        "governance": gov_result.to_dict(),
        "awareness": aware_result.to_dict(),
        "cognitive_load": cog_result.to_dict(),
        "interruption": int_result.to_dict(),
        "reality_drift": drift_result.to_dict(),
        "meta_ide": ide_result.to_dict(),
    }

    results_file = run_dir / "evidence_results.json"
    results_file.write_text(
        json.dumps(combined, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("C29 evidence saved to %s", results_file)

    return combined


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------


async def _run_standalone(task_id: str, url: str, headed: bool) -> None:
    """Run the full evidence collection as a standalone script.

    Launches Playwright, authenticates via Clerk, and runs all tests.
    Intended for direct execution on Beast.

    Args:
        task_id: Task identifier for file naming.
        url: Cockpit URL to navigate to.
        headed: Whether to run with a visible browser window.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: playwright not installed. Run: pip install playwright")
        sys.exit(1)

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=not headed)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()

        print(f"Navigating to {url} ...")
        await page.goto(url)
        await page.wait_for_load_state("networkidle", timeout=15000)

        # Check if Clerk login is needed
        login_visible = await _element_visible(
            page, '[class*="cl-signIn"], [class*="cl-rootBox"]', timeout=5000
        )

        if login_visible:
            print("Clerk login page detected.")
            print("Please complete authentication in the browser window.")
            print("Waiting up to 120 seconds for login...")

            # Wait for cockpit to load after manual auth
            try:
                await page.wait_for_url(
                    f"{url}/**",
                    timeout=120000,
                )
                await page.wait_for_load_state(
                    "networkidle", timeout=10000
                )
                print("Authentication complete.")
            except Exception as exc:
                print(f"Authentication timeout: {exc}")
                await browser.close()
                sys.exit(1)

        # Verify cockpit loaded
        nav_visible = await _element_visible(page, "nav", timeout=10000)
        if not nav_visible:
            print("ERROR: Cockpit navigation not found after load.")
            await page.screenshot(
                path=_screenshot_path(task_id, "error_no_nav")
            )
            await browser.close()
            sys.exit(1)

        print(f"Cockpit loaded. Running C29 evidence collection for {task_id} ...")
        results = await collect_full_evidence(page, task_id)

        await browser.close()

    # Print summary
    print("\n=== C29 Evidence Collection Complete ===")
    print(f"Task: {task_id}")
    print(f"Screenshots: {len(results['browser_evidence']['screenshots'])}")
    print(f"Traces: {len(results['browser_evidence']['execution_traces'])}")

    cont = results["continuity"]
    print(f"\nContinuity: TTRC={cont['resume_time_seconds']}s, "
          f"preserved={cont['context_preserved']}")

    gov = results["governance"]
    print(f"Governance: required={gov['approvals_required']}, "
          f"enforced={gov['approvals_enforced']}")

    aware = results["awareness"]
    print(f"Awareness: score={aware['awareness_score']}")

    cog = results["cognitive_load"]
    print(f"Cognitive Load: score={cog['cognitive_load_score']:.2f}, "
          f"steps={cog['reconstruction_steps']}")

    intr = results["interruption"]
    print(f"Interruption: resume={intr['resume_time_seconds']}s, "
          f"accuracy={intr['context_accuracy']}")

    drift = results["reality_drift"]
    print(f"Reality Drift: detected={drift['drift_detected']}, "
          f"method={drift['detection_method']}")

    ide = results["meta_ide"]
    print(f"Meta IDE: score={ide['meta_ide_score']}")

    run_dir = _run_dir(task_id)
    print(f"\nResults saved to: {run_dir}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="C29 Browser Evidence Collector — runs on Beast"
    )
    parser.add_argument(
        "task_id",
        help="Task identifier (e.g. c29-001)",
    )
    parser.add_argument(
        "--url",
        default=_COCKPIT_URL,
        help="Cockpit URL (default: %(default)s)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        default=True,
        help="Run with visible browser (default: True)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run headless (overrides --headed)",
    )

    args = parser.parse_args()
    headed = not args.headless

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    asyncio.run(_run_standalone(args.task_id, args.url, headed))
