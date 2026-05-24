"""The Awakening — Phase 12 reality brief synthesis.

Synthesizes all instantiation data into a reality brief that verifies
the populated reality model is correct. The AI states what it knows
about the operator, and the operator confirms or corrects.

Data sources:
  - Onboarding result (identity, business context, stage)
  - Personality config (preset, traits)
  - Discovery scan (platforms, accounts, workspaces)
  - Diagnostic scan (domains, maturity level)
  - Profile inference (primary mode, confidence)
  - Governance config (autonomy levels, domains)
  - Continuity state (session history)

Deterministic template fallback when no LLM is available.

UMH workstation subsystem.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _load_json(path: str | Path) -> dict[str, Any] | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _load_onboarding() -> dict[str, Any] | None:
    return _load_json("data/sessions/onboarding_result.json")


def _load_personality() -> dict[str, Any] | None:
    return _load_json("data/sessions/personality.json")


def _load_discovery() -> dict[str, Any] | None:
    return _load_json("data/sessions/discovery_result.json")


def _load_governance() -> dict[str, Any] | None:
    return _load_json("data/sessions/governance.json")


def _load_profile_inference() -> dict[str, Any] | None:
    return _load_json("data/sessions/profile_inference.json")


def _load_diagnostic_scan() -> dict[str, Any] | None:
    scan_dir = Path("data/diagnostic_scans")
    if not scan_dir.exists():
        return None
    scans = sorted(scan_dir.glob("scan_*.json"), reverse=True)
    if not scans:
        return None
    return _load_json(scans[0])


def _load_continuity_resume() -> dict[str, Any] | None:
    return _load_json("data/runtime/workstation_continuity/resume_state.json")


def gather_reality_data() -> dict[str, Any]:
    """Gather all instantiation data into a single dict."""
    data: dict[str, Any] = {}

    onboarding = _load_onboarding()
    if onboarding:
        data["onboarding"] = onboarding

    personality = _load_personality()
    if personality:
        data["personality"] = personality

    discovery = _load_discovery()
    if discovery:
        data["discovery"] = discovery

    governance = _load_governance()
    if governance:
        data["governance"] = governance

    profile = _load_profile_inference()
    if profile:
        data["profile"] = profile

    diagnostic = _load_diagnostic_scan()
    if diagnostic:
        data["diagnostic_scan"] = diagnostic

    continuity = _load_continuity_resume()
    if continuity:
        data["continuity"] = continuity

    return data


def build_reality_brief(data: dict[str, Any]) -> str:
    """Build a deterministic reality brief from gathered data.

    Template-based synthesis — no LLM required. Uses structured data
    from all instantiation phases to produce a human-readable summary
    that the operator can confirm or correct.
    """
    sections: list[str] = []

    onboarding = data.get("onboarding", {})
    personality = data.get("personality", {})
    discovery = data.get("discovery", {})
    governance = data.get("governance", {})
    profile = data.get("profile", {})
    diagnostic = data.get("diagnostic_scan", {})
    continuity = data.get("continuity", {})

    # Identity section
    operator = onboarding.get("operator_name", "")
    ai_name = onboarding.get("ai_name", os.environ.get("UMH_PERSONA_NAME", "UMH"))
    company = onboarding.get("company_name", "")
    role = onboarding.get("role", "")

    if operator or company:
        identity_parts = []
        if operator:
            identity_parts.append(f"Operator: {operator}")
        if role:
            identity_parts.append(f"Role: {role}")
        if company:
            company_type = onboarding.get("company_type", "")
            if company_type:
                identity_parts.append(f"Company: {company} ({company_type})")
            else:
                identity_parts.append(f"Company: {company}")
        sections.append("Identity\n  " + "\n  ".join(identity_parts))

    # Business context section
    stage = onboarding.get("stage", 0)
    revenue = onboarding.get("current_revenue", 0)
    clients = onboarding.get("client_count", 0)
    offer = onboarding.get("offer_name", "")
    icp = onboarding.get("icp_description", "")
    channel = onboarding.get("primary_channel", "")
    north_star = onboarding.get("north_star", "")
    constraint = onboarding.get("biggest_constraint", "")

    if stage or offer or north_star:
        biz_parts = []
        stage_labels = {1: "Pre-revenue", 2: "Early revenue", 3: "Growing"}
        if stage:
            biz_parts.append(f"Stage: {stage_labels.get(stage, f'Stage {stage}')}")
        if revenue:
            biz_parts.append(f"Revenue: ${revenue:,.0f}/mo")
        if clients:
            biz_parts.append(f"Clients: {clients}")
        if offer:
            price = onboarding.get("offer_price", 0)
            if price:
                biz_parts.append(f"Offer: {offer} (${price:,.0f})")
            else:
                biz_parts.append(f"Offer: {offer}")
        if icp:
            biz_parts.append(f"ICP: {icp}")
        if channel:
            biz_parts.append(f"Channel: {channel}")
        if north_star:
            biz_parts.append(f"North star: {north_star}")
        if constraint:
            biz_parts.append(f"Biggest constraint: {constraint}")
        sections.append("Business Context\n  " + "\n  ".join(biz_parts))

    # Personality section
    preset = personality.get("preset", "")
    if preset:
        sections.append(f"Personality: {preset.capitalize()}")

    # Environment section
    platforms = discovery.get("platforms_found", 0)
    accounts = discovery.get("accounts_found", 0)
    workspaces = discovery.get("workspaces_found", 0)
    maturity = discovery.get("maturity_level", "")

    if platforms or accounts:
        env_parts = []
        if platforms:
            env_parts.append(f"{platforms} platforms detected")
        if accounts:
            env_parts.append(f"{accounts} accounts found")
        if workspaces:
            env_parts.append(f"{workspaces} workspaces mapped")
        if maturity:
            env_parts.append(f"Maturity: {maturity}")
        sections.append("Environment\n  " + "\n  ".join(env_parts))

    # Diagnostic scan section
    scan_domains = diagnostic.get("domains", {})
    scan_maturity = diagnostic.get("maturity_level", "")
    if scan_domains or scan_maturity:
        diag_parts = []
        completed = sum(
            1
            for d in scan_domains.values()
            if isinstance(d, dict) and d.get("status") == "completed"
        )
        total = len(scan_domains)
        if total:
            diag_parts.append(f"Scanned {completed}/{total} domains")
        if scan_maturity:
            diag_parts.append(f"Scan maturity: {scan_maturity}")
        sections.append("Diagnostic Scan\n  " + "\n  ".join(diag_parts))

    # Profile inference section
    primary_mode = profile.get("primary_mode", "")
    confidence = profile.get("confidence", 0)
    if primary_mode:
        conf_pct = f"{confidence * 100:.0f}%" if confidence else "low"
        sections.append(f"Inferred profile: {primary_mode} (confidence: {conf_pct})")

    # Governance section
    gov_domains = governance.get("domains", {})
    if gov_domains:
        high_autonomy = [
            d
            for d, cfg in gov_domains.items()
            if isinstance(cfg, dict) and cfg.get("autonomy") in ("act_freely", "act_with_approval")
        ]
        restricted = [
            d
            for d, cfg in gov_domains.items()
            if isinstance(cfg, dict) and cfg.get("autonomy") in ("none", "read_only")
        ]
        gov_parts = []
        if high_autonomy:
            gov_parts.append(f"High autonomy: {', '.join(high_autonomy[:4])}")
        if restricted:
            gov_parts.append(f"Restricted: {', '.join(restricted[:4])}")
        if gov_parts:
            sections.append("Governance\n  " + "\n  ".join(gov_parts))

    # Session history section
    if continuity:
        cont_state = continuity.get("continuity_state", {})
        total_exec = cont_state.get("total_executions", 0)
        if total_exec:
            sections.append(
                f"Session history: {total_exec} executions, "
                f"{cont_state.get('total_successes', 0)} succeeded"
            )

    if not sections:
        return (
            f"I'm {ai_name}. No instantiation data found yet. "
            "Run `umh setup` to begin the onboarding flow."
        )

    # Build the brief
    header = "Based on what I've observed:"
    if ai_name and ai_name != "UMH":
        header = f"{ai_name} reporting. {header}"

    brief = header + "\n\n" + "\n\n".join(sections)

    # Add recommendation if we have enough context
    if north_star and constraint:
        brief += (
            f"\n\nRecommendation: Your north star is '{north_star}' "
            f"and your biggest constraint is '{constraint}'. "
            f"Focus execution on removing that constraint first."
        )
    elif north_star:
        brief += f"\n\nRecommendation: Stay focused on '{north_star}'."

    brief += "\n\nIs this accurate? Correct anything that's wrong."

    return brief


def run_awakening() -> str:
    """Run The Awakening — gather data and build reality brief."""
    data = gather_reality_data()
    return build_reality_brief(data)


def show_awakening() -> int:
    """Display The Awakening reality brief for the CLI."""
    print()
    print("The Awakening — Reality Brief")
    print("=" * 50)
    print()

    brief = run_awakening()
    print(brief)
    print()
    return 0
