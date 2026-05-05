"""
Pipeline update detection and Notion stage updates.
Extracted from discord_bot.py — detects natural language
pipeline signals (won/lost/booked) and updates Notion.
"""

import re
import sys
import os

_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def detect_pipeline_update(text: str) -> tuple[str, str] | None:
    """
    Detect natural language pipeline stage updates.
    Returns (stage, lead_hint) or None if not a pipeline update.

    Examples:
      "just closed that lead" → ("Won", "")
      "he ghosted" → ("Lost", "")
      "closed alex" → ("Won", "alex")
      "that lead booked a call" → ("Booked", "")
    """
    text_lower = text.lower()

    won_signals = [
        "just closed",
        "closed the deal",
        "closed them",
        "they signed",
        "they paid",
        "just won",
        "deal closed",
        "sale closed",
        "they bought",
        "just sold",
        "sold them",
        "closed a deal",
        "closed a sale",
    ]
    lost_signals = [
        "ghosted",
        "not interested",
        "lost that",
        "dead lead",
        "he left",
        "she left",
        "they left",
        "no response",
        "went cold",
        "lost them",
        "fell off",
        "dropped off",
        "unqualified",
    ]
    booked_signals = [
        "booked a call",
        "scheduled a call",
        "just booked",
        "call booked",
        "set a call",
        "locked in a call",
    ]

    stage = None
    for s in won_signals:
        if s in text_lower:
            stage = "Won"
            break
    # Bare "closed <Name>" pattern
    if not stage:
        if re.search(r"\bclosed\s+[A-Z][a-z]+", text):
            stage = "Won"

    if not stage:
        for s in lost_signals:
            if s in text_lower:
                stage = "Lost"
                break
    if not stage:
        for s in booked_signals:
            if s in text_lower:
                stage = "Booked"
                break

    if not stage:
        return None

    # Try to extract a lead name hint
    username_match = re.search(r"@(\w+)", text)
    lead_hint = username_match.group(1) if username_match else ""

    if not lead_hint:
        name_match = re.search(r"(?:closed|lost|booked|sold|won)\s+([A-Z][a-z]+)", text)
        lead_hint = name_match.group(1) if name_match else ""

    return (stage, lead_hint)


async def handle_pipeline_update(
    message,
    text: str,
) -> bool:
    """
    Check for pipeline update in message text.
    If detected, update Notion and send confirmation.
    Returns True if handled, False otherwise.
    """
    pipeline_update = detect_pipeline_update(text)
    if not pipeline_update:
        return False

    stage, lead_hint = pipeline_update
    try:
        sys.path.insert(0, os.path.join(_REPO_ROOT, "services"))
        from calendly_webhook import update_notion_lead_stage

        success = update_notion_lead_stage(
            name=lead_hint,
            email="",
            new_stage=stage,
        )
        if success:
            await message.channel.send(
                f"Pipeline updated — {lead_hint or 'lead'} moved to **{stage}**."
            )
        else:
            await message.channel.send(
                f"Couldn't find that lead in Notion. Try mentioning their @username."
            )
    except Exception as e:
        await message.channel.send(f"Pipeline update failed: {e}")
    return True
