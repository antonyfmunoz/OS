"""Phase 10 review dashboard — summary of everything instantiated.

Aggregates all UMH subsystems into a single status view:
onboarding result, personality, permissions, governance, discovery,
profile inference, sensing adapters. This is the "Here's what I know"
moment before The Awakening (Phase 12).
"""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

UMH_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


def _load_onboarding() -> dict | None:
    path = os.path.join(UMH_ROOT, "data", "onboarding", "onboarding_result.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.debug("Failed to load onboarding result: %s", exc)
        return None


def _section_identity(onboarding: dict | None) -> list[str]:
    lines = ["  IDENTITY"]
    if onboarding is None:
        lines.append("    (not configured — run `umh setup`)")
        return lines
    lines.append(f"    Operator:     {onboarding.get('operator_name', '?')}")
    lines.append(f"    AI name:      {onboarding.get('ai_name', '?')}")
    if onboarding.get("company_name"):
        lines.append(f"    Company:      {onboarding['company_name']}")
    if onboarding.get("company_type"):
        lines.append(f"    Type:         {onboarding['company_type']}")
    lines.append(f"    Stage:        {onboarding.get('stage', '?')}")
    if onboarding.get("north_star"):
        lines.append(f"    North star:   {onboarding['north_star']}")
    if onboarding.get("biggest_constraint"):
        lines.append(f"    Constraint:   {onboarding['biggest_constraint']}")
    return lines


def _section_personality() -> list[str]:
    lines = ["", "  PERSONALITY"]
    try:
        from umh.personality import load_personality

        config = load_personality()
        traits = config.traits
        lines.append(f"    Preset:       {config.preset.value}")
        lines.append(f"    Tone/Style:   {traits.tone} / {traits.style}")
        lines.append(f"    Governance:   {traits.governance.value}")
        lines.append(f"    Proactivity:  {traits.proactivity.value}")
        if config.is_multi_mode:
            overrides = ", ".join(f"{m}={p}" for m, p in config.mode_overrides.items())
            lines.append(f"    Mode mapping: {overrides}")
    except Exception as exc:
        logger.debug("Personality load failed: %s", exc)
        lines.append("    (not configured)")
    return lines


def _section_permissions() -> list[str]:
    lines = ["", "  PERMISSIONS"]
    try:
        from umh.permissions import PermissionStore

        store = PermissionStore()
        active = store.list_active()
        if active:
            lines.append(f"    Active grants: {len(active)}")
            for p in active[:8]:
                lines.append(f"      [+] {p.scope.value}")
            if len(active) > 8:
                lines.append(f"      ... and {len(active) - 8} more")
        else:
            lines.append("    No active permissions")

        denied = [p for p in store.list_all() if p.status.value == "denied"]
        if denied:
            lines.append(f"    Denied: {len(denied)}")
    except Exception as exc:
        logger.debug("Permissions load failed: %s", exc)
        lines.append("    (not configured)")
    return lines


def _section_governance() -> list[str]:
    lines = ["", "  GOVERNANCE"]
    try:
        from umh.governance_config import load_governance

        prefs = load_governance()
        lines.append(f"    Autonomy:     {prefs.global_autonomy.value}")
        lines.append(f"    Notifications: {prefs.notification_frequency.value}")
        lines.append(f"    Retention:    {prefs.data_retention.value}")
        overrides = len(prefs.domain_overrides)
        if overrides:
            lines.append(f"    Custom domains: {overrides}")
    except Exception as exc:
        logger.debug("Governance load failed: %s", exc)
        lines.append("    (defaults active)")
    return lines


def _section_discovery() -> list[str]:
    lines = ["", "  ENVIRONMENT"]
    try:
        from umh.discovery import DiscoveryScanner

        scanner = DiscoveryScanner()
        result = scanner.get_latest_result()
        if result:
            lines.append(f"    Platforms:     {result.platforms_found}")
            lines.append(f"    Accounts:      {result.accounts_found}")
            lines.append(f"    Workspaces:    {result.workspaces_found}")
            lines.append(f"    Maturity:      {result.maturity_level}")
        else:
            lines.append("    (no scan results — run `umh discover`)")
    except Exception as exc:
        logger.debug("Discovery load failed: %s", exc)
        lines.append("    (discovery unavailable)")

    try:
        from umh.diagnostic_scan import DiagnosticScanner

        scanner = DiagnosticScanner()
        result = scanner.get_latest_result()
        if result:
            lines.append(
                f"    Deep scan:     {result.domains_completed}/{result.domains_scanned} domains"
            )
            lines.append(f"    Entities:      {result.total_entities}")
            lines.append(f"    Scan maturity: {result.maturity_level}")
    except Exception as exc:
        logger.debug("Diagnostic scan load failed: %s", exc)

    return lines


def _section_profile() -> list[str]:
    lines = ["", "  PROFILE"]
    try:
        from umh.profile_inference import load_inference, run_full_inference

        result = load_inference()
        if result is None:
            result = run_full_inference()
        lines.append(f"    Primary mode:  {result.primary_mode}")
        if result.suggestions:
            top = result.suggestions[:3]
            for s in top:
                lines.append(f"      {s.mode}: {s.confidence:.0%} ({s.source})")
        if result.event_count:
            lines.append(f"    Events:        {result.event_count}")
    except Exception as exc:
        logger.debug("Profile inference failed: %s", exc)
        lines.append("    (inference not yet run)")
    return lines


def _section_sensing() -> list[str]:
    lines = ["", "  SENSING"]
    try:
        from substrate.sockets.sensing_port import sensing_summary

        summary = sensing_summary()
        total = summary.get("total", 0)
        if total > 0:
            lines.append(f"    Adapters:      {total} registered")
            families = summary.get("families", [])
            if families:
                lines.append(f"    Families:      {', '.join(families)}")
            by_state = summary.get("by_state", {})
            if by_state:
                state_str = ", ".join(f"{k}: {v}" for k, v in by_state.items())
                lines.append(f"    State:         {state_str}")
        else:
            lines.append("    No sensing adapters registered")
    except Exception as exc:
        logger.debug("Sensing summary failed: %s", exc)
        lines.append("    (sensing port not active)")
    return lines


def _section_workstation() -> list[str]:
    lines = ["", "  WORKSTATION"]
    try:
        from umh.profile import ProfileManager

        pm = ProfileManager()
        prefs = pm.get_preferences()
        lines.append(f"    Voice:         {prefs.voice_mode.replace('_', '-')}")
        lines.append(f"    Webcam:        {'enabled' if prefs.webcam_enabled else 'disabled'}")
        lines.append(f"    Default mode:  {prefs.default_profile}")
        lines.append(f"    Auto-away:     {prefs.auto_away_minutes} min")
        lines.append(
            f"    Mode stacking: {'enabled' if prefs.mode_stacking_enabled else 'disabled'}"
        )
    except Exception as exc:
        logger.debug("Workstation preferences load failed: %s", exc)
        lines.append("    (preferences unavailable)")
    return lines


def show_review() -> int:
    """Display the complete instance review dashboard."""
    onboarding = _load_onboarding()
    ai_name = (onboarding or {}).get("ai_name", "UMH")

    all_lines: list[str] = []
    all_lines.append("")
    all_lines.append("=" * 56)
    all_lines.append(f"  UMH Instance Review — {ai_name}")
    all_lines.append("=" * 56)

    all_lines.extend(_section_identity(onboarding))
    all_lines.extend(_section_personality())
    all_lines.extend(_section_permissions())
    all_lines.extend(_section_governance())
    all_lines.extend(_section_discovery())
    all_lines.extend(_section_profile())
    all_lines.extend(_section_sensing())
    all_lines.extend(_section_workstation())

    # Instantiation completeness
    sections = {
        "Identity": onboarding is not None,
        "Personality": True,
        "Permissions": True,
        "Governance": True,
        "Discovery": _has_discovery(),
        "Profile": _has_profile(),
        "Workstation": True,
    }

    all_lines.append("")
    all_lines.append("  INSTANTIATION STATUS")
    complete = sum(1 for v in sections.values() if v)
    total = len(sections)
    all_lines.append(f"    {complete}/{total} sections configured")
    for name, done in sections.items():
        icon = "+" if done else "-"
        all_lines.append(f"    [{icon}] {name}")

    all_lines.append("=" * 56)
    all_lines.append("")

    print("\n".join(all_lines))
    return 0


def _has_discovery() -> bool:
    discovery_dir = os.path.join(UMH_ROOT, "data", "environment_maps")
    if os.path.isdir(discovery_dir):
        return any(f.startswith("scan_") for f in os.listdir(discovery_dir))
    return False


def _has_profile() -> bool:
    inference_file = os.path.join(UMH_ROOT, "data", "sessions", "inferred_profiles.json")
    return os.path.exists(inference_file)
