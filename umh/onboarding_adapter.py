"""Onboarding adapter — wraps OnboardingEngine for CLI/voice interaction.

Drives the 15-question onboarding flow via stdin/voice instead of Discord.
Covers Phase 1 (naming) and Phase 4 (business context) of UMH instance
instantiation.

The flow:
  1. OpenClaw naming — AI speaks first, asks operator's name, then AI name
  2. Setup method selection — auto or manual
  3. 15 questions across 6 topic areas (OnboardingEngine)
  4. Deterministic stage extraction + optional LLM analysis
  5. Persona + preferences set from answers
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


@dataclass
class OnboardingResult:
    """Structured output from the onboarding flow."""

    operator_name: str = ""
    ai_name: str = "UMH"
    company_name: str = ""
    company_type: str = ""
    offer_name: str = ""
    offer_price: float = 0.0
    icp_description: str = ""
    primary_channel: str = ""
    current_revenue: float = 0.0
    client_count: int = 0
    north_star: str = ""
    communication_style: str = "direct"
    biggest_constraint: str = ""
    stage: int = 1
    timezone: str = ""
    role: str = ""
    raw_answers: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


def _determine_stage(revenue: float, clients: int) -> int:
    if revenue > 50000:
        return 3
    if revenue > 5000 or clients >= 5:
        return 2
    return 1


def _extract_data_deterministic(answers: dict) -> dict[str, Any]:
    """Extract structured data from raw answers without LLM."""
    data: dict[str, Any] = {}

    for key, entry in answers.items():
        q = entry.get("question", "").lower()
        a = entry.get("answer", "").strip()

        if "your name" in q:
            data["founder_name"] = a
        elif "role or title" in q:
            data["role"] = a
        elif "timezone" in q:
            data["timezone"] = a
        elif "company name" in q:
            data["company_name"] = a
        elif "type of business" in q:
            data["company_type"] = a
        elif "describe what you do" in q:
            data["description"] = a
        elif "primary offer" in q:
            data["offer_name"] = a
            try:
                import re

                price_match = re.search(r"\$?(\d[\d,]*)", a)
                if price_match:
                    data["offer_price"] = float(price_match.group(1).replace(",", ""))
            except Exception:
                pass
        elif "ideal customer" in q:
            data["icp_description"] = a
        elif "channel" in q and "customer" not in q:
            data["primary_channel"] = a
        elif "paying customers" in q:
            try:
                data["client_count"] = int("".join(c for c in a if c.isdigit()) or "0")
            except ValueError:
                data["client_count"] = 0
        elif "monthly revenue" in q:
            try:
                import re

                rev_match = re.search(r"\$?(\d[\d,]*)", a)
                if rev_match:
                    data["current_revenue"] = float(rev_match.group(1).replace(",", ""))
            except Exception:
                data["current_revenue"] = 0
        elif "revenue goal" in q:
            data["north_star"] = a
        elif "one thing" in q:
            data["biggest_constraint"] = a
        elif "named" in q and "ai" in q.lower():
            data["ai_name"] = a
        elif "communicate" in q or "communication" in q:
            data["communication_style"] = a

    return data


def _build_result(data: dict, raw_answers: dict) -> OnboardingResult:
    revenue = float(data.get("current_revenue", 0) or 0)
    clients = int(data.get("client_count", 0) or 0)

    return OnboardingResult(
        operator_name=data.get("founder_name", ""),
        ai_name=data.get("ai_name", "UMH"),
        company_name=data.get("company_name", ""),
        company_type=data.get("company_type", ""),
        offer_name=data.get("offer_name", ""),
        offer_price=float(data.get("offer_price", 0) or 0),
        icp_description=data.get("icp_description", ""),
        primary_channel=data.get("primary_channel", ""),
        current_revenue=revenue,
        client_count=clients,
        north_star=data.get("north_star", ""),
        communication_style=data.get("communication_style", "direct"),
        biggest_constraint=data.get("biggest_constraint", ""),
        stage=_determine_stage(revenue, clients),
        timezone=data.get("timezone", ""),
        role=data.get("role", ""),
        raw_answers=raw_answers,
    )


def _save_result(result: OnboardingResult) -> None:
    """Persist onboarding result to disk and set env vars."""
    data_dir = os.path.join(os.environ.get("UMH_ROOT", "/opt/OS"), "data", "onboarding")
    os.makedirs(data_dir, exist_ok=True)

    path = os.path.join(data_dir, "onboarding_result.json")
    with open(path, "w") as f:
        json.dump(result.as_dict(), f, indent=2)
    logger.info("Onboarding result saved to %s", path)

    os.environ["UMH_PERSONA_NAME"] = result.ai_name
    os.environ["UMH_OPERATOR_NAME"] = result.operator_name


def _apply_persona(result: OnboardingResult) -> None:
    """Set persona from onboarding result."""
    try:
        from substrate.foundation.persona import Persona, PresentationStyle

        style_map = {
            "direct": PresentationStyle.TACTICAL,
            "blunt": PresentationStyle.TACTICAL,
            "coaching": PresentationStyle.CONVERSATIONAL,
            "questions": PresentationStyle.CONVERSATIONAL,
            "analytical": PresentationStyle.FORMAL,
            "data-driven": PresentationStyle.FORMAL,
        }

        style = PresentationStyle.TACTICAL
        comm = result.communication_style.lower()
        for keyword, preset in style_map.items():
            if keyword in comm:
                style = preset
                break

        persona = Persona(name=result.ai_name, presentation_style=style)
        os.environ["UMH_PERSONA_NAME"] = persona.display_name
        logger.info("Persona set: %s (%s)", persona.display_name, style.value)
    except (ImportError, Exception) as exc:
        logger.debug("Persona setup failed: %s", exc)
        os.environ["UMH_PERSONA_NAME"] = result.ai_name


def run_onboarding_cli(text_only: bool = False) -> OnboardingResult | None:
    """Run the interactive onboarding flow via stdin.

    Returns OnboardingResult on success, None if cancelled.
    """
    print()
    print("=" * 50)
    print("  UMH Instance Instantiation")
    print("=" * 50)
    print()

    # Phase 1: OpenClaw naming pattern
    print("I'm your intelligence system. Let's get set up.")
    print()

    operator_name = _ask("Before we begin — what should I call you?")
    if operator_name is None:
        return None

    print(f"\nGood to meet you, {operator_name}.")
    ai_name = _ask("And what should you call me?")
    if ai_name is None:
        return None
    if not ai_name.strip():
        ai_name = "UMH"

    print(f"\n{ai_name}, online.\n")
    os.environ["UMH_PERSONA_NAME"] = ai_name

    # Phase 2: Setup method
    method = _ask("Auto-setup (sensible defaults) or manual (full walkthrough)? [auto/manual]")
    if method is None:
        return None

    if method.strip().lower().startswith("a"):
        print("\nRunning auto-setup with defaults...\n")
        result = OnboardingResult(
            operator_name=operator_name,
            ai_name=ai_name,
        )
        _save_result(result)
        _apply_persona(result)
        return result

    # Phase 4: Full 15-question flow via OnboardingEngine
    print("\nLet's configure your system. This takes about 5 minutes.\n")

    engine = None
    session = None
    try:
        from substrate.control_plane.onboarding.onboarding_engine import OnboardingEngine

        engine = OnboardingEngine(ctx=None)
        session = engine.start_session(org_id="local", user_id=operator_name)
    except (ImportError, Exception) as exc:
        logger.debug("OnboardingEngine not available: %s", exc)

    raw_answers: dict = {}

    if engine is not None and session is not None:
        while True:
            question = engine.get_next_question(session)
            if question is None:
                break

            # Skip name question — already asked in Phase 1
            if "your name" in question.lower() and session.question_index == 0:
                engine.store_answer(session, operator_name)
                continue

            # Skip AI name question — already asked in Phase 1
            if "named" in question.lower() and "ai" in question.lower():
                engine.store_answer(session, ai_name)
                continue

            answer = _ask(question)
            if answer is None:
                return None
            engine.store_answer(session, answer)

        raw_answers = dict(session.answers)
    else:
        # Fallback: ask questions directly without OnboardingEngine
        print("(Running without OnboardingEngine — deterministic mode)\n")
        questions = [
            ("role", "What is your role or title?"),
            ("timezone", "What timezone are you in?"),
            ("company_name", "What is your company name?"),
            (
                "company_type",
                "What type of business? (coaching, agency, SaaS, ecommerce, content, other)",
            ),
            ("description", "Describe what you do in one sentence."),
            ("offer_name", "What is your primary offer? (what + price)"),
            ("icp", "Who is your ideal customer?"),
            ("channel", "What channel do you use to find customers?"),
            ("customers", "How many paying customers do you have?"),
            ("revenue", "What is your current monthly revenue?"),
            ("goal", "Revenue goal for the next 12 months?"),
            ("constraint", "What ONE thing would change everything for your business?"),
            (
                "comm_style",
                "Communication preference? (direct/blunt, coaching/questions, analytical)",
            ),
        ]

        for key, question in questions:
            answer = _ask(question)
            if answer is None:
                return None
            raw_answers[key] = {"question": question, "answer": answer}

    # Extract structured data (deterministic — no LLM needed)
    data = _extract_data_deterministic(raw_answers)
    data.setdefault("founder_name", operator_name)
    data.setdefault("ai_name", ai_name)

    result = _build_result(data, raw_answers)
    _save_result(result)
    _apply_persona(result)

    # Display summary
    _print_summary(result)

    return result


def _ask(question: str) -> str | None:
    """Ask a question via stdin. Returns None on EOF/interrupt."""
    try:
        return input(f"  {question}\n  > ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n\nOnboarding cancelled.")
        return None


def _print_summary(result: OnboardingResult) -> None:
    """Display onboarding completion summary."""
    print()
    print("=" * 50)
    print(f"  {result.ai_name} is online.")
    print("=" * 50)
    print()
    if result.company_name:
        print(f"  Company:    {result.company_name}")
    if result.company_type:
        print(f"  Type:       {result.company_type}")
    print(f"  Stage:      {result.stage}")
    if result.offer_name:
        print(f"  Offer:      {result.offer_name}")
    if result.primary_channel:
        print(f"  Channel:    {result.primary_channel}")
    if result.north_star:
        print(f"  North star: {result.north_star}")
    if result.biggest_constraint:
        print(f"  Constraint: {result.biggest_constraint}")
    print(f"  Comm style: {result.communication_style}")
    print()
    print(f"  Type anything to talk to {result.ai_name}.")
    print()
